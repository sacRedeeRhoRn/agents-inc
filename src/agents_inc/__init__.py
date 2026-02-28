"""agents-inc package."""

from __future__ import annotations

import re
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path


def _fallback_version() -> str:
    pyproject = Path(__file__).resolve().parents[2] / "pyproject.toml"
    if not pyproject.exists():
        return "0+unknown"
    text = pyproject.read_text(encoding="utf-8", errors="replace")
    match = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    return match.group(1) if match else "0+unknown"


def get_version() -> str:
    # Prefer local pyproject when running from a source checkout to avoid
    # mismatches with an older globally installed distribution.
    fallback = _fallback_version()
    if fallback != "0+unknown":
        return fallback
    try:
        return version("agents-inc")
    except PackageNotFoundError:
        return fallback


__version__ = get_version()

__all__ = ["__version__", "get_version"]
