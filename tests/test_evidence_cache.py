#!/usr/bin/env python3
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from agents_inc.core.evidence_cache import (  # noqa: E402
    evidence_id_for_citation,
    load_evidence_cache,
    merge_evidence_refs_into_cache,
)


class EvidenceCacheTests(unittest.TestCase):
    def test_evidence_id_is_deterministic(self) -> None:
        a = evidence_id_for_citation("https://Example.org/path#fragment")
        b = evidence_id_for_citation("https://example.org/path")
        self.assertTrue(a.startswith("ev_"))
        self.assertEqual(a, b)

    def test_merge_deduplicates_and_evicts_lru(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            project_root = Path(td)
            merge_evidence_refs_into_cache(
                project_root=project_root,
                evidence_refs=[
                    {"evidence_id": "ev_a", "citation": "https://a.example.org"},
                    {"evidence_id": "ev_b", "citation": "https://b.example.org"},
                ],
                max_entries=2,
            )
            # Touch ev_b so ev_a becomes oldest.
            merge_evidence_refs_into_cache(
                project_root=project_root,
                evidence_refs=[
                    {"evidence_id": "ev_b", "citation": "https://b.example.org"},
                    {"evidence_id": "ev_c", "citation": "https://c.example.org"},
                ],
                max_entries=2,
            )
            cache = load_evidence_cache(project_root)
            entries = cache.get("entries", {})
            self.assertIn("ev_b", entries)
            self.assertIn("ev_c", entries)
            self.assertNotIn("ev_a", entries)


if __name__ == "__main__":
    unittest.main(verbosity=2)
