from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

import yaml

from agents_inc.core.fabric_lib import now_iso

THREADS_SCHEMA_VERSION = "3.1"


def agent_threads_path(project_root: Path) -> Path:
    return project_root / ".agents-inc" / "state" / "agent-threads.yaml"


def load_agent_threads(project_root: Path) -> dict:
    path = agent_threads_path(project_root)
    if not path.exists():
        return {
            "schema_version": THREADS_SCHEMA_VERSION,
            "orchestrator": {},
            "heads": {},
            "specialists": {},
        }
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception:
        data = None
    if not isinstance(data, dict):
        data = {}
    out = {
        "schema_version": THREADS_SCHEMA_VERSION,
        "orchestrator": data.get("orchestrator", {}),
        "heads": data.get("heads", {}),
        "specialists": data.get("specialists", {}),
    }
    if not isinstance(out["orchestrator"], dict):
        out["orchestrator"] = {}
    if not isinstance(out["heads"], dict):
        out["heads"] = {}
    if not isinstance(out["specialists"], dict):
        out["specialists"] = {}
    return out


def save_agent_threads(project_root: Path, payload: dict) -> Path:
    path = agent_threads_path(project_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    clean = dict(payload)
    clean["schema_version"] = THREADS_SCHEMA_VERSION
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(clean, handle, sort_keys=False)
    return path


def get_orchestrator_thread(project_root: Path) -> Optional[str]:
    payload = load_agent_threads(project_root)
    orchestrator = payload.get("orchestrator", {})
    if not isinstance(orchestrator, dict):
        return None
    thread_id = str(orchestrator.get("thread_id") or "").strip()
    return thread_id or None


def set_orchestrator_thread(project_root: Path, thread_id: str, status: str) -> Path:
    payload = load_agent_threads(project_root)
    payload["orchestrator"] = {
        "thread_id": str(thread_id or "").strip(),
        "status": str(status or "").strip(),
        "updated_at": now_iso(),
    }
    return save_agent_threads(project_root, payload)


def get_head_thread(project_root: Path, group_id: str) -> Optional[str]:
    payload = load_agent_threads(project_root)
    heads = payload.get("heads", {})
    if not isinstance(heads, dict):
        return None
    row = heads.get(group_id)
    if not isinstance(row, dict):
        return None
    thread_id = str(row.get("thread_id") or "").strip()
    return thread_id or None


def set_head_thread(project_root: Path, group_id: str, thread_id: str, status: str) -> Path:
    payload = load_agent_threads(project_root)
    heads = payload.setdefault("heads", {})
    if not isinstance(heads, dict):
        heads = {}
        payload["heads"] = heads
    heads[group_id] = {
        "thread_id": str(thread_id or "").strip(),
        "status": str(status or "").strip(),
        "updated_at": now_iso(),
    }
    return save_agent_threads(project_root, payload)


def get_specialist_thread(project_root: Path, group_id: str, specialist_id: str) -> Optional[str]:
    payload = load_agent_threads(project_root)
    specialists = payload.get("specialists", {})
    if not isinstance(specialists, dict):
        return None
    group_rows = specialists.get(group_id)
    if not isinstance(group_rows, dict):
        return None
    row = group_rows.get(specialist_id)
    if not isinstance(row, dict):
        return None
    thread_id = str(row.get("thread_id") or "").strip()
    return thread_id or None


def set_specialist_thread(
    project_root: Path,
    group_id: str,
    specialist_id: str,
    thread_id: str,
    status: str,
) -> Path:
    payload = load_agent_threads(project_root)
    specialists = payload.setdefault("specialists", {})
    if not isinstance(specialists, dict):
        specialists = {}
        payload["specialists"] = specialists
    group_rows = specialists.setdefault(group_id, {})
    if not isinstance(group_rows, dict):
        group_rows = {}
        specialists[group_id] = group_rows
    group_rows[specialist_id] = {
        "thread_id": str(thread_id or "").strip(),
        "status": str(status or "").strip(),
        "updated_at": now_iso(),
    }
    return save_agent_threads(project_root, payload)


def thread_snapshot(project_root: Path) -> Dict[str, object]:
    payload = load_agent_threads(project_root)
    return {
        "schema_version": str(payload.get("schema_version") or THREADS_SCHEMA_VERSION),
        "orchestrator": payload.get("orchestrator", {}),
        "heads": payload.get("heads", {}),
        "specialists": payload.get("specialists", {}),
    }
