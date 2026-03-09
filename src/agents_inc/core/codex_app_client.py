from __future__ import annotations

import json
import queue
import subprocess
import threading
import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Deque, Dict, Optional, Tuple

from agents_inc.core.util.errors import FabricError


class CodexAppServerError(FabricError):
    pass


@dataclass
class TurnResult:
    thread_id: str
    turn_id: str
    text: str


class CodexAppClient:
    def __init__(
        self,
        *,
        cwd: Path,
        env: Optional[Dict[str, str]] = None,
        approval_policy: str = "never",
        sandbox_mode: str = "workspace-write",
        network_access: bool = True,
    ) -> None:
        self.cwd = Path(cwd).expanduser().resolve()
        self.env = dict(env or {})
        self.approval_policy = approval_policy
        self.sandbox_mode = str(sandbox_mode or "").strip() or "workspace-write"
        self.network_access = bool(network_access)
        self.proc: Optional[subprocess.Popen[str]] = None
        self._next_id = 1
        self._events: "queue.Queue[Tuple[str, str]]" = queue.Queue()
        self._buffered_events: Deque[Tuple[str, str]] = deque()
        self._stderr_tail: Deque[str] = deque(maxlen=40)

    def start(self) -> None:
        if self.proc is not None:
            return
        self.proc = subprocess.Popen(
            ["codex", "app-server", "--listen", "stdio://"],
            cwd=str(self.cwd),
            env=self.env or None,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        if not self.proc.stdin or not self.proc.stdout or not self.proc.stderr:
            raise CodexAppServerError("failed to start codex app-server streams")
        self._start_reader(self.proc.stdout, "stdout")
        self._start_reader(self.proc.stderr, "stderr")
        self._request(
            "initialize",
            {
                "protocolVersion": "2",
                "clientInfo": {"name": "agents-inc", "version": "5.0.0"},
            },
            timeout_sec=0.0,
        )
        self._send_notification("initialized", {})

    def close(self) -> None:
        if self.proc is None:
            return
        self.proc.terminate()
        try:
            self.proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            self.proc.kill()
        self.proc = None

    def start_thread(self) -> str:
        result = self._request(
            "thread/start",
            self._thread_params(),
            timeout_sec=0.0,
        )
        thread = result.get("thread")
        if not isinstance(thread, dict):
            raise CodexAppServerError("thread/start response missing thread object")
        thread_id = str(thread.get("id") or "").strip()
        if not thread_id:
            raise CodexAppServerError("thread/start response missing thread id")
        return thread_id

    def resume_thread(self, thread_id: str) -> str:
        params = self._thread_params()
        params["threadId"] = str(thread_id)
        result = self._request(
            "thread/resume",
            params,
            timeout_sec=0.0,
        )
        thread = result.get("thread")
        if not isinstance(thread, dict):
            raise CodexAppServerError("thread/resume response missing thread object")
        resumed = str(thread.get("id") or "").strip()
        if not resumed:
            raise CodexAppServerError("thread/resume response missing thread id")
        return resumed

    def run_turn(
        self,
        *,
        thread_id: str,
        text: str,
        timeout_sec: float = 0.0,
        cancel_event: threading.Event | None = None,
        event_callback: Callable[[dict], None] | None = None,
    ) -> TurnResult:
        result = self._request(
            "turn/start",
            {"threadId": str(thread_id), "input": [{"type": "text", "text": str(text)}]},
            timeout_sec=0.0,
        )
        turn = result.get("turn")
        if not isinstance(turn, dict):
            raise CodexAppServerError("turn/start response missing turn object")
        turn_id = str(turn.get("id") or "").strip()
        if not turn_id:
            raise CodexAppServerError("turn/start response missing turn id")

        full_text = ""
        delta_text = ""
        task_complete_text = ""
        deadline: float | None = None
        try:
            parsed_timeout = float(timeout_sec)
        except (TypeError, ValueError):
            parsed_timeout = 0.0
        if parsed_timeout > 0:
            deadline = time.monotonic() + parsed_timeout

        while True:
            if cancel_event is not None and cancel_event.is_set():
                self._cancel_turn(thread_id=str(thread_id), turn_id=turn_id)
                raise CodexAppServerError("turn interrupted by user")
            if deadline is None:
                poll_timeout = 0.5
            else:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                poll_timeout = min(0.5, max(0.0, remaining))
            event = self._next_event(timeout_sec=poll_timeout)
            if event is None:
                continue
            kind, payload = event
            if kind == "stderr":
                self._record_stderr(payload)
                continue
            obj = self._parse_json(payload)
            if not isinstance(obj, dict):
                continue
            method = str(obj.get("method") or "")
            params = obj.get("params") if isinstance(obj.get("params"), dict) else {}

            if method == "item/agentMessage/delta":
                if str(params.get("turnId") or "") == turn_id:
                    chunk = str(params.get("delta") or "")
                    delta_text += chunk
                    if chunk and event_callback is not None:
                        try:
                            event_callback({"event": "agent_delta", "text": chunk})
                        except Exception:
                            pass
                continue

            if method == "item/completed":
                if str(params.get("turnId") or "") != turn_id:
                    continue
                item = params.get("item") if isinstance(params.get("item"), dict) else {}
                if str(item.get("type") or "") == "agentMessage":
                    full_text = str(item.get("text") or full_text)
                    if full_text and event_callback is not None:
                        try:
                            event_callback({"event": "agent_message", "text": full_text})
                        except Exception:
                            pass
                continue

            if method == "codex/event/task_complete":
                msg = params.get("msg") if isinstance(params.get("msg"), dict) else {}
                if str(msg.get("turn_id") or "") == turn_id:
                    task_complete_text = str(msg.get("last_agent_message") or task_complete_text)
                continue

            if method == "turn/completed":
                turn_payload = params.get("turn") if isinstance(params.get("turn"), dict) else {}
                completed_turn_id = str(turn_payload.get("id") or "")
                if completed_turn_id != turn_id:
                    continue
                if str(turn_payload.get("status") or "") == "failed":
                    err = turn_payload.get("error")
                    raise CodexAppServerError(f"turn failed: {err}")
                text_out = full_text or task_complete_text or delta_text
                return TurnResult(thread_id=str(thread_id), turn_id=turn_id, text=text_out.strip())

        raise CodexAppServerError(
            self._timeout_message(f"turn timed out after {parsed_timeout:.0f}s")
        )

    def _cancel_turn(self, *, thread_id: str, turn_id: str) -> None:
        try:
            self._request(
                "turn/cancel",
                {"threadId": str(thread_id), "turnId": str(turn_id)},
                timeout_sec=1.0,
            )
        except Exception:
            return

    def _thread_params(self) -> dict:
        return {
            "cwd": str(self.cwd),
            "approvalPolicy": self.approval_policy,
            "sandbox": self.sandbox_mode,
            "config": {
                "sandbox_workspace_write.network_access": bool(self.network_access),
            },
        }

    def _start_reader(self, stream: subprocess.PIPE, kind: str) -> None:  # type: ignore[type-arg]
        def _worker() -> None:
            for line in stream:
                self._events.put((kind, line.rstrip("\n")))

        threading.Thread(target=_worker, daemon=True).start()

    def _request(self, method: str, params: dict, *, timeout_sec: float) -> dict:
        req_id = self._send_request(method, params)
        return self._wait_response(req_id, timeout_sec=timeout_sec)

    def _send_request(self, method: str, params: dict) -> int:
        if self.proc is None or self.proc.stdin is None:
            raise CodexAppServerError("codex app-server is not running")
        req_id = self._next_id
        self._next_id += 1
        message = {"jsonrpc": "2.0", "id": req_id, "method": method, "params": params}
        self.proc.stdin.write(json.dumps(message) + "\n")
        self.proc.stdin.flush()
        return req_id

    def _send_notification(self, method: str, params: Optional[dict] = None) -> None:
        if self.proc is None or self.proc.stdin is None:
            raise CodexAppServerError("codex app-server is not running")
        message = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            message["params"] = params
        self.proc.stdin.write(json.dumps(message) + "\n")
        self.proc.stdin.flush()

    def _wait_response(self, req_id: int, *, timeout_sec: float) -> dict:
        deadline: float | None = None
        try:
            parsed_timeout = float(timeout_sec)
        except (TypeError, ValueError):
            parsed_timeout = 0.0
        if parsed_timeout > 0:
            deadline = time.monotonic() + parsed_timeout

        while True:
            if deadline is None:
                poll_timeout = 0.5
            else:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                poll_timeout = min(0.5, max(0.0, remaining))
            buffered_response = self._find_buffered_response(req_id)
            if buffered_response is not None:
                return buffered_response
            event = self._poll_event(timeout_sec=poll_timeout)
            if event is None:
                continue
            kind, payload = event
            if kind == "stderr":
                self._record_stderr(payload)
                continue
            obj = self._parse_json(payload)
            if not isinstance(obj, dict):
                continue
            event_id = obj.get("id")
            if event_id is None:
                self._buffered_events.append((kind, payload))
                continue
            try:
                numeric_id = int(event_id)
            except (TypeError, ValueError):
                self._buffered_events.append((kind, payload))
                continue
            if numeric_id != req_id:
                self._buffered_events.append((kind, payload))
                continue
            if isinstance(obj.get("error"), dict):
                err = obj["error"]
                message = str(err.get("message") or "unknown app-server error")
                raise CodexAppServerError(f"{message} (method request id={req_id})")
            result = obj.get("result")
            if not isinstance(result, dict):
                return {}
            return result
        raise CodexAppServerError(
            self._timeout_message(f"request id={req_id} timed out after {parsed_timeout:.0f}s")
        )

    def _next_event(self, *, timeout_sec: float) -> Optional[Tuple[str, str]]:
        if self._buffered_events:
            return self._buffered_events.popleft()
        return self._poll_event(timeout_sec=timeout_sec)

    def _poll_event(self, *, timeout_sec: float) -> Optional[Tuple[str, str]]:
        try:
            return self._events.get(timeout=timeout_sec)
        except queue.Empty:
            return None

    def _find_buffered_response(self, req_id: int) -> Optional[dict]:
        if not self._buffered_events:
            return None
        kept: Deque[Tuple[str, str]] = deque()
        response: Optional[dict] = None
        while self._buffered_events:
            kind, payload = self._buffered_events.popleft()
            if kind == "stderr":
                self._record_stderr(payload)
                continue
            obj = self._parse_json(payload)
            if not isinstance(obj, dict):
                kept.append((kind, payload))
                continue
            event_id = obj.get("id")
            try:
                numeric_id = int(event_id)
            except (TypeError, ValueError):
                kept.append((kind, payload))
                continue
            if numeric_id != req_id:
                kept.append((kind, payload))
                continue
            if isinstance(obj.get("error"), dict):
                err = obj["error"]
                message = str(err.get("message") or "unknown app-server error")
                raise CodexAppServerError(f"{message} (method request id={req_id})")
            loaded = obj.get("result")
            response = loaded if isinstance(loaded, dict) else {}
            break
        while self._buffered_events:
            kept.append(self._buffered_events.popleft())
        self._buffered_events = kept
        return response

    def _record_stderr(self, line: str) -> None:
        text = str(line or "").strip()
        if text:
            self._stderr_tail.append(text)

    def _timeout_message(self, base: str) -> str:
        if not self._stderr_tail:
            return base
        tail = " | ".join(list(self._stderr_tail)[-5:])
        return f"{base}; recent stderr: {tail}"

    @staticmethod
    def _parse_json(line: str) -> Optional[dict]:
        if not line:
            return None
        try:
            loaded = json.loads(line)
        except json.JSONDecodeError:
            return None
        if not isinstance(loaded, dict):
            return None
        return loaded
