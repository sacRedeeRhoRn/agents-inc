from __future__ import annotations

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
        if not own_valid:
            new_actions.append(
                "repair own exposed handoff structure and publish non-pending status"
            )
        if own_citations <= 0:
            new_actions.append("add own citations and evidence URLs before next cycle")
        if not new_actions:
            new_actions.append("maintain current quality and improve cross-group alignment notes")

        satisfied = own_valid and own_citations > 0 and len(requests) == 0
        decisions[group_id] = {
            "group_id": group_id,
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
        payload = {}
        reasons: List[str] = []
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

        claims = payload.get("claims_with_citations")
        if not isinstance(claims, list):
            claims = []
        citation_count = 0
        for claim in claims:
            if not isinstance(claim, dict):
                continue
            if str(claim.get("citation") or "").strip():
                citation_count += 1
            citations = claim.get("citations")
            if isinstance(citations, list):
                citation_count += len([item for item in citations if str(item).strip()])

        valid = len(reasons) == 0
        out[group_id] = {
            "group_id": group_id,
            "status": status or "UNKNOWN",
            "citation_count": citation_count,
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
