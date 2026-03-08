from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from agents_inc.core.codex_app_client import CodexAppClient, CodexAppServerError
from agents_inc.core.codex_home import codex_launch_env
from agents_inc.core.orchestrator_reply import OrchestratorReplyConfig, run_orchestrator_reply
from agents_inc.core.orchestrator_state import load_orchestrator_state, save_orchestrator_state
from agents_inc.core.progress_notes import format_progress_event
from agents_inc.core.util.fs import read_text, write_text
from agents_inc.core.util.time import now_iso

_BLOCKED_RE = re.compile(
    r"BLOCKED\[(?P<status>[^\]]+)\]\s+blocked_report=(?P<report>\S+)\s+blocked_reasons=(?P<reasons>\S+)"
)


@dataclass
class OrchestratorChatConfig:
    fabric_root: Path
    project_root: Path
    project_id: str
    orchestration_prefix: str = "/agents-inc"
    resume_thread_id: str = ""
    no_launch: bool = False
    sync_orchestrated_to_direct_thread: bool = True
    sync_context_timeout_sec: float = 5.0
    project_index_path: Path | None = None
    auto_restart_checkpoint_id: str = ""
    auto_restart_objective: str = ""
    auto_restart_turn_dir: str = ""
    auto_restart_from_cycle: int = 0
    auto_restart_group_objectives: Dict[str, str] | None = None
    auto_restart_cycle_summaries: List[dict] | None = None


def _append_chat_line(path: Path, speaker: str, text: str) -> None:
    line = f"{now_iso()} {speaker}: {text.rstrip()}\n"
    previous = ""
    if path.exists():
        previous = path.read_text(encoding="utf-8")
    write_text(path, previous + line)


def _parse_blocked_error(text: str) -> dict | None:
    match = _BLOCKED_RE.search(str(text))
    if not match:
        return None
    return {
        "status": str(match.group("status") or "").strip(),
        "blocked_report": str(match.group("report") or "").strip(),
        "blocked_reasons": str(match.group("reasons") or "").strip(),
    }


def _load_blocked_reasons(path: str, *, limit: int = 6) -> List[str]:
    p = Path(str(path or "").strip()).expanduser()
    if not p.exists():
        return []
    try:
        payload = json.loads(p.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return []
    if not isinstance(payload, dict):
        return []
    rows = payload.get("reasons", [])
    if not isinstance(rows, list):
        return []
    out: List[str] = []
    for item in rows:
        reason = str(item or "").strip()
        if reason:
            out.append(reason)
        if len(out) >= limit:
            break
    return out


def _normalize_resume_objectives(value: Dict[str, str] | None) -> Dict[str, str] | None:
    if not isinstance(value, dict):
        return None
    out: Dict[str, str] = {}
    for raw_key, raw_value in value.items():
        key = str(raw_key or "").strip()
        text = str(raw_value or "")
        if not key or not text.strip():
            continue
        out[key] = text
    return out or None


def _normalize_resume_cycle_summaries(value: List[dict] | None) -> List[dict] | None:
    if not isinstance(value, list):
        return None
    out: List[dict] = []
    for item in value:
        if isinstance(item, dict):
            out.append(dict(item))
    return out or None


def run_orchestrator_chat(config: OrchestratorChatConfig) -> dict:
    project_root = config.project_root.expanduser().resolve()
    chat_log_path = project_root / ".agents-inc" / "state" / "orchestrator-chat.log"

    state = load_orchestrator_state(project_root, project_id=config.project_id)
    state["prefix"] = config.orchestration_prefix
    state["chat_log_path"] = str(chat_log_path)

    thread_id = ""
    fallback_from_thread = ""
    if config.no_launch:
        existing_thread = str(state.get("thread_id") or "").strip()
        if config.resume_thread_id:
            thread_id = str(config.resume_thread_id).strip()
            if existing_thread and existing_thread != thread_id:
                fallback_from_thread = existing_thread
        else:
            thread_id = existing_thread
        state["thread_id"] = thread_id
        state["status"] = "inactive"
        save_orchestrator_state(project_root, state)
        return {
            "project_id": config.project_id,
            "project_root": str(project_root),
            "thread_id": thread_id,
            "fallback_from_thread": fallback_from_thread,
            "prefix": config.orchestration_prefix,
            "chat_log_path": str(chat_log_path),
        }

    client = CodexAppClient(cwd=project_root, env=codex_launch_env(project_root))
    try:
        client.start()
        if config.resume_thread_id:
            try:
                thread_id = client.resume_thread(config.resume_thread_id)
            except CodexAppServerError:
                fallback_from_thread = config.resume_thread_id
                thread_id = client.start_thread()
        else:
            existing_thread = str(state.get("thread_id") or "").strip()
            if existing_thread:
                try:
                    thread_id = client.resume_thread(existing_thread)
                except CodexAppServerError:
                    fallback_from_thread = existing_thread
                    thread_id = client.start_thread()
            else:
                thread_id = client.start_thread()

        state["thread_id"] = thread_id
        state["status"] = "active"
        save_orchestrator_state(project_root, state)

        summary = {
            "project_id": config.project_id,
            "project_root": str(project_root),
            "thread_id": thread_id,
            "fallback_from_thread": fallback_from_thread,
            "prefix": config.orchestration_prefix,
            "chat_log_path": str(chat_log_path),
        }
        print(f"managed orchestrator chat started for project '{config.project_id}'")
        print(f"thread_id: {thread_id}")
        print(f"prefix for orchestration: {config.orchestration_prefix}")
        print("type '/quit' to exit")
        pending_sync_notes: List[str] = []

        def _flush_pending_sync_notes() -> None:
            if not config.sync_orchestrated_to_direct_thread:
                pending_sync_notes.clear()
                return
            while pending_sync_notes:
                note = pending_sync_notes.pop(0)
                try:
                    timeout_sec = max(0.1, float(config.sync_context_timeout_sec or 0.0))
                except Exception:
                    timeout_sec = 5.0
                try:
                    client.run_turn(
                        thread_id=thread_id,
                        text=note,
                        timeout_sec=timeout_sec,
                    )
                except CodexAppServerError as exc:
                    message = str(exc).strip() or "sync-to-direct-thread failed"
                    _append_chat_line(chat_log_path, "codex-sync-error", message)
                    continue

        def _run_orchestrated_objective(
            objective: str,
            *,
            output_dir: Optional[Path] = None,
            resume_from_cycle: int = 0,
            resume_group_objectives: Dict[str, str] | None = None,
            resume_cycle_summaries: List[dict] | None = None,
        ) -> str:
            def _print_live_event(event: dict) -> None:
                line = format_progress_event(event)
                if not line:
                    return
                print("agents-inc-live>", flush=True)
                print(line, flush=True)
                _append_chat_line(chat_log_path, "agents-inc-live", line)

            try:
                result = run_orchestrator_reply(
                    OrchestratorReplyConfig(
                        fabric_root=config.fabric_root,
                        project_id=config.project_id,
                        message=objective,
                        group="",
                        output_dir=output_dir,
                        progress_callback=_print_live_event,
                        project_index_path=config.project_index_path,
                        resume_from_cycle=max(0, int(resume_from_cycle or 0)),
                        resume_group_objectives=resume_group_objectives,
                        resume_previous_cycle_summaries=resume_cycle_summaries,
                    )
                )
            except Exception as exc:  # noqa: BLE001
                blocked = _parse_blocked_error(str(exc))
                if blocked:
                    print("agents-inc>")
                    print(f"blocked: {blocked['status']}")
                    top_reasons = _load_blocked_reasons(blocked.get("blocked_reasons", ""))
                    if top_reasons:
                        print("top blockers:")
                        for row in top_reasons:
                            print(f"- {row}")
                    print(f"blocked report: {blocked['blocked_report']}")
                    print("session remains active; adjust objective/constraints and retry.")
                    _append_chat_line(
                        chat_log_path,
                        "agents-inc",
                        "blocked: {0} | report: {1}".format(
                            blocked["status"], blocked["blocked_report"]
                        ),
                    )
                    return "blocked"
                message = str(exc).strip() or "unknown orchestration error"
                print("agents-inc>")
                print(f"orchestration error: {message}")
                print("session remains active; fix and retry.")
                _append_chat_line(chat_log_path, "agents-inc-error", message)
                return "error"
            final_answer_path = Path(str(result.get("final_answer_path") or "")).expanduser()
            answer = (
                read_text(final_answer_path).strip()
                if final_answer_path.exists()
                else "orchestrator completed with no final answer artifact"
            )
            print("agents-inc>")
            print(answer)
            _append_chat_line(chat_log_path, "agents-inc", answer)
            if config.sync_orchestrated_to_direct_thread:
                sync_note = (
                    "The following response was produced via /agents-inc orchestration. "
                    "Keep this as project context.\n\n"
                    f"{answer}"
                )
                pending_sync_notes.append(sync_note)
            return "completed"

        auto_checkpoint_id = str(config.auto_restart_checkpoint_id or "").strip()
        auto_objective = str(config.auto_restart_objective or "").strip()
        if auto_checkpoint_id and auto_objective:
            auto_turn_dir = str(config.auto_restart_turn_dir or "").strip()
            auto_output_dir = (
                Path(auto_turn_dir).expanduser().resolve() if auto_turn_dir else None
            )
            resume_objectives = _normalize_resume_objectives(config.auto_restart_group_objectives)
            resume_cycle_summaries = _normalize_resume_cycle_summaries(
                config.auto_restart_cycle_summaries
            )
            start_cycle = max(0, int(config.auto_restart_from_cycle or 0))
            auto_line = (
                "live: auto-resume from checkpoint={0} | restart_cycle={1}".format(
                    auto_checkpoint_id,
                    start_cycle + 1,
                )
            )
            print("agents-inc-live>", flush=True)
            print(auto_line, flush=True)
            _append_chat_line(chat_log_path, "agents-inc-live", auto_line)
            auto_status = _run_orchestrated_objective(
                auto_objective,
                output_dir=auto_output_dir,
                resume_from_cycle=start_cycle,
                resume_group_objectives=resume_objectives,
                resume_cycle_summaries=resume_cycle_summaries,
            )
            state["last_auto_resume_checkpoint_id"] = auto_checkpoint_id
            state["last_auto_resume_status"] = auto_status
            state["last_auto_resume_at"] = now_iso()
            save_orchestrator_state(project_root, state)

        while True:
            try:
                raw = input("you> ")
            except EOFError:
                break
            text = str(raw or "").strip()
            if not text:
                continue
            if text in {"/quit", "/exit"}:
                break
            _append_chat_line(chat_log_path, "user", text)
            if text.startswith(config.orchestration_prefix):
                objective = text[len(config.orchestration_prefix) :].strip()
                if not objective:
                    print("agents-inc> provide a request after the orchestration prefix")
                    continue
                _run_orchestrated_objective(objective)
                continue

            _flush_pending_sync_notes()
            print("codex-live> processing direct turn...", flush=True)
            _append_chat_line(chat_log_path, "codex-live", "processing direct turn")
            try:
                turn = client.run_turn(thread_id=thread_id, text=text)
            except CodexAppServerError as exc:
                message = str(exc).strip() or "unknown codex app-server error"
                print("codex> direct turn failed; keeping session active")
                print(f"codex> error: {message}")
                _append_chat_line(chat_log_path, "codex-error", message)
                try:
                    previous_thread = thread_id
                    thread_id = client.start_thread()
                    state["thread_id"] = thread_id
                    state["status"] = "active"
                    save_orchestrator_state(project_root, state)
                    print(f"codex> resumed on a fresh thread: {thread_id}")
                    if previous_thread and previous_thread != thread_id:
                        print(f"codex> previous thread was: {previous_thread}")
                    print("codex> please resend your message.")
                except CodexAppServerError as recovery_exc:
                    recovery = str(recovery_exc).strip() or "failed to start recovery thread"
                    print(f"codex> recovery failed: {recovery}")
                    _append_chat_line(chat_log_path, "codex-error", f"recovery failed: {recovery}")
                continue
            answer = turn.text.strip() or "(empty response)"
            print("codex>")
            print(answer)
            _append_chat_line(chat_log_path, "codex", answer)
            state["last_turn_id"] = turn.turn_id
            save_orchestrator_state(project_root, state)
        return summary
    finally:
        state = load_orchestrator_state(project_root, project_id=config.project_id)
        state["status"] = "inactive"
        save_orchestrator_state(project_root, state)
        client.close()
