#!/usr/bin/env python3
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from agents_inc.core.live_dashboard import LiveDashboard  # noqa: E402


@unittest.skipUnless(LiveDashboard.supported(), "rich not installed")
class LiveDashboardTests(unittest.TestCase):
    def test_turn_started_resets_previous_dashboard_state(self) -> None:
        dashboard = LiveDashboard()

        dashboard.handle_event(
            {
                "event": "turn_started",
                "project_id": "proj-old",
                "execution_mode": "light",
                "max_cycles": 0,
                "heartbeat_sec": 30,
                "selected_groups": ["developer", "quality-assurance"],
            }
        )
        dashboard.handle_event({"event": "cycle_started", "cycle": 3})
        dashboard.handle_event(
            {"event": "runtime_group_note", "group_id": "developer", "text": "old worklog"}
        )
        dashboard.handle_event({"event": "meeting_room_note", "text": "old meeting note"})
        dashboard.handle_event({"event": "turn_blocked", "status": "BLOCKED_TEST"})

        dashboard.handle_event(
            {
                "event": "turn_started",
                "project_id": "proj-new",
                "execution_mode": "light",
                "max_cycles": 0,
                "heartbeat_sec": 15,
                "selected_groups": ["literature-intelligence"],
            }
        )

        self.assertEqual(dashboard._project_id, "proj-new")
        self.assertEqual(dashboard._cycle, 0)
        self.assertEqual(dashboard._turn_state, "running")
        self.assertEqual(dashboard._blocked_status, "")
        self.assertEqual(list(dashboard._meeting_lines), [])
        self.assertEqual(sorted(dashboard._groups.keys()), ["literature-intelligence"])
        self.assertEqual(list(dashboard._groups["literature-intelligence"].lines), [])

    def test_stop_clears_terminal_when_alt_screen_unavailable(self) -> None:
        dashboard = LiveDashboard()

        class _FakeConsole:
            is_terminal = True

            def __init__(self) -> None:
                self.clear_calls = []

            def clear(self, home: bool = True) -> None:
                self.clear_calls.append(home)

        class _FakeLive:
            def __init__(self, console) -> None:
                self.console = console
                self._alt_screen = False
                self.stopped = False

            def stop(self) -> None:
                self.stopped = True

        console = _FakeConsole()
        live = _FakeLive(console)
        dashboard._live = live

        dashboard.stop()

        self.assertTrue(live.stopped)
        self.assertEqual(console.clear_calls, [True])
        self.assertIsNone(dashboard._live)

    def test_stop_does_not_clear_terminal_when_alt_screen_used(self) -> None:
        dashboard = LiveDashboard()

        class _FakeConsole:
            is_terminal = True

            def __init__(self) -> None:
                self.clear_calls = []

            def clear(self, home: bool = True) -> None:
                self.clear_calls.append(home)

        class _FakeLive:
            def __init__(self, console) -> None:
                self.console = console
                self._alt_screen = True
                self.stopped = False

            def stop(self) -> None:
                self.stopped = True

        console = _FakeConsole()
        live = _FakeLive(console)
        dashboard._live = live

        dashboard.stop()

        self.assertTrue(live.stopped)
        self.assertEqual(console.clear_calls, [])
        self.assertIsNone(dashboard._live)


if __name__ == "__main__":
    unittest.main(verbosity=2)
