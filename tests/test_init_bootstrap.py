#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from agents_inc.cli import init_session  # noqa: E402


class InitBootstrapTests(unittest.TestCase):
    def test_init_bootstrap_no_launch_writes_state(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            fabric_root = Path(td) / "fabric"
            config_path = Path(td) / ".agents-inc" / "config.yaml"
            projects_root = Path(td) / "projects"
            buf = StringIO()
            argv = [
                "agents-inc-init",
                "--fabric-root",
                str(fabric_root),
                "--config-path",
                str(config_path),
                "--projects-root",
                str(projects_root),
                "--no-launch",
                "--json",
            ]
            with patch.object(sys, "argv", argv):
                with patch("sys.stdout", new=buf):
                    code = init_session.main()
            self.assertEqual(code, 0)
            payload = json.loads(buf.getvalue())
            self.assertEqual(payload["mode"], "bootstrap")
            self.assertEqual(Path(payload["fabric_root"]).resolve(), fabric_root.resolve())
            self.assertEqual(Path(payload["projects_root"]).resolve(), projects_root.resolve())
            state_path = Path(payload["bootstrap_state"])
            self.assertTrue(state_path.exists())

    def test_init_bootstrap_no_launch_human_output(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            fabric_root = Path(td) / "fabric"
            config_path = Path(td) / ".agents-inc" / "config.yaml"
            argv = [
                "agents-inc-init",
                "--fabric-root",
                str(fabric_root),
                "--config-path",
                str(config_path),
                "--no-launch",
            ]
            buf = StringIO()
            with patch.object(sys, "argv", argv):
                with patch("sys.stdout", new=buf):
                    code = init_session.main()
            self.assertEqual(code, 0)
            text = buf.getvalue()
            self.assertIn("agents-inc init complete.", text)
            self.assertIn("agents-inc group-list", text)
            self.assertIn("agents-inc init --json", text)

    def test_init_bootstrap_missing_codex_still_succeeds(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            fabric_root = Path(td) / "fabric"
            config_path = Path(td) / ".agents-inc" / "config.yaml"
            argv = [
                "agents-inc-init",
                "--fabric-root",
                str(fabric_root),
                "--config-path",
                str(config_path),
            ]
            with patch.object(sys, "argv", argv):
                with patch("agents_inc.cli.init_session.shutil.which", return_value=None):
                    code = init_session.main()
            self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
