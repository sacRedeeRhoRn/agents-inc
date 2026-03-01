from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Dict, List, Optional

import yaml

from agents_inc.core.fabric_lib import FabricError, slugify
from agents_inc.core.session_state import now_iso, state_dir

CODEX_HOME_SCHEMA_VERSION = "2.2"
SKILL_ACTIVATION_SCHEMA_VERSION = "2.2"
DEFAULT_GLOBAL_CODEX_HOME = Path.home() / ".codex"


def resolve_project_codex_home(project_root: Path) -> Path:
    return state_dir(project_root).parent / "codex-home"


def resolve_project_skill_target(project_root: Path) -> Path:
    return resolve_project_codex_home(project_root) / "skills" / "local"


def codex_home_state_path(project_root: Path) -> Path:
    return state_dir(project_root) / "codex-home.yaml"


def skill_activation_state_path(project_root: Path) -> Path:
    return state_dir(project_root) / "skill-activation.yaml"


def _dump_yaml(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(payload, handle, sort_keys=False)


def _load_yaml(path: Path, default: dict) -> dict:
    if not path.exists():
        return dict(default)
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        return dict(default)
    payload = dict(default)
    payload.update(loaded)
    return payload


def _remove_path(path: Path) -> None:
    if not path.exists() and not path.is_symlink():
        return
    if path.is_symlink() or path.is_file():
        path.unlink()
        return
    shutil.rmtree(path)


def _ensure_symlink(src: Path, dst: Path) -> None:
    if dst.is_symlink() and dst.resolve() == src.resolve():
        return
    _remove_path(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.symlink_to(src)


def _default_codex_home_state(project_root: Path, project_id: str = "") -> dict:
    codex_home = resolve_project_codex_home(project_root)
    return {
        "schema_version": CODEX_HOME_SCHEMA_VERSION,
        "project_id": project_id,
        "codex_home": str(codex_home),
        "skills_dir": str(codex_home / "skills" / "local"),
        "skill_scope": "project-strict",
        "auth_link_mode": "symlink",
        "config_link_mode": "symlink",
        "updated_at": now_iso(),
    }


def load_codex_home_state(project_root: Path, project_id: str = "") -> dict:
    default = _default_codex_home_state(project_root, project_id=project_id)
    payload = _load_yaml(codex_home_state_path(project_root), default)
    payload["schema_version"] = CODEX_HOME_SCHEMA_VERSION
    return payload


def save_codex_home_state(project_root: Path, payload: dict) -> dict:
    state = _default_codex_home_state(
        project_root,
        project_id=str(payload.get("project_id") or ""),
    )
    state.update(payload)
    state["schema_version"] = CODEX_HOME_SCHEMA_VERSION
    state["updated_at"] = now_iso()
    _dump_yaml(codex_home_state_path(project_root), state)
    return state


def ensure_project_codex_home(
    project_root: Path,
    *,
    project_id: str,
    global_codex_home: Path = DEFAULT_GLOBAL_CODEX_HOME,
    config_link_mode: str = "symlink",
) -> dict:
    mode = str(config_link_mode or "symlink").strip().lower()
    if mode not in {"symlink", "copy"}:
        raise FabricError("config_link_mode must be 'symlink' or 'copy'")

    codex_home = resolve_project_codex_home(project_root)
    skills_dir = codex_home / "skills" / "local"
    skills_dir.mkdir(parents=True, exist_ok=True)

    auth_src = global_codex_home / "auth.json"
    auth_dst = codex_home / "auth.json"
    auth_mode = "missing"
    if auth_src.exists():
        _ensure_symlink(auth_src, auth_dst)
        auth_mode = "symlink"

    config_src = global_codex_home / "config.toml"
    config_dst = codex_home / "config.toml"
    config_mode = "missing"
    if config_src.exists():
        if mode == "symlink":
            _ensure_symlink(config_src, config_dst)
            config_mode = "symlink"
        else:
            _remove_path(config_dst)
            config_dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(config_src, config_dst)
            config_mode = "copy"

    payload = {
        "schema_version": CODEX_HOME_SCHEMA_VERSION,
        "project_id": slugify(project_id),
        "codex_home": str(codex_home),
        "skills_dir": str(skills_dir),
        "skill_scope": "project-strict",
        "auth_link_mode": auth_mode,
        "config_link_mode": config_mode,
        "updated_at": now_iso(),
    }
    _dump_yaml(codex_home_state_path(project_root), payload)
    return payload


def _normalize_groups(value: Optional[List[str]]) -> List[str]:
    if not value:
        return []
    out: List[str] = []
    for raw in value:
        group_id = str(raw or "").strip()
        if not group_id or group_id in out:
            continue
        out.append(group_id)
    return out


def _default_skill_activation() -> dict:
    return {
        "schema_version": SKILL_ACTIVATION_SCHEMA_VERSION,
        "active_head_groups": [],
        "active_specialist_groups": [],
        "updated_at": now_iso(),
    }


def load_skill_activation_state(project_root: Path) -> dict:
    payload = _load_yaml(skill_activation_state_path(project_root), _default_skill_activation())
    payload["schema_version"] = SKILL_ACTIVATION_SCHEMA_VERSION
    payload["active_head_groups"] = _normalize_groups(payload.get("active_head_groups"))
    payload["active_specialist_groups"] = _normalize_groups(payload.get("active_specialist_groups"))
    return payload


def save_skill_activation_state(
    project_root: Path,
    *,
    active_head_groups: List[str],
    active_specialist_groups: List[str],
) -> dict:
    payload = {
        "schema_version": SKILL_ACTIVATION_SCHEMA_VERSION,
        "active_head_groups": _normalize_groups(active_head_groups),
        "active_specialist_groups": _normalize_groups(active_specialist_groups),
        "updated_at": now_iso(),
    }
    _dump_yaml(skill_activation_state_path(project_root), payload)
    return payload


def ensure_skill_activation_state(
    project_root: Path,
    *,
    default_head_groups: Optional[List[str]] = None,
) -> dict:
    state_path = skill_activation_state_path(project_root)
    if state_path.exists():
        return load_skill_activation_state(project_root)
    return save_skill_activation_state(
        project_root,
        active_head_groups=_normalize_groups(default_head_groups),
        active_specialist_groups=[],
    )


def codex_launch_env(
    project_root: Path, base_env: Optional[Dict[str, str]] = None
) -> Dict[str, str]:
    env = dict(base_env or os.environ)
    env["CODEX_HOME"] = str(resolve_project_codex_home(project_root))
    return env
