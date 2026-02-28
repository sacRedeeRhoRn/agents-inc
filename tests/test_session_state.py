#!/usr/bin/env python3
from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from agents_inc.core.session_state import (  # noqa: E402
    find_resume_project,
    load_checkpoint,
    load_project_index,
    load_session_state,
    mark_stale_index_entries,
    resolve_state_project_root,
    write_checkpoint,
)


class SessionStateTests(unittest.TestCase):
    def test_checkpoint_roundtrip_and_latest_pointer(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            project_root = Path(td) / "proj-a"
            project_root.mkdir(parents=True, exist_ok=True)
            index_path = Path(td) / "projects-index.yaml"
            payload = {
                "project_id": "proj-a",
                "project_root": str(project_root),
                "fabric_root": str(project_root / "agent_group_fabric"),
                "task": "test-task",
                "constraints": {"timeline": "2 weeks"},
                "selected_groups": ["material-scientist"],
                "primary_group": "material-scientist",
                "group_order_recommendation": ["material-scientist"],
                "router_call": "Use $research-router for project proj-a group material-scientist: test-task.",
                "latest_artifacts": {},
                "pending_actions": ["act"],
            }
            first = write_checkpoint(project_root=project_root, payload=payload, project_index_path=index_path)
            second = write_checkpoint(project_root=project_root, payload=payload, project_index_path=index_path)

            self.assertNotEqual(first["checkpoint_id"], second["checkpoint_id"])

            latest = load_checkpoint(project_root, "latest")
            self.assertEqual(latest["checkpoint_id"], second["checkpoint_id"])

            first_loaded = load_checkpoint(project_root, str(first["checkpoint_id"]))
            self.assertEqual(first_loaded["checkpoint_id"], first["checkpoint_id"])

            state = load_session_state(project_root)
            self.assertEqual(int(state["checkpoint_counter"]), 2)
            self.assertEqual(state["latest_checkpoint_id"], second["checkpoint_id"])

            index_data = load_project_index(index_path)
            self.assertEqual(index_data["projects"]["proj-a"]["last_checkpoint"], second["checkpoint_id"])
            self.assertEqual(index_data["projects"]["proj-a"]["status"], "active")

    def test_mark_stale_entries(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            project_root = Path(td) / "proj-stale"
            project_root.mkdir(parents=True, exist_ok=True)
            index_path = Path(td) / "projects-index.yaml"
            payload = {
                "project_id": "proj-stale",
                "project_root": str(project_root),
                "fabric_root": str(project_root / "agent_group_fabric"),
                "task": "x",
                "constraints": {},
                "selected_groups": ["developer"],
                "primary_group": "developer",
                "group_order_recommendation": ["developer"],
                "router_call": "Use $research-router for project proj-stale group developer: x.",
                "latest_artifacts": {},
                "pending_actions": [],
            }
            write_checkpoint(project_root=project_root, payload=payload, project_index_path=index_path)
            shutil.rmtree(project_root)

            updated = mark_stale_index_entries(index_path)
            self.assertEqual(updated["projects"]["proj-stale"]["status"], "stale")

    def test_find_resume_project_with_fallback_scan(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            scan_root = Path(td) / "codex-projects"
            project_root = scan_root / "proj-fallback"
            manifest_path = (
                project_root
                / "agent_group_fabric"
                / "generated"
                / "projects"
                / "proj-fallback"
                / "manifest.yaml"
            )
            manifest_path.parent.mkdir(parents=True, exist_ok=True)
            manifest_path.write_text(yaml.safe_dump({"project_id": "proj-fallback"}, sort_keys=False), encoding="utf-8")

            index_path = Path(td) / "projects-index.yaml"
            found = find_resume_project(
                index_path=index_path,
                project_id="proj-fallback",
                fallback_scan_root=scan_root,
            )
            self.assertIsNotNone(found)
            self.assertEqual(found["project_id"], "proj-fallback")

            index_data = load_project_index(index_path)
            self.assertIn("proj-fallback", index_data["projects"])
            self.assertEqual(index_data["projects"]["proj-fallback"]["status"], "active")

    def test_resolve_state_project_root_prefers_parent_project_root(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            project_root = Path(td) / "proj-root"
            fabric_root = project_root / "agent_group_fabric"
            fabric_root.mkdir(parents=True, exist_ok=True)
            (project_root / "project-manifest.yaml").write_text(
                yaml.safe_dump({"project_id": "proj-root"}, sort_keys=False),
                encoding="utf-8",
            )
            resolved = resolve_state_project_root(fabric_root, "proj-root")
            self.assertEqual(resolved, project_root)

    def test_resolve_state_project_root_falls_back_to_generated_project(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            fabric_root = Path(td) / "agent_group_fabric"
            fabric_root.mkdir(parents=True, exist_ok=True)
            resolved = resolve_state_project_root(fabric_root, "proj-x")
            self.assertEqual(resolved, fabric_root / "generated" / "projects" / "proj-x")


if __name__ == "__main__":
    unittest.main(verbosity=2)
