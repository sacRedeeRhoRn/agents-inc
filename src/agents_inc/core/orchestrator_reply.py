from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from agents_inc.core.fabric_lib import (
    FabricError,
    build_dispatch_plan,
    execution_mode_from_manifest,
    load_yaml,
    slugify,
    stable_json,
    write_text,
)
from agents_inc.core.head_meeting import HeadMeetingConfig, run_head_meeting
from agents_inc.core.layered_runtime import LayeredRuntimeConfig, run_layered_runtime
from agents_inc.core.model_profiles import (
    DEFAULT_HEAD_MODEL,
    DEFAULT_HEAD_REASONING_EFFORT,
    DEFAULT_SPECIALIST_MODEL,
    DEFAULT_SPECIALIST_REASONING_EFFORT,
    normalize_model_slug,
    normalize_reasoning_effort,
)
from agents_inc.core.negotiation_monitor import NegotiationCycleRecord
from agents_inc.core.orchestration import report as orchestration_report
from agents_inc.core.orchestration.cycle_engine import build_cycle_summary
from agents_inc.core.orchestration.meeting import build_negotiation_monitor
from agents_inc.core.orchestration.turn_router import (
    resolve_primary_group as resolve_primary_group_router,
)
from agents_inc.core.orchestration.turn_router import (
    selected_groups_from_manifest,
)
from agents_inc.core.orchestrator_state import mark_orchestrator_saved
from agents_inc.core.response_policy import (
    classify_request_mode,
    ensure_response_policy,
    flatten_specialist_sessions,
    lookup_specialist_session,
    strip_non_group_prefix,
    upsert_specialist_sessions,
)
from agents_inc.core.session_compaction import compact_session
from agents_inc.core.session_state import (
    default_project_index_path,
    load_checkpoint,
    now_iso,
    resolve_state_project_root,
    write_checkpoint,
)
from agents_inc.core.token_usage import write_turn_token_usage_report
from agents_inc.core.util.edges import resolve_handoff_edges

OBJECTIVE_COVERAGE_THRESHOLD = 0.8
OBJECTIVE_RESPONSE_STATUS_VALUES = {"ANSWERED", "PARTIAL", "BLOCKED"}
CONSENSUS_CLUSTER_SIMILARITY = 0.45
CONSENSUS_MIN_SIGNAL_WORDS = 6


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
    max_cycles: int = 0
    heartbeat_sec: int = 30
    abort_file: Optional[Path] = None
    require_negotiation: bool = True
    audit: bool = False
    specialist_model: str = DEFAULT_SPECIALIST_MODEL
    specialist_reasoning_effort: str | None = DEFAULT_SPECIALIST_REASONING_EFFORT
    head_model: str = DEFAULT_HEAD_MODEL
    head_reasoning_effort: str | None = DEFAULT_HEAD_REASONING_EFFORT
    web_search_policy: str = "web-role-only"
    progress_callback: Callable[[dict], None] | None = None
    project_index_path: Path | None = None
    resume_from_cycle: int = 0
    resume_group_objectives: Dict[str, str] | None = None
    resume_previous_cycle_summaries: List[dict] | None = None


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
    *,
    base_objective: str,
    selected_groups: List[str],
    group_manifests: Dict[str, dict],
    execution_mode: str,
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
            ]
        )
        if execution_mode == "light":
            lines.extend(
                [
                    "- head-controller executes group objective directly (no specialist delegation)",
                    "- group exposed summary/handoff/integration notes",
                    "- claim-level citations for published assertions",
                ]
            )
        else:
            lines.extend(
                [
                    "- specialist internal work/handoff artifacts",
                    "- group exposed summary/handoff/integration notes",
                    "- claim-level citations for published assertions",
                ]
            )
        lines.extend(
            [
                "",
                "Execution mode:",
                f"- {execution_mode}",
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


def _normalize_web_search_policy(value: str | None) -> str:
    policy = str(value or "").strip().lower()
    if policy in {"all-enabled", "web-role-only"}:
        return policy
    return "web-role-only"


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


def _load_latest_router_call(project_root: Path) -> str:
    try:
        checkpoint = load_checkpoint(project_root, "latest")
    except Exception:
        return ""
    return str(checkpoint.get("router_call") or "").strip()


def _normalize_resume_group_objectives(
    *,
    selected_groups: List[str],
    default_objectives: Dict[str, str],
    resume_objectives: Dict[str, str] | None,
) -> Dict[str, str]:
    if not isinstance(resume_objectives, dict):
        return dict(default_objectives)
    resolved: Dict[str, str] = {}
    for group_id in selected_groups:
        candidate = resume_objectives.get(group_id)
        if isinstance(candidate, str) and candidate.strip():
            resolved[group_id] = candidate
            continue
        resolved[group_id] = str(default_objectives.get(group_id) or "")
    return resolved


def _normalize_resume_cycle_summaries(
    resume_rows: List[dict] | None,
) -> Tuple[List[dict], int]:
    rows: List[dict] = []
    max_cycle_id = 0
    if not isinstance(resume_rows, list):
        return rows, max_cycle_id
    for item in resume_rows:
        if not isinstance(item, dict):
            continue
        copied = dict(item)
        rows.append(copied)
        try:
            cycle_id = int(copied.get("cycle_id", 0) or 0)
        except Exception:
            cycle_id = 0
        if cycle_id > max_cycle_id:
            max_cycle_id = cycle_id
    return rows, max_cycle_id


def _auto_checkpoint_blocked_turn(
    *,
    config: OrchestratorReplyConfig,
    project_root: Path,
    project_id: str,
    selected_groups: List[str],
    primary_group: str,
    turn_dir: Path,
    block_status: str,
    blocked_reasons: List[str],
    blocked_reasons_path: Path,
    blocked_report_path: Path,
    latest_artifacts: Dict[str, str],
    group_objectives: Dict[str, str],
    cycle_summaries: List[dict],
    cycles_executed: int,
) -> dict:
    try:
        index_path = default_project_index_path(
            str(config.project_index_path) if config.project_index_path else None
        )
        constraints = _load_constraints(project_root)
        router_call = _load_latest_router_call(project_root)
        checkpoint_latest_artifacts = dict(latest_artifacts)
        checkpoint_latest_artifacts.update(
            {
                "turn_dir": str(turn_dir),
                "blocked_reasons": str(blocked_reasons_path),
                "blocked_report": str(blocked_report_path),
                "delegation_ledger": str(turn_dir / "delegation-ledger.json"),
                "evidence_index": str(turn_dir / "group-evidence-index.json"),
                "quality_report": str(turn_dir / "final-answer-quality.json"),
            }
        )
        blocked_resume = {
            "enabled": True,
            "blocked_status": block_status,
            "objective": config.message,
            "turn_dir": str(turn_dir),
            "resume_from_cycle": max(0, int(cycles_executed)),
            "group_objectives": group_objectives,
            "cycle_summaries": cycle_summaries,
            "blocked_reasons_path": str(blocked_reasons_path),
            "blocked_report_path": str(blocked_report_path),
            "updated_at": now_iso(),
        }
        payload = {
            "project_id": project_id,
            "project_root": str(project_root),
            "fabric_root": str(config.fabric_root),
            "task": config.message,
            "constraints": constraints,
            "selected_groups": selected_groups,
            "primary_group": primary_group,
            "group_order_recommendation": selected_groups,
            "router_call": router_call,
            "latest_artifacts": checkpoint_latest_artifacts,
            "pending_actions": [
                f"Review blocked report: {blocked_report_path}",
                (
                    "Resume with `agents-inc resume {0}` to auto-restart from cycle {1}.".format(
                        project_id,
                        max(0, int(cycles_executed) + 1),
                    )
                ),
            ],
            "blocked_resume": blocked_resume,
            "blocked_summary": {
                "status": block_status,
                "reasons": blocked_reasons,
                "cycles_executed": max(0, int(cycles_executed)),
            },
            "updated_at": now_iso(),
        }
        checkpoint = write_checkpoint(
            project_root=project_root,
            payload=payload,
            project_index_path=index_path,
        )
        compact = compact_session(
            project_root=project_root,
            payload={
                **payload,
                "latest_checkpoint_id": str(checkpoint["checkpoint_id"]),
                "latest_checkpoint_path": str(checkpoint["checkpoint_path"]),
            },
            selected_groups=selected_groups,
        )
        mark_orchestrator_saved(
            project_root,
            project_id=project_id,
            checkpoint_id=str(checkpoint["checkpoint_id"]),
        )
        return {
            "checkpoint_id": str(checkpoint["checkpoint_id"]),
            "checkpoint_path": str(checkpoint["checkpoint_path"]),
            "compact_id": str(compact["compact_id"]),
            "compact_path": str(compact["compact_path"]),
        }
    except Exception as exc:  # noqa: BLE001
        return {"error": str(exc)}


def _build_delegation_ledger(
    *,
    project_id: str,
    message: str,
    group_manifests: Dict[str, dict],
    execution_mode: str,
) -> dict:
    rows = []
    for group_id in sorted(group_manifests.keys()):
        dispatch = build_dispatch_plan(
            project_id,
            group_id,
            message,
            group_manifests[group_id],
            execution_mode=execution_mode,
        )
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


def _build_evidence_lookup(payload: dict) -> Dict[str, dict]:
    refs = payload.get("evidence_refs")
    if not isinstance(refs, list):
        return {}
    out: Dict[str, dict] = {}
    for row in refs:
        if not isinstance(row, dict):
            continue
        evidence_id = str(
            row.get("evidence_id") or row.get("id") or row.get("key") or ""
        ).strip()
        if not evidence_id:
            continue
        out[evidence_id] = dict(row)
    return out


def _evidence_ids_from_claim(claim: dict) -> List[str]:
    rows = claim.get("evidence_ids")
    if not isinstance(rows, list):
        return []
    out: List[str] = []
    for item in rows:
        text = str(item or "").strip()
        if text and text not in out:
            out.append(text)
    return out


def _citation_from_claim(claim: dict, evidence_lookup: Optional[Dict[str, dict]] = None) -> List[str]:
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
    if evidence_lookup:
        for evidence_id in _evidence_ids_from_claim(claim):
            row = evidence_lookup.get(evidence_id)
            if not isinstance(row, dict):
                continue
            text = str(
                row.get("citation")
                or row.get("url")
                or row.get("source_url")
                or row.get("doi")
                or ""
            ).strip()
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


def _normalize_response_status(value: object) -> str:
    text = str(value or "").strip().upper().replace("-", "_").replace(" ", "_")
    if not text:
        return ""
    if text in OBJECTIVE_RESPONSE_STATUS_VALUES:
        return text
    if text in {"COMPLETE", "PASS", "RESOLVED", "SATISFIED", "DONE"}:
        return "ANSWERED"
    if text in {"PARTIALLY_RESOLVED", "INCOMPLETE", "UNRESOLVED", "CONDITIONAL"}:
        return "PARTIAL"
    if text.startswith("BLOCKED") or text in {"FAILED", "REJECTED", "NEEDS_EVIDENCE"}:
        return "BLOCKED"
    return ""


def _parse_objective_coverage(value: object) -> float | None:
    if isinstance(value, (int, float)):
        raw = float(value)
        if raw > 1.0:
            raw = raw / 100.0
        return max(0.0, min(1.0, raw))
    text = str(value or "").strip()
    if not text:
        return None
    if text.endswith("%"):
        text = text[:-1].strip()
        try:
            return max(0.0, min(1.0, float(text) / 100.0))
        except Exception:
            return None
    try:
        raw = float(text)
    except Exception:
        return None
    if raw > 1.0:
        raw = raw / 100.0
    return max(0.0, min(1.0, raw))


def _parse_bool(value: object, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value or "").strip().lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off"}:
        return False
    return bool(default)


def _response_status_from_text(*, status: str, summary_text: str, notes_text: str) -> str:
    normalized = _normalize_response_status(status)
    if normalized:
        return normalized
    combined = f"{summary_text}\n{notes_text}".lower()
    if any(
        hint in combined
        for hint in (
            "blocked",
            "needs evidence",
            "insufficient evidence",
            "cannot conclude",
            "unable to conclude",
            "not enough evidence",
        )
    ):
        return "BLOCKED"
    if any(
        hint in combined
        for hint in (
            "partial",
            "incomplete",
            "conditional",
            "unresolved",
            "next cycle",
            "assumption",
        )
    ):
        return "PARTIAL"
    return "PARTIAL"


def _extract_recommended_actions(payload: dict) -> List[str]:
    rows: List[str] = []
    for key in ("recommended_actions", "next_actions", "actions", "new_actions"):
        value = payload.get(key)
        if not isinstance(value, list):
            continue
        for item in value:
            text = str(item or "").strip()
            if text and text not in rows:
                rows.append(text)
    return rows


def _objective_tokens(text: str) -> List[str]:
    out: List[str] = []
    for token in re.findall(r"[a-z0-9]+", str(text or "").lower()):
        if len(token) < 4:
            continue
        if token in {
            "with",
            "from",
            "that",
            "this",
            "your",
            "what",
            "when",
            "where",
            "which",
            "have",
            "will",
            "would",
            "should",
            "could",
            "into",
            "over",
            "under",
            "using",
            "based",
            "only",
            "hours",
            "time",
            "give",
            "want",
            "make",
            "include",
            "criteria",
        }:
            continue
        if token not in out:
            out.append(token)
    return out


def _estimate_objective_coverage(objective: str, response_text: str) -> float:
    objective_terms = _objective_tokens(objective)
    if not objective_terms:
        return 1.0 if response_text.strip() else 0.0
    response_terms = set(_objective_tokens(response_text))
    if not response_terms:
        return 0.0
    overlap = sum(1 for token in objective_terms if token in response_terms)
    return round(overlap / len(objective_terms), 3)


def _truncate(value: str, max_chars: int = 320) -> str:
    text = str(value or "").strip().replace("\n", " ")
    if not text:
        return ""
    if len(text) <= max_chars:
        return text
    cut = text[:max_chars].rstrip()
    if " " in cut:
        cut = cut.rsplit(" ", 1)[0]
    return cut.rstrip(".,;:") + "..."


def _fallback_objective_response(*, summary_text: str, claims: List[dict], group_id: str) -> str:
    candidate = _truncate(summary_text, max_chars=300)
    if candidate:
        return candidate
    for claim in claims:
        if not isinstance(claim, dict):
            continue
        text = _truncate(str(claim.get("claim") or ""), max_chars=300)
        if text:
            return text
    return f"{group_id} did not publish an explicit objective response."


def _collect_group_contributions(project_dir: Path, groups: List[str], objective: str) -> List[dict]:
    rows: List[dict] = []
    for group_id in groups:
        exposed_dir = project_dir / "agent-groups" / group_id / "exposed"
        group_manifest_path = project_dir / "agent-groups" / group_id / "group.yaml"
        summary_path = exposed_dir / "summary.md"
        handoff_path = exposed_dir / "handoff.json"
        notes_path = exposed_dir / "INTEGRATION_NOTES.md"

        group_manifest = load_yaml(group_manifest_path) if group_manifest_path.exists() else {}
        if not isinstance(group_manifest, dict):
            group_manifest = {}
        head_persona = group_manifest.get("head", {})
        if isinstance(head_persona, dict):
            head_persona = head_persona.get("persona", {})
        else:
            head_persona = {}
        if not isinstance(head_persona, dict):
            head_persona = {}
        try:
            persona_threshold = float(head_persona.get("confidence_threshold") or 0.8)
        except Exception:
            persona_threshold = 0.8
        persona_threshold = max(0.0, min(1.0, persona_threshold))
        persona_override_policy = str(head_persona.get("override_policy") or "head-meeting-only")

        summary_text = _safe_read(summary_path)
        notes_text = _safe_read(notes_path)
        reasons: List[str] = []
        structural_reasons: List[str] = []
        handoff_payload: dict = {}

        if not handoff_path.exists():
            reasons.append("missing exposed/handoff.json")
            structural_reasons.append("missing exposed/handoff.json")
        else:
            loaded = load_yaml(handoff_path)
            if not isinstance(loaded, dict):
                reasons.append("exposed/handoff.json is not a mapping")
                structural_reasons.append("exposed/handoff.json is not a mapping")
            else:
                handoff_payload = loaded

        status = str(handoff_payload.get("status") or "").strip().upper()
        if status in {"", "PENDING"}:
            reasons.append("handoff status is pending")
            structural_reasons.append("handoff status is pending")

        artifacts = handoff_payload.get("artifacts")
        artifact_preview: List[str] = []
        if isinstance(artifacts, list):
            for item in artifacts:
                preview = _parse_artifact_preview(item)
                if preview and preview not in artifact_preview:
                    artifact_preview.append(preview)

        claims_payload = handoff_payload.get("claims")
        if not isinstance(claims_payload, list):
            claims_payload = handoff_payload.get("claims_with_citations")
        claims: List[dict] = []
        if isinstance(claims_payload, list):
            for item in claims_payload:
                if isinstance(item, dict):
                    claims.append(item)
        evidence_lookup = _build_evidence_lookup(handoff_payload)

        citation_refs: List[str] = []
        claim_preview_rows: List[dict] = []
        evidence_preview_rows: List[dict] = []
        for evidence_id, row in sorted(evidence_lookup.items()):
            citation = str(
                row.get("citation")
                or row.get("url")
                or row.get("source_url")
                or row.get("doi")
                or ""
            ).strip()
            evidence_preview_rows.append(
                {
                    "evidence_id": evidence_id,
                    "citation": citation,
                    "title": str(row.get("title") or "").strip(),
                    "source_type": str(row.get("source_type") or "").strip(),
                }
            )
        for claim in claims:
            refs = _citation_from_claim(claim, evidence_lookup=evidence_lookup)
            evidence_ids = _evidence_ids_from_claim(claim)
            for ref in refs:
                if ref not in citation_refs:
                    citation_refs.append(ref)
            preview = _claim_preview(claim)
            if preview:
                claim_preview_rows.append(
                    {
                        "text": preview,
                        "evidence_ids": evidence_ids,
                        "citations": refs,
                    }
                )

        summary_ready = (
            bool(summary_text) and "pending head publication" not in summary_text.lower()
        )
        has_substance = bool(artifact_preview) or bool(claim_preview_rows) or summary_ready
        if not has_substance:
            reasons.append("no published artifacts/claims in exposed handoff")

        response_status = _normalize_response_status(
            handoff_payload.get("response_status")
            or handoff_payload.get("objective_status")
            or handoff_payload.get("result_status")
        )
        if not response_status:
            response_status = _response_status_from_text(
                status=status,
                summary_text=summary_text,
                notes_text=notes_text,
            )

        objective_response = str(
            handoff_payload.get("objective_response")
            or handoff_payload.get("response_to_objective")
            or handoff_payload.get("decision_summary")
            or ""
        ).strip()
        if not objective_response:
            objective_response = _fallback_objective_response(
                summary_text=summary_text,
                claims=claims,
                group_id=group_id,
            )
        objective_response = _truncate(objective_response, max_chars=320)

        decision_summary = str(handoff_payload.get("decision_summary") or "").strip()
        if not decision_summary:
            decision_summary = objective_response
        decision_summary = _truncate(decision_summary, max_chars=320)

        recommended_actions = _extract_recommended_actions(handoff_payload)
        if not recommended_actions:
            recommended_actions = [
                "Tighten objective-specific evidence and rerun the next cycle."
            ]

        objective_coverage = _parse_objective_coverage(handoff_payload.get("objective_coverage"))
        if objective_coverage is None:
            coverage_text = " ".join(
                [
                    objective_response,
                    decision_summary,
                    summary_text,
                    notes_text,
                    " ".join(
                        str(claim.get("claim") or "") for claim in claims if isinstance(claim, dict)
                    ),
                ]
            )
            objective_coverage = _estimate_objective_coverage(objective, coverage_text)

        if response_status == "ANSWERED":
            objective_coverage = max(objective_coverage, OBJECTIVE_COVERAGE_THRESHOLD)
        elif response_status == "BLOCKED":
            objective_coverage = min(objective_coverage, 0.49)
        elif response_status == "PARTIAL":
            objective_coverage = min(objective_coverage, 0.79)

        persona_id = str(handoff_payload.get("persona_id") or "").strip()
        persona_stance = _truncate(str(handoff_payload.get("persona_stance") or "").strip(), max_chars=220)
        persona_challenge = _truncate(
            str(handoff_payload.get("persona_challenge") or "").strip(),
            max_chars=220,
        )
        raw_persona_confidence = _parse_objective_coverage(handoff_payload.get("persona_confidence"))
        persona_confidence = raw_persona_confidence
        if persona_confidence is None:
            persona_confidence = persona_threshold
        persona_confidence = max(0.0, min(1.0, float(persona_confidence)))
        persona_override_evidence = _parse_bool(
            handoff_payload.get("persona_override_evidence"),
            default=False,
        )
        persona_missing: List[str] = []
        if not persona_id:
            persona_missing.append("persona_id")
        if not persona_stance:
            persona_missing.append("persona_stance")
        if not persona_challenge:
            persona_missing.append("persona_challenge")
        if raw_persona_confidence is None:
            persona_missing.append("persona_confidence")
        if persona_missing:
            reasons.append(
                "persona contract incomplete ({0})".format(", ".join(persona_missing))
            )
        persona_contract_valid = len(persona_missing) == 0
        persona_override_allowed = bool(
            persona_contract_valid
            and persona_override_evidence
            and persona_override_policy == "head-meeting-only"
            and persona_confidence >= persona_threshold
        )

        if response_status != "ANSWERED":
            reasons.append(f"objective not fully satisfied ({response_status})")
        if objective_coverage < OBJECTIVE_COVERAGE_THRESHOLD and not persona_override_allowed:
            reasons.append(
                "objective coverage below threshold ({0:.2f} < {1:.2f})".format(
                    objective_coverage, OBJECTIVE_COVERAGE_THRESHOLD
                )
            )

        structural_valid = len(structural_reasons) == 0
        valid = not reasons
        rows.append(
            {
                "group_id": group_id,
                "valid": valid,
                "reasons": reasons,
                "structural_valid": structural_valid,
                "structural_reasons": structural_reasons,
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
                "evidence_refs": evidence_preview_rows,
                "response_status": response_status,
                "objective_response": objective_response,
                "decision_summary": decision_summary,
                "recommended_actions": recommended_actions[:8],
                "objective_coverage": round(max(0.0, min(1.0, float(objective_coverage))), 3),
                "persona_id": persona_id,
                "persona_stance": persona_stance,
                "persona_challenge": persona_challenge,
                "persona_confidence": round(persona_confidence, 3),
                "persona_override_evidence": bool(persona_override_evidence),
                "persona_override_allowed": bool(persona_override_allowed),
                "persona_override_policy": persona_override_policy,
                "persona_confidence_threshold": round(persona_threshold, 3),
                "persona_contract_valid": persona_contract_valid,
            }
        )
    return rows


def _effective_contribution_valid(row: dict) -> bool:
    if not isinstance(row, dict):
        return False
    return bool(row.get("valid")) or bool(row.get("persona_override_allowed"))


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
        valid = _effective_contribution_valid(row)
        if valid:
            contributed.append(group_id)
        else:
            missing.append(group_id)
        status_map[group_id] = {
            "valid": valid,
            "persona_override_allowed": bool(row.get("persona_override_allowed")),
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
        effective_valid = _effective_contribution_valid(row)
        status_label = "valid"
        if not bool(row.get("valid")) and bool(row.get("persona_override_allowed")):
            status_label = "valid (persona-override)"
        elif not effective_valid:
            status_label = "blocked"
        lines.append(f"### {group_id}")
        lines.append("- contribution status: `{0}`".format(status_label))
        lines.append("- exposed handoff: `{0}`".format(row.get("handoff_path", "")))
        lines.append("- exposed summary: `{0}`".format(row.get("summary_path", "")))
        lines.append(
            "- artifact_count: `{0}` | claim_count: `{1}` | citation_count: `{2}`".format(
                row.get("artifact_count", 0),
                row.get("claim_count", 0),
                row.get("citation_count", 0),
            )
        )
        lines.append(
            "- objective_status: `{0}` | objective_coverage: `{1}`".format(
                row.get("response_status", "UNKNOWN"),
                row.get("objective_coverage", 0.0),
            )
        )
        objective_response = str(row.get("objective_response") or "").strip()
        if objective_response:
            lines.append("- objective_response:")
            lines.append(f"  {objective_response}")
        decision_summary = str(row.get("decision_summary") or "").strip()
        if decision_summary and decision_summary != objective_response:
            lines.append("- decision_summary:")
            lines.append(f"  {decision_summary}")
        persona_stance = str(row.get("persona_stance") or "").strip()
        persona_challenge = str(row.get("persona_challenge") or "").strip()
        if persona_stance:
            lines.append("- persona_stance:")
            lines.append(f"  {persona_stance}")
        if persona_challenge:
            lines.append("- persona_challenge:")
            lines.append(f"  {persona_challenge}")

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
                evidence_ids = claim.get("evidence_ids", [])
                evidence_text = (
                    ", ".join(str(item) for item in evidence_ids[:3])
                    if isinstance(evidence_ids, list) and evidence_ids
                    else ""
                )
                refs = claim.get("citations", [])
                ref_text = ", ".join(str(item) for item in refs[:2]) if refs else "no-citation"
                if evidence_text:
                    lines.append(f"  - {text} [evidence_ids: {evidence_text}] [refs: {ref_text}]")
                else:
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
            evidence_ids = first.get("evidence_ids", [])
            if isinstance(evidence_ids, list):
                refs = [str(item) for item in evidence_ids if str(item).strip()]
            if not refs:
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
        "| Evidence ID | Source Type | Provider/Group | Year | Title/Ref | URL |",
        "|---|---|---|---:|---|---|",
    ]

    for row in web_rows:
        title = str(row.get("title", "")).replace("|", "/")
        lines.append(
            "| {0} | web | {1} | {2} | {3} | {4} |".format(
                str(row.get("evidence_id") or ""),
                row.get("provider", ""),
                row.get("year", "-"),
                title,
                row.get("url", ""),
            )
        )

    for row in artifact_citations:
        lines.append(
            "| {0} | artifact | {1} | - | {2} | {3} |".format(
                str(row.get("evidence_id") or ""),
                row.get("group_id", ""),
                str(row.get("citation") or "").replace("|", "/"),
                row.get("url", ""),
            )
        )

    if len(lines) == 2:
        lines.append("| none | none | none | - | no evidence rows captured | - |")
    return "\n".join(lines)


def _collect_artifact_citations(contributions: List[dict]) -> List[dict]:
    rows: List[dict] = []
    seen: set = set()
    seen_citation: set = set()
    for row in contributions:
        group_id = str(row.get("group_id") or "")
        evidence_rows = row.get("evidence_refs", [])
        if isinstance(evidence_rows, list):
            for evidence in evidence_rows:
                if not isinstance(evidence, dict):
                    continue
                evidence_id = str(evidence.get("evidence_id") or "").strip()
                citation = str(evidence.get("citation") or "").strip()
                key = (group_id, evidence_id, citation)
                if key in seen:
                    continue
                seen.add(key)
                if citation:
                    seen_citation.add((group_id, citation))
                rows.append(
                    {
                        "group_id": group_id,
                        "evidence_id": evidence_id,
                        "citation": citation,
                        "url": citation if citation.startswith("http") else "",
                    }
                )
        refs = row.get("citation_refs", [])
        if not isinstance(refs, list):
            continue
        for ref in refs:
            text = str(ref).strip()
            if not text:
                continue
            if (group_id, text) in seen_citation:
                continue
            key = (group_id, "", text)
            if key in seen:
                continue
            seen.add(key)
            seen_citation.add((group_id, text))
            url = text if text.startswith("http") else ""
            rows.append(
                {
                    "group_id": group_id,
                    "evidence_id": "",
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


def _overall_objective_status(contributions: List[dict]) -> str:
    statuses = [str(row.get("response_status") or "") for row in contributions if isinstance(row, dict)]
    normalized = [status for status in statuses if status in OBJECTIVE_RESPONSE_STATUS_VALUES]
    if not normalized:
        return "PARTIAL"
    if any(status == "BLOCKED" for status in normalized):
        return "BLOCKED"
    if any(status == "PARTIAL" for status in normalized):
        return "PARTIAL"
    return "ANSWERED"


def _collect_next_actions(contributions: List[dict], *, limit: int = 5) -> List[str]:
    rows: List[str] = []
    for row in contributions:
        actions = row.get("recommended_actions", [])
        if not isinstance(actions, list):
            continue
        for action in actions:
            text = str(action or "").strip()
            if text and text not in rows:
                rows.append(text)
            if len(rows) >= limit:
                return rows
    return rows


def _collect_direct_answers(contributions: List[dict], *, limit: int = 8) -> List[dict]:
    rows: List[dict] = []
    for row in contributions:
        if not isinstance(row, dict):
            continue
        group_id = str(row.get("group_id") or "").strip()
        if not group_id:
            continue
        response = _truncate(str(row.get("objective_response") or "").strip(), max_chars=320)
        if not response:
            response = _truncate(str(row.get("decision_summary") or "").strip(), max_chars=320)
        if not response:
            continue
        rows.append(
            {
                "group_id": group_id,
                "response": response,
                "response_status": str(row.get("response_status") or "UNKNOWN"),
                "objective_coverage": float(row.get("objective_coverage") or 0.0),
                "persona_confidence": float(row.get("persona_confidence") or 0.0),
            }
        )
        if len(rows) >= limit:
            break
    return rows


def _consensus_tokens(text: object) -> set[str]:
    return set(_objective_tokens(str(text or "")))


def _token_jaccard(left: set[str], right: set[str]) -> float:
    if not left and not right:
        return 1.0
    if not left or not right:
        return 0.0
    union = left | right
    if not union:
        return 0.0
    return len(left & right) / len(union)


def _split_signal_lines(text: str, *, limit: int = 6) -> List[str]:
    rows: List[str] = []
    for raw in re.split(r"[\r\n]+|(?<=[.!?])\s+", str(text or "").strip()):
        candidate = _clean_signal_text(raw)
        if not candidate:
            continue
        if len(re.findall(r"\b\w+\b", candidate)) < CONSENSUS_MIN_SIGNAL_WORDS:
            continue
        if candidate not in rows:
            rows.append(candidate)
        if len(rows) >= limit:
            break
    return rows


def _clean_signal_text(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    text = re.sub(r"^[#>\-\*\s\d\.\)\(]+", "", text)
    text = text.replace("`", "")
    text = re.sub(r"\bfor\s+[a-z0-9\-]+/[a-z0-9\-]+\b", "", text, flags=re.IGNORECASE)
    text = " ".join(text.split()).strip()
    return text


def _extract_consensus_signals(contributions: List[dict]) -> List[dict]:
    rows: List[dict] = []
    for row in contributions:
        if not isinstance(row, dict):
            continue
        group_id = str(row.get("group_id") or "").strip()
        if not group_id:
            continue
        added = 0
        claim_preview = row.get("claim_preview", [])
        if isinstance(claim_preview, list):
            for claim in claim_preview:
                if not isinstance(claim, dict):
                    continue
                text = _truncate(_clean_signal_text(claim.get("text")), max_chars=260)
                if not text:
                    continue
                tokens = _consensus_tokens(text)
                if len(tokens) < CONSENSUS_MIN_SIGNAL_WORDS:
                    continue
                rows.append(
                    {
                        "group_id": group_id,
                        "text": text,
                        "tokens": tokens,
                        "citations": (
                            [str(item).strip() for item in claim.get("citations", []) if str(item).strip()]
                            if isinstance(claim.get("citations"), list)
                            else []
                        ),
                        "coverage": float(row.get("objective_coverage") or 0.0),
                        "citation_count": int(row.get("citation_count", 0)),
                        "claim_count": int(row.get("claim_count", 0)),
                    }
                )
                added += 1
                if added >= 4:
                    break
        if added > 0:
            continue
        for sentence in _split_signal_lines(str(row.get("objective_response") or ""), limit=3):
            tokens = _consensus_tokens(sentence)
            if len(tokens) < CONSENSUS_MIN_SIGNAL_WORDS:
                continue
            rows.append(
                {
                    "group_id": group_id,
                    "text": _truncate(sentence, max_chars=260),
                    "tokens": tokens,
                    "citations": [
                        str(item).strip()
                        for item in row.get("citation_refs", [])[:5]
                        if str(item).strip()
                    ],
                    "coverage": float(row.get("objective_coverage") or 0.0),
                    "citation_count": int(row.get("citation_count", 0)),
                    "claim_count": int(row.get("claim_count", 0)),
                }
            )
            added += 1
            if added >= 3:
                break
    return rows


def _cluster_consensus_signals(signals: List[dict]) -> List[dict]:
    clusters: List[dict] = []
    for signal in signals:
        if not isinstance(signal, dict):
            continue
        tokens = signal.get("tokens")
        if not isinstance(tokens, set) or not tokens:
            continue
        text = str(signal.get("text") or "").strip()
        if not text:
            continue
        best_index = -1
        best_similarity = 0.0
        for index, cluster in enumerate(clusters):
            similarity = _token_jaccard(tokens, cluster.get("tokens", set()))
            if similarity > best_similarity:
                best_similarity = similarity
                best_index = index
        if best_index >= 0 and best_similarity >= CONSENSUS_CLUSTER_SIMILARITY:
            cluster = clusters[best_index]
            rows = cluster.get("rows", [])
            if isinstance(rows, list):
                rows.append(signal)
            groups = cluster.get("groups", set())
            if isinstance(groups, set):
                groups.add(str(signal.get("group_id") or ""))
            citations = cluster.get("citations", set())
            if isinstance(citations, set):
                for item in signal.get("citations", []):
                    text = str(item or "").strip()
                    if text:
                        citations.add(text)
            # Keep the representative concise while preserving a high-support statement.
            rep = str(cluster.get("representative_text") or "")
            if rep and len(text) < len(rep):
                cluster["representative_text"] = text
        else:
            clusters.append(
                {
                    "representative_text": text,
                    "tokens": set(tokens),
                    "groups": {str(signal.get("group_id") or "")},
                    "citations": {
                        str(item).strip()
                        for item in signal.get("citations", [])
                        if str(item).strip()
                    },
                    "rows": [signal],
                }
            )
    out: List[dict] = []
    for cluster in clusters:
        groups = sorted({item for item in cluster.get("groups", set()) if item})
        citations = sorted({item for item in cluster.get("citations", set()) if item})
        rows = cluster.get("rows", [])
        coverage_values = [
            float(item.get("coverage") or 0.0)
            for item in rows
            if isinstance(item, dict)
        ]
        out.append(
            {
                "text": _truncate(str(cluster.get("representative_text") or ""), max_chars=260),
                "support_groups": groups,
                "support_count": len(groups),
                "citation_refs": citations,
                "citation_count": len(citations),
                "avg_coverage": (
                    round(sum(coverage_values) / len(coverage_values), 3)
                    if coverage_values
                    else 0.0
                ),
            }
        )
    out.sort(
        key=lambda item: (
            -int(item.get("support_count", 0)),
            -float(item.get("avg_coverage", 0.0)),
            str(item.get("text") or ""),
        )
    )
    return out


def _required_consensus_support(total_groups: int) -> int:
    if total_groups <= 0:
        return 0
    if total_groups <= 4:
        return total_groups
    return max(3, int(total_groups * 0.75 + 0.999))


def _build_consensus_report(
    *,
    message: str,
    contributions: List[dict],
    meeting_conclusion: dict,
    cycle_summaries: List[dict],
) -> dict:
    answered_rows = [
        row
        for row in contributions
        if isinstance(row, dict)
        and _effective_contribution_valid(row)
        and str(row.get("response_status") or "") == "ANSWERED"
        and float(row.get("objective_coverage") or 0.0) >= OBJECTIVE_COVERAGE_THRESHOLD
    ]
    blocking_groups = [
        str(row.get("group_id") or "")
        for row in contributions
        if isinstance(row, dict)
        and (
            not _effective_contribution_valid(row)
            or str(row.get("response_status") or "") != "ANSWERED"
            or float(row.get("objective_coverage") or 0.0) < OBJECTIVE_COVERAGE_THRESHOLD
        )
    ]
    blocking_groups = [group for group in blocking_groups if group]

    signals = _extract_consensus_signals(answered_rows)
    clusters = _cluster_consensus_signals(signals)
    required_support = _required_consensus_support(len(answered_rows))
    consensus_points = [
        row for row in clusters if int(row.get("support_count", 0)) >= required_support
    ]
    top_support_count = int(consensus_points[0].get("support_count", 0)) if consensus_points else 0
    top_support_groups = list(consensus_points[0].get("support_groups", [])) if consensus_points else []

    anchor_rows = answered_rows if answered_rows else [row for row in contributions if isinstance(row, dict)]
    anchor = None
    if anchor_rows:
        anchor = sorted(
            anchor_rows,
            key=lambda row: (
                -float(row.get("objective_coverage") or 0.0),
                -int(row.get("citation_count") or 0),
                -int(row.get("claim_count") or 0),
                str(row.get("group_id") or ""),
            ),
        )[0]
    anchor_response = _truncate(
        _clean_signal_text((anchor or {}).get("objective_response") or ""),
        max_chars=420,
    )
    if consensus_points:
        consensus_conclusion = _clean_signal_text(consensus_points[0].get("text"))
    elif anchor_response:
        consensus_conclusion = anchor_response
    else:
        consensus_conclusion = "No answer-ready consensus conclusion was published in this cycle."

    meeting_all_satisfied = bool(meeting_conclusion.get("all_satisfied"))
    meeting_consensus_ready = bool(meeting_conclusion.get("consensus_ready"))
    meeting_cycle_depth_ready = bool(meeting_conclusion.get("minimum_cycle_depth_ready"))
    if not meeting_consensus_ready:
        total_groups = int(meeting_conclusion.get("total_groups", 0))
        ready_groups = int(meeting_conclusion.get("consensus_ready_count", 0))
        meeting_consensus_ready = total_groups > 0 and ready_groups >= total_groups
    if not meeting_cycle_depth_ready:
        total_groups = int(meeting_conclusion.get("total_groups", 0))
        ready_groups = int(meeting_conclusion.get("minimum_cycle_depth_ready_count", 0))
        meeting_cycle_depth_ready = total_groups > 0 and ready_groups >= total_groups
    consensus_gate_met = bool(
        meeting_all_satisfied
        and meeting_consensus_ready
        and meeting_cycle_depth_ready
        and len(answered_rows) > 0
        and not blocking_groups
    )
    if consensus_gate_met and top_support_count <= 0:
        top_support_count = len(answered_rows)
        top_support_groups = [
            str(row.get("group_id") or "")
            for row in answered_rows
            if str(row.get("group_id") or "")
        ]
    if blocking_groups:
        decision_status = "BLOCKED"
    elif consensus_gate_met:
        decision_status = "ANSWERED"
    else:
        decision_status = "PARTIAL"

    if decision_status == "ANSWERED":
        decision = "all active groups converged on a shared conclusion and passed strict meeting gates."
    elif decision_status == "PARTIAL":
        decision = "groups produced useful progress but did not reach strict consensus closure yet."
    else:
        decision = "at least one active group remains blocked or below objective gate threshold."

    coverage_values = [float(row.get("objective_coverage") or 0.0) for row in answered_rows]
    avg_coverage = round(sum(coverage_values) / len(coverage_values), 3) if coverage_values else 0.0
    support_ratio = (top_support_count / len(answered_rows)) if answered_rows else 0.0
    strict_ready_ratio = 0.0
    total_groups = int(meeting_conclusion.get("total_groups", 0))
    if total_groups > 0:
        strict_ready_ratio = float(meeting_conclusion.get("strict_ready_count", 0)) / total_groups
    confidence = round(
        max(
            0.0,
            min(1.0, (0.45 * support_ratio) + (0.35 * avg_coverage) + (0.20 * strict_ready_ratio)),
        ),
        3,
    )

    completed: List[str] = []
    for item in consensus_points[:5]:
        text = _clean_signal_text(item.get("text"))
        if not text:
            continue
        completed.append(text)
    if not completed and consensus_gate_met and answered_rows:
        completed.append(_truncate(consensus_conclusion, max_chars=300))
        completed.append(
            "Integrated decision gates passed: strict evidence, strict consensus alignment, and no blocking groups."
        )
    if not completed and anchor_response:
        completed.append(anchor_response)

    unique_evidence_refs: List[str] = []
    for row in answered_rows:
        refs = row.get("citation_refs", [])
        if not isinstance(refs, list):
            continue
        for item in refs:
            text = str(item or "").strip()
            if text and text not in unique_evidence_refs:
                unique_evidence_refs.append(text)
    if not unique_evidence_refs:
        for item in consensus_points:
            refs = item.get("citation_refs", [])
            if not isinstance(refs, list):
                continue
            for ref in refs:
                text = str(ref or "").strip()
                if text and text not in unique_evidence_refs:
                    unique_evidence_refs.append(text)

    explicit_basis: List[dict] = []
    for point in consensus_points[:6]:
        citations = [
            str(item).strip()
            for item in point.get("citation_refs", [])
            if str(item).strip()
        ]
        explicit_basis.append(
            {
                "statement": str(point.get("text") or "").strip(),
                "support_count": int(point.get("support_count", 0)),
                "support_total": len(answered_rows),
                "support_percent": (
                    round(
                        (int(point.get("support_count", 0)) / len(answered_rows)) * 100.0,
                        1,
                    )
                    if answered_rows
                    else 0.0
                ),
                "avg_coverage": round(float(point.get("avg_coverage", 0.0)), 3),
                "citation_count": len(citations),
                "citations": citations[:4],
            }
        )
    if not explicit_basis and anchor_response:
        explicit_basis.append(
            {
                "statement": anchor_response,
                "support_count": len(answered_rows),
                "support_total": len(answered_rows),
                "support_percent": 100.0 if answered_rows else 0.0,
                "avg_coverage": avg_coverage,
                "citation_count": len(unique_evidence_refs),
                "citations": unique_evidence_refs[:4],
            }
        )

    strict_ready_count = int(meeting_conclusion.get("strict_ready_count", 0))
    consensus_ready_count = int(meeting_conclusion.get("consensus_ready_count", 0))
    total_groups = int(meeting_conclusion.get("total_groups", 0))
    gate_rows = [
        {
            "gate": "all_groups_answered",
            "passed": len(answered_rows) == len(contributions) and len(contributions) > 0,
            "basis": f"answered_groups={len(answered_rows)} total_groups={len(contributions)}",
        },
        {
            "gate": "meeting_unanimous_satisfied",
            "passed": bool(meeting_all_satisfied),
            "basis": "meeting_verdict={0}".format(str(meeting_conclusion.get("verdict") or "UNKNOWN")),
        },
        {
            "gate": "strict_evidence_ready",
            "passed": total_groups > 0 and strict_ready_count >= total_groups,
            "basis": f"strict_evidence_ready={strict_ready_count}/{total_groups}",
        },
        {
            "gate": "strict_consensus_alignment",
            "passed": total_groups > 0 and consensus_ready_count >= total_groups,
            "basis": f"strict_consensus_ready={consensus_ready_count}/{total_groups}",
        },
        {
            "gate": "minimum_cycle_depth",
            "passed": bool(meeting_cycle_depth_ready),
            "basis": (
                "minimum_cycle_depth_ready={0}/{1}".format(
                    int(meeting_conclusion.get("minimum_cycle_depth_ready_count", 0)),
                    int(meeting_conclusion.get("total_groups", 0)),
                )
            ),
        },
        {
            "gate": "no_blocking_groups",
            "passed": len(blocking_groups) == 0,
            "basis": f"blocking_groups={len(blocking_groups)}",
        },
    ]

    unresolved: List[str] = []
    if not meeting_all_satisfied:
        unsatisfied = meeting_conclusion.get("unsatisfied_groups", [])
        if isinstance(unsatisfied, list) and unsatisfied:
            unresolved.append(
                "meeting not fully satisfied; rework required for: "
                + ", ".join(str(item) for item in unsatisfied if str(item).strip())
            )
    if decision_status != "ANSWERED":
        if len(answered_rows) >= 2 and not consensus_points:
            unresolved.append(
                "shared conclusion support is below strict threshold; group outputs remain partially divergent."
            )
        if blocking_groups:
            unresolved.append("blocking groups: " + ", ".join(blocking_groups))
    if not unresolved:
        unresolved.append("none")

    detailed_conclusion_parts = [
        f"Current consensus conclusion: {consensus_conclusion}",
        "Decision basis: {0} explicit basis signal(s), {1} unique evidence reference(s), and gate status {2}/{3} passed.".format(
            len(explicit_basis),
            len(unique_evidence_refs),
            len([row for row in gate_rows if bool(row.get("passed"))]),
            len(gate_rows),
        ),
    ]
    if unresolved and unresolved != ["none"]:
        detailed_conclusion_parts.append(
            "Remaining limits: " + "; ".join(str(item) for item in unresolved[:2])
        )
    detailed_conclusion = " ".join(detailed_conclusion_parts).strip()

    next_actions = _collect_next_actions(contributions, limit=5)
    if not next_actions:
        next_actions = ["Continue with published artifacts and validation steps."]

    last_cycle_id = 0
    if cycle_summaries:
        try:
            last_cycle_id = int(cycle_summaries[-1].get("cycle_id") or 0)
        except Exception:
            last_cycle_id = 0

    return {
        "schema_version": "3.1",
        "generated_at": now_iso(),
        "objective": message,
        "decision_status": decision_status,
        "decision": decision,
        "consensus_conclusion": consensus_conclusion,
        "detailed_conclusion": detailed_conclusion,
        "consensus_gate_met": consensus_gate_met,
        "confidence": confidence,
        "groups_total": len([row for row in contributions if isinstance(row, dict)]),
        "groups_answered": len(answered_rows),
        "groups_blocking": blocking_groups,
        "support_required": required_support,
        "support_observed": top_support_count,
        "supporting_groups": top_support_groups,
        "consensus_points": consensus_points[:8],
        "explicit_basis": explicit_basis,
        "decision_gates": gate_rows,
        "unique_evidence_refs": unique_evidence_refs[:12],
        "completed_actions": completed,
        "unresolved_points": unresolved,
        "next_actions": next_actions,
        "meeting_cycle_id": int(meeting_conclusion.get("cycle_id", 0) or 0),
        "runtime_cycle_id": last_cycle_id,
        "meeting_verdict": str(meeting_conclusion.get("verdict") or "UNKNOWN"),
    }


def _render_consensus_report_markdown(report: dict) -> str:
    lines = [
        "# Consensus Report",
        "",
        f"- objective: {report.get('objective', '')}",
        f"- decision_status: `{report.get('decision_status', 'UNKNOWN')}`",
        f"- decision: {report.get('decision', '')}",
        f"- confidence: `{report.get('confidence', 0.0)}`",
        f"- support: `{report.get('support_observed', 0)}/{report.get('groups_answered', 0)}` "
        f"(required `{report.get('support_required', 0)}`)",
        "",
        "## Consensus Conclusion",
        str(report.get("consensus_conclusion") or ""),
        "",
        "## Detailed Conclusion",
        str(report.get("detailed_conclusion") or ""),
        "",
        "## Explicit Basis",
    ]
    basis_rows = report.get("explicit_basis", [])
    if isinstance(basis_rows, list) and basis_rows:
        for index, row in enumerate(basis_rows, start=1):
            if not isinstance(row, dict):
                continue
            statement = str(row.get("statement") or "").strip()
            support_count = int(row.get("support_count", 0))
            support_total = int(row.get("support_total", 0))
            support_percent = float(row.get("support_percent", 0.0))
            citation_count = int(row.get("citation_count", 0))
            citations = row.get("citations", [])
            citations_preview = "; ".join(
                str(item).strip() for item in citations[:3] if str(item).strip()
            )
            lines.append(
                "{0}. {1} | support={2}/{3} ({4}%) | citations={5}".format(
                    index,
                    statement or "basis statement not available",
                    support_count,
                    support_total,
                    support_percent,
                    citation_count,
                )
            )
            lines.append(
                "   evidence_refs: {0}".format(citations_preview if citations_preview else "none")
            )
    else:
        lines.append("1. No explicit basis signal was extracted.")
    lines.extend(
        [
            "",
            "## Decision Gates",
        ]
    )
    gate_rows = report.get("decision_gates", [])
    if isinstance(gate_rows, list) and gate_rows:
        for row in gate_rows:
            if not isinstance(row, dict):
                continue
            lines.append(
                "- {0}: `{1}` ({2})".format(
                    str(row.get("gate") or "unknown-gate"),
                    "PASS" if bool(row.get("passed")) else "FAIL",
                    str(row.get("basis") or "no basis"),
                )
            )
    else:
        lines.append("- decision gates unavailable")
    lines.extend(
        [
            "",
            "## Evidence References",
        ]
    )
    evidence_refs = report.get("unique_evidence_refs", [])
    if isinstance(evidence_refs, list) and evidence_refs:
        for index, item in enumerate(evidence_refs[:10], start=1):
            lines.append(f"{index}. {str(item)}")
    else:
        lines.append("1. No explicit evidence reference was captured in this cycle.")
    lines.extend(
        [
            "",
            "## Completed At Current Stage",
        ]
    )
    completed = report.get("completed_actions", [])
    if isinstance(completed, list) and completed:
        for index, item in enumerate(completed, start=1):
            lines.append(f"{index}. {str(item)}")
    else:
        lines.append("1. No completed objective action was published.")
    lines.extend(["", "## Open Points"])
    unresolved = report.get("unresolved_points", [])
    if isinstance(unresolved, list) and unresolved:
        for item in unresolved:
            lines.append(f"- {str(item)}")
    else:
        lines.append("- none")
    lines.extend(["", "## Next Actions"])
    actions = report.get("next_actions", [])
    if isinstance(actions, list) and actions:
        for index, action in enumerate(actions, start=1):
            lines.append(f"{index}. {str(action)}")
    else:
        lines.append("1. Continue with published artifacts and validation steps.")
    lines.extend(
        [
            "",
            "## Trace",
            f"- meeting_cycle_id: `{report.get('meeting_cycle_id', 0)}`",
            f"- runtime_cycle_id: `{report.get('runtime_cycle_id', 0)}`",
            f"- meeting_verdict: `{report.get('meeting_verdict', 'UNKNOWN')}`",
        ]
    )
    return "\n".join(lines).strip() + "\n"


def _collect_meeting_conclusion(contributions: List[dict], meeting_outputs: List[dict]) -> dict:
    latest_matrix: dict = {}
    latest_decisions: dict = {}
    latest_cycle = 0
    if meeting_outputs:
        latest = meeting_outputs[-1]
        if isinstance(latest, dict):
            matrix = latest.get("matrix", {})
            if isinstance(matrix, dict):
                latest_matrix = matrix
                try:
                    latest_cycle = int(matrix.get("cycle_id") or 0)
                except Exception:
                    latest_cycle = 0
            decisions = latest.get("decisions", {})
            if isinstance(decisions, dict):
                latest_decisions = decisions

    total_groups = len([row for row in contributions if isinstance(row, dict)])
    satisfied_groups: List[str] = []
    unsatisfied_groups: List[str] = []
    request_count = 0
    criticism_count = 0
    strict_ready_count = 0
    consensus_ready_count = 0
    minimum_cycle_depth_ready_count = 0
    consensus_min_similarity = 1.0
    consensus_avg_similarity = 1.0
    consensus_stats_present = False
    if latest_decisions:
        for group_id, row in latest_decisions.items():
            if not isinstance(row, dict):
                continue
            if bool(row.get("satisfied")):
                satisfied_groups.append(str(group_id))
            else:
                unsatisfied_groups.append(str(group_id))
            if bool(row.get("strict_evidence_complete")):
                strict_ready_count += 1
            if bool(row.get("consensus_alignment_ok")):
                consensus_ready_count += 1
            if bool(row.get("minimum_cycle_depth_met")):
                minimum_cycle_depth_ready_count += 1
            if "consensus_pair_min_similarity" in row:
                consensus_stats_present = True
                try:
                    consensus_min_similarity = min(
                        consensus_min_similarity,
                        float(row.get("consensus_pair_min_similarity") or 0.0),
                    )
                except Exception:
                    consensus_min_similarity = min(consensus_min_similarity, 0.0)
            if "consensus_pair_avg_similarity" in row:
                consensus_stats_present = True
                try:
                    consensus_avg_similarity = min(
                        consensus_avg_similarity,
                        float(row.get("consensus_pair_avg_similarity") or 0.0),
                    )
                except Exception:
                    consensus_avg_similarity = min(consensus_avg_similarity, 0.0)
            requests = row.get("request_changes", [])
            if isinstance(requests, list):
                request_count += len([item for item in requests if str(item).strip()])
            criticisms = row.get("criticisms", [])
            if isinstance(criticisms, list):
                criticism_count += len([item for item in criticisms if str(item).strip()])
    else:
        for row in contributions:
            if not isinstance(row, dict):
                continue
            group_id = str(row.get("group_id") or "").strip()
            if not group_id:
                continue
            if _effective_contribution_valid(row) and str(row.get("response_status") or "") == "ANSWERED":
                satisfied_groups.append(group_id)
            else:
                unsatisfied_groups.append(group_id)
            if (
                int(row.get("citation_count", 0)) >= 1
                and int(row.get("claim_count", 0)) >= 1
                and float(row.get("objective_coverage", 0.0)) >= 0.8
            ):
                strict_ready_count += 1
                consensus_ready_count += 1

    if isinstance(latest_matrix.get("unsatisfied_groups"), list):
        unsatisfied_groups = [str(item) for item in latest_matrix.get("unsatisfied_groups", []) if str(item).strip()]
    if isinstance(latest_matrix.get("satisfied_groups"), list):
        satisfied_groups = [str(item) for item in latest_matrix.get("satisfied_groups", []) if str(item).strip()]
    if isinstance(latest_matrix.get("consensus_alignment_groups"), list):
        consensus_ready_count = len(
            [
                str(item)
                for item in latest_matrix.get("consensus_alignment_groups", [])
                if str(item).strip()
            ]
        )
    if isinstance(latest_matrix.get("minimum_cycle_depth_groups"), list):
        minimum_cycle_depth_ready_count = len(
            [
                str(item)
                for item in latest_matrix.get("minimum_cycle_depth_groups", [])
                if str(item).strip()
            ]
        )

    all_satisfied = bool(latest_matrix.get("all_satisfied")) if latest_matrix else not unsatisfied_groups
    verdict = "SATISFIED" if all_satisfied else "REWORK_REQUIRED"
    return {
        "cycle_id": latest_cycle,
        "verdict": verdict,
        "total_groups": total_groups,
        "satisfied_groups": sorted(set(satisfied_groups)),
        "unsatisfied_groups": sorted(set(unsatisfied_groups)),
        "request_count": int(request_count),
        "criticism_count": int(criticism_count),
        "strict_ready_count": int(strict_ready_count),
        "consensus_ready_count": int(consensus_ready_count),
        "minimum_cycle_depth_ready_count": int(minimum_cycle_depth_ready_count),
        "consensus_min_pair_similarity": (
            round(consensus_min_similarity, 3) if consensus_stats_present else 0.0
        ),
        "consensus_avg_pair_similarity": (
            round(consensus_avg_similarity, 3) if consensus_stats_present else 0.0
        ),
        "all_satisfied": bool(all_satisfied),
        "consensus_ready": bool(latest_matrix.get("consensus_ready")) if latest_matrix else bool(all_satisfied),
        "minimum_cycle_depth_ready": (
            bool(latest_matrix.get("minimum_cycle_depth_ready"))
            if latest_matrix
            else bool(all_satisfied)
        ),
    }


def _collect_user_focused_done_rows(contributions: List[dict], *, limit: int = 10) -> List[dict]:
    direct_answers = _collect_direct_answers(contributions, limit=max(limit * 2, 10))
    direct_answers.sort(
        key=lambda item: (
            0 if str(item.get("response_status") or "") == "ANSWERED" else 1,
            -float(item.get("objective_coverage") or 0.0),
            str(item.get("group_id") or ""),
        )
    )
    seen: set[str] = set()
    rows: List[dict] = []
    for item in direct_answers:
        response = str(item.get("response") or "").strip()
        if not response:
            continue
        fingerprint = re.sub(r"[^a-z0-9]+", " ", response.lower()).strip()[:120]
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        rows.append(
            {
                "group_id": str(item.get("group_id") or ""),
                "status": str(item.get("response_status") or "UNKNOWN"),
                "coverage": float(item.get("objective_coverage") or 0.0),
                "response": _truncate(response, max_chars=260),
            }
        )
        if len(rows) >= limit:
            break
    return rows


def _render_group_mode_chat_answer(
    *,
    project_id: str,
    message: str,
    contributions: List[dict],
    cycle_summaries: List[dict],
    meeting_outputs: List[dict],
    consensus_report: dict,
    consensus_report_path: Path,
    turn_dir: Path,
    full_report_path: Path,
) -> str:
    overall_status = str(consensus_report.get("decision_status") or _overall_objective_status(contributions))
    blocking = [
        str(row.get("group_id") or "")
        for row in contributions
        if not _effective_contribution_valid(row)
        or str(row.get("response_status") or "") != "ANSWERED"
        or (
            float(row.get("objective_coverage") or 0.0) < OBJECTIVE_COVERAGE_THRESHOLD
            and not bool(row.get("persona_override_allowed"))
        )
    ]
    blocking = [group for group in blocking if group]
    headline = str(consensus_report.get("decision") or "").strip()
    if not headline:
        if overall_status == "ANSWERED":
            headline = "objective answered across all active groups."
        elif overall_status == "PARTIAL":
            headline = "objective only partially addressed; additional cycle or tighter constraints needed."
        else:
            headline = "objective blocked; at least one group did not produce an answer-ready handoff."

    lines = [
        f"# Orchestrator Reply - {project_id}",
        "",
        "## Consensus Decision",
        f"- objective: {message}",
        f"- status: `{overall_status}`",
        f"- decision: {headline}",
        "- confidence: `{0}`".format(consensus_report.get("confidence", 0.0)),
        "- consensus_support: `{0}/{1}` (required `{2}`)".format(
            int(consensus_report.get("support_observed", 0)),
            int(consensus_report.get("groups_answered", 0)),
            int(consensus_report.get("support_required", 0)),
        ),
        f"- blocking_groups: {', '.join(blocking) if blocking else 'none'}",
        "- conclusion: {0}".format(str(consensus_report.get("consensus_conclusion") or "")),
    ]
    detailed_conclusion = str(consensus_report.get("detailed_conclusion") or "").strip()
    if detailed_conclusion:
        lines.extend(["", "## Detailed Conclusion", detailed_conclusion])

    basis_rows = consensus_report.get("explicit_basis", [])
    lines.extend(["", "## Explicit Basis"])
    if isinstance(basis_rows, list) and basis_rows:
        for index, row in enumerate(basis_rows[:5], start=1):
            if not isinstance(row, dict):
                continue
            statement = str(row.get("statement") or "").strip()
            support_count = int(row.get("support_count", 0))
            support_total = int(row.get("support_total", 0))
            support_percent = float(row.get("support_percent", 0.0))
            citation_count = int(row.get("citation_count", 0))
            lines.append(
                "{0}. {1} | support={2}/{3} ({4}%) | citations={5}".format(
                    index,
                    statement or "basis statement not available",
                    support_count,
                    support_total,
                    support_percent,
                    citation_count,
                )
            )
    else:
        lines.append("1. No explicit basis signal was extracted.")
    meeting_conclusion = _collect_meeting_conclusion(
        contributions=contributions,
        meeting_outputs=meeting_outputs,
    )
    lines.extend(
        [
            "",
            "## Meeting Gate",
            "- cycle: `{0}`".format(meeting_conclusion.get("cycle_id", 0)),
            "- verdict: `{0}`".format(meeting_conclusion.get("verdict", "UNKNOWN")),
            "- strict_satisfied_groups: `{0}/{1}`".format(
                len(meeting_conclusion.get("satisfied_groups", [])),
                int(meeting_conclusion.get("total_groups", 0)),
            ),
            "- strict_evidence_ready_groups: `{0}/{1}`".format(
                int(meeting_conclusion.get("strict_ready_count", 0)),
                int(meeting_conclusion.get("total_groups", 0)),
            ),
            "- strict_consensus_ready_groups: `{0}/{1}`".format(
                int(meeting_conclusion.get("consensus_ready_count", 0)),
                int(meeting_conclusion.get("total_groups", 0)),
            ),
            "- minimum_cycle_depth_ready_groups: `{0}/{1}`".format(
                int(meeting_conclusion.get("minimum_cycle_depth_ready_count", 0)),
                int(meeting_conclusion.get("total_groups", 0)),
            ),
            "- consensus_pair_similarity_floor: `{0}`".format(
                meeting_conclusion.get("consensus_min_pair_similarity", 0.0)
            ),
            "- open_change_requests: `{0}`".format(int(meeting_conclusion.get("request_count", 0))),
            "- open_criticisms: `{0}`".format(int(meeting_conclusion.get("criticism_count", 0))),
            "- groups_requiring_rework: {0}".format(
                ", ".join(str(item) for item in meeting_conclusion.get("unsatisfied_groups", []))
                if meeting_conclusion.get("unsatisfied_groups")
                else "none"
            ),
        ]
    )
    lines.extend(["", "## Decision Gates"])
    gate_rows = consensus_report.get("decision_gates", [])
    if isinstance(gate_rows, list) and gate_rows:
        for row in gate_rows:
            if not isinstance(row, dict):
                continue
            lines.append(
                "- {0}: `{1}` ({2})".format(
                    str(row.get("gate") or "unknown-gate"),
                    "PASS" if bool(row.get("passed")) else "FAIL",
                    str(row.get("basis") or "no basis"),
                )
            )
    else:
        lines.append("- decision gates unavailable")

    completed_rows = consensus_report.get("completed_actions", [])
    lines.extend(["", "## Current Stage"])
    if isinstance(completed_rows, list) and completed_rows:
        for index, item in enumerate(completed_rows, start=1):
            lines.append(f"{index}. {str(item)}")
    else:
        lines.append("1. No consensus-ready completion details were published.")

    if cycle_summaries:
        last_cycle = cycle_summaries[-1]
        lines.extend(
            [
                "",
                "## Runtime Trace",
                "- last_cycle: `{0}` runtime_blocked=`{1}` escalations=`{2}`".format(
                    last_cycle.get("cycle_id", "?"),
                    bool(last_cycle.get("runtime_blocked")),
                    int(last_cycle.get("escalation_count", 0)),
                ),
            ]
        )

    actions = consensus_report.get("next_actions", [])
    lines.extend(["", "## What To Do Next"])
    if isinstance(actions, list) and actions:
        for index, action in enumerate(actions, start=1):
            lines.append(f"{index}. {str(action)}")
    else:
        lines.append("1. Continue with published artifacts and validation steps.")

    unresolved = consensus_report.get("unresolved_points", [])
    lines.extend(["", "## Open Points"])
    if isinstance(unresolved, list) and unresolved:
        for item in unresolved:
            lines.append(f"- {str(item)}")
    else:
        lines.append("- none")

    lines.extend(
        [
            "",
            "## Artifacts",
            f"- consensus_report: `{consensus_report_path}`",
            f"- full_report: `{full_report_path}`",
            f"- turn_dir: `{turn_dir}`",
        ]
    )
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
        if isinstance(row, dict) and _effective_contribution_valid(row)
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
                "valid" if _effective_contribution_valid(row) else "blocked",
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
        if _effective_contribution_valid(row):
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
            (
                '- `agents-inc orchestrator-reply --project-id {0} --message "{1}" '
                "--meeting-enabled --require-negotiation true`"
            ).format(
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


def _emit_progress(config: OrchestratorReplyConfig, event: dict) -> None:
    callback = config.progress_callback
    if callback is None:
        return
    try:
        callback(event)
    except Exception:
        # Progress rendering is best effort and must not break orchestration.
        return


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
        specialist_model=normalize_model_slug(
            config.specialist_model,
            default=DEFAULT_SPECIALIST_MODEL,
        ),
        specialist_reasoning_effort=normalize_reasoning_effort(
            config.specialist_reasoning_effort,
            default=DEFAULT_SPECIALIST_REASONING_EFFORT,
        ),
        head_model=normalize_model_slug(
            config.head_model,
            default=DEFAULT_HEAD_MODEL,
        ),
        head_reasoning_effort=normalize_reasoning_effort(
            config.head_reasoning_effort,
            default=DEFAULT_HEAD_REASONING_EFFORT,
        ),
        web_search_policy=_normalize_web_search_policy(config.web_search_policy),
        progress_callback=config.progress_callback,
        project_index_path=(
            Path(str(config.project_index_path)).expanduser().resolve()
            if config.project_index_path is not None
            else None
        ),
        resume_from_cycle=max(0, int(config.resume_from_cycle or 0)),
        resume_group_objectives=(
            dict(config.resume_group_objectives) if isinstance(config.resume_group_objectives, dict) else None
        ),
        resume_previous_cycle_summaries=(
            list(config.resume_previous_cycle_summaries)
            if isinstance(config.resume_previous_cycle_summaries, list)
            else None
        ),
    )
    project_root, project_dir, manifest = _load_project_bundle(config)
    policy = ensure_response_policy(project_root)
    selected_groups = selected_groups_from_manifest(manifest)
    execution_mode = execution_mode_from_manifest(manifest, default="full")
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
        "execution_mode": execution_mode,
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
        execution_mode=execution_mode,
    )
    handoff_edges = manifest.get("handoff_edges") or []
    if not isinstance(handoff_edges, list):
        handoff_edges = []
    active_handoff_edges = _expected_negotiation_edges(selected_groups, handoff_edges)
    negotiation_text, negotiation_stats = _render_negotiation_sequence(
        selected_groups, primary_group, active_handoff_edges
    )
    write_text(turn_dir / "negotiation-sequence.md", negotiation_text)

    default_group_objectives = _build_group_objective_cards(
        base_objective=config.message,
        selected_groups=selected_groups,
        group_manifests=group_manifests,
        execution_mode=execution_mode,
    )
    group_objectives = _normalize_resume_group_objectives(
        selected_groups=selected_groups,
        default_objectives=default_group_objectives,
        resume_objectives=config.resume_group_objectives,
    )
    resume_cycle_summaries, resume_cycle_max = _normalize_resume_cycle_summaries(
        config.resume_previous_cycle_summaries
    )
    _emit_progress(
        config,
        {
            "event": "turn_started",
            "project_id": config.project_id,
            "selected_groups": selected_groups,
            "max_cycles": config.max_cycles,
            "heartbeat_sec": config.heartbeat_sec,
            "execution_mode": execution_mode,
        },
    )
    blocked_reasons: List[str] = []
    block_status = ""
    cycle = max(0, int(config.resume_from_cycle or 0), resume_cycle_max)
    last_completed_cycle = cycle
    cycle_summaries: List[dict] = list(resume_cycle_summaries)
    meeting_outputs: List[dict] = []
    cycle_records: List[NegotiationCycleRecord] = []
    runtime_result = {}
    timed_out_specialists: List[dict] = []
    unresolved_escalations: List[dict] = []
    latest_artifacts: Dict[str, str] = {}

    while True:
        next_cycle = cycle + 1
        if config.max_cycles > 0 and next_cycle > config.max_cycles:
            block_status = "BLOCKED_MAX_CYCLES"
            blocked_reasons.append(
                f"max cycle limit reached before unanimous satisfaction: {config.max_cycles}"
            )
            break
        cycle = next_cycle

        _emit_progress(
            config,
            {
                "event": "cycle_started",
                "project_id": config.project_id,
                "cycle": cycle,
                "selected_groups": selected_groups,
            },
        )
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
                specialist_model=config.specialist_model,
                specialist_reasoning_effort=config.specialist_reasoning_effort,
                head_model=config.head_model,
                head_reasoning_effort=config.head_reasoning_effort,
                web_search_policy=config.web_search_policy,
                progress_callback=config.progress_callback,
                cycle_id=cycle,
                execution_mode=execution_mode,
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
        last_completed_cycle = max(last_completed_cycle, cycle)
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
                    meeting_executed=False,
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
                    meeting_executed=False,
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
                    meeting_executed=False,
                )
            )
            break

        _emit_progress(
            config,
            {
                "event": "meeting_started",
                "project_id": config.project_id,
                "cycle": cycle,
                "selected_groups": selected_groups,
            },
        )
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
        _emit_progress(
            config,
            {
                "event": "meeting_result",
                "project_id": config.project_id,
                "cycle": cycle,
                "all_satisfied": bool(meeting.get("all_satisfied")),
                "unsatisfied_groups": unsatisfied_groups,
            },
        )
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
                meeting_executed=True,
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
    token_usage_report = write_turn_token_usage_report(turn_dir=turn_dir)
    token_usage_summary = token_usage_report.get("summary", {})
    if not isinstance(token_usage_summary, dict):
        token_usage_summary = {}
    token_usage_json_path = str(token_usage_report.get("json_path") or "")
    token_usage_md_path = str(token_usage_report.get("md_path") or "")

    evidence_rows: List[dict] = []
    contributions = _collect_group_contributions(
        project_dir,
        selected_groups,
        objective=config.message,
    )
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
            if _effective_contribution_valid(row):
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
        _emit_progress(
            config,
            {
                "event": "turn_blocked",
                "project_id": config.project_id,
                "status": block_status,
                "reason_count": len(blocked_reasons),
            },
        )
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
        quality["cycles_executed"] = last_completed_cycle
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
            "cycles_executed": last_completed_cycle,
            "agent_timeout_sec": config.agent_timeout_sec,
            "agent_timeout_mode": _timeout_mode(config.agent_timeout_sec),
            "timed_out_specialists": timed_out_specialists,
            "cycle_summaries": cycle_summaries,
            "negotiation_monitor": monitor,
            "meeting_monitor_paths": meeting_monitor_paths,
            "latest_artifacts": latest_artifacts,
            "escalations": unresolved_escalations,
            "escalations_path": str(turn_dir / "escalations.json"),
            "token_usage_summary": token_usage_summary,
            "token_usage_json_path": token_usage_json_path,
            "token_usage_md_path": token_usage_md_path,
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
        auto_checkpoint = _auto_checkpoint_blocked_turn(
            config=config,
            project_root=project_root,
            project_id=config.project_id,
            selected_groups=selected_groups,
            primary_group=primary_group,
            turn_dir=turn_dir,
            block_status=block_status,
            blocked_reasons=blocked_reasons,
            blocked_reasons_path=blocked_path,
            blocked_report_path=blocked_report_path,
            latest_artifacts=latest_artifacts,
            group_objectives=group_objectives,
            cycle_summaries=cycle_summaries,
            cycles_executed=last_completed_cycle,
        )
        if auto_checkpoint:
            blocked_payload["auto_checkpoint"] = auto_checkpoint
            write_text(blocked_path, stable_json(blocked_payload) + "\n")
        raise FabricError(
            "BLOCKED[{0}] blocked_report={1} blocked_reasons={2}".format(
                block_status,
                blocked_report_path,
                blocked_path,
            )
        )

    constraints = _load_constraints(project_root)
    full_report = _render_group_mode_answer(
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

    final_dir = turn_dir / "final"
    final_dir.mkdir(parents=True, exist_ok=True)
    final_path = turn_dir / "final-exposed-answer.md"
    full_report_path = final_dir / "full-report.md"
    full_report_json_path = final_dir / "full-report.json"
    consensus_report_json_path = final_dir / "consensus-report.json"
    consensus_report_md_path = final_dir / "consensus-report.md"
    key_points_path = final_dir / "key-points.txt"
    meeting_conclusion = _collect_meeting_conclusion(
        contributions=contributions,
        meeting_outputs=meeting_outputs,
    )
    consensus_report = _build_consensus_report(
        message=config.message,
        contributions=contributions,
        meeting_conclusion=meeting_conclusion,
        cycle_summaries=cycle_summaries,
    )
    write_text(consensus_report_json_path, stable_json(consensus_report) + "\n")
    write_text(consensus_report_md_path, _render_consensus_report_markdown(consensus_report))

    final_answer = _render_group_mode_chat_answer(
        project_id=config.project_id,
        message=config.message,
        contributions=contributions,
        cycle_summaries=cycle_summaries,
        meeting_outputs=meeting_outputs,
        consensus_report=consensus_report,
        consensus_report_path=consensus_report_md_path,
        turn_dir=turn_dir,
        full_report_path=full_report_path,
    )

    quality = _quality_gate(
        mode=mode,
        answer_text=full_report,
        detail_profile=str(policy.get("detail_profile") or "publication-grade"),
        evidence_rows=evidence_rows,
        artifact_citations=artifact_citations,
        negotiation_stats=negotiation_stats,
        delegation_ledger=delegation,
        contributions=contributions,
        turn_dir=turn_dir,
    )
    quality["cycles_executed"] = last_completed_cycle
    quality["meeting_cycles"] = len(meeting_outputs)
    quality["agent_timeout_sec"] = config.agent_timeout_sec
    quality["agent_timeout_mode"] = _timeout_mode(config.agent_timeout_sec)
    quality["timed_out_specialist_count"] = len(timed_out_specialists)

    if not quality.get("passed"):
        _emit_progress(
            config,
            {
                "event": "turn_blocked",
                "project_id": config.project_id,
                "status": "BLOCKED_QUALITY_GATE",
                "reason_count": 1,
            },
        )
        quality["block_status"] = "BLOCKED_QUALITY_GATE"
        quality["block_reasons"] = ["group-mode final answer failed quality checks"]
        write_text(turn_dir / "final-answer-quality.json", stable_json(quality) + "\n")
        blocked_path = turn_dir / "blocked-reasons.json"
        blocked_payload = {
            "schema_version": "3.1",
            "status": "BLOCKED_QUALITY_GATE",
            "project_id": config.project_id,
            "group": primary_group,
            "generated_at": now_iso(),
            "reasons": ["group-mode final answer failed quality checks"],
            "quality_checks": quality.get("checks", {}),
            "timed_out_specialists": timed_out_specialists,
            "latest_artifacts": latest_artifacts,
            "token_usage_summary": token_usage_summary,
            "token_usage_json_path": token_usage_json_path,
            "token_usage_md_path": token_usage_md_path,
            "cycles_executed": last_completed_cycle,
            "cycle_summaries": cycle_summaries,
        }
        write_text(blocked_path, stable_json(blocked_payload) + "\n")
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
        auto_checkpoint = _auto_checkpoint_blocked_turn(
            config=config,
            project_root=project_root,
            project_id=config.project_id,
            selected_groups=selected_groups,
            primary_group=primary_group,
            turn_dir=turn_dir,
            block_status="BLOCKED_QUALITY_GATE",
            blocked_reasons=["group-mode final answer failed quality checks"],
            blocked_reasons_path=blocked_path,
            blocked_report_path=blocked_report_path,
            latest_artifacts=latest_artifacts,
            group_objectives=group_objectives,
            cycle_summaries=cycle_summaries,
            cycles_executed=last_completed_cycle,
        )
        if auto_checkpoint:
            blocked_payload["auto_checkpoint"] = auto_checkpoint
            write_text(blocked_path, stable_json(blocked_payload) + "\n")
        raise FabricError(
            "BLOCKED[BLOCKED_QUALITY_GATE] blocked_report={0} blocked_reasons={1}".format(
                blocked_report_path,
                blocked_path,
            )
        )

    write_text(final_path, final_answer)
    write_text(full_report_path, full_report)
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
                "token_usage_summary": token_usage_summary,
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
                    "token_usage_json": token_usage_json_path,
                    "token_usage_markdown": token_usage_md_path,
                    "consensus_report_json": str(consensus_report_json_path),
                    "consensus_report_markdown": str(consensus_report_md_path),
                },
                "consensus_report": consensus_report,
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
    _emit_progress(
        config,
            {
                "event": "turn_completed",
                "project_id": config.project_id,
                "cycles_executed": last_completed_cycle,
            },
        )

    return {
        "mode": mode,
        "project_id": config.project_id,
        "group": primary_group,
        "selected_groups": selected_groups,
        "turn_dir": str(turn_dir),
        "final_answer_path": str(final_path),
        "full_report_path": str(full_report_path),
        "full_report_json_path": str(full_report_json_path),
        "consensus_report_path": str(consensus_report_md_path),
        "consensus_report_json_path": str(consensus_report_json_path),
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
        "token_usage_summary": token_usage_summary,
        "token_usage_json_path": token_usage_json_path,
        "token_usage_md_path": token_usage_md_path,
        "cycles": cycle_summaries,
    }
