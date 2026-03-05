from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Optional

from agents_inc.core.context_state import load_global_context
from agents_inc.core.fabric_lib import FabricError, load_yaml
from agents_inc.core.util.fs import dump_yaml, load_yaml_map
from agents_inc.core.util.time import now_iso, to_stamp  # noqa: F401  (now_iso re-exported)

STATE_SCHEMA_VERSION = "3.0"
INDEX_SCHEMA_VERSION = "3.0"
STATE_REL_DIR = Path(".agents-inc") / "state"

try:
    import pwd
except Exception:  # pragma: no cover - non-posix fallback
    pwd = None  # type: ignore[assignment]


def _effective_home() -> Path:
    return Path.home().expanduser().resolve()


def _real_user_home() -> Path:
    if pwd is None:  # pragma: no cover - non-posix fallback
        return _effective_home()
    try:
        return Path(pwd.getpwuid(os.getuid()).pw_dir).expanduser().resolve()
    except Exception:  # noqa: BLE001
        return _effective_home()


def _default_index_path() -> Path:
    return (_effective_home() / ".agents-inc" / "projects-index.yaml").resolve()


def _global_config_candidates() -> set[Path]:
    return {
        (_effective_home() / ".agents-inc" / "config.yaml").resolve(),
        (_real_user_home() / ".agents-inc" / "config.yaml").resolve(),
    }


def _global_local_index_candidates() -> set[Path]:
    return {
        (_effective_home() / ".agents-inc" / "projects" / "index.yaml").resolve(),
        (_real_user_home() / ".agents-inc" / "projects" / "index.yaml").resolve(),
    }


def _find_upward_file(relative_path: Path, *, start: Optional[Path] = None) -> Optional[Path]:
    current = (start or Path.cwd()).expanduser().resolve()
    for base in (current, *current.parents):
        candidate = (base / relative_path).expanduser().resolve()
        if candidate.exists():
            return candidate
    return None


def _require_schema(path: Path, payload: dict, expected: str, kind: str) -> None:
    found = str(payload.get("schema_version") or "")
    if found and found == expected:
        return
    raise FabricError(
        f"{kind} schema_version '{found or '<missing>'}' is not supported. "
        "Run 'agents-inc migrate-v2 --apply' before continuing."
    )


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
    default_index_path = _default_index_path()
    discovered = _find_upward_file(Path(".agents-inc") / "projects" / "index.yaml")
    if discovered is not None and discovered.resolve() not in _global_local_index_candidates():
        return discovered
    discovered_config = _find_upward_file(Path(".agents-inc") / "config.yaml")
    if discovered_config is not None and discovered_config.resolve() not in _global_config_candidates():
        return (discovered_config.parent / "projects" / "index.yaml").resolve()
    context = load_global_context()
    context_index = str(context.get("project_index") or "").strip()
    if context_index:
        return Path(context_index).expanduser().resolve()
    context_config = str(context.get("config_path") or "").strip()
    if context_config:
        return (
            Path(context_config).expanduser().resolve().parent / "projects" / "index.yaml"
        ).resolve()
    return default_index_path


def ensure_state_dirs(project_root: Path) -> None:
    checkpoints_dir(project_root).mkdir(parents=True, exist_ok=True)


def load_session_state(project_root: Path) -> dict:
    default = {
        "schema_version": STATE_SCHEMA_VERSION,
        "checkpoint_counter": 0,
    }
    path = session_state_path(project_root)
    loaded = load_yaml_map(path, default)
    if path.exists():
        found = str(loaded.get("schema_version") or "")
        if found != STATE_SCHEMA_VERSION:
            loaded["schema_version"] = STATE_SCHEMA_VERSION
            dump_yaml(path, loaded)
    return loaded


def save_session_state(project_root: Path, state: dict) -> None:
    ensure_state_dirs(project_root)
    clean = dict(state)
    clean["schema_version"] = STATE_SCHEMA_VERSION
    dump_yaml(session_state_path(project_root), clean)


def load_project_index(path: Path) -> dict:
    default = {
        "schema_version": INDEX_SCHEMA_VERSION,
        "projects": {},
    }
    data = load_yaml_map(path, default)
    if path.exists():
        found = str(data.get("schema_version") or "")
        if found != INDEX_SCHEMA_VERSION:
            # Auto-upgrade old index schema to avoid breaking checkpoint writes on
            # otherwise valid project metadata.
            data["schema_version"] = INDEX_SCHEMA_VERSION
            save_project_index(path, data)
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
    dump_yaml(path, clean)


def mark_stale_index_entries(index_path: Path) -> dict:
    index_data = load_project_index(index_path)
    projects = index_data.setdefault("projects", {})
    changed = False
    for payload in projects.values():
        if not isinstance(payload, dict):
            continue
        if str(payload.get("status") or "") == "inactive":
            # Explicitly deactivated projects stay inactive until user reactivates them.
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
    return list_index_projects(index_path, include_stale=False)


def list_index_projects(index_path: Path, include_stale: bool = False) -> List[dict]:
    index_data = mark_stale_index_entries(index_path)
    projects = index_data.get("projects", {})
    out: List[dict] = []
    if not isinstance(projects, dict):
        return out
    for project_id, payload in sorted(projects.items()):
        if not isinstance(payload, dict):
            continue
        if not include_stale and payload.get("status") != "active":
            continue
        out.append({"project_id": project_id, **payload})
    return out


def get_index_project(index_path: Path, project_id: str) -> Optional[dict]:
    index_data = mark_stale_index_entries(index_path)
    projects = index_data.get("projects", {})
    if not isinstance(projects, dict):
        return None
    payload = projects.get(project_id)
    if not isinstance(payload, dict):
        return None
    return {"project_id": project_id, **payload}


def set_index_project_status(index_path: Path, project_id: str, status: str) -> dict:
    normalized = str(status).strip().lower()
    if normalized not in {"active", "stale", "inactive"}:
        raise FabricError(f"unsupported project status: {status}")
    index_data = load_project_index(index_path)
    projects = index_data.setdefault("projects", {})
    if not isinstance(projects, dict) or project_id not in projects:
        raise FabricError(f"project '{project_id}' not found in index")
    payload = projects.get(project_id)
    if not isinstance(payload, dict):
        raise FabricError(f"invalid project entry for '{project_id}'")
    payload["status"] = normalized
    payload["updated_at"] = now_iso()
    save_project_index(index_path, index_data)
    return {"project_id": project_id, **payload}


def remove_index_project(index_path: Path, project_id: str) -> bool:
    index_data = load_project_index(index_path)
    projects = index_data.setdefault("projects", {})
    if not isinstance(projects, dict):
        return False
    if project_id not in projects:
        return False
    projects.pop(project_id, None)
    save_project_index(index_path, index_data)
    return True


def _find_local_project_manifest(project_root: Path, project_id: str) -> Optional[Path]:
    candidate = (
        project_root
        / "agent_group_fabric"
        / "generated"
        / "projects"
        / project_id
        / "manifest.yaml"
    )
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


def _checkpoint_info_for_project_root(project_root: Path) -> Dict[str, str]:
    checkpoint_path = latest_checkpoint_path(project_root)
    checkpoint_id = "latest"
    if checkpoint_path.exists():
        loaded = load_yaml_map(checkpoint_path, {})
        if isinstance(loaded.get("checkpoint_id"), str):
            checkpoint_id = loaded["checkpoint_id"]
    return {
        "checkpoint_id": checkpoint_id,
        "checkpoint_path": str(checkpoint_path),
    }


def sync_index_from_scan(index_path: Path, scan_root: Path) -> Dict[str, int]:
    index_data = load_project_index(index_path)
    projects = index_data.setdefault("projects", {})
    if not isinstance(projects, dict):
        projects = {}
        index_data["projects"] = projects

    created = 0
    updated = 0
    changed = False
    now = now_iso()

    for found in discover_projects(scan_root):
        project_id = str(found["project_id"])
        project_root = Path(str(found["project_root"])).expanduser().resolve()
        fabric_root = Path(str(found["fabric_root"])).expanduser().resolve()
        cp = _checkpoint_info_for_project_root(project_root)
        next_payload = {
            "project_root": str(project_root),
            "fabric_root": str(fabric_root),
            "last_checkpoint": cp["checkpoint_id"],
            "last_checkpoint_path": cp["checkpoint_path"],
            "updated_at": now,
            "status": "active" if project_root.exists() else "stale",
        }
        prev = projects.get(project_id)
        if not isinstance(prev, dict):
            projects[project_id] = next_payload
            created += 1
            changed = True
            continue

        if str(prev.get("status") or "") == "inactive":
            next_payload["status"] = "inactive"

        stable_prev = dict(prev)
        stable_prev.pop("updated_at", None)
        stable_next = dict(next_payload)
        stable_next.pop("updated_at", None)
        if stable_prev != stable_next:
            projects[project_id] = next_payload
            updated += 1
            changed = True

    if changed:
        save_project_index(index_path, index_data)

    mark_stale_index_entries(index_path)
    return {"created": created, "updated": updated}


def find_resume_project(
    *,
    index_path: Path,
    project_id: Optional[str],
    fallback_scan_root: Path,
) -> Optional[dict]:
    active = list_active_index_projects(index_path)
    if project_id:
        indexed = get_index_project(index_path, project_id)
        if isinstance(indexed, dict) and str(indexed.get("status") or "") == "inactive":
            return None

        for payload in active:
            if payload.get("project_id") == project_id:
                return payload

        # If a project has an explicit index entry (active/stale/inactive), do not
        # silently replace it by scan fallback.
        if isinstance(indexed, dict):
            return None

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
                    latest = load_yaml_map(checkpoint_path, {})
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
        latest = load_yaml_map(latest_checkpoint_path(project_root), {})
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
    found = str(data.get("schema_version") or "")
    if found != STATE_SCHEMA_VERSION:
        data["schema_version"] = STATE_SCHEMA_VERSION
        dump_yaml(cp_path, data)
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
    checkpoint_id = f"{to_stamp(created_at)}-{counter:06d}"

    checkpoint_payload = dict(payload)
    checkpoint_payload["schema_version"] = STATE_SCHEMA_VERSION
    checkpoint_payload["checkpoint_id"] = checkpoint_id
    checkpoint_payload["created_at"] = created_at
    checkpoint_payload["updated_at"] = created_at

    checkpoint_path = checkpoints_dir(project_root) / f"{checkpoint_id}.yaml"
    dump_yaml(checkpoint_path, checkpoint_payload)

    latest_payload = {
        "schema_version": STATE_SCHEMA_VERSION,
        "project_id": payload.get("project_id"),
        "checkpoint_id": checkpoint_id,
        "checkpoint_path": str(checkpoint_path),
        "updated_at": created_at,
    }
    dump_yaml(latest_checkpoint_path(project_root), latest_payload)

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
