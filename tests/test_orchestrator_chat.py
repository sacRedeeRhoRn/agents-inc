#!/usr/bin/env python3
from __future__ import annotations

import io
import sys
import tempfile
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

    def run_turn(self, *, thread_id: str, text: str, timeout_sec: float = 300.0) -> TurnResult:  # noqa: ARG002
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

    def run_turn(self, *, thread_id: str, text: str, timeout_sec: float = 300.0) -> TurnResult:  # noqa: ARG002
        self._run_calls += 1
        if self._run_calls == 1:
            raise CodexAppServerError("simulated direct-turn failure")
        return TurnResult(thread_id=thread_id, turn_id="turn-2", text=f"recovered: {text}")


class OrchestratorChatTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main(verbosity=2)
