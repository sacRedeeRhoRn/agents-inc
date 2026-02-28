#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


def run_cmd(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True)


class GroupsCLITests(unittest.TestCase):
    def test_groups_list_json_contract(self) -> None:
        proc = run_cmd(
            ["python3", str(SCRIPTS / "groups.py"), "list", "--fabric-root", str(ROOT), "--json"]
        )
        self.assertEqual(proc.returncode, 0, msg=f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}")
        payload = json.loads(proc.stdout)
        self.assertIn("groups", payload)
        self.assertGreaterEqual(len(payload["groups"]), 1)
        row = payload["groups"][0]
        for key in [
            "group_id",
            "display_name",
            "domain",
            "specialist_count",
            "template_version",
            "schema_version",
            "status",
            "source_path",
            "head_agent_id",
        ]:
            self.assertIn(key, row)

    def test_groups_new_non_interactive(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            fabric_root = Path(td) / "fabric"
            proc = run_cmd(
                [
                    "python3",
                    str(SCRIPTS / "groups.py"),
                    "new",
                    "--fabric-root",
                    str(fabric_root),
                    "--group-id",
                    "test-catalog-group",
                    "--display-name",
                    "Test Catalog Group",
                    "--domain",
                    "materials",
                    "--no-mirror-resources",
                ]
            )
            self.assertEqual(
                proc.returncode, 0, msg=f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
            )
            manifest_path = fabric_root / "catalog" / "groups" / "test-catalog-group.yaml"
            self.assertTrue(manifest_path.exists())
            manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["schema_version"], "2.0")
            self.assertGreaterEqual(len(manifest.get("specialists", [])), 5)


class MigrationTests(unittest.TestCase):
    def test_migrate_v2_group_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            fabric_root = Path(td) / "fabric"
            groups_dir = fabric_root / "catalog" / "groups"
            groups_dir.mkdir(parents=True, exist_ok=True)

            legacy = {
                "group_id": "legacy-group",
                "display_name": "Legacy Group",
                "template_version": "1.0.0",
                "domain": "legacy",
                "head": {
                    "agent_id": "legacy-head",
                    "skill_name": "grp-legacy-head",
                    "mission": "legacy mission",
                },
                "specialists": [
                    {
                        "agent_id": "legacy-core",
                        "skill_name": "grp-legacy-core",
                        "focus": "legacy focus",
                        "required_references": ["references/legacy-core.md"],
                        "required_outputs": ["claims_with_citations.md"],
                    }
                ],
                "tool_profile": "default",
                "default_workdirs": ["inputs", "analysis", "outputs"],
                "quality_gates": {
                    "citation_required": True,
                    "unresolved_claims_block": True,
                    "peer_check_required": True,
                    "consistency_required": True,
                    "scope_required": True,
                    "reproducibility_required": True,
                },
            }
            legacy_path = groups_dir / "legacy-group.yaml"
            legacy_path.write_text(yaml.safe_dump(legacy, sort_keys=False), encoding="utf-8")

            index_path = Path(td) / "projects-index.yaml"
            index_path.write_text(
                yaml.safe_dump({"schema_version": "1.0", "projects": {}}, sort_keys=False),
                encoding="utf-8",
            )

            dry = run_cmd(
                [
                    "python3",
                    str(SCRIPTS / "migrate_v2.py"),
                    "--fabric-root",
                    str(fabric_root),
                    "--project-index",
                    str(index_path),
                    "--dry-run",
                ]
            )
            self.assertEqual(dry.returncode, 0, msg=f"stdout:\n{dry.stdout}\nstderr:\n{dry.stderr}")

            apply = run_cmd(
                [
                    "python3",
                    str(SCRIPTS / "migrate_v2.py"),
                    "--fabric-root",
                    str(fabric_root),
                    "--project-index",
                    str(index_path),
                    "--apply",
                ]
            )
            self.assertEqual(
                apply.returncode, 0, msg=f"stdout:\n{apply.stdout}\nstderr:\n{apply.stderr}"
            )

            migrated = yaml.safe_load(legacy_path.read_text(encoding="utf-8"))
            self.assertEqual(migrated["schema_version"], "2.0")
            self.assertGreaterEqual(len(migrated.get("specialists", [])), 4)
            index = yaml.safe_load(index_path.read_text(encoding="utf-8"))
            self.assertEqual(index["schema_version"], "2.0")


if __name__ == "__main__":
    unittest.main(verbosity=2)
