#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from agents_inc.core.token_usage import write_turn_token_usage_report  # noqa: E402


class TokenUsageReportTests(unittest.TestCase):
    def test_write_turn_token_usage_report_aggregates_sessions(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            turn_dir = Path(td)
            session_a = (
                turn_dir
                / "cycles"
                / "cycle-0001"
                / "layer4"
                / "developer"
                / "web-research-specialist"
                / "codex-home"
                / "sessions"
                / "session-a.jsonl"
            )
            session_b = (
                turn_dir
                / "cycles"
                / "cycle-0001"
                / "layer4"
                / "developer"
                / "integration-specialist"
                / "codex-home"
                / "sessions"
                / "session-b.jsonl"
            )
            session_a.parent.mkdir(parents=True, exist_ok=True)
            session_b.parent.mkdir(parents=True, exist_ok=True)
            session_a.write_text(
                "\n".join(
                    [
                        json.dumps(
                            {
                                "type": "event_msg",
                                "payload": {
                                    "type": "token_count",
                                    "input_tokens": 100,
                                    "cached_input_tokens": 20,
                                    "output_tokens": 50,
                                    "reasoning_output_tokens": 10,
                                    "total_token_usage": 150,
                                },
                            }
                        ),
                        json.dumps(
                            {
                                "type": "event_msg",
                                "payload": {
                                    "type": "token_count",
                                    "input_tokens": 120,
                                    "cached_input_tokens": 30,
                                    "output_tokens": 60,
                                    "reasoning_output_tokens": 20,
                                    "total_token_usage": 180,
                                },
                            }
                        ),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            session_b.write_text(
                json.dumps(
                    {
                        "type": "event_msg",
                        "payload": {
                            "type": "token_count",
                            "input_tokens": 40,
                            "cached_input_tokens": 5,
                            "output_tokens": 30,
                            "reasoning_output_tokens": 5,
                            "total_token_usage": 70,
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            result = write_turn_token_usage_report(turn_dir=turn_dir)
            summary = result.get("summary", {})
            self.assertEqual(summary.get("input_tokens"), 160)
            self.assertEqual(summary.get("cached_input_tokens"), 35)
            self.assertEqual(summary.get("output_tokens"), 90)
            self.assertEqual(summary.get("reasoning_output_tokens"), 25)
            self.assertEqual(summary.get("total_token_usage"), 250)
            self.assertEqual(summary.get("billable_token_estimate"), 215)
            self.assertEqual(summary.get("sessions_with_usage"), 2)

            json_path = Path(str(result.get("json_path") or ""))
            md_path = Path(str(result.get("md_path") or ""))
            self.assertTrue(json_path.exists())
            self.assertTrue(md_path.exists())

    def test_write_turn_token_usage_report_handles_no_token_events(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            turn_dir = Path(td)
            session_a = (
                turn_dir
                / "cycles"
                / "cycle-0001"
                / "layer4"
                / "developer"
                / "domain-core-specialist"
                / "codex-home"
                / "sessions"
                / "session-a.jsonl"
            )
            session_a.parent.mkdir(parents=True, exist_ok=True)
            session_a.write_text(
                json.dumps({"type": "event_msg", "payload": {"type": "item.completed"}}) + "\n",
                encoding="utf-8",
            )
            result = write_turn_token_usage_report(turn_dir=turn_dir)
            summary = result.get("summary", {})
            self.assertEqual(summary.get("input_tokens"), 0)
            self.assertEqual(summary.get("cached_input_tokens"), 0)
            self.assertEqual(summary.get("output_tokens"), 0)
            self.assertEqual(summary.get("reasoning_output_tokens"), 0)
            self.assertEqual(summary.get("total_token_usage"), 0)
            self.assertEqual(summary.get("billable_token_estimate"), 0)
            self.assertEqual(summary.get("sessions_with_usage"), 0)

            report_payload = json.loads(Path(result["json_path"]).read_text(encoding="utf-8"))
            self.assertEqual(report_payload.get("scanned_session_file_count"), 1)
            self.assertEqual(report_payload.get("sessions_with_usage"), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
