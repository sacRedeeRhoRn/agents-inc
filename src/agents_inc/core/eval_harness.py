from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Tuple

from agents_inc.core.fabric_lib import gate_specialist_output, now_iso


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if isinstance(payload, dict):
        return payload
    return {}


def _latest_specialist_sessions(turn_dir: Path) -> Dict[str, dict]:
    latest = _load_json(turn_dir / "specialist-sessions.latest.json")
    if latest:
        return {str(k): v for k, v in latest.items() if isinstance(v, dict)}
    cycles_dir = turn_dir / "cycles"
    if not cycles_dir.exists():
        return {}
    cycle_dirs = sorted(
        [path for path in cycles_dir.iterdir() if path.is_dir() and path.name.startswith("cycle-")]
    )
    if not cycle_dirs:
        return {}
    fallback = _load_json(cycle_dirs[-1] / "layer4" / "specialist-sessions.json")
    return {str(k): v for k, v in fallback.items() if isinstance(v, dict)}


def _coerce_map(value: object) -> Dict[str, object]:
    if isinstance(value, dict):
        return {str(k): v for k, v in value.items()}
    return {}


def _specialist_paths(
    project_dir: Path,
    group_id: str,
    specialist_id: str,
    *,
    session_row: Dict[str, object],
    source: str,
) -> Tuple[Path, Path]:
    normalized_source = str(source or "").strip().lower()
    if normalized_source == "turn-snapshot":
        snapshot_work = str(session_row.get("snapshot_work_path") or "").strip()
        snapshot_handoff = str(session_row.get("snapshot_handoff_path") or "").strip()
        if snapshot_work and snapshot_handoff:
            work_path = Path(snapshot_work).expanduser()
            handoff_path = Path(snapshot_handoff).expanduser()
            if work_path.exists() and handoff_path.exists():
                return work_path, handoff_path
    root = project_dir / "agent-groups" / group_id / "internal" / specialist_id
    return root / "work.md", root / "handoff.json"


def score_session(
    *,
    turn_dir: Path,
    project_dir: Path,
    group_manifests: Dict[str, dict],
    source: str = "turn-snapshot",
) -> Dict[str, object]:
    sessions = _latest_specialist_sessions(turn_dir)
    by_group: Dict[str, dict] = {}
    specialist_scores: List[float] = []

    for group_id, manifest in group_manifests.items():
        group_scores: Dict[str, dict] = {}
        specialist_rows = manifest.get("specialists", [])
        if not isinstance(specialist_rows, list):
            specialist_rows = []
        group_sessions = sessions.get(group_id, {})
        if not isinstance(group_sessions, dict):
            group_sessions = {}

        for specialist in specialist_rows:
            if not isinstance(specialist, dict):
                continue
            specialist_id = str(specialist.get("agent_id") or "").strip()
            if not specialist_id:
                continue
            role = str(specialist.get("role") or "domain-core")
            expected_skill = str(
                specialist.get("effective_skill_name") or specialist.get("skill_name") or ""
            ).strip()
            session_row = _coerce_map(group_sessions.get(specialist_id))
            visible_skills = session_row.get("visible_skills")
            if not isinstance(visible_skills, list):
                visible_skills = []
            visible_skills = [str(item).strip() for item in visible_skills if str(item).strip()]

            work_path, handoff_path = _specialist_paths(
                project_dir,
                group_id,
                specialist_id,
                session_row=session_row,
                source=source,
            )
            work_exists = work_path.exists()
            handoff_exists = handoff_path.exists()
            handoff_payload = _load_json(handoff_path)
            gate = gate_specialist_output(
                handoff_payload,
                role=role,
                citation_required=True,
                web_available=True,
            )
            gate_status = str(gate.get("status") or "BLOCKED_INVALID")

            check_skill = bool(expected_skill and expected_skill in visible_skills) or bool(
                not expected_skill and visible_skills
            )
            check_artifacts = bool(work_exists and handoff_exists)
            check_gate = gate_status == "PASS"
            check_block_behavior = True
            status_text = str(handoff_payload.get("status") or "").strip().upper()
            if status_text.startswith("BLOCKED") and status_text != "BLOCKED_NEEDS_EVIDENCE":
                check_block_behavior = False

            checks = {
                "skill_loaded": check_skill,
                "required_artifacts": check_artifacts,
                "role_gate_passed": check_gate,
                "block_behavior": check_block_behavior,
            }
            score = round(sum(1.0 for value in checks.values() if value) / float(len(checks)), 3)
            specialist_scores.append(score)
            group_scores[specialist_id] = {
                "score": score,
                "checks": checks,
                "gate_status": gate_status,
                "expected_skill": expected_skill,
                "visible_skills": visible_skills,
                "work_path": str(work_path),
                "handoff_path": str(handoff_path),
            }

        group_score = 0.0
        if group_scores:
            group_score = round(
                sum(float(row["score"]) for row in group_scores.values()) / float(len(group_scores)),
                3,
            )
        by_group[group_id] = {
            "group_score": group_score,
                "specialists": group_scores,
            }

    overall = 0.0
    if specialist_scores:
        overall = round(sum(specialist_scores) / float(len(specialist_scores)), 3)

    report: Dict[str, object] = {
        "schema_version": "1.0",
        "generated_at": now_iso(),
        "turn_dir": str(turn_dir),
        "project_dir": str(project_dir),
        "source": str(source or "turn-snapshot"),
        "overall_score": overall,
        "groups": by_group,
    }
    (turn_dir / "eval-scores.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report
