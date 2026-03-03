from __future__ import annotations

import json
import unittest
from pathlib import Path

from agents_inc.core.codex_app_client import CodexAppClient


class CodexAppClientTests(unittest.TestCase):
    def test_wait_response_buffers_non_target_notifications(self) -> None:
        client = CodexAppClient(cwd=Path("."))
        client._events.put(("stdout", json.dumps({"method": "thread/started", "params": {}})))  # type: ignore[attr-defined]
        client._events.put(("stdout", json.dumps({"id": 7, "result": {"ok": True}})))  # type: ignore[attr-defined]

        result = client._wait_response(7, timeout_sec=0.5)  # type: ignore[attr-defined]
        self.assertEqual(result, {"ok": True})

        buffered = client._next_event(timeout_sec=0.0)  # type: ignore[attr-defined]
        self.assertIsNotNone(buffered)
        _, payload = buffered or ("", "")
        obj = json.loads(payload)
        self.assertEqual(obj.get("method"), "thread/started")

    def test_wait_response_finds_matching_buffered_response(self) -> None:
        client = CodexAppClient(cwd=Path("."))
        client._buffered_events.append(  # type: ignore[attr-defined]
            ("stdout", json.dumps({"id": 3, "result": {"thread": {"id": "thr-1"}}}))
        )

        result = client._wait_response(3, timeout_sec=0.2)  # type: ignore[attr-defined]
        thread = result.get("thread", {})
        self.assertEqual(thread.get("id"), "thr-1")

    def test_run_turn_consumes_buffered_notifications(self) -> None:
        client = CodexAppClient(cwd=Path("."))

        def _fake_request(method: str, params: dict, *, timeout_sec: float) -> dict:
            _ = (method, params, timeout_sec)
            return {"turn": {"id": "turn-1"}}

        client._request = _fake_request  # type: ignore[method-assign]
        client._buffered_events.extend(  # type: ignore[attr-defined]
            [
                (
                    "stdout",
                    json.dumps(
                        {
                            "method": "item/agentMessage/delta",
                            "params": {"turnId": "turn-1", "delta": "O"},
                        }
                    ),
                ),
                (
                    "stdout",
                    json.dumps(
                        {
                            "method": "item/agentMessage/delta",
                            "params": {"turnId": "turn-1", "delta": "K"},
                        }
                    ),
                ),
                (
                    "stdout",
                    json.dumps(
                        {
                            "method": "turn/completed",
                            "params": {"turn": {"id": "turn-1", "status": "completed"}},
                        }
                    ),
                ),
            ]
        )

        turn = client.run_turn(thread_id="thread-1", text="say ok", timeout_sec=0.5)
        self.assertEqual(turn.turn_id, "turn-1")
        self.assertEqual(turn.text, "OK")


if __name__ == "__main__":
    unittest.main(verbosity=2)
