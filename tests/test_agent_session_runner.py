#!/usr/bin/env python3
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from agents_inc.core.agent_session_runner import (  # noqa: E402
    AgentRunConfig,
    AgentSessionRunner,
    _parse_session_output,
)
from agents_inc.core.codex_app_client import TurnResult  # noqa: E402


class AgentSessionRunnerTimeoutTests(unittest.TestCase):
    def test_unlimited_timeout_uses_none(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            project_root = Path(td)
            runner = AgentSessionRunner(backend="mock")
            config = AgentRunConfig(
                project_root=project_root,
                prompt="test",
                raw_log_path=project_root / "raw.log",
                redacted_log_path=project_root / "redacted.log",
                timeout_sec=0,
            )
            with patch("subprocess.run") as run_mock:
                run_mock.return_value.returncode = 0
                with patch.object(AgentSessionRunner, "_launch_env", return_value={}):
                    runner._run_process(config=config, cmd=["echo", "ok"])
            kwargs = run_mock.call_args.kwargs
            self.assertIsNone(kwargs.get("timeout"))

    def test_finite_timeout_uses_seconds(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            project_root = Path(td)
            runner = AgentSessionRunner(backend="mock")
            config = AgentRunConfig(
                project_root=project_root,
                prompt="test",
                raw_log_path=project_root / "raw.log",
                redacted_log_path=project_root / "redacted.log",
                timeout_sec=77,
            )
            with patch("subprocess.run") as run_mock:
                run_mock.return_value.returncode = 0
                with patch.object(AgentSessionRunner, "_launch_env", return_value={}):
                    runner._run_process(config=config, cmd=["echo", "ok"])
            kwargs = run_mock.call_args.kwargs
            self.assertEqual(kwargs.get("timeout"), 77)

    def test_backend_registry_env_selection(self) -> None:
        with patch.dict("os.environ", {"AGENTS_INC_BACKEND": "mock"}, clear=False):
            runner = AgentSessionRunner()
        self.assertEqual(runner.backend, "mock")

    def test_build_codex_cmd_includes_model_and_effort(self) -> None:
        cmd = AgentSessionRunner._build_codex_cmd(
            codex_bin="codex",
            prompt="hello",
            thread_id=None,
            model="gpt-5.3-codex-spark",
            model_reasoning_effort="xhigh",
        )
        self.assertIn("--model", cmd)
        self.assertIn("gpt-5.3-codex-spark", cmd)
        self.assertIn("-c", cmd)
        self.assertIn('model_reasoning_effort="xhigh"', cmd)
        self.assertEqual(cmd[-1], "hello")

    def test_build_codex_resume_cmd_includes_model_and_effort(self) -> None:
        cmd = AgentSessionRunner._build_codex_cmd(
            codex_bin="codex",
            prompt="next turn",
            thread_id="thread-abc",
            model="gpt-5.3-codex",
            model_reasoning_effort="xhigh",
        )
        self.assertIn("resume", cmd)
        self.assertIn("--model", cmd)
        self.assertIn("gpt-5.3-codex", cmd)
        self.assertIn('model_reasoning_effort="xhigh"', cmd)
        self.assertEqual(cmd[-2], "thread-abc")
        self.assertEqual(cmd[-1], "next turn")

    def test_build_codex_cmd_disables_mcp_when_requested(self) -> None:
        cmd = AgentSessionRunner._build_codex_cmd(
            codex_bin="codex",
            prompt="hello",
            thread_id=None,
            disable_mcp=True,
        )
        self.assertIn("-c", cmd)
        self.assertIn("mcp_servers={}", cmd)

    def test_build_codex_cmd_includes_approval_sandbox_and_cd(self) -> None:
        cmd = AgentSessionRunner._build_codex_cmd(
            codex_bin="codex",
            prompt="hello",
            thread_id=None,
            approval_policy="never",
            sandbox_mode="workspace-write",
            sandbox_cd_dir=Path("/tmp/run-a"),
            sandbox_network_access=True,
        )
        self.assertIn('approval_policy="never"', cmd)
        self.assertIn("-s", cmd)
        self.assertIn("workspace-write", cmd)
        self.assertIn("sandbox_workspace_write.network_access=true", cmd)
        self.assertIn("--cd", cmd)
        self.assertIn("/tmp/run-a", cmd)

    def test_parse_session_output_fallback_reads_json_fence(self) -> None:
        raw = """
work notes without strict markers.

```json
{"status":"COMPLETE","claims":[{"claim":"x","evidence_ids":["e1"]}],"evidence_refs":[{"evidence_id":"e1","citation":"https://example.org"}]}
```
"""
        work, payload, error, parse_mode = _parse_session_output(raw)
        self.assertEqual(error, "")
        self.assertEqual(parse_mode, "fallback")
        self.assertIsInstance(payload, dict)
        self.assertEqual(payload.get("status"), "COMPLETE")
        self.assertTrue(bool(work.strip()))

    def test_parse_session_output_fallback_reads_trailing_json_object(self) -> None:
        raw = """
model response without block delimiters.
Here is final payload:
{"status":"COMPLETE","claims":[{"claim":"x","evidence_ids":["e1"]}],"evidence_refs":[{"evidence_id":"e1","citation":"https://example.org"}]}
"""
        work, payload, error, parse_mode = _parse_session_output(raw)
        self.assertEqual(error, "")
        self.assertEqual(parse_mode, "fallback")
        self.assertIsInstance(payload, dict)
        self.assertEqual(payload.get("status"), "COMPLETE")
        self.assertTrue(bool(work.strip()))

    def test_streaming_head_sessions_use_app_server_path(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            project_root = Path(td)
            events = []

            class _FakeClient:
                def __init__(
                    self,
                    *,
                    cwd: Path,
                    env: dict | None = None,
                    approval_policy: str = "never",
                    sandbox_mode: str = "workspace-write",
                    network_access: bool = True,
                ) -> None:
                    self.cwd = cwd
                    self.env = dict(env or {})
                    self.approval_policy = approval_policy
                    self.sandbox_mode = sandbox_mode
                    self.network_access = network_access

                def start(self) -> None:
                    return None

                def close(self) -> None:
                    return None

                def start_thread(self) -> str:
                    return "thread-app-1"

                def resume_thread(self, thread_id: str) -> str:
                    return thread_id

                def run_turn(
                    self,
                    *,
                    thread_id: str,
                    text: str,
                    timeout_sec: float = 0.0,
                    cancel_event=None,
                    event_callback=None,
                ) -> TurnResult:
                    if event_callback is not None:
                        event_callback({"event": "agent_delta", "text": "LIVE_NOTE: note one\n"})
                        event_callback({"event": "agent_message", "text": "LIVE_NOTE: note one\nBEGIN_WORK\n# Work\n\nok\nEND_WORK\nBEGIN_HANDOFF_JSON\n{\"status\":\"COMPLETE\"}\nEND_HANDOFF_JSON\n"})
                    return TurnResult(
                        thread_id=thread_id,
                        turn_id="turn-1",
                        text=(
                            "LIVE_NOTE: note one\n"
                            "BEGIN_WORK\n# Work\n\nok\nEND_WORK\n"
                            "BEGIN_HANDOFF_JSON\n{\"status\":\"COMPLETE\"}\nEND_HANDOFF_JSON\n"
                        ),
                    )

            runner = AgentSessionRunner(backend="mock")
            config = AgentRunConfig(
                project_root=project_root,
                prompt="test prompt",
                raw_log_path=project_root / "raw.log",
                redacted_log_path=project_root / "redacted.log",
                timeout_sec=0,
                stream_callback=events.append,
                approval_policy="never",
                sandbox_mode="workspace-write",
                sandbox_network_access=True,
            )
            with patch("shutil.which", return_value="/usr/bin/codex"):
                with patch(
                    "agents_inc.core.agent_session_runner.CodexAppClient",
                    _FakeClient,
                ):
                    result = runner._run_codex(config)

            self.assertTrue(result.success)
            self.assertEqual(result.thread_id, "thread-app-1")
            self.assertEqual(result.parsed_handoff.get("status"), "COMPLETE")
            event_names = [event.get("event") for event in events if isinstance(event, dict)]
            self.assertIn("agent_delta", event_names)
            self.assertIn("agent_message", event_names)


if __name__ == "__main__":
    unittest.main(verbosity=2)
