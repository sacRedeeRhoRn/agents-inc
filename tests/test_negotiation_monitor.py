#!/usr/bin/env python3
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from agents_inc.core.negotiation_monitor import (  # noqa: E402
    NegotiationCycleRecord,
    evaluate_negotiation,
)


class NegotiationMonitorTests(unittest.TestCase):
    def test_fails_when_no_meetings(self) -> None:
        monitor = evaluate_negotiation(
            selected_groups=["g1", "g2"],
            cycles=[],
            require_negotiation=True,
            final_all_satisfied=False,
        )
        self.assertFalse(bool(monitor["passed"]))
        self.assertIn("meeting_cycles_executed_gte_1", monitor["checks"])
        self.assertFalse(bool(monitor["checks"]["meeting_cycles_executed_gte_1"]))

    def test_passes_with_peer_actions_and_satisfaction(self) -> None:
        cycles = [
            NegotiationCycleRecord(
                cycle_id=1,
                objectives={"g1": "a", "g2": "b"},
                refined_objectives={"g1": "a refined", "g2": "b refined"},
                decisions={
                    "g1": {
                        "request_changes": ["g2: tighten evidence"],
                        "criticisms": [],
                        "accepted_items": [],
                        "new_actions": ["add citation links"],
                    },
                    "g2": {
                        "request_changes": [],
                        "criticisms": ["g1: clarify assumptions"],
                        "accepted_items": ["g1: accepted baseline"],
                        "new_actions": ["add confidence bounds"],
                    },
                },
                unsatisfied_groups=["g1", "g2"],
            )
        ]
        monitor = evaluate_negotiation(
            selected_groups=["g1", "g2"],
            cycles=cycles,
            require_negotiation=True,
            final_all_satisfied=True,
        )
        self.assertTrue(bool(monitor["passed"]))
        self.assertTrue(bool(monitor["checks"]["cross_group_critique_or_request_exists"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
