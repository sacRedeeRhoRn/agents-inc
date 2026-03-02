from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from agents_inc.core.credential_store import save_connection_profile, save_keychain_secret
from agents_inc.core.escalation import build_escalation_response, write_escalation_response


def _prompt(field: str, *, default: str = "", interactive: bool = True) -> str:
    if not interactive:
        return default
    hint = f" [{default}]" if default else ""
    try:
        raw = input(f"{field}{hint}: ").strip()
    except EOFError:
        return default
    return raw or default


def _resolve_ssh(
    request: Dict[str, object],
    *,
    interactive: bool,
) -> Dict[str, object]:
    profile_name = _prompt(
        "profile_name",
        default=f"{request.get('group_id', 'group')}-{request.get('specialist_id', 'specialist')}",
        interactive=interactive,
    )
    host = _prompt("host", interactive=interactive)
    port = _prompt("port", default="22", interactive=interactive)
    user = _prompt("user", interactive=interactive)
    auth_method = _prompt("auth_method(key/password)", default="key", interactive=interactive)
    key_path = _prompt("key_path", default="~/.ssh/id_rsa", interactive=interactive)
    values = {
        "type": "ssh_connection",
        "host": host,
        "port": int(port) if str(port).isdigit() else 22,
        "user": user,
        "auth_method": auth_method,
        "key_path": key_path,
        "profile_name": profile_name,
    }
    return values


def _resolve_generic(
    request: Dict[str, object],
    *,
    interactive: bool,
) -> Dict[str, object]:
    values: Dict[str, object] = {"type": str(request.get("type") or "custom")}
    fields_needed = request.get("fields_needed")
    if isinstance(fields_needed, list):
        for field in fields_needed:
            field_name = str(field or "").strip()
            if not field_name:
                continue
            values[field_name] = _prompt(field_name, interactive=interactive)
    return values


def _required_fields(request: Dict[str, object], req_type: str) -> List[str]:
    fields: List[str] = []
    fields_needed = request.get("fields_needed")
    if isinstance(fields_needed, list):
        for field in fields_needed:
            field_name = str(field or "").strip()
            if field_name and field_name not in fields:
                fields.append(field_name)
    if req_type == "ssh_connection":
        for field_name in ["host", "user", "auth_method"]:
            if field_name not in fields:
                fields.append(field_name)
    if req_type == "api_token" and all(
        field not in fields for field in ["token", "api_token", "keychain_key"]
    ):
        fields.append("token")
    return fields


def _is_present(value: object) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list):
        return bool(value)
    if isinstance(value, dict):
        return bool(value)
    return value is not None


def _validate_resolution(
    *,
    request: Dict[str, object],
    values: Dict[str, object],
    req_type: str,
) -> List[str]:
    reasons: List[str] = []
    for field_name in _required_fields(request, req_type):
        if field_name in {"token", "api_token"}:
            if not (_is_present(values.get("token")) or _is_present(values.get("api_token"))):
                reasons.append(f"missing required field: {field_name}")
            continue
        if not _is_present(values.get(field_name)):
            reasons.append(f"missing required field: {field_name}")
    if req_type == "api_token":
        if not (
            _is_present(values.get("token"))
            or _is_present(values.get("api_token"))
            or _is_present(values.get("keychain_key"))
        ):
            reasons.append("api_token escalation requires token or keychain_key")
    return reasons


def _persist_resolved_values(
    *,
    request: Dict[str, object],
    values: Dict[str, object],
    req_type: str,
) -> List[str]:
    reasons: List[str] = []
    if req_type == "ssh_connection":
        profile_name = str(values.get("profile_name") or "").strip()
        if not profile_name:
            profile_name = (
                f"{request.get('group_id', 'group')}-{request.get('specialist_id', 'specialist')}"
            )
            values["profile_name"] = profile_name
        port_value = values.get("port")
        try:
            port = int(port_value) if port_value is not None else 22
        except Exception:
            port = 22
        profile_payload = {
            "type": "ssh_connection",
            "host": values.get("host"),
            "port": port,
            "user": values.get("user"),
            "auth_method": values.get("auth_method"),
            "key_path": values.get("key_path"),
        }
        profile_path = save_connection_profile(profile_name=profile_name, values=profile_payload)
        values["profile_path"] = str(profile_path)
    if req_type == "api_token":
        secret = str(values.get("token") or values.get("api_token") or "").strip()
        if secret:
            key = str(request.get("request_id") or "agents-inc-token")
            stored = save_keychain_secret("agents-inc", key, secret)
            if stored:
                values.pop("token", None)
                values.pop("api_token", None)
                values["keychain_key"] = key
            else:
                reasons.append("failed to store api token in keychain")
        if not str(values.get("keychain_key") or "").strip():
            reasons.append("missing keychain_key for api_token escalation")
    return reasons


def resolve_escalation_request(
    request: Dict[str, object],
    *,
    interactive: bool,
) -> Dict[str, object]:
    req_type = str(request.get("type") or "custom").strip().lower()
    if req_type == "ssh_connection":
        values = _resolve_ssh(request, interactive=interactive)
    else:
        values = _resolve_generic(request, interactive=interactive)
    unresolved_reasons = _validate_resolution(request=request, values=values, req_type=req_type)
    if not unresolved_reasons:
        unresolved_reasons.extend(
            _persist_resolved_values(request=request, values=values, req_type=req_type)
        )
    status = "RESOLVED" if not unresolved_reasons else "UNRESOLVED"
    return build_escalation_response(
        request=request,
        status=status,
        values=values,
        unresolved_reasons=unresolved_reasons,
    )


def resolve_escalations(
    escalations: List[Dict[str, object]],
    *,
    interactive: bool,
) -> Dict[str, object]:
    resolved: List[Dict[str, object]] = []
    unresolved: List[Dict[str, object]] = []
    for request in escalations:
        response = resolve_escalation_request(request, interactive=interactive)
        response_path = Path(str(request.get("response_path") or "").strip())
        if response_path:
            write_escalation_response(response_path=response_path, payload=response)
        if str(response.get("status") or "").upper() == "RESOLVED":
            resolved.append(request)
        else:
            unresolved.append(request)
    return {
        "resolved_count": len(resolved),
        "unresolved_count": len(unresolved),
        "resolved": resolved,
        "unresolved": unresolved,
    }
