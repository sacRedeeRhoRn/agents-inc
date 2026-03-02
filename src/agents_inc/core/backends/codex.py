from __future__ import annotations

from agents_inc.core.backends.base import AgentBackend


class CodexBackend(AgentBackend):
    name = "codex"

    def run(self, runner, config):  # type: ignore[override]
        return runner._run_codex(config)
