from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Dict, List

from agents_inc.core.fabric_lib import now_iso, stable_json, write_text


@dataclass
class NegotiationCycleRecord:
    cycle_id: int
    objectives: Dict[str, str]
    refined_objectives: Dict[str, str]
    decisions: Dict[str, dict]
    unsatisfied_groups: List[str]
    meeting_executed: bool = False


def evaluate_negotiation(
    *,
    selected_groups: List[str],
    cycles: List[NegotiationCycleRecord],
    require_negotiation: bool,
    final_all_satisfied: bool,
) -> dict:
    meeting_cycles = sum(1 for record in cycles if bool(record.meeting_executed))
    per_head_actions: Dict[str, dict] = {}
    cross_group_critique_or_request_count = 0
    objective_delta_for_unsatisfied = False

    for group_id in selected_groups:
        per_head_actions[group_id] = {
            "peer_action_seen": False,
            "new_actions_seen": False,
            "request_count": 0,
            "criticism_count": 0,
            "accepted_count": 0,
        }

    for record in cycles:
        decisions = record.decisions
        if not isinstance(decisions, dict):
            continue

        for group_id in selected_groups:
            row = decisions.get(group_id, {})
            if not isinstance(row, dict):
                continue
            requests = _normalized_list(row.get("request_changes"))
            criticisms = _normalized_list(row.get("criticisms"))
            accepted = _normalized_list(row.get("accepted_items"))
            new_actions = _normalized_list(row.get("new_actions"))

            peer_action_seen = bool(requests or criticisms or accepted)
            if peer_action_seen:
                per_head_actions[group_id]["peer_action_seen"] = True
            if new_actions:
                per_head_actions[group_id]["new_actions_seen"] = True

            per_head_actions[group_id]["request_count"] += len(requests)
            per_head_actions[group_id]["criticism_count"] += len(criticisms)
            per_head_actions[group_id]["accepted_count"] += len(accepted)

            cross_group_critique_or_request_count += len(requests) + len(criticisms)

        # For unsatisfied heads, next-cycle plan must change (or same-cycle refined objective must change).
        for group_id in record.unsatisfied_groups:
            before = str(record.objectives.get(group_id) or "")
            after = str(record.refined_objectives.get(group_id) or "")
            if _hash_text(before) != _hash_text(after):
                objective_delta_for_unsatisfied = True

    checks = {
        "meeting_cycles_executed_gte_1": meeting_cycles >= 1,
        "each_head_has_peer_action": all(
            bool(per_head_actions[group_id]["peer_action_seen"]) for group_id in selected_groups
        ),
        "each_head_has_new_actions": all(
            bool(per_head_actions[group_id]["new_actions_seen"]) for group_id in selected_groups
        ),
        "cross_group_critique_or_request_exists": cross_group_critique_or_request_count > 0,
        "objective_delta_for_unsatisfied_heads": (
            objective_delta_for_unsatisfied
            if any(record.unsatisfied_groups for record in cycles)
            else True
        ),
        "final_unanimous_satisfied": bool(final_all_satisfied),
    }

    reasons: List[str] = []
    if require_negotiation:
        for key, passed in checks.items():
            if not passed:
                reasons.append(f"failed negotiation check: {key}")

    passed = (not require_negotiation) or (len(reasons) == 0)
    return {
        "schema_version": "3.1",
        "generated_at": now_iso(),
        "require_negotiation": bool(require_negotiation),
        "meeting_cycles_executed": meeting_cycles,
        "cross_group_critique_or_request_count": cross_group_critique_or_request_count,
        "objective_delta_for_unsatisfied": objective_delta_for_unsatisfied,
        "per_head_actions": per_head_actions,
        "checks": checks,
        "passed": passed,
        "reasons": reasons,
    }


def write_negotiation_monitor(*, monitor: dict, meeting_dir) -> dict:
    meeting_dir.mkdir(parents=True, exist_ok=True)
    json_path = meeting_dir / "negotiation-monitor.json"
    md_path = meeting_dir / "negotiation-monitor.md"
    write_text(json_path, stable_json(monitor) + "\n")
    write_text(md_path, _render_monitor_markdown(monitor))
    return {
        "json_path": str(json_path),
        "md_path": str(md_path),
    }


def _render_monitor_markdown(monitor: dict) -> str:
    checks = monitor.get("checks", {})
    if not isinstance(checks, dict):
        checks = {}
    lines = [
        "# Negotiation Monitor",
        "",
        f"- passed: `{bool(monitor.get('passed'))}`",
        f"- require_negotiation: `{bool(monitor.get('require_negotiation'))}`",
        f"- meeting_cycles_executed: `{int(monitor.get('meeting_cycles_executed') or 0)}`",
        f"- cross_group_critique_or_request_count: `{int(monitor.get('cross_group_critique_or_request_count') or 0)}`",
        "",
        "## Checks",
    ]
    for key, value in checks.items():
        lines.append(f"- {key}: `{bool(value)}`")

    reasons = monitor.get("reasons", [])
    if isinstance(reasons, list) and reasons:
        lines.extend(["", "## Reasons"])
        for reason in reasons:
            lines.append(f"- {reason}")

    actions = monitor.get("per_head_actions", {})
    if isinstance(actions, dict) and actions:
        lines.extend(["", "## Per Head Summary"])
        for group_id in sorted(actions.keys()):
            row = actions.get(group_id, {})
            if not isinstance(row, dict):
                continue
            lines.append(
                "- {0}: peer_action={1}, new_actions={2}, requests={3}, criticisms={4}, accepted={5}".format(
                    group_id,
                    bool(row.get("peer_action_seen")),
                    bool(row.get("new_actions_seen")),
                    int(row.get("request_count") or 0),
                    int(row.get("criticism_count") or 0),
                    int(row.get("accepted_count") or 0),
                )
            )
    return "\n".join(lines).rstrip() + "\n"


def _normalized_list(value: object) -> List[str]:
    if not isinstance(value, list):
        return []
    out: List[str] = []
    for item in value:
        text = str(item).strip()
        if text:
            out.append(text)
    return out


def _hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="replace")).hexdigest()
