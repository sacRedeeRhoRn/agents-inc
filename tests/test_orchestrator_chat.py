#!/usr/bin/env python3
from __future__ import annotations

import io
import sys
import tempfile
import time
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from agents_inc.core.codex_app_client import CodexAppServerError, TurnResult  # noqa: E402
from agents_inc.core.fabric_lib import FabricError  # noqa: E402
from agents_inc.core.orchestrator_chat import (  # noqa: E402
    OrchestratorChatConfig,
    _watch_double_escape_interrupt,
    run_orchestrator_chat,
)
from agents_inc.core.orchestrator_state import load_orchestrator_state  # noqa: E402


class _SuccessClient:
    def __init__(self, *, cwd: Path, env: dict) -> None:  # noqa: ARG002
        self.cwd = cwd

    def start(self) -> None:
        return None

    def close(self) -> None:
        return None

    def start_thread(self) -> str:
        return "thread-1"

    def resume_thread(self, thread_id: str) -> str:
        return thread_id

    def run_turn(
        self,
        *,
        thread_id: str,
        text: str,
        timeout_sec: float = 300.0,  # noqa: ARG002
        cancel_event=None,  # noqa: ANN001,ARG002
    ) -> TurnResult:
        return TurnResult(thread_id=thread_id, turn_id="turn-1", text=f"echo: {text}")


class _RecoveringClient:
    def __init__(self, *, cwd: Path, env: dict) -> None:  # noqa: ARG002
        self.cwd = cwd
        self._thread_counter = 0
        self._run_calls = 0

    def start(self) -> None:
        return None

    def close(self) -> None:
        return None

    def start_thread(self) -> str:
        self._thread_counter += 1
        return f"thread-{self._thread_counter}"

    def resume_thread(self, thread_id: str) -> str:
        return thread_id

    def run_turn(
        self,
        *,
        thread_id: str,
        text: str,
        timeout_sec: float = 300.0,  # noqa: ARG002
        cancel_event=None,  # noqa: ANN001,ARG002
    ) -> TurnResult:
        self._run_calls += 1
        if self._run_calls == 1:
            raise CodexAppServerError("simulated direct-turn failure")
        return TurnResult(thread_id=thread_id, turn_id="turn-2", text=f"recovered: {text}")


class _SyncTimeoutClient:
    def __init__(self, *, cwd: Path, env: dict) -> None:  # noqa: ARG002
        self.cwd = cwd

    def start(self) -> None:
        return None

    def close(self) -> None:
        return None

    def start_thread(self) -> str:
        return "thread-1"

    def resume_thread(self, thread_id: str) -> str:
        return thread_id

    def run_turn(
        self,
        *,
        thread_id: str,
        text: str,
        timeout_sec: float = 300.0,  # noqa: ARG002
        cancel_event=None,  # noqa: ANN001,ARG002
    ) -> TurnResult:
        if text.startswith(
            "The following response was produced via /agents-inc orchestration."
        ):
            raise CodexAppServerError("turn timed out after 5s")
        return TurnResult(thread_id=thread_id, turn_id="turn-3", text=f"echo: {text}")


class _InterruptibleDirectClient:
    def __init__(self, *, cwd: Path, env: dict) -> None:  # noqa: ARG002
        self.cwd = cwd

    def start(self) -> None:
        return None

    def close(self) -> None:
        return None

    def start_thread(self) -> str:
        return "thread-1"

    def resume_thread(self, thread_id: str) -> str:
        return thread_id

    def run_turn(
        self,
        *,
        thread_id: str,
        text: str,
        timeout_sec: float = 300.0,  # noqa: ARG002
        cancel_event=None,  # noqa: ANN001
    ) -> TurnResult:
        if text.startswith("The following response was produced via /agents-inc orchestration."):
            return TurnResult(thread_id=thread_id, turn_id="turn-sync", text="synced")
        deadline = time.time() + 1.0
        while time.time() < deadline:
            if cancel_event is not None and cancel_event.is_set():
                raise CodexAppServerError("turn interrupted by user")
            time.sleep(0.01)
        return TurnResult(thread_id=thread_id, turn_id="turn-long", text="late answer")


class OrchestratorChatTests(unittest.TestCase):
    def test_double_esc_watch_treats_keyboard_interrupt_as_abort_request(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            chat_log_path = Path(td) / "chat.log"
            interrupt_calls = {"count": 0}

            class _FakeWorker:
                def __init__(self) -> None:
                    self.calls = 0

                def is_alive(self) -> bool:
                    return self.calls < 2

                def join(self, timeout=None) -> None:  # noqa: ARG002
                    self.calls += 1
                    if self.calls == 1:
                        raise KeyboardInterrupt()

            def _on_interrupt() -> None:
                interrupt_calls["count"] += 1

            with patch("agents_inc.core.orchestrator_chat._stdin_fd_if_tty", return_value=None):
                interrupted = _watch_double_escape_interrupt(
                    worker=_FakeWorker(),
                    on_interrupt=_on_interrupt,
                    chat_log_path=chat_log_path,
                )

            self.assertTrue(interrupted)
            self.assertEqual(interrupt_calls["count"], 1)
            self.assertIn("interrupt requested", chat_log_path.read_text(encoding="utf-8"))

    def test_direct_turn_prints_live_prefix_and_reply(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            project_root = Path(td) / "proj-chat"
            project_root.mkdir(parents=True, exist_ok=True)
            out = io.StringIO()
            with redirect_stdout(out):
                with patch("agents_inc.core.orchestrator_chat.CodexAppClient", _SuccessClient):
                    with patch("builtins.input", side_effect=["hello codex", "/quit"]):
                        summary = run_orchestrator_chat(
                            OrchestratorChatConfig(
                                fabric_root=project_root / "agent_group_fabric",
                                project_root=project_root,
                                project_id="proj-chat",
                            )
                        )
            self.assertEqual(summary["thread_id"], "thread-1")
            text = out.getvalue()
            self.assertIn("codex-live> processing direct turn...", text)
            self.assertIn("codex>", text)
            self.assertIn("echo: hello codex", text)
            state = load_orchestrator_state(project_root, project_id="proj-chat")
            self.assertEqual(state.get("last_turn_id"), "turn-1")

    def test_direct_turn_failure_recovers_with_new_thread(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            project_root = Path(td) / "proj-recover"
            project_root.mkdir(parents=True, exist_ok=True)
            out = io.StringIO()
            with redirect_stdout(out):
                with patch("agents_inc.core.orchestrator_chat.CodexAppClient", _RecoveringClient):
                    with patch(
                        "builtins.input",
                        side_effect=["first message", "second message", "/quit"],
                    ):
                        summary = run_orchestrator_chat(
                            OrchestratorChatConfig(
                                fabric_root=project_root / "agent_group_fabric",
                                project_root=project_root,
                                project_id="proj-recover",
                            )
                        )
            self.assertEqual(summary["thread_id"], "thread-1")
            output = out.getvalue()
            self.assertIn("direct turn failed; keeping session active", output)
            self.assertIn("resumed on a fresh thread: thread-2", output)
            self.assertIn("please resend your message.", output)
            self.assertIn("recovered: second message", output)
            state = load_orchestrator_state(project_root, project_id="proj-recover")
            self.assertEqual(state.get("thread_id"), "thread-2")
            self.assertEqual(state.get("last_turn_id"), "turn-2")

    def test_orchestration_blocked_keeps_chat_active(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            project_root = Path(td) / "proj-blocked"
            project_root.mkdir(parents=True, exist_ok=True)
            turn_dir = project_root / ".agents-inc" / "turns" / "turn-test"
            turn_dir.mkdir(parents=True, exist_ok=True)
            blocked_reasons = turn_dir / "blocked-reasons.json"
            blocked_report = turn_dir / "blocked-report.md"
            blocked_reasons.write_text(
                (
                    '{"reasons":["group developer contribution invalid",'
                    '"group literature-intelligence contribution invalid"]}\n'
                ),
                encoding="utf-8",
            )
            blocked_report.write_text("# blocked report\n", encoding="utf-8")
            final_answer = turn_dir / "final-exposed-answer.md"
            final_answer.write_text("final answer text\n", encoding="utf-8")

            call_count = {"n": 0}

            def _fake_orchestrator(config):  # type: ignore[no-untyped-def]
                call_count["n"] += 1
                if call_count["n"] == 1:
                    raise FabricError(
                        "BLOCKED[BLOCKED_LAYERED_RUNTIME] blocked_report={0} blocked_reasons={1}".format(
                            blocked_report,
                            blocked_reasons,
                        )
                    )
                return {"final_answer_path": str(final_answer)}

            out = io.StringIO()
            with redirect_stdout(out):
                with patch("agents_inc.core.orchestrator_chat.CodexAppClient", _SuccessClient):
                    with patch(
                        "agents_inc.core.orchestrator_chat.run_orchestrator_reply",
                        side_effect=_fake_orchestrator,
                    ):
                        with patch(
                            "builtins.input",
                            side_effect=["/agents-inc first objective", "/agents-inc second objective", "/quit"],
                        ):
                            run_orchestrator_chat(
                                OrchestratorChatConfig(
                                    fabric_root=project_root / "agent_group_fabric",
                                    project_root=project_root,
                                    project_id="proj-blocked",
                                )
                            )
            text = out.getvalue()
            self.assertIn("blocked: BLOCKED_LAYERED_RUNTIME", text)
            self.assertIn("top blockers:", text)
            self.assertIn("group developer contribution invalid", text)
            self.assertIn("session remains active", text)
            self.assertIn("final answer text", text)

    def test_auto_restart_runs_before_user_input(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            project_root = Path(td) / "proj-auto-resume"
            project_root.mkdir(parents=True, exist_ok=True)
            turn_dir = project_root / ".agents-inc" / "turns" / "turn-auto"
            turn_dir.mkdir(parents=True, exist_ok=True)
            final_answer = turn_dir / "final-exposed-answer.md"
            final_answer.write_text("auto resume answer\n", encoding="utf-8")

            captured = {"calls": []}

            def _fake_orchestrator(config):  # type: ignore[no-untyped-def]
                captured["calls"].append(config)
                return {"final_answer_path": str(final_answer)}

            out = io.StringIO()
            with redirect_stdout(out):
                with patch("agents_inc.core.orchestrator_chat.CodexAppClient", _SuccessClient):
                    with patch(
                        "agents_inc.core.orchestrator_chat.run_orchestrator_reply",
                        side_effect=_fake_orchestrator,
                    ):
                        with patch("builtins.input", side_effect=["/quit"]):
                            run_orchestrator_chat(
                                OrchestratorChatConfig(
                                    fabric_root=project_root / "agent_group_fabric",
                                    project_root=project_root,
                                    project_id="proj-auto-resume",
                                    auto_restart_checkpoint_id="cp-000001",
                                    auto_restart_objective="resume objective",
                                    auto_restart_turn_dir=str(turn_dir),
                                    auto_restart_from_cycle=4,
                                    auto_restart_group_objectives={
                                        "developer": "resume developer objective"
                                    },
                                    auto_restart_cycle_summaries=[{"cycle_id": 1}, {"cycle_id": 2}],
                                )
                            )
            text = out.getvalue()
            self.assertIn("live: auto-resume from checkpoint=cp-000001", text)
            self.assertIn("auto resume answer", text)
            self.assertEqual(len(captured["calls"]), 1)
            config = captured["calls"][0]
            self.assertEqual(config.message, "resume objective")
            self.assertEqual(int(config.resume_from_cycle), 4)
            self.assertEqual(Path(str(config.output_dir)).resolve(), turn_dir.resolve())
            state = load_orchestrator_state(project_root, project_id="proj-auto-resume")
            self.assertEqual(state.get("last_auto_resume_checkpoint_id"), "cp-000001")
            self.assertEqual(state.get("last_auto_resume_status"), "completed")

    def test_auto_restart_blocked_then_manual_retry_succeeds(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            project_root = Path(td) / "proj-auto-resume-blocked"
            project_root.mkdir(parents=True, exist_ok=True)
            turn_dir = project_root / ".agents-inc" / "turns" / "turn-auto-blocked"
            turn_dir.mkdir(parents=True, exist_ok=True)
            blocked_reasons = turn_dir / "blocked-reasons.json"
            blocked_report = turn_dir / "blocked-report.md"
            blocked_reasons.write_text('{"reasons":["auto resume blocked"]}\n', encoding="utf-8")
            blocked_report.write_text("# blocked report\n", encoding="utf-8")
            final_answer = turn_dir / "final-exposed-answer.md"
            final_answer.write_text("manual retry answer\n", encoding="utf-8")

            call_count = {"n": 0}

            def _fake_orchestrator(config):  # type: ignore[no-untyped-def]
                call_count["n"] += 1
                if call_count["n"] == 1:
                    raise FabricError(
                        "BLOCKED[BLOCKED_LAYERED_RUNTIME] blocked_report={0} blocked_reasons={1}".format(
                            blocked_report,
                            blocked_reasons,
                        )
                    )
                return {"final_answer_path": str(final_answer)}

            out = io.StringIO()
            with redirect_stdout(out):
                with patch("agents_inc.core.orchestrator_chat.CodexAppClient", _SuccessClient):
                    with patch(
                        "agents_inc.core.orchestrator_chat.run_orchestrator_reply",
                        side_effect=_fake_orchestrator,
                    ):
                        with patch(
                            "builtins.input",
                            side_effect=["/agents-inc manual retry objective", "/quit"],
                        ):
                            run_orchestrator_chat(
                                OrchestratorChatConfig(
                                    fabric_root=project_root / "agent_group_fabric",
                                    project_root=project_root,
                                    project_id="proj-auto-resume-blocked",
                                    auto_restart_checkpoint_id="cp-000002",
                                    auto_restart_objective="auto blocked objective",
                                    auto_restart_turn_dir=str(turn_dir),
                                )
                            )
            text = out.getvalue()
            self.assertIn("blocked: BLOCKED_LAYERED_RUNTIME", text)
            self.assertIn("manual retry answer", text)
            self.assertEqual(call_count["n"], 2)
            state = load_orchestrator_state(project_root, project_id="proj-auto-resume-blocked")
            self.assertEqual(state.get("last_auto_resume_checkpoint_id"), "cp-000002")
            self.assertEqual(state.get("last_auto_resume_status"), "blocked")

    def test_orchestration_reply_returns_prompt_even_if_sync_times_out(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            project_root = Path(td) / "proj-sync-timeout"
            project_root.mkdir(parents=True, exist_ok=True)
            turn_dir = project_root / ".agents-inc" / "turns" / "turn-sync-timeout"
            turn_dir.mkdir(parents=True, exist_ok=True)
            final_answer = turn_dir / "final-exposed-answer.md"
            final_answer.write_text("orchestrated answer\n", encoding="utf-8")

            def _fake_orchestrator(config):  # type: ignore[no-untyped-def]
                return {"final_answer_path": str(final_answer)}

            out = io.StringIO()
            with redirect_stdout(out):
                with patch("agents_inc.core.orchestrator_chat.CodexAppClient", _SyncTimeoutClient):
                    with patch(
                        "agents_inc.core.orchestrator_chat.run_orchestrator_reply",
                        side_effect=_fake_orchestrator,
                    ):
                        with patch(
                            "builtins.input",
                            side_effect=[
                                "/agents-inc generate result",
                                "continue in direct chat",
                                "/quit",
                            ],
                        ):
                            run_orchestrator_chat(
                                OrchestratorChatConfig(
                                    fabric_root=project_root / "agent_group_fabric",
                                    project_root=project_root,
                                    project_id="proj-sync-timeout",
                                )
                            )
            text = out.getvalue()
            self.assertIn("orchestrated answer", text)
            self.assertIn("codex-live> processing direct turn...", text)
            self.assertIn("echo: continue in direct chat", text)

    def test_double_esc_interrupts_orchestration_and_keeps_chat_alive(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            project_root = Path(td) / "proj-esc-orchestration"
            project_root.mkdir(parents=True, exist_ok=True)
            turn_dir = project_root / ".agents-inc" / "turns" / "turn-esc-orchestration"
            turn_dir.mkdir(parents=True, exist_ok=True)
            blocked_reasons = turn_dir / "blocked-reasons.json"
            blocked_report = turn_dir / "blocked-report.md"
            blocked_reasons.write_text('{"reasons":["abort file detected"]}\n', encoding="utf-8")
            blocked_report.write_text("# blocked report\n", encoding="utf-8")

            def _fake_orchestrator(config):  # type: ignore[no-untyped-def]
                abort_file = Path(str(config.abort_file or ""))
                deadline = time.time() + 1.0
                while time.time() < deadline and not abort_file.exists():
                    time.sleep(0.01)
                raise FabricError(
                    "BLOCKED[BLOCKED_ABORT_REQUESTED] blocked_report={0} blocked_reasons={1}".format(
                        blocked_report,
                        blocked_reasons,
                    )
                )

            def _fake_watch(**kwargs):  # type: ignore[no-untyped-def]
                on_interrupt = kwargs["on_interrupt"]
                worker = kwargs["worker"]
                on_interrupt()
                worker.join(timeout=1.0)
                return True

            out = io.StringIO()
            with redirect_stdout(out):
                with patch("agents_inc.core.orchestrator_chat.CodexAppClient", _SuccessClient):
                    with patch(
                        "agents_inc.core.orchestrator_chat.run_orchestrator_reply",
                        side_effect=_fake_orchestrator,
                    ):
                        with patch(
                            "agents_inc.core.orchestrator_chat._watch_double_escape_interrupt",
                            side_effect=_fake_watch,
                        ):
                            with patch(
                                "builtins.input",
                                side_effect=[
                                    "/agents-inc long orchestration",
                                    "still alive",
                                    "/quit",
                                ],
                            ):
                                run_orchestrator_chat(
                                    OrchestratorChatConfig(
                                        fabric_root=project_root / "agent_group_fabric",
                                        project_root=project_root,
                                        project_id="proj-esc-orchestration",
                                    )
                                )
            text = out.getvalue()
            self.assertIn("interrupted: orchestration aborted by user", text)
            self.assertIn("echo: still alive", text)

    def test_double_esc_interrupts_direct_turn_and_keeps_session_active(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            project_root = Path(td) / "proj-esc-direct"
            project_root.mkdir(parents=True, exist_ok=True)

            def _fake_watch(**kwargs):  # type: ignore[no-untyped-def]
                on_interrupt = kwargs["on_interrupt"]
                worker = kwargs["worker"]
                on_interrupt()
                worker.join(timeout=1.0)
                return True

            out = io.StringIO()
            with redirect_stdout(out):
                with patch(
                    "agents_inc.core.orchestrator_chat.CodexAppClient",
                    _InterruptibleDirectClient,
                ):
                    with patch(
                        "agents_inc.core.orchestrator_chat._watch_double_escape_interrupt",
                        side_effect=_fake_watch,
                    ):
                        with patch(
                            "builtins.input",
                            side_effect=["long direct turn", "/quit"],
                        ):
                            run_orchestrator_chat(
                                OrchestratorChatConfig(
                                    fabric_root=project_root / "agent_group_fabric",
                                    project_root=project_root,
                                    project_id="proj-esc-direct",
                                )
                            )
            text = out.getvalue()
            self.assertIn("direct turn interrupted by user; session remains active", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
