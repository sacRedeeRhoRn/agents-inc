from __future__ import annotations

import json
import threading
import unittest
from pathlib import Path

from agents_inc.core.codex_app_client import CodexAppClient, CodexAppServerError


class CodexAppClientTests(unittest.TestCase):
    def test_start_thread_requests_network_enabled_workspace_write(self) -> None:
        client = CodexAppClient(cwd=Path("."), approval_policy="never")
        captured: dict = {}

        def _fake_request(method: str, params: dict, *, timeout_sec: float) -> dict:
            captured["method"] = method
            captured["params"] = dict(params)
            captured["timeout_sec"] = float(timeout_sec)
            return {"thread": {"id": "thr-123"}}

        client._request = _fake_request  # type: ignore[method-assign]
        thread_id = client.start_thread()

        self.assertEqual(thread_id, "thr-123")
        self.assertEqual(captured.get("method"), "thread/start")
        params = captured.get("params", {})
        self.assertEqual(params.get("approvalPolicy"), "never")
        self.assertEqual(params.get("sandbox"), "workspace-write")
        config = params.get("config", {})
        self.assertEqual(config.get("sandbox_workspace_write.network_access"), True)

    def test_resume_thread_requests_network_enabled_workspace_write(self) -> None:
        client = CodexAppClient(cwd=Path("."), approval_policy="never")
        captured: dict = {}

        def _fake_request(method: str, params: dict, *, timeout_sec: float) -> dict:
            captured["method"] = method
            captured["params"] = dict(params)
            captured["timeout_sec"] = float(timeout_sec)
            return {"thread": {"id": "thr-abc"}}

        client._request = _fake_request  # type: ignore[method-assign]
        thread_id = client.resume_thread("thr-input")

        self.assertEqual(thread_id, "thr-abc")
        self.assertEqual(captured.get("method"), "thread/resume")
        params = captured.get("params", {})
        self.assertEqual(params.get("threadId"), "thr-input")
        self.assertEqual(params.get("approvalPolicy"), "never")
        self.assertEqual(params.get("sandbox"), "workspace-write")
        config = params.get("config", {})
        self.assertEqual(config.get("sandbox_workspace_write.network_access"), True)

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

    def test_run_turn_interrupt_requests_cancel(self) -> None:
        client = CodexAppClient(cwd=Path("."))
        calls: list[str] = []

        def _fake_request(method: str, params: dict, *, timeout_sec: float) -> dict:
            calls.append(method)
            if method == "turn/start":
                return {"turn": {"id": "turn-2"}}
            if method == "turn/cancel":
                return {"ok": True}
            return {}

        client._request = _fake_request  # type: ignore[method-assign]
        cancel_event = threading.Event()
        cancel_event.set()

        with self.assertRaises(CodexAppServerError) as ctx:
            client.run_turn(
                thread_id="thread-1",
                text="interrupt me",
                timeout_sec=1.0,
                cancel_event=cancel_event,
            )
        self.assertIn("interrupted by user", str(ctx.exception))
        self.assertEqual(calls[:2], ["turn/start", "turn/cancel"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
