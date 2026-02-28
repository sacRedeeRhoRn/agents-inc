#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def run_cmd(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True)


class LongRunUnitTests(unittest.TestCase):
    def test_path_policy_allows_specialist_own_internal_write(self) -> None:
        from agents_inc.core.long_run import evaluate_access

        ok, _ = evaluate_access(
            actor_role="specialist",
            actor_group="g1",
            actor_agent="a1",
            op="write",
            target_rel="agent-groups/g1/internal/a1/result.json",
        )
        self.assertTrue(ok)

    def test_path_policy_denies_cross_group_internal_access(self) -> None:
        from agents_inc.core.long_run import evaluate_access

        ok_read, _ = evaluate_access(
            actor_role="head",
            actor_group="g2",
            actor_agent="head-g2",
            op="read",
            target_rel="agent-groups/g1/internal/a1/result.json",
        )
        ok_write, _ = evaluate_access(
            actor_role="specialist",
            actor_group="g2",
            actor_agent="a2",
            op="write",
            target_rel="agent-groups/g1/internal/a1/other.json",
        )
        self.assertFalse(ok_read)
        self.assertFalse(ok_write)

    def test_path_policy_allows_cross_group_exposed_read(self) -> None:
        from agents_inc.core.long_run import evaluate_access

        ok, _ = evaluate_access(
            actor_role="head",
            actor_group="g2",
            actor_agent="head-g2",
            op="read",
            target_rel="agent-groups/g1/exposed/latest-summary.json",
        )
        self.assertTrue(ok)

    def test_detect_owner_mismatches(self) -> None:
        from agents_inc.core.long_run import detect_owner_mismatches

        mismatches = detect_owner_mismatches(
            changed_paths=[
                "agent-groups/g1/internal/a1/result.json",
                "agent-groups/g1/exposed/latest-summary.json",
            ],
            expected_owner_by_path={
                "agent-groups/g1/internal/a1/result.json": "specialist:g1:a1",
                "agent-groups/g1/exposed/latest-summary.json": "head:g1:head-g1",
            },
            actual_owner_by_path={
                "agent-groups/g1/internal/a1/result.json": "specialist:g1:a1",
                "agent-groups/g1/exposed/latest-summary.json": "specialist:g1:a1",
            },
        )
        self.assertEqual(len(mismatches), 1)
        self.assertEqual(mismatches[0]["path"], "agent-groups/g1/exposed/latest-summary.json")


class LongRunIntegrationTests(unittest.TestCase):
    @staticmethod
    def _remove_tree(path: Path) -> None:
        if not path.exists():
            return
        try:
            shutil.rmtree(path)
            return
        except Exception:
            pass
        for item in sorted(path.rglob("*"), reverse=True):
            try:
                if item.is_file() or item.is_symlink():
                    item.unlink()
                elif item.is_dir():
                    item.rmdir()
            except Exception:
                continue
        try:
            path.rmdir()
        except Exception:
            pass

    @classmethod
    def setUpClass(cls) -> None:
        cls.project_ids = [
            "proj-test-longrun-pass",
            "proj-test-longrun-isolation",
            "proj-test-longrun-deadlock",
            "proj-test-longrun-gate",
            "proj-test-longrun-audit",
            "proj-test-longrun-deterministic",
            "proj-test-longrun-contention",
        ]
        for pid in cls.project_ids:
            project_dir = ROOT / "generated" / "projects" / pid
            cls._remove_tree(project_dir)

    @classmethod
    def tearDownClass(cls) -> None:
        for pid in cls.project_ids:
            project_dir = ROOT / "generated" / "projects" / pid
            cls._remove_tree(project_dir)

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

    def _base_cmd(self, project_id: str, output_dir: Path) -> list[str]:
        return [
            "python3",
            str(SCRIPTS / "long_run_test.py"),
            "--fabric-root",
            str(ROOT),
            "--project-id",
            project_id,
            "--task",
            "Film thickness dependent polymorphism stability of metastable phase",
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
            "--conflict-rate",
            "0",
            "--max-retries",
            "3",
            "--retry-backoff-ms",
            "0",
        ]

    def test_full_group_fast_run_hits_coverage_100(self) -> None:
        output_dir = (
            ROOT / "generated" / "projects" / "proj-test-longrun-pass" / "long-run" / "fast-pass"
        )
        proc = run_cmd(self._base_cmd("proj-test-longrun-pass", output_dir))
        self.assertEqual(proc.returncode, 0, msg=f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}")

        report = json.loads((output_dir / "final-report.json").read_text(encoding="utf-8"))
        self.assertEqual(report["interaction"]["coverage_percent"], 100.0)
        self.assertEqual(report["isolation"]["violation_count"], 0)
        self.assertEqual(len(report["groups"]), 10)

    def test_injected_isolation_violation_returns_code_2(self) -> None:
        output_dir = (
            ROOT
            / "generated"
            / "projects"
            / "proj-test-longrun-isolation"
            / "long-run"
            / "inject-isolation"
        )
        cmd = self._base_cmd("proj-test-longrun-isolation", output_dir) + [
            "--inject-isolation-violation"
        ]
        proc = run_cmd(cmd)
        self.assertEqual(proc.returncode, 2, msg=f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}")

        report = json.loads((output_dir / "final-report.json").read_text(encoding="utf-8"))
        self.assertEqual(report["exit_code"], 2)

    def test_injected_deadlock_returns_code_3(self) -> None:
        output_dir = (
            ROOT
            / "generated"
            / "projects"
            / "proj-test-longrun-deadlock"
            / "long-run"
            / "inject-deadlock"
        )
        cmd = self._base_cmd("proj-test-longrun-deadlock", output_dir) + ["--inject-lease-deadlock"]
        proc = run_cmd(cmd)
        self.assertEqual(proc.returncode, 3, msg=f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}")

        report = json.loads((output_dir / "final-report.json").read_text(encoding="utf-8"))
        self.assertEqual(report["exit_code"], 3)

    def test_injected_gate_exposure_failure_returns_code_5(self) -> None:
        output_dir = (
            ROOT / "generated" / "projects" / "proj-test-longrun-gate" / "long-run" / "inject-gate"
        )
        cmd = self._base_cmd("proj-test-longrun-gate", output_dir) + [
            "--inject-gate-expose-failure"
        ]
        proc = run_cmd(cmd)
        self.assertEqual(proc.returncode, 5, msg=f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}")

        report = json.loads((output_dir / "final-report.json").read_text(encoding="utf-8"))
        self.assertEqual(report["exit_code"], 5)

    def test_audit_mode_preserves_isolation_and_changes_install_behavior(self) -> None:
        output_dir = (
            ROOT / "generated" / "projects" / "proj-test-longrun-audit" / "long-run" / "audit-mode"
        )
        cmd = self._base_cmd("proj-test-longrun-audit", output_dir) + ["--audit"]
        proc = run_cmd(cmd)
        self.assertEqual(proc.returncode, 0, msg=f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}")

        report = json.loads((output_dir / "final-report.json").read_text(encoding="utf-8"))
        self.assertTrue(report["audit_mode"])
        self.assertEqual(report["isolation"]["violation_count"], 0)
        self.assertGreater(report["installed_specialist_skill_count"], 0)

    def test_deterministic_events_with_fixed_seed(self) -> None:
        output_a = (
            ROOT
            / "generated"
            / "projects"
            / "proj-test-longrun-deterministic"
            / "long-run"
            / "run-a"
        )
        output_b = (
            ROOT
            / "generated"
            / "projects"
            / "proj-test-longrun-deterministic"
            / "long-run"
            / "run-b"
        )

        cmd_a = self._base_cmd("proj-test-longrun-deterministic", output_a)
        cmd_b = self._base_cmd("proj-test-longrun-deterministic", output_b)

        proc_a = run_cmd(cmd_a)
        proc_b = run_cmd(cmd_b)
        self.assertEqual(
            proc_a.returncode, 0, msg=f"stdout:\n{proc_a.stdout}\nstderr:\n{proc_a.stderr}"
        )
        self.assertEqual(
            proc_b.returncode, 0, msg=f"stdout:\n{proc_b.stdout}\nstderr:\n{proc_b.stderr}"
        )

        events_a = (output_a / "events.ndjson").read_text(encoding="utf-8")
        events_b = (output_b / "events.ndjson").read_text(encoding="utf-8")
        self.assertEqual(events_a, events_b)

    def test_lease_retry_succeeds_under_injected_contention(self) -> None:
        output_dir = (
            ROOT
            / "generated"
            / "projects"
            / "proj-test-longrun-contention"
            / "long-run"
            / "contention"
        )
        cmd = self._base_cmd("proj-test-longrun-contention", output_dir)
        cmd[cmd.index("--groups") + 1] = "material-scientist"
        cmd[cmd.index("--conflict-rate") + 1] = "1.0"
        cmd[cmd.index("--max-retries") + 1] = "3"
        proc = run_cmd(cmd)
        self.assertEqual(proc.returncode, 0, msg=f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}")

        report = json.loads((output_dir / "final-report.json").read_text(encoding="utf-8"))
        self.assertGreaterEqual(report["lease"]["conflicts"], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
