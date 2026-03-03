from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Sequence

from agents_inc.core.codex_app_client import CodexAppClient
from agents_inc.core.group_wizard import MANDATORY_ROLES, GroupDraft, propose_specialists
from agents_inc.core.util.errors import FabricError

WEB_RESEARCH_ROLE = "web-research"


@dataclass
class GroupGenerationOutcome:
    draft: GroupDraft
    codex_used: bool
    codex_response: str
    extra_roles: List[str]


def _extract_json_object(text: str) -> dict:
    body = str(text or "").strip()
    if not body:
        return {}
    # Prefer raw JSON responses, then fenced blocks, then first object in text.
    for candidate in (
        body,
        *re.findall(r"```json\s*(\{.*?\})\s*```", body, flags=re.DOTALL),
        *re.findall(r"(\{.*\})", body, flags=re.DOTALL),
    ):
        try:
            loaded = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(loaded, dict):
            return loaded
    return {}


def _normalize_roles(values: Sequence[str]) -> List[str]:
    out: List[str] = []
    for item in values:
        role = str(item or "").strip().lower().replace("_", "-")
        if role and role not in out:
            out.append(role)
    return out


def _suggest_extra_roles_with_codex(
    *,
    cwd: Path,
    group_id: str,
    display_name: str,
    domain: str,
    purpose: str,
    success_criteria: Sequence[str],
) -> tuple[List[str], str]:
    prompt = "\n".join(
        [
            "Design specialist roles for an agents-inc group.",
            "Return JSON only with this schema:",
            '{"extra_roles": ["role-a", "role-b"], "notes": "short"}',
            "",
            f"group_id: {group_id}",
            f"display_name: {display_name}",
            f"domain: {domain}",
            f"purpose: {purpose}",
            "success_criteria:",
            *[f"- {item}" for item in success_criteria],
            "",
            "Constraints:",
            "- Base mandatory roles are already fixed by framework.",
            "- You may suggest only additional specialist roles.",
            "- Include concise practical roles; avoid duplicates.",
            "- Do not include web-research in extra_roles unless truly needed as duplicate.",
        ]
    )
    client = CodexAppClient(cwd=cwd)
    client.start()
    try:
        thread_id = client.start_thread()
        turn = client.run_turn(thread_id=thread_id, text=prompt, timeout_sec=0.0)
    finally:
        client.close()
    payload = _extract_json_object(turn.text)
    raw_roles = payload.get("extra_roles", [])
    if not isinstance(raw_roles, list):
        raw_roles = []
    extra_roles = _normalize_roles([str(item) for item in raw_roles])
    return extra_roles, turn.text


def generate_group_draft(
    *,
    cwd: Path,
    group_id: str,
    display_name: str,
    domain: str,
    purpose: str,
    success_criteria: Sequence[str],
    use_codex: bool,
    static_extra_roles: Sequence[str] = (),
) -> GroupGenerationOutcome:
    codex_used = False
    codex_response = ""
    extra_roles = _normalize_roles([str(item) for item in static_extra_roles])
    if use_codex:
        try:
            suggested, codex_response = _suggest_extra_roles_with_codex(
                cwd=cwd,
                group_id=group_id,
                display_name=display_name,
                domain=domain,
                purpose=purpose,
                success_criteria=success_criteria,
            )
            for role in suggested:
                if role not in extra_roles and role not in MANDATORY_ROLES:
                    extra_roles.append(role)
            codex_used = True
        except Exception:  # noqa: BLE001
            codex_used = False
            codex_response = ""

    specialists = propose_specialists(
        group_id,
        display_name,
        domain,
        extra_roles=extra_roles,
    )
    roles = [str(item.get("role") or "") for item in specialists if isinstance(item, dict)]
    if WEB_RESEARCH_ROLE not in roles:
        raise FabricError("generated specialist set must include web-research role")

    draft = GroupDraft(
        group_id=group_id,
        display_name=display_name,
        domain=domain,
        purpose=purpose,
        success_criteria=[str(item).strip() for item in success_criteria if str(item).strip()],
        specialists=specialists,
    )
    return GroupGenerationOutcome(
        draft=draft,
        codex_used=codex_used,
        codex_response=codex_response,
        extra_roles=extra_roles,
    )
