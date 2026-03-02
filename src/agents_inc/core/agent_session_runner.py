from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict

from agents_inc.core.backends.registry import resolve_backend
from agents_inc.core.codex_home import codex_launch_env
from agents_inc.core.fabric_lib import now_iso, write_text
from agents_inc.core.transcript_capture import redact_text

WORK_BLOCK_RE = re.compile(r"BEGIN_WORK\s*(.*?)\s*END_WORK", re.DOTALL | re.IGNORECASE)
HANDOFF_BLOCK_RE = re.compile(
    r"BEGIN_HANDOFF_JSON\s*(\{.*?\})\s*END_HANDOFF_JSON",
    re.DOTALL | re.IGNORECASE,
)


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
            )

        used_resume = bool(str(config.thread_id or "").strip())
        primary_cmd = self._build_codex_cmd(
            codex_bin=codex_bin,
            prompt=self._prompt_with_web_mode(config.prompt, config.web_search),
            thread_id=(str(config.thread_id or "").strip() or None),
        )

        try:
            primary_proc = self._run_process(config=config, cmd=primary_cmd)
            primary_raw = (primary_proc.stdout or "") + "\n" + (primary_proc.stderr or "")
            thread_id, agent_text = _extract_exec_json(primary_raw)
            parse_input = agent_text if agent_text else primary_raw
            parsed_work, parsed_handoff, parse_error = _parse_session_output(parse_input)
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
                )
                rotate_proc = self._run_process(config=config, cmd=rotate_cmd)
                rotate_raw = (rotate_proc.stdout or "") + "\n" + (rotate_proc.stderr or "")
                rotate_thread_id, rotate_agent_text = _extract_exec_json(rotate_raw)
                rotate_parse_input = rotate_agent_text if rotate_agent_text else rotate_raw
                rotate_work, rotate_handoff, rotate_error = _parse_session_output(
                    rotate_parse_input
                )
                if rotate_proc.returncode == 0 and not rotate_error:
                    success = True
                    parse_error = ""
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
            )

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
        handoff = {
            "schema_version": "3.0",
            "status": "COMPLETE",
            "assumptions": ["mock runner"],
            "claims_with_citations": [
                {
                    "claim": f"{label} completed specialist task.",
                    "citation": citation,
                }
            ],
            "repro_steps": ["Run mocked specialist session"],
            "artifact_paths": [],
            "execution_status": "COMPLETE",
            "dependencies_satisfied": True,
            "produced_artifacts": [],
            "citations_summary": {
                "count": 1,
                "has_web_url": True,
            },
        }
        if role == "web-research":
            handoff["source_quality_note"] = "Mock source quality note."
            handoff["claims_with_citations"] = [
                {"claim": f"{label} web claim 1", "citation": "https://example.org/a"},
                {"claim": f"{label} web claim 2", "citation": "https://example.org/b"},
                {"claim": f"{label} web claim 3", "citation": "https://example.org/c"},
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
        work = f"# Work\n\nMock execution for `{label}` at {started}.\n"
        raw_text = (
            "BEGIN_WORK\n"
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
    def _build_codex_cmd(*, codex_bin: str, prompt: str, thread_id: str | None) -> list[str]:
        if thread_id:
            return [
                codex_bin,
                "exec",
                "resume",
                "--json",
                "--skip-git-repo-check",
                thread_id,
                prompt,
            ]
        return [
            codex_bin,
            "exec",
            "--json",
            "--skip-git-repo-check",
            prompt,
        ]

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
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_value,
            env=self._launch_env(config),
            cwd=str(config.work_dir or config.project_root),
        )


def _extract_exec_json(raw_text: str) -> tuple[str, str]:
    thread_id = ""
    agent_messages: list[str] = []
    for line in raw_text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("{") or not stripped.endswith("}"):
            continue
        try:
            payload = json.loads(stripped)
        except Exception:
            continue
        if not isinstance(payload, dict):
            continue
        event_type = str(payload.get("type") or "")
        if event_type == "thread.started":
            thread = str(payload.get("thread_id") or "").strip()
            if thread:
                thread_id = thread
            continue
        if event_type != "item.completed":
            continue
        item = payload.get("item")
        if not isinstance(item, dict):
            continue
        if str(item.get("type") or "") != "agent_message":
            continue
        text = str(item.get("text") or "").strip()
        if text:
            agent_messages.append(text)
    return thread_id, "\n\n".join(agent_messages).strip()


def datetime_from_iso(value: str):
    from datetime import datetime, timezone

    parsed = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(parsed)
    except Exception:
        return datetime.now(timezone.utc)


def _parse_session_output(raw_text: str) -> tuple[str, Dict[str, object], str]:
    work_match = WORK_BLOCK_RE.search(raw_text)
    handoff_match = HANDOFF_BLOCK_RE.search(raw_text)

    if not work_match:
        return "", {}, "missing BEGIN_WORK/END_WORK block"
    if not handoff_match:
        return "", {}, "missing BEGIN_HANDOFF_JSON/END_HANDOFF_JSON block"

    work_text = work_match.group(1).strip()
    handoff_raw = handoff_match.group(1).strip()
    try:
        payload = json.loads(handoff_raw)
    except Exception as exc:  # noqa: BLE001
        return work_text, {}, f"invalid handoff json: {exc}"

    if not isinstance(payload, dict):
        return work_text, {}, "handoff payload must be JSON object"
    return work_text, payload, ""
