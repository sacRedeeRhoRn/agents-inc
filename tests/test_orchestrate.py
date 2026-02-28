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
from agents_inc.core.task_intake_qa import (  # noqa: E402
    answer_questions,
    build_question_bank,
)
from agents_inc.core.transcript_capture import (  # noqa: E402
    extract_final_plan_block,
    redact_text,
)


class OrchestrateUnitTests(unittest.TestCase):
    def test_question_bank_enforces_minimum_12(self) -> None:
        questions = build_question_bank(12)
        self.assertGreaterEqual(len(questions), 12)

    def test_answers_require_evidence_or_uncertainty(self) -> None:
        questions = build_question_bank(12)
        answers = answer_questions(
            questions=questions,
            task="cobalt silicide polymorphism workflow",
            artifact_paths=[],
            web_evidence=[{"source_url": "https://example.org/ref"}],
        )
        self.assertEqual(len(answers), len(questions))
        for answer in answers:
            refs = answer.get("evidence_refs", [])
            uncertainty = bool(answer.get("uncertainty", False))
            self.assertTrue((isinstance(refs, list) and bool(refs)) or uncertainty)

    def test_redaction_masks_tokens(self) -> None:
        redacted = redact_text("Authorization: Bearer abcdefghijklmnop\napi_key=SUPERSECRET123")
        self.assertNotIn("abcdefghijklmnop", redacted)
        self.assertNotIn("SUPERSECRET123", redacted)

    def test_extract_final_plan_rejects_placeholder(self) -> None:
        text = "BEGIN_FINAL_PLAN\n...\nEND_FINAL_PLAN"
        self.assertEqual(extract_final_plan_block(text), "")

    def test_group_contract_requires_web_research_role(self) -> None:
        manifest_path = ROOT / "catalog" / "groups" / "material-scientist.yaml"
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
        manifest_path = ROOT / "catalog" / "groups" / "material-scientist.yaml"
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
