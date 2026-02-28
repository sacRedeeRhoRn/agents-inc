from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

import yaml

from agents_inc.core.fabric_lib import FabricError, load_project_manifest, load_yaml, slugify
from agents_inc.core.session_state import now_iso, state_dir

RESPONSE_POLICY_SCHEMA_VERSION = "2.1"
SPECIALIST_SESSIONS_SCHEMA_VERSION = "2.1"

DEFAULT_RESPONSE_POLICY = {
    "schema_version": RESPONSE_POLICY_SCHEMA_VERSION,
    "default_mode": "group-detailed",
    "non_group_prefix": "[non-group]",
    "detail_profile": "publication-grade",
    "non_group_profile": "concise",
}


def response_policy_path(project_root: Path) -> Path:
    return state_dir(project_root) / "response-policy.yaml"


def specialist_sessions_path(project_root: Path) -> Path:
    return state_dir(project_root) / "specialist-sessions.yaml"


def _dump_yaml(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(payload, handle, sort_keys=False)


def load_response_policy(project_root: Path) -> dict:
    path = response_policy_path(project_root)
    if not path.exists():
        return dict(DEFAULT_RESPONSE_POLICY)
    payload = load_yaml(path)
    if not isinstance(payload, dict):
        raise FabricError(f"invalid response policy: {path}")
    merged = dict(DEFAULT_RESPONSE_POLICY)
    merged.update(payload)
    return _normalize_policy(merged)


def _normalize_policy(policy: dict) -> dict:
    out = dict(DEFAULT_RESPONSE_POLICY)
    out.update(policy)
    if out.get("default_mode") not in {"group-detailed", "non-group"}:
        out["default_mode"] = "group-detailed"
    prefix = str(out.get("non_group_prefix") or "[non-group]")
    if not prefix:
        prefix = "[non-group]"
    out["non_group_prefix"] = prefix
    out["detail_profile"] = str(out.get("detail_profile") or "publication-grade")
    out["non_group_profile"] = str(out.get("non_group_profile") or "concise")
    out["schema_version"] = RESPONSE_POLICY_SCHEMA_VERSION
    return out


def ensure_response_policy(project_root: Path) -> dict:
    policy = load_response_policy(project_root)
    _dump_yaml(response_policy_path(project_root), policy)
    return policy


def classify_request_mode(message: str, policy: Optional[dict] = None) -> str:
    effective = _normalize_policy(policy or DEFAULT_RESPONSE_POLICY)
    prefix = str(effective["non_group_prefix"])
    if str(message or "").startswith(prefix):
        return "non-group"
    return str(effective["default_mode"])


def strip_non_group_prefix(message: str, policy: Optional[dict] = None) -> str:
    text = str(message or "")
    effective = _normalize_policy(policy or DEFAULT_RESPONSE_POLICY)
    prefix = str(effective["non_group_prefix"])
    if text.startswith(prefix):
        return text[len(prefix) :].lstrip()
    return text


def _default_specialist_sessions(project_id: str) -> dict:
    return {
        "schema_version": SPECIALIST_SESSIONS_SCHEMA_VERSION,
        "project_id": project_id,
        "specialist_counters": {},
        "sessions": {},
        "updated_at": now_iso(),
    }


def load_specialist_sessions(project_root: Path, project_id: str = "") -> dict:
    path = specialist_sessions_path(project_root)
    if not path.exists():
        return _default_specialist_sessions(project_id)
    payload = load_yaml(path)
    if not isinstance(payload, dict):
        raise FabricError(f"invalid specialist session map: {path}")
    out = _default_specialist_sessions(project_id or str(payload.get("project_id") or ""))
    out.update(payload)
    if out.get("schema_version") not in {
        SPECIALIST_SESSIONS_SCHEMA_VERSION,
        RESPONSE_POLICY_SCHEMA_VERSION,
    }:
        raise FabricError(
            f"unsupported specialist session schema_version '{out.get('schema_version')}' in {path}"
        )
    out["schema_version"] = SPECIALIST_SESSIONS_SCHEMA_VERSION
    return out


def upsert_specialist_sessions(
    *,
    project_root: Path,
    project_fabric_root: Path,
    project_id: str,
    selected_groups: Optional[List[str]] = None,
) -> Dict[str, Dict[str, str]]:
    _, manifest = load_project_manifest(project_fabric_root, project_id)
    groups_map = manifest.get("groups", {})
    if not isinstance(groups_map, dict):
        raise FabricError("project manifest missing groups map")

    groups = selected_groups or manifest.get("selected_groups") or []
    if not isinstance(groups, list):
        groups = []
    groups = [str(group_id) for group_id in groups if str(group_id).strip()]

    state = load_specialist_sessions(project_root, project_id=project_id)
    sessions = state.get("sessions")
    if not isinstance(sessions, dict):
        sessions = {}
    counters = state.get("specialist_counters")
    if not isinstance(counters, dict):
        counters = {}

    now = now_iso()
    out: Dict[str, Dict[str, str]] = {}

    for group_id in groups:
        group_entry = groups_map.get(group_id)
        if not isinstance(group_entry, dict):
            continue
        group_manifest_rel = str(group_entry.get("manifest_path") or "").strip()
        if not group_manifest_rel:
            continue
        group_manifest_path = (
            project_fabric_root / "generated" / "projects" / project_id / group_manifest_rel
        )
        group_manifest = load_yaml(group_manifest_path)
        if not isinstance(group_manifest, dict):
            continue

        group_sessions = sessions.get(group_id)
        if not isinstance(group_sessions, dict):
            group_sessions = {}
        resolved_group_sessions: Dict[str, str] = {}

        for specialist in group_manifest.get("specialists", []):
            if not isinstance(specialist, dict):
                continue
            specialist_id = str(specialist.get("agent_id") or "").strip()
            if not specialist_id:
                continue
            role = str(specialist.get("role") or "").strip()
            flat_key = f"{group_id}::{specialist_id}"
            existing = group_sessions.get(specialist_id)
            if isinstance(existing, dict) and isinstance(existing.get("session_code"), str):
                existing["role"] = role
                existing["updated_at"] = now
                resolved_group_sessions[specialist_id] = str(existing["session_code"])
                continue

            counter = int(counters.get(flat_key, 0)) + 1
            counters[flat_key] = counter
            session_code = f"{project_id}::{group_id}::{specialist_id}::{counter:06d}"
            group_sessions[specialist_id] = {
                "session_code": session_code,
                "counter": counter,
                "role": role,
                "updated_at": now,
            }
            resolved_group_sessions[specialist_id] = session_code

        sessions[group_id] = group_sessions
        out[group_id] = resolved_group_sessions

    state["schema_version"] = SPECIALIST_SESSIONS_SCHEMA_VERSION
    state["project_id"] = project_id
    state["specialist_counters"] = counters
    state["sessions"] = sessions
    state["updated_at"] = now
    _dump_yaml(specialist_sessions_path(project_root), state)
    return out


def flatten_specialist_sessions(project_root: Path, project_id: str = "") -> List[dict]:
    payload = load_specialist_sessions(project_root, project_id=project_id)
    rows: List[dict] = []
    sessions = payload.get("sessions")
    if not isinstance(sessions, dict):
        return rows
    for group_id, group_sessions in sessions.items():
        if not isinstance(group_sessions, dict):
            continue
        for specialist_id, info in group_sessions.items():
            if not isinstance(info, dict):
                continue
            rows.append(
                {
                    "group_id": str(group_id),
                    "specialist_id": str(specialist_id),
                    "role": str(info.get("role") or ""),
                    "session_code": str(info.get("session_code") or ""),
                    "updated_at": str(info.get("updated_at") or ""),
                }
            )
    rows.sort(key=lambda row: (row["group_id"], row["specialist_id"]))
    return rows


def _match_group_id(query: str, group_candidates: List[str]) -> Optional[str]:
    normalized = slugify(query)
    for group_id in group_candidates:
        if group_id in normalized:
            return group_id
        spaced = group_id.replace("-", " ")
        if spaced in query.lower():
            return group_id
    return None


def lookup_specialist_session(
    *,
    project_root: Path,
    project_id: str,
    query: str,
    fallback_group: Optional[str] = None,
) -> Optional[dict]:
    rows = flatten_specialist_sessions(project_root, project_id=project_id)
    if not rows:
        return None
    groups = sorted({row["group_id"] for row in rows})
    group_id = _match_group_id(query, groups) or fallback_group
    lowered = query.lower()

    role_hint = ""
    specialist_hint = ""
    if "web-search specialist" in lowered or "web research specialist" in lowered:
        role_hint = "web-research"
    if "integration specialist" in lowered:
        role_hint = "integration"
    if "evidence-review specialist" in lowered:
        role_hint = "evidence-review"
    if "repro-qa specialist" in lowered or "repro qa specialist" in lowered:
        role_hint = "repro-qa"

    for row in rows:
        if group_id and row["group_id"] != group_id:
            continue
        if role_hint and row["role"] != role_hint:
            continue
        if specialist_hint and row["specialist_id"] != specialist_hint:
            continue
        return row
    return None
