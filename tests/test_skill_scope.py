#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from typing import Dict, List

import yaml

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


def run_cmd(cmd: List[str], env: Dict[str, str]) -> str:
    proc = subprocess.run(cmd, capture_output=True, text=True, env=env)
    if proc.returncode != 0:
        raise AssertionError(
            "command failed: {0}\nstdout:\n{1}\nstderr:\n{2}".format(
                " ".join(cmd), proc.stdout, proc.stderr
            )
        )
    return proc.stdout


def managed_rows(skills_dir: Path) -> List[dict]:
    rows: List[dict] = []
    if not skills_dir.exists():
        return rows
    for marker in sorted(skills_dir.glob("*/.fabric-managed.json")):
        rows.append(json.loads(marker.read_text(encoding="utf-8")))
    return rows


def seed_home(home_dir: Path) -> None:
    codex_home = home_dir / ".codex"
    codex_home.mkdir(parents=True, exist_ok=True)
    (codex_home / "auth.json").write_text('{"token":"test"}\n', encoding="utf-8")
    (codex_home / "config.toml").write_text('model = "gpt-5"\n', encoding="utf-8")


def init_project(root_dir: Path, project_id: str, groups: str) -> dict:
    home_dir = root_dir / "home"
    projects_root = root_dir / "projects"
    project_root = projects_root / project_id
    project_index = root_dir / "projects-index.yaml"
    seed_home(home_dir)

    env = dict(os.environ)
    env["HOME"] = str(home_dir)

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
            "--groups",
            groups,
            "--task",
            "Film thickness dependent polymorphism stability of metastable phase",
            "--timeline",
            "2 weeks",
            "--compute",
            "cpu",
            "--remote-cluster",
            "no",
            "--output-target",
            "technical report",
            "--project-index",
            str(project_index),
            "--mode",
            "new",
            "--non-interactive",
        ],
        env=env,
    )
    return {
        "env": env,
        "home_dir": home_dir,
        "projects_root": projects_root,
        "project_root": project_root,
        "project_index": project_index,
        "project_id": project_id,
    }


class SkillScopeTests(unittest.TestCase):
    def test_init_uses_project_scoped_codex_home_and_head_only_activation(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            ctx = init_project(Path(td), "proj-scope-init", "developer,material-scientist")
            project_root = Path(ctx["project_root"])
            home_dir = Path(ctx["home_dir"])

            codex_state_path = project_root / ".agents-inc" / "state" / "codex-home.yaml"
            activation_path = project_root / ".agents-inc" / "state" / "skill-activation.yaml"
            self.assertTrue(codex_state_path.exists())
            self.assertTrue(activation_path.exists())

            codex_state = yaml.safe_load(codex_state_path.read_text(encoding="utf-8"))
            activation = yaml.safe_load(activation_path.read_text(encoding="utf-8"))
            self.assertEqual(codex_state["skill_scope"], "project-strict")
            self.assertEqual(codex_state["project_id"], "proj-scope-init")
            self.assertEqual(
                Path(str(codex_state["codex_home"])).resolve(),
                (project_root / ".agents-inc" / "codex-home").resolve(),
            )
            self.assertEqual(activation["active_specialist_groups"], [])
            self.assertEqual(
                activation["active_head_groups"],
                ["developer", "material-scientist"],
            )

            project_skill_dir = project_root / ".agents-inc" / "codex-home" / "skills" / "local"
            rows = managed_rows(project_skill_dir)
            self.assertTrue(rows)
            self.assertTrue(all(row.get("role") == "head" for row in rows))

            global_skill_dir = home_dir / ".codex" / "skills" / "local"
            self.assertFalse(global_skill_dir.exists())

    def test_skills_activate_specialists_for_selected_group_only(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            ctx = init_project(Path(td), "proj-scope-activate", "developer,material-scientist")
            project_root = Path(ctx["project_root"])
            project_index = Path(ctx["project_index"])
            projects_root = Path(ctx["projects_root"])
            env = dict(ctx["env"])

            run_cmd(
                [
                    "python3",
                    str(SCRIPTS / "skills.py"),
                    "activate",
                    "--project-id",
                    "proj-scope-activate",
                    "--groups",
                    "developer",
                    "--specialists",
                    "--project-index",
                    str(project_index),
                    "--scan-root",
                    str(projects_root),
                ],
                env=env,
            )

            activation_path = project_root / ".agents-inc" / "state" / "skill-activation.yaml"
            activation = yaml.safe_load(activation_path.read_text(encoding="utf-8"))
            self.assertEqual(
                activation["active_head_groups"],
                ["developer", "material-scientist"],
            )
            self.assertEqual(activation["active_specialist_groups"], ["developer"])

            rows = managed_rows(project_root / ".agents-inc" / "codex-home" / "skills" / "local")
            specialist_rows = [row for row in rows if row.get("role") == "specialist"]
            self.assertTrue(specialist_rows)
            self.assertTrue(all(row.get("group_id") == "developer" for row in specialist_rows))
            self.assertFalse(
                any(
                    row.get("group_id") == "material-scientist" and row.get("role") == "specialist"
                    for row in rows
                )
            )

    def test_skills_deactivate_removes_selected_group_managed_skills(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            ctx = init_project(Path(td), "proj-scope-deactivate", "developer,material-scientist")
            project_root = Path(ctx["project_root"])
            project_index = Path(ctx["project_index"])
            projects_root = Path(ctx["projects_root"])
            env = dict(ctx["env"])

            run_cmd(
                [
                    "python3",
                    str(SCRIPTS / "skills.py"),
                    "activate",
                    "--project-id",
                    "proj-scope-deactivate",
                    "--groups",
                    "developer",
                    "--specialists",
                    "--project-index",
                    str(project_index),
                    "--scan-root",
                    str(projects_root),
                ],
                env=env,
            )
            run_cmd(
                [
                    "python3",
                    str(SCRIPTS / "skills.py"),
                    "deactivate",
                    "--project-id",
                    "proj-scope-deactivate",
                    "--groups",
                    "developer",
                    "--project-index",
                    str(project_index),
                    "--scan-root",
                    str(projects_root),
                ],
                env=env,
            )

            activation_path = project_root / ".agents-inc" / "state" / "skill-activation.yaml"
            activation = yaml.safe_load(activation_path.read_text(encoding="utf-8"))
            self.assertEqual(activation["active_head_groups"], ["material-scientist"])
            self.assertEqual(activation["active_specialist_groups"], [])

            rows = managed_rows(project_root / ".agents-inc" / "codex-home" / "skills" / "local")
            self.assertFalse(any(row.get("group_id") == "developer" for row in rows))
            self.assertTrue(
                any(
                    row.get("group_id") == "material-scientist" and row.get("role") == "head"
                    for row in rows
                )
            )

    def test_cleanup_global_removes_only_managed_entries(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "skills" / "local"
            managed = target / "managed-skill"
            custom = target / "custom-skill"
            managed.mkdir(parents=True, exist_ok=True)
            custom.mkdir(parents=True, exist_ok=True)
            (managed / ".fabric-managed.json").write_text(
                json.dumps({"project_id": "proj-test", "group_id": "developer"}),
                encoding="utf-8",
            )
            (custom / "SKILL.md").write_text("# custom\n", encoding="utf-8")

            run_cmd(
                [
                    "python3",
                    str(SCRIPTS / "skills.py"),
                    "cleanup-global",
                    "--target",
                    str(target),
                    "--apply",
                ],
                env=dict(os.environ),
            )

            self.assertFalse(managed.exists())
            self.assertTrue(custom.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
