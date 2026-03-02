from __future__ import annotations

from agents_inc.core.backends.base import AgentBackend
from agents_inc.core.backends.codex import CodexBackend
from agents_inc.core.backends.mock import MockBackend

_BACKENDS = {
    "codex": CodexBackend,
    "mock": MockBackend,
}


def available_backends() -> list[str]:
    return sorted(_BACKENDS.keys())


def resolve_backend(name: str) -> AgentBackend:
    normalized = str(name or "").strip().lower()
    backend_cls = _BACKENDS.get(normalized)
    if backend_cls is None:
        backend_cls = CodexBackend
    return backend_cls()
