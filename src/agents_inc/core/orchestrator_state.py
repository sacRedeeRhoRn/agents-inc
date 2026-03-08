from __future__ import annotations

from pathlib import Path
from typing import Optional

from agents_inc.core.session_state import state_dir
from agents_inc.core.util.fs import dump_yaml, load_yaml_map
from agents_inc.core.util.time import now_iso

ORCHESTRATOR_STATE_SCHEMA_VERSION = "1.0"


def orchestrator_state_path(project_root: Path) -> Path:
    return state_dir(project_root) / "orchestrator-session.yaml"


def _default_state(project_id: str = "") -> dict:
    return {
        "schema_version": ORCHESTRATOR_STATE_SCHEMA_VERSION,
        "project_id": str(project_id or ""),
        "thread_id": "",
        "status": "inactive",
        "last_turn_id": "",
        "last_saved_checkpoint_id": "",
        "last_saved_at": "",
        "last_auto_resume_checkpoint_id": "",
        "last_auto_resume_status": "",
        "last_auto_resume_at": "",
        "chat_log_path": "",
        "prefix": "/agents-inc",
        "updated_at": now_iso(),
    }


def load_orchestrator_state(project_root: Path, project_id: str = "") -> dict:
    state = load_yaml_map(orchestrator_state_path(project_root), _default_state(project_id))
    state["schema_version"] = ORCHESTRATOR_STATE_SCHEMA_VERSION
    if project_id:
        state["project_id"] = project_id
    if not isinstance(state.get("thread_id"), str):
        state["thread_id"] = ""
    if not isinstance(state.get("status"), str):
        state["status"] = "inactive"
    if not isinstance(state.get("prefix"), str) or not str(state.get("prefix")).strip():
        state["prefix"] = "/agents-inc"
    return state


def save_orchestrator_state(project_root: Path, payload: dict) -> dict:
    state = _default_state(str(payload.get("project_id") or ""))
    state.update(payload)
    state["schema_version"] = ORCHESTRATOR_STATE_SCHEMA_VERSION
    state["updated_at"] = now_iso()
    dump_yaml(orchestrator_state_path(project_root), state)
    return state


def mark_orchestrator_saved(
    project_root: Path,
    *,
    project_id: str,
    checkpoint_id: str,
    saved_at: Optional[str] = None,
) -> dict:
    state = load_orchestrator_state(project_root, project_id=project_id)
    state["last_saved_checkpoint_id"] = str(checkpoint_id)
    state["last_saved_at"] = str(saved_at or now_iso())
    return save_orchestrator_state(project_root, state)
