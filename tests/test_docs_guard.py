#!/usr/bin/env python3
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class DocsGuards(unittest.TestCase):
    def test_bootstrap_markdown_has_multiline_structure(self) -> None:
        path = ROOT / "docs" / "bootstrap" / "START_IN_CODEX.md"
        text = path.read_text(encoding="utf-8")
        self.assertGreaterEqual(text.count("\n"), 20)
        self.assertIn("## Mission", text)
        self.assertIn("## New Project Flow", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
