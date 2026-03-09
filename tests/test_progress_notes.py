#!/usr/bin/env python3
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from agents_inc.core.progress_notes import format_progress_event  # noqa: E402


class ProgressNotesTests(unittest.TestCase):
    def test_runtime_group_note_is_rendered(self) -> None:
        text = format_progress_event(
            {
                "event": "runtime_group_note",
                "cycle": 3,
                "group_id": "developer",
                "text": "testing live worklog rendering",
            }
        )
        self.assertEqual(
            text,
            "live: cycle 3 group developer note | testing live worklog rendering",
        )

    def test_runtime_group_waiting_is_rendered(self) -> None:
        text = format_progress_event(
            {
                "event": "runtime_group_waiting",
                "cycle": 2,
                "group_id": "developer",
                "summary": "waiting on specialists 1/4 complete | pending=web-research",
            }
        )
        self.assertEqual(
            text,
            "live: cycle 2 group developer waiting | waiting on specialists 1/4 complete | pending=web-research",
        )

    def test_meeting_room_note_is_rendered(self) -> None:
        text = format_progress_event(
            {
                "event": "meeting_room_note",
                "cycle": 4,
                "text": "consensus ready: all groups aligned",
            }
        )
        self.assertEqual(
            text,
            "live: cycle 4 meeting room | consensus ready: all groups aligned",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
