#!/usr/bin/env python3
from __future__ import annotations

import sys
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

    def test_main_routes_list_command(self) -> None:
        with patch("agents_inc.cli.list_sessions.main", return_value=7) as mocked:
            with patch.object(sys, "argv", ["agents-inc", "list", "--json"]):
                code = cli_main.main()
        self.assertEqual(code, 7)
        mocked.assert_called_once()

    def test_resume_cli_no_launch(self) -> None:
        summary = {
            "project_id": "proj-test",
            "project_root": "/tmp/proj-test",
            "session_code": "sc-1",
            "selected_groups": ["developer"],
            "router_call": "Use $research-router for project proj-test group developer: test.",
        }
        with patch("agents_inc.cli.resume.run_resume_flow", return_value=summary) as run_resume:
            with patch.object(sys, "argv", ["agents-inc-resume", "proj-test", "--no-launch"]):
                code = resume_cli.main()
        self.assertEqual(code, 0)
        run_resume.assert_called_once()

    def test_resume_cli_launches_codex(self) -> None:
        summary = {
            "project_id": "proj-test",
            "project_root": "/tmp/proj-test",
            "session_code": "sc-1",
            "selected_groups": ["developer", "material-scientist"],
            "router_call": "Use $research-router for project proj-test group developer: test.",
        }
        with patch("agents_inc.cli.resume.run_resume_flow", return_value=summary):
            with patch("agents_inc.cli.resume.shutil.which", return_value="/usr/bin/codex"):
                with patch("agents_inc.cli.resume.subprocess.run") as mocked_run:
                    mocked_run.return_value.returncode = 0
                    with patch.object(sys, "argv", ["agents-inc-resume", "proj-test"]):
                        code = resume_cli.main()
        self.assertEqual(code, 0)
        mocked_run.assert_called_once()
        cmd = mocked_run.call_args[0][0]
        self.assertEqual(cmd[0], "/usr/bin/codex")
        self.assertEqual(cmd[1], "-C")
        self.assertEqual(cmd[2], "/tmp/proj-test")


if __name__ == "__main__":
    unittest.main(verbosity=2)
