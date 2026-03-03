#!/usr/bin/env python3
from __future__ import annotations

import io
import json
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

from agents_inc.cli import list_sessions as list_sessions_cli  # noqa: E402
from agents_inc.core.session_state import save_project_index  # noqa: E402


class CLIListSessionsTests(unittest.TestCase):
    def _seed_index(self, td: str) -> Path:
        root = Path(td)
        active_root = root / "proj-active"
        inactive_root = root / "proj-inactive"
        active_root.mkdir(parents=True, exist_ok=True)
        inactive_root.mkdir(parents=True, exist_ok=True)
        index_path = root / "projects-index.yaml"
        save_project_index(
            index_path,
            {
                "schema_version": "3.0",
                "projects": {
                    "proj-active": {
                        "project_root": str(active_root),
                        "fabric_root": str(active_root / "agent_group_fabric"),
                        "status": "active",
                    },
                    "proj-inactive": {
                        "project_root": str(inactive_root),
                        "fabric_root": str(inactive_root / "agent_group_fabric"),
                        "status": "inactive",
                    },
                    "proj-stale": {
                        "project_root": str(root / "proj-stale-missing"),
                        "fabric_root": str(root / "proj-stale-missing" / "agent_group_fabric"),
                        "status": "stale",
                    },
                },
            },
        )
        return index_path

    def test_default_list_includes_inactive_excludes_stale(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            index_path = self._seed_index(td)
            out = io.StringIO()
            with redirect_stdout(out):
                with patch.object(
                    sys,
                    "argv",
                    [
                        "agents-inc-list",
                        "--project-index",
                        str(index_path),
                        "--scan-root",
                        td,
                        "--no-scan",
                        "--json",
                    ],
                ):
                    code = list_sessions_cli.main()
            self.assertEqual(code, 0)
            payload = json.loads(out.getvalue())
            sessions = payload.get("sessions", [])
            self.assertEqual(payload.get("count"), 2)
            self.assertEqual(
                {str(row.get("project_id")) for row in sessions},
                {"proj-active", "proj-inactive"},
            )

    def test_include_stale_flag_adds_stale_rows(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            index_path = self._seed_index(td)
            out = io.StringIO()
            with redirect_stdout(out):
                with patch.object(
                    sys,
                    "argv",
                    [
                        "agents-inc-list",
                        "--project-index",
                        str(index_path),
                        "--scan-root",
                        td,
                        "--no-scan",
                        "--include-stale",
                        "--json",
                    ],
                ):
                    code = list_sessions_cli.main()
            self.assertEqual(code, 0)
            payload = json.loads(out.getvalue())
            sessions = payload.get("sessions", [])
            self.assertEqual(payload.get("count"), 3)
            self.assertEqual(
                {str(row.get("project_id")) for row in sessions},
                {"proj-active", "proj-inactive", "proj-stale"},
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
