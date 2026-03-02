#!/usr/bin/env python3
from __future__ import annotations

import json
import os
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
    FabricError,
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
    def test_router_template_uses_cli_not_hardcoded_script_path(self) -> None:
        template = (
            ROOT
            / "src"
            / "agents_inc"
            / "resources"
            / "templates"
            / "router"
            / "research-router"
            / "SKILL.template.md"
        ).read_text(encoding="utf-8")
        self.assertIn("agents-inc orchestrator-reply", template)
        self.assertNotIn("dispatch_dry_run.py", template)

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
            (ROOT / "catalog" / "groups" / "literature-intelligence.yaml").read_text(
                encoding="utf-8"
            )
        )
        self.assertIsInstance(group_manifest, dict)
        dispatch = build_dispatch_plan(
            "proj-dispatch-meta",
            "literature-intelligence",
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
                    "literature-intelligence,developer,quality-assurance",
                    "--force",
                ],
            ):
                code = new_project_cli.main()
            self.assertEqual(code, 0)

            blocked_turn_dir = Path(td) / "blocked-turn"
            with self.assertRaises(FabricError):
                run_orchestrator_reply(
                    OrchestratorReplyConfig(
                        fabric_root=fabric_root,
                        project_id=project_id,
                        message=(
                            "Design a complete evidence-backed multi-group workflow with "
                            "cross-domain process gates."
                        ),
                        group="auto",
                        output_dir=blocked_turn_dir,
                    )
                )

            self.assertTrue((blocked_turn_dir / "blocked-report.md").exists())
            self.assertTrue((blocked_turn_dir / "blocked-reasons.json").exists())
            self.assertFalse((blocked_turn_dir / "final-exposed-answer.md").exists())

            project_dir = fabric_root / "generated" / "projects" / project_id
            for group_id in ["literature-intelligence", "developer", "quality-assurance"]:
                exposed = project_dir / "agent-groups" / group_id / "exposed"
                (exposed / "summary.md").write_text(
                    f"# Summary\n\n{group_id} published validated handoff outputs.\n",
                    encoding="utf-8",
                )
                (exposed / "INTEGRATION_NOTES.md").write_text(
                    f"# Integration Notes\n\n{group_id} integration checks passed.\n",
                    encoding="utf-8",
                )
                (exposed / "handoff.json").write_text(
                    json.dumps(
                        {
                            "schema_version": "2.0",
                            "status": "PASS",
                            "artifacts": [f"outputs/{group_id}/report.md"],
                            "claims_with_citations": [
                                {
                                    "claim": f"{group_id} claim",
                                    "citation": f"https://example.org/{group_id}",
                                }
                            ],
                        },
                        indent=2,
                        sort_keys=True,
                    )
                    + "\n",
                    encoding="utf-8",
                )

            with patch.dict(os.environ, {"AGENTS_INC_AGENT_RUNNER": "mock"}):
                group_result = run_orchestrator_reply(
                    OrchestratorReplyConfig(
                        fabric_root=fabric_root,
                        project_id=project_id,
                        message=(
                            "Design a complete evidence-backed multi-group workflow with "
                            "cross-domain process gates."
                        ),
                        group="auto",
                        output_dir=Path(td) / "pass-turn",
                    )
                )
            self.assertEqual(group_result["mode"], "group-detailed")
            group_turn_dir = Path(group_result["turn_dir"])
            self.assertTrue((group_turn_dir / "delegation-ledger.json").exists())
            self.assertTrue((group_turn_dir / "negotiation-sequence.md").exists())
            self.assertTrue((group_turn_dir / "group-evidence-index.json").exists())
            self.assertTrue((group_turn_dir / "meeting" / "negotiation-monitor.json").exists())
            self.assertTrue((group_turn_dir / "meeting" / "negotiation-monitor.md").exists())
            self.assertTrue((group_turn_dir / "final-exposed-answer.md").exists())
            self.assertTrue((group_turn_dir / "final" / "full-report.md").exists())
            self.assertTrue((group_turn_dir / "final" / "key-points.txt").exists())
            self.assertTrue(
                (
                    group_turn_dir / "cycles" / "cycle-0001" / "layer2" / "orchestrator-plan.json"
                ).exists()
            )
            self.assertTrue(
                (
                    group_turn_dir / "cycles" / "cycle-0001" / "layer2" / "group-objectives.json"
                ).exists()
            )
            self.assertTrue(
                (
                    group_turn_dir
                    / "cycles"
                    / "cycle-0001"
                    / "layer2"
                    / "refined-group-objectives.json"
                ).exists()
            )
            self.assertTrue(
                (
                    group_turn_dir / "cycles" / "cycle-0001" / "layer3" / "group-head-sessions.json"
                ).exists()
            )
            self.assertTrue(
                (
                    group_turn_dir / "cycles" / "cycle-0001" / "layer4" / "specialist-sessions.json"
                ).exists()
            )
            self.assertTrue(
                (group_turn_dir / "cycles" / "cycle-0001" / "cooperation-ledger.ndjson").exists()
            )
            self.assertTrue((group_turn_dir / "cycles" / "cycle-0001" / "wait-state.json").exists())
            self.assertTrue((group_turn_dir / "wait-state.latest.json").exists())
            self.assertTrue((group_turn_dir / "cooperation-ledger.latest.ndjson").exists())
            self.assertTrue((group_turn_dir / "group-head-sessions.latest.json").exists())
            self.assertTrue((group_turn_dir / "specialist-sessions.latest.json").exists())
            self.assertTrue(bool(group_result["quality"]["passed"]))
            self.assertTrue(bool(group_result["negotiation_monitor"]["passed"]))

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

    def test_group_mode_mock_runner_waits_all_groups(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            fabric_root = Path(td) / "agent_group_fabric"
            ensure_fabric_root_initialized(fabric_root)
            project_id = "proj-runtime-test"
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
                    "literature-intelligence,developer,quality-assurance",
                    "--force",
                ],
            ):
                code = new_project_cli.main()
            self.assertEqual(code, 0)

            with patch.dict(os.environ, {"AGENTS_INC_AGENT_RUNNER": "mock"}):
                result = run_orchestrator_reply(
                    OrchestratorReplyConfig(
                        fabric_root=fabric_root,
                        project_id=project_id,
                        message=(
                            "Build a reusable research orchestration package with clear "
                            "evidence-backed gate checks."
                        ),
                        group="auto",
                        output_dir=Path(td) / "runtime-pass-turn",
                    )
                )

            self.assertEqual(result["mode"], "group-detailed")
            quality = result["quality"]
            self.assertTrue(bool(quality.get("all_active_groups_contributed")))
            self.assertTrue(bool(quality.get("passed")))

            turn_dir = Path(result["turn_dir"])
            wait_state = json.loads(
                (turn_dir / "cycles" / "cycle-0001" / "wait-state.json").read_text(encoding="utf-8")
            )
            self.assertTrue(bool(wait_state.get("all_groups_complete")))
            self.assertEqual(wait_state.get("agent_timeout_mode"), "unlimited")

            orchestrator_plan = json.loads(
                (
                    turn_dir / "cycles" / "cycle-0001" / "layer2" / "orchestrator-plan.json"
                ).read_text(encoding="utf-8")
            )
            self.assertEqual(
                orchestrator_plan.get("settings", {}).get("agent_timeout_mode"), "unlimited"
            )

            specialist_sessions = json.loads(
                (
                    turn_dir / "cycles" / "cycle-0001" / "layer4" / "specialist-sessions.json"
                ).read_text(encoding="utf-8")
            )
            found_mount_status = False
            for group_payload in specialist_sessions.values():
                if not isinstance(group_payload, dict):
                    continue
                for specialist_payload in group_payload.values():
                    if not isinstance(specialist_payload, dict):
                        continue
                    mount_status = specialist_payload.get("mount_status")
                    if isinstance(mount_status, dict):
                        found_mount_status = True
                        self.assertIn("references_source", mount_status)
                        self.assertIn("mode", mount_status)
            self.assertTrue(found_mount_status)

    def test_blocked_payload_includes_timed_out_specialists(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            fabric_root = Path(td) / "agent_group_fabric"
            ensure_fabric_root_initialized(fabric_root)
            project_id = "proj-timeout-block"
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
                    "literature-intelligence,literature-intelligence,data-curation",
                    "--force",
                ],
            ):
                code = new_project_cli.main()
            self.assertEqual(code, 0)

            def _fake_runtime(runtime_config):  # type: ignore[no-untyped-def]
                wait_state = runtime_config.turn_dir / "wait-state.json"
                ledger = runtime_config.turn_dir / "cooperation-ledger.ndjson"
                head_sessions = runtime_config.turn_dir / "layer3" / "group-head-sessions.json"
                specialist_sessions = (
                    runtime_config.turn_dir / "layer4" / "specialist-sessions.json"
                )
                wait_state.parent.mkdir(parents=True, exist_ok=True)
                head_sessions.parent.mkdir(parents=True, exist_ok=True)
                specialist_sessions.parent.mkdir(parents=True, exist_ok=True)
                wait_state.write_text(
                    json.dumps({"all_groups_complete": False}, indent=2) + "\n",
                    encoding="utf-8",
                )
                ledger.write_text("", encoding="utf-8")
                head_sessions.write_text("{}\n", encoding="utf-8")
                specialist_sessions.write_text("{}\n", encoding="utf-8")
                return {
                    "blocked": True,
                    "blocked_groups": ["literature-intelligence"],
                    "reasons": ["simulated timeout block"],
                    "timed_out_specialists": [
                        {
                            "group_id": "literature-intelligence",
                            "specialist_id": "phase-stability-specialist",
                            "attempts": 2,
                            "raw_log_path": str(runtime_config.turn_dir / "raw.log"),
                            "redacted_log_path": str(runtime_config.turn_dir / "redacted.log"),
                        }
                    ],
                    "wait_state_path": str(wait_state),
                    "cooperation_ledger_path": str(ledger),
                    "group_head_sessions_path": str(head_sessions),
                    "specialist_sessions_path": str(specialist_sessions),
                }

            blocked_turn = Path(td) / "blocked-timeout-turn"
            with patch("agents_inc.core.orchestrator_reply.run_layered_runtime", _fake_runtime):
                with self.assertRaises(FabricError):
                    run_orchestrator_reply(
                        OrchestratorReplyConfig(
                            fabric_root=fabric_root,
                            project_id=project_id,
                            message="find exploratory silicide candidates",
                            group="auto",
                            output_dir=blocked_turn,
                            agent_timeout_sec=15,
                        )
                    )

            payload = json.loads(
                (blocked_turn / "blocked-reasons.json").read_text(encoding="utf-8")
            )
            self.assertEqual(payload.get("agent_timeout_mode"), "bounded")
            timed_out = payload.get("timed_out_specialists", [])
            self.assertIsInstance(timed_out, list)
            self.assertEqual(len(timed_out), 1)
            self.assertEqual(timed_out[0].get("specialist_id"), "phase-stability-specialist")

    def test_blocked_payload_includes_escalations(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            fabric_root = Path(td) / "agent_group_fabric"
            ensure_fabric_root_initialized(fabric_root)
            project_id = "proj-escalation-block"
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
                code = new_project_cli.main()
            self.assertEqual(code, 0)

            def _fake_runtime(runtime_config):  # type: ignore[no-untyped-def]
                wait_state = runtime_config.turn_dir / "wait-state.json"
                ledger = runtime_config.turn_dir / "cooperation-ledger.ndjson"
                head_sessions = runtime_config.turn_dir / "layer3" / "group-head-sessions.json"
                specialist_sessions = (
                    runtime_config.turn_dir / "layer4" / "specialist-sessions.json"
                )
                wait_state.parent.mkdir(parents=True, exist_ok=True)
                head_sessions.parent.mkdir(parents=True, exist_ok=True)
                specialist_sessions.parent.mkdir(parents=True, exist_ok=True)
                wait_state.write_text(
                    json.dumps({"all_groups_complete": False}, indent=2) + "\n",
                    encoding="utf-8",
                )
                ledger.write_text("", encoding="utf-8")
                head_sessions.write_text("{}\n", encoding="utf-8")
                specialist_sessions.write_text("{}\n", encoding="utf-8")
                return {
                    "blocked": True,
                    "blocked_groups": ["developer"],
                    "reasons": ["escalation requested"],
                    "timed_out_specialists": [],
                    "escalations": [
                        {
                            "request_id": "req-escalate-1",
                            "type": "ssh_connection",
                            "reason": "Need SSH credentials",
                            "fields_needed": ["host", "user"],
                            "group_id": "developer",
                            "specialist_id": "ssh-remote-ops-expert",
                            "response_path": str(
                                runtime_config.project_dir
                                / "agent-groups"
                                / "developer"
                                / "internal"
                                / "ssh-remote-ops-expert"
                                / "ESCALATION_RESPONSE.json"
                            ),
                        }
                    ],
                    "wait_state_path": str(wait_state),
                    "cooperation_ledger_path": str(ledger),
                    "group_head_sessions_path": str(head_sessions),
                    "specialist_sessions_path": str(specialist_sessions),
                }

            blocked_turn = Path(td) / "blocked-escalation-turn"
            with patch("agents_inc.core.orchestrator_reply.run_layered_runtime", _fake_runtime):
                with self.assertRaises(FabricError):
                    run_orchestrator_reply(
                        OrchestratorReplyConfig(
                            fabric_root=fabric_root,
                            project_id=project_id,
                            message="run remote validation on secured host",
                            group="auto",
                            output_dir=blocked_turn,
                            agent_timeout_sec=15,
                        )
                    )

            payload = json.loads(
                (blocked_turn / "blocked-reasons.json").read_text(encoding="utf-8")
            )
            self.assertEqual(payload.get("status"), "BLOCKED_ESCALATION_REQUIRED")
            escalations = payload.get("escalations", [])
            self.assertIsInstance(escalations, list)
            self.assertEqual(len(escalations), 1)
            self.assertTrue((blocked_turn / "escalations.json").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
