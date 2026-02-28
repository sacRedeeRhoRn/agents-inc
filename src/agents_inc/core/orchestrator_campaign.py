from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from agents_inc.core.fabric_lib import (
    FabricError,
    dump_yaml,
    ensure_group_shape,
    load_group_catalog,
    load_yaml,
    now_iso,
    slugify,
    suggest_groups,
    write_text,
)
from agents_inc.core.orchestrator_reply import OrchestratorReplyConfig, run_orchestrator_reply
from agents_inc.core.task_intake_qa import (
    answer_questions,
    build_question_bank,
    gather_web_evidence,
    render_complete_film_plan,
    render_qa_transcript,
    write_qa_bundle,
)
from agents_inc.core.transcript_capture import (
    capture_with_script,
    extract_final_plan_block,
    redact_log,
    write_command_log,
)

RECOMMENDED_GROUPS = [
    "polymorphism-researcher",
    "literature-intelligence",
    "data-curation",
    "material-scientist",
    "developer",
    "quality-assurance",
    "designer",
]


@dataclass
class OrchestratorConfig:
    fabric_root: Path
    project_id: str
    task: str
    create_group: Optional[str]
    group_selection: str
    groups: Optional[list[str]]
    questions_min: int
    self_qa: str
    live_codex: bool
    report_root: Path
    until_pass: bool
    timeline: str
    compute: str
    remote_cluster: str
    output_target: str
    projects_root: Optional[Path]
    long_run_duration_min: int
    codex_timeout_sec: int
    allow_live_fallback: bool
    codex_web_search: bool
    seed: int


def _timestamp_slug() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def _catalog_paths(fabric_root: Path, group_id: str) -> list[Path]:
    return [
        fabric_root / "catalog" / "groups" / f"{group_id}.yaml",
        fabric_root
        / "src"
        / "agents_inc"
        / "resources"
        / "catalog"
        / "groups"
        / f"{group_id}.yaml",
    ]


def _dep(agent_id: str) -> dict:
    return {
        "agent_id": agent_id,
        "required_artifacts": [f"internal/{agent_id}/handoff.json"],
        "validate_with": "json-parse",
        "on_missing": "request-rerun",
    }


def _polymorphism_manifest() -> dict:
    specialists = [
        {
            "agent_id": "phase-stability-specialist",
            "skill_name": "grp-polymorphism-researcher-phase-stability",
            "role": "domain-core",
            "focus": "Film-thickness-dependent polymorph stability and phase competition analysis.",
            "required_references": ["references/phase-stability-core.md"],
            "required_outputs": ["work.md", "handoff.json"],
            "contract": {
                "inputs": ["objective.md", "group-context.json"],
                "outputs": ["work.md", "handoff.json"],
                "output_schema": "specialist-handoff-v2",
            },
            "depends_on": [],
            "execution": {
                "remote_transport": "local",
                "scheduler": "local",
                "hardware": "cpu",
                "requires_gpu": False,
            },
        },
        {
            "agent_id": "dft-electronic-structure-specialist",
            "skill_name": "grp-polymorphism-researcher-dft-electronic-structure",
            "role": "domain-core",
            "focus": "DFT electronic structure and SOC-enabled topological indicator workflow.",
            "required_references": ["references/dft-electronic-structure-core.md"],
            "required_outputs": ["work.md", "handoff.json"],
            "contract": {
                "inputs": ["objective.md", "group-context.json"],
                "outputs": ["work.md", "handoff.json"],
                "output_schema": "specialist-handoff-v2",
            },
            "depends_on": [_dep("phase-stability-specialist")],
            "execution": {
                "remote_transport": "ssh",
                "scheduler": "slurm",
                "hardware": "cuda",
                "requires_gpu": True,
            },
        },
        {
            "agent_id": "md-kinetics-specialist",
            "skill_name": "grp-polymorphism-researcher-md-kinetics",
            "role": "domain-core",
            "focus": "MD-based kinetic stability, interface evolution, and thermal trajectory analysis.",
            "required_references": ["references/md-kinetics-core.md"],
            "required_outputs": ["work.md", "handoff.json"],
            "contract": {
                "inputs": ["objective.md", "group-context.json"],
                "outputs": ["work.md", "handoff.json"],
                "output_schema": "specialist-handoff-v2",
            },
            "depends_on": [_dep("phase-stability-specialist")],
            "execution": {
                "remote_transport": "ssh",
                "scheduler": "slurm",
                "hardware": "cuda",
                "requires_gpu": True,
            },
        },
        {
            "agent_id": "fem-process-specialist",
            "skill_name": "grp-polymorphism-researcher-fem-process",
            "role": "domain-core",
            "focus": "FEM process-window, stress-thermal coupling, and diffusion sensitivity modeling.",
            "required_references": ["references/fem-process-core.md"],
            "required_outputs": ["work.md", "handoff.json"],
            "contract": {
                "inputs": ["objective.md", "group-context.json"],
                "outputs": ["work.md", "handoff.json"],
                "output_schema": "specialist-handoff-v2",
            },
            "depends_on": [_dep("phase-stability-specialist")],
            "execution": {
                "remote_transport": "local",
                "scheduler": "local",
                "hardware": "cpu",
                "requires_gpu": False,
            },
        },
        {
            "agent_id": "web-experimental-data-specialist",
            "skill_name": "grp-polymorphism-researcher-web-experimental-data",
            "role": "web-research",
            "focus": "Gather web-published experimental cobalt-silicide film data with citation-quality summaries.",
            "required_references": ["references/web-experimental-data-core.md"],
            "required_outputs": ["work.md", "handoff.json"],
            "contract": {
                "inputs": ["objective.md", "group-context.json"],
                "outputs": ["work.md", "handoff.json"],
                "output_schema": "specialist-handoff-v2",
            },
            "depends_on": [],
            "execution": {
                "remote_transport": "local",
                "scheduler": "local",
                "hardware": "cpu",
                "requires_gpu": False,
            },
        },
        {
            "agent_id": "integration-specialist",
            "skill_name": "grp-polymorphism-researcher-integration",
            "role": "integration",
            "focus": "Cross-specialist handoff integration and consumability verification.",
            "required_references": ["references/integration-core.md"],
            "required_outputs": ["work.md", "handoff.json"],
            "contract": {
                "inputs": ["objective.md", "group-context.json"],
                "outputs": ["work.md", "handoff.json"],
                "output_schema": "specialist-handoff-v2",
            },
            "depends_on": [
                _dep("phase-stability-specialist"),
                _dep("dft-electronic-structure-specialist"),
                _dep("md-kinetics-specialist"),
                _dep("fem-process-specialist"),
                _dep("web-experimental-data-specialist"),
            ],
            "execution": {
                "remote_transport": "local",
                "scheduler": "local",
                "hardware": "cpu",
                "requires_gpu": False,
            },
        },
        {
            "agent_id": "evidence-review-specialist",
            "skill_name": "grp-polymorphism-researcher-evidence-review",
            "role": "evidence-review",
            "focus": "Claim-level evidence adequacy review for synthesis and simulation recommendations.",
            "required_references": ["references/evidence-review-core.md"],
            "required_outputs": ["work.md", "handoff.json"],
            "contract": {
                "inputs": ["objective.md", "group-context.json"],
                "outputs": ["work.md", "handoff.json"],
                "output_schema": "specialist-handoff-v2",
            },
            "depends_on": [
                _dep("web-experimental-data-specialist"),
                _dep("integration-specialist"),
            ],
            "execution": {
                "remote_transport": "local",
                "scheduler": "local",
                "hardware": "cpu",
                "requires_gpu": False,
            },
        },
        {
            "agent_id": "repro-qa-specialist",
            "skill_name": "grp-polymorphism-researcher-repro-qa",
            "role": "repro-qa",
            "focus": "Reproducibility checklist and cross-run QA for procedure and package outputs.",
            "required_references": ["references/repro-qa-core.md"],
            "required_outputs": ["work.md", "handoff.json"],
            "contract": {
                "inputs": ["objective.md", "group-context.json"],
                "outputs": ["work.md", "handoff.json"],
                "output_schema": "specialist-handoff-v2",
            },
            "depends_on": [
                _dep("integration-specialist"),
                _dep("evidence-review-specialist"),
            ],
            "execution": {
                "remote_transport": "local",
                "scheduler": "local",
                "hardware": "cpu",
                "requires_gpu": False,
            },
        },
    ]
    return {
        "schema_version": "2.0",
        "group_id": "polymorphism-researcher",
        "display_name": "Polymorphism Researcher Group",
        "template_version": "2.0.0",
        "domain": "metastable-thin-film-polymorphism",
        "purpose": "Design and validate thin-film polymorphism synthesis procedures with DFT/MD/FEM support.",
        "success_criteria": [
            "Synthesis path with measurable low-resistivity targets",
            "Cross-validated DFT/MD/FEM computational plan",
            "Evidence-backed and reproducible exposed deliverables",
        ],
        "head": {
            "agent_id": "polymorphism-researcher-head",
            "skill_name": "grp-polymorphism-researcher-head",
            "mission": "Route and quality-gate polymorphism synthesis and compute specialists.",
            "publish_contract": {
                "exposed_required": ["summary.md", "handoff.json", "INTEGRATION_NOTES.md"],
                "visibility": "group-only",
            },
        },
        "specialists": specialists,
        "required_artifacts": {
            "objective_types": {
                "default": {
                    "specialist_internal": [
                        "internal/<agent-id>/work.md",
                        "internal/<agent-id>/handoff.json",
                    ],
                    "head_exposed": [
                        "exposed/summary.md",
                        "exposed/handoff.json",
                        "exposed/INTEGRATION_NOTES.md",
                    ],
                }
            }
        },
        "gate_profile": {
            "profile_id": "polymorphism-evidence-v2",
            "specialist_output_schema": "specialist-handoff-v2",
            "checks": {
                "web_citations_required": True,
                "repro_command_required": True,
                "consistency_required": True,
                "scope_enforced": True,
            },
        },
        "tool_profile": "science-default",
        "default_workdirs": ["inputs", "analysis", "outputs"],
        "quality_gates": {
            "citation_required": True,
            "unresolved_claims_block": True,
            "peer_check_required": True,
            "consistency_required": True,
            "scope_required": True,
            "reproducibility_required": True,
        },
        "interaction": {"mode": "interactive-separated", "linked_groups": ["developer"]},
        "execution_defaults": {
            "web_search_enabled": True,
            "remote_transport": "ssh",
            "schedulers": ["pbs", "slurm", "local"],
            "hardware": ["cpu", "cuda"],
        },
    }


def _create_or_update_polymorphism_group(fabric_root: Path) -> list[str]:
    manifest = _polymorphism_manifest()
    changed: list[str] = []
    for path in _catalog_paths(fabric_root, "polymorphism-researcher"):
        path.parent.mkdir(parents=True, exist_ok=True)
        existing = None
        if path.exists():
            existing = load_yaml(path)
        if existing != manifest:
            dump_yaml(path, manifest)
            changed.append(str(path))
    return changed


def _default_web_specialist(group_id: str) -> dict:
    return {
        "agent_id": "web-research-specialist",
        "skill_name": f"grp-{group_id}-web-research",
        "role": "web-research",
        "focus": "Gather web-published references and extract citation-ready evidence.",
        "required_references": ["references/web-research-core.md"],
        "required_outputs": ["work.md", "handoff.json"],
        "contract": {
            "inputs": ["objective.md", "group-context.json"],
            "outputs": ["work.md", "handoff.json"],
            "output_schema": "specialist-handoff-v2",
        },
        "depends_on": [],
        "execution": {
            "web_search_enabled": True,
            "remote_transport": "local",
            "scheduler": "local",
            "hardware": "cpu",
            "requires_gpu": False,
        },
    }


def enforce_web_research_specialists(fabric_root: Path) -> list[str]:
    changed: list[str] = []
    for base in [
        fabric_root / "catalog" / "groups",
        fabric_root / "src" / "agents_inc" / "resources" / "catalog" / "groups",
    ]:
        if not base.exists():
            continue
        for path in sorted(base.glob("*.yaml")):
            data = load_yaml(path)
            if not isinstance(data, dict):
                continue
            updated = False
            execution_defaults = data.get("execution_defaults")
            if not isinstance(execution_defaults, dict):
                execution_defaults = {
                    "web_search_enabled": True,
                    "remote_transport": "local",
                    "schedulers": ["local"],
                    "hardware": ["cpu"],
                }
                data["execution_defaults"] = execution_defaults
                updated = True
            elif "web_search_enabled" not in execution_defaults:
                execution_defaults["web_search_enabled"] = True
                data["execution_defaults"] = execution_defaults
                updated = True
            specialists = data.get("specialists", [])
            if not isinstance(specialists, list):
                continue
            has_web = any(
                isinstance(spec, dict) and str(spec.get("role", "")).strip() == "web-research"
                for spec in specialists
            )
            if has_web and not updated:
                continue
            if not has_web:
                group_id = str(data.get("group_id") or path.stem)
                specialists.append(_default_web_specialist(group_id))
                data["specialists"] = specialists
            data["template_version"] = "2.0.0"
            dump_yaml(path, data)
            changed.append(str(path))
    return changed


def _run_command(
    *,
    name: str,
    command: list[str],
    cwd: Path,
    env: Optional[dict] = None,
    timeout_sec: int = 600,
) -> dict:
    started_at = now_iso()
    proc = subprocess.run(
        command,
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout_sec,
    )
    finished_at = now_iso()
    return {
        "name": name,
        "command": " ".join(command),
        "return_code": int(proc.returncode),
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "started_at": started_at,
        "finished_at": finished_at,
    }


def _parse_json_file(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _recommended_groups(task: str, output_target: str) -> list[str]:
    lowered = task.lower()
    if "polymorphism" in lowered or "cobalt silicide" in lowered:
        return list(RECOMMENDED_GROUPS)
    guessed, _ = suggest_groups(task, "cuda", "yes", output_target)
    ordered: list[str] = []
    for group_id in RECOMMENDED_GROUPS:
        if group_id in guessed and group_id not in ordered:
            ordered.append(group_id)
    for group_id in guessed:
        if group_id not in ordered:
            ordered.append(group_id)
    if "polymorphism-researcher" not in ordered:
        ordered.insert(0, "polymorphism-researcher")
    return ordered


def _validate_group_contracts(fabric_root: Path) -> None:
    groups = load_group_catalog(fabric_root)
    failures: list[str] = []
    for group_id, group in groups.items():
        errors = ensure_group_shape(group, source=f"catalog/groups/{group_id}.yaml")
        if errors:
            failures.extend(errors)
    if failures:
        raise FabricError("group contract validation failed:\n- " + "\n- ".join(failures))


def _evaluate_pass_criteria(
    *,
    selected_groups: list[str],
    answers: list[dict],
    questions_min: int,
    report: dict,
    orchestrator_turn: Optional[dict],
) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if len(answers) < questions_min:
        reasons.append(f"question_count {len(answers)} < required {questions_min}")
    for answer in answers:
        refs = answer.get("evidence_refs", [])
        uncertainty = bool(answer.get("uncertainty", False))
        if (not isinstance(refs, list) or not refs) and not uncertainty:
            reasons.append(f"{answer.get('question_id', '<unknown>')} missing evidence refs")

    exit_code = int(report.get("exit_code", 1))
    if exit_code != 0:
        reasons.append(f"long-run exit_code={exit_code}")
    coverage = float(report.get("interaction", {}).get("coverage_percent", 0.0))
    if coverage < 100.0:
        reasons.append(f"coverage_percent={coverage} < 100")
    isolation_violations = int(report.get("isolation", {}).get("violation_count", 1))
    if isolation_violations != 0:
        reasons.append(f"isolation_violation_count={isolation_violations}")

    matrix = report.get("group_completion_matrix", {})
    if not isinstance(matrix, dict):
        matrix = {}
    for group_id in selected_groups:
        group_stat = matrix.get(group_id)
        if not isinstance(group_stat, dict):
            reasons.append(f"group={group_id} missing completion matrix entry")
            continue
        if int(group_stat.get("head_publications", 0)) < 1:
            reasons.append(f"group={group_id} head_publications < 1")
        if int(group_stat.get("specialist_tasks", 0)) < 1:
            reasons.append(f"group={group_id} specialist_tasks < 1")

    if not isinstance(orchestrator_turn, dict):
        reasons.append("missing orchestrator turn validation result")
    else:
        if str(orchestrator_turn.get("mode", "")) != "group-detailed":
            reasons.append(
                f"orchestrator_turn_mode={orchestrator_turn.get('mode')} != group-detailed"
            )
        delegation_path = Path(str(orchestrator_turn.get("delegation_path", "")))
        if not delegation_path.exists():
            reasons.append("delegation ledger missing")
        else:
            try:
                delegation = json.loads(delegation_path.read_text(encoding="utf-8"))
                groups = delegation.get("groups", [])
                if not isinstance(groups, list) or not groups:
                    reasons.append("delegation ledger has no groups")
            except Exception as exc:  # noqa: BLE001
                reasons.append(f"delegation ledger parse failed: {exc}")

        negotiation_path = Path(str(orchestrator_turn.get("negotiation_path", "")))
        if not negotiation_path.exists():
            reasons.append("negotiation sequence missing")
        quality = orchestrator_turn.get("quality", {})
        if not isinstance(quality, dict):
            reasons.append("orchestrator quality payload missing")
        else:
            if not bool(quality.get("passed")):
                reasons.append("orchestrator final quality gate failed")
            negotiation = quality.get("negotiation", {})
            coverage = 0.0
            if isinstance(negotiation, dict):
                coverage = float(negotiation.get("coverage_percent", 0.0))
            if coverage < 100.0:
                reasons.append(f"negotiation_coverage_percent={coverage} < 100")
    return (len(reasons) == 0), reasons


def _classify_failure(reasons: list[str]) -> str:
    text = " ".join(reasons).lower()
    if "question_count" in text:
        return "question-flow defect"
    if "web-research" in text:
        return "group contract defect"
    if "dispatch" in text:
        return "dispatch topology defect"
    if "isolation" in text:
        return "isolation defect"
    if "blocked" in text or "evidence" in text:
        return "gate/evidence defect"
    if "codex" in text:
        return "codex interaction defect"
    return "unknown defect"


def _copy_if_exists(src: Path, dst: Path) -> None:
    if not src.exists():
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def _write_report(
    *,
    run_dir: Path,
    config: OrchestratorConfig,
    selected_groups: list[str],
    answers: list[dict],
    command_rows: list[dict],
    refinement_rows: list[dict],
    long_report: dict,
    orchestrator_turn: Optional[dict],
    live_redacted_log: Optional[Path],
    complete_plan_path: Optional[Path],
    codex_web_plan_path: Optional[Path],
) -> dict:
    report_json_path = run_dir / "REPORT.json"
    report_md_path = run_dir / "REPORT.md"
    qa_transcript = render_qa_transcript(task=config.task, answers=answers)

    final = {
        "project_id": config.project_id,
        "task": config.task,
        "selected_groups": selected_groups,
        "question_count": len(answers),
        "long_run_exit_code": int(long_report.get("exit_code", 1)),
        "coverage_percent": float(long_report.get("interaction", {}).get("coverage_percent", 0.0)),
        "isolation_violations": int(long_report.get("isolation", {}).get("violation_count", 0)),
        "group_completion_matrix": long_report.get("group_completion_matrix", {}),
        "orchestrator_turn": orchestrator_turn or {},
        "commands_executed": command_rows,
        "refinement_history": refinement_rows,
        "live_session_redacted_log": str(live_redacted_log) if live_redacted_log else "",
        "complete_plan_path": str(complete_plan_path) if complete_plan_path else "",
        "codex_web_plan_path": str(codex_web_plan_path) if codex_web_plan_path else "",
        "run_dir": str(run_dir),
        "generated_at": now_iso(),
    }
    write_text(report_json_path, json.dumps(final, indent=2, sort_keys=True) + "\n")

    matrix = final.get("group_completion_matrix", {})
    lines = [
        "# Orchestrator Evidence Report",
        "",
        f"- project_id: `{config.project_id}`",
        f"- task: {config.task}",
        f"- generated_at: `{final['generated_at']}`",
        f"- run_dir: `{run_dir}`",
        f"- long_run_exit_code: `{final['long_run_exit_code']}`",
        f"- coverage_percent: `{final['coverage_percent']}`",
        f"- isolation_violations: `{final['isolation_violations']}`",
        "",
        "## Active Groups",
    ]
    for group_id in selected_groups:
        lines.append(f"- {group_id}")
    lines.extend(
        [
            "",
            "## Multi-Agent Group Matrix",
            "| Group | Specialist Tasks | Head Publications |",
            "|---|---:|---:|",
        ]
    )
    for group_id in selected_groups:
        row = matrix.get(group_id, {}) if isinstance(matrix, dict) else {}
        lines.append(
            f"| `{group_id}` | {int(row.get('specialist_tasks', 0))} | {int(row.get('head_publications', 0))} |"
        )
    lines.extend(
        [
            "",
            "## Orchestrator Turn",
            f"- mode: `{(orchestrator_turn or {}).get('mode', '')}`",
            f"- turn_dir: `{(orchestrator_turn or {}).get('turn_dir', '')}`",
            f"- final_answer_path: `{(orchestrator_turn or {}).get('final_answer_path', '')}`",
            f"- quality_passed: `{bool(((orchestrator_turn or {}).get('quality') or {}).get('passed', False))}`",
            "",
            "## Router Intake Questions and Answers",
            qa_transcript,
            "",
            "## Refinement History",
        ]
    )
    for row in refinement_rows:
        lines.append(
            f"- iteration `{row.get('iteration')}`: `{row.get('status')}` ({row.get('classification')})"
        )
        for reason in row.get("reasons", []):
            lines.append(f"  - {reason}")
    lines.extend(
        [
            "",
            "## Command Timeline",
            f"See `{run_dir / 'commands.md'}`",
        ]
    )
    if complete_plan_path and complete_plan_path.exists():
        lines.extend(
            [
                "",
                "## Complete Plan Artifact",
                f"- `{complete_plan_path}`",
            ]
        )
    if codex_web_plan_path and codex_web_plan_path.exists():
        lines.extend(
            [
                "",
                "## Codex Web Plan Artifact",
                f"- `{codex_web_plan_path}`",
            ]
        )
    if live_redacted_log and live_redacted_log.exists():
        redacted = live_redacted_log.read_text(encoding="utf-8", errors="replace")
        lines.extend(
            [
                "",
                "## Live Codex Session Transcript (Redacted)",
                "```text",
                redacted.strip(),
                "```",
            ]
        )
    write_text(report_md_path, "\n".join(lines).strip() + "\n")
    return final


def run_orchestrator_campaign(config: OrchestratorConfig) -> dict:
    project_id = slugify(config.project_id)
    run_dir = (
        config.report_root / f"{_timestamp_slug()}-{project_id}-polymorphism-live-orchestrator"
    )
    run_dir.mkdir(parents=True, exist_ok=True)
    qa_dir = run_dir / "qa"
    dispatch_dir = run_dir / "dispatch-plans"
    plan_dir = run_dir / "plan"
    dispatch_dir.mkdir(parents=True, exist_ok=True)
    plan_dir.mkdir(parents=True, exist_ok=True)

    events: list[dict] = []
    command_rows: list[dict] = []
    refinement_rows: list[dict] = []

    run_config = {
        "project_id": project_id,
        "task": config.task,
        "group_selection": config.group_selection,
        "questions_min": config.questions_min,
        "self_qa": config.self_qa,
        "live_codex": config.live_codex,
        "until_pass": config.until_pass,
        "timeline": config.timeline,
        "compute": config.compute,
        "remote_cluster": config.remote_cluster,
        "output_target": config.output_target,
        "long_run_duration_min": config.long_run_duration_min,
        "allow_live_fallback": config.allow_live_fallback,
        "codex_web_search": config.codex_web_search,
        "seed": config.seed,
        "created_at": now_iso(),
    }
    dump_yaml(run_dir / "run-config.yaml", run_config)

    if config.create_group == "polymorphism-researcher":
        changed = _create_or_update_polymorphism_group(config.fabric_root)
        events.append({"event": "create_group", "changed": changed, "at": now_iso()})

    changed = enforce_web_research_specialists(config.fabric_root)
    if changed:
        events.append({"event": "web_role_injection", "changed": changed, "at": now_iso()})
    _validate_group_contracts(config.fabric_root)

    if config.group_selection == "recommended":
        selected_groups = _recommended_groups(config.task, config.output_target)
    elif config.groups:
        selected_groups = [slugify(group_id) for group_id in config.groups if group_id.strip()]
    else:
        selected_groups = _recommended_groups(config.task, config.output_target)

    catalog = load_group_catalog(config.fabric_root)
    unknown = [group_id for group_id in selected_groups if group_id not in catalog]
    if unknown:
        raise FabricError("unknown selected group(s): " + ", ".join(unknown))

    projects_root = config.projects_root or (run_dir / "projects")
    projects_root.mkdir(parents=True, exist_ok=True)
    project_root = projects_root / project_id
    project_root.mkdir(parents=True, exist_ok=True)

    long_report: dict = {}
    orchestrator_turn_report: Optional[dict] = None
    live_raw_log: Optional[Path] = None
    live_redacted_log: Optional[Path] = None
    complete_plan_path: Optional[Path] = None
    codex_web_plan_path: Optional[Path] = None
    answers: list[dict] = []
    live_codex_enabled = bool(config.live_codex)
    live_codex_failure_reason: Optional[str] = None
    iteration = 0
    while True:
        iteration += 1
        iter_dir = run_dir / f"iteration-{iteration:02d}"
        iter_dir.mkdir(parents=True, exist_ok=True)
        events.append({"event": "iteration_start", "iteration": iteration, "at": now_iso()})

        init_cmd = [
            sys.executable,
            "-m",
            "agents_inc.cli.init_session",
            "--fabric-root",
            str(config.fabric_root),
            "--project-root",
            str(project_root),
            "--projects-root",
            str(projects_root),
            "--project-id",
            project_id,
            "--groups",
            ",".join(selected_groups),
            "--task",
            config.task,
            "--timeline",
            config.timeline,
            "--compute",
            config.compute,
            "--remote-cluster",
            config.remote_cluster,
            "--output-target",
            config.output_target,
            "--mode",
            "new",
            "--non-interactive",
            "--overwrite-existing",
        ]
        init_row = _run_command(name="init", command=init_cmd, cwd=config.fabric_root)
        command_rows.append(init_row)
        if init_row["return_code"] != 0:
            raise FabricError(f"init failed: {init_row['stderr']}")

        project_fabric_root = project_root / "agent_group_fabric"
        kickoff_path = project_root / "kickoff.md"
        router_call_path = project_root / "router-call.txt"
        manifest_path = project_root / "project-manifest.yaml"

        questions = build_question_bank(config.questions_min)
        web_evidence = gather_web_evidence(task=config.task)
        answers = answer_questions(
            questions=questions,
            task=config.task,
            artifact_paths=[kickoff_path, router_call_path, manifest_path],
            web_evidence=web_evidence,
            asked_by=config.self_qa,
        )
        write_qa_bundle(
            output_dir=qa_dir,
            task=config.task,
            questions=questions,
            answers=answers,
            web_evidence=web_evidence,
        )

        if live_codex_enabled:
            codex_bin = shutil.which("codex")
            if not codex_bin:
                raise FabricError("codex binary not found while --live-codex is enabled")
            prompt = (
                "You are the research-router head. Use web search only; do not inspect local files. "
                "Produce one response that includes: 12 intake Q/A, synthesis DOE, DFT/MD/FEM workflow, "
                "anticipated resistivity-vs-thickness outcomes, and a web evidence table with at least "
                "6 source URLs and at least 3 experimental data points. If a data point is unavailable, "
                "mark it UNCERTAIN. Output only inside markers:\nBEGIN_FINAL_PLAN\n...\nEND_FINAL_PLAN"
            )
            write_text(run_dir / "session.prompt.md", prompt + "\n")
            live_raw_log = run_dir / "session.raw.log"
            codex_cmd = [codex_bin]
            if config.codex_web_search:
                codex_cmd.append("--search")
            codex_cmd.extend(
                [
                    "exec",
                    "--skip-git-repo-check",
                    "-C",
                    str(project_root),
                    prompt,
                ]
            )
            try:
                capture = capture_with_script(
                    raw_log_path=live_raw_log,
                    command=codex_cmd,
                    cwd=config.fabric_root,
                    env=os.environ.copy(),
                    timeout_sec=config.codex_timeout_sec,
                )
            except subprocess.TimeoutExpired:
                live_codex_failure_reason = "codex interaction timeout"
                command_rows.append(
                    {
                        "name": "live-codex",
                        "command": " ".join(codex_cmd[:-1]) + " <prompt>",
                        "return_code": 124,
                        "stdout": "",
                        "stderr": "live codex step timed out",
                        "started_at": now_iso(),
                        "finished_at": now_iso(),
                    }
                )
                reasons = [live_codex_failure_reason]
                refinement_rows.append(
                    {
                        "iteration": iteration,
                        "status": "fallback" if config.allow_live_fallback else "failed",
                        "classification": _classify_failure(reasons),
                        "reasons": reasons,
                    }
                )
                if config.allow_live_fallback:
                    live_codex_enabled = False
                else:
                    break
                capture = None
            command_rows.append(
                (
                    {
                        "name": "live-codex",
                        "command": " ".join(codex_cmd[:-1]) + " <prompt>",
                        "return_code": int(capture.returncode),
                        "stdout": capture.stdout,
                        "stderr": capture.stderr,
                        "started_at": now_iso(),
                        "finished_at": now_iso(),
                    }
                    if capture is not None
                    else None
                )
            )
            command_rows = [row for row in command_rows if row is not None]
            live_redacted_log = run_dir / "session.redacted.log"
            if live_raw_log.exists() and live_raw_log.stat().st_size > 0:
                redact_log(live_raw_log, live_redacted_log)
                codex_block = extract_final_plan_block(
                    live_raw_log.read_text(encoding="utf-8", errors="replace")
                )
                if codex_block.strip():
                    codex_web_plan_path = plan_dir / "codex-web-plan.md"
                    write_text(codex_web_plan_path, codex_block.strip() + "\n")
            if capture is not None and capture.returncode != 0:
                live_codex_failure_reason = (
                    f"codex interaction failed (return_code={capture.returncode})"
                )
                reasons = [live_codex_failure_reason]
                refinement_rows.append(
                    {
                        "iteration": iteration,
                        "status": "fallback" if config.allow_live_fallback else "failed",
                        "classification": _classify_failure(reasons),
                        "reasons": reasons,
                    }
                )
                if config.allow_live_fallback:
                    live_codex_enabled = False
                else:
                    break

        complete_plan_text = render_complete_film_plan(
            task=config.task,
            selected_groups=selected_groups,
            answers=answers,
            web_evidence=web_evidence,
            codex_web_plan=(
                codex_web_plan_path.read_text(encoding="utf-8", errors="replace")
                if codex_web_plan_path and codex_web_plan_path.exists()
                else ""
            ),
        )
        complete_plan_path = plan_dir / "complete-film-synthesis-plan.md"
        write_text(complete_plan_path, complete_plan_text)

        turn_output_dir = run_dir / "turns" / f"iteration-{iteration:02d}"
        orchestrator_turn_report = run_orchestrator_reply(
            OrchestratorReplyConfig(
                fabric_root=project_fabric_root,
                project_id=project_id,
                message=config.task,
                group="auto",
                output_dir=turn_output_dir,
            )
        )

        for group_id in selected_groups:
            dispatch_json = dispatch_dir / f"{group_id}.json"
            dispatch_cmd = [
                sys.executable,
                "-m",
                "agents_inc.cli.dispatch_dry_run",
                "--fabric-root",
                str(project_fabric_root),
                "--project-id",
                project_id,
                "--group",
                group_id,
                "--objective",
                config.task,
                "--json-out",
                str(dispatch_json),
                "--locking-mode",
                "auto",
            ]
            dispatch_row = _run_command(
                name=f"dispatch-{group_id}",
                command=dispatch_cmd,
                cwd=config.fabric_root,
            )
            command_rows.append(dispatch_row)
            if dispatch_row["return_code"] != 0:
                raise FabricError(f"dispatch failed for {group_id}: {dispatch_row['stderr']}")

        long_dir = run_dir / "long-run" / f"iteration-{iteration:02d}"
        long_cmd = [
            sys.executable,
            "-m",
            "agents_inc.cli.long_run_test",
            "--fabric-root",
            str(project_fabric_root),
            "--project-id",
            project_id,
            "--task",
            config.task,
            "--groups",
            ",".join(selected_groups),
            "--duration-min",
            str(config.long_run_duration_min),
            "--strict-isolation",
            "hard-fail",
            "--run-mode",
            "local-sim",
            "--seed",
            str(config.seed),
            "--output-dir",
            str(long_dir),
        ]
        long_row = _run_command(
            name="long-run", command=long_cmd, cwd=config.fabric_root, timeout_sec=1800
        )
        command_rows.append(long_row)
        long_report = _parse_json_file(long_dir / "final-report.json")
        _copy_if_exists(long_dir / "events.ndjson", run_dir / "events.ndjson")
        _copy_if_exists(long_dir / "access-ledger.ndjson", run_dir / "access-ledger.ndjson")
        _copy_if_exists(long_dir / "lease-events.ndjson", run_dir / "lease-events.ndjson")
        _copy_if_exists(long_dir / "coverage.json", run_dir / "coverage.json")
        write_text(
            run_dir / "group-matrix.json",
            json.dumps(long_report.get("group_completion_matrix", {}), indent=2, sort_keys=True)
            + "\n",
        )

        passed, reasons = _evaluate_pass_criteria(
            selected_groups=selected_groups,
            answers=answers,
            questions_min=config.questions_min,
            report=long_report,
            orchestrator_turn=orchestrator_turn_report,
        )
        if live_codex_failure_reason and not config.allow_live_fallback:
            reasons.append(live_codex_failure_reason)
            passed = False
        refinement_rows.append(
            {
                "iteration": iteration,
                "status": "passed" if passed else "failed",
                "classification": "none" if passed else _classify_failure(reasons),
                "reasons": reasons,
            }
        )
        if passed:
            break
        if not config.until_pass:
            break

    dump_yaml(run_dir / "qa" / "questions.yaml", _parse_yaml_or_empty(qa_dir / "questions.yaml"))
    dump_yaml(run_dir / "qa" / "answers.yaml", _parse_yaml_or_empty(qa_dir / "answers.yaml"))
    write_text(
        run_dir / "qa" / "qa-transcript.md", render_qa_transcript(task=config.task, answers=answers)
    )
    write_command_log(run_dir / "commands.md", command_rows)
    _write_events(run_dir / "events.ndjson", events)
    _write_refinement_history(run_dir / "refinement-history.md", refinement_rows)

    final = _write_report(
        run_dir=run_dir,
        config=config,
        selected_groups=selected_groups,
        answers=answers,
        command_rows=command_rows,
        refinement_rows=refinement_rows,
        long_report=long_report,
        orchestrator_turn=orchestrator_turn_report,
        live_redacted_log=live_redacted_log,
        complete_plan_path=complete_plan_path,
        codex_web_plan_path=codex_web_plan_path,
    )
    return final


def _parse_yaml_or_empty(path: Path) -> dict | list:
    if not path.exists():
        return {}
    data = load_yaml(path)
    return data if isinstance(data, (dict, list)) else {}


def _write_events(path: Path, events: list[dict]) -> None:
    rows = [json.dumps(event, sort_keys=True) for event in events]
    write_text(path, "\n".join(rows) + ("\n" if rows else ""))


def _write_refinement_history(path: Path, rows: list[dict]) -> None:
    lines = ["# Refinement History", ""]
    for row in rows:
        lines.append(
            f"- iteration `{row.get('iteration')}` -> `{row.get('status')}` ({row.get('classification')})"
        )
        for reason in row.get("reasons", []):
            lines.append(f"  - {reason}")
    write_text(path, "\n".join(lines).strip() + "\n")


def render_report_from_run_dir(run_dir: Path) -> dict:
    report_json = run_dir / "REPORT.json"
    if not report_json.exists():
        raise FabricError(f"missing REPORT.json in run dir: {run_dir}")
    report = json.loads(report_json.read_text(encoding="utf-8"))
    report_md = run_dir / "REPORT.md"
    lines = [
        "# Orchestrator Evidence Report (Regenerated)",
        "",
        f"- project_id: `{report.get('project_id', '')}`",
        f"- task: {report.get('task', '')}",
        f"- generated_at: `{now_iso()}`",
        f"- run_dir: `{run_dir}`",
        "",
        "## Summary",
        f"- question_count: `{report.get('question_count', 0)}`",
        f"- coverage_percent: `{report.get('coverage_percent', 0)}`",
        f"- isolation_violations: `{report.get('isolation_violations', 0)}`",
        "",
        "## Existing Detailed Report",
        "The original detailed report is preserved in `REPORT.json` and command/QA artifacts under this run directory.",
    ]
    write_text(report_md, "\n".join(lines).strip() + "\n")
    return report
