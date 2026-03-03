#!/usr/bin/env python3
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from agents_inc.cli import main as cli_main  # noqa: E402
from agents_inc.cli import resume as resume_cli  # noqa: E402


class CLIMainTests(unittest.TestCase):
    def test_main_unknown_command_returns_2(self) -> None:
        with patch.object(sys, "argv", ["agents-inc", "nope"]):
            code = cli_main.main()
        self.assertEqual(code, 2)

    def test_main_routes_init_command(self) -> None:
        with patch("agents_inc.cli.init_session.main", return_value=6) as mocked:
            with patch.object(sys, "argv", ["agents-inc", "init"]):
                code = cli_main.main()
        self.assertEqual(code, 6)
        mocked.assert_called_once()

    def test_main_routes_group_list_command(self) -> None:
        with patch("agents_inc.cli.group_list.main", return_value=5) as mocked:
            with patch.object(sys, "argv", ["agents-inc", "group-list"]):
                code = cli_main.main()
        self.assertEqual(code, 5)
        mocked.assert_called_once()

    def test_main_routes_create_command(self) -> None:
        with patch("agents_inc.cli.create_project.main", return_value=4) as mocked:
            with patch.object(sys, "argv", ["agents-inc", "create", "proj-x"]):
                code = cli_main.main()
        self.assertEqual(code, 4)
        mocked.assert_called_once()

    def test_main_routes_save_command(self) -> None:
        with patch("agents_inc.cli.save_project.main", return_value=3) as mocked:
            with patch.object(sys, "argv", ["agents-inc", "save", "proj-x"]):
                code = cli_main.main()
        self.assertEqual(code, 3)
        mocked.assert_called_once()

    def test_main_routes_list_command(self) -> None:
        with patch("agents_inc.cli.list_sessions.main", return_value=7) as mocked:
            with patch.object(sys, "argv", ["agents-inc", "list", "--json"]):
                code = cli_main.main()
        self.assertEqual(code, 7)
        mocked.assert_called_once()

    def test_main_routes_deactivate_command(self) -> None:
        with patch("agents_inc.cli.deactivate_project.main", return_value=8) as mocked:
            with patch.object(sys, "argv", ["agents-inc", "deactivate", "proj-x"]):
                code = cli_main.main()
        self.assertEqual(code, 8)
        mocked.assert_called_once()

    def test_main_routes_delete_command(self) -> None:
        with patch("agents_inc.cli.delete_project.main", return_value=12) as mocked:
            with patch.object(sys, "argv", ["agents-inc", "delete", "proj-x", "--yes"]):
                code = cli_main.main()
        self.assertEqual(code, 12)
        mocked.assert_called_once()

    def test_main_routes_project_groups_command(self) -> None:
        with patch("agents_inc.cli.project_groups.main", return_value=14) as mocked:
            with patch.object(sys, "argv", ["agents-inc", "project-groups", "list"]):
                code = cli_main.main()
        self.assertEqual(code, 14)
        mocked.assert_called_once()

    def test_main_version_flag(self) -> None:
        with patch.object(sys, "argv", ["agents-inc", "--version"]):
            code = cli_main.main()
        self.assertEqual(code, 0)

    def test_resume_cli_no_launch(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            project_root = Path(td) / "proj-test"
            project_root.mkdir(parents=True, exist_ok=True)
            with patch(
                "agents_inc.cli.resume.resolve_project_context",
                return_value=(
                    project_root / "agent_group_fabric",
                    project_root,
                    project_root,
                    project_root / "manifest.yaml",
                    {"project_id": "proj-test"},
                ),
            ):
                with patch(
                    "agents_inc.cli.resume.run_orchestrator_chat",
                    return_value={"thread_id": "thread-1", "chat_log_path": str(project_root / "chat.log")},
                ) as run_chat:
                    with patch.object(
                        sys, "argv", ["agents-inc-resume", "proj-test", "--no-launch", "--json"]
                    ):
                        code = resume_cli.main()
        self.assertEqual(code, 0)
        run_chat.assert_called_once()

    def test_resume_cli_runs_managed_chat(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            project_root = Path(td) / "proj-test"
            project_root.mkdir(parents=True, exist_ok=True)
            with patch(
                "agents_inc.cli.resume.resolve_project_context",
                return_value=(
                    project_root / "agent_group_fabric",
                    project_root,
                    project_root,
                    project_root / "manifest.yaml",
                    {"project_id": "proj-test"},
                ),
            ):
                with patch(
                    "agents_inc.cli.resume.load_orchestrator_state",
                    return_value={"thread_id": "thread-prev"},
                ):
                    with patch(
                        "agents_inc.cli.resume.run_orchestrator_chat",
                        return_value={"thread_id": "thread-next", "chat_log_path": str(project_root / "chat.log")},
                    ) as run_chat:
                        with patch.object(sys, "argv", ["agents-inc-resume", "proj-test", "--json"]):
                            code = resume_cli.main()
            self.assertEqual(code, 0)
            run_chat.assert_called_once()


if __name__ == "__main__":
    unittest.main(verbosity=2)
