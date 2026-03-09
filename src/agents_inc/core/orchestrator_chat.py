from __future__ import annotations

import json
import os
import re
import select
import sys
import threading
import time
from contextlib import nullcontext
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional

try:
    import termios
    import tty
except Exception:  # pragma: no cover - platform fallback (e.g., Windows)
    termios = None  # type: ignore[assignment]
    tty = None  # type: ignore[assignment]

from agents_inc.core.codex_app_client import CodexAppClient, CodexAppServerError
from agents_inc.core.codex_home import codex_launch_env
from agents_inc.core.live_dashboard import LiveDashboard, should_enable_dashboard
from agents_inc.core.orchestrator_reply import OrchestratorReplyConfig, run_orchestrator_reply
from agents_inc.core.orchestrator_state import load_orchestrator_state, save_orchestrator_state
from agents_inc.core.progress_notes import format_progress_event
from agents_inc.core.util.fs import read_text, write_text
from agents_inc.core.util.time import now_iso

_BLOCKED_RE = re.compile(
    r"BLOCKED\[(?P<status>[^\]]+)\]\s+blocked_report=(?P<report>\S+)\s+blocked_reasons=(?P<reasons>\S+)"
)
_DOUBLE_ESC_WINDOW_SEC = 0.7
_INTERRUPT_POLL_SEC = 0.1


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


def _stdin_fd_if_tty() -> int | None:
    try:
        fd = int(sys.stdin.fileno())
    except Exception:
        return None
    if fd < 0:
        return None
    if not os.isatty(fd):
        return None
    return fd


def _watch_double_escape_interrupt(
    *,
    worker: threading.Thread,
    on_interrupt: Callable[[], None],
    chat_log_path: Path,
) -> bool:
    def _mark_interrupt(current: bool) -> bool:
        if current:
            return current
        try:
            on_interrupt()
        except Exception:
            pass
        line = "live: interrupt requested (double ESC)"
        print("agents-inc-live>", flush=True)
        print(line, flush=True)
        _append_chat_line(chat_log_path, "agents-inc-live", line)
        return True

    fd = _stdin_fd_if_tty()
    if fd is None:
        while worker.is_alive():
            try:
                worker.join(timeout=_INTERRUPT_POLL_SEC)
            except KeyboardInterrupt:
                interrupted = _mark_interrupt(False)
                while worker.is_alive():
                    try:
                        worker.join(timeout=_INTERRUPT_POLL_SEC)
                    except KeyboardInterrupt:
                        interrupted = _mark_interrupt(interrupted)
                        continue
                return interrupted
        return False

    original_attrs = None
    if termios is not None and tty is not None:
        try:
            original_attrs = termios.tcgetattr(fd)
            tty.setcbreak(fd)
        except Exception:
            original_attrs = None

    interrupted = False
    last_esc_at = 0.0
    try:
        while worker.is_alive():
            try:
                worker.join(timeout=_INTERRUPT_POLL_SEC)
            except KeyboardInterrupt:
                interrupted = _mark_interrupt(interrupted)
                continue
            if not worker.is_alive():
                break
            try:
                ready, _, _ = select.select([fd], [], [], 0.0)
            except Exception:
                continue
            if not ready:
                continue
            try:
                chunk = os.read(fd, 32)
            except Exception:
                continue
            if not chunk:
                continue
            for byte in chunk:
                if byte != 0x1B:
                    continue
                now = time.monotonic()
                if not interrupted and (now - last_esc_at) <= _DOUBLE_ESC_WINDOW_SEC:
                    interrupted = _mark_interrupt(interrupted)
                last_esc_at = now
    finally:
        if original_attrs is not None and termios is not None:
            try:
                termios.tcsetattr(fd, termios.TCSADRAIN, original_attrs)
            except Exception:
                pass
    return interrupted


def _run_interruptible_action(
    *,
    action: Callable[[], object],
    on_interrupt: Callable[[], None],
    chat_log_path: Path,
) -> tuple[object | None, BaseException | None, bool]:
    result_box: Dict[str, object] = {}
    error_box: Dict[str, BaseException] = {}

    def _worker() -> None:
        try:
            result_box["value"] = action()
        except BaseException as exc:  # noqa: BLE001
            error_box["error"] = exc

    worker = threading.Thread(target=_worker, daemon=True)
    worker.start()
    interrupted = _watch_double_escape_interrupt(
        worker=worker,
        on_interrupt=on_interrupt,
        chat_log_path=chat_log_path,
    )
    while worker.is_alive():
        try:
            worker.join(timeout=_INTERRUPT_POLL_SEC)
        except KeyboardInterrupt:
            if not interrupted:
                interrupted = True
                try:
                    on_interrupt()
                except Exception:
                    pass
                line = "live: interrupt requested (double ESC)"
                print("agents-inc-live>", flush=True)
                print(line, flush=True)
                _append_chat_line(chat_log_path, "agents-inc-live", line)
            continue
    return result_box.get("value"), error_box.get("error"), interrupted


def run_orchestrator_chat(config: OrchestratorChatConfig) -> dict:
    project_root = config.project_root.expanduser().resolve()
    chat_log_path = project_root / ".agents-inc" / "state" / "orchestrator-chat.log"

    state = load_orchestrator_state(project_root, project_id=config.project_id)
    state["prefix"] = config.orchestration_prefix
    state["chat_log_path"] = str(chat_log_path)

    def _save_state() -> None:
        nonlocal state
        state = save_orchestrator_state(project_root, state)

    def _set_pending_orchestration(
        *,
        objective: str,
        output_dir: Optional[Path],
        resume_from_cycle: int,
        resume_group_objectives: Dict[str, str] | None,
        resume_cycle_summaries: List[dict] | None,
        checkpoint_id: str = "",
    ) -> None:
        pending = {
            "objective": str(objective or "").strip(),
            "turn_dir": str(output_dir) if output_dir else "",
            "resume_from_cycle": max(0, int(resume_from_cycle or 0)),
            "group_objectives": dict(resume_group_objectives)
            if isinstance(resume_group_objectives, dict)
            else {},
            "cycle_summaries": list(resume_cycle_summaries)
            if isinstance(resume_cycle_summaries, list)
            else [],
            "checkpoint_id": str(checkpoint_id or "").strip(),
            "requested_at": now_iso(),
        }
        state["pending_orchestration"] = pending
        _save_state()

    def _mark_pending_interrupt_requested() -> None:
        pending = state.get("pending_orchestration")
        if not isinstance(pending, dict):
            return
        pending = dict(pending)
        pending["interrupt_requested_at"] = now_iso()
        state["pending_orchestration"] = pending
        _save_state()

    def _clear_pending_orchestration() -> None:
        if not isinstance(state.get("pending_orchestration"), dict):
            return
        if not state.get("pending_orchestration"):
            return
        state["pending_orchestration"] = {}
        _save_state()

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
        _save_state()
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
        _save_state()

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
        print("double-press ESC to interrupt active orchestration/direct turns")
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
            resume_checkpoint_id: str = "",
        ) -> str:
            _set_pending_orchestration(
                objective=objective,
                output_dir=output_dir,
                resume_from_cycle=resume_from_cycle,
                resume_group_objectives=resume_group_objectives,
                resume_cycle_summaries=resume_cycle_summaries,
                checkpoint_id=resume_checkpoint_id,
            )
            dashboard = None
            if should_enable_dashboard(
                "auto",
                interactive=bool(getattr(sys.stdout, "isatty", lambda: False)()),
                json_mode=False,
            ):
                dashboard = LiveDashboard()

            def _print_live_event(event: dict) -> None:
                if dashboard is not None:
                    dashboard.handle_event(event)
                line = format_progress_event(event)
                if not line:
                    return
                if dashboard is None:
                    print("agents-inc-live>", flush=True)
                    print(line, flush=True)
                _append_chat_line(chat_log_path, "agents-inc-live", line)

            abort_dir = project_root / ".agents-inc" / "state"
            abort_dir.mkdir(parents=True, exist_ok=True)
            abort_file = abort_dir / f"abort-request-{int(time.time() * 1000)}.flag"

            def _request_abort() -> None:
                if abort_file.exists():
                    return
                write_text(
                    abort_file,
                    "user interrupt requested via double ESC at {0}\n".format(now_iso()),
                )
                _mark_pending_interrupt_requested()

            def _call_orchestrator() -> object:
                return run_orchestrator_reply(
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
                        abort_file=abort_file,
                    )
                )

            try:
                with (dashboard if dashboard is not None else nullcontext()):
                    run_result, run_error, _ = _run_interruptible_action(
                        action=_call_orchestrator,
                        on_interrupt=_request_abort,
                        chat_log_path=chat_log_path,
                    )
                if run_error is not None:
                    raise run_error
                result = run_result if isinstance(run_result, dict) else {}
            except Exception as exc:  # noqa: BLE001
                blocked = _parse_blocked_error(str(exc))
                if blocked:
                    if str(blocked.get("status") or "") == "BLOCKED_ABORT_REQUESTED":
                        _clear_pending_orchestration()
                        print("agents-inc>")
                        print("interrupted: orchestration aborted by user (double ESC).")
                        _append_chat_line(
                            chat_log_path,
                            "agents-inc",
                            "interrupted: orchestration aborted by user",
                        )
                        return "interrupted"
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
                    _clear_pending_orchestration()
                    return "blocked"
                message = str(exc).strip() or "unknown orchestration error"
                print("agents-inc>")
                print(f"orchestration error: {message}")
                print("session remains active; fix and retry.")
                _append_chat_line(chat_log_path, "agents-inc-error", message)
                _clear_pending_orchestration()
                return "error"
            finally:
                if abort_file.exists():
                    try:
                        abort_file.unlink()
                    except Exception:
                        pass
            final_answer_path = Path(str(result.get("final_answer_path") or "")).expanduser()
            answer = (
                read_text(final_answer_path).strip()
                if final_answer_path.exists()
                else "orchestrator completed with no final answer artifact"
            )
            print("agents-inc>")
            print(answer)
            _append_chat_line(chat_log_path, "agents-inc", answer)
            _clear_pending_orchestration()
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
                resume_checkpoint_id=auto_checkpoint_id,
            )
            state["last_auto_resume_checkpoint_id"] = auto_checkpoint_id
            state["last_auto_resume_status"] = auto_status
            state["last_auto_resume_at"] = now_iso()
            _save_state()

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
            cancel_event = threading.Event()

            def _run_direct_turn() -> object:
                return client.run_turn(
                    thread_id=thread_id,
                    text=text,
                    cancel_event=cancel_event,
                )

            turn_result, turn_error, interrupted = _run_interruptible_action(
                action=_run_direct_turn,
                on_interrupt=cancel_event.set,
                chat_log_path=chat_log_path,
            )
            if turn_error is not None:
                message = str(turn_error).strip() or "unknown codex app-server error"
                if interrupted and "interrupted by user" in message.lower():
                    print("codex> direct turn interrupted by user; session remains active")
                    _append_chat_line(
                        chat_log_path,
                        "codex-live",
                        "direct turn interrupted by user",
                    )
                    continue
                print("codex> direct turn failed; keeping session active")
                print(f"codex> error: {message}")
                _append_chat_line(chat_log_path, "codex-error", message)
                try:
                    previous_thread = thread_id
                    thread_id = client.start_thread()
                    state["thread_id"] = thread_id
                    state["status"] = "active"
                    _save_state()
                    print(f"codex> resumed on a fresh thread: {thread_id}")
                    if previous_thread and previous_thread != thread_id:
                        print(f"codex> previous thread was: {previous_thread}")
                    print("codex> please resend your message.")
                except CodexAppServerError as recovery_exc:
                    recovery = str(recovery_exc).strip() or "failed to start recovery thread"
                    print(f"codex> recovery failed: {recovery}")
                    _append_chat_line(chat_log_path, "codex-error", f"recovery failed: {recovery}")
                continue
            turn = turn_result
            if turn is None:
                print("codex> direct turn failed; keeping session active")
                _append_chat_line(chat_log_path, "codex-error", "direct turn missing result payload")
                continue
            answer = str(getattr(turn, "text", "")).strip() or "(empty response)"
            print("codex>")
            print(answer)
            _append_chat_line(chat_log_path, "codex", answer)
            state["last_turn_id"] = str(getattr(turn, "turn_id", ""))
            _save_state()
        return summary
    finally:
        state = load_orchestrator_state(project_root, project_id=config.project_id)
        state["status"] = "inactive"
        save_orchestrator_state(project_root, state)
        client.close()
