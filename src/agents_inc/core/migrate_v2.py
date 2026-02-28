from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Any, Dict, List, Tuple

import yaml

from agents_inc.core.fabric_lib import FabricError, load_yaml, now_iso, slugify
from agents_inc.core.group_wizard import (
    MANDATORY_ROLES,
    normalize_specialist_dependencies,
    propose_specialists,
)

SCHEMA_V2 = "2.0"


def _load_yaml(path: Path) -> dict:
    data = load_yaml(path)
    if not isinstance(data, dict):
        raise FabricError(f"invalid yaml map: {path}")
    return data


def _dump_yaml(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(value, handle, sort_keys=False)


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _infer_role(agent_id: str, focus: str) -> str:
    text = f"{agent_id} {focus}".lower()
    if "integrat" in text or "bridge" in text:
        return "integration"
    if "review" in text or "evidence" in text or "citation" in text:
        return "evidence-review"
    if "repro" in text or "quality" in text or "qa" in text or "risk" in text:
        return "repro-qa"
    return "domain-core"


def _normalize_depends(depends_on: Any) -> List[dict]:
    if not depends_on:
        return []
    out: List[dict] = []
    if isinstance(depends_on, list):
        for item in depends_on:
            if isinstance(item, dict):
                dep = {
                    "agent_id": str(item.get("agent_id") or "").strip(),
                    "required_artifacts": [
                        str(x) for x in item.get("required_artifacts", []) if str(x).strip()
                    ],
                    "validate_with": str(item.get("validate_with") or "exists"),
                    "on_missing": str(item.get("on_missing") or "request-rerun"),
                }
                if dep["agent_id"]:
                    if not dep["required_artifacts"]:
                        dep["required_artifacts"] = [
                            f"internal/{dep['agent_id']}/handoff.json",
                        ]
                    out.append(dep)
            elif isinstance(item, str) and item.strip():
                aid = item.strip()
                out.append(
                    {
                        "agent_id": aid,
                        "required_artifacts": [f"internal/{aid}/handoff.json"],
                        "validate_with": "json-parse",
                        "on_missing": "request-rerun",
                    }
                )
    return out


def _normalize_specialist(group_id: str, specialist: dict) -> dict:
    agent_id = str(specialist.get("agent_id") or "").strip() or "domain-core-specialist"
    focus = str(specialist.get("focus") or "")
    role = str(specialist.get("role") or _infer_role(agent_id, focus))
    required_refs = specialist.get("required_references")
    if not isinstance(required_refs, list) or not required_refs:
        required_refs = [f"references/{role}-core.md"]
    required_outputs = specialist.get("required_outputs")
    if not isinstance(required_outputs, list) or not required_outputs:
        required_outputs = ["work.md", "handoff.json"]
    if "work.md" not in required_outputs:
        required_outputs.append("work.md")
    if "handoff.json" not in required_outputs:
        required_outputs.append("handoff.json")

    contract = specialist.get("contract") if isinstance(specialist.get("contract"), dict) else {}
    contract.setdefault("inputs", ["objective.md", "group-context.json"])
    contract.setdefault("outputs", ["work.md", "handoff.json"])
    contract.setdefault("output_schema", "specialist-handoff-v2")

    normalized = dict(specialist)
    normalized["agent_id"] = slugify(agent_id)
    normalized["skill_name"] = str(
        specialist.get("skill_name") or f"grp-{group_id}-{slugify(role)}"
    )
    normalized["role"] = slugify(role)
    normalized["focus"] = focus or f"{normalized['role']} specialist"
    normalized["required_references"] = [str(x) for x in required_refs]
    normalized["required_outputs"] = [str(x) for x in required_outputs]
    normalized["contract"] = contract
    normalized["depends_on"] = _normalize_depends(specialist.get("depends_on"))
    execution = specialist.get("execution") if isinstance(specialist.get("execution"), dict) else {}
    execution.setdefault("remote_transport", "local")
    execution.setdefault("scheduler", "local")
    execution.setdefault("hardware", "cpu")
    execution.setdefault("requires_gpu", False)
    normalized["execution"] = execution
    return normalized


def _ensure_minimum_roles(
    group_id: str, display_name: str, domain: str, specialists: List[dict]
) -> List[dict]:
    existing_roles = {str(spec.get("role") or "") for spec in specialists}
    template_specs = propose_specialists(group_id, display_name, domain)
    by_role = {str(spec.get("role")): spec for spec in template_specs}
    out = list(specialists)
    for role in MANDATORY_ROLES:
        if role not in existing_roles and role in by_role:
            out.append(by_role[role])
    if len(out) < 4:
        for candidate in template_specs:
            agent_id = str(candidate.get("agent_id") or "")
            if all(str(s.get("agent_id")) != agent_id for s in out):
                out.append(candidate)
            if len(out) >= 4:
                break
    return out


def _repair_specialist_dependencies(specialists: List[dict]) -> List[dict]:
    specialist_ids = {
        str(spec.get("agent_id") or "").strip() for spec in specialists if isinstance(spec, dict)
    }
    specialist_ids.discard("")
    if not specialist_ids:
        return specialists

    # Keep dependency checks strict while remapping placeholder refs to real specialist IDs.
    normalize_specialist_dependencies(specialists)
    for specialist in specialists:
        if not isinstance(specialist, dict):
            continue
        cleaned: List[dict] = []
        for dep in specialist.get("depends_on", []) or []:
            if not isinstance(dep, dict):
                continue
            dep_agent = str(dep.get("agent_id") or "").strip()
            if dep_agent not in specialist_ids:
                continue
            artifacts = dep.get("required_artifacts")
            if not isinstance(artifacts, list) or not artifacts:
                artifacts = [f"internal/{dep_agent}/handoff.json"]
            cleaned.append(
                {
                    "agent_id": dep_agent,
                    "required_artifacts": [str(item) for item in artifacts if str(item).strip()],
                    "validate_with": str(dep.get("validate_with") or "json-parse"),
                    "on_missing": str(dep.get("on_missing") or "request-rerun"),
                }
            )
        specialist["depends_on"] = cleaned
    return specialists


def migrate_group_manifest(data: dict) -> dict:
    group_id = slugify(str(data.get("group_id") or "group"))
    display_name = str(data.get("display_name") or group_id.replace("-", " ").title())
    domain = slugify(str(data.get("domain") or "general-research"))

    head = data.get("head") if isinstance(data.get("head"), dict) else {}
    head.setdefault("agent_id", f"{group_id}-head")
    head.setdefault("skill_name", f"grp-{group_id}-head")
    head.setdefault("mission", f"Route and quality-gate specialist outputs for {display_name}.")
    publish_contract = (
        head.get("publish_contract") if isinstance(head.get("publish_contract"), dict) else {}
    )
    publish_contract.setdefault(
        "exposed_required", ["summary.md", "handoff.json", "INTEGRATION_NOTES.md"]
    )
    publish_contract.setdefault("visibility", "group-only")
    head["publish_contract"] = publish_contract

    raw_specialists = data.get("specialists") if isinstance(data.get("specialists"), list) else []
    specialists = [
        _normalize_specialist(group_id, s) for s in raw_specialists if isinstance(s, dict)
    ]
    specialists = _ensure_minimum_roles(group_id, display_name, domain, specialists)
    specialists = _repair_specialist_dependencies(specialists)

    out = dict(data)
    out["schema_version"] = SCHEMA_V2
    out["group_id"] = group_id
    out["display_name"] = display_name
    out["template_version"] = "2.0.0"
    out["domain"] = domain
    out["purpose"] = str(
        data.get("purpose") or f"Coordinate expert specialists for {display_name} objectives."
    )
    success = data.get("success_criteria")
    if not isinstance(success, list) or not success:
        success = [
            "All required artifacts produced",
            "Gate profile satisfied",
            "Exposed handoff consumable",
        ]
    out["success_criteria"] = [str(item) for item in success if str(item).strip()]
    out["head"] = head
    out["specialists"] = specialists
    out["required_artifacts"] = data.get("required_artifacts") or {
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
    }
    out["gate_profile"] = data.get("gate_profile") or {
        "profile_id": "standard-evidence-v2",
        "specialist_output_schema": "specialist-handoff-v2",
        "checks": {
            "web_citations_required": True,
            "repro_command_required": True,
            "consistency_required": True,
            "scope_enforced": True,
        },
    }
    gates = data.get("quality_gates") if isinstance(data.get("quality_gates"), dict) else {}
    gates.setdefault("citation_required", True)
    gates.setdefault("unresolved_claims_block", True)
    gates.setdefault("peer_check_required", True)
    gates.setdefault("consistency_required", True)
    gates.setdefault("scope_required", True)
    gates.setdefault("reproducibility_required", True)
    out["quality_gates"] = gates
    interaction = data.get("interaction") if isinstance(data.get("interaction"), dict) else {}
    interaction.setdefault("mode", "interactive-separated")
    interaction.setdefault("linked_groups", [])
    out["interaction"] = interaction
    execution_defaults = (
        data.get("execution_defaults") if isinstance(data.get("execution_defaults"), dict) else {}
    )
    execution_defaults.setdefault("remote_transport", "local")
    execution_defaults.setdefault("schedulers", ["local"])
    execution_defaults.setdefault("hardware", ["cpu"])
    out["execution_defaults"] = execution_defaults
    out["tool_profile"] = str(data.get("tool_profile") or "default")
    workdirs = (
        data.get("default_workdirs") if isinstance(data.get("default_workdirs"), list) else []
    )
    out["default_workdirs"] = [str(item) for item in workdirs if str(item).strip()] or [
        "inputs",
        "analysis",
        "outputs",
    ]
    return out


def migrate_project_manifest(data: dict) -> dict:
    out = dict(data)
    out["schema_version"] = SCHEMA_V2
    out.setdefault("visibility", {"mode": "group-only", "audit_override": True})
    out.setdefault("overlays", {})
    out["overlays"].setdefault("allow_project_overrides", True)
    out["overlays"].setdefault(
        "protected_sections",
        ["safety_policy", "citation_gate", "tool_restrictions", "routing_audit"],
    )
    return out


def _infer_skill_role(path: Path, frontmatter: dict) -> str:
    if frontmatter.get("role") in {"head", "specialist", "router"}:
        return str(frontmatter["role"])
    text = str(path).lower()
    name = str(frontmatter.get("name") or "")
    if "research-router" in name or "/research-router/" in text:
        return "router"
    if "-head" in name or "/head/" in text:
        return "head"
    return "specialist"


def migrate_skill_markdown(text: str, path: Path) -> str:
    if not text.startswith("---\n"):
        return text
    end = text.find("\n---", 4)
    if end == -1:
        return text
    frontmatter_text = text[4:end]
    if "{{" in frontmatter_text and "}}" in frontmatter_text:
        # Template placeholders are already authored for v2; skip YAML parsing.
        return text
    frontmatter = yaml.safe_load(frontmatter_text)
    if not isinstance(frontmatter, dict):
        return text
    body = text[end + 4 :].lstrip("\n")

    role = _infer_skill_role(path, frontmatter)
    frontmatter["version"] = str(frontmatter.get("version") or SCHEMA_V2)
    frontmatter["role"] = role
    frontmatter["scope"] = str(frontmatter.get("scope") or "project-scoped")
    frontmatter["inputs"] = frontmatter.get("inputs") or ["objective", "project_id", "group_id"]
    frontmatter["outputs"] = frontmatter.get("outputs") or ["summary.md", "handoff.json"]
    frontmatter["failure_modes"] = frontmatter.get("failure_modes") or [
        "missing_evidence",
        "scope_violation",
    ]
    frontmatter["autouse_triggers"] = frontmatter.get("autouse_triggers") or [
        "group objective dispatch"
    ]

    ordered: Dict[str, Any] = {}
    for key in [
        "name",
        "version",
        "role",
        "description",
        "scope",
        "inputs",
        "outputs",
        "failure_modes",
        "autouse_triggers",
        "allowed-tools",
        "metadata",
    ]:
        if key in frontmatter:
            ordered[key] = frontmatter[key]

    rendered = yaml.safe_dump(ordered, sort_keys=False).rstrip()
    return f"---\n{rendered}\n---\n\n{body}"


def _backup_path(base: Path, target: Path) -> Path:
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(target).lstrip("/"))
    return base / safe


def _update_schema_file(path: Path, schema_version: str) -> Tuple[bool, str]:
    if not path.exists():
        return False, "missing"
    data = _load_yaml(path)
    if str(data.get("schema_version") or "") == schema_version:
        return False, "already"
    data["schema_version"] = schema_version
    _dump_yaml(path, data)
    return True, "updated"


def run_migration(
    *,
    fabric_root: Path,
    project_index_path: Path,
    apply: bool,
    backup_dir: Path,
) -> dict:
    report = {
        "fabric_root": str(fabric_root),
        "project_index_path": str(project_index_path),
        "apply": bool(apply),
        "updated": [],
        "skipped": [],
        "errors": [],
        "timestamp": now_iso(),
    }

    candidates: List[Tuple[str, Path]] = []
    for base in [
        fabric_root / "catalog" / "groups",
        fabric_root / "src" / "agents_inc" / "resources" / "catalog" / "groups",
    ]:
        if base.exists():
            for path in sorted(base.glob("*.yaml")):
                candidates.append(("group_manifest", path))

    generated_root = fabric_root / "generated" / "projects"
    if generated_root.exists():
        for project_dir in sorted(generated_root.glob("*")):
            manifest = project_dir / "manifest.yaml"
            if manifest.exists():
                candidates.append(("project_manifest", manifest))
            for gpath in sorted(project_dir.glob("agent-groups/*/group.yaml")):
                candidates.append(("group_manifest", gpath))
            for skill in sorted(project_dir.glob("**/SKILL.md")):
                candidates.append(("skill_markdown", skill))

    # Include templates and bootstrap skill templates.
    for skill in sorted(
        (fabric_root / "src" / "agents_inc" / "resources" / "templates").glob(
            "**/SKILL.template.md"
        )
    ):
        candidates.append(("skill_markdown", skill))

    if project_index_path.exists():
        candidates.append(("session_index", project_index_path))

    for kind, path in candidates:
        try:
            if kind == "group_manifest":
                before = _load_yaml(path)
                after = migrate_group_manifest(before)
                changed = json.dumps(before, sort_keys=True) != json.dumps(after, sort_keys=True)
                if not changed:
                    report["skipped"].append({"path": str(path), "reason": "already_v2"})
                    continue
                if apply:
                    bpath = _backup_path(backup_dir, path)
                    bpath.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(path, bpath)
                    _dump_yaml(path, after)
                report["updated"].append({"path": str(path), "kind": kind})
                continue

            if kind == "project_manifest":
                before = _load_yaml(path)
                after = migrate_project_manifest(before)
                changed = json.dumps(before, sort_keys=True) != json.dumps(after, sort_keys=True)
                if not changed:
                    report["skipped"].append({"path": str(path), "reason": "already_v2"})
                    continue
                if apply:
                    bpath = _backup_path(backup_dir, path)
                    bpath.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(path, bpath)
                    _dump_yaml(path, after)
                report["updated"].append({"path": str(path), "kind": kind})
                continue

            if kind == "skill_markdown":
                before = _read_text(path)
                after = migrate_skill_markdown(before, path)
                if before == after:
                    report["skipped"].append(
                        {"path": str(path), "reason": "already_v2_or_non_frontmatter"}
                    )
                    continue
                if apply:
                    bpath = _backup_path(backup_dir, path)
                    bpath.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(path, bpath)
                    _write_text(path, after)
                report["updated"].append({"path": str(path), "kind": kind})
                continue

            if kind == "session_index":
                if not path.exists():
                    report["skipped"].append({"path": str(path), "reason": "missing"})
                    continue
                data = _load_yaml(path)
                if str(data.get("schema_version") or "") == SCHEMA_V2:
                    report["skipped"].append({"path": str(path), "reason": "already_v2"})
                    continue
                data["schema_version"] = SCHEMA_V2
                if apply:
                    bpath = _backup_path(backup_dir, path)
                    bpath.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(path, bpath)
                    _dump_yaml(path, data)
                report["updated"].append({"path": str(path), "kind": kind})
                continue
        except Exception as exc:  # noqa: BLE001
            report["errors"].append({"path": str(path), "kind": kind, "error": str(exc)})

    return report
