#!/usr/bin/env python3
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from agents_inc.cli import orchestrator_reply as orchestrator_reply_cli  # noqa: E402


class CLIOrchestratorReplyTests(unittest.TestCase):
    def test_runtime_timeout_defaults_to_unlimited(self) -> None:
        args = SimpleNamespace(
            live_profile="bounded",
            max_parallel=None,
            retry_attempts=None,
            retry_backoff_sec=None,
            agent_timeout_sec=None,
            max_cycles=None,
            heartbeat_sec=None,
        )
        runtime = orchestrator_reply_cli._resolve_runtime_settings(args)
        self.assertEqual(runtime["agent_timeout_sec"], 0)

    def test_runtime_timeout_zero_means_unlimited(self) -> None:
        args = SimpleNamespace(
            live_profile="custom",
            max_parallel=None,
            retry_attempts=None,
            retry_backoff_sec=None,
            agent_timeout_sec=0,
            max_cycles=None,
            heartbeat_sec=None,
        )
        runtime = orchestrator_reply_cli._resolve_runtime_settings(args)
        self.assertEqual(runtime["agent_timeout_sec"], 0)

    def test_runtime_timeout_positive_is_preserved(self) -> None:
        args = SimpleNamespace(
            live_profile="custom",
            max_parallel=None,
            retry_attempts=None,
            retry_backoff_sec=None,
            agent_timeout_sec=123,
            max_cycles=None,
            heartbeat_sec=None,
        )
        runtime = orchestrator_reply_cli._resolve_runtime_settings(args)
        self.assertEqual(runtime["agent_timeout_sec"], 123)

    def test_group_mode_rejects_no_meeting(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            fake_root = Path(td)
            with patch(
                "agents_inc.cli.orchestrator_reply._resolve_project_fabric_root",
                return_value=fake_root,
            ):
                with patch("agents_inc.cli.orchestrator_reply.ensure_fabric_root_initialized"):
                    with patch(
                        "agents_inc.cli.orchestrator_reply.run_orchestrator_reply"
                    ) as runner:
                        with patch.object(
                            sys,
                            "argv",
                            [
                                "agents-inc",
                                "--project-id",
                                "proj-a",
                                "--message",
                                "normal group objective",
                                "--no-meeting",
                            ],
                        ):
                            code = orchestrator_reply_cli.main()
            self.assertEqual(code, 1)
            runner.assert_not_called()

    def test_group_mode_rejects_max_cycles_lt_2(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            fake_root = Path(td)
            with patch(
                "agents_inc.cli.orchestrator_reply._resolve_project_fabric_root",
                return_value=fake_root,
            ):
                with patch("agents_inc.cli.orchestrator_reply.ensure_fabric_root_initialized"):
                    with patch(
                        "agents_inc.cli.orchestrator_reply.run_orchestrator_reply"
                    ) as runner:
                        with patch.object(
                            sys,
                            "argv",
                            [
                                "agents-inc",
                                "--project-id",
                                "proj-a",
                                "--message",
                                "normal group objective",
                                "--max-cycles",
                                "1",
                            ],
                        ):
                            code = orchestrator_reply_cli.main()
            self.assertEqual(code, 1)
            runner.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
