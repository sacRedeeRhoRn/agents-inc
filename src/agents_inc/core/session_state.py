from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import yaml

from agents_inc.core.fabric_lib import FabricError, load_yaml

STATE_SCHEMA_VERSION = "1.0"
INDEX_SCHEMA_VERSION = "1.0"
STATE_REL_DIR = Path(".agents-inc") / "state"
DEFAULT_INDEX_PATH = Path.home() / ".agents-inc" / "projects-index.yaml"


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _stamp(iso_value: str) -> str:
    return iso_value.replace("-", "").replace(":", "").replace("+00:00", "Z").replace(".", "")


def _load_yaml_map(path: Path, default: dict) -> dict:
    if not path.exists():
        return dict(default)
    loaded = load_yaml(path)
    if not isinstance(loaded, dict):
        return dict(default)
    out = dict(default)
    out.update(loaded)
    return out


def _dump_yaml(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(value, handle, sort_keys=False)


def state_dir(project_root: Path) -> Path:
    return project_root / STATE_REL_DIR


def session_state_path(project_root: Path) -> Path:
    return state_dir(project_root) / "session-state.yaml"


def latest_checkpoint_path(project_root: Path) -> Path:
    return state_dir(project_root) / "latest-checkpoint.yaml"


def checkpoints_dir(project_root: Path) -> Path:
    return state_dir(project_root) / "checkpoints"


def default_project_index_path(raw: Optional[str] = None) -> Path:
    if raw:
        return Path(raw).expanduser().resolve()
    return DEFAULT_INDEX_PATH


def ensure_state_dirs(project_root: Path) -> None:
    checkpoints_dir(project_root).mkdir(parents=True, exist_ok=True)


def load_session_state(project_root: Path) -> dict:
    default = {
        "schema_version": STATE_SCHEMA_VERSION,
        "checkpoint_counter": 0,
    }
    return _load_yaml_map(session_state_path(project_root), default)


def save_session_state(project_root: Path, state: dict) -> None:
    ensure_state_dirs(project_root)
    clean = dict(state)
    clean["schema_version"] = STATE_SCHEMA_VERSION
    _dump_yaml(session_state_path(project_root), clean)


def load_project_index(path: Path) -> dict:
    default = {
        "schema_version": INDEX_SCHEMA_VERSION,
        "projects": {},
    }
    data = _load_yaml_map(path, default)
    projects = data.get("projects")
    if not isinstance(projects, dict):
        data["projects"] = {}
    data["schema_version"] = INDEX_SCHEMA_VERSION
    return data


def save_project_index(path: Path, index_data: dict) -> None:
    clean = dict(index_data)
    clean["schema_version"] = INDEX_SCHEMA_VERSION
    projects = clean.get("projects")
    if not isinstance(projects, dict):
        clean["projects"] = {}
    _dump_yaml(path, clean)


def mark_stale_index_entries(index_path: Path) -> dict:
    index_data = load_project_index(index_path)
    projects = index_data.setdefault("projects", {})
    changed = False
    for payload in projects.values():
        if not isinstance(payload, dict):
            continue
        project_root_raw = payload.get("project_root")
        if not isinstance(project_root_raw, str):
            continue
        is_active = Path(project_root_raw).expanduser().exists()
        status = "active" if is_active else "stale"
        if payload.get("status") != status:
            payload["status"] = status
            changed = True
    if changed:
        save_project_index(index_path, index_data)
    return index_data


def upsert_project_index_entry(
    *,
    index_path: Path,
    project_id: str,
    project_root: Path,
    fabric_root: Path,
    checkpoint_id: str,
    checkpoint_path: Path,
    updated_at: str,
) -> None:
    index_data = load_project_index(index_path)
    projects = index_data.setdefault("projects", {})
    projects[project_id] = {
        "project_root": str(project_root),
        "fabric_root": str(fabric_root),
        "last_checkpoint": checkpoint_id,
        "last_checkpoint_path": str(checkpoint_path),
        "updated_at": updated_at,
        "status": "active" if project_root.exists() else "stale",
    }
    save_project_index(index_path, index_data)


def list_active_index_projects(index_path: Path) -> List[dict]:
    index_data = mark_stale_index_entries(index_path)
    projects = index_data.get("projects", {})
    out: List[dict] = []
    if not isinstance(projects, dict):
        return out
    for project_id, payload in sorted(projects.items()):
        if not isinstance(payload, dict):
            continue
        if payload.get("status") != "active":
            continue
        out.append({"project_id": project_id, **payload})
    return out


def _find_local_project_manifest(project_root: Path, project_id: str) -> Optional[Path]:
    candidate = project_root / "agent_group_fabric" / "generated" / "projects" / project_id / "manifest.yaml"
    if candidate.exists():
        return candidate
    return None


def discover_projects(scan_root: Path) -> List[dict]:
    out: List[dict] = []
    if not scan_root.exists():
        return out
    for child in sorted(scan_root.iterdir()):
        if not child.is_dir():
            continue
        generated = child / "agent_group_fabric" / "generated" / "projects"
        if not generated.exists():
            continue
        for manifest_path in sorted(generated.glob("*/manifest.yaml")):
            project_id = manifest_path.parent.name
            out.append(
                {
                    "project_id": project_id,
                    "project_root": str(child),
                    "fabric_root": str(child / "agent_group_fabric"),
                    "manifest_path": str(manifest_path),
                }
            )
    return out


def find_resume_project(
    *,
    index_path: Path,
    project_id: Optional[str],
    fallback_scan_root: Path,
) -> Optional[dict]:
    active = list_active_index_projects(index_path)
    if project_id:
        for payload in active:
            if payload.get("project_id") == project_id:
                return payload

        for found in discover_projects(fallback_scan_root):
            if found.get("project_id") != project_id:
                continue
            root = Path(str(found["project_root"])).expanduser().resolve()
            fabric = Path(str(found["fabric_root"])).expanduser().resolve()
            manifest_path = _find_local_project_manifest(root, project_id)
            if manifest_path:
                now = now_iso()
                checkpoint = "latest"
                checkpoint_path = latest_checkpoint_path(root)
                if checkpoint_path.exists():
                    latest = _load_yaml_map(checkpoint_path, {})
                    if isinstance(latest.get("checkpoint_id"), str):
                        checkpoint = latest["checkpoint_id"]
                upsert_project_index_entry(
                    index_path=index_path,
                    project_id=project_id,
                    project_root=root,
                    fabric_root=fabric,
                    checkpoint_id=checkpoint,
                    checkpoint_path=checkpoint_path,
                    updated_at=now,
                )
                return {
                    "project_id": project_id,
                    "project_root": str(root),
                    "fabric_root": str(fabric),
                    "last_checkpoint": checkpoint,
                    "last_checkpoint_path": str(checkpoint_path),
                    "updated_at": now,
                    "status": "active",
                }
        return None

    if len(active) == 1:
        return active[0]
    return None


def load_checkpoint(project_root: Path, checkpoint_id: str = "latest") -> dict:
    if checkpoint_id == "latest":
        latest = _load_yaml_map(latest_checkpoint_path(project_root), {})
        cp_path_raw = latest.get("checkpoint_path")
        if not isinstance(cp_path_raw, str):
            raise FabricError(f"latest checkpoint does not exist: {project_root}")
        cp_path = Path(cp_path_raw).expanduser().resolve()
    else:
        cp_path = checkpoints_dir(project_root) / f"{checkpoint_id}.yaml"
    if not cp_path.exists():
        raise FabricError(f"checkpoint does not exist: {cp_path}")

    data = load_yaml(cp_path)
    if not isinstance(data, dict):
        raise FabricError(f"invalid checkpoint: {cp_path}")
    return data


def resolve_state_project_root(fabric_root: Path, project_id: str) -> Path:
    if fabric_root.name == "agent_group_fabric":
        parent = fabric_root.parent
        manifest_path = parent / "project-manifest.yaml"
        if manifest_path.exists():
            try:
                manifest = load_yaml(manifest_path)
                if isinstance(manifest, dict) and manifest.get("project_id") == project_id:
                    return parent
            except Exception:
                pass
        if (parent / "kickoff.md").exists() or (parent / "router-call.txt").exists():
            return parent
        if (parent / ".agents-inc").exists():
            return parent
    return fabric_root / "generated" / "projects" / project_id


def write_checkpoint(
    *,
    project_root: Path,
    payload: dict,
    project_index_path: Path,
) -> dict:
    ensure_state_dirs(project_root)
    current = load_session_state(project_root)

    counter = int(current.get("checkpoint_counter", 0)) + 1
    created_at = now_iso()
    checkpoint_id = f"{_stamp(created_at)}-{counter:06d}"

    checkpoint_payload = dict(payload)
    checkpoint_payload["schema_version"] = STATE_SCHEMA_VERSION
    checkpoint_payload["checkpoint_id"] = checkpoint_id
    checkpoint_payload["created_at"] = created_at
    checkpoint_payload["updated_at"] = created_at

    checkpoint_path = checkpoints_dir(project_root) / f"{checkpoint_id}.yaml"
    _dump_yaml(checkpoint_path, checkpoint_payload)

    latest_payload = {
        "schema_version": STATE_SCHEMA_VERSION,
        "project_id": payload.get("project_id"),
        "checkpoint_id": checkpoint_id,
        "checkpoint_path": str(checkpoint_path),
        "updated_at": created_at,
    }
    _dump_yaml(latest_checkpoint_path(project_root), latest_payload)

    updated_state = {
        **current,
        "schema_version": STATE_SCHEMA_VERSION,
        "project_id": payload.get("project_id"),
        "project_root": str(project_root),
        "fabric_root": payload.get("fabric_root"),
        "checkpoint_counter": counter,
        "latest_checkpoint_id": checkpoint_id,
        "latest_checkpoint_path": str(checkpoint_path),
        "updated_at": created_at,
    }
    save_session_state(project_root, updated_state)

    project_id = payload.get("project_id")
    if isinstance(project_id, str) and project_id:
        fabric_root = payload.get("fabric_root")
        if isinstance(fabric_root, str) and fabric_root:
            upsert_project_index_entry(
                index_path=project_index_path,
                project_id=project_id,
                project_root=project_root,
                fabric_root=Path(fabric_root),
                checkpoint_id=checkpoint_id,
                checkpoint_path=checkpoint_path,
                updated_at=created_at,
            )

    return {
        "checkpoint_id": checkpoint_id,
        "checkpoint_path": checkpoint_path,
        "latest_checkpoint_path": latest_checkpoint_path(project_root),
        "session_state_path": session_state_path(project_root),
        "project_index_path": project_index_path,
    }
