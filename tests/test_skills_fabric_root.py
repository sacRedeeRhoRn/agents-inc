#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from agents_inc.cli import skills as skills_cli  # noqa: E402


class SkillsFabricRootTests(unittest.TestCase):
    def test_resolve_project_prefers_explicit_fabric_root_when_manifest_exists(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            explicit_fabric = base / "explicit-fabric"
            manifest = explicit_fabric / "generated" / "projects" / "proj-a" / "manifest.yaml"
            manifest.parent.mkdir(parents=True, exist_ok=True)
            manifest.write_text("project_id: proj-a\nselected_groups: []\n", encoding="utf-8")

            args = argparse.Namespace(
                project_id="proj-a",
                fabric_root=str(explicit_fabric),
                project_index=str(base / "projects-index.yaml"),
                scan_root=str(base / "scan"),
                config_path=None,
            )
            with patch(
                "agents_inc.cli.skills.find_resume_project",
                return_value={
                    "project_root": str(base / "proj-a"),
                    "fabric_root": str(base / "indexed-fabric"),
                },
            ):
                _, _, resolved_fabric = skills_cli._resolve_project(args)
            self.assertEqual(resolved_fabric, explicit_fabric.resolve())


if __name__ == "__main__":
    unittest.main(verbosity=2)
