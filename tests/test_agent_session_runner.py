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


if __name__ == "__main__":
    unittest.main(verbosity=2)
