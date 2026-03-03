from __future__ import annotations

from pathlib import Path
from typing import Optional

import yaml

from agents_inc.core.util.time import now_iso

CONTEXT_SCHEMA_VERSION = "1.0"


def default_context_path(raw: Optional[str] = None) -> Path:
    if raw:
        return Path(raw).expanduser().resolve()
    return Path.home() / ".agents-inc" / "context.yaml"


def _default_context() -> dict:
    return {
        "schema_version": CONTEXT_SCHEMA_VERSION,
        "config_path": "",
        "project_index": "",
        "projects_root": "",
        "fabric_root": "",
        "updated_at": "",
    }


def load_global_context(path: Optional[Path] = None) -> dict:
    target = (path or default_context_path()).expanduser().resolve()
    payload = _default_context()
    if not target.exists():
        return payload
    try:
        loaded = yaml.safe_load(target.read_text(encoding="utf-8")) or {}
    except Exception:  # noqa: BLE001
        return payload
    if not isinstance(loaded, dict):
        return payload

    for key in ("config_path", "project_index", "projects_root", "fabric_root", "updated_at"):
        value = loaded.get(key)
        if isinstance(value, str):
            payload[key] = value
    return payload


def save_global_context(payload: dict, path: Optional[Path] = None) -> Path:
    target = (path or default_context_path()).expanduser().resolve()
    merged = _default_context()
    if isinstance(payload, dict):
        for key in ("config_path", "project_index", "projects_root", "fabric_root"):
            value = payload.get(key)
            if isinstance(value, str):
                merged[key] = value
    merged["updated_at"] = now_iso()
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(merged, handle, sort_keys=False)
    return target
