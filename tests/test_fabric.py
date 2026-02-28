#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
WORKSPACE = ROOT.parent

sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(WORKSPACE / "multi_agent_dirs"))

from fabric_lib import (  # noqa: E402
    ensure_group_shape,
    ensure_unique_names,
    gate_specialist_output,
    merge_locked_sections,
)
from controller import DirectoryController  # noqa: E402


def run_cmd(cmd: list[str]) -> str:
    proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return proc.stdout


class FabricUnitTests(unittest.TestCase):
    def test_manifest_validation_rejects_invalid_group(self) -> None:
        manifest = {
            "group_id": "bad group",
            "display_name": "x",
        }
        errors = ensure_group_shape(manifest, "invalid.yaml")
        self.assertTrue(errors)

    def test_skill_name_collision_resolution(self) -> None:
        names = ["proj-a-b", "proj-a-b", "proj-a-b", "proj-a-c"]
        unique = ensure_unique_names(names)
        self.assertEqual(len(unique), len(set(unique)))

    def test_overlay_sync_preserves_unlocked_and_updates_locked(self) -> None:
        existing = """# Title\n\nBEGIN_LOCKED:safety_policy\nold\nEND_LOCKED:safety_policy\n\nCustom section\n"""
        canonical = """# Title\n\nBEGIN_LOCKED:safety_policy\nnew\nEND_LOCKED:safety_policy\n"""
        merged = merge_locked_sections(existing, canonical)
        self.assertIn("new", merged)
        self.assertIn("Custom section", merged)

    def test_quality_gate_uncited_blocks(self) -> None:
        out = {"claims_with_citations": [{"claim": "x"}], "repro_steps": ["a"]}
        gate = gate_specialist_output(out, citation_required=True, web_available=True)
        self.assertEqual(gate["status"], "BLOCKED_UNCITED")

    def test_quality_gate_web_unavailable_blocks(self) -> None:
        out = {
            "claims_with_citations": [{"claim": "x", "citation": "local"}],
            "repro_steps": ["a"],
            "needs_web_evidence": True,
        }
        gate = gate_specialist_output(out, citation_required=True, web_available=False)
        self.assertEqual(gate["status"], "BLOCKED_NEEDS_EVIDENCE")

    def test_quality_gate_passes_with_citation(self) -> None:
        out = {
            "claims_with_citations": [{"claim": "x", "citation": "doi:10.1000/x"}],
            "repro_steps": ["step1", "step2"],
        }
        gate = gate_specialist_output(out, citation_required=True, web_available=True)
        self.assertEqual(gate["status"], "PASS")


class FabricIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.project_ids = [
            "proj-test-alpha",
            "proj-test-beta",
            "proj-test-sync",
            "proj-test-visibility",
            "proj-test-hpc",
        ]
        for pid in cls.project_ids:
            project_dir = ROOT / "generated" / "projects" / pid
            if project_dir.exists():
                shutil.rmtree(project_dir)

    @classmethod
    def tearDownClass(cls) -> None:
        for pid in cls.project_ids:
            project_dir = ROOT / "generated" / "projects" / pid
            if project_dir.exists():
                shutil.rmtree(project_dir)
        registry_path = ROOT / "catalog" / "project-registry.yaml"
        if registry_path.exists():
            registry = yaml.safe_load(registry_path.read_text(encoding="utf-8")) or {}
            projects = registry.get("projects", {})
            if isinstance(projects, dict):
                for pid in cls.project_ids:
                    projects.pop(pid, None)
                registry["projects"] = projects
                registry_path.write_text(
                    yaml.safe_dump(registry, sort_keys=False), encoding="utf-8"
                )

    def test_generate_two_projects_with_overlap_unique_skill_ids(self) -> None:
        run_cmd(
            [
                "python3",
                str(SCRIPTS / "new_project_bundle.py"),
                "--project-id",
                "proj-test-alpha",
                "--groups",
                "developer,material-scientist",
                "--force",
            ]
        )
        run_cmd(
            [
                "python3",
                str(SCRIPTS / "new_project_bundle.py"),
                "--project-id",
                "proj-test-beta",
                "--groups",
                "developer,material-scientist",
                "--force",
            ]
        )

        a_manifest = yaml.safe_load(
            (ROOT / "generated" / "projects" / "proj-test-alpha" / "manifest.yaml").read_text(
                encoding="utf-8"
            )
        )
        b_manifest = yaml.safe_load(
            (ROOT / "generated" / "projects" / "proj-test-beta" / "manifest.yaml").read_text(
                encoding="utf-8"
            )
        )

        a_skills = set()
        b_skills = set()
        for payload in a_manifest["groups"].values():
            for rel in payload["skill_dirs"]:
                skill_md = ROOT / "generated" / "projects" / "proj-test-alpha" / rel / "SKILL.md"
                text = skill_md.read_text(encoding="utf-8")
                name = text.split("\n", 3)[1].split(":", 1)[1].strip()
                a_skills.add(name)
        for payload in b_manifest["groups"].values():
            for rel in payload["skill_dirs"]:
                skill_md = ROOT / "generated" / "projects" / "proj-test-beta" / rel / "SKILL.md"
                text = skill_md.read_text(encoding="utf-8")
                name = text.split("\n", 3)[1].split(":", 1)[1].strip()
                b_skills.add(name)

        self.assertFalse(a_skills.intersection(b_skills))

    def test_install_sync_removes_stale_skills(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            target = Path(td)
            run_cmd(
                [
                    "python3",
                    str(SCRIPTS / "new_project_bundle.py"),
                    "--project-id",
                    "proj-test-sync",
                    "--groups",
                    "developer",
                ]
            )
            run_cmd(
                [
                    "python3",
                    str(SCRIPTS / "install_codex_skills.py"),
                    "--project-id",
                    "proj-test-sync",
                    "--target",
                    str(target),
                    "--sync",
                ]
            )
            first_dirs = {p.name for p in target.iterdir() if p.is_dir() and p.name.startswith("proj-proj-test-sync")}
            self.assertTrue(first_dirs)

            run_cmd(
                [
                    "python3",
                    str(SCRIPTS / "new_project_bundle.py"),
                    "--project-id",
                    "proj-test-sync",
                    "--groups",
                    "quality-assurance",
                    "--force",
                ]
            )
            run_cmd(
                [
                    "python3",
                    str(SCRIPTS / "install_codex_skills.py"),
                    "--project-id",
                    "proj-test-sync",
                    "--target",
                    str(target),
                    "--sync",
                ]
            )
            second_dirs = {p.name for p in target.iterdir() if p.is_dir() and p.name.startswith("proj-proj-test-sync")}
            self.assertTrue(second_dirs)
            self.assertNotEqual(first_dirs, second_dirs)

    def test_dispatch_dry_run_deterministic(self) -> None:
        run_cmd(
            [
                "python3",
                str(SCRIPTS / "new_project_bundle.py"),
                "--project-id",
                "proj-test-alpha",
                "--groups",
                "material-scientist",
                "--force",
            ]
        )

        first = run_cmd(
            [
                "python3",
                str(SCRIPTS / "dispatch_dry_run.py"),
                "--project-id",
                "proj-test-alpha",
                "--group",
                "material-scientist",
                "--objective",
                "test objective",
            ]
        )
        second = run_cmd(
            [
                "python3",
                str(SCRIPTS / "dispatch_dry_run.py"),
                "--project-id",
                "proj-test-alpha",
                "--group",
                "material-scientist",
                "--objective",
                "test objective",
            ]
        )
        self.assertEqual(first, second)

    def test_manifest_has_group_only_visibility(self) -> None:
        run_cmd(
            [
                "python3",
                str(SCRIPTS / "new_project_bundle.py"),
                "--project-id",
                "proj-test-visibility",
                "--groups",
                "developer",
                "--force",
            ]
        )
        manifest = yaml.safe_load(
            (ROOT / "generated" / "projects" / "proj-test-visibility" / "manifest.yaml").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(manifest["visibility"]["mode"], "group-only")
        self.assertTrue(manifest["visibility"]["audit_override"])

    def test_dispatch_includes_execution_metadata_for_hpc_group(self) -> None:
        run_cmd(
            [
                "python3",
                str(SCRIPTS / "new_project_bundle.py"),
                "--project-id",
                "proj-test-hpc",
                "--groups",
                "atomistic-hpc-simulation",
                "--force",
            ]
        )
        payload = json.loads(
            run_cmd(
                [
                    "python3",
                    str(SCRIPTS / "dispatch_dry_run.py"),
                    "--project-id",
                    "proj-test-hpc",
                    "--group",
                    "atomistic-hpc-simulation",
                    "--objective",
                    "run hpc test",
                ]
            )
        )
        self.assertEqual(payload["session_mode"], "interactive-separated")
        found_transport = False
        found_scheduler = False
        found_hardware = False
        for phase in payload["phases"]:
            for task in phase["tasks"]:
                if "transport" in task:
                    found_transport = True
                if "scheduler" in task:
                    found_scheduler = True
                if "hardware" in task:
                    found_hardware = True
        self.assertTrue(found_transport and found_scheduler and found_hardware)

    def test_generate_full_docs_reference(self) -> None:
        out = ROOT / "docs" / "generated" / "full-template-skill-reference.md"
        if out.exists():
            out.unlink()
        run_cmd(
            [
                "python3",
                str(SCRIPTS / "generate_docs.py"),
                "--fabric-root",
                str(ROOT),
                "--output",
                str(out),
                "--include-generated-projects",
            ]
        )
        self.assertTrue(out.exists())


class ConcurrencyTests(unittest.TestCase):
    def test_lease_conflict_and_expiry(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            ctl = DirectoryController(root)
            ctl.init()
            ctl.register_agent("a1")
            ctl.register_agent("a2")
            ctl.add_directory("work/slot", shared=False)

            ctl.acquire("a1", "work/slot", ttl_seconds=1)
            with self.assertRaises(RuntimeError):
                ctl.acquire("a2", "work/slot", ttl_seconds=1)

            time.sleep(1.2)
            lease2 = ctl.acquire("a2", "work/slot", ttl_seconds=1)
            self.assertEqual(lease2.agent_id, "a2")


if __name__ == "__main__":
    unittest.main(verbosity=2)
