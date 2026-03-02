from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Dict, List, Optional

from agents_inc.core.util.time import now_iso

ESCALATION_REQUEST_FILE = "ESCALATION_REQUEST.json"
ESCALATION_RESPONSE_FILE = "ESCALATION_RESPONSE.json"
ESCALATION_SCHEMA_VERSION = "1.0"
ESCALATION_TYPES = {
    "ssh_connection",
    "file_path",
    "api_token",
    "permission",
    "custom",
}
ESCALATION_STATES = {"NONE", "REQUESTED", "RESOLVED", "UNRESOLVED", "INVALID"}


def _as_clean_list(value: object) -> List[str]:
    if not isinstance(value, list):
        return []
    out: List[str] = []
    for item in value:
        text = str(item or "").strip()
        if text:
            out.append(text)
    return out


def _load_json_map(path: Path) -> tuple[Dict[str, object], Optional[str]]:
    if not path.exists():
        return {}, None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return {}, f"invalid json at {path.name}: {exc}"
    if not isinstance(payload, dict):
        return {}, f"invalid payload at {path.name}: expected object"
    return payload, None


def normalize_escalation_request(
    payload: Dict[str, object],
    *,
    group_id: str,
    specialist_id: str,
    work_dir: Path,
) -> Dict[str, object]:
    req_type = str(payload.get("type") or "custom").strip().lower()
    if req_type not in ESCALATION_TYPES:
        req_type = "custom"

    request_id = str(payload.get("request_id") or "").strip() or str(uuid.uuid4())
    fields_needed = _as_clean_list(payload.get("fields_needed"))
    if not fields_needed:
        fields_needed = ["details"]

    normalized: Dict[str, object] = {
        "schema_version": ESCALATION_SCHEMA_VERSION,
        "request_id": request_id,
        "type": req_type,
        "reason": str(payload.get("reason") or "").strip() or "missing escalation reason",
        "fields_needed": fields_needed,
        "urgency": str(payload.get("urgency") or "blocking").strip().lower() or "blocking",
        "group_id": group_id,
        "specialist_id": specialist_id,
        "work_dir": str(work_dir),
        "request_path": str(work_dir / ESCALATION_REQUEST_FILE),
        "response_path": str(work_dir / ESCALATION_RESPONSE_FILE),
        "detected_at": now_iso(),
    }
    return normalized


def load_escalation_request(
    *,
    work_dir: Path,
    group_id: str,
    specialist_id: str,
) -> Optional[Dict[str, object]]:
    request_path = work_dir / ESCALATION_REQUEST_FILE
    if not request_path.exists():
        return None
    payload, _ = _load_json_map(request_path)
    return normalize_escalation_request(
        payload,
        group_id=group_id,
        specialist_id=specialist_id,
        work_dir=work_dir,
    )


def load_escalation_response(*, work_dir: Path) -> Optional[Dict[str, object]]:
    response_path = work_dir / ESCALATION_RESPONSE_FILE
    if not response_path.exists():
        return None
    payload, _ = _load_json_map(response_path)
    return payload


def resolve_escalation_state(
    *,
    work_dir: Path,
    group_id: str,
    specialist_id: str,
) -> Dict[str, object]:
    request_path = work_dir / ESCALATION_REQUEST_FILE
    response_path = work_dir / ESCALATION_RESPONSE_FILE
    reasons: List[str] = []

    if not request_path.exists():
        return {
            "state": "NONE",
            "request": None,
            "response": None,
            "reasons": reasons,
            "request_path": str(request_path),
            "response_path": str(response_path),
        }

    request_raw, request_err = _load_json_map(request_path)
    if request_err:
        reasons.append(request_err)
    request = normalize_escalation_request(
        request_raw,
        group_id=group_id,
        specialist_id=specialist_id,
        work_dir=work_dir,
    )

    if not response_path.exists():
        return {
            "state": "REQUESTED",
            "request": request,
            "response": None,
            "reasons": reasons,
            "request_path": str(request_path),
            "response_path": str(response_path),
        }

    response_raw, response_err = _load_json_map(response_path)
    if response_err:
        reasons.append(response_err)
        return {
            "state": "INVALID",
            "request": request,
            "response": None,
            "reasons": reasons,
            "request_path": str(request_path),
            "response_path": str(response_path),
        }

    if not response_raw:
        reasons.append("empty escalation response")
        return {
            "state": "INVALID",
            "request": request,
            "response": response_raw,
            "reasons": reasons,
            "request_path": str(request_path),
            "response_path": str(response_path),
        }

    response_status = str(response_raw.get("status") or "").strip().upper()
    if response_status not in {"RESOLVED", "UNRESOLVED", "REJECTED"}:
        reasons.append("invalid escalation response status")
        return {
            "state": "INVALID",
            "request": request,
            "response": response_raw,
            "reasons": reasons,
            "request_path": str(request_path),
            "response_path": str(response_path),
        }

    response_request_id = str(response_raw.get("request_id") or "").strip()
    request_id = str(request.get("request_id") or "").strip()
    if response_request_id != request_id:
        reasons.append("escalation response request_id does not match request")
        return {
            "state": "INVALID",
            "request": request,
            "response": response_raw,
            "reasons": reasons,
            "request_path": str(request_path),
            "response_path": str(response_path),
        }

    state = "RESOLVED" if response_status == "RESOLVED" else "UNRESOLVED"
    return {
        "state": state,
        "request": request,
        "response": response_raw,
        "reasons": reasons,
        "request_path": str(request_path),
        "response_path": str(response_path),
    }


def build_escalation_response(
    *,
    request: Dict[str, object],
    status: str,
    values: Dict[str, object],
    unresolved_reasons: Optional[List[str]] = None,
) -> Dict[str, object]:
    normalized_status = str(status or "").strip().upper() or "UNRESOLVED"
    if normalized_status not in {"RESOLVED", "UNRESOLVED", "REJECTED"}:
        normalized_status = "UNRESOLVED"
    payload = {
        "schema_version": ESCALATION_SCHEMA_VERSION,
        "request_id": str(request.get("request_id") or "").strip(),
        "status": normalized_status,
        "values": values,
        "updated_at": now_iso(),
    }
    reasons = _as_clean_list(unresolved_reasons)
    if reasons:
        payload["unresolved_reasons"] = reasons
    return payload


def write_escalation_response(
    *,
    response_path: Path,
    payload: Dict[str, object],
) -> None:
    response_path.parent.mkdir(parents=True, exist_ok=True)
    response_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
