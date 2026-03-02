"""Canonical text / serialisation utilities — single source of truth.

No other module in agents_inc defines slugify(), stable_json(), etc.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List

from agents_inc.core.util.errors import FabricError


def slugify(value: str) -> str:
    """Convert an arbitrary string to a URL/filename-safe slug.

    Raises FabricError if the result would be empty.
    """
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower())
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    if not slug:
        raise FabricError(f"cannot derive slug from '{value}'")
    return slug


def stable_json(data: Any) -> str:
    """Serialise *data* to JSON with sorted keys and 2-space indent."""
    return json.dumps(data, sort_keys=True, indent=2)


def format_bullet(items: Iterable[str], prefix: str = "- ") -> str:
    """Format an iterable as a Markdown bullet list.

    Returns '- (none)' when the iterable is empty or all-whitespace.
    """
    cleaned = [str(item).strip() for item in items if str(item).strip()]
    if not cleaned:
        return "- (none)"
    return "\n".join(prefix + item for item in cleaned)


def render_template(template: str, context: Dict[str, str]) -> str:
    """Replace ``{{key}}`` placeholders in *template* with *context* values."""
    out = template
    for key, val in context.items():
        out = out.replace("{{" + key + "}}", val)
    return out


def ensure_json_serializable(value: Any) -> Any:
    """Recursively convert Path objects to strings for JSON serialisation."""
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {k: ensure_json_serializable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [ensure_json_serializable(v) for v in value]
    return value


def ensure_unique_names(names: List[str]) -> List[str]:
    """Deduplicate a list of names, appending numeric suffixes when needed.

    All names are capped at 64 characters (Codex skill name limit).
    """
    used: set = set()
    out: List[str] = []
    for name in names:
        candidate = name
        suffix = 2
        while candidate in used:
            suffix_text = f"-{suffix}"
            if len(name) + len(suffix_text) <= 64:
                candidate = name + suffix_text
            else:
                base = name[: 64 - len(suffix_text)].rstrip("-")
                candidate = base + suffix_text
            suffix += 1
        used.add(candidate)
        out.append(candidate)
    return out
