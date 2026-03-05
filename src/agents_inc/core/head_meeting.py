from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

from agents_inc.core.fabric_lib import load_yaml, now_iso, stable_json, write_text


@dataclass
class HeadMeetingConfig:
    project_id: str
    cycle_id: int
    cycle_dir: Path
    project_dir: Path
    selected_groups: List[str]
    message: str


OBJECTIVE_COVERAGE_THRESHOLD = 0.8
OBJECTIVE_RESPONSE_STATUS_VALUES = {"ANSWERED", "PARTIAL", "BLOCKED"}


def run_head_meeting(config: HeadMeetingConfig) -> dict:
    meeting_dir = config.cycle_dir / "meeting"
    meeting_dir.mkdir(parents=True, exist_ok=True)

    exposed_rows = _collect_group_exposed(config.project_dir, config.selected_groups)
    decisions: Dict[str, dict] = {}
    for group_id in config.selected_groups:
        self_row = exposed_rows.get(group_id, {})
        requests: List[str] = []
        criticisms: List[str] = []
        accepted: List[str] = []
        new_actions: List[str] = []

        for other_group, row in exposed_rows.items():
            if other_group == group_id:
                continue
            if bool(row.get("valid")):
                accepted.append(f"{other_group}: accept current exposed handoff for this cycle")
                if config.cycle_id == 1:
                    criticisms.append(
                        f"{other_group}: add one quantitative delta in next cycle for stronger cross-group comparability"
                    )
            else:
                reason = "; ".join(str(item) for item in row.get("reasons", []))
                requests.append(f"{other_group}: fix exposed handoff ({reason})")
                criticisms.append(
                    f"{other_group}: published result is not consumable this cycle ({reason})"
                )

            if int(row.get("citation_count", 0)) <= 0:
                requests.append(f"{other_group}: add claim-level citations and evidence URLs")

        own_valid = bool(self_row.get("valid"))
        own_citations = int(self_row.get("citation_count", 0))
        own_response_status = str(self_row.get("response_status") or "PARTIAL")
        own_coverage = float(self_row.get("objective_coverage") or 0.0)
        if not own_valid:
            new_actions.append(
                "repair own exposed handoff structure and publish non-pending status"
            )
        if own_citations <= 0:
            new_actions.append("add own citations and evidence URLs before next cycle")
        if own_response_status != "ANSWERED":
            new_actions.append(
                "publish explicit objective_response with response_status=ANSWERED when objective is satisfied"
            )
        if own_coverage < OBJECTIVE_COVERAGE_THRESHOLD:
            new_actions.append(
                "increase objective_coverage by tightening decision summary and objective-specific outputs"
            )
        if not new_actions:
            new_actions.append("maintain current quality and improve cross-group alignment notes")

        satisfied = (
            own_valid
            and own_citations > 0
            and own_response_status == "ANSWERED"
            and own_coverage >= OBJECTIVE_COVERAGE_THRESHOLD
            and len(requests) == 0
        )
        decisions[group_id] = {
            "group_id": group_id,
            "response_status": own_response_status,
            "objective_coverage": round(own_coverage, 3),
            "request_changes": sorted(set(requests)),
            "criticisms": sorted(set(criticisms)),
            "accepted_items": sorted(set(accepted)),
            "new_actions": sorted(set(new_actions)),
            "satisfied": satisfied,
            "updated_at": now_iso(),
        }

    minutes_md = _render_minutes(config, decisions)
    minutes_path = meeting_dir / f"minutes-cycle-{config.cycle_id:04d}.md"
    write_text(minutes_path, minutes_md)

    decisions_path = meeting_dir / f"decisions-cycle-{config.cycle_id:04d}.json"
    write_text(
        decisions_path,
        stable_json(
            {
                "schema_version": "3.1",
                "project_id": config.project_id,
                "cycle_id": config.cycle_id,
                "generated_at": now_iso(),
                "decisions": decisions,
            }
        )
        + "\n",
    )

    matrix = {
        "schema_version": "3.1",
        "project_id": config.project_id,
        "cycle_id": config.cycle_id,
        "satisfied_groups": sorted(
            [group_id for group_id, row in decisions.items() if bool(row.get("satisfied"))]
        ),
        "unsatisfied_groups": sorted(
            [group_id for group_id, row in decisions.items() if not bool(row.get("satisfied"))]
        ),
        "all_satisfied": all(bool(row.get("satisfied")) for row in decisions.values()),
        "updated_at": now_iso(),
    }
    matrix_path = meeting_dir / f"satisfaction-matrix-cycle-{config.cycle_id:04d}.json"
    write_text(matrix_path, stable_json(matrix) + "\n")

    return {
        "minutes_path": str(minutes_path),
        "decisions_path": str(decisions_path),
        "satisfaction_path": str(matrix_path),
        "all_satisfied": bool(matrix.get("all_satisfied")),
        "decisions": decisions,
        "matrix": matrix,
    }


def _collect_group_exposed(project_dir: Path, groups: List[str]) -> Dict[str, dict]:
    out: Dict[str, dict] = {}
    for group_id in groups:
        handoff_path = project_dir / "agent-groups" / group_id / "exposed" / "handoff.json"
        summary_path = project_dir / "agent-groups" / group_id / "exposed" / "summary.md"
        payload = {}
        reasons: List[str] = []
        summary_text = ""
        if summary_path.exists():
            summary_text = summary_path.read_text(encoding="utf-8", errors="replace")
        if handoff_path.exists():
            loaded = load_yaml(handoff_path)
            if isinstance(loaded, dict):
                payload = loaded
            else:
                reasons.append("exposed handoff is not a mapping")
        else:
            reasons.append("missing exposed handoff")

        status = str(payload.get("status") or "").strip().upper()
        if status in {"", "PENDING"}:
            reasons.append("handoff status is pending")

        claims = payload.get("claims")
        if not isinstance(claims, list):
            claims = payload.get("claims_with_citations")
        if not isinstance(claims, list):
            claims = []
        citation_count = 0
        seen_ids: set[str] = set()
        for claim in claims:
            if not isinstance(claim, dict):
                continue
            evidence_ids = claim.get("evidence_ids")
            if isinstance(evidence_ids, list):
                for item in evidence_ids:
                    text = str(item or "").strip()
                    if text and text not in seen_ids:
                        seen_ids.add(text)
            if str(claim.get("citation") or "").strip():
                citation_count += 1
            citations = claim.get("citations")
            if isinstance(citations, list):
                citation_count += len([item for item in citations if str(item).strip()])
        if seen_ids:
            citation_count = len(seen_ids)

        response_status = _normalize_response_status(
            payload.get("response_status")
            or payload.get("objective_status")
            or payload.get("result_status")
        )
        if not response_status:
            response_status = _infer_response_status(status=status, summary_text=summary_text)

        objective_response = str(
            payload.get("objective_response")
            or payload.get("response_to_objective")
            or payload.get("decision_summary")
            or ""
        ).strip()
        decision_summary = str(payload.get("decision_summary") or "").strip()
        coverage = _parse_objective_coverage(payload.get("objective_coverage"))
        if coverage is None:
            if response_status == "ANSWERED":
                coverage = 0.9
            elif response_status == "BLOCKED":
                coverage = 0.4
            else:
                coverage = 0.6

        if not objective_response:
            reasons.append("objective response missing")
        if response_status != "ANSWERED":
            reasons.append(f"objective not fully satisfied ({response_status})")
        if coverage < OBJECTIVE_COVERAGE_THRESHOLD:
            reasons.append(
                "objective coverage below threshold ({0:.2f} < {1:.2f})".format(
                    coverage, OBJECTIVE_COVERAGE_THRESHOLD
                )
            )

        valid = len(reasons) == 0
        out[group_id] = {
            "group_id": group_id,
            "status": status or "UNKNOWN",
            "citation_count": citation_count,
            "response_status": response_status,
            "objective_response": objective_response,
            "decision_summary": decision_summary,
            "objective_coverage": round(coverage, 3),
            "valid": valid,
            "reasons": reasons,
            "handoff_path": str(handoff_path),
        }
    return out


def _render_minutes(config: HeadMeetingConfig, decisions: Dict[str, dict]) -> str:
    lines: List[str] = [
        f"# Head Meeting Minutes (Cycle {config.cycle_id:04d})",
        "",
        f"- project_id: `{config.project_id}`",
        f"- objective: {config.message}",
        f"- generated_at: `{now_iso()}`",
        "",
    ]

    for group_id in config.selected_groups:
        row = decisions.get(group_id, {})
        lines.append(f"## {group_id}")
        lines.append(f"- satisfied: `{bool(row.get('satisfied'))}`")
        lines.append(f"- response_status: `{row.get('response_status', 'UNKNOWN')}`")
        lines.append(f"- objective_coverage: `{row.get('objective_coverage', 0.0)}`")
        for key in ["request_changes", "criticisms", "accepted_items", "new_actions"]:
            values = row.get(key, [])
            if not isinstance(values, list) or not values:
                lines.append(f"- {key}: none")
                continue
            lines.append(f"- {key}:")
            for item in values:
                lines.append(f"  - {item}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


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


def _infer_response_status(*, status: str, summary_text: str) -> str:
    normalized = _normalize_response_status(status)
    if normalized:
        return normalized
    summary = str(summary_text or "").lower()
    if any(
        hint in summary
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
        hint in summary
        for hint in ("partial", "incomplete", "conditional", "unresolved", "next cycle")
    ):
        return "PARTIAL"
    return "PARTIAL"


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
    match = re.match(r"^\d+(\.\d+)?$", text)
    if not match:
        return None
    raw = float(text)
    if raw > 1.0:
        raw = raw / 100.0
    return max(0.0, min(1.0, raw))
