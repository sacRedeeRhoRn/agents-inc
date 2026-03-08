#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import tempfile
import time
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

import yaml

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from agents_inc.core.agent_session_runner import AgentSessionRunner  # noqa: E402
from agents_inc.core.evidence_cache import load_evidence_cache  # noqa: E402
from agents_inc.core.layered_runtime import (  # noqa: E402
    LayeredRuntimeConfig,
    _build_head_prompt,
    _build_specialist_prompt,
    _hydrate_evidence_refs_from_cache,
    _prepare_agent_codex_home,
    _resolve_head_timeout_sec,
    _symlink_or_copy,
    run_layered_runtime,
)


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
                self.assertTrue(bool(cfg.disable_mcp))
                self.assertEqual(cfg.approval_policy, "never")
                self.assertEqual(cfg.sandbox_mode, "workspace-write")
                self.assertEqual(Path(str(cfg.sandbox_cd_dir)), Path(str(cfg.work_dir)))
                self.assertTrue(bool(cfg.sandbox_network_access))
                if str(cfg.session_label).endswith("/web-research-specialist"):
                    self.assertTrue(bool(cfg.web_search))
                else:
                    self.assertFalse(bool(cfg.web_search))
            self.assertEqual(head_runs[0].model, "gpt-5.3-codex")
            self.assertEqual(head_runs[0].model_reasoning_effort, "xhigh")
            self.assertFalse(bool(head_runs[0].disable_mcp))
            self.assertEqual(head_runs[0].approval_policy, "never")
            self.assertEqual(head_runs[0].sandbox_mode, "workspace-write")
            self.assertEqual(
                Path(str(head_runs[0].sandbox_cd_dir)),
                Path(str(head_runs[0].work_dir)),
            )
            self.assertTrue(bool(head_runs[0].sandbox_network_access))

    def test_web_search_policy_all_enabled_applies_to_all_specialists(self) -> None:
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
                project_id="proj-web-policy",
                project_root=project_root,
                project_dir=project_dir,
                turn_dir=turn_dir,
                message="test web-search policy",
                selected_groups=["developer"],
                group_manifests={"developer": deepcopy(group_manifest)},
                web_search_policy="all-enabled",
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
            self.assertGreater(len(specialist_runs), 0)
            self.assertTrue(all(bool(cfg.web_search) for cfg in specialist_runs))

    def test_runtime_emits_heartbeat_and_group_completion_events(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            project_root = root / "project-root"
            project_dir = root / "project-dir"
            turn_dir = root / "turn-001"
            project_root.mkdir(parents=True, exist_ok=True)
            project_dir.mkdir(parents=True, exist_ok=True)
            turn_dir.mkdir(parents=True, exist_ok=True)

            developer_manifest = yaml.safe_load(
                (ROOT / "catalog" / "groups" / "developer.yaml").read_text(encoding="utf-8")
            )
            qa_manifest = yaml.safe_load(
                (ROOT / "catalog" / "groups" / "quality-assurance.yaml").read_text(encoding="utf-8")
            )
            self.assertIsInstance(developer_manifest, dict)
            self.assertIsInstance(qa_manifest, dict)

            events: list[dict] = []

            def _fake_group(*args, **kwargs):  # type: ignore[no-untyped-def]
                group_id = str(args[1])
                time.sleep(1.2)
                return {
                    "status": "COMPLETE",
                    "started_at": "2026-03-03T00:00:00Z",
                    "finished_at": "2026-03-03T00:00:01Z",
                    "error": "",
                    "timed_out_specialists": [],
                    "escalations": [],
                    "specialist_failures": [],
                    "group_id": group_id,
                }

            runtime_config = LayeredRuntimeConfig(
                project_id="proj-heartbeat",
                project_root=project_root,
                project_dir=project_dir,
                turn_dir=turn_dir,
                message="test runtime heartbeat",
                selected_groups=["developer", "quality-assurance"],
                group_manifests={
                    "developer": deepcopy(developer_manifest),
                    "quality-assurance": deepcopy(qa_manifest),
                },
                heartbeat_sec=1,
                max_parallel=2,
                cycle_id=2,
                progress_callback=lambda event: events.append(dict(event)),
            )

            with patch("agents_inc.core.layered_runtime._run_group", side_effect=_fake_group):
                result = run_layered_runtime(runtime_config)

            self.assertFalse(bool(result.get("blocked")))
            event_names = {str(row.get("event")) for row in events if isinstance(row, dict)}
            self.assertIn("runtime_heartbeat", event_names)
            self.assertIn("runtime_group_done", event_names)

    def test_runtime_group_exception_is_blocked_not_crash(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            project_root = root / "project-root"
            project_dir = root / "project-dir"
            turn_dir = root / "turn-001"
            project_root.mkdir(parents=True, exist_ok=True)
            project_dir.mkdir(parents=True, exist_ok=True)
            turn_dir.mkdir(parents=True, exist_ok=True)

            developer_manifest = yaml.safe_load(
                (ROOT / "catalog" / "groups" / "developer.yaml").read_text(encoding="utf-8")
            )
            self.assertIsInstance(developer_manifest, dict)
            runtime_config = LayeredRuntimeConfig(
                project_id="proj-group-exc",
                project_root=project_root,
                project_dir=project_dir,
                turn_dir=turn_dir,
                message="test group exception handling",
                selected_groups=["developer"],
                group_manifests={"developer": deepcopy(developer_manifest)},
            )

            with patch(
                "agents_inc.core.layered_runtime._run_group",
                side_effect=ValueError("'' does not appear to be an IPv4 or IPv6 address"),
            ):
                result = run_layered_runtime(runtime_config)

            self.assertTrue(bool(result.get("blocked")))
            reason_text = "\n".join(str(item) for item in result.get("reasons", []))
            self.assertIn("does not appear to be an IPv4 or IPv6 address", reason_text)

    def test_runtime_specialist_exception_is_blocked_not_crash(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            project_root = root / "project-root"
            project_dir = root / "project-dir"
            turn_dir = root / "turn-001"
            project_root.mkdir(parents=True, exist_ok=True)
            project_dir.mkdir(parents=True, exist_ok=True)
            turn_dir.mkdir(parents=True, exist_ok=True)

            developer_manifest = yaml.safe_load(
                (ROOT / "catalog" / "groups" / "developer.yaml").read_text(encoding="utf-8")
            )
            self.assertIsInstance(developer_manifest, dict)
            runtime_config = LayeredRuntimeConfig(
                project_id="proj-specialist-exc",
                project_root=project_root,
                project_dir=project_dir,
                turn_dir=turn_dir,
                message="test specialist exception handling",
                selected_groups=["developer"],
                group_manifests={"developer": deepcopy(developer_manifest)},
            )

            with patch(
                "agents_inc.core.layered_runtime._run_specialist_with_retries",
                side_effect=ValueError("'' does not appear to be an IPv4 or IPv6 address"),
            ):
                result = run_layered_runtime(runtime_config)

            self.assertTrue(bool(result.get("blocked")))
            reason_text = "\n".join(str(item) for item in result.get("reasons", []))
            self.assertIn("does not appear to be an IPv4 or IPv6 address", reason_text)

    def test_final_gate_failure_soft_passes_specialist_and_group(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            project_root = root / "project-root"
            project_dir = root / "project-dir"
            turn_dir = root / "turn-001"
            project_root.mkdir(parents=True, exist_ok=True)
            project_dir.mkdir(parents=True, exist_ok=True)
            turn_dir.mkdir(parents=True, exist_ok=True)

            developer_manifest = yaml.safe_load(
                (ROOT / "catalog" / "groups" / "developer.yaml").read_text(encoding="utf-8")
            )
            self.assertIsInstance(developer_manifest, dict)

            runtime_config = LayeredRuntimeConfig(
                project_id="proj-soft-gate",
                project_root=project_root,
                project_dir=project_dir,
                turn_dir=turn_dir,
                message="test specialist gate soft pass",
                selected_groups=["developer"],
                group_manifests={"developer": deepcopy(developer_manifest)},
                retry_attempts=0,
                retry_backoff_sec=0,
            )

            def _fake_gate(output, role="", citation_required=True, web_available=True):  # type: ignore[no-untyped-def]
                role_name = str(role).strip().lower()
                if role_name == "web-research":
                    return {
                        "status": "BLOCKED_UNCITED",
                        "reasons": ["web-research requires at least 3 web citations"],
                    }
                return {"status": "PASS", "reasons": []}

            with patch.dict("os.environ", {"AGENTS_INC_BACKEND": "mock"}, clear=False):
                with patch(
                    "agents_inc.core.layered_runtime.gate_specialist_output",
                    side_effect=_fake_gate,
                ):
                    result = run_layered_runtime(runtime_config)

            self.assertFalse(bool(result.get("blocked")))
            group_status = result.get("group_status", {}).get("developer", {})
            self.assertEqual(group_status.get("status"), "COMPLETE")

            sessions_path = Path(str(result.get("specialist_sessions_path") or ""))
            sessions = json.loads(sessions_path.read_text(encoding="utf-8"))
            web_row = sessions.get("developer", {}).get("web-research-specialist", {})
            self.assertEqual(web_row.get("status"), "COMPLETE_WITH_WARNINGS")
            self.assertIn("specialist gate failed", str(web_row.get("error", "")))

            snapshot_handoff = Path(str(web_row.get("snapshot_handoff_path") or ""))
            payload = json.loads(snapshot_handoff.read_text(encoding="utf-8"))
            gate_row = payload.get("quality_gate", {})
            self.assertTrue(bool(isinstance(gate_row, dict) and gate_row.get("soft_pass")))

    def test_runtime_persists_and_reuses_evidence_cache(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            project_root = root / "project-root"
            project_dir = root / "project-dir"
            project_root.mkdir(parents=True, exist_ok=True)
            project_dir.mkdir(parents=True, exist_ok=True)

            developer_manifest = yaml.safe_load(
                (ROOT / "catalog" / "groups" / "developer.yaml").read_text(encoding="utf-8")
            )
            self.assertIsInstance(developer_manifest, dict)

            runtime_config_a = LayeredRuntimeConfig(
                project_id="proj-cache-a",
                project_root=project_root,
                project_dir=project_dir,
                turn_dir=root / "turn-001",
                message="cache warm-up run",
                selected_groups=["developer"],
                group_manifests={"developer": deepcopy(developer_manifest)},
            )
            runtime_config_b = LayeredRuntimeConfig(
                project_id="proj-cache-b",
                project_root=project_root,
                project_dir=project_dir,
                turn_dir=root / "turn-002",
                message="cache reuse run",
                selected_groups=["developer"],
                group_manifests={"developer": deepcopy(developer_manifest)},
            )

            with patch.dict("os.environ", {"AGENTS_INC_BACKEND": "mock"}, clear=False):
                first = run_layered_runtime(runtime_config_a)
                second = run_layered_runtime(runtime_config_b)

            self.assertFalse(bool(first.get("blocked")))
            self.assertFalse(bool(second.get("blocked")))

            cache = load_evidence_cache(project_root)
            entries = cache.get("entries", {})
            self.assertIsInstance(entries, dict)
            self.assertGreater(len(entries), 0)

            hit_counts = [int((row or {}).get("hit_count", 0)) for row in entries.values()]
            self.assertGreaterEqual(max(hit_counts), 2)

            first_id = sorted(entries.keys())[0]
            first_row = entries[first_id]
            self.assertIsInstance(first_row, dict)
            hydrated = _hydrate_evidence_refs_from_cache(
                project_root=project_root,
                payload={
                    "claims": [{"claim": "cached-claim", "evidence_ids": [first_id]}],
                    "evidence_refs": [],
                },
            )
            hydrated_refs = hydrated.get("evidence_refs", [])
            self.assertIsInstance(hydrated_refs, list)
            self.assertGreater(len(hydrated_refs), 0)
            self.assertEqual(str(hydrated_refs[0].get("evidence_id", "")), first_id)
            self.assertEqual(
                str(hydrated_refs[0].get("citation", "")),
                str(first_row.get("citation", "")),
            )

    def test_specialist_prompt_includes_role_specific_requirements(self) -> None:
        base_kwargs = {
            "objective": "test objective",
            "group_id": "developer",
            "specialist_id": "integration-specialist",
            "focus": "integration focus",
            "skill_name": "",
            "dependencies": [],
            "required_outputs": [],
            "required_references": [],
            "required_reference_paths": [],
            "dependency_artifact_paths": [],
            "web_search_enabled": True,
            "artifact_scope": {"work_path": "work.md", "handoff_path": "handoff.json"},
        }
        integration_prompt = _build_specialist_prompt(role="integration", **base_kwargs)
        self.assertIn('"dependencies_consumed": []', integration_prompt)
        self.assertIn('"integration_risks": []', integration_prompt)

        evidence_prompt = _build_specialist_prompt(role="evidence-review", **base_kwargs)
        self.assertIn('"contradictions": false', evidence_prompt)
        self.assertIn('"unsupported_claims": []', evidence_prompt)

        repro_prompt = _build_specialist_prompt(role="repro-qa", **base_kwargs)
        self.assertIn('"repro_commands": ["<exact command>"]', repro_prompt)
        self.assertIn('"expected_outputs": ["<observable output>"]', repro_prompt)

    def test_specialist_prompt_includes_retry_gate_feedback(self) -> None:
        prompt = _build_specialist_prompt(
            objective="test objective",
            group_id="developer",
            specialist_id="integration-specialist",
            role="integration",
            focus="integration focus",
            skill_name="",
            dependencies=[],
            required_outputs=[],
            required_references=[],
            required_reference_paths=[],
            dependency_artifact_paths=[],
            web_search_enabled=True,
            artifact_scope={"work_path": "work.md", "handoff_path": "handoff.json"},
            retry_gate_reasons=[
                "integration dependencies_consumed must be a list",
                "integration integration_risks must be a list",
            ],
        )
        self.assertIn("Retry correction checklist from prior gate failure", prompt)
        self.assertIn("integration dependencies_consumed must be a list", prompt)
        self.assertIn("integration integration_risks must be a list", prompt)

    def test_resolve_head_timeout_sec_scales_and_bounds(self) -> None:
        self.assertEqual(_resolve_head_timeout_sec(0), 0)
        self.assertEqual(_resolve_head_timeout_sec(-1), 0)
        self.assertEqual(_resolve_head_timeout_sec(120), 480)
        self.assertEqual(_resolve_head_timeout_sec(180), 540)
        self.assertEqual(_resolve_head_timeout_sec(900), 1800)

    def test_build_head_prompt_includes_no_web_search_rule(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            handoff = root / "handoff.json"
            handoff.write_text(
                yaml.safe_dump(
                    {
                        "status": "COMPLETE",
                        "dependencies_satisfied": True,
                        "citations_summary": {"count": 1, "has_web_url": True},
                        "claims_with_citations": [
                            {"claim": "Claim A", "citation": "https://example.org/a"}
                        ],
                        "produced_artifacts": ["artifact-a"],
                    },
                    sort_keys=True,
                ),
                encoding="utf-8",
            )

            phase_outputs = {
                "web-research-specialist": type(
                    "Row",
                    (),
                    {"handoff_path": str(handoff)},
                )()
            }
            prompt = _build_head_prompt(
                objective="test",
                group_id="developer",
                dispatch={"head_agent": "head", "head_skill": "dev-head"},
                phase_outputs=phase_outputs,  # type: ignore[arg-type]
                execution_mode="full",
            )
            self.assertIn("Do not perform web searches", prompt)
            self.assertIn("Specialist summaries (canonical)", prompt)
            self.assertIn("Persona contract (canonical)", prompt)
            self.assertIn("web-research-specialist", prompt)
            self.assertIn('"response_status": "ANSWERED"', prompt)
            self.assertIn('"objective_coverage": 0.9', prompt)
            self.assertIn('"persona_stance": "field-proud stance in one line"', prompt)
            self.assertIn('"persona_override_evidence": false', prompt)

    def test_build_head_prompt_light_mode_direct_execution(self) -> None:
        prompt = _build_head_prompt(
            objective="test light mode objective",
            group_id="developer",
            dispatch={
                "head_agent": "head",
                "head_skill": "dev-head",
                "head_task_brief": {"purpose": "build direct answer"},
            },
            phase_outputs={},  # type: ignore[arg-type]
            execution_mode="light",
        )
        self.assertIn("Execute this group objective directly", prompt)
        self.assertIn("Web search is enabled", prompt)
        self.assertIn("Persona contract (canonical)", prompt)
        self.assertIn('"persona_stance": "field-proud stance in one line"', prompt)
        self.assertNotIn("Specialist summaries (canonical)", prompt)

    def test_light_mode_runs_head_only(self) -> None:
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
            skill_root = project_root / ".agents-inc" / "codex-home" / "skills" / "local"
            for skill_name in ["grp-developer-head", "grp-developer-domain-core"]:
                skill_dir = skill_root / skill_name
                skill_dir.mkdir(parents=True, exist_ok=True)
                (skill_dir / "SKILL.md").write_text(
                    f"# {skill_name}\n",
                    encoding="utf-8",
                )
            runtime_config = LayeredRuntimeConfig(
                project_id="proj-light-head-only",
                project_root=project_root,
                project_dir=project_dir,
                turn_dir=turn_dir,
                message="test light mode",
                selected_groups=["developer"],
                group_manifests={"developer": deepcopy(group_manifest)},
                execution_mode="light",
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
            self.assertEqual(len(specialist_runs), 0)
            self.assertEqual(len(head_runs), 1)
            self.assertTrue(bool(head_runs[0].web_search))
            orchestrator_plan = json.loads(
                (turn_dir / "layer2" / "orchestrator-plan.json").read_text(encoding="utf-8")
            )
            self.assertEqual(orchestrator_plan["settings"].get("execution_mode"), "light")
            group_head_sessions = json.loads(
                Path(str(result.get("group_head_sessions_path") or "")).read_text(encoding="utf-8")
            )
            visible_skills = group_head_sessions.get("developer", {}).get("visible_skills", [])
            self.assertIn("grp-developer-head", visible_skills)
            self.assertIn("grp-developer-domain-core", visible_skills)


if __name__ == "__main__":
    unittest.main(verbosity=2)
