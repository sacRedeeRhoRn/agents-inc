from __future__ import annotations

from agents_inc.core.backends.base import AgentBackend


class MockBackend(AgentBackend):
    name = "mock"

    def run(self, runner, config):  # type: ignore[override]
        return runner._run_mock(config)
