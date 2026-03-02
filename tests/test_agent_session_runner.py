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

from agents_inc.core.agent_session_runner import AgentRunConfig, AgentSessionRunner  # noqa: E402


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


if __name__ == "__main__":
    unittest.main(verbosity=2)
