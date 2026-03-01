#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from agents_inc.cli import dispatch_dry_run, orchestrator_reply  # noqa: E402


class CLIProjectResolutionTests(unittest.TestCase):
    def test_orchestrator_reply_resolves_fabric_root_from_index(self) -> None:
        args = argparse.Namespace(
            fabric_root=None,
            project_index="/tmp/index.yaml",
            scan_root="/tmp/projects",
            config_path=None,
        )
        with patch(
            "agents_inc.cli.orchestrator_reply.find_resume_project",
            return_value={"fabric_root": "/tmp/projects/proj-a/agent_group_fabric"},
        ):
            resolved = orchestrator_reply._resolve_project_fabric_root(args, "proj-a")
        self.assertEqual(
            resolved,
            Path("/tmp/projects/proj-a/agent_group_fabric").resolve(),
        )

    def test_dispatch_prefers_explicit_fabric_root(self) -> None:
        args = argparse.Namespace(
            fabric_root="/tmp/explicit-fabric",
            project_index=None,
            scan_root=None,
            config_path=None,
        )
        with patch("agents_inc.cli.dispatch_dry_run.find_resume_project") as mocked:
            resolved = dispatch_dry_run._resolve_project_fabric_root(args, "proj-b")
        self.assertEqual(resolved, Path("/tmp/explicit-fabric").resolve())
        mocked.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
