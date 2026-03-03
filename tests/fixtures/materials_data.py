"""Domain-agnostic long-run test fixtures.

These constants are test-only fixtures for cross-group orchestration and isolation checks.
They are NOT part of the framework runtime behavior.
"""

from __future__ import annotations

from typing import List, Tuple

CANONICAL_TASK = "End-to-end professional services workflow with evidence-backed delivery gates"

FULL_GROUPS: List[str] = [
    "developer",
    "quality-assurance",
    "literature-intelligence",
    "data-curation",
    "integration-delivery",
    "design-communication",
]

HANDOFF_EDGES: List[Tuple[str, str]] = [
    ("literature-intelligence", "data-curation"),
    ("literature-intelligence", "integration-delivery"),
    ("data-curation", "integration-delivery"),
    ("developer", "integration-delivery"),
    ("literature-intelligence", "quality-assurance"),
    ("integration-delivery", "quality-assurance"),
    ("integration-delivery", "design-communication"),
    ("quality-assurance", "design-communication"),
    ("quality-assurance", "developer"),
]
