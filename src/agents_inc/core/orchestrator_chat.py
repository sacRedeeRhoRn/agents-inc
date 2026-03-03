from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from agents_inc.core.codex_app_client import CodexAppClient, CodexAppServerError
from agents_inc.core.codex_home import codex_launch_env
from agents_inc.core.orchestrator_reply import OrchestratorReplyConfig, run_orchestrator_reply
from agents_inc.core.orchestrator_state import load_orchestrator_state, save_orchestrator_state
from agents_inc.core.progress_notes import format_progress_event
from agents_inc.core.util.fs import read_text, write_text
from agents_inc.core.util.time import now_iso


@dataclass
class OrchestratorChatConfig:
    fabric_root: Path
    project_root: Path
    project_id: str
    orchestration_prefix: str = "/agents-inc"
    resume_thread_id: str = ""
    no_launch: bool = False
    sync_orchestrated_to_direct_thread: bool = True


def _append_chat_line(path: Path, speaker: str, text: str) -> None:
    line = f"{now_iso()} {speaker}: {text.rstrip()}\n"
    previous = ""
    if path.exists():
        previous = path.read_text(encoding="utf-8")
    write_text(path, previous + line)


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

                def _print_live_event(event: dict) -> None:
                    line = format_progress_event(event)
                    if not line:
                        return
                    print("agents-inc-live>")
                    print(line)
                    _append_chat_line(chat_log_path, "agents-inc-live", line)

                result = run_orchestrator_reply(
                    OrchestratorReplyConfig(
                        fabric_root=config.fabric_root,
                        project_id=config.project_id,
                        message=objective,
                        group="",
                        progress_callback=_print_live_event,
                    )
                )
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
                    try:
                        client.run_turn(thread_id=thread_id, text=sync_note, timeout_sec=180.0)
                    except CodexAppServerError:
                        # Non-fatal: orchestration output is still preserved in artifacts/log.
                        pass
                continue

            turn = client.run_turn(thread_id=thread_id, text=text)
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
