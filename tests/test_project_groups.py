#!/usr/bin/env python3
from __future__ import annotations

import io
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

from agents_inc.cli import new_project as new_project_cli  # noqa: E402
from agents_inc.cli import project_groups as project_groups_cli  # noqa: E402
from agents_inc.core.fabric_lib import ensure_fabric_root_initialized, load_yaml  # noqa: E402


class ProjectGroupsTests(unittest.TestCase):
    def test_add_and_remove_group_updates_project_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            fabric_root = Path(td) / "agent_group_fabric"
            ensure_fabric_root_initialized(fabric_root)
            project_id = "proj-group-lifecycle"

            with patch.object(
                sys,
                "argv",
                [
                    "agents-inc new-project",
                    "--fabric-root",
                    str(fabric_root),
                    "--project-id",
                    project_id,
                    "--groups",
                    "developer",
                    "--force",
                ],
            ):
                self.assertEqual(new_project_cli.main(), 0)

            with patch.object(
                sys,
                "argv",
                [
                    "agents-inc project-groups",
                    "add",
                    "--fabric-root",
                    str(fabric_root),
                    "--project-id",
                    project_id,
                    "--groups",
                    "integration-delivery",
                    "--activate-heads",
                    "--json",
                ],
            ):
                self.assertEqual(project_groups_cli.main(), 0)

            manifest_path = fabric_root / "generated" / "projects" / project_id / "manifest.yaml"
            manifest = load_yaml(manifest_path)
            self.assertIsInstance(manifest, dict)
            selected = manifest.get("selected_groups", [])
            self.assertIn("integration-delivery", selected)

            with patch.object(
                sys,
                "argv",
                [
                    "agents-inc project-groups",
                    "remove",
                    "--fabric-root",
                    str(fabric_root),
                    "--project-id",
                    project_id,
                    "--groups",
                    "integration-delivery",
                    "--json",
                ],
            ):
                self.assertEqual(project_groups_cli.main(), 0)

            manifest = load_yaml(manifest_path)
            self.assertIsInstance(manifest, dict)
            selected = manifest.get("selected_groups", [])
            self.assertNotIn("integration-delivery", selected)

    def test_create_group_adds_catalog_and_project_selection(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            fabric_root = Path(td) / "agent_group_fabric"
            ensure_fabric_root_initialized(fabric_root)
            project_id = "proj-group-create"

            with patch.object(
                sys,
                "argv",
                [
                    "agents-inc new-project",
                    "--fabric-root",
                    str(fabric_root),
                    "--project-id",
                    project_id,
                    "--groups",
                    "developer",
                    "--force",
                ],
            ):
                self.assertEqual(new_project_cli.main(), 0)

            with patch.object(
                sys,
                "argv",
                [
                    "agents-inc project-groups",
                    "create",
                    "--fabric-root",
                    str(fabric_root),
                    "--project-id",
                    project_id,
                    "--group-id",
                    "literature-intelligence-lite",
                    "--display-name",
                    "Polymorphism Researcher Lite",
                    "--domain",
                    "materials-research",
                    "--json",
                ],
            ):
                self.assertEqual(project_groups_cli.main(), 0)

            catalog_manifest = (
                fabric_root / "catalog" / "groups" / "literature-intelligence-lite.yaml"
            )
            self.assertTrue(catalog_manifest.exists())

            manifest_path = fabric_root / "generated" / "projects" / project_id / "manifest.yaml"
            manifest = load_yaml(manifest_path)
            self.assertIsInstance(manifest, dict)
            selected = manifest.get("selected_groups", [])
            self.assertIn("literature-intelligence-lite", selected)

    def test_list_command_reports_selected_groups(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            fabric_root = Path(td) / "agent_group_fabric"
            ensure_fabric_root_initialized(fabric_root)
            project_id = "proj-group-list"

            with patch.object(
                sys,
                "argv",
                [
                    "agents-inc new-project",
                    "--fabric-root",
                    str(fabric_root),
                    "--project-id",
                    project_id,
                    "--groups",
                    "developer,quality-assurance",
                    "--force",
                ],
            ):
                self.assertEqual(new_project_cli.main(), 0)

            buf = io.StringIO()
            with redirect_stdout(buf):
                with patch.object(
                    sys,
                    "argv",
                    [
                        "agents-inc project-groups",
                        "list",
                        "--fabric-root",
                        str(fabric_root),
                        "--project-id",
                        project_id,
                    ],
                ):
                    self.assertEqual(project_groups_cli.main(), 0)
            text = buf.getvalue()
            self.assertIn("selected_groups: developer,quality-assurance", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
