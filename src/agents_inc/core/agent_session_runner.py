from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List

from agents_inc.core.backends.registry import resolve_backend
from agents_inc.core.codex_app_client import CodexAppClient, CodexAppServerError
from agents_inc.core.codex_home import codex_launch_env
from agents_inc.core.fabric_lib import now_iso, write_text
from agents_inc.core.transcript_capture import redact_text

WORK_BLOCK_RE = re.compile(r"BEGIN_WORK\s*(.*?)\s*END_WORK", re.DOTALL | re.IGNORECASE)
HANDOFF_BLOCK_RE = re.compile(
    r"BEGIN_HANDOFF_JSON\s*(\{.*?\})\s*END_HANDOFF_JSON",
    re.DOTALL | re.IGNORECASE,
)
JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL | re.IGNORECASE)


@dataclass
class AgentRunConfig:
    project_root: Path
    prompt: str
    raw_log_path: Path
    redacted_log_path: Path
    work_dir: Path | None = None
    codex_home: Path | None = None
    thread_id: str | None = None
    timeout_sec: int = 0
    web_search: bool = True
    session_label: str = ""
    model: str | None = None
    model_reasoning_effort: str | None = None
    disable_mcp: bool = False
    approval_policy: str | None = None
    sandbox_mode: str | None = None
    sandbox_cd_dir: Path | None = None
    sandbox_network_access: bool | None = None
    stream_callback: Callable[[Dict[str, object]], None] | None = None


@dataclass
class AgentRunResult:
    success: bool
    return_code: int
    stdout: str
    stderr: str
    raw_text: str
    parsed_work: str
    parsed_handoff: Dict[str, object]
    error: str
    started_at: str
    finished_at: str
    backend: str
    thread_id: str
    used_resume: bool
    rotated_thread: bool
    parse_mode: str


class AgentSessionRunner:
    """Run specialist/head sessions in isolated Codex executions."""

    def __init__(self, backend: str | None = None):
        chosen = (
            backend
            or os.environ.get("AGENTS_INC_BACKEND")
            or os.environ.get("AGENTS_INC_AGENT_RUNNER")
            or "codex"
        ).strip()
        self._backend_adapter = resolve_backend(chosen)
        self.backend = self._backend_adapter.name

    def run(self, config: AgentRunConfig) -> AgentRunResult:
        return self._backend_adapter.run(self, config)

    def _run_codex(self, config: AgentRunConfig) -> AgentRunResult:
        started = now_iso()
        codex_bin = shutil.which("codex")
        if not codex_bin:
            finished = now_iso()
            message = "codex binary not found on PATH"
            self._write_logs(
                config,
                raw_text=message,
            )
            return AgentRunResult(
                success=False,
                return_code=127,
                stdout="",
                stderr=message,
                raw_text=message,
                parsed_work="",
                parsed_handoff={},
                error=message,
                started_at=started,
                finished_at=finished,
                backend=self.backend,
                thread_id="",
                used_resume=False,
                rotated_thread=False,
                parse_mode="",
            )

        if config.stream_callback is not None and not bool(config.disable_mcp):
            return self._run_codex_via_app_server(config=config, started=started)

        used_resume = bool(str(config.thread_id or "").strip())
        primary_cmd = self._build_codex_cmd(
            codex_bin=codex_bin,
            prompt=self._prompt_with_web_mode(config.prompt, config.web_search),
            thread_id=(str(config.thread_id or "").strip() or None),
            model=config.model,
            model_reasoning_effort=config.model_reasoning_effort,
            disable_mcp=bool(config.disable_mcp),
            approval_policy=config.approval_policy,
            sandbox_mode=config.sandbox_mode,
            sandbox_cd_dir=config.sandbox_cd_dir,
            sandbox_network_access=config.sandbox_network_access,
        )

        try:
            primary_proc = self._run_process(config=config, cmd=primary_cmd)
            primary_raw = (primary_proc.stdout or "") + "\n" + (primary_proc.stderr or "")
            thread_id, agent_text = _extract_exec_json(primary_raw)
            parse_input = agent_text if agent_text else primary_raw
            parsed_work, parsed_handoff, parse_error, parse_mode = _parse_session_output(parse_input)
            success = primary_proc.returncode == 0 and not parse_error
            rotated = False
            final_proc = primary_proc
            final_raw = primary_raw
            final_thread_id = thread_id
            final_agent_text = agent_text

            if not success and used_resume:
                # Resume may fail due stale/missing thread. Rotate to a fresh thread once.
                rotate_cmd = self._build_codex_cmd(
                    codex_bin=codex_bin,
                    prompt=self._prompt_with_web_mode(config.prompt, config.web_search),
                    thread_id=None,
                    model=config.model,
                    model_reasoning_effort=config.model_reasoning_effort,
                    disable_mcp=bool(config.disable_mcp),
                    approval_policy=config.approval_policy,
                    sandbox_mode=config.sandbox_mode,
                    sandbox_cd_dir=config.sandbox_cd_dir,
                    sandbox_network_access=config.sandbox_network_access,
                )
                rotate_proc = self._run_process(config=config, cmd=rotate_cmd)
                rotate_raw = (rotate_proc.stdout or "") + "\n" + (rotate_proc.stderr or "")
                rotate_thread_id, rotate_agent_text = _extract_exec_json(rotate_raw)
                rotate_parse_input = rotate_agent_text if rotate_agent_text else rotate_raw
                rotate_work, rotate_handoff, rotate_error, rotate_parse_mode = _parse_session_output(
                    rotate_parse_input
                )
                if rotate_proc.returncode == 0 and not rotate_error:
                    success = True
                    parse_error = ""
                    parse_mode = rotate_parse_mode
                    parsed_work = rotate_work
                    parsed_handoff = rotate_handoff
                    final_proc = rotate_proc
                    final_raw = primary_raw + "\n--- THREAD_ROTATION_FALLBACK ---\n" + rotate_raw
                    final_thread_id = rotate_thread_id
                    final_agent_text = rotate_agent_text
                    rotated = True
                else:
                    final_raw = primary_raw + "\n--- THREAD_ROTATION_FAILED ---\n" + rotate_raw
                    parse_error = parse_error or rotate_error or "agent failed"
                    final_proc = rotate_proc if rotate_proc.returncode != 0 else primary_proc
                    final_thread_id = rotate_thread_id or thread_id

            if parse_mode:
                final_raw = final_raw.rstrip() + f"\n--- PARSE_MODE:{parse_mode} ---\n"
            self._write_logs(config, raw_text=final_raw)
            finished = now_iso()
            if not parse_error and success and not parsed_work and final_agent_text:
                parse_error = "missing BEGIN_WORK/END_WORK block"
                success = False
            return AgentRunResult(
                success=success,
                return_code=int(final_proc.returncode),
                stdout=final_proc.stdout or "",
                stderr=final_proc.stderr or "",
                raw_text=final_raw,
                parsed_work=parsed_work,
                parsed_handoff=parsed_handoff,
                error=parse_error,
                started_at=started,
                finished_at=finished,
                backend=self.backend,
                thread_id=str(final_thread_id or ""),
                used_resume=used_resume,
                rotated_thread=rotated,
                parse_mode=parse_mode,
            )
        except subprocess.TimeoutExpired as exc:
            stdout = self._coerce_text(exc.stdout)
            stderr = self._coerce_text(exc.stderr)
            raw_text = stdout + "\n" + stderr
            raw_text = raw_text.strip() + "\nTIMEOUT"
            self._write_logs(config, raw_text=raw_text)
            finished = now_iso()
            return AgentRunResult(
                success=False,
                return_code=124,
                stdout=stdout,
                stderr=stderr,
                raw_text=raw_text,
                parsed_work="",
                parsed_handoff={},
                error="agent session timeout",
                started_at=started,
                finished_at=finished,
                backend=self.backend,
                thread_id=str(config.thread_id or ""),
                used_resume=used_resume,
                rotated_thread=False,
                parse_mode="",
            )

    def _run_codex_via_app_server(
        self, *, config: AgentRunConfig, started: str
    ) -> AgentRunResult:
        used_resume = bool(str(config.thread_id or "").strip())
        rotated = False
        thread_id = str(config.thread_id or "").strip()
        session_cwd = Path(
            config.sandbox_cd_dir or config.work_dir or config.project_root
        ).expanduser().resolve()
        event_lines: List[str] = []
        client = CodexAppClient(
            cwd=session_cwd,
            env=self._launch_env(config),
            approval_policy=str(config.approval_policy or "never"),
            sandbox_mode=str(config.sandbox_mode or "workspace-write"),
            network_access=(
                bool(config.sandbox_network_access)
                if config.sandbox_network_access is not None
                else True
            ),
        )

        def _forward_event(event: Dict[str, object]) -> None:
            event_lines.append(json.dumps(event, ensure_ascii=False))
            self._emit_stream_event(config, event)

        try:
            client.start()
            try:
                active_thread_id = (
                    client.resume_thread(thread_id) if thread_id else client.start_thread()
                )
            except CodexAppServerError:
                if used_resume:
                    active_thread_id = client.start_thread()
                    rotated = True
                else:
                    raise
            turn = client.run_turn(
                thread_id=active_thread_id,
                text=self._prompt_with_web_mode(config.prompt, config.web_search),
                timeout_sec=float(max(0, int(config.timeout_sec or 0))),
                event_callback=_forward_event,
            )
            parse_input = str(turn.text or "")
            parsed_work, parsed_handoff, parse_error, parse_mode = _parse_session_output(parse_input)
            success = not parse_error
            raw_parts = list(event_lines)
            if parse_mode:
                raw_parts.append(f"--- PARSE_MODE:{parse_mode} ---")
            raw_parts.append(parse_input)
            raw_text = "\n".join(part for part in raw_parts if str(part).strip()).rstrip() + "\n"
            self._write_logs(config, raw_text=raw_text)
            finished = now_iso()
            if success and not parsed_work and parse_input:
                parse_error = "missing BEGIN_WORK/END_WORK block"
                success = False
            return AgentRunResult(
                success=success,
                return_code=0 if success else 1,
                stdout=parse_input,
                stderr="",
                raw_text=raw_text,
                parsed_work=parsed_work,
                parsed_handoff=parsed_handoff,
                error=parse_error,
                started_at=started,
                finished_at=finished,
                backend=self.backend,
                thread_id=str(turn.thread_id or active_thread_id),
                used_resume=used_resume,
                rotated_thread=rotated,
                parse_mode=parse_mode,
            )
        except CodexAppServerError as exc:
            raw_text = "\n".join(event_lines + [str(exc).strip()]).rstrip() + "\n"
            self._write_logs(config, raw_text=raw_text)
            finished = now_iso()
            return AgentRunResult(
                success=False,
                return_code=1,
                stdout="",
                stderr=str(exc),
                raw_text=raw_text,
                parsed_work="",
                parsed_handoff={},
                error=str(exc),
                started_at=started,
                finished_at=finished,
                backend=self.backend,
                thread_id=thread_id,
                used_resume=used_resume,
                rotated_thread=rotated,
                parse_mode="",
            )
        finally:
            client.close()

    def _run_mock(self, config: AgentRunConfig) -> AgentRunResult:
        started = now_iso()
        label = config.session_label or "agent"
        thread_id = str(config.thread_id or "").strip()
        if not thread_id:
            safe = re.sub(r"[^a-z0-9-]+", "-", label.lower()).strip("-") or "agent"
            thread_id = f"mock-{safe}-{int(datetime_from_iso(started).timestamp())}"
        role_match = re.search(r"^Role:\s*(.+)$", str(config.prompt), re.MULTILINE)
        role = str(role_match.group(1)).strip().lower() if role_match else ""
        citation = "https://example.org/mock-evidence"
        if role in {"domain-core", "domain_core", "domain"}:
            citation = "local:references/domain-core.md"
        evidence_ref = {
            "evidence_id": "ev_mock_001",
            "citation": citation,
            "title": "mock evidence",
            "source_type": "web" if citation.startswith("http") else "reference",
        }
        handoff = {
            "schema_version": "4.0",
            "status": "COMPLETE",
            "assumptions": ["mock runner"],
            "claims": [
                {
                    "claim": f"{label} completed specialist task.",
                    "evidence_ids": [evidence_ref["evidence_id"]],
                }
            ],
            "evidence_refs": [evidence_ref],
            "repro_steps": ["Run mocked specialist session"],
            "artifact_paths": [],
            "execution_status": "COMPLETE",
            "dependencies_satisfied": True,
            "produced_artifacts": [],
            "citations_summary": {
                "count": 1,
                "has_web_url": bool(citation.startswith("http")),
            },
        }
        if role == "web-research":
            handoff["claims"] = [
                {"claim": f"{label} web claim 1", "evidence_ids": ["ev_mock_a"]},
                {"claim": f"{label} web claim 2", "evidence_ids": ["ev_mock_b"]},
                {"claim": f"{label} web claim 3", "evidence_ids": ["ev_mock_c"]},
            ]
            handoff["evidence_refs"] = [
                {
                    "evidence_id": "ev_mock_a",
                    "citation": "https://example.org/a",
                    "title": "mock a",
                    "source_type": "web",
                },
                {
                    "evidence_id": "ev_mock_b",
                    "citation": "https://example.org/b",
                    "title": "mock b",
                    "source_type": "web",
                },
                {
                    "evidence_id": "ev_mock_c",
                    "citation": "https://example.org/c",
                    "title": "mock c",
                    "source_type": "web",
                },
            ]
            handoff["citations_summary"] = {
                "count": 3,
                "has_web_url": True,
            }
        elif role == "evidence-review":
            handoff["contradictions"] = False
            handoff["unsupported_claims"] = []
        elif role == "repro-qa":
            handoff["repro_commands"] = ["pytest -q"]
            handoff["expected_outputs"] = ["all tests passed"]
        elif role == "integration":
            handoff["dependencies_consumed"] = []
            handoff["integration_risks"] = []
        work = (
            "# Work\n\n"
            f"Mock execution for `{label}` at {started}. "
            "This run produced an evidence-backed objective response with explicit decision basis, "
            "cross-check assumptions, and concrete next actions for downstream validation. "
            "Quality gates were evaluated for coverage, evidence sufficiency, and integration readiness.\n"
        )
        mock_live_notes = [
            f"LIVE_NOTE: {label} opened the objective and established the working frame.",
            f"LIVE_NOTE: {label} checked evidence sufficiency and narrowed the leading path.",
            f"LIVE_NOTE: {label} prepared the final structured handoff.",
        ]
        if config.stream_callback is not None:
            self._emit_stream_event(
                config,
                {
                    "event": "agent_message",
                    "text": "\n".join(mock_live_notes) + "\n",
                },
            )
        raw_text = (
            "\n".join(mock_live_notes)
            + "\nBEGIN_WORK\n"
            + work
            + "\nEND_WORK\nBEGIN_HANDOFF_JSON\n"
            + json.dumps(handoff, indent=2)
            + "\nEND_HANDOFF_JSON\n"
        )
        self._write_logs(config, raw_text=raw_text)
        finished = now_iso()
        return AgentRunResult(
            success=True,
            return_code=0,
            stdout=raw_text,
            stderr="",
            raw_text=raw_text,
            parsed_work=work,
            parsed_handoff=handoff,
            error="",
            started_at=started,
            finished_at=finished,
            backend=self.backend,
            thread_id=thread_id,
            used_resume=bool(config.thread_id),
            rotated_thread=False,
            parse_mode="strict",
        )

    @staticmethod
    def _write_logs(config: AgentRunConfig, raw_text: str) -> None:
        config.raw_log_path.parent.mkdir(parents=True, exist_ok=True)
        write_text(config.raw_log_path, raw_text.rstrip() + "\n")
        write_text(config.redacted_log_path, redact_text(raw_text).rstrip() + "\n")

    @staticmethod
    def _prompt_with_web_mode(prompt: str, web_search: bool) -> str:
        if not web_search:
            return prompt
        return (
            "Web evidence mode: enabled. Use available web search capabilities to ground key claims when possible.\n\n"
            + prompt
        )

    @staticmethod
    def _coerce_text(value: object) -> str:
        if value is None:
            return ""
        if isinstance(value, bytes):
            return value.decode("utf-8", errors="replace")
        return str(value)

    @staticmethod
    def _launch_env(config: AgentRunConfig) -> Dict[str, str]:
        env = codex_launch_env(config.project_root)
        if config.codex_home is not None:
            env["CODEX_HOME"] = str(config.codex_home)
        return env

    @staticmethod
    def _build_codex_cmd(
        *,
        codex_bin: str,
        prompt: str,
        thread_id: str | None,
        model: str | None = None,
        model_reasoning_effort: str | None = None,
        disable_mcp: bool = False,
        approval_policy: str | None = None,
        sandbox_mode: str | None = None,
        sandbox_cd_dir: Path | None = None,
        sandbox_network_access: bool | None = None,
    ) -> list[str]:
        cmd: list[str] = [codex_bin, "exec"]
        if thread_id:
            cmd.append("resume")
        cmd.extend(["--json", "--skip-git-repo-check"])
        model_name = str(model or "").strip()
        if model_name:
            cmd.extend(["--model", model_name])
        effort = str(model_reasoning_effort or "").strip()
        if effort:
            cmd.extend(["-c", f'model_reasoning_effort="{effort}"'])
        policy = str(approval_policy or "").strip()
        if policy:
            cmd.extend(["-c", f'approval_policy="{policy}"'])
        sandbox = str(sandbox_mode or "").strip()
        if sandbox:
            cmd.extend(["-s", sandbox])
        if sandbox == "workspace-write" and sandbox_network_access is not None:
            cmd.extend(
                [
                    "-c",
                    "sandbox_workspace_write.network_access="
                    + ("true" if sandbox_network_access else "false"),
                ]
            )
        cd_dir = str(sandbox_cd_dir or "").strip()
        if cd_dir:
            cmd.extend(["--cd", cd_dir])
        if disable_mcp:
            cmd.extend(["-c", "mcp_servers={}"])
        if thread_id:
            cmd.extend([thread_id, prompt])
        else:
            cmd.append(prompt)
        return cmd

    def _run_process(
        self, *, config: AgentRunConfig, cmd: list[str]
    ) -> subprocess.CompletedProcess:
        timeout_value: int | None = None
        try:
            parsed_timeout = int(config.timeout_sec)
        except Exception:
            parsed_timeout = 0
        if parsed_timeout > 0:
            timeout_value = parsed_timeout
        if config.stream_callback is None:
            return subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout_value,
                env=self._launch_env(config),
                cwd=str(config.work_dir or config.project_root),
            )

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            env=self._launch_env(config),
            cwd=str(config.work_dir or config.project_root),
        )
        if proc.stdout is None or proc.stderr is None:
            raise RuntimeError("failed to create subprocess pipes")

        stdout_chunks: List[str] = []
        stderr_chunks: List[str] = []

        def _reader(stream_name: str, stream, sink: List[str]) -> None:  # type: ignore[no-untyped-def]
            try:
                for chunk in iter(stream.readline, ""):
                    sink.append(chunk)
                    self._emit_stream_event(
                        config,
                        {
                            "event": "raw_line",
                            "stream": stream_name,
                            "text": chunk,
                        },
                    )
                    for parsed in _extract_exec_stream_events(chunk):
                        self._emit_stream_event(config, parsed)
            finally:
                try:
                    stream.close()
                except Exception:
                    return

        stdout_thread = threading.Thread(
            target=_reader, args=("stdout", proc.stdout, stdout_chunks), daemon=True
        )
        stderr_thread = threading.Thread(
            target=_reader, args=("stderr", proc.stderr, stderr_chunks), daemon=True
        )
        stdout_thread.start()
        stderr_thread.start()
        try:
            proc.wait(timeout=timeout_value)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
            stdout_thread.join()
            stderr_thread.join()
            raise subprocess.TimeoutExpired(
                cmd=cmd,
                timeout=timeout_value if timeout_value is not None else 0,
                output="".join(stdout_chunks),
                stderr="".join(stderr_chunks),
            )

        stdout_thread.join()
        stderr_thread.join()
        return subprocess.CompletedProcess(
            cmd,
            int(proc.returncode),
            stdout="".join(stdout_chunks),
            stderr="".join(stderr_chunks),
        )

    @staticmethod
    def _emit_stream_event(config: AgentRunConfig, event: Dict[str, object]) -> None:
        callback = config.stream_callback
        if callback is None:
            return
        try:
            callback(dict(event))
        except Exception:
            return


def _extract_exec_json(raw_text: str) -> tuple[str, str]:
    thread_id = ""
    agent_messages: list[str] = []
    for line in raw_text.splitlines():
        for event in _extract_exec_stream_events(line):
            kind = str(event.get("event") or "")
            if kind == "thread_started":
                thread = str(event.get("thread_id") or "").strip()
                if thread:
                    thread_id = thread
            elif kind == "agent_message":
                text = str(event.get("text") or "").strip()
                if text:
                    agent_messages.append(text)
    return thread_id, "\n\n".join(agent_messages).strip()


def _extract_exec_stream_events(raw_line: str) -> List[Dict[str, object]]:
    stripped = str(raw_line or "").strip()
    if not stripped.startswith("{") or not stripped.endswith("}"):
        return []
    try:
        payload = json.loads(stripped)
    except Exception:
        return []
    if not isinstance(payload, dict):
        return []

    candidates = [payload]
    if str(payload.get("type") or "").strip() == "event_msg":
        nested = payload.get("payload")
        if isinstance(nested, dict):
            candidates = [nested]

    out: List[Dict[str, object]] = []
    for item in candidates:
        out.extend(_extract_exec_stream_events_from_payload(item))
    return out


def _extract_exec_stream_events_from_payload(payload: Dict[str, object]) -> List[Dict[str, object]]:
    out: List[Dict[str, object]] = []
    event_type = str(payload.get("type") or "").strip()
    method = str(payload.get("method") or "").strip()
    params = payload.get("params") if isinstance(payload.get("params"), dict) else {}

    if event_type == "thread.started":
        thread = str(payload.get("thread_id") or "").strip()
        if thread:
            out.append({"event": "thread_started", "thread_id": thread})
    elif method == "thread/started":
        params_thread = str(params.get("threadId") or params.get("thread_id") or "").strip()
        if params_thread:
            out.append({"event": "thread_started", "thread_id": params_thread})

    if method == "item/agentMessage/delta":
        delta_text = str(params.get("delta") or "")
        if delta_text:
            out.append({"event": "agent_delta", "text": delta_text})

    if method == "item/completed":
        item = params.get("item") if isinstance(params.get("item"), dict) else {}
        if str(item.get("type") or "").strip() == "agentMessage":
            text = str(item.get("text") or "").strip()
            if text:
                out.append({"event": "agent_message", "text": text})

    if event_type == "item.completed":
        item = payload.get("item")
        if isinstance(item, dict) and str(item.get("type") or "").strip() == "agent_message":
            text = str(item.get("text") or "").strip()
            if text:
                out.append({"event": "agent_message", "text": text})

    if event_type in {"message.delta", "response.output_text.delta"}:
        delta_text = str(payload.get("delta") or "").strip()
        if delta_text:
            out.append({"event": "agent_delta", "text": delta_text})

    if event_type == "item.delta":
        item = payload.get("item")
        if isinstance(item, dict) and str(item.get("type") or "").strip() in {
            "agent_message",
            "agentMessage",
        }:
            delta_text = str(payload.get("delta") or item.get("delta") or "").strip()
            if delta_text:
                out.append({"event": "agent_delta", "text": delta_text})

    return out


def datetime_from_iso(value: str):
    from datetime import datetime, timezone

    parsed = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(parsed)
    except Exception:
        return datetime.now(timezone.utc)


def _parse_session_output(raw_text: str) -> tuple[str, Dict[str, object], str, str]:
    work_match = WORK_BLOCK_RE.search(raw_text)
    handoff_match = HANDOFF_BLOCK_RE.search(raw_text)

    if work_match and handoff_match:
        work_text = work_match.group(1).strip()
        handoff_raw = handoff_match.group(1).strip()
        try:
            payload = json.loads(handoff_raw)
        except Exception as exc:  # noqa: BLE001
            return work_text, {}, f"invalid handoff json: {exc}", "strict"

        if not isinstance(payload, dict):
            return work_text, {}, "handoff payload must be JSON object", "strict"
        return work_text, payload, "", "strict"

    return _parse_session_output_fallback(raw_text, work_match)


def _parse_session_output_fallback(
    raw_text: str, work_match: re.Match[str] | None
) -> tuple[str, Dict[str, object], str, str]:
    payload: Dict[str, object] = {}
    payload_span: tuple[int, int] | None = None

    for match in JSON_FENCE_RE.finditer(raw_text):
        snippet = str(match.group(1) or "").strip()
        if not snippet:
            continue
        try:
            parsed = json.loads(snippet)
        except Exception:
            continue
        if isinstance(parsed, dict):
            payload = parsed
            payload_span = (match.start(0), match.end(0))

    if not payload:
        parsed_obj, span = _extract_last_json_object(raw_text)
        if isinstance(parsed_obj, dict):
            payload = parsed_obj
            payload_span = span

    if not payload:
        if work_match is None:
            return "", {}, "missing BEGIN_WORK/END_WORK block", ""
        return work_match.group(1).strip(), {}, "missing BEGIN_HANDOFF_JSON/END_HANDOFF_JSON block", ""

    if work_match is not None:
        work_text = work_match.group(1).strip()
    else:
        trimmed = raw_text
        if payload_span is not None:
            start, end = payload_span
            trimmed = (raw_text[:start] + raw_text[end:]).strip()
        work_text = trimmed.strip()

    if not work_text:
        work_text = (
            "# Work Notes\n\n"
            "Recovered work notes from fallback parse because strict BEGIN_WORK/END_WORK markers were missing."
        )
    return work_text, payload, "", "fallback"


def _extract_last_json_object(raw_text: str) -> tuple[object | None, tuple[int, int] | None]:
    decoder = json.JSONDecoder()
    best_obj: object | None = None
    best_span: tuple[int, int] | None = None
    best_len = -1
    best_start = -1
    for index, char in enumerate(raw_text):
        if char != "{":
            continue
        try:
            parsed, end_index = decoder.raw_decode(raw_text[index:])
        except Exception:
            continue
        if not isinstance(parsed, dict):
            continue
        span_len = int(end_index)
        if span_len > best_len or (span_len == best_len and index > best_start):
            best_obj = parsed
            best_span = (index, index + span_len)
            best_len = span_len
            best_start = index
    return best_obj, best_span
