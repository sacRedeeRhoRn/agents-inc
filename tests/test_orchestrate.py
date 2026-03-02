#!/usr/bin/env python3
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from agents_inc.cli import orchestrate as orchestrate_cli  # noqa: E402
from agents_inc.core.fabric_lib import ensure_group_shape  # noqa: E402
from agents_inc.core.transcript_capture import (  # noqa: E402
    extract_final_plan_block,
    redact_text,
)


class OrchestrateUnitTests(unittest.TestCase):
    def test_redaction_masks_tokens(self) -> None:
        redacted = redact_text("Authorization: Bearer abcdefghijklmnop\napi_key=SUPERSECRET123")
        self.assertNotIn("abcdefghijklmnop", redacted)
        self.assertNotIn("SUPERSECRET123", redacted)

    def test_extract_final_plan_rejects_placeholder(self) -> None:
        text = "BEGIN_FINAL_PLAN\n...\nEND_FINAL_PLAN"
        self.assertEqual(extract_final_plan_block(text), "")

    def test_group_contract_requires_web_research_role(self) -> None:
        manifest_path = ROOT / "catalog" / "groups" / "integration-delivery.yaml"
        manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
        self.assertIsInstance(manifest, dict)
        specialists = manifest.get("specialists", [])
        self.assertIsInstance(specialists, list)
        no_web = [
            specialist
            for specialist in specialists
            if isinstance(specialist, dict) and specialist.get("role") != "web-research"
        ]
        manifest["specialists"] = no_web
        errors = ensure_group_shape(manifest, source=str(manifest_path))
        self.assertTrue(any("web-research" in error for error in errors))

    def test_group_contract_requires_web_search_default_flag(self) -> None:
        manifest_path = ROOT / "catalog" / "groups" / "integration-delivery.yaml"
        manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
        self.assertIsInstance(manifest, dict)
        execution_defaults = manifest.get("execution_defaults")
        self.assertIsInstance(execution_defaults, dict)
        execution_defaults.pop("web_search_enabled", None)
        manifest["execution_defaults"] = execution_defaults
        errors = ensure_group_shape(manifest, source=str(manifest_path))
        self.assertTrue(any("execution_defaults.web_search_enabled" in error for error in errors))

    def test_orchestrate_cli_invokes_campaign(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            payload = {"run_dir": td, "coverage_percent": 100.0}
            with patch(
                "agents_inc.cli.orchestrate.run_orchestrator_campaign", return_value=payload
            ):
                with patch.object(
                    sys,
                    "argv",
                    [
                        "agents-inc orchestrate",
                        "--fabric-root",
                        str(ROOT),
                        "--project-id",
                        "proj-orch-test",
                        "--task",
                        "test task",
                    ],
                ):
                    code = orchestrate_cli.main()
        self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
