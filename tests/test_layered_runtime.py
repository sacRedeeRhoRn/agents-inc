#!/usr/bin/env python3
from __future__ import annotations

import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

import yaml

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from agents_inc.core.layered_runtime import (  # noqa: E402
    LayeredRuntimeConfig,
    _prepare_agent_codex_home,
    _symlink_or_copy,
    run_layered_runtime,
)
from agents_inc.core.agent_session_runner import AgentSessionRunner  # noqa: E402


class LayeredRuntimeMountTests(unittest.TestCase):
    def test_prepare_agent_codex_home_mounts_group_references(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            project_root = root / "project-root"
            project_dir = root / "project-dir"
            source_skill = (
                project_root / ".agents-inc" / "codex-home" / "skills" / "local" / "skill-a"
            )
            source_skill.mkdir(parents=True, exist_ok=True)
            (source_skill / "SKILL.md").write_text("# skill-a\n", encoding="utf-8")
            refs = project_dir / "agent-groups" / "group-a" / "references"
            refs.mkdir(parents=True, exist_ok=True)
            (refs / "doc.md").write_text("ref\n", encoding="utf-8")

            config = LayeredRuntimeConfig(
                project_id="proj-a",
                project_root=project_root,
                project_dir=project_dir,
                turn_dir=root / "turn",
                message="test",
                selected_groups=["group-a"],
                group_manifests={},
            )
            agent_home, visible, missing, mount_status = _prepare_agent_codex_home(
                config=config,
                runtime_dir=root / "runtime" / "group-a" / "specialist-a",
                group_id="group-a",
                allowed_skill_names=["skill-a"],
            )
            self.assertEqual(visible, ["skill-a"])
            self.assertEqual(missing, [])
            self.assertTrue(bool(mount_status.get("references_available")))
            self.assertEqual(int(mount_status.get("mounted_skill_count", 0)), 1)
            mounted_ref = agent_home / "skills" / "local" / "skill-a" / "references" / "doc.md"
            self.assertTrue(mounted_ref.exists())

    def test_symlink_or_copy_falls_back_to_copy(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            src = root / "src-dir"
            dst = root / "dst-dir"
            src.mkdir(parents=True, exist_ok=True)
            (src / "a.txt").write_text("x\n", encoding="utf-8")
            with patch.object(Path, "symlink_to", side_effect=OSError("symlink blocked")):
                _symlink_or_copy(src, dst)
            self.assertTrue((dst / "a.txt").exists())
            self.assertFalse(dst.is_symlink())

    def test_role_model_profile_propagates_to_agent_runs(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            project_root = root / "project-root"
            project_dir = root / "project-dir"
            turn_dir = root / "turn-001"
            project_root.mkdir(parents=True, exist_ok=True)
            project_dir.mkdir(parents=True, exist_ok=True)
            turn_dir.mkdir(parents=True, exist_ok=True)

            group_manifest = yaml.safe_load(
                (ROOT / "catalog" / "groups" / "developer.yaml").read_text(encoding="utf-8")
            )
            self.assertIsInstance(group_manifest, dict)
            runtime_config = LayeredRuntimeConfig(
                project_id="proj-model-prop",
                project_root=project_root,
                project_dir=project_dir,
                turn_dir=turn_dir,
                message="test role model profile",
                selected_groups=["developer"],
                group_manifests={"developer": deepcopy(group_manifest)},
                specialist_model="gpt-5.3-codex-spark",
                specialist_reasoning_effort=None,
                head_model="gpt-5.3-codex",
                head_reasoning_effort="xhigh",
            )

            captured = []
            original_run = AgentSessionRunner.run

            def _capture_run(self, config):  # type: ignore[no-untyped-def]
                captured.append(config)
                return original_run(self, config)

            with patch.dict("os.environ", {"AGENTS_INC_BACKEND": "mock"}, clear=False):
                with patch.object(AgentSessionRunner, "run", _capture_run):
                    result = run_layered_runtime(runtime_config)

            self.assertFalse(bool(result.get("blocked")))
            specialist_runs = [cfg for cfg in captured if "/head" not in str(cfg.session_label)]
            head_runs = [cfg for cfg in captured if "/head" in str(cfg.session_label)]
            self.assertGreater(len(specialist_runs), 0)
            self.assertEqual(len(head_runs), 1)
            for cfg in specialist_runs:
                self.assertEqual(cfg.model, "gpt-5.3-codex-spark")
                self.assertIsNone(cfg.model_reasoning_effort)
            self.assertEqual(head_runs[0].model, "gpt-5.3-codex")
            self.assertEqual(head_runs[0].model_reasoning_effort, "xhigh")


if __name__ == "__main__":
    unittest.main(verbosity=2)
