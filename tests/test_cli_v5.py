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

from agents_inc.cli import create_project as create_cli  # noqa: E402
from agents_inc.cli import group_list as group_list_cli  # noqa: E402
from agents_inc.cli import new_group as new_group_cli  # noqa: E402
from agents_inc.cli import save_project as save_cli  # noqa: E402
from agents_inc.core.fabric_lib import ensure_fabric_root_initialized, load_yaml  # noqa: E402


class CLIV5Tests(unittest.TestCase):
    def test_group_list_outputs_indexed_ids(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            fabric_root = Path(td) / "fabric"
            ensure_fabric_root_initialized(fabric_root)
            buf = io.StringIO()
            with redirect_stdout(buf):
                with patch.object(
                    sys,
                    "argv",
                    ["agents-inc-group-list", "--fabric-root", str(fabric_root)],
                ):
                    code = group_list_cli.main()
            self.assertEqual(code, 0)
            text = buf.getvalue()
            self.assertIn("1.", text)
            self.assertIn("developer", text)

    def test_create_project_with_groups_and_no_launch(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            fabric_root = Path(td) / "fabric"
            projects_root = Path(td) / "projects"
            config_path = Path(td) / ".agents-inc" / "config.yaml"
            with patch(
                "agents_inc.cli.create_project.run_orchestrator_chat",
                return_value={"thread_id": "thread-123", "chat_log_path": str(Path(td) / "chat.log")},
            ):
                with patch.object(
                    sys,
                    "argv",
                    [
                        "agents-inc-create",
                        "proj-v5",
                        "--fabric-root",
                        str(fabric_root),
                        "--projects-root",
                        str(projects_root),
                        "--config-path",
                        str(config_path),
                        "--groups",
                        "developer,quality-assurance",
                        "--no-launch",
                        "--json",
                    ],
                ):
                    code = create_cli.main()
            self.assertEqual(code, 0)
            manifest_path = (
                projects_root
                / "proj-v5"
                / "agent_group_fabric"
                / "generated"
                / "projects"
                / "proj-v5"
                / "manifest.yaml"
            )
            self.assertTrue(manifest_path.exists())
            manifest = load_yaml(manifest_path)
            self.assertIsInstance(manifest, dict)
            selected = manifest.get("selected_groups", [])
            self.assertIn("developer", selected)
            self.assertIn("quality-assurance", selected)

    def test_create_project_respects_custom_group_from_source_fabric(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            fabric_root = Path(td) / "fabric"
            projects_root = Path(td) / "projects"
            config_path = Path(td) / ".agents-inc" / "config.yaml"
            ensure_fabric_root_initialized(fabric_root)
            with patch.object(
                sys,
                "argv",
                [
                    "agents-inc-new-group",
                    "--fabric-root",
                    str(fabric_root),
                    "--group-id",
                    "material-scientist",
                    "--display-name",
                    "Material Scientist",
                    "--domain",
                    "materials",
                    "--purpose",
                    "Identify candidate topological semimetal materials feasible for local compute workflows",
                    "--success-criteria",
                    "candidate shortlist with citations,reproducible local workflow",
                    "--extra-roles",
                    "crystallography-expert,solid-state-physics-expert",
                    "--no-codex",
                    "--force",
                ],
            ):
                self.assertEqual(new_group_cli.main(), 0)

            with patch(
                "agents_inc.cli.create_project.run_orchestrator_chat",
                return_value={"thread_id": "thread-123", "chat_log_path": str(Path(td) / "chat.log")},
            ):
                with patch.object(
                    sys,
                    "argv",
                    [
                        "agents-inc-create",
                        "proj-custom",
                        "--fabric-root",
                        str(fabric_root),
                        "--projects-root",
                        str(projects_root),
                        "--config-path",
                        str(config_path),
                        "--groups",
                        "developer,material-scientist",
                        "--no-launch",
                        "--json",
                    ],
                ):
                    code = create_cli.main()
            self.assertEqual(code, 0)

            manifest_path = (
                projects_root
                / "proj-custom"
                / "agent_group_fabric"
                / "generated"
                / "projects"
                / "proj-custom"
                / "manifest.yaml"
            )
            self.assertTrue(manifest_path.exists())
            manifest = load_yaml(manifest_path)
            self.assertIsInstance(manifest, dict)
            selected = manifest.get("selected_groups", [])
            self.assertEqual(selected, ["developer", "material-scientist"])

            synced_group = (
                projects_root
                / "proj-custom"
                / "agent_group_fabric"
                / "catalog"
                / "groups"
                / "material-scientist.yaml"
            )
            self.assertTrue(synced_group.exists())

    def test_save_project_creates_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            fabric_root = Path(td) / "fabric"
            projects_root = Path(td) / "projects"
            config_path = Path(td) / ".agents-inc" / "config.yaml"
            with patch(
                "agents_inc.cli.create_project.run_orchestrator_chat",
                return_value={"thread_id": "thread-123", "chat_log_path": str(Path(td) / "chat.log")},
            ):
                with patch.object(
                    sys,
                    "argv",
                    [
                        "agents-inc-create",
                        "proj-save",
                        "--fabric-root",
                        str(fabric_root),
                        "--projects-root",
                        str(projects_root),
                        "--config-path",
                        str(config_path),
                        "--groups",
                        "developer",
                        "--no-launch",
                    ],
                ):
                    self.assertEqual(create_cli.main(), 0)

            buf = io.StringIO()
            with redirect_stdout(buf):
                with patch.object(
                    sys,
                    "argv",
                    [
                        "agents-inc-save",
                        "proj-save",
                        "--scan-root",
                        str(projects_root),
                        "--config-path",
                        str(config_path),
                        "--json",
                    ],
                ):
                    code = save_cli.main()
            self.assertEqual(code, 0)
            payload = json.loads(buf.getvalue())
            self.assertIn("checkpoint_id", payload)
            self.assertIn("compact_id", payload)

    def test_new_group_without_codex_creates_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            fabric_root = Path(td) / "fabric"
            ensure_fabric_root_initialized(fabric_root)
            with patch.object(
                sys,
                "argv",
                [
                    "agents-inc-new-group",
                    "--fabric-root",
                    str(fabric_root),
                    "--group-id",
                    "client-success",
                    "--display-name",
                    "Client Success",
                    "--domain",
                    "professional-services",
                    "--purpose",
                    "Support client onboarding and delivery handoffs.",
                    "--success-criteria",
                    "handoffs complete,evidence validated",
                    "--no-codex",
                    "--force",
                ],
            ):
                code = new_group_cli.main()
            self.assertEqual(code, 0)
            manifest_path = fabric_root / "catalog" / "groups" / "client-success.yaml"
            self.assertTrue(manifest_path.exists())
            manifest = load_yaml(manifest_path)
            self.assertIsInstance(manifest, dict)
            specialists = manifest.get("specialists", [])
            roles = [str(item.get("role") or "") for item in specialists if isinstance(item, dict)]
            self.assertIn("web-research", roles)

    def test_regenerate_core_groups_from_seed(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            fabric_root = Path(td) / "fabric"
            ensure_fabric_root_initialized(fabric_root)
            with patch.object(
                sys,
                "argv",
                [
                    "agents-inc-new-group",
                    "--fabric-root",
                    str(fabric_root),
                    "--regenerate-core",
                    "--no-codex",
                    "--json",
                ],
            ):
                code = new_group_cli.main()
            self.assertEqual(code, 0)
            for gid in [
                "developer",
                "integration-delivery",
                "literature-intelligence",
                "data-curation",
                "quality-assurance",
                "design-communication",
            ]:
                self.assertTrue((fabric_root / "catalog" / "groups" / f"{gid}.yaml").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
