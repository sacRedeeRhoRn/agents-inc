from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from agents_inc.core.fabric_lib import (
    FabricError,
    build_dispatch_plan,
    load_yaml,
    slugify,
    stable_json,
    write_text,
)
from agents_inc.core.head_meeting import HeadMeetingConfig, run_head_meeting
from agents_inc.core.layered_runtime import LayeredRuntimeConfig, run_layered_runtime
from agents_inc.core.negotiation_monitor import NegotiationCycleRecord
from agents_inc.core.orchestration import report as orchestration_report
from agents_inc.core.orchestration.cycle_engine import build_cycle_summary
from agents_inc.core.orchestration.meeting import build_negotiation_monitor
from agents_inc.core.orchestration.turn_router import (
    resolve_primary_group as resolve_primary_group_router,
    selected_groups_from_manifest,
)
from agents_inc.core.response_policy import (
    classify_request_mode,
    ensure_response_policy,
    flatten_specialist_sessions,
    lookup_specialist_session,
    strip_non_group_prefix,
    upsert_specialist_sessions,
)
from agents_inc.core.session_state import load_checkpoint, now_iso, resolve_state_project_root
from agents_inc.core.util.edges import resolve_handoff_edges


@dataclass
class OrchestratorReplyConfig:
    fabric_root: Path
    project_id: str
    message: str
    group: str
    output_dir: Optional[Path] = None
    max_parallel: int = 0
    retry_attempts: int = 2
    retry_backoff_sec: int = 5
    agent_timeout_sec: int = 0
    loop_mode: str = "cooperative"
    meeting_enabled: bool = True
    stop_rule: str = "unanimous-head-satisfied"
    max_cycles: int = 4
    heartbeat_sec: int = 30
    abort_file: Optional[Path] = None
    require_negotiation: bool = True
    audit: bool = False


def _turn_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _load_project_bundle(config: OrchestratorReplyConfig) -> Tuple[Path, Path, dict]:
    project_dir = config.fabric_root / "generated" / "projects" / config.project_id
    manifest_path = project_dir / "manifest.yaml"
    if not manifest_path.exists():
        raise FabricError(f"project manifest not found: {manifest_path}")
    manifest = load_yaml(manifest_path)
    if not isinstance(manifest, dict):
        raise FabricError(f"invalid project manifest: {manifest_path}")
    project_root = resolve_state_project_root(config.fabric_root, config.project_id)
    project_root.mkdir(parents=True, exist_ok=True)
    return project_root, project_dir, manifest


def _turn_dir(project_root: Path, output_dir: Optional[Path]) -> Path:
    if output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir
    target = project_root / ".agents-inc" / "turns" / _turn_id()
    target.mkdir(parents=True, exist_ok=True)
    return target


def _selected_groups(manifest: dict) -> List[str]:
    selected = manifest.get("selected_groups")
    if not isinstance(selected, list) or not selected:
        raise FabricError("project manifest missing selected_groups")
    groups: List[str] = []
    for item in selected:
        group_id = str(item).strip()
        if group_id and group_id not in groups:
            groups.append(group_id)
    return groups


def _load_group_manifests(project_dir: Path, manifest: dict, groups: List[str]) -> Dict[str, dict]:
    out: Dict[str, dict] = {}
    group_entries = manifest.get("groups")
    if not isinstance(group_entries, dict):
        raise FabricError("project manifest missing groups map")
    for group_id in groups:
        payload = group_entries.get(group_id)
        if not isinstance(payload, dict):
            raise FabricError(f"group '{group_id}' missing from project manifest")
        rel = str(payload.get("manifest_path") or "").strip()
        if not rel:
            raise FabricError(f"group '{group_id}' has empty manifest_path")
        group_path = project_dir / rel
        group_manifest = load_yaml(group_path)
        if not isinstance(group_manifest, dict):
            raise FabricError(f"invalid group manifest: {group_path}")
        out[group_id] = group_manifest
    return out


def _resolve_primary_group(groups: List[str], requested_group: str) -> str:
    if requested_group and requested_group != "auto":
        if requested_group not in groups:
            raise FabricError(f"group '{requested_group}' is not active in current project")
        return requested_group
    return groups[0]


def _build_group_objective_cards(
    *, base_objective: str, selected_groups: List[str], group_manifests: Dict[str, dict]
) -> Dict[str, str]:
    cards: Dict[str, str] = {}
    for group_id in selected_groups:
        manifest = group_manifests.get(group_id, {})
        purpose = str(manifest.get("purpose") or "").strip()
        head = manifest.get("head")
        mission = ""
        if isinstance(head, dict):
            mission = str(head.get("mission") or "").strip()
        specialists = manifest.get("specialists")
        focus_rows: List[str] = []
        if isinstance(specialists, list):
            for specialist in specialists[:5]:
                if not isinstance(specialist, dict):
                    continue
                role = str(specialist.get("role") or "domain-core").strip()
                focus = str(specialist.get("focus") or "").strip()
                if not focus:
                    continue
                focus_rows.append(f"- {role}: {focus}")
        lines = [
            base_objective.strip(),
            "",
            f"Group: {group_id}",
        ]
        if purpose:
            lines.append(f"Purpose: {purpose}")
        if mission:
            lines.append(f"Head mission: {mission}")
        if focus_rows:
            lines.extend(["", "Specialist priorities:"])
            lines.extend(focus_rows)
        lines.extend(
            [
                "",
                "Group outputs required this cycle:",
                "- specialist internal work/handoff artifacts",
                "- group exposed summary/handoff/integration notes",
                "- claim-level citations for published assertions",
            ]
        )
        cards[group_id] = "\n".join(lines).strip()
    return cards


def _hash_payload(value: object) -> str:
    return hashlib.sha256(stable_json(value).encode("utf-8", errors="replace")).hexdigest()


def _timeout_mode(value: int) -> str:
    try:
        parsed = int(value)
    except Exception:
        parsed = 0
    return "bounded" if parsed > 0 else "unlimited"


def _copy_latest_artifact(source_path: str, target_path: Path) -> str:
    source = Path(str(source_path)).expanduser().resolve()
    if not source.exists():
        return ""
    data = source.read_bytes()
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_bytes(data)
    return str(target_path)


def _write_turn_latest_artifacts(turn_dir: Path, runtime_result: dict) -> dict:
    mapping = {
        "wait_state_path": turn_dir / "wait-state.latest.json",
        "cooperation_ledger_path": turn_dir / "cooperation-ledger.latest.ndjson",
        "group_head_sessions_path": turn_dir / "group-head-sessions.latest.json",
        "specialist_sessions_path": turn_dir / "specialist-sessions.latest.json",
    }
    out = {}
    for key, target in mapping.items():
        source = str(runtime_result.get(key) or "").strip()
        if not source:
            continue
        copied = _copy_latest_artifact(source, target)
        if copied:
            out[key] = copied
    return out


def _load_constraints(project_root: Path) -> dict:
    try:
        checkpoint = load_checkpoint(project_root, "latest")
    except Exception:
        return {}
    constraints = checkpoint.get("constraints")
    if isinstance(constraints, dict):
        return constraints
    return {}


def _build_delegation_ledger(
    *,
    project_id: str,
    message: str,
    group_manifests: Dict[str, dict],
) -> dict:
    rows = []
    for group_id in sorted(group_manifests.keys()):
        dispatch = build_dispatch_plan(project_id, group_id, message, group_manifests[group_id])
        rows.append(
            {
                "group_id": group_id,
                "head_agent": dispatch.get("head_agent"),
                "phase_count": len(dispatch.get("phases", [])),
                "task_count": sum(
                    len(phase.get("tasks", [])) for phase in dispatch.get("phases", [])
                ),
                "dispatch_mode": dispatch.get("dispatch_mode"),
                "session_mode": dispatch.get("session_mode"),
                "gate_profile": dispatch.get("gate_profile", {}),
                "tasks": dispatch.get("phases", []),
            }
        )
    required_groups = [str(row.get("group_id") or "") for row in rows if row.get("group_id")]
    return {
        "schema_version": "3.0",
        "project_id": project_id,
        "objective": message,
        "generated_at": now_iso(),
        "groups": rows,
        "required_groups": required_groups,
        "contribution_status": {},
        "contributed_groups": [],
        "missing_groups": required_groups,
        "all_active_groups_contributed": False,
    }


def _expected_negotiation_edges(
    groups: List[str], handoff_edges: List[Tuple[str, str]]
) -> List[Tuple[str, str]]:
    return resolve_handoff_edges(groups, handoff_edges)


def _render_negotiation_sequence(
    groups: List[str], primary_group: str, expected_edges: List[Tuple[str, str]]
) -> Tuple[str, dict]:
    lines = [
        "# Negotiation Sequence",
        "",
        f"- primary_group: `{primary_group}`",
        f"- active_groups: {', '.join(groups)}",
        f"- expected_edges: {len(expected_edges)}",
        "",
        "## Sequence",
    ]
    covered_edges: List[Tuple[str, str]] = []
    for idx, (src, dst) in enumerate(expected_edges, start=1):
        lines.append(
            f"{idx}. `{src}` publishes exposed summary; `{dst}` consumes and returns integration feedback."
        )
        covered_edges.append((src, dst))
    if not expected_edges:
        lines.append("1. Single-group flow: head negotiates internally across specialists.")

    lines.extend(
        [
            "",
            "## Conflict Resolution Protocol",
            "1. Evidence-review specialist flags contradictions at claim level.",
            "2. Integration specialists request rerun for missing dependency artifacts.",
            "3. Heads reconcile unresolved assumptions before exposed publication.",
            "4. Router publishes a merged decision log with explicit risk gates.",
        ]
    )
    coverage = 100.0
    if expected_edges:
        coverage = round((len(covered_edges) / len(expected_edges)) * 100.0, 2)
    stats = {
        "expected_edges": [{"from": src, "to": dst} for src, dst in expected_edges],
        "covered_edges": [{"from": src, "to": dst} for src, dst in covered_edges],
        "coverage_percent": coverage,
    }
    return "\n".join(lines).strip() + "\n", stats


def _extract_evidence_rows(web_evidence: List[dict], min_urls: int = 8) -> List[dict]:
    rows: List[dict] = []
    for item in web_evidence:
        if not isinstance(item, dict):
            continue
        if item.get("error"):
            continue
        url = str(item.get("source_url") or "").strip()
        if not url:
            continue
        title = str(item.get("title") or item.get("query") or "untitled").strip()
        provider = str(item.get("provider") or "").strip()
        year = item.get("year")
        rows.append(
            {
                "provider": provider,
                "title": title,
                "url": url,
                "year": str(year) if isinstance(year, int) else "-",
            }
        )
        if len(rows) >= max(min_urls, 12):
            break
    return rows


def _safe_read(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace").strip()


def _citation_from_claim(claim: dict) -> List[str]:
    refs: List[str] = []
    candidates = [
        claim.get("citation"),
        claim.get("url"),
        claim.get("source_url"),
        claim.get("doi"),
    ]
    citations = claim.get("citations")
    if isinstance(citations, list):
        candidates.extend(citations)
    for raw in candidates:
        text = str(raw or "").strip()
        if not text:
            continue
        if text.lower().startswith("doi:"):
            text = "https://doi.org/" + text[4:].strip()
        if text and text not in refs:
            refs.append(text)
    return refs


def _claim_preview(claim: dict) -> str:
    text = str(claim.get("claim") or claim.get("text") or "").strip()
    if not text:
        return ""
    return text[:220]


def _parse_artifact_preview(item: object) -> str:
    if isinstance(item, str):
        return item.strip()
    if isinstance(item, dict):
        for key in ("path", "artifact", "id", "name", "title"):
            text = str(item.get(key) or "").strip()
            if text:
                return text
    return ""


def _collect_group_contributions(project_dir: Path, groups: List[str]) -> List[dict]:
    rows: List[dict] = []
    for group_id in groups:
        exposed_dir = project_dir / "agent-groups" / group_id / "exposed"
        summary_path = exposed_dir / "summary.md"
        handoff_path = exposed_dir / "handoff.json"
        notes_path = exposed_dir / "INTEGRATION_NOTES.md"

        summary_text = _safe_read(summary_path)
        notes_text = _safe_read(notes_path)
        reasons: List[str] = []
        handoff_payload: dict = {}

        if not handoff_path.exists():
            reasons.append("missing exposed/handoff.json")
        else:
            loaded = load_yaml(handoff_path)
            if not isinstance(loaded, dict):
                reasons.append("exposed/handoff.json is not a mapping")
            else:
                handoff_payload = loaded

        status = str(handoff_payload.get("status") or "").strip().upper()
        if status in {"", "PENDING"}:
            reasons.append("handoff status is pending")

        artifacts = handoff_payload.get("artifacts")
        artifact_preview: List[str] = []
        if isinstance(artifacts, list):
            for item in artifacts:
                preview = _parse_artifact_preview(item)
                if preview and preview not in artifact_preview:
                    artifact_preview.append(preview)

        claims_payload = handoff_payload.get("claims_with_citations")
        if not isinstance(claims_payload, list):
            claims_payload = handoff_payload.get("claims")
        claims: List[dict] = []
        if isinstance(claims_payload, list):
            for item in claims_payload:
                if isinstance(item, dict):
                    claims.append(item)

        citation_refs: List[str] = []
        claim_preview_rows: List[dict] = []
        for claim in claims:
            refs = _citation_from_claim(claim)
            for ref in refs:
                if ref not in citation_refs:
                    citation_refs.append(ref)
            preview = _claim_preview(claim)
            if preview:
                claim_preview_rows.append(
                    {
                        "text": preview,
                        "citations": refs,
                    }
                )

        summary_ready = (
            bool(summary_text) and "pending head publication" not in summary_text.lower()
        )
        has_substance = bool(artifact_preview) or bool(claim_preview_rows) or summary_ready
        if not has_substance:
            reasons.append("no published artifacts/claims in exposed handoff")

        rows.append(
            {
                "group_id": group_id,
                "valid": not reasons,
                "reasons": reasons,
                "status": status or "UNKNOWN",
                "summary_path": str(summary_path),
                "handoff_path": str(handoff_path),
                "integration_notes_path": str(notes_path),
                "summary_excerpt": summary_text[:500],
                "integration_excerpt": notes_text[:500],
                "artifact_preview": artifact_preview[:8],
                "claim_preview": claim_preview_rows[:8],
                "artifact_count": len(artifact_preview),
                "claim_count": len(claim_preview_rows),
                "citation_refs": citation_refs,
                "citation_count": len(citation_refs),
            }
        )
    return rows


def _apply_contribution_status(delegation_ledger: dict, contributions: List[dict]) -> dict:
    required = [str(item) for item in delegation_ledger.get("required_groups", []) if str(item)]
    by_group = {str(row.get("group_id") or ""): row for row in contributions}
    status_map = {}
    contributed: List[str] = []
    missing: List[str] = []

    for group_id in required:
        row = by_group.get(group_id)
        if not row:
            status_map[group_id] = {
                "valid": False,
                "reasons": ["group contribution record missing"],
            }
            missing.append(group_id)
            continue
        valid = bool(row.get("valid"))
        if valid:
            contributed.append(group_id)
        else:
            missing.append(group_id)
        status_map[group_id] = {
            "valid": valid,
            "status": row.get("status", "UNKNOWN"),
            "reasons": row.get("reasons", []),
            "artifact_count": row.get("artifact_count", 0),
            "claim_count": row.get("claim_count", 0),
            "citation_count": row.get("citation_count", 0),
            "handoff_path": row.get("handoff_path", ""),
        }

    updated = dict(delegation_ledger)
    updated["contribution_status"] = status_map
    updated["contributed_groups"] = contributed
    updated["missing_groups"] = missing
    updated["all_active_groups_contributed"] = len(missing) == 0
    return updated


def _render_delegation_summary_table(delegation_ledger: dict) -> str:
    lines = [
        "| Group | Head | Phases | Tasks | Contribution |",
        "|---|---|---:|---:|---|",
    ]
    contribution = delegation_ledger.get("contribution_status")
    if not isinstance(contribution, dict):
        contribution = {}
    for row in delegation_ledger.get("groups", []):
        group_id = str(row.get("group_id", ""))
        state = contribution.get(group_id, {})
        label = "valid" if state.get("valid") else "missing/invalid"
        lines.append(
            "| {0} | {1} | {2} | {3} | {4} |".format(
                group_id,
                row.get("head_agent", ""),
                row.get("phase_count", 0),
                row.get("task_count", 0),
                label,
            )
        )
    return "\n".join(lines)


def _render_group_findings(contributions: List[dict]) -> str:
    lines: List[str] = []
    for row in contributions:
        group_id = str(row.get("group_id") or "")
        lines.append(f"### {group_id}")
        lines.append(
            "- contribution status: `{0}`".format("valid" if row.get("valid") else "blocked")
        )
        lines.append("- exposed handoff: `{0}`".format(row.get("handoff_path", "")))
        lines.append("- exposed summary: `{0}`".format(row.get("summary_path", "")))
        lines.append(
            "- artifact_count: `{0}` | claim_count: `{1}` | citation_count: `{2}`".format(
                row.get("artifact_count", 0),
                row.get("claim_count", 0),
                row.get("citation_count", 0),
            )
        )

        reasons = row.get("reasons", [])
        if isinstance(reasons, list) and reasons:
            for reason in reasons:
                lines.append(f"- block_reason: {reason}")

        summary_excerpt = str(row.get("summary_excerpt") or "").strip()
        if summary_excerpt:
            lines.append("- summary excerpt:")
            lines.append(f"  {summary_excerpt}")

        integration_excerpt = str(row.get("integration_excerpt") or "").strip()
        if integration_excerpt:
            lines.append("- integration excerpt:")
            lines.append(f"  {integration_excerpt}")

        claim_rows = row.get("claim_preview", [])
        if isinstance(claim_rows, list) and claim_rows:
            lines.append("- claim-level published signals:")
            for claim in claim_rows[:5]:
                text = str(claim.get("text") or "").strip()
                refs = claim.get("citations", [])
                ref_text = ", ".join(str(item) for item in refs[:2]) if refs else "no-citation"
                lines.append(f"  - {text} [refs: {ref_text}]")

        artifacts = row.get("artifact_preview", [])
        if isinstance(artifacts, list) and artifacts:
            lines.append("- published artifacts:")
            for item in artifacts[:5]:
                lines.append(f"  - {item}")

        lines.append("")
    return "\n".join(lines).strip()


def _render_integrated_plan_from_contributions(contributions: List[dict]) -> str:
    lines = [
        "1. Consolidate all group-exposed handoff artifacts as the single source of truth for this turn.",
        "2. Resolve inter-group conflicts only through exposed claim/citation records and integration notes.",
        "3. Advance experiment/compute execution only for artifacts that passed evidence and reproducibility checks.",
    ]
    step_index = 4
    for row in contributions:
        group_id = str(row.get("group_id") or "")
        summary_excerpt = str(row.get("summary_excerpt") or "").strip()
        artifacts = row.get("artifact_preview", [])
        claims = row.get("claim_preview", [])

        detail_bits: List[str] = []
        if summary_excerpt:
            detail_bits.append(summary_excerpt[:260])
        if isinstance(artifacts, list) and artifacts:
            detail_bits.append("artifacts=" + ", ".join(str(item) for item in artifacts[:3]))
        if isinstance(claims, list) and claims:
            claim_text = "; ".join(str(item.get("text") or "") for item in claims[:2])
            if claim_text.strip():
                detail_bits.append("claims=" + claim_text[:260])

        if not detail_bits:
            detail_bits.append("No publishable detail found beyond status metadata.")

        lines.append(f"{step_index}. `{group_id}` contribution: {' | '.join(detail_bits)}")
        step_index += 1

    lines.append(
        f"{step_index}. Publish integrated decision only after all active groups keep valid exposed handoff status."
    )
    return "\n".join(lines)


def _render_anticipated_results_table(contributions: List[dict]) -> str:
    lines = [
        "| Group | Published Signal | Citation Refs |",
        "|---|---|---|",
    ]
    for row in contributions:
        group_id = str(row.get("group_id") or "")
        claims = row.get("claim_preview", [])
        summary_excerpt = str(row.get("summary_excerpt") or "").strip()
        signal = ""
        refs: List[str] = []

        if isinstance(claims, list) and claims:
            first = claims[0]
            signal = str(first.get("text") or "").strip()
            citations = first.get("citations", [])
            if isinstance(citations, list):
                refs = [str(item) for item in citations if str(item).strip()]

        if not signal:
            signal = (
                summary_excerpt[:180]
                if summary_excerpt
                else "No quantitative forecast published yet."
            )

        ref_text = ", ".join(refs[:2]) if refs else "-"
        lines.append(
            "| {0} | {1} | {2} |".format(
                group_id,
                signal.replace("|", "/"),
                ref_text.replace("|", "/"),
            )
        )
    return "\n".join(lines)


def _render_evidence_table(web_rows: List[dict], artifact_citations: List[dict]) -> str:
    lines = [
        "| Source Type | Provider/Group | Year | Title/Ref | URL |",
        "|---|---|---:|---|---|",
    ]

    for row in web_rows:
        title = str(row.get("title", "")).replace("|", "/")
        lines.append(
            "| web | {0} | {1} | {2} | {3} |".format(
                row.get("provider", ""),
                row.get("year", "-"),
                title,
                row.get("url", ""),
            )
        )

    for row in artifact_citations:
        lines.append(
            "| artifact | {0} | - | {1} | {2} |".format(
                row.get("group_id", ""),
                str(row.get("citation") or "").replace("|", "/"),
                row.get("url", ""),
            )
        )

    if len(lines) == 2:
        lines.append("| none | none | - | no evidence rows captured | - |")
    return "\n".join(lines)


def _collect_artifact_citations(contributions: List[dict]) -> List[dict]:
    rows: List[dict] = []
    seen: set = set()
    for row in contributions:
        group_id = str(row.get("group_id") or "")
        refs = row.get("citation_refs", [])
        if not isinstance(refs, list):
            continue
        for ref in refs:
            text = str(ref).strip()
            if not text:
                continue
            key = (group_id, text)
            if key in seen:
                continue
            seen.add(key)
            url = text if text.startswith("http") else ""
            rows.append(
                {
                    "group_id": group_id,
                    "citation": text,
                    "url": url,
                }
            )
    return rows


def _render_group_mode_answer(
    *,
    project_id: str,
    message: str,
    constraints: dict,
    delegation_ledger: dict,
    negotiation_stats: dict,
    evidence_rows: List[dict],
    artifact_citations: List[dict],
    contributions: List[dict],
    turn_dir: Path,
    project_root: Path,
) -> str:
    constraints_rows = []
    for key, value in constraints.items():
        constraints_rows.append(f"- {key}: {value}")
    if not constraints_rows:
        constraints_rows = [
            "- constraints not explicitly set in latest checkpoint; using project defaults."
        ]

    candidate_block = "No optional domain-adapter artifacts were published for this turn."

    lines = [
        f"# Orchestrator Reply - {project_id}",
        "",
        "## Objective and Constraints",
        message,
        "",
        *constraints_rows,
        "",
        "## Delegation Summary",
        "Source: `delegation-ledger.json`",
        "",
        _render_delegation_summary_table(delegation_ledger),
        "",
        "## Inter-Group Negotiation and Conflict Resolution",
        "Source: `negotiation-sequence.md`",
        "",
        "- Expected handoff edges: `{0}`".format(len(negotiation_stats.get("expected_edges", []))),
        "- Covered handoff edges: `{0}`".format(len(negotiation_stats.get("covered_edges", []))),
        "- Coverage percent: `{0}`".format(negotiation_stats.get("coverage_percent", 0.0)),
        "- Required active group contributors: `{0}`".format(
            len(delegation_ledger.get("required_groups", []))
        ),
        "- Valid contributed groups: `{0}`".format(
            len(delegation_ledger.get("contributed_groups", []))
        ),
        "",
        "## Group-by-Group Findings",
        _render_group_findings(contributions),
        "",
        "## Integrated Execution Plan",
        _render_integrated_plan_from_contributions(contributions),
        "",
        "## Optional Domain Artifacts",
        candidate_block,
        "",
        "## Anticipated Results",
        _render_anticipated_results_table(contributions),
        "",
        "## Evidence Table (URLs)",
        _render_evidence_table(evidence_rows, artifact_citations),
        "",
        "## Risks and Decision Gates",
        "- Gate A (all-active-groups): every active group must publish valid exposed handoff artifacts.",
        "- Gate B (evidence): at least one web URL or artifact citation set must be present for this turn.",
        "- Gate C (integration): conflicting exposed claims must be resolved through negotiation before publication.",
        "- Gate D (reproducibility): recommended actions must point to published artifacts and executable steps.",
        "",
        "## Next Actions",
        "1. Dispatch groups with invalid/missing exposed handoff status.",
        "2. Re-run orchestrator reply once all active groups publish valid exposed artifacts.",
        "3. Promote this integrated output only after evidence and integration gates pass.",
        "",
        "## Artifact Index",
        f"- turn_dir: `{turn_dir}`",
        f"- delegation ledger: `{turn_dir / 'delegation-ledger.json'}`",
        f"- negotiation sequence: `{turn_dir / 'negotiation-sequence.md'}`",
        f"- group evidence index: `{turn_dir / 'group-evidence-index.json'}`",
    ]
    return "\n".join(lines).strip() + "\n"


def _quality_gate(
    *,
    mode: str,
    answer_text: str,
    detail_profile: str,
    evidence_rows: List[dict],
    artifact_citations: List[dict],
    negotiation_stats: dict,
    delegation_ledger: Optional[dict],
    contributions: Optional[List[dict]],
    turn_dir: Path,
) -> dict:
    word_count = len(re.findall(r"\b\w+\b", answer_text))
    if mode != "group-detailed":
        checks = {
            "mode_is_non_group": mode == "non-group",
            "concise_word_count_max": word_count <= 180,
            "delegation_not_emitted": not (turn_dir / "delegation-ledger.json").exists(),
        }
        return {
            "schema_version": "3.0",
            "mode": mode,
            "detail_profile": detail_profile,
            "word_count": word_count,
            "min_words_required": 0,
            "section_status": {},
            "web_evidence_url_count": 0,
            "artifact_citation_count": 0,
            "checks": checks,
            "negotiation": {"expected_edges": [], "covered_edges": [], "coverage_percent": 100.0},
            "delegation_group_count": 0,
            "all_active_groups_contributed": False,
            "passed": all(checks.values()),
            "generated_at": now_iso(),
        }

    min_words = 500 if detail_profile == "publication-grade" else 40
    required_sections = [
        "## Objective and Constraints",
        "## Delegation Summary",
        "## Inter-Group Negotiation and Conflict Resolution",
        "## Group-by-Group Findings",
        "## Integrated Execution Plan",
        "## Optional Domain Artifacts",
        "## Anticipated Results",
        "## Evidence Table (URLs)",
        "## Risks and Decision Gates",
        "## Next Actions",
    ]
    section_status = {section: bool(section in answer_text) for section in required_sections}
    web_urls = [str(row.get("url") or "").strip() for row in evidence_rows if isinstance(row, dict)]
    web_urls = [url for url in web_urls if url]

    artifact_refs = []
    for row in artifact_citations:
        if not isinstance(row, dict):
            continue
        text = str(row.get("citation") or "").strip()
        if text:
            artifact_refs.append(text)

    delegation_ok = bool(
        delegation_ledger
        and isinstance(delegation_ledger.get("groups"), list)
        and len(delegation_ledger["groups"]) > 0
        and (turn_dir / "delegation-ledger.json").exists()
    )
    negotiation_ok = bool(
        (turn_dir / "negotiation-sequence.md").exists()
        and float(negotiation_stats.get("coverage_percent", 0.0)) >= 100.0
    )

    required_groups = []
    if isinstance(delegation_ledger, dict):
        required_groups = [
            str(group_id)
            for group_id in delegation_ledger.get("required_groups", [])
            if str(group_id).strip()
        ]

    valid_contributions = [
        str(row.get("group_id") or "")
        for row in (contributions or [])
        if isinstance(row, dict) and bool(row.get("valid"))
    ]
    valid_set = {group_id for group_id in valid_contributions if group_id}
    required_set = {group_id for group_id in required_groups if group_id}

    all_groups_contributed = bool(required_groups) and required_set.issubset(valid_set)
    evidence_available = bool(web_urls or artifact_refs)

    checks = {
        "mode_is_group_detailed": mode == "group-detailed",
        "word_count_min": word_count >= min_words,
        "sections_complete": all(section_status.values()),
        "evidence_available": evidence_available,
        "delegation_artifact_present": delegation_ok,
        "negotiation_artifact_present": negotiation_ok,
        "all_active_groups_contributed": all_groups_contributed,
    }

    return {
        "schema_version": "3.0",
        "mode": mode,
        "detail_profile": detail_profile,
        "word_count": word_count,
        "min_words_required": min_words,
        "section_status": section_status,
        "web_evidence_url_count": len(web_urls),
        "artifact_citation_count": len(artifact_refs),
        "checks": checks,
        "negotiation": negotiation_stats,
        "delegation_group_count": (
            len(delegation_ledger.get("groups", [])) if isinstance(delegation_ledger, dict) else 0
        ),
        "required_groups": required_groups,
        "valid_contributed_groups": sorted(valid_set),
        "all_active_groups_contributed": all_groups_contributed,
        "passed": all(checks.values()),
        "generated_at": now_iso(),
    }


def _render_blocked_report(
    *,
    project_id: str,
    message: str,
    status: str,
    reasons: List[str],
    contributions: List[dict],
    web_evidence_count: int,
    artifact_citation_count: int,
    turn_dir: Path,
    timed_out_specialists: List[dict] | None = None,
    escalations: List[dict] | None = None,
) -> str:
    lines = [
        f"# BLOCKED Turn - {project_id}",
        "",
        "## Objective",
        message,
        "",
        "## Block Status",
        f"- status: `{status}`",
        "",
        "## Reasons",
    ]
    for reason in reasons:
        lines.append(f"- {reason}")

    lines.extend(
        [
            "",
            "## Contributor Status",
            "| Group | Status | Artifact Count | Claim Count | Citation Count | Reasons |",
            "|---|---|---:|---:|---:|---|",
        ]
    )

    for row in contributions:
        reason_text = "; ".join(str(item) for item in row.get("reasons", []))
        lines.append(
            "| {0} | {1} | {2} | {3} | {4} | {5} |".format(
                row.get("group_id", ""),
                "valid" if row.get("valid") else "blocked",
                row.get("artifact_count", 0),
                row.get("claim_count", 0),
                row.get("citation_count", 0),
                reason_text.replace("|", "/"),
            )
        )

    lines.extend(
        [
            "",
            "## Evidence Summary",
            f"- web evidence URLs: `{web_evidence_count}`",
            f"- artifact citation refs: `{artifact_citation_count}`",
        ]
    )

    if timed_out_specialists:
        lines.extend(
            [
                "",
                "## Timed Out Specialists",
                "| Group | Specialist | Attempts | Raw Log | Redacted Log |",
                "|---|---|---:|---|---|",
            ]
        )
        for row in timed_out_specialists:
            lines.append(
                "| {0} | {1} | {2} | {3} | {4} |".format(
                    row.get("group_id", ""),
                    row.get("specialist_id", ""),
                    row.get("attempts", ""),
                    row.get("raw_log_path", ""),
                    row.get("redacted_log_path", ""),
                )
            )

    if escalations:
        lines.extend(
            [
                "",
                "## Escalations",
                "| Group | Specialist | Type | Reason | Request ID |",
                "|---|---|---|---|---|",
            ]
        )
        for row in escalations:
            lines.append(
                "| {0} | {1} | {2} | {3} | {4} |".format(
                    row.get("group_id", ""),
                    row.get("specialist_id", ""),
                    row.get("type", ""),
                    str(row.get("reason", "")).replace("|", "/"),
                    row.get("request_id", ""),
                )
            )

    lines.extend(["", "## Recovery Commands"])

    for row in contributions:
        if row.get("valid"):
            continue
        group_id = str(row.get("group_id") or "")
        if not group_id:
            continue
        lines.append(
            '- `agents-inc dispatch --project-id {0} --group {1} --objective "{2}" --locking-mode auto`'.format(
                project_id,
                group_id,
                message.replace('"', "'"),
            )
        )

    lines.extend(
        [
            '- `agents-inc orchestrator-reply --project-id {0} --message "{1}"`'.format(
                project_id,
                message.replace('"', "'"),
            ),
            "",
            "## Artifact Index",
            f"- turn_dir: `{turn_dir}`",
            f"- blocked reasons: `{turn_dir / 'blocked-reasons.json'}`",
            f"- quality report: `{turn_dir / 'final-answer-quality.json'}`",
        ]
    )
    return "\n".join(lines).strip() + "\n"


def _render_non_group_answer(
    *,
    project_id: str,
    query: str,
    project_root: Path,
    primary_group: str,
) -> str:
    normalized = query.lower()
    if "session id" in normalized and "specialist" in normalized:
        match = lookup_specialist_session(
            project_root=project_root,
            project_id=project_id,
            query=query,
            fallback_group=primary_group,
        )
        if match:
            return (
                "specialist session\n"
                f"- project_id: {project_id}\n"
                f"- group_id: {match['group_id']}\n"
                f"- specialist_id: {match['specialist_id']}\n"
                f"- role: {match['role']}\n"
                f"- session_code: {match['session_code']}\n"
            )
        return "specialist session not found for the requested query.\n"

    if "list" in normalized and "session" in normalized:
        rows = flatten_specialist_sessions(project_root, project_id=project_id)
        if not rows:
            return "no specialist sessions found.\n"
        lines = [
            "specialist sessions",
            f"- project_id: {project_id}",
        ]
        for row in rows[:20]:
            lines.append(
                "- {0}/{1} ({2}) -> {3}".format(
                    row.get("group_id", ""),
                    row.get("specialist_id", ""),
                    row.get("role", ""),
                    row.get("session_code", ""),
                )
            )
        return "\n".join(lines) + "\n"

    return (
        "non-group quick response\n"
        f"- project_id: {project_id}\n"
        f"- primary_group: {primary_group}\n"
        f"- query: {query.strip()}\n"
    )


def _refine_group_objectives(
    *,
    current_objectives: Dict[str, str],
    selected_groups: List[str],
    decisions: dict,
) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for group_id in selected_groups:
        current_text = str(current_objectives.get(group_id) or "").strip()
        if not current_text:
            current_text = ""
        row = decisions.get(group_id, {})
        new_actions = row.get("new_actions", [])
        if not isinstance(new_actions, list):
            new_actions = []
        merged = [f"- {str(item)}" for item in new_actions if str(item).strip()]
        if not merged:
            out[group_id] = current_text
            continue
        out[group_id] = (
            current_text + "\n\nCycle refinement for this group:\n" + "\n".join(merged[:12])
        )
    return out


def _render_key_points(
    *,
    project_id: str,
    selected_groups: List[str],
    final_report_path: Path,
    turn_dir: Path,
) -> str:
    lines = [
        f"project_id: {project_id}",
        f"active_groups: {', '.join(selected_groups)}",
        f"full_report_path: {final_report_path}",
        f"turn_dir: {turn_dir}",
    ]
    return "\n".join(lines).strip() + "\n"


def run_orchestrator_reply(config: OrchestratorReplyConfig) -> dict:
    project_id = slugify(config.project_id)
    config = OrchestratorReplyConfig(
        fabric_root=config.fabric_root,
        project_id=project_id,
        message=config.message,
        group=config.group,
        output_dir=config.output_dir,
        max_parallel=int(config.max_parallel),
        retry_attempts=int(config.retry_attempts),
        retry_backoff_sec=int(config.retry_backoff_sec),
        agent_timeout_sec=max(0, int(config.agent_timeout_sec)),
        loop_mode=str(config.loop_mode or "cooperative"),
        meeting_enabled=bool(config.meeting_enabled),
        stop_rule=str(config.stop_rule or "unanimous-head-satisfied"),
        max_cycles=max(0, int(config.max_cycles)),
        heartbeat_sec=max(5, int(config.heartbeat_sec)),
        abort_file=config.abort_file,
        require_negotiation=bool(config.require_negotiation),
        audit=bool(config.audit),
    )
    project_root, project_dir, manifest = _load_project_bundle(config)
    policy = ensure_response_policy(project_root)
    selected_groups = selected_groups_from_manifest(manifest)
    primary_group = resolve_primary_group_router(selected_groups, config.group)
    upsert_specialist_sessions(
        project_root=project_root,
        project_fabric_root=config.fabric_root,
        project_id=config.project_id,
        selected_groups=selected_groups,
    )

    turn_dir = _turn_dir(project_root, config.output_dir)
    write_text(turn_dir / "request.txt", config.message.strip() + "\n")

    mode = classify_request_mode(config.message, policy)
    mode_payload = {
        "schema_version": "3.0",
        "mode": mode,
        "non_group_prefix": policy.get("non_group_prefix", "[non-group]"),
        "group": primary_group,
        "require_negotiation": bool(config.require_negotiation),
        "generated_at": now_iso(),
    }
    write_text(turn_dir / "mode.json", stable_json(mode_payload) + "\n")

    if mode == "non-group":
        query = strip_non_group_prefix(config.message, policy)
        answer = _render_non_group_answer(
            project_id=config.project_id,
            query=query,
            project_root=project_root,
            primary_group=primary_group,
        )
        final_path = turn_dir / "final-exposed-answer.md"
        write_text(final_path, answer.strip() + "\n")
        quality = _quality_gate(
            mode=mode,
            answer_text=answer,
            detail_profile=str(policy.get("non_group_profile") or "concise"),
            evidence_rows=[],
            artifact_citations=[],
            negotiation_stats={
                "expected_edges": [],
                "covered_edges": [],
                "coverage_percent": 100.0,
            },
            delegation_ledger=None,
            contributions=None,
            turn_dir=turn_dir,
        )
        write_text(turn_dir / "final-answer-quality.json", stable_json(quality) + "\n")
        return {
            "mode": mode,
            "project_id": config.project_id,
            "group": primary_group,
            "turn_dir": str(turn_dir),
            "final_answer_path": str(final_path),
            "quality_path": str(turn_dir / "final-answer-quality.json"),
            "quality": quality,
        }

    group_manifests = _load_group_manifests(project_dir, manifest, selected_groups)
    delegation = _build_delegation_ledger(
        project_id=config.project_id,
        message=config.message,
        group_manifests=group_manifests,
    )
    handoff_edges = manifest.get("handoff_edges") or []
    if not isinstance(handoff_edges, list):
        handoff_edges = []
    active_handoff_edges = _expected_negotiation_edges(selected_groups, handoff_edges)
    negotiation_text, negotiation_stats = _render_negotiation_sequence(
        selected_groups, primary_group, active_handoff_edges
    )
    write_text(turn_dir / "negotiation-sequence.md", negotiation_text)

    group_objectives = _build_group_objective_cards(
        base_objective=config.message,
        selected_groups=selected_groups,
        group_manifests=group_manifests,
    )
    blocked_reasons: List[str] = []
    block_status = ""
    cycle = 0
    watchdog_limit = 100 if config.max_cycles == 0 else max(1, int(config.max_cycles))
    cycle_summaries: List[dict] = []
    meeting_outputs: List[dict] = []
    cycle_records: List[NegotiationCycleRecord] = []
    runtime_result = {}
    timed_out_specialists: List[dict] = []
    unresolved_escalations: List[dict] = []
    latest_artifacts: Dict[str, str] = {}

    while True:
        cycle += 1
        if config.max_cycles > 0 and cycle > config.max_cycles:
            block_status = "BLOCKED_MAX_CYCLES"
            blocked_reasons.append(
                f"max cycle limit reached before unanimous satisfaction: {config.max_cycles}"
            )
            break
        if cycle > watchdog_limit:
            block_status = "BLOCKED_WATCHDOG"
            blocked_reasons.append("watchdog cycle limit reached before unanimous satisfaction")
            break

        cycle_dir = turn_dir / "cycles" / f"cycle-{cycle:04d}"
        cycle_dir.mkdir(parents=True, exist_ok=True)
        cycle_layer2 = cycle_dir / "layer2"
        cycle_layer2.mkdir(parents=True, exist_ok=True)
        write_text(
            cycle_layer2 / "group-objectives.json",
            stable_json(
                {
                    "schema_version": "3.1",
                    "project_id": config.project_id,
                    "cycle_id": cycle,
                    "generated_at": now_iso(),
                    "objectives": group_objectives,
                    "objectives_hash": _hash_payload(group_objectives),
                }
            )
            + "\n",
        )
        runtime_result = run_layered_runtime(
            LayeredRuntimeConfig(
                project_id=config.project_id,
                project_root=project_root,
                project_dir=project_dir,
                turn_dir=cycle_dir,
                message=config.message,
                selected_groups=selected_groups,
                group_manifests=group_manifests,
                group_objectives=group_objectives,
                max_parallel=config.max_parallel,
                retry_attempts=config.retry_attempts,
                retry_backoff_sec=config.retry_backoff_sec,
                agent_timeout_sec=config.agent_timeout_sec,
                heartbeat_sec=config.heartbeat_sec,
                abort_file=config.abort_file,
                audit=config.audit,
                handoff_edges=active_handoff_edges,
            )
        )
        latest_artifacts = _write_turn_latest_artifacts(turn_dir, runtime_result)
        cycle_timeouts = runtime_result.get("timed_out_specialists", [])
        if isinstance(cycle_timeouts, list):
            for row in cycle_timeouts:
                if not isinstance(row, dict):
                    continue
                if row not in timed_out_specialists:
                    timed_out_specialists.append(row)
        cycle_escalations = runtime_result.get("escalations", [])
        if not isinstance(cycle_escalations, list):
            cycle_escalations = []
        write_text(cycle_dir / "escalations.json", stable_json(cycle_escalations) + "\n")
        for row in cycle_escalations:
            if isinstance(row, dict) and row not in unresolved_escalations:
                unresolved_escalations.append(row)
        write_text(turn_dir / "escalations.json", stable_json(unresolved_escalations) + "\n")
        cycle_summaries.append(
            build_cycle_summary(
                cycle_id=cycle,
                runtime_result=runtime_result,
                objectives_hash=_hash_payload(group_objectives),
                agent_timeout_sec=config.agent_timeout_sec,
                agent_timeout_mode=_timeout_mode(config.agent_timeout_sec),
                cycle_timeouts=cycle_timeouts,
                cycle_escalations=cycle_escalations,
                latest_artifacts=latest_artifacts,
            )
        )
        if runtime_result.get("blocked"):
            write_text(
                cycle_layer2 / "refined-group-objectives.json",
                stable_json(
                    {
                        "schema_version": "3.1",
                        "project_id": config.project_id,
                        "cycle_id": cycle,
                        "generated_at": now_iso(),
                        "objectives": group_objectives,
                        "objectives_hash": _hash_payload(group_objectives),
                        "refinement_source": "runtime-blocked",
                    }
                )
                + "\n",
            )
            cycle_records.append(
                NegotiationCycleRecord(
                    cycle_id=cycle,
                    objectives=dict(group_objectives),
                    refined_objectives=dict(group_objectives),
                    decisions={},
                    unsatisfied_groups=selected_groups,
                )
            )
        if runtime_result.get("blocked"):
            block_status = "BLOCKED_LAYERED_RUNTIME"
            if unresolved_escalations:
                block_status = "BLOCKED_ESCALATION_REQUIRED"
                blocked_reasons.append(
                    f"{len(unresolved_escalations)} unresolved specialist escalation request(s)"
                )
            reasons = runtime_result.get("reasons", [])
            if isinstance(reasons, list):
                blocked_reasons.extend(str(item) for item in reasons if str(item).strip())
            timed_out_rows = runtime_result.get("timed_out_specialists", [])
            if isinstance(timed_out_rows, list) and timed_out_rows:
                blocked_reasons.append(
                    "timed out specialists: "
                    + ", ".join(
                        "{0}/{1}".format(
                            str(row.get("group_id") or ""),
                            str(row.get("specialist_id") or ""),
                        )
                        for row in timed_out_rows
                        if isinstance(row, dict)
                    )
                )
            break

        if config.abort_file and config.abort_file.exists():
            block_status = "BLOCKED_ABORT_REQUESTED"
            blocked_reasons.append(f"abort file detected: {config.abort_file}")
            write_text(
                cycle_layer2 / "refined-group-objectives.json",
                stable_json(
                    {
                        "schema_version": "3.1",
                        "project_id": config.project_id,
                        "cycle_id": cycle,
                        "generated_at": now_iso(),
                        "objectives": group_objectives,
                        "objectives_hash": _hash_payload(group_objectives),
                        "refinement_source": "abort-detected",
                    }
                )
                + "\n",
            )
            cycle_records.append(
                NegotiationCycleRecord(
                    cycle_id=cycle,
                    objectives=dict(group_objectives),
                    refined_objectives=dict(group_objectives),
                    decisions={},
                    unsatisfied_groups=selected_groups,
                )
            )
            break

        if not config.meeting_enabled:
            write_text(
                cycle_layer2 / "refined-group-objectives.json",
                stable_json(
                    {
                        "schema_version": "3.1",
                        "project_id": config.project_id,
                        "cycle_id": cycle,
                        "generated_at": now_iso(),
                        "objectives": group_objectives,
                        "objectives_hash": _hash_payload(group_objectives),
                        "refinement_source": "meeting-disabled",
                    }
                )
                + "\n",
            )
            cycle_records.append(
                NegotiationCycleRecord(
                    cycle_id=cycle,
                    objectives=dict(group_objectives),
                    refined_objectives=dict(group_objectives),
                    decisions={},
                    unsatisfied_groups=[],
                )
            )
            break

        meeting = run_head_meeting(
            HeadMeetingConfig(
                project_id=config.project_id,
                cycle_id=cycle,
                cycle_dir=cycle_dir,
                project_dir=project_dir,
                selected_groups=selected_groups,
                message=config.message,
            )
        )
        meeting_outputs.append(meeting)
        refined_objectives = _refine_group_objectives(
            current_objectives=group_objectives,
            selected_groups=selected_groups,
            decisions=meeting.get("decisions", {}),
        )
        write_text(
            cycle_layer2 / "refined-group-objectives.json",
            stable_json(
                {
                    "schema_version": "3.1",
                    "project_id": config.project_id,
                    "cycle_id": cycle,
                    "generated_at": now_iso(),
                    "objectives": refined_objectives,
                    "objectives_hash": _hash_payload(refined_objectives),
                    "refinement_source": "head-meeting",
                }
            )
            + "\n",
        )
        matrix = meeting.get("matrix", {})
        unsatisfied_groups = []
        if isinstance(matrix, dict):
            raw_unsatisfied = matrix.get("unsatisfied_groups", [])
            if isinstance(raw_unsatisfied, list):
                unsatisfied_groups = [str(item) for item in raw_unsatisfied if str(item).strip()]
        cycle_records.append(
            NegotiationCycleRecord(
                cycle_id=cycle,
                objectives=dict(group_objectives),
                refined_objectives=dict(refined_objectives),
                decisions=(
                    meeting.get("decisions", {})
                    if isinstance(meeting.get("decisions"), dict)
                    else {}
                ),
                unsatisfied_groups=unsatisfied_groups,
            )
        )
        if bool(meeting.get("all_satisfied")):
            break
        group_objectives = refined_objectives

    final_all_satisfied = (
        bool(meeting_outputs[-1].get("all_satisfied")) if meeting_outputs else False
    )
    monitor, meeting_monitor_paths = build_negotiation_monitor(
        selected_groups=selected_groups,
        cycle_records=cycle_records,
        require_negotiation=bool(config.require_negotiation),
        final_all_satisfied=final_all_satisfied,
        meeting_dir=turn_dir / "meeting",
    )
    if bool(config.require_negotiation) and not bool(monitor.get("passed")) and not block_status:
        block_status = "BLOCKED_NEGOTIATION_NOT_OBSERVED"
        reasons = monitor.get("reasons", [])
        if isinstance(reasons, list):
            blocked_reasons.extend(str(item) for item in reasons if str(item).strip())

    write_text(turn_dir / "escalations.json", stable_json(unresolved_escalations) + "\n")

    evidence_rows: List[dict] = []
    contributions = _collect_group_contributions(project_dir, selected_groups)
    artifact_citations = _collect_artifact_citations(contributions)
    delegation = _apply_contribution_status(delegation, contributions)
    write_text(turn_dir / "delegation-ledger.json", stable_json(delegation) + "\n")

    evidence_index = {
        "schema_version": "3.1",
        "project_id": config.project_id,
        "generated_at": now_iso(),
        "web_evidence": evidence_rows,
        "artifact_citations": artifact_citations,
        "contributions": contributions,
        "all_active_groups_contributed": delegation.get("all_active_groups_contributed", False),
        "missing_groups": delegation.get("missing_groups", []),
        "cycles": cycle_summaries,
        "negotiation_monitor": monitor,
    }
    write_text(turn_dir / "group-evidence-index.json", stable_json(evidence_index) + "\n")

    if not delegation.get("all_active_groups_contributed") and not block_status:
        block_status = "BLOCKED_GROUP_CONTRIBUTIONS"
        for row in contributions:
            if row.get("valid"):
                continue
            reasons = row.get("reasons", [])
            reason_text = "; ".join(str(item) for item in reasons)
            blocked_reasons.append(
                "group '{0}' contribution invalid: {1}".format(row.get("group_id", ""), reason_text)
            )

    if not evidence_rows and not artifact_citations and not block_status:
        block_status = "BLOCKED_NEEDS_EVIDENCE"
        blocked_reasons.append("no web evidence URLs and no artifact citation refs available")

    if block_status:
        quality = _quality_gate(
            mode=mode,
            answer_text="",
            detail_profile=str(policy.get("detail_profile") or "publication-grade"),
            evidence_rows=evidence_rows,
            artifact_citations=artifact_citations,
            negotiation_stats=negotiation_stats,
            delegation_ledger=delegation,
            contributions=contributions,
            turn_dir=turn_dir,
        )
        quality["block_status"] = block_status
        quality["block_reasons"] = blocked_reasons
        quality["cycles_executed"] = cycle
        quality["agent_timeout_sec"] = config.agent_timeout_sec
        quality["agent_timeout_mode"] = _timeout_mode(config.agent_timeout_sec)
        quality["timed_out_specialist_count"] = len(timed_out_specialists)
        write_text(turn_dir / "final-answer-quality.json", stable_json(quality) + "\n")

        blocked_payload = {
            "schema_version": "3.1",
            "status": block_status,
            "project_id": config.project_id,
            "group": primary_group,
            "generated_at": now_iso(),
            "reasons": blocked_reasons,
            "required_groups": delegation.get("required_groups", []),
            "missing_groups": delegation.get("missing_groups", []),
            "web_evidence_url_count": len(evidence_rows),
            "artifact_citation_count": len(artifact_citations),
            "cycles_executed": cycle,
            "agent_timeout_sec": config.agent_timeout_sec,
            "agent_timeout_mode": _timeout_mode(config.agent_timeout_sec),
            "timed_out_specialists": timed_out_specialists,
            "cycle_summaries": cycle_summaries,
            "negotiation_monitor": monitor,
            "meeting_monitor_paths": meeting_monitor_paths,
            "latest_artifacts": latest_artifacts,
            "escalations": unresolved_escalations,
            "escalations_path": str(turn_dir / "escalations.json"),
        }
        blocked_path = turn_dir / "blocked-reasons.json"
        write_text(blocked_path, stable_json(blocked_payload) + "\n")
        blocked_report = orchestration_report.render_blocked_report(
            project_id=config.project_id,
            message=config.message,
            status=block_status,
            reasons=blocked_reasons,
            contributions=contributions,
            web_evidence_count=len(evidence_rows),
            artifact_citation_count=len(artifact_citations),
            turn_dir=turn_dir,
            timed_out_specialists=timed_out_specialists,
            escalations=unresolved_escalations,
        )
        blocked_report_path = turn_dir / "blocked-report.md"
        write_text(blocked_report_path, blocked_report)
        raise FabricError(
            "BLOCKED[{0}] blocked_report={1} blocked_reasons={2}".format(
                block_status,
                blocked_report_path,
                blocked_path,
            )
        )

    constraints = _load_constraints(project_root)
    answer = _render_group_mode_answer(
        project_id=config.project_id,
        message=config.message,
        constraints=constraints,
        delegation_ledger=delegation,
        negotiation_stats=negotiation_stats,
        evidence_rows=evidence_rows,
        artifact_citations=artifact_citations,
        contributions=contributions,
        turn_dir=turn_dir,
        project_root=project_root,
    )

    quality = _quality_gate(
        mode=mode,
        answer_text=answer,
        detail_profile=str(policy.get("detail_profile") or "publication-grade"),
        evidence_rows=evidence_rows,
        artifact_citations=artifact_citations,
        negotiation_stats=negotiation_stats,
        delegation_ledger=delegation,
        contributions=contributions,
        turn_dir=turn_dir,
    )
    quality["cycles_executed"] = cycle
    quality["meeting_cycles"] = len(meeting_outputs)
    quality["agent_timeout_sec"] = config.agent_timeout_sec
    quality["agent_timeout_mode"] = _timeout_mode(config.agent_timeout_sec)
    quality["timed_out_specialist_count"] = len(timed_out_specialists)

    if not quality.get("passed"):
        quality["block_status"] = "BLOCKED_QUALITY_GATE"
        quality["block_reasons"] = ["group-mode final answer failed quality checks"]
        write_text(turn_dir / "final-answer-quality.json", stable_json(quality) + "\n")
        blocked_path = turn_dir / "blocked-reasons.json"
        write_text(
            blocked_path,
            stable_json(
                {
                    "schema_version": "3.1",
                    "status": "BLOCKED_QUALITY_GATE",
                    "project_id": config.project_id,
                    "group": primary_group,
                    "generated_at": now_iso(),
                    "reasons": ["group-mode final answer failed quality checks"],
                    "quality_checks": quality.get("checks", {}),
                    "timed_out_specialists": timed_out_specialists,
                    "latest_artifacts": latest_artifacts,
                }
            )
            + "\n",
        )
        blocked_report_path = turn_dir / "blocked-report.md"
        write_text(
            blocked_report_path,
            orchestration_report.render_blocked_report(
                project_id=config.project_id,
                message=config.message,
                status="BLOCKED_QUALITY_GATE",
                reasons=["group-mode final answer failed quality checks"],
                contributions=contributions,
                web_evidence_count=len(evidence_rows),
                artifact_citation_count=len(artifact_citations),
                turn_dir=turn_dir,
                timed_out_specialists=timed_out_specialists,
                escalations=unresolved_escalations,
            ),
        )
        raise FabricError(
            "BLOCKED[BLOCKED_QUALITY_GATE] blocked_report={0} blocked_reasons={1}".format(
                blocked_report_path,
                blocked_path,
            )
        )

    final_dir = turn_dir / "final"
    final_dir.mkdir(parents=True, exist_ok=True)
    final_path = turn_dir / "final-exposed-answer.md"
    full_report_path = final_dir / "full-report.md"
    full_report_json_path = final_dir / "full-report.json"
    key_points_path = final_dir / "key-points.txt"

    write_text(final_path, answer)
    write_text(full_report_path, answer)
    write_text(
        full_report_json_path,
        stable_json(
            {
                "schema_version": "3.1",
                "project_id": config.project_id,
                "group": primary_group,
                "generated_at": now_iso(),
                "cycles": cycle_summaries,
                "meetings": meeting_outputs,
                "quality": quality,
                "negotiation_monitor": monitor,
                "agent_timeout_sec": config.agent_timeout_sec,
                "agent_timeout_mode": _timeout_mode(config.agent_timeout_sec),
                "timed_out_specialists": timed_out_specialists,
                "escalations": unresolved_escalations,
                "latest_artifacts": latest_artifacts,
                "paths": {
                    "final_markdown": str(full_report_path),
                    "key_points": str(key_points_path),
                    "negotiation_monitor_json": meeting_monitor_paths["json_path"],
                    "negotiation_monitor_md": meeting_monitor_paths["md_path"],
                    "wait_state_latest": str(turn_dir / "wait-state.latest.json"),
                    "cooperation_ledger_latest": str(turn_dir / "cooperation-ledger.latest.ndjson"),
                    "group_head_sessions_latest": str(turn_dir / "group-head-sessions.latest.json"),
                    "specialist_sessions_latest": str(turn_dir / "specialist-sessions.latest.json"),
                    "escalations": str(turn_dir / "escalations.json"),
                },
            }
        )
        + "\n",
    )
    write_text(turn_dir / "final-answer-quality.json", stable_json(quality) + "\n")
    key_points = orchestration_report.render_key_points(
        project_id=config.project_id,
        selected_groups=selected_groups,
        final_report_path=full_report_path,
        turn_dir=turn_dir,
    )
    write_text(key_points_path, key_points)

    return {
        "mode": mode,
        "project_id": config.project_id,
        "group": primary_group,
        "selected_groups": selected_groups,
        "turn_dir": str(turn_dir),
        "final_answer_path": str(final_path),
        "full_report_path": str(full_report_path),
        "full_report_json_path": str(full_report_json_path),
        "key_points_path": str(key_points_path),
        "quality_path": str(turn_dir / "final-answer-quality.json"),
        "quality": quality,
        "negotiation_monitor": monitor,
        "delegation_path": str(turn_dir / "delegation-ledger.json"),
        "negotiation_path": str(turn_dir / "negotiation-sequence.md"),
        "evidence_path": str(turn_dir / "group-evidence-index.json"),
        "layered_runtime": runtime_result,
        "latest_artifacts": latest_artifacts,
        "escalations": unresolved_escalations,
        "escalations_path": str(turn_dir / "escalations.json"),
        "cycles": cycle_summaries,
    }
