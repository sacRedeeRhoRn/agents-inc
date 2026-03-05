from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import yaml

from agents_inc.core.context_state import load_global_context
from agents_inc.core.session_state import now_iso

CONFIG_SCHEMA_VERSION = "1.0"

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


def _default_config_path() -> Path:
    return (_effective_home() / ".agents-inc" / "config.yaml").resolve()


def _default_projects_root() -> Path:
    return (_effective_home() / "codex-projects").resolve()


def _global_config_candidates() -> set[Path]:
    return {
        _default_config_path().resolve(),
        (_real_user_home() / ".agents-inc" / "config.yaml").resolve(),
    }


def _find_upward_file(relative_path: Path, *, start: Optional[Path] = None) -> Optional[Path]:
    current = (start or Path.cwd()).expanduser().resolve()
    for base in (current, *current.parents):
        candidate = (base / relative_path).expanduser().resolve()
        if candidate.exists():
            return candidate
    return None


def default_config_path(raw: Optional[str] = None) -> Path:
    if raw:
        return Path(raw).expanduser().resolve()
    default_path = _default_config_path()
    discovered = _find_upward_file(Path(".agents-inc") / "config.yaml")
    if discovered is not None and discovered.resolve() not in _global_config_candidates():
        return discovered
    context = load_global_context()
    context_path = str(context.get("config_path") or "").strip()
    if context_path:
        return Path(context_path).expanduser().resolve()
    return default_path


def _default_config() -> dict:
    return {
        "schema_version": CONFIG_SCHEMA_VERSION,
        "defaults": {
            "projects_root": str(_default_projects_root()),
            "last_release_tag": "",
        },
        "updated_at": now_iso(),
    }


def load_config(path: Path) -> dict:
    config = _default_config()
    if not path.exists():
        return config
    with path.open("r", encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle) or {}
    if not isinstance(loaded, dict):
        return config
    defaults = loaded.get("defaults")
    if isinstance(defaults, dict):
        config["defaults"].update(defaults)
    updated_at = loaded.get("updated_at")
    if isinstance(updated_at, str) and updated_at.strip():
        config["updated_at"] = updated_at
    return config


def save_config(path: Path, config: dict) -> None:
    payload = _default_config()
    if isinstance(config, dict):
        defaults = config.get("defaults")
        if isinstance(defaults, dict):
            payload["defaults"].update(defaults)
        if isinstance(config.get("updated_at"), str):
            payload["updated_at"] = config["updated_at"]
    payload["schema_version"] = CONFIG_SCHEMA_VERSION
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(payload, handle, sort_keys=False)


def get_projects_root(config_path: Path) -> Path:
    config = load_config(config_path)
    raw = config.get("defaults", {}).get("projects_root")
    if isinstance(raw, str) and raw.strip():
        return Path(raw).expanduser().resolve()
    return _default_projects_root()


def set_projects_root(config_path: Path, projects_root: Path) -> dict:
    config = load_config(config_path)
    config.setdefault("defaults", {})
    config["defaults"]["projects_root"] = str(projects_root.expanduser().resolve())
    config["updated_at"] = now_iso()
    save_config(config_path, config)
    return config


def set_last_release_tag(config_path: Path, release_tag: str) -> dict:
    config = load_config(config_path)
    config.setdefault("defaults", {})
    config["defaults"]["last_release_tag"] = str(release_tag)
    config["updated_at"] = now_iso()
    save_config(config_path, config)
    return config
