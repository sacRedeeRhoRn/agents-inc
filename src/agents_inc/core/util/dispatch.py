"""Canonical dispatch planning and gating utilities — single source of truth.

build_dispatch_plan(), gate_specialist_output(), and suggest_groups() were
defined in fabric_lib.py alongside ~1000 lines of unrelated logic.  They live
here so the dispatch concern is self-contained and independently testable.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from agents_inc.core.util.constants import SCHEMA_VERSION
from agents_inc.core.util.errors import FabricError


# ── Internal helpers ───────────────────────────────────────────────────────


def _normalize_dep_entries(depends_on: Any) -> List[dict]:
    if not depends_on:
        return []
    out: List[dict] = []
    if isinstance(depends_on, list):
        for dep in depends_on:
            if isinstance(dep, str) and dep.strip():
                aid = dep.strip()
                out.append(
                    {
                        "agent_id": aid,
                        "required_artifacts": [f"internal/{aid}/handoff.json"],
                        "validate_with": "json-parse",
                        "on_missing": "request-rerun",
                    }
                )
                continue
            if not isinstance(dep, dict):
                continue
            aid = str(dep.get("agent_id") or "").strip()
            if not aid:
                continue
            req = dep.get("required_artifacts")
            required_artifacts = (
                [str(item) for item in req if str(item).strip()]
                if isinstance(req, list)
                else [f"internal/{aid}/handoff.json"]
            )
            validate_with = str(dep.get("validate_with") or "exists")
            on_missing = str(dep.get("on_missing") or "request-rerun")
            out.append(
                {
                    "agent_id": aid,
                    "required_artifacts": required_artifacts,
                    "validate_with": validate_with,
                    "on_missing": on_missing,
                }
            )
    return out


# ── Public API ─────────────────────────────────────────────────────────────


def resolve_task_execution(group_manifest: dict, specialist: dict) -> dict:
    """Merge group-level execution defaults with per-specialist overrides."""
    defaults = group_manifest.get("execution_defaults", {})
    task_exec = specialist.get("execution", {})
    merged = {
        "transport": "local",
        "scheduler": "local",
        "hardware": "cpu",
        "requires_gpu": False,
        "web_search_enabled": True,
    }
    if isinstance(defaults, dict):
        if "web_search_enabled" in defaults:
            merged["web_search_enabled"] = bool(defaults["web_search_enabled"])
        if defaults.get("remote_transport") == "ssh":
            merged["transport"] = "ssh"
        schedulers = defaults.get("schedulers", [])
        if isinstance(schedulers, list) and schedulers:
            merged["scheduler"] = str(schedulers[0])
        hardware = defaults.get("hardware", [])
        if isinstance(hardware, list) and hardware:
            merged["hardware"] = str(hardware[0])
            merged["requires_gpu"] = any(
                "gpu" in str(x).lower() or "cuda" in str(x).lower() for x in hardware
            )

    if isinstance(task_exec, dict):
        if "web_search_enabled" in task_exec:
            merged["web_search_enabled"] = bool(task_exec["web_search_enabled"])
        if task_exec.get("remote_transport"):
            merged["transport"] = str(task_exec["remote_transport"])
        if task_exec.get("scheduler"):
            merged["scheduler"] = str(task_exec["scheduler"])
        if task_exec.get("hardware"):
            merged["hardware"] = str(task_exec["hardware"])
        if "requires_gpu" in task_exec:
            merged["requires_gpu"] = bool(task_exec["requires_gpu"])

    return merged


def build_dispatch_plan(
    project_id: str, group_id: str, objective: str, group_manifest: dict
) -> dict:
    """Build a topologically-sorted dispatch plan for a group's specialists.

    Raises FabricError on cyclic or unsatisfiable dependencies.
    """
    specialists = group_manifest.get("specialists", [])
    if not specialists:
        raise FabricError(f"group '{group_id}' has no specialists")

    spec_map: Dict[str, dict] = {}
    dep_entries_map: Dict[str, List[dict]] = {}
    deps_map: Dict[str, set] = {}
    for specialist in specialists:
        aid = specialist["agent_id"]
        spec_map[aid] = specialist
        dep_entries = _normalize_dep_entries(specialist.get("depends_on", []))
        dep_entries_map[aid] = dep_entries
        deps_map[aid] = {entry["agent_id"] for entry in dep_entries}

    remaining = set(spec_map.keys())
    completed: set = set()
    phases = []
    phase_id = 1

    while remaining:
        ready = sorted([aid for aid in remaining if deps_map[aid].issubset(completed)])
        if not ready:
            blocked = sorted(remaining)
            raise FabricError(
                "cyclic or unsatisfied specialist dependencies in group '{0}': {1}".format(
                    group_id, ", ".join(blocked)
                )
            )

        mode = "parallel" if len(ready) > 1 else "sequential"
        tasks = []
        for aid in ready:
            specialist = spec_map[aid]
            exec_meta = resolve_task_execution(group_manifest, specialist)
            dep_entries = dep_entries_map.get(aid, [])
            tasks.append(
                {
                    "agent_id": aid,
                    "role": specialist.get("role", "domain-core"),
                    "focus": specialist.get("focus", ""),
                    "skill_name": specialist.get(
                        "effective_skill_name", specialist.get("skill_name", "")
                    ),
                    "required_outputs": [
                        str(item)
                        for item in specialist.get("required_outputs", [])
                        if str(item).strip()
                    ],
                    "required_references": [
                        str(item)
                        for item in specialist.get("required_references", [])
                        if str(item).strip()
                    ],
                    "depends_on": sorted(list(deps_map[aid])),
                    "dependency_checks": dep_entries,
                    "workdir": "generated/projects/{0}/work/{1}/{2}".format(
                        project_id, group_id, aid
                    ),
                    "transport": exec_meta["transport"],
                    "scheduler": exec_meta["scheduler"],
                    "hardware": exec_meta["hardware"],
                    "requires_gpu": exec_meta["requires_gpu"],
                    "web_search_enabled": exec_meta["web_search_enabled"],
                }
            )
        phases.append({"phase_id": phase_id, "mode": mode, "tasks": tasks})

        phase_id += 1
        completed.update(ready)
        remaining.difference_update(ready)

    interaction = group_manifest.get("interaction", {})
    session_mode = "interactive-separated"
    if isinstance(interaction, dict) and interaction.get("mode"):
        session_mode = str(interaction["mode"])

    return {
        "project_id": project_id,
        "group_id": group_id,
        "objective": objective,
        "dispatch_mode": "hybrid",
        "session_mode": session_mode,
        "schema_version": SCHEMA_VERSION,
        "head_agent": group_manifest["head"]["agent_id"],
        "head_skill": group_manifest["head"].get(
            "effective_skill_name", group_manifest["head"]["skill_name"]
        ),
        "specialist_output_schema": str(
            group_manifest.get("gate_profile", {}).get(
                "specialist_output_schema", "specialist-handoff-v2"
            )
        ),
        "group_web_search_default": bool(
            group_manifest.get("execution_defaults", {}).get("web_search_enabled", True)
        ),
        "gate_profile": group_manifest.get("gate_profile", {}),
        "phases": phases,
        "quality_gates": group_manifest.get("quality_gates", {}),
    }


def gate_specialist_output(
    output: dict,
    role: str = "",
    citation_required: bool = True,
    web_available: bool = True,
) -> dict:
    """Evaluate a specialist handoff against the framework quality gates.

    Returns ``{"status": "PASS", "reasons": []}`` on success, or a blocked
    status dict with reasons on failure.
    """
    if not isinstance(output, dict):
        return {"status": "BLOCKED_INVALID", "reasons": ["output must be a map"]}

    reasons: List[str] = []

    if citation_required:
        claims = output.get("claims_with_citations", [])
        if not isinstance(claims, list) or not claims:
            reasons.append("missing claims_with_citations")
        else:
            for idx, claim in enumerate(claims):
                citation = None
                if isinstance(claim, dict):
                    citation = claim.get("citation")
                if not citation:
                    reasons.append(f"claim[{idx}] missing citation")

    if output.get("needs_web_evidence") and not web_available:
        reasons.append("required web evidence unavailable")
        return {"status": "BLOCKED_NEEDS_EVIDENCE", "reasons": reasons}

    if output.get("contradictions"):
        reasons.append("internal contradictions detected")

    if output.get("scope_violation"):
        reasons.append("scope violation")

    if not output.get("repro_steps"):
        reasons.append("missing reproducibility steps")

    execution_status = str(output.get("execution_status") or "").strip().upper()
    if execution_status not in {"COMPLETE", "PASS"}:
        reasons.append("missing or invalid execution_status")

    if output.get("dependencies_satisfied") is not True:
        reasons.append("dependencies_satisfied must be true")

    if not isinstance(output.get("produced_artifacts"), list):
        reasons.append("produced_artifacts must be a list")

    if not isinstance(output.get("citations_summary"), dict):
        reasons.append("citations_summary must be a map")

    role_name = str(role or "").strip().lower()
    claims = output.get("claims_with_citations", [])
    normalized_claims = claims if isinstance(claims, list) else []

    if role_name == "web-research":
        web_citation_count = 0
        for claim in normalized_claims:
            if not isinstance(claim, dict):
                continue
            candidates = [claim.get("citation"), claim.get("url"), claim.get("source_url")]
            refs = claim.get("citations")
            if isinstance(refs, list):
                candidates.extend(refs)
            if any(str(item or "").strip().startswith(("http://", "https://")) for item in candidates):
                web_citation_count += 1
        if web_citation_count < 3:
            reasons.append("web-research requires at least 3 web citations")
        if not str(output.get("source_quality_note") or "").strip():
            reasons.append("web-research missing source_quality_note")
    elif role_name == "evidence-review":
        if "contradictions" not in output:
            reasons.append("evidence-review must include contradictions field")
        if not isinstance(output.get("unsupported_claims"), list):
            reasons.append("evidence-review unsupported_claims must be a list")
    elif role_name == "repro-qa":
        repro_commands = output.get("repro_commands")
        if not isinstance(repro_commands, list) or not repro_commands:
            reasons.append("repro-qa requires repro_commands list")
        expected_outputs = output.get("expected_outputs")
        if not isinstance(expected_outputs, list) or not expected_outputs:
            reasons.append("repro-qa requires expected_outputs list")
    elif role_name == "integration":
        if not isinstance(output.get("dependencies_consumed"), list):
            reasons.append("integration dependencies_consumed must be a list")
        if not isinstance(output.get("integration_risks"), list):
            reasons.append("integration integration_risks must be a list")
    elif role_name in {"domain-core", "domain_core", "domain"}:
        has_local_reference = False
        for claim in normalized_claims:
            if not isinstance(claim, dict):
                continue
            citation = str(claim.get("citation") or "").strip()
            if citation.startswith(("local:", "references/", "agent-groups/")):
                has_local_reference = True
                break
        if not has_local_reference:
            reasons.append("domain-core requires at least one local reference citation")

    if reasons:
        blocked_status = (
            "BLOCKED_UNCITED" if any("citation" in r for r in reasons) else "BLOCKED_REVIEW"
        )
        return {"status": blocked_status, "reasons": reasons}

    return {"status": "PASS", "reasons": []}


def suggest_groups(
    task: str, compute: str, remote_cluster: str, output_target: str
) -> Tuple[List[str], List[str]]:
    """Heuristically suggest group IDs based on task keywords.

    Returns (ordered_group_ids, rationale_strings).
    """
    text = " ".join([task.lower(), output_target.lower()])
    selected: List[str] = []
    rationale: List[str] = []

    if any(k in text for k in ["python", "script", "automation", "ssh", "pipeline", "debug"]):
        selected.append("developer")
        rationale.append(
            "Implementation/automation requirements suggest developer group involvement."
        )

    if any(k in text for k in ["quality", "verify", "audit", "consistency", "risk"]):
        selected.append("quality-assurance")
        rationale.append("Explicit verification intent suggests quality assurance group.")

    if any(
        k in text
        for k in [
            "research",
            "reference",
            "citation",
            "evidence",
            "survey",
            "compare",
            "benchmark",
            "literature",
        ]
    ):
        selected.append("literature-intelligence")
        rationale.append("Research/evidence intent suggests literature-intelligence support.")

    if any(
        k in text
        for k in ["data", "dataset", "schema", "etl", "normalization", "metadata", "curation"]
    ):
        selected.append("data-curation")
        rationale.append("Data processing keywords suggest data-curation group support.")

    if any(
        k in text for k in ["integrate", "handoff", "delivery", "deployment", "rollout", "release"]
    ):
        selected.append("integration-delivery")
        rationale.append("Delivery/integration objectives suggest integration-delivery group.")

    if any(
        k in text
        for k in [
            "design",
            "narrative",
            "story",
            "presentation",
            "communication",
            "stakeholder",
            "brief",
        ]
    ):
        selected.append("design-communication")
        rationale.append("Communication and framing goals suggest design-communication group.")

    if remote_cluster.strip().lower() in {"yes", "y", "true", "1"}:
        if "developer" not in selected:
            selected.append("developer")
            rationale.append(
                "Remote cluster workflow requires SSH/automation bridge via developer group."
            )

    if compute.strip().lower() in {"gpu", "cuda"}:
        if "developer" not in selected:
            selected.append("developer")
        if "integration-delivery" not in selected:
            selected.append("integration-delivery")
        rationale.append("GPU/accelerated constraints suggest developer + integration-delivery.")

    if not selected:
        selected = [
            "developer",
            "quality-assurance",
            "literature-intelligence",
            "data-curation",
            "integration-delivery",
            "design-communication",
        ]
        rationale.append("No clear specialty keywords; using balanced domain-agnostic core set.")

    canonical_order = [
        "developer",
        "quality-assurance",
        "data-curation",
        "literature-intelligence",
        "integration-delivery",
        "design-communication",
    ]
    ordered: List[str] = []
    for gid in canonical_order:
        if gid in selected and gid not in ordered:
            ordered.append(gid)
    for gid in selected:
        if gid not in ordered:
            ordered.append(gid)

    return ordered, rationale
