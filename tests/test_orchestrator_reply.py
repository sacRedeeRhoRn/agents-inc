#!/usr/bin/env python3
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from agents_inc.cli import new_project as new_project_cli  # noqa: E402
from agents_inc.core.fabric_lib import (  # noqa: E402
    build_dispatch_plan,
    ensure_fabric_root_initialized,
)
from agents_inc.core.orchestrator_reply import (  # noqa: E402
    OrchestratorReplyConfig,
    run_orchestrator_reply,
)
from agents_inc.core.response_policy import (  # noqa: E402
    DEFAULT_RESPONSE_POLICY,
    classify_request_mode,
)


class OrchestratorReplyTests(unittest.TestCase):
    def test_mode_parser_uses_strict_prefix(self) -> None:
        self.assertEqual(
            classify_request_mode("[non-group] list sessions", DEFAULT_RESPONSE_POLICY), "non-group"
        )
        self.assertEqual(
            classify_request_mode("please [non-group] list sessions", DEFAULT_RESPONSE_POLICY),
            "group-detailed",
        )

    def test_dispatch_includes_web_search_metadata(self) -> None:
        group_manifest = yaml.safe_load(
            (ROOT / "catalog" / "groups" / "polymorphism-researcher.yaml").read_text(
                encoding="utf-8"
            )
        )
        self.assertIsInstance(group_manifest, dict)
        dispatch = build_dispatch_plan(
            "proj-dispatch-meta",
            "polymorphism-researcher",
            "test objective",
            group_manifest,
        )
        self.assertIn("group_web_search_default", dispatch)
        self.assertTrue(bool(dispatch["group_web_search_default"]))
        for phase in dispatch.get("phases", []):
            for task in phase.get("tasks", []):
                self.assertIn("web_search_enabled", task)

    def test_group_and_non_group_turn_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            fabric_root = Path(td) / "agent_group_fabric"
            ensure_fabric_root_initialized(fabric_root)
            project_id = "proj-reply-test"
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
                    "polymorphism-researcher,developer,quality-assurance",
                    "--force",
                ],
            ):
                code = new_project_cli.main()
            self.assertEqual(code, 0)

            group_result = run_orchestrator_reply(
                OrchestratorReplyConfig(
                    fabric_root=fabric_root,
                    project_id=project_id,
                    message=(
                        "Design a complete low-resistivity cobalt silicide film workflow with DFT, "
                        "MD, FEM, and evidence-backed process gates."
                    ),
                    group="auto",
                )
            )
            self.assertEqual(group_result["mode"], "group-detailed")
            group_turn_dir = Path(group_result["turn_dir"])
            self.assertTrue((group_turn_dir / "delegation-ledger.json").exists())
            self.assertTrue((group_turn_dir / "negotiation-sequence.md").exists())
            self.assertTrue((group_turn_dir / "group-evidence-index.json").exists())
            self.assertTrue((group_turn_dir / "final-exposed-answer.md").exists())
            self.assertTrue(bool(group_result["quality"]["passed"]))

            non_group_result = run_orchestrator_reply(
                OrchestratorReplyConfig(
                    fabric_root=fabric_root,
                    project_id=project_id,
                    message=(
                        "[non-group] Bring session id of web-search specialist of "
                        "polymorphism researcher dangled to current project."
                    ),
                    group="auto",
                )
            )
            self.assertEqual(non_group_result["mode"], "non-group")
            non_group_turn_dir = Path(non_group_result["turn_dir"])
            self.assertFalse((non_group_turn_dir / "delegation-ledger.json").exists())
            answer_text = (non_group_turn_dir / "final-exposed-answer.md").read_text(
                encoding="utf-8"
            )
            self.assertIn("session_code", answer_text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
