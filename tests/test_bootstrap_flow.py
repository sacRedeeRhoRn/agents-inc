#!/usr/bin/env python3
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class BootstrapFlowTests(unittest.TestCase):
    def test_start_prompt_asks_new_or_resume_before_checks(self) -> None:
        path = ROOT / "docs" / "bootstrap" / "START_IN_CODEX.md"
        text = path.read_text(encoding="utf-8")

        question = "Start new project or resume existing project?"
        self.assertIn(question, text)
        self.assertIn("Do not run any checks or terminal commands before the user answers.", text)

        first_contract_idx = text.index("## First Turn Contract (Mandatory)")
        question_idx = text.index(question)
        install_idx = text.index("## Install Check")
        self.assertLess(first_contract_idx, question_idx)
        self.assertLess(question_idx, install_idx)

    def test_readme_quick_start_points_to_v2_2_1_bootstrap(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn('export AGI_VER="v2.2.1"', readme)
        self.assertIn("docs/bootstrap/START_IN_CODEX.md", readme)
        self.assertIn("## Quick Start (Codex Orchestrator, v2.2.1)", readme)
        self.assertIn("[OVERVIEW.md](./OVERVIEW.md)", readme)


if __name__ == "__main__":
    unittest.main(verbosity=2)
