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

from agents_inc.cli import deactivate_project, delete_project  # noqa: E402
from agents_inc.core.session_state import (  # noqa: E402
    find_resume_project,
    get_index_project,
    load_project_index,
    write_checkpoint,
)


class ProjectControlTests(unittest.TestCase):
    def _seed_project(self, td: str, project_id: str) -> tuple[Path, Path]:
        project_root = Path(td) / "projects" / project_id
        (project_root / ".agents-inc" / "state").mkdir(parents=True, exist_ok=True)
        (project_root / "agent_group_fabric").mkdir(parents=True, exist_ok=True)
        index_path = Path(td) / "projects-index.yaml"
        payload = {
            "project_id": project_id,
            "project_root": str(project_root),
            "fabric_root": str(project_root / "agent_group_fabric"),
            "task": "x",
            "constraints": {},
            "selected_groups": ["developer"],
            "primary_group": "developer",
            "group_order_recommendation": ["developer"],
            "router_call": f"Use $research-router for project {project_id} group developer: x.",
            "latest_artifacts": {},
            "pending_actions": [],
        }
        write_checkpoint(project_root=project_root, payload=payload, project_index_path=index_path)
        return project_root, index_path

    def test_deactivate_blocks_resume_discovery(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            project_id = "proj-deactivate-test"
            project_root, index_path = self._seed_project(td, project_id)

            with patch.object(
                sys,
                "argv",
                [
                    "agents-inc deactivate",
                    project_id,
                    "--project-index",
                    str(index_path),
                    "--scan-root",
                    str(Path(td) / "projects"),
                ],
            ):
                code = deactivate_project.main()
            self.assertEqual(code, 0)

            row = get_index_project(index_path, project_id)
            self.assertIsNotNone(row)
            assert row is not None
            self.assertEqual(row.get("status"), "inactive")

            resumed = find_resume_project(
                index_path=index_path,
                project_id=project_id,
                fallback_scan_root=project_root.parent,
            )
            self.assertIsNone(resumed)

    def test_delete_requires_yes_and_removes_project_and_index(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            project_id = "proj-delete-test"
            project_root, index_path = self._seed_project(td, project_id)

            with patch.object(
                sys,
                "argv",
                [
                    "agents-inc delete",
                    project_id,
                    "--project-index",
                    str(index_path),
                    "--scan-root",
                    str(Path(td) / "projects"),
                ],
            ):
                denied = delete_project.main()
            self.assertEqual(denied, 1)
            self.assertTrue(project_root.exists())

            with patch.object(
                sys,
                "argv",
                [
                    "agents-inc delete",
                    project_id,
                    "--project-index",
                    str(index_path),
                    "--scan-root",
                    str(Path(td) / "projects"),
                    "--yes",
                ],
            ):
                deleted = delete_project.main()
            self.assertEqual(deleted, 0)
            self.assertFalse(project_root.exists())
            index = load_project_index(index_path)
            self.assertNotIn(project_id, index.get("projects", {}))


if __name__ == "__main__":
    unittest.main(verbosity=2)
