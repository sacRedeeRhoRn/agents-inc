#!/usr/bin/env python3
from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from agents_inc.cli import orchestrator_reply as orchestrator_reply_cli  # noqa: E402
from agents_inc.core.model_profiles import (  # noqa: E402
    DEFAULT_HEAD_MODEL,
    DEFAULT_HEAD_REASONING_EFFORT,
    DEFAULT_SPECIALIST_MODEL,
    DEFAULT_SPECIALIST_REASONING_EFFORT,
)


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
        self.assertEqual(runtime["max_cycles"], 0)

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
        self.assertEqual(runtime["max_cycles"], 0)

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

    def test_group_mode_allows_max_cycles_1(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            fake_root = Path(td)
            captured = {}

            def _fake_run(config):  # type: ignore[no-untyped-def]
                captured["config"] = config
                return {
                    "project_id": "proj-a",
                    "turn_dir": str(fake_root / "turn"),
                    "full_report_path": str(fake_root / "full-report.md"),
                }

            with patch(
                "agents_inc.cli.orchestrator_reply._resolve_project_fabric_root",
                return_value=fake_root,
            ):
                with patch("agents_inc.cli.orchestrator_reply.ensure_fabric_root_initialized"):
                    with patch(
                        "agents_inc.cli.orchestrator_reply.run_orchestrator_reply",
                        side_effect=_fake_run,
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
                                "--json",
                            ],
                        ):
                            code = orchestrator_reply_cli.main()
            self.assertEqual(code, 0)
            runner.assert_called_once()
            config = captured.get("config")
            self.assertIsNotNone(config)
            self.assertEqual(config.max_cycles, 1)

    def test_model_settings_defaults(self) -> None:
        args = SimpleNamespace(
            specialist_model=None,
            head_model=None,
            specialist_reasoning_effort=None,
            head_reasoning_effort=None,
        )
        settings = orchestrator_reply_cli._resolve_model_settings(args)
        self.assertEqual(settings["specialist_model"], DEFAULT_SPECIALIST_MODEL)
        self.assertEqual(settings["head_model"], DEFAULT_HEAD_MODEL)
        self.assertEqual(
            settings["specialist_reasoning_effort"], DEFAULT_SPECIALIST_REASONING_EFFORT
        )
        self.assertEqual(settings["head_reasoning_effort"], DEFAULT_HEAD_REASONING_EFFORT)

    def test_model_settings_normalize_aliases(self) -> None:
        args = SimpleNamespace(
            specialist_model="codex-5.3-spark",
            head_model="codex-5.3",
            specialist_reasoning_effort=None,
            head_reasoning_effort="extra",
        )
        settings = orchestrator_reply_cli._resolve_model_settings(args)
        self.assertEqual(settings["specialist_model"], "gpt-5.3-codex-spark")
        self.assertEqual(settings["head_model"], "gpt-5.3-codex")
        self.assertEqual(
            settings["specialist_reasoning_effort"], DEFAULT_SPECIALIST_REASONING_EFFORT
        )
        self.assertEqual(settings["head_reasoning_effort"], "xhigh")

    def test_main_passes_model_overrides(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            fake_root = Path(td)
            captured = {}

            def _fake_run(config):  # type: ignore[no-untyped-def]
                captured["config"] = config
                return {
                    "project_id": "proj-a",
                    "turn_dir": str(fake_root / "turn"),
                    "full_report_path": str(fake_root / "full-report.md"),
                }

            with patch(
                "agents_inc.cli.orchestrator_reply._resolve_project_fabric_root",
                return_value=fake_root,
            ):
                with patch("agents_inc.cli.orchestrator_reply.ensure_fabric_root_initialized"):
                    with patch(
                        "agents_inc.cli.orchestrator_reply.run_orchestrator_reply",
                        side_effect=_fake_run,
                    ):
                        with patch.object(
                            sys,
                            "argv",
                            [
                                "agents-inc-orchestrator-reply",
                                "--project-id",
                                "proj-a",
                                "--message",
                                "delegate objective",
                                "--specialist-model",
                                "codex-5.3-spark",
                                "--head-model",
                                "codex-5.3",
                                "--head-reasoning-effort",
                                "xhigh",
                                "--json",
                            ],
                        ):
                            code = orchestrator_reply_cli.main()
            self.assertEqual(code, 0)
            config = captured.get("config")
            self.assertIsNotNone(config)
            self.assertEqual(config.specialist_model, "gpt-5.3-codex-spark")
            self.assertEqual(config.head_model, "gpt-5.3-codex")
            self.assertEqual(config.head_reasoning_effort, "xhigh")
            self.assertEqual(config.web_search_policy, "web-role-only")

    def test_main_passes_web_search_policy_override(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            fake_root = Path(td)
            captured = {}

            def _fake_run(config):  # type: ignore[no-untyped-def]
                captured["config"] = config
                return {
                    "project_id": "proj-a",
                    "turn_dir": str(fake_root / "turn"),
                    "full_report_path": str(fake_root / "full-report.md"),
                }

            with patch(
                "agents_inc.cli.orchestrator_reply._resolve_project_fabric_root",
                return_value=fake_root,
            ):
                with patch("agents_inc.cli.orchestrator_reply.ensure_fabric_root_initialized"):
                    with patch(
                        "agents_inc.cli.orchestrator_reply.run_orchestrator_reply",
                        side_effect=_fake_run,
                    ):
                        with patch.object(
                            sys,
                            "argv",
                            [
                                "agents-inc-orchestrator-reply",
                                "--project-id",
                                "proj-a",
                                "--message",
                                "delegate objective",
                                "--web-search-policy",
                                "all-enabled",
                                "--json",
                            ],
                        ):
                            code = orchestrator_reply_cli.main()
            self.assertEqual(code, 0)
            config = captured.get("config")
            self.assertIsNotNone(config)
            self.assertEqual(config.web_search_policy, "all-enabled")

    def test_main_prints_live_notes_in_non_json_mode(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            fake_root = Path(td)

            def _fake_run(config):  # type: ignore[no-untyped-def]
                callback = config.progress_callback
                self.assertTrue(callable(callback))
                assert callback is not None
                callback(
                    {
                        "event": "turn_started",
                        "selected_groups": ["developer", "quality-assurance"],
                        "max_cycles": 4,
                    }
                )
                callback({"event": "cycle_started", "cycle": 1})
                callback({"event": "meeting_started", "cycle": 1})
                return {
                    "project_id": "proj-a",
                    "turn_dir": str(fake_root / "turn"),
                    "full_report_path": str(fake_root / "full-report.md"),
                }

            out = io.StringIO()
            with redirect_stdout(out):
                with patch(
                    "agents_inc.cli.orchestrator_reply._resolve_project_fabric_root",
                    return_value=fake_root,
                ):
                    with patch("agents_inc.cli.orchestrator_reply.ensure_fabric_root_initialized"):
                        with patch(
                            "agents_inc.cli.orchestrator_reply.run_orchestrator_reply",
                            side_effect=_fake_run,
                        ):
                            with patch.object(
                                sys,
                                "argv",
                                [
                                    "agents-inc-orchestrator-reply",
                                    "--project-id",
                                    "proj-a",
                                    "--message",
                                    "delegate objective",
                                ],
                            ):
                                code = orchestrator_reply_cli.main()
            self.assertEqual(code, 0)
            text = out.getvalue()
            self.assertIn("live: turn started", text)
            self.assertIn("live: cycle 1 started", text)
            self.assertIn("live: cycle 1 head meeting started", text)

    def test_main_clears_terminal_before_non_json_final_output(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            fake_root = Path(td)

            def _fake_run(config):  # type: ignore[no-untyped-def]
                return {
                    "project_id": "proj-a",
                    "turn_dir": str(fake_root / "turn"),
                    "full_report_path": str(fake_root / "full-report.md"),
                }

            out = io.StringIO()
            with redirect_stdout(out):
                with patch(
                    "agents_inc.cli.orchestrator_reply._resolve_project_fabric_root",
                    return_value=fake_root,
                ):
                    with patch("agents_inc.cli.orchestrator_reply.ensure_fabric_root_initialized"):
                        with patch(
                            "agents_inc.cli.orchestrator_reply.run_orchestrator_reply",
                            side_effect=_fake_run,
                        ):
                            with patch(
                                "agents_inc.cli.orchestrator_reply.clear_interactive_terminal"
                            ) as clear_terminal:
                                with patch.object(
                                    sys,
                                    "argv",
                                    [
                                        "agents-inc-orchestrator-reply",
                                        "--project-id",
                                        "proj-a",
                                        "--message",
                                        "delegate objective",
                                    ],
                                ):
                                    code = orchestrator_reply_cli.main()
            self.assertEqual(code, 0)
            clear_terminal.assert_called_once()
            self.assertIn("project_id: proj-a", out.getvalue())

    def test_main_json_mode_streams_live_notes_to_stderr(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            fake_root = Path(td)

            def _fake_run(config):  # type: ignore[no-untyped-def]
                callback = config.progress_callback
                self.assertTrue(callable(callback))
                assert callback is not None
                callback({"event": "cycle_started", "cycle": 1})
                return {
                    "project_id": "proj-a",
                    "turn_dir": str(fake_root / "turn"),
                    "full_report_path": str(fake_root / "full-report.md"),
                }

            out = io.StringIO()
            err = io.StringIO()
            with redirect_stdout(out):
                with redirect_stderr(err):
                    with patch(
                        "agents_inc.cli.orchestrator_reply._resolve_project_fabric_root",
                        return_value=fake_root,
                    ):
                        with patch(
                            "agents_inc.cli.orchestrator_reply.ensure_fabric_root_initialized"
                        ):
                            with patch(
                                "agents_inc.cli.orchestrator_reply.run_orchestrator_reply",
                                side_effect=_fake_run,
                            ):
                                with patch.object(
                                    sys,
                                    "argv",
                                    [
                                        "agents-inc-orchestrator-reply",
                                        "--project-id",
                                        "proj-a",
                                        "--message",
                                        "delegate objective",
                                        "--json",
                                    ],
                                ):
                                    code = orchestrator_reply_cli.main()
            self.assertEqual(code, 0)
            payload = json.loads(out.getvalue())
            self.assertEqual(payload.get("project_id"), "proj-a")
            self.assertIn("live: cycle 1 started", err.getvalue())

    def test_main_returns_130_for_abort_interrupt(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            fake_root = Path(td)
            blocked_text = (
                "BLOCKED[BLOCKED_ABORT_REQUESTED] "
                "blocked_report=/tmp/report blocked_reasons=/tmp/reasons"
            )

            out = io.StringIO()
            with redirect_stdout(out):
                with patch(
                    "agents_inc.cli.orchestrator_reply._resolve_project_fabric_root",
                    return_value=fake_root,
                ):
                    with patch("agents_inc.cli.orchestrator_reply.ensure_fabric_root_initialized"):
                        with patch(
                            "agents_inc.cli.orchestrator_reply.run_orchestrator_reply",
                            side_effect=RuntimeError(blocked_text),
                        ):
                            with patch.object(
                                sys,
                                "argv",
                                [
                                    "agents-inc-orchestrator-reply",
                                    "--project-id",
                                    "proj-a",
                                    "--message",
                                    "delegate objective",
                                ],
                            ):
                                code = orchestrator_reply_cli.main()
            self.assertEqual(code, 130)
            self.assertIn("interrupted: orchestration aborted by user", out.getvalue())


if __name__ == "__main__":
    unittest.main(verbosity=2)
