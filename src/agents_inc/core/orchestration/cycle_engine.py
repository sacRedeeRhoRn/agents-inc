from __future__ import annotations

from typing import Dict


def build_cycle_summary(
    *,
    cycle_id: int,
    runtime_result: dict,
    objectives_hash: str,
    agent_timeout_sec: int,
    agent_timeout_mode: str,
    cycle_timeouts: list,
    cycle_escalations: list,
    latest_artifacts: Dict[str, str],
) -> dict:
    return {
        "cycle_id": cycle_id,
        "runtime_blocked": bool(runtime_result.get("blocked")),
        "blocked_groups": runtime_result.get("blocked_groups", []),
        "objectives_hash": objectives_hash,
        "agent_timeout_sec": agent_timeout_sec,
        "agent_timeout_mode": agent_timeout_mode,
        "timed_out_specialists": cycle_timeouts,
        "escalation_count": len(cycle_escalations),
        "latest_artifacts": latest_artifacts,
    }
