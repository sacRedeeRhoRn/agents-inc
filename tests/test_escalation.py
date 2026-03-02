#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from agents_inc.cli.escalation_prompt import resolve_escalation_request  # noqa: E402
from agents_inc.core.escalation import (  # noqa: E402
    ESCALATION_REQUEST_FILE,
    ESCALATION_RESPONSE_FILE,
    build_escalation_response,
    load_escalation_request,
    resolve_escalation_state,
    write_escalation_response,
)


class EscalationTests(unittest.TestCase):
    def test_load_and_normalize_escalation_request(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            work_dir = Path(td)
            payload = {
                "type": "ssh_connection",
                "reason": "Need remote host credentials",
                "fields_needed": ["host", "port", "user"],
                "urgency": "blocking",
                "request_id": "req-1",
            }
            (work_dir / ESCALATION_REQUEST_FILE).write_text(
                json.dumps(payload, indent=2) + "\n",
                encoding="utf-8",
            )
            req = load_escalation_request(
                work_dir=work_dir,
                group_id="developer",
                specialist_id="ssh-remote-ops-expert",
            )
            self.assertIsInstance(req, dict)
            self.assertEqual(req["type"], "ssh_connection")
            self.assertEqual(req["request_id"], "req-1")
            self.assertEqual(req["group_id"], "developer")

    def test_write_escalation_response(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            work_dir = Path(td)
            request = {
                "request_id": "req-2",
                "type": "file_path",
            }
            response = build_escalation_response(
                request=request,
                status="RESOLVED",
                values={"data_path": "/tmp/data"},
            )
            response_path = work_dir / "ESCALATION_RESPONSE.json"
            write_escalation_response(response_path=response_path, payload=response)
            parsed = json.loads(response_path.read_text(encoding="utf-8"))
            self.assertEqual(parsed["status"], "RESOLVED")
            self.assertEqual(parsed["request_id"], "req-2")

    def test_resolve_escalation_state_requested(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            work_dir = Path(td)
            (work_dir / ESCALATION_REQUEST_FILE).write_text(
                json.dumps(
                    {
                        "request_id": "req-3",
                        "type": "file_path",
                        "reason": "need local path",
                        "fields_needed": ["path"],
                    },
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )
            state = resolve_escalation_state(
                work_dir=work_dir,
                group_id="developer",
                specialist_id="python-expert",
            )
            self.assertEqual(state.get("state"), "REQUESTED")

    def test_resolve_escalation_state_invalid_request_id(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            work_dir = Path(td)
            (work_dir / ESCALATION_REQUEST_FILE).write_text(
                json.dumps(
                    {
                        "request_id": "req-4",
                        "type": "permission",
                        "reason": "need approval",
                        "fields_needed": ["approval"],
                    },
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )
            (work_dir / ESCALATION_RESPONSE_FILE).write_text(
                json.dumps(
                    {
                        "request_id": "different-id",
                        "status": "RESOLVED",
                        "values": {"approval": "yes"},
                    },
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )
            state = resolve_escalation_state(
                work_dir=work_dir,
                group_id="developer",
                specialist_id="python-expert",
            )
            self.assertEqual(state.get("state"), "INVALID")

    def test_resolve_escalation_request_non_interactive_unresolved(self) -> None:
        request = {
            "request_id": "req-5",
            "type": "ssh_connection",
            "fields_needed": ["host", "user", "auth_method"],
            "group_id": "developer",
            "specialist_id": "ssh-remote-ops-expert",
        }
        response = resolve_escalation_request(request, interactive=False)
        self.assertEqual(response.get("status"), "UNRESOLVED")
        reasons = response.get("unresolved_reasons", [])
        self.assertIsInstance(reasons, list)
        self.assertTrue(any("missing required field" in str(reason) for reason in reasons))

    def test_resolve_escalation_request_ssh_resolved(self) -> None:
        request = {
            "request_id": "req-6",
            "type": "ssh_connection",
            "fields_needed": ["host", "user", "auth_method"],
            "group_id": "developer",
            "specialist_id": "ssh-remote-ops-expert",
        }
        with patch("agents_inc.cli.escalation_prompt.save_connection_profile") as save_profile:
            save_profile.return_value = Path("/tmp/profile.yaml")
            with patch(
                "agents_inc.cli.escalation_prompt._prompt",
                side_effect=["dev-profile", "example.org", "22", "deploy", "key", "~/.ssh/id_rsa"],
            ):
                response = resolve_escalation_request(request, interactive=True)
        self.assertEqual(response.get("status"), "RESOLVED")
        values = response.get("values", {})
        self.assertEqual(values.get("profile_name"), "dev-profile")
        self.assertEqual(values.get("profile_path"), "/tmp/profile.yaml")


if __name__ == "__main__":
    unittest.main(verbosity=2)
