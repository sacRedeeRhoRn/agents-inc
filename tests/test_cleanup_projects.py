#!/usr/bin/env python3
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from agents_inc.cli import cleanup_projects as cleanup_cli  # noqa: E402


class CleanupProjectsTests(unittest.TestCase):
    def test_cleanup_all_indexed_deletes_roots_and_clears_index(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            index_path = root / "projects-index.yaml"
            proj_a = root / "proj-a"
            proj_b = root / "proj-b"
            proj_a.mkdir(parents=True, exist_ok=True)
            proj_b.mkdir(parents=True, exist_ok=True)
            (proj_a / ".agents-inc").mkdir(parents=True, exist_ok=True)
            (proj_b / "agent_group_fabric").mkdir(parents=True, exist_ok=True)

            with index_path.open("w", encoding="utf-8") as handle:
                yaml.safe_dump(
                    {
                        "schema_version": "3.0",
                        "projects": {
                            "proj-a": {"project_root": str(proj_a), "status": "active"},
                            "proj-b": {"project_root": str(proj_b), "status": "active"},
                        },
                    },
                    handle,
                    sort_keys=False,
                )

            with patch.object(
                sys,
                "argv",
                [
                    "agents-inc cleanup-projects",
                    "--all-indexed",
                    "--yes",
                    "--project-index",
                    str(index_path),
                ],
            ):
                code = cleanup_cli.main()
            self.assertEqual(code, 0)
            self.assertFalse(proj_a.exists())
            self.assertFalse(proj_b.exists())
            payload = yaml.safe_load(index_path.read_text(encoding="utf-8"))
            self.assertEqual(payload.get("projects"), {})


if __name__ == "__main__":
    unittest.main(verbosity=2)
