#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from agents_inc.core.head_meeting import HeadMeetingConfig, run_head_meeting  # noqa: E402


def _write_group_exposed(
    project_dir: Path,
    *,
    group_id: str,
    response_status: str,
    objective_coverage: float,
) -> None:
    exposed = project_dir / "agent-groups" / group_id / "exposed"
    exposed.mkdir(parents=True, exist_ok=True)
    (exposed / "summary.md").write_text(
        f"# Summary\n\n{group_id} summary for objective response.\n",
        encoding="utf-8",
    )
    (exposed / "INTEGRATION_NOTES.md").write_text(
        f"# Integration Notes\n\n{group_id} notes.\n",
        encoding="utf-8",
    )
    (exposed / "handoff.json").write_text(
        json.dumps(
            {
                "schema_version": "3.1",
                "status": "COMPLETE",
                "response_status": response_status,
                "objective_response": f"{group_id} objective response",
                "decision_summary": f"{group_id} decision summary",
                "objective_coverage": objective_coverage,
                "recommended_actions": ["next action"],
                "claims_with_citations": [
                    {
                        "claim": f"{group_id} claim",
                        "citation": f"https://example.org/{group_id}",
                    }
                ],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


class HeadMeetingTests(unittest.TestCase):
    def test_meeting_unsatisfied_when_any_group_is_not_answered(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            project_dir = root / "generated" / "projects" / "proj-a"
            cycle_dir = root / "turn" / "cycles" / "cycle-0001"
            cycle_dir.mkdir(parents=True, exist_ok=True)

            _write_group_exposed(
                project_dir,
                group_id="developer",
                response_status="ANSWERED",
                objective_coverage=0.92,
            )
            _write_group_exposed(
                project_dir,
                group_id="quality-assurance",
                response_status="BLOCKED",
                objective_coverage=0.40,
            )

            result = run_head_meeting(
                HeadMeetingConfig(
                    project_id="proj-a",
                    cycle_id=1,
                    cycle_dir=cycle_dir,
                    project_dir=project_dir,
                    selected_groups=["developer", "quality-assurance"],
                    message="answer the objective with explicit pass/fail criteria",
                )
            )

            self.assertFalse(bool(result.get("all_satisfied")))
            matrix = result.get("matrix", {})
            self.assertIn("developer", matrix.get("unsatisfied_groups", []))
            self.assertIn("quality-assurance", matrix.get("unsatisfied_groups", []))

    def test_meeting_satisfied_when_all_groups_answered(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            project_dir = root / "generated" / "projects" / "proj-b"
            cycle_dir = root / "turn" / "cycles" / "cycle-0001"
            cycle_dir.mkdir(parents=True, exist_ok=True)

            _write_group_exposed(
                project_dir,
                group_id="developer",
                response_status="ANSWERED",
                objective_coverage=0.95,
            )
            _write_group_exposed(
                project_dir,
                group_id="integration-delivery",
                response_status="ANSWERED",
                objective_coverage=0.90,
            )

            result = run_head_meeting(
                HeadMeetingConfig(
                    project_id="proj-b",
                    cycle_id=1,
                    cycle_dir=cycle_dir,
                    project_dir=project_dir,
                    selected_groups=["developer", "integration-delivery"],
                    message="deliver objective answer",
                )
            )

            self.assertTrue(bool(result.get("all_satisfied")))
            matrix = result.get("matrix", {})
            self.assertEqual(matrix.get("unsatisfied_groups", []), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
