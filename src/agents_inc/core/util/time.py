"""Canonical time utilities — single source of truth.

No other module in agents_inc defines now_iso() or to_stamp().
All callers import from here (or through the fabric_lib backward-compat shim).
"""

from __future__ import annotations

from datetime import datetime, timezone


def now_iso() -> str:
    """Return current UTC time as ISO 8601 string (second precision, Z suffix).

    Example: '2026-03-02T12:00:00Z'
    """
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def to_stamp(iso_value: str) -> str:
    """Compact ISO timestamp suitable for filenames (no separators).

    Example: '20260302T120000Z'

    Was duplicated as _stamp() in session_state.py and session_compaction.py.
    """
    return iso_value.replace("-", "").replace(":", "").replace("+00:00", "Z").replace(".", "")
