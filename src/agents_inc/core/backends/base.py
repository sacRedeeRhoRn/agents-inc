from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents_inc.core.agent_session_runner import AgentRunConfig, AgentRunResult, AgentSessionRunner


class AgentBackend(ABC):
    name: str = ""

    @abstractmethod
    def run(self, runner: "AgentSessionRunner", config: "AgentRunConfig") -> "AgentRunResult":
        raise NotImplementedError
