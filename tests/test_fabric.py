#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from dataclasses import dataclass
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
try:
    from controller import DirectoryController  # type: ignore  # noqa: E402
except Exception:  # pragma: no cover
    @dataclass
    class _Lease:
        agent_id: str
        directory: str
        expires_at: float


    class DirectoryController:  # Minimal fallback for isolated CI.
        def __init__(self, root: Path) -> None:
            self.root = Path(root)
            self._agents: set[str] = set()
            self._dirs: dict[str, bool] = {}
            self._leases: dict[str, _Lease] = {}

        def init(self) -> None:
            self.root.mkdir(parents=True, exist_ok=True)

        def register_agent(self, agent_id: str) -> None:
            self._agents.add(agent_id)

        def add_directory(self, directory: str, shared: bool = False) -> None:
            self._dirs[directory] = bool(shared)

        def acquire(self, agent_id: str, directory: str, ttl_seconds: int = 60) -> _Lease:
            if agent_id not in self._agents:
                raise RuntimeError(f"unknown agent: {agent_id}")
            if directory not in self._dirs:
                raise RuntimeError(f"unknown directory: {directory}")

            now = time.monotonic()
            current = self._leases.get(directory)
            if current and current.expires_at > now and current.agent_id != agent_id and not self._dirs[directory]:
                raise RuntimeError("lease conflict")

            lease = _Lease(agent_id=agent_id, directory=directory, expires_at=now + ttl_seconds)
            self._leases[directory] = lease
            return lease


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

    def test_init_session_emits_long_run_command_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            project_root = Path(td) / "session-project"
            target_skills = Path(td) / "skills"
            project_index = Path(td) / "projects-index.yaml"
            run_cmd(
                [
                    "python3",
                    str(SCRIPTS / "init_session.py"),
                    "--fabric-root",
                    str(ROOT),
                    "--project-root",
                    str(project_root),
                    "--project-id",
                    "proj-test-intake-longrun",
                    "--task",
                    "Film thickness dependent polymorphism stability of metastable phase",
                    "--timeline",
                    "2 weeks",
                    "--compute",
                    "cuda",
                    "--remote-cluster",
                    "yes",
                    "--output-target",
                    "technical report",
                    "--target-skill-dir",
                    str(target_skills),
                    "--project-index",
                    str(project_index),
                    "--mode",
                    "new",
                    "--non-interactive",
                ]
            )

            long_run_cmd = project_root / "long-run-command.sh"
            self.assertTrue(long_run_cmd.exists())
            text = long_run_cmd.read_text(encoding="utf-8")
            self.assertIn("agents-inc long-run", text)
            self.assertIn("--groups all", text)

            self.assertTrue((project_root / ".agents-inc" / "state" / "session-state.yaml").exists())
            self.assertTrue((project_root / ".agents-inc" / "state" / "latest-checkpoint.yaml").exists())
            self.assertTrue((project_root / ".agents-inc" / "state" / "latest-compacted.yaml").exists())
            self.assertTrue((project_root / ".agents-inc" / "state" / "group-sessions.yaml").exists())
            self.assertTrue(project_index.exists())

    def test_init_session_new_mode_non_destructive_without_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            project_root = Path(td) / "session-project"
            target_skills = Path(td) / "skills"
            project_index = Path(td) / "projects-index.yaml"
            project_id = "proj-test-intake-nondestructive"

            base_cmd = [
                "python3",
                str(SCRIPTS / "init_session.py"),
                "--fabric-root",
                str(ROOT),
                "--project-root",
                str(project_root),
                "--project-id",
                project_id,
                "--task",
                "Film thickness dependent polymorphism stability of metastable phase",
                "--timeline",
                "2 weeks",
                "--compute",
                "cuda",
                "--remote-cluster",
                "yes",
                "--output-target",
                "technical report",
                "--target-skill-dir",
                str(target_skills),
                "--project-index",
                str(project_index),
                "--mode",
                "new",
                "--non-interactive",
            ]
            run_cmd(base_cmd)

            sentinel = (
                project_root
                / "agent_group_fabric"
                / "generated"
                / "projects"
                / project_id
                / "long-run"
                / "sentinel.txt"
            )
            sentinel.parent.mkdir(parents=True, exist_ok=True)
            sentinel.write_text("keep-me", encoding="utf-8")

            proc = subprocess.run(base_cmd, capture_output=True, text=True)
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("overwrite is disabled", proc.stdout + proc.stderr)
            self.assertTrue(sentinel.exists())

    def test_init_session_resume_preserves_artifacts_and_checkpoint_selection(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            project_root = Path(td) / "session-project"
            target_skills = Path(td) / "skills"
            project_index = Path(td) / "projects-index.yaml"
            project_id = "proj-test-resume-checkpoint"
            task = "Film thickness dependent polymorphism stability of metastable phase"

            run_cmd(
                [
                    "python3",
                    str(SCRIPTS / "init_session.py"),
                    "--fabric-root",
                    str(ROOT),
                    "--project-root",
                    str(project_root),
                    "--project-id",
                    project_id,
                    "--task",
                    task,
                    "--timeline",
                    "2 weeks",
                    "--compute",
                    "cuda",
                    "--remote-cluster",
                    "yes",
                    "--output-target",
                    "technical report",
                    "--target-skill-dir",
                    str(target_skills),
                    "--project-index",
                    str(project_index),
                    "--mode",
                    "new",
                    "--non-interactive",
                ]
            )

            sentinel = (
                project_root
                / "agent_group_fabric"
                / "generated"
                / "projects"
                / project_id
                / "long-run"
                / "resume-sentinel.txt"
            )
            sentinel.parent.mkdir(parents=True, exist_ok=True)
            sentinel.write_text("persist", encoding="utf-8")

            run_cmd(
                [
                    "python3",
                    str(SCRIPTS / "dispatch_dry_run.py"),
                    "--fabric-root",
                    str(project_root / "agent_group_fabric"),
                    "--project-id",
                    project_id,
                    "--group",
                    "material-scientist",
                    "--objective",
                    "resume objective checkpoint test",
                    "--project-index",
                    str(project_index),
                ]
            )

            latest = yaml.safe_load(
                (project_root / ".agents-inc" / "state" / "latest-checkpoint.yaml").read_text(encoding="utf-8")
            )
            checkpoint_id = latest["checkpoint_id"]

            run_cmd(
                [
                    "python3",
                    str(SCRIPTS / "init_session.py"),
                    "--mode",
                    "resume",
                    "--resume-project-id",
                    project_id,
                    "--resume-checkpoint",
                    checkpoint_id,
                    "--project-index",
                    str(project_index),
                    "--non-interactive",
                ]
            )

            self.assertTrue(sentinel.exists())

            router_text = (project_root / "router-call.txt").read_text(encoding="utf-8")
            self.assertIn("resume objective checkpoint test", router_text)

            kickoff_text = (project_root / "kickoff.md").read_text(encoding="utf-8")
            self.assertIn("Kickoff (Resumed)", kickoff_text)
            self.assertIn(checkpoint_id, kickoff_text)

    def test_long_run_after_resume_still_passes(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            project_root = Path(td) / "session-project"
            target_skills = Path(td) / "skills"
            project_index = Path(td) / "projects-index.yaml"
            project_id = "proj-test-resume-longrun"
            task = "Film thickness dependent polymorphism stability of metastable phase"

            run_cmd(
                [
                    "python3",
                    str(SCRIPTS / "init_session.py"),
                    "--fabric-root",
                    str(ROOT),
                    "--project-root",
                    str(project_root),
                    "--project-id",
                    project_id,
                    "--task",
                    task,
                    "--timeline",
                    "2 weeks",
                    "--compute",
                    "cuda",
                    "--remote-cluster",
                    "yes",
                    "--output-target",
                    "technical report",
                    "--target-skill-dir",
                    str(target_skills),
                    "--project-index",
                    str(project_index),
                    "--mode",
                    "new",
                    "--non-interactive",
                ]
            )

            run_cmd(
                [
                    "python3",
                    str(SCRIPTS / "init_session.py"),
                    "--mode",
                    "resume",
                    "--resume-project-id",
                    project_id,
                    "--project-index",
                    str(project_index),
                    "--non-interactive",
                ]
            )

            output_dir = (
                project_root
                / "agent_group_fabric"
                / "generated"
                / "projects"
                / project_id
                / "long-run"
                / "resume-fast-pass"
            )
            proc = subprocess.run(
                [
                    "python3",
                    str(SCRIPTS / "long_run_test.py"),
                    "--fabric-root",
                    str(project_root / "agent_group_fabric"),
                    "--project-id",
                    project_id,
                    "--task",
                    task,
                    "--groups",
                    "all",
                    "--duration-min",
                    "5",
                    "--strict-isolation",
                    "hard-fail",
                    "--run-mode",
                    "local-sim",
                    "--seed",
                    "20260301",
                    "--output-dir",
                    str(output_dir),
                    "--project-index",
                    str(project_index),
                    "--conflict-rate",
                    "0",
                    "--max-retries",
                    "3",
                    "--retry-backoff-ms",
                    "0",
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(proc.returncode, 0, msg=f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}")

            report = json.loads((output_dir / "final-report.json").read_text(encoding="utf-8"))
            self.assertEqual(report["interaction"]["coverage_percent"], 100.0)
            self.assertEqual(report["isolation"]["violation_count"], 0)

    def test_list_sessions_cli_lists_created_projects(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            codex_projects_root = Path(td) / "codex-projects"
            project_root = codex_projects_root / "proj-test-list-sessions"
            target_skills = Path(td) / "skills"
            project_index = Path(td) / "projects-index.yaml"

            run_cmd(
                [
                    "python3",
                    str(SCRIPTS / "init_session.py"),
                    "--fabric-root",
                    str(ROOT),
                    "--project-root",
                    str(project_root),
                    "--project-id",
                    "proj-test-list-sessions",
                    "--task",
                    "Film thickness dependent polymorphism stability of metastable phase",
                    "--timeline",
                    "2 weeks",
                    "--compute",
                    "cuda",
                    "--remote-cluster",
                    "yes",
                    "--output-target",
                    "technical report",
                    "--target-skill-dir",
                    str(target_skills),
                    "--project-index",
                    str(project_index),
                    "--mode",
                    "new",
                    "--non-interactive",
                ]
            )

            raw = run_cmd(
                [
                    "python3",
                    str(SCRIPTS / "list_sessions.py"),
                    "--project-index",
                    str(project_index),
                    "--scan-root",
                    str(codex_projects_root),
                    "--json",
                ]
            )
            payload = json.loads(raw)
            self.assertGreaterEqual(payload.get("count", 0), 1)
            ids = {row.get("project_id") for row in payload.get("sessions", [])}
            self.assertIn("proj-test-list-sessions", ids)
            row = next(r for r in payload.get("sessions", []) if r.get("project_id") == "proj-test-list-sessions")
            self.assertTrue(str(row.get("session_code", "")))
            self.assertIn("material-scientist", row.get("active_groups", []))

    def test_resume_cli_auto_falls_back_to_checkpoint_when_compact_missing(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            project_root = Path(td) / "session-project"
            target_skills = Path(td) / "skills"
            project_index = Path(td) / "projects-index.yaml"
            project_id = "proj-test-resume-fallback"
            task = "Film thickness dependent polymorphism stability of metastable phase"

            run_cmd(
                [
                    "python3",
                    str(SCRIPTS / "init_session.py"),
                    "--fabric-root",
                    str(ROOT),
                    "--project-root",
                    str(project_root),
                    "--project-id",
                    project_id,
                    "--task",
                    task,
                    "--timeline",
                    "2 weeks",
                    "--compute",
                    "cuda",
                    "--remote-cluster",
                    "yes",
                    "--output-target",
                    "technical report",
                    "--target-skill-dir",
                    str(target_skills),
                    "--project-index",
                    str(project_index),
                    "--mode",
                    "new",
                    "--non-interactive",
                ]
            )

            compact_root = project_root / ".agents-inc" / "state" / "compacted"
            if compact_root.exists():
                shutil.rmtree(compact_root)
            latest_compact = project_root / ".agents-inc" / "state" / "latest-compacted.yaml"
            if latest_compact.exists():
                latest_compact.unlink()

            proc = subprocess.run(
                [
                    "python3",
                    str(SCRIPTS / "resume.py"),
                    project_id,
                    "--project-index",
                    str(project_index),
                    "--no-launch",
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(proc.returncode, 0, msg=f"stdout:\\n{proc.stdout}\\nstderr:\\n{proc.stderr}")
            self.assertTrue((project_root / "kickoff.md").exists())
            self.assertIn("Kickoff (Resumed)", (project_root / "kickoff.md").read_text(encoding="utf-8"))


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
