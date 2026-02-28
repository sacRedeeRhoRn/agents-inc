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

from agents_inc.core.config_state import (  # noqa: E402
    default_config_path,
    get_projects_root,
    set_projects_root,
)
from agents_inc.core.session_compaction import (  # noqa: E402
    compact_session,
    load_compacted,
    load_group_sessions,
    load_latest_compacted_summary,
)
from agents_inc.core.session_state import (  # noqa: E402
    find_resume_project,
    list_index_projects,
    load_checkpoint,
    load_project_index,
    load_session_state,
    mark_stale_index_entries,
    resolve_state_project_root,
    sync_index_from_scan,
    write_checkpoint,
)


class SessionStateTests(unittest.TestCase):
    def test_config_projects_root_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            config_path = Path(td) / "config.yaml"
            self.assertEqual(
                get_projects_root(config_path), (Path.home() / "codex-projects").resolve()
            )

            custom_root = Path(td) / "research-projects"
            set_projects_root(config_path, custom_root)
            self.assertEqual(get_projects_root(config_path), custom_root.resolve())
            self.assertEqual(default_config_path(str(config_path)), config_path.resolve())

    def test_compact_session_roundtrip_and_group_codes(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            project_root = Path(td) / "proj-a"
            project_root.mkdir(parents=True, exist_ok=True)
            payload = {
                "project_id": "proj-a",
                "project_root": str(project_root),
                "fabric_root": str(project_root / "agent_group_fabric"),
                "task": "test-task",
                "selected_groups": ["developer", "material-scientist"],
                "router_call": "Use $research-router for project proj-a group developer: test-task.",
                "pending_actions": ["act"],
                "latest_artifacts": {},
            }
            first = compact_session(
                project_root=project_root,
                payload=payload,
                selected_groups=payload["selected_groups"],
            )
            second = compact_session(
                project_root=project_root,
                payload=payload,
                selected_groups=payload["selected_groups"],
            )
            self.assertNotEqual(first["compact_id"], second["compact_id"])

            latest = load_compacted(project_root, "latest")
            self.assertEqual(latest["compact_id"], second["compact_id"])
            self.assertEqual(latest["group_session_map"]["developer"], "proj-a::developer::000001")
            self.assertEqual(
                latest["group_session_map"]["material-scientist"],
                "proj-a::material-scientist::000001",
            )

            sessions = load_group_sessions(project_root)
            self.assertIn("developer", sessions["sessions"])

            summary = load_latest_compacted_summary(project_root)
            self.assertIsNotNone(summary)
            assert summary is not None
            self.assertEqual(summary["session_code"], second["session_code"])
            self.assertIn("developer", summary["active_groups"])

    def test_group_session_codes_are_project_scoped(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            project_a = Path(td) / "proj-a"
            project_b = Path(td) / "proj-b"
            project_a.mkdir(parents=True, exist_ok=True)
            project_b.mkdir(parents=True, exist_ok=True)
            payload_a = {
                "project_id": "proj-a",
                "project_root": str(project_a),
                "fabric_root": str(project_a / "agent_group_fabric"),
                "task": "a",
                "selected_groups": ["developer"],
                "router_call": "x",
                "pending_actions": [],
                "latest_artifacts": {},
            }
            payload_b = {
                "project_id": "proj-b",
                "project_root": str(project_b),
                "fabric_root": str(project_b / "agent_group_fabric"),
                "task": "b",
                "selected_groups": ["developer"],
                "router_call": "y",
                "pending_actions": [],
                "latest_artifacts": {},
            }
            compact_a = compact_session(
                project_root=project_a, payload=payload_a, selected_groups=["developer"]
            )
            compact_b = compact_session(
                project_root=project_b, payload=payload_b, selected_groups=["developer"]
            )
            self.assertNotEqual(
                compact_a["group_session_map"]["developer"],
                compact_b["group_session_map"]["developer"],
            )

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
            first = write_checkpoint(
                project_root=project_root, payload=payload, project_index_path=index_path
            )
            second = write_checkpoint(
                project_root=project_root, payload=payload, project_index_path=index_path
            )

            self.assertNotEqual(first["checkpoint_id"], second["checkpoint_id"])

            latest = load_checkpoint(project_root, "latest")
            self.assertEqual(latest["checkpoint_id"], second["checkpoint_id"])

            first_loaded = load_checkpoint(project_root, str(first["checkpoint_id"]))
            self.assertEqual(first_loaded["checkpoint_id"], first["checkpoint_id"])

            state = load_session_state(project_root)
            self.assertEqual(int(state["checkpoint_counter"]), 2)
            self.assertEqual(state["latest_checkpoint_id"], second["checkpoint_id"])

            index_data = load_project_index(index_path)
            self.assertEqual(
                index_data["projects"]["proj-a"]["last_checkpoint"], second["checkpoint_id"]
            )
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
            write_checkpoint(
                project_root=project_root, payload=payload, project_index_path=index_path
            )
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
            manifest_path.write_text(
                yaml.safe_dump({"project_id": "proj-fallback"}, sort_keys=False), encoding="utf-8"
            )

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

    def test_list_index_projects_include_stale(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            project_root = Path(td) / "proj-stale-list"
            project_root.mkdir(parents=True, exist_ok=True)
            index_path = Path(td) / "projects-index.yaml"
            payload = {
                "project_id": "proj-stale-list",
                "project_root": str(project_root),
                "fabric_root": str(project_root / "agent_group_fabric"),
                "task": "x",
                "constraints": {},
                "selected_groups": ["developer"],
                "primary_group": "developer",
                "group_order_recommendation": ["developer"],
                "router_call": "Use $research-router for project proj-stale-list group developer: x.",
                "latest_artifacts": {},
                "pending_actions": [],
            }
            write_checkpoint(
                project_root=project_root, payload=payload, project_index_path=index_path
            )
            shutil.rmtree(project_root)

            active = list_index_projects(index_path, include_stale=False)
            self.assertEqual(active, [])

            all_rows = list_index_projects(index_path, include_stale=True)
            self.assertEqual(len(all_rows), 1)
            self.assertEqual(all_rows[0]["status"], "stale")

    def test_sync_index_from_scan_discovers_project(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            scan_root = Path(td) / "codex-projects"
            project_root = scan_root / "proj-sync"
            manifest_path = (
                project_root
                / "agent_group_fabric"
                / "generated"
                / "projects"
                / "proj-sync"
                / "manifest.yaml"
            )
            manifest_path.parent.mkdir(parents=True, exist_ok=True)
            manifest_path.write_text(
                yaml.safe_dump({"project_id": "proj-sync"}, sort_keys=False), encoding="utf-8"
            )
            latest_path = project_root / ".agents-inc" / "state" / "latest-checkpoint.yaml"
            latest_path.parent.mkdir(parents=True, exist_ok=True)
            latest_path.write_text(
                yaml.safe_dump(
                    {
                        "project_id": "proj-sync",
                        "checkpoint_id": "20260301T000000Z-000001",
                        "checkpoint_path": str(
                            project_root
                            / ".agents-inc"
                            / "state"
                            / "checkpoints"
                            / "20260301T000000Z-000001.yaml"
                        ),
                    },
                    sort_keys=False,
                ),
                encoding="utf-8",
            )

            index_path = Path(td) / "projects-index.yaml"
            stats = sync_index_from_scan(index_path, scan_root)
            self.assertEqual(stats["created"], 1)
            self.assertEqual(stats["updated"], 0)

            rows = list_index_projects(index_path, include_stale=False)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["project_id"], "proj-sync")
            self.assertEqual(rows[0]["last_checkpoint"], "20260301T000000Z-000001")

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
