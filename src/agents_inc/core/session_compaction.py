from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

from agents_inc.core.fabric_lib import FabricError, load_yaml
from agents_inc.core.session_state import state_dir
from agents_inc.core.util.fs import dump_yaml, load_yaml_map
from agents_inc.core.util.time import now_iso, to_stamp  # noqa: F401  (now_iso re-exported)

COMPACT_SCHEMA_VERSION = "3.0"


def compacted_dir(project_root: Path) -> Path:
    return state_dir(project_root) / "compacted"


def compacted_state_path(project_root: Path) -> Path:
    return state_dir(project_root) / "compacted-state.yaml"


def latest_compacted_path(project_root: Path) -> Path:
    return state_dir(project_root) / "latest-compacted.yaml"


def group_sessions_path(project_root: Path) -> Path:
    return state_dir(project_root) / "group-sessions.yaml"


def _require_schema(path: Path, payload: dict) -> None:
    found = str(payload.get("schema_version") or "")
    if found and found == COMPACT_SCHEMA_VERSION:
        return
    raise FabricError(
        f"compaction schema_version '{found or '<missing>'}' is not supported. "
        "Run 'agents-inc migrate-v2 --apply' before continuing."
    )


def load_group_sessions(project_root: Path) -> dict:
    path = group_sessions_path(project_root)
    data = load_yaml_map(
        group_sessions_path(project_root),
        {
            "schema_version": COMPACT_SCHEMA_VERSION,
            "project_id": "",
            "group_counters": {},
            "sessions": {},
            "updated_at": now_iso(),
        },
    )
    if path.exists():
        found = str(data.get("schema_version") or "")
        if found != COMPACT_SCHEMA_VERSION:
            data["schema_version"] = COMPACT_SCHEMA_VERSION
            dump_yaml(path, data)
    return data


def upsert_group_sessions(project_root: Path, project_id: str, groups: List[str]) -> Dict[str, str]:
    data = load_group_sessions(project_root)
    sessions = data.get("sessions")
    if not isinstance(sessions, dict):
        sessions = {}
    counters = data.get("group_counters")
    if not isinstance(counters, dict):
        counters = {}

    now = now_iso()
    out: Dict[str, str] = {}
    for group_id in groups:
        payload = sessions.get(group_id)
        if isinstance(payload, dict) and isinstance(payload.get("session_code"), str):
            payload["updated_at"] = now
            out[group_id] = str(payload["session_code"])
            continue

        counter = int(counters.get(group_id, 0)) + 1
        counters[group_id] = counter
        session_code = f"{project_id}::{group_id}::{counter:06d}"
        sessions[group_id] = {
            "session_code": session_code,
            "counter": counter,
            "updated_at": now,
        }
        out[group_id] = session_code

    data["schema_version"] = COMPACT_SCHEMA_VERSION
    data["project_id"] = project_id
    data["group_counters"] = counters
    data["sessions"] = sessions
    data["updated_at"] = now
    dump_yaml(group_sessions_path(project_root), data)
    return out


def compact_session(
    *,
    project_root: Path,
    payload: dict,
    selected_groups: Optional[List[str]] = None,
) -> dict:
    now = now_iso()
    state = load_yaml_map(
        compacted_state_path(project_root),
        {
            "schema_version": COMPACT_SCHEMA_VERSION,
            "counter": 0,
            "updated_at": now,
        },
    )
    counter = int(state.get("counter", 0)) + 1
    compact_id = f"{to_stamp(now)}-{counter:06d}"

    project_id = str(payload.get("project_id") or "")
    groups = selected_groups or payload.get("selected_groups") or []
    if not isinstance(groups, list):
        groups = []
    groups = [str(group_id) for group_id in groups if str(group_id).strip()]
    group_session_map = (
        upsert_group_sessions(project_root, project_id, groups) if project_id else {}
    )

    compact_payload = dict(payload)
    compact_payload["schema_version"] = COMPACT_SCHEMA_VERSION
    compact_payload["compact_id"] = compact_id
    compact_payload["session_code"] = compact_id
    compact_payload["group_session_map"] = group_session_map
    compact_payload["selected_groups"] = groups
    compact_payload["created_at"] = now
    compact_payload["updated_at"] = now

    compact_path = compacted_dir(project_root) / f"{compact_id}.yaml"
    dump_yaml(compact_path, compact_payload)

    latest = {
        "schema_version": COMPACT_SCHEMA_VERSION,
        "project_id": project_id,
        "compact_id": compact_id,
        "session_code": compact_id,
        "compact_path": str(compact_path),
        "updated_at": now,
    }
    dump_yaml(latest_compacted_path(project_root), latest)

    state["schema_version"] = COMPACT_SCHEMA_VERSION
    state["counter"] = counter
    state["updated_at"] = now
    dump_yaml(compacted_state_path(project_root), state)

    return {
        "compact_id": compact_id,
        "session_code": compact_id,
        "compact_path": compact_path,
        "latest_compacted_path": latest_compacted_path(project_root),
        "group_session_map": group_session_map,
    }


def load_compacted(project_root: Path, compact_id: str = "latest") -> dict:
    if compact_id == "latest":
        latest = load_yaml_map(latest_compacted_path(project_root), {})
        path_raw = latest.get("compact_path")
        if not isinstance(path_raw, str) or not path_raw.strip():
            raise FabricError(f"latest compacted session does not exist: {project_root}")
        compact_path = Path(path_raw).expanduser().resolve()
    else:
        compact_path = compacted_dir(project_root) / f"{compact_id}.yaml"
    if not compact_path.exists():
        raise FabricError(f"compacted session does not exist: {compact_path}")
    loaded = load_yaml(compact_path)
    if not isinstance(loaded, dict):
        raise FabricError(f"invalid compacted session: {compact_path}")
    found = str(loaded.get("schema_version") or "")
    if found != COMPACT_SCHEMA_VERSION:
        loaded["schema_version"] = COMPACT_SCHEMA_VERSION
        dump_yaml(compact_path, loaded)
    return loaded


def load_latest_compacted_summary(project_root: Path) -> Optional[dict]:
    try:
        compact = load_compacted(project_root, "latest")
    except Exception:
        return None
    selected_groups = compact.get("selected_groups", [])
    if not isinstance(selected_groups, list):
        selected_groups = []
    return {
        "session_code": str(compact.get("session_code") or compact.get("compact_id") or ""),
        "active_groups": [str(group_id) for group_id in selected_groups],
        "group_session_map": compact.get("group_session_map", {}),
        "compact_id": str(compact.get("compact_id") or ""),
    }
