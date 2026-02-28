from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Optional

from agents_inc.core.fabric_lib import FabricError, slugify

ASK = Callable[[str, Optional[str]], str]


MANDATORY_ROLES = [
    "domain-core",
    "web-research",
    "integration",
    "evidence-review",
    "repro-qa",
]

ROLE_ORDER = [
    "domain-core",
    "web-research",
    "integration",
    "evidence-review",
    "repro-qa",
]

ROLE_NEEDS_DOMAIN_DEP = {
    "integration",
    "evidence-review",
    "repro-qa",
}


@dataclass
class GroupDraft:
    group_id: str
    display_name: str
    domain: str
    purpose: str
    success_criteria: List[str]
    specialists: List[dict]


def _role_focus(role: str, domain: str, display_name: str) -> str:
    mapping = {
        "domain-core": f"Primary domain analysis for {display_name} in {domain}",
        "web-research": f"Web evidence and experimental data gathering for {display_name}",
        "integration": f"Cross-artifact integration and consumability checks for {display_name}",
        "evidence-review": f"Claim-level evidence review and citation sufficiency for {display_name}",
        "repro-qa": f"Reproducibility and quality assurance checks for {display_name}",
    }
    return mapping.get(role, f"Specialized {role} analysis for {display_name}")


def _role_agent_id(role: str) -> str:
    if role == "domain-core":
        return "domain-core-specialist"
    return f"{role}-specialist"


def _specialist_from_role(group_id: str, display_name: str, domain: str, role: str) -> dict:
    agent_id = _role_agent_id(role)
    depends_on: List[dict] = []
    if role in ROLE_NEEDS_DOMAIN_DEP:
        depends_on.append(
            {
                "agent_id": "domain-core-specialist",
                "required_artifacts": [
                    "internal/domain-core-specialist/handoff.json",
                ],
                "validate_with": "json-parse",
                "on_missing": "request-rerun",
            }
        )
    return {
        "agent_id": agent_id,
        "skill_name": f"grp-{group_id}-{role}",
        "role": role,
        "focus": _role_focus(role, domain, display_name),
        "required_references": [f"references/{role}-core.md"],
        "required_outputs": [
            "work.md",
            "handoff.json",
        ],
        "contract": {
            "inputs": ["objective.md", "group-context.json"],
            "outputs": ["work.md", "handoff.json"],
            "output_schema": "specialist-handoff-v2",
        },
        "depends_on": depends_on,
        "execution": {
            "web_search_enabled": True,
            "remote_transport": "local",
            "scheduler": "local",
            "hardware": "cpu",
            "requires_gpu": False,
        },
    }


def _canonical_domain_agent_id(specialists: List[dict]) -> str:
    for specialist in specialists:
        if str(specialist.get("role") or "") == "domain-core":
            agent_id = str(specialist.get("agent_id") or "").strip()
            if agent_id:
                return agent_id
    for specialist in specialists:
        agent_id = str(specialist.get("agent_id") or "").strip()
        if agent_id:
            return agent_id
    return "domain-core-specialist"


def _dep_entry(agent_id: str) -> dict:
    return {
        "agent_id": agent_id,
        "required_artifacts": [f"internal/{agent_id}/handoff.json"],
        "validate_with": "json-parse",
        "on_missing": "request-rerun",
    }


def normalize_specialist_dependencies(specialists: List[dict]) -> List[dict]:
    if not specialists:
        return specialists

    known_ids = {
        str(specialist.get("agent_id") or "").strip()
        for specialist in specialists
        if isinstance(specialist, dict)
    }
    known_ids.discard("")
    domain_agent = _canonical_domain_agent_id(specialists)

    for specialist in specialists:
        if not isinstance(specialist, dict):
            continue
        role = str(specialist.get("role") or "").strip()
        self_id = str(specialist.get("agent_id") or "").strip()
        raw_deps = specialist.get("depends_on")
        normalized: List[dict] = []
        if isinstance(raw_deps, list):
            for dep in raw_deps:
                if not isinstance(dep, dict):
                    continue
                dep_agent = str(dep.get("agent_id") or "").strip()
                if dep_agent == "domain-core-specialist":
                    dep_agent = domain_agent
                if dep_agent not in known_ids:
                    if (
                        role in ROLE_NEEDS_DOMAIN_DEP
                        and domain_agent in known_ids
                        and domain_agent != self_id
                    ):
                        dep_agent = domain_agent
                    else:
                        continue
                required = dep.get("required_artifacts")
                artifacts = (
                    [str(item) for item in required if str(item).strip()]
                    if isinstance(required, list)
                    else []
                )
                if not artifacts:
                    artifacts = [f"internal/{dep_agent}/handoff.json"]
                artifacts = [
                    artifact.replace("domain-core-specialist", dep_agent) for artifact in artifacts
                ]
                normalized.append(
                    {
                        "agent_id": dep_agent,
                        "required_artifacts": artifacts,
                        "validate_with": str(dep.get("validate_with") or "json-parse"),
                        "on_missing": str(dep.get("on_missing") or "request-rerun"),
                    }
                )

        if role in ROLE_NEEDS_DOMAIN_DEP and domain_agent in known_ids and domain_agent != self_id:
            if not any(str(dep.get("agent_id") or "") == domain_agent for dep in normalized):
                normalized.append(_dep_entry(domain_agent))

        specialist["depends_on"] = normalized

    return specialists


def propose_specialists(
    group_id: str, display_name: str, domain: str, extra_roles: Optional[List[str]] = None
) -> List[dict]:
    roles = list(ROLE_ORDER)
    for role in extra_roles or []:
        key = slugify(role)
        if key not in roles:
            roles.append(key)
    specialists = [_specialist_from_role(group_id, display_name, domain, role) for role in roles]
    return normalize_specialist_dependencies(specialists)


def _validate_specialists(specialists: List[dict]) -> None:
    roles = {str(item.get("role", "")) for item in specialists}
    missing = [role for role in MANDATORY_ROLES if role not in roles]
    if missing:
        raise FabricError("missing mandatory specialist role(s): " + ", ".join(missing))
    if len(specialists) < 4:
        raise FabricError("at least 4 specialists are required")


def _format_specialists_for_prompt(specialists: List[dict]) -> str:
    lines = []
    for idx, specialist in enumerate(specialists, start=1):
        lines.append(
            "{0}. {1} ({2}) - {3}".format(
                idx,
                specialist["agent_id"],
                specialist["role"],
                specialist["focus"],
            )
        )
    return "\n".join(lines)


def _review_specialists_interactively(
    ask: ASK,
    *,
    group_id: str,
    display_name: str,
    domain: str,
    specialists: List[dict],
) -> List[dict]:
    reviewed: List[dict] = []
    for specialist in specialists:
        agent_id = str(specialist.get("agent_id") or "").strip() or "specialist"
        role = str(specialist.get("role") or "").strip() or "domain-core"
        choice = (
            ask(
                f"Specialist '{agent_id}' ({role}) action: include/edit/skip",
                "include",
            )
            .strip()
            .lower()
        )
        if choice in {"skip", "no", "n"}:
            continue
        if choice in {"edit", "e"}:
            edited_role = slugify(ask("  role", role)) or role
            base = _specialist_from_role(group_id, display_name, domain, edited_role)
            edited_agent = slugify(ask("  agent_id", agent_id)) or base["agent_id"]
            edited_focus = (
                ask("  focus", str(specialist.get("focus") or base["focus"])).strip()
                or base["focus"]
            )
            base["agent_id"] = edited_agent
            base["skill_name"] = f"grp-{group_id}-{edited_role}"
            base["focus"] = edited_focus
            reviewed.append(base)
            continue
        reviewed.append(dict(specialist))

    normalize_specialist_dependencies(reviewed)
    missing = [
        role for role in MANDATORY_ROLES if role not in {str(s.get("role") or "") for s in reviewed}
    ]
    if missing:
        auto_add = (
            ask(
                "Missing mandatory roles (" + ", ".join(missing) + "). Auto-add now? (yes/no)",
                "yes",
            )
            .strip()
            .lower()
        )
        if auto_add not in {"yes", "y"}:
            raise FabricError("cannot continue without mandatory specialist roles")
        for role in missing:
            reviewed.append(_specialist_from_role(group_id, display_name, domain, role))
        normalize_specialist_dependencies(reviewed)
    return reviewed


def run_interactive_wizard(
    ask: ASK,
    *,
    group_id: Optional[str] = None,
    display_name: Optional[str] = None,
    domain: Optional[str] = None,
) -> GroupDraft:
    draft_group_id = slugify(ask("Group id", group_id or "new-group"))
    draft_display_name = ask("Display name", display_name or "New Group").strip() or "New Group"
    draft_domain = slugify(ask("Domain", domain or "general-research"))
    purpose = ask(
        "Purpose",
        f"Coordinate expert specialists for {draft_display_name} objectives.",
    ).strip()
    success_raw = ask(
        "Success criteria (comma-separated)",
        "All required artifacts produced, Gate profile satisfied, Exposed handoff consumable",
    )
    success_criteria = [item.strip() for item in success_raw.split(",") if item.strip()]
    if not success_criteria:
        raise FabricError("success criteria cannot be empty")

    extra_roles_raw = ask(
        "Additional specialist roles (comma-separated, optional)",
        "",
    )
    extra_roles = [item.strip() for item in extra_roles_raw.split(",") if item.strip()]

    specialists = propose_specialists(
        draft_group_id,
        draft_display_name,
        draft_domain,
        extra_roles=extra_roles,
    )
    print("\nProposed specialists:")
    print(_format_specialists_for_prompt(specialists))
    specialists = _review_specialists_interactively(
        ask,
        group_id=draft_group_id,
        display_name=draft_display_name,
        domain=draft_domain,
        specialists=specialists,
    )
    specialists = normalize_specialist_dependencies(specialists)

    _validate_specialists(specialists)

    return GroupDraft(
        group_id=draft_group_id,
        display_name=draft_display_name,
        domain=draft_domain,
        purpose=purpose,
        success_criteria=success_criteria,
        specialists=specialists,
    )


def build_manifest_v2(draft: GroupDraft) -> dict:
    group_id = draft.group_id
    return {
        "schema_version": "2.0",
        "group_id": group_id,
        "display_name": draft.display_name,
        "template_version": "2.0.0",
        "domain": draft.domain,
        "purpose": draft.purpose,
        "success_criteria": draft.success_criteria,
        "head": {
            "agent_id": f"{group_id}-head",
            "skill_name": f"grp-{group_id}-head",
            "mission": f"Route and quality-gate specialist outputs for {draft.display_name}.",
            "publish_contract": {
                "exposed_required": [
                    "summary.md",
                    "handoff.json",
                    "INTEGRATION_NOTES.md",
                ],
                "visibility": "group-only",
            },
        },
        "specialists": draft.specialists,
        "required_artifacts": {
            "objective_types": {
                "default": {
                    "specialist_internal": [
                        "internal/<agent-id>/work.md",
                        "internal/<agent-id>/handoff.json",
                    ],
                    "head_exposed": [
                        "exposed/summary.md",
                        "exposed/handoff.json",
                        "exposed/INTEGRATION_NOTES.md",
                    ],
                }
            }
        },
        "gate_profile": {
            "profile_id": "standard-evidence-v2",
            "specialist_output_schema": "specialist-handoff-v2",
            "checks": {
                "web_citations_required": True,
                "repro_command_required": True,
                "consistency_required": True,
                "scope_enforced": True,
            },
        },
        "quality_gates": {
            "citation_required": True,
            "unresolved_claims_block": True,
            "peer_check_required": True,
            "consistency_required": True,
            "scope_required": True,
            "reproducibility_required": True,
        },
        "interaction": {
            "mode": "interactive-separated",
            "linked_groups": [],
        },
        "execution_defaults": {
            "web_search_enabled": True,
            "remote_transport": "local",
            "schedulers": ["local"],
            "hardware": ["cpu"],
        },
        "tool_profile": "default",
        "default_workdirs": ["inputs", "analysis", "outputs"],
    }
