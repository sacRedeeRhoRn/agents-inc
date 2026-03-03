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

from agents_inc.core.eval_harness import score_session  # noqa: E402


class EvalHarnessTests(unittest.TestCase):
    def test_score_session_writes_eval_scores(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            project_dir = root / "project"
            turn_dir = root / "turn"
            specialist_dir = (
                project_dir / "agent-groups" / "developer" / "internal" / "python-expert"
            )
            snapshot_dir = turn_dir / "layer4" / "specialists" / "developer" / "python-expert"
            specialist_dir.mkdir(parents=True, exist_ok=True)
            snapshot_dir.mkdir(parents=True, exist_ok=True)
            turn_dir.mkdir(parents=True, exist_ok=True)

            (specialist_dir / "work.md").write_text("# work\n", encoding="utf-8")
            (specialist_dir / "handoff.json").write_text(
                json.dumps(
                    {
                        "status": "COMPLETE",
                        "claims_with_citations": [
                            {"claim": "x", "citation": "local:references/python-core.md"}
                        ],
                        "repro_steps": ["pytest -q"],
                        "execution_status": "COMPLETE",
                        "dependencies_satisfied": True,
                        "produced_artifacts": [],
                        "citations_summary": {"count": 1, "has_web_url": False},
                    },
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )
            (snapshot_dir / "work.md").write_text("# snapshot work\n", encoding="utf-8")
            (snapshot_dir / "handoff.json").write_text(
                json.dumps(
                    {
                        "status": "COMPLETE",
                        "claims_with_citations": [
                            {"claim": "snapshot-x", "citation": "local:references/python-core.md"}
                        ],
                        "repro_steps": ["pytest -q"],
                        "execution_status": "COMPLETE",
                        "dependencies_satisfied": True,
                        "produced_artifacts": [],
                        "citations_summary": {"count": 1, "has_web_url": False},
                    },
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )
            (turn_dir / "specialist-sessions.latest.json").write_text(
                json.dumps(
                    {
                        "developer": {
                            "python-expert": {
                                "visible_skills": ["developer-python-expert--proj-a"],
                                "snapshot_work_path": str(snapshot_dir / "work.md"),
                                "snapshot_handoff_path": str(snapshot_dir / "handoff.json"),
                            }
                        }
                    },
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )

            report = score_session(
                turn_dir=turn_dir,
                project_dir=project_dir,
                group_manifests={
                    "developer": {
                        "specialists": [
                            {
                                "agent_id": "python-expert",
                                "role": "domain-core",
                                "effective_skill_name": "developer-python-expert--proj-a",
                            }
                        ]
                    }
                },
            )

            self.assertIn("overall_score", report)
            self.assertEqual(report.get("source"), "turn-snapshot")
            self.assertTrue((turn_dir / "eval-scores.json").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
