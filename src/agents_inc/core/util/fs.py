"""Canonical filesystem I/O utilities — single source of truth.

No other module in agents_inc defines load_yaml(), dump_yaml(), write_text(),
load_yaml_map(), or atomic_write().

The private helpers _dump_yaml() and _load_yaml_map() that were duplicated
across session_state.py, session_compaction.py, codex_home.py, and
response_policy.py are replaced by the public functions here.
"""
from __future__ import annotations

import io
import os
from pathlib import Path
from typing import Any

import yaml

from agents_inc.core.util.errors import FabricError


# ── YAML I/O ──────────────────────────────────────────────────────────────


def load_yaml(path: Path) -> Any:
    """Load and parse a YAML file.  Raises FabricError if the file is missing."""
    if not path.exists():
        raise FabricError(f"missing file: {path}")
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def dump_yaml(path: Path, value: Any) -> None:
    """Write *value* to *path* as YAML, creating parent directories as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        yaml.safe_dump(value, fh, sort_keys=False)


def load_yaml_map(path: Path, default: dict) -> dict:
    """Load a YAML file that is expected to be a mapping.

    Returns a copy of *default* merged with the loaded mapping when the file
    exists and is valid; returns a copy of *default* otherwise.

    Replaces the private _load_yaml_map() helper that was duplicated in
    session_state.py, session_compaction.py, and codex_home.py.
    """
    if not path.exists():
        return dict(default)
    try:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return dict(default)
    if not isinstance(loaded, dict):
        return dict(default)
    out = dict(default)
    out.update(loaded)
    return out


# ── Text I/O ──────────────────────────────────────────────────────────────


def read_text(path: Path) -> str:
    """Read a text file.  Raises FabricError if the file is missing."""
    if not path.exists():
        raise FabricError(f"missing file: {path}")
    return path.read_text(encoding="utf-8")


def write_text(path: Path, value: str) -> None:
    """Write *value* to *path*, creating parent directories as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")


def atomic_write(path: Path, content: str) -> None:
    """Write *content* to *path* via a temp file + atomic rename.

    Guarantees that concurrent readers never see a partial write.
    The temp file is cleaned up on failure.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    try:
        tmp.write_text(content, encoding="utf-8")
        tmp.replace(path)
    except Exception:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def atomic_dump_yaml(path: Path, value: Any) -> None:
    """Like dump_yaml() but uses an atomic write via a temp file + rename."""
    buf = io.StringIO()
    yaml.safe_dump(value, buf, sort_keys=False)
    atomic_write(path, buf.getvalue())


# ── Directory helpers ──────────────────────────────────────────────────────


def copy_dir(src: Path, dst: Path) -> None:
    """Recursively copy *src* to *dst*, replacing *dst* if it exists."""
    if not src.exists():
        raise FabricError(f"missing source dir: {src}")
    if dst.exists():
        delete_dir(dst)
    dst.mkdir(parents=True, exist_ok=True)
    for path in sorted(src.rglob("*")):
        rel = path.relative_to(src)
        out = dst / rel
        if path.is_dir():
            out.mkdir(parents=True, exist_ok=True)
        else:
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(path.read_bytes())


def delete_dir(path: Path) -> None:
    """Recursively delete *path* (no-op if it does not exist)."""
    if not path.exists():
        return
    for item in sorted(path.rglob("*"), reverse=True):
        if item.is_file() or item.is_symlink():
            item.unlink()
        elif item.is_dir():
            item.rmdir()
    path.rmdir()
