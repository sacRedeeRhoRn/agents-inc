from __future__ import annotations

from pathlib import Path
from typing import Optional

import yaml

from agents_inc.core.session_state import now_iso

CONFIG_SCHEMA_VERSION = "1.0"
DEFAULT_CONFIG_PATH = Path.home() / ".agents-inc" / "config.yaml"
DEFAULT_PROJECTS_ROOT = Path.home() / "codex-projects"


def default_config_path(raw: Optional[str] = None) -> Path:
    if raw:
        return Path(raw).expanduser().resolve()
    return DEFAULT_CONFIG_PATH


def _default_config() -> dict:
    return {
        "schema_version": CONFIG_SCHEMA_VERSION,
        "defaults": {
            "projects_root": str(DEFAULT_PROJECTS_ROOT),
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
    return DEFAULT_PROJECTS_ROOT


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
