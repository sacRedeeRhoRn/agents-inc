from __future__ import annotations

DEFAULT_SPECIALIST_MODEL = "gpt-5.3-codex-spark"
DEFAULT_HEAD_MODEL = "gpt-5.3-codex"
DEFAULT_HEAD_REASONING_EFFORT = "xhigh"

_MODEL_ALIASES = {
    "codex-5.3": DEFAULT_HEAD_MODEL,
    "codex-5.3-spark": DEFAULT_SPECIALIST_MODEL,
}

_REASONING_ALIASES = {
    "extra": "xhigh",
    "xhigh": "xhigh",
    "high": "high",
    "medium": "medium",
    "low": "low",
}


def normalize_model_slug(value: str | None, *, default: str) -> str:
    raw = str(value or "").strip()
    if not raw:
        return default
    return _MODEL_ALIASES.get(raw.lower(), raw)


def normalize_reasoning_effort(value: str | None, *, default: str | None) -> str | None:
    raw = str(value or "").strip()
    if not raw:
        return default
    return _REASONING_ALIASES.get(raw.lower(), raw)
