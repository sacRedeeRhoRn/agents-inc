from __future__ import annotations

import argparse
import copy
from pathlib import Path
from typing import List, Tuple

from agents_inc.core.fabric_lib import (
    BUNDLE_VERSION,
    DEFAULT_INSTALL_TARGET,
    ROUTER_SKILL_NAME,
    TEMPLATE_VERSION,
    FabricError,
    dump_yaml,
    ensure_fabric_root_initialized,
    ensure_unique_names,
    format_bullet,
    load_group_catalog,
    load_profiles,
    make_skill_name,
    normalize_execution_mode,
    render_template,
    resolve_fabric_root,
    select_groups,
    slugify,
    upsert_project_registry_entry,
    write_text,
)
from agents_inc.core.persona_tools import synthesize_domain_doctrine, synthesize_expert_profile

REFERENCE_STARTER_BY_ROLE = {
    "domain-core": "domain-core.md",
    "web-research": "web-research.md",
    "evidence-review": "evidence-review.md",
    "repro-qa": "repro-qa.md",
    "integration": "integration.md",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate reusable multi-agent project bundle")
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--groups", default="", help="comma-separated group ids")
    parser.add_argument("--profile", default=None, help="profile id from catalog/profiles")
    parser.add_argument("--fabric-root", default=None, help="path to fabric root")
    parser.add_argument(
        "--target-skill-dir",
        default=DEFAULT_INSTALL_TARGET,
        help="default install target embedded in generated manifest",
    )
    parser.add_argument(
        "--visibility-mode",
        default="group-only",
        choices=["group-only", "full"],
        help="default artifact exposure mode",
    )
    parser.add_argument(
        "--execution-mode",
        default="light",
        choices=["light", "full"],
        help="project runtime execution mode",
    )
    parser.add_argument(
        "--audit-override",
        dest="audit_override",
        action="store_true",
        default=True,
        help="allow audit-time specialist artifact visibility override (default: enabled)",
    )
    parser.add_argument(
        "--no-audit-override",
        dest="audit_override",
        action="store_false",
        help="disable audit-time specialist artifact visibility override",
    )
    parser.add_argument("--force", action="store_true", help="overwrite existing project bundle")
    return parser.parse_args()


def read_template(fabric_root: Path, rel_path: str) -> str:
    return (fabric_root / rel_path).read_text(encoding="utf-8")


def render_specialist_block(specialists: List[dict]) -> str:
    rows = []
    for specialist in specialists:
        rows.append(
            "- `{0}`: {1} (skill: `{2}`)".format(
                specialist["agent_id"],
                specialist["focus"],
                specialist["effective_skill_name"],
            )
        )
    return "\n".join(rows)


def resolve_head_persona(group: dict) -> dict:
    head = group.get("head", {}) if isinstance(group, dict) else {}
    if not isinstance(head, dict):
        head = {}
    persona = head.get("persona", {})
    if not isinstance(persona, dict):
        persona = {}

    group_id = str(group.get("group_id") or "group").strip() or "group"
    display_name = str(group.get("display_name") or group_id).strip() or group_id
    domain = str(group.get("domain") or "general-domain").strip().replace("-", " ")
    doctrine_rows = synthesize_domain_doctrine(
        success_criteria=group.get("success_criteria"),
        specialists=group.get("specialists"),
        provided_doctrine=persona.get("domain_doctrine"),
    )

    return {
        "persona_id": str(persona.get("persona_id") or f"persona-{group_id}-head").strip(),
        "tone": str(persona.get("tone") or "authoritative").strip(),
        "aggression": str(persona.get("aggression") or "unrestricted-confrontation").strip(),
        "pride_statement": str(
            persona.get("pride_statement")
            or f"I represent {display_name} and defend {domain} standards with uncompromising rigor."
        ).strip(),
        "domain_doctrine": doctrine_rows[:6],
        "challenge_style": str(
            persona.get("challenge_style")
            or "Confront weak assumptions directly and demand stronger domain-grounded support."
        ).strip(),
        "visibility": str(persona.get("visibility") or "moderate").strip(),
        "confidence_threshold": float(persona.get("confidence_threshold") or 0.8),
        "override_policy": str(persona.get("override_policy") or "head-meeting-only").strip(),
    }


def render_workdirs_block(project_id: str, group_id: str, specialists: List[dict]) -> str:
    rows = [
        "- `generated/projects/{0}/work/{1}/{2}`".format(
            project_id, group_id, specialist["agent_id"]
        )
        for specialist in specialists
    ]
    return "\n".join(rows)


def render_quality_gate_block(gates: dict) -> str:
    rows = []
    for key, value in gates.items():
        rows.append("- `{0}`: `{1}`".format(key, bool(value)))
    return "\n".join(rows)


def render_deliverable_block(specialists: List[dict]) -> str:
    rows = []
    for specialist in specialists:
        for output in specialist.get("required_outputs", []):
            rows.append("- `{0}` from `{1}`".format(output, specialist["agent_id"]))
    return "\n".join(rows)


def render_handoff_block(specialists: List[dict]) -> str:
    rows = []
    for specialist in specialists:
        deps = specialist.get("depends_on", [])
        dep_names: List[str] = []
        if isinstance(deps, list):
            for dep in deps:
                if isinstance(dep, str):
                    dep_names.append(dep)
                elif isinstance(dep, dict) and dep.get("agent_id"):
                    dep_names.append(str(dep["agent_id"]))
        rows.append(
            '  - from: "{0}"\n    to: "{1}"\n    condition: "{2}"'.format(
                specialist["agent_id"],
                "head-controller",
                (
                    "after dependencies satisfied ({0})".format(", ".join(dep_names))
                    if dep_names
                    else "after task completion"
                ),
            )
        )
    return "\n".join(rows)


def render_gate_checks_block(group: dict) -> str:
    checks = group.get("gate_profile", {}).get("checks", {})
    if not isinstance(checks, dict) or not checks:
        return (
            "- `citation_required`: `true`\n- `scope_enforced`: `true`\n- `repro_required`: `true`"
        )
    rows: List[str] = []
    for key, value in checks.items():
        rows.append("- `{0}`: `{1}`".format(key, bool(value)))
    return "\n".join(rows)


def render_specialist_definition_of_done(group: dict, specialist: dict) -> str:
    rows: List[str] = []
    for output in specialist.get("required_outputs", []):
        rows.append("Produce `{0}`.".format(output))
    checks = group.get("gate_profile", {}).get("checks", {})
    if isinstance(checks, dict):
        for key, value in checks.items():
            if bool(value):
                rows.append("Pass gate check `{0}`.".format(key))
    return format_bullet(rows)


def render_specialist_method(specialist: dict) -> str:
    deps = specialist.get("depends_on", [])
    dep_names: List[str] = []
    if isinstance(deps, list):
        for dep in deps:
            if isinstance(dep, str) and dep.strip():
                dep_names.append(dep.strip())
            elif isinstance(dep, dict):
                dep_name = str(dep.get("agent_id") or "").strip()
                if dep_name:
                    dep_names.append(dep_name)
    steps = [
        "1. Parse the objective and isolate the sub-problem tied to this specialist focus.",
        "2. Load required references first; mark unknowns before claiming conclusions.",
        "3. Build claim-level outputs with explicit evidence and assumptions.",
        "4. Write required artifacts and ensure paths are reproducible by peers.",
    ]
    if dep_names:
        steps.insert(
            2,
            "3. Consume dependency artifacts from: {0}.".format(", ".join(sorted(dep_names))),
        )
        steps[3] = "4. Build claim-level outputs with explicit evidence and assumptions."
        steps[4] = "5. Write required artifacts and ensure paths are reproducible by peers."
    return "\n".join(steps)


def render_specialist_failure_modes(group: dict) -> str:
    rows = [
        "Missing citations for key claims -> return `BLOCKED_UNCITED`.",
        "Missing required evidence -> return `BLOCKED_NEEDS_EVIDENCE`.",
        "Scope creep into other specialists' responsibilities -> return `BLOCKED_REVIEW`.",
    ]
    checks = group.get("gate_profile", {}).get("checks", {})
    if isinstance(checks, dict):
        for key, value in checks.items():
            if bool(value):
                rows.append("Gate `{0}` violation -> return `BLOCKED_REVIEW`.".format(key))
    return format_bullet(rows)


def _load_reference_starter(fabric_root: Path, role: str) -> str:
    starter_name = REFERENCE_STARTER_BY_ROLE.get(str(role).strip().lower(), "domain-core.md")
    starter_path = fabric_root / "templates" / "group" / "references" / "starters" / starter_name
    if starter_path.exists():
        return starter_path.read_text(encoding="utf-8")
    fallback = fabric_root / "templates" / "group" / "references" / "starters" / "domain-core.md"
    if fallback.exists():
        return fallback.read_text(encoding="utf-8")
    return ""


def assign_effective_skill_names(project_id: str, group: dict) -> dict:
    group_copy = copy.deepcopy(group)
    base_names = [
        make_skill_name(project_id, group_copy["group_id"], group_copy["head"]["agent_id"])
    ]
    for specialist in group_copy["specialists"]:
        base_names.append(
            make_skill_name(project_id, group_copy["group_id"], specialist["agent_id"])
        )
    unique = ensure_unique_names(base_names)

    group_copy["head"]["effective_skill_name"] = unique[0]
    for idx, specialist in enumerate(group_copy["specialists"]):
        specialist["effective_skill_name"] = unique[idx + 1]

    return group_copy


def write_group_assets(
    fabric_root: Path, project_id: str, project_dir: Path, group: dict
) -> Tuple[str, dict]:
    group_id = group["group_id"]
    group_dir = project_dir / "agent-groups" / group_id
    group_dir.mkdir(parents=True, exist_ok=True)

    template_agents = read_template(fabric_root, "templates/group/AGENTS.template.md")
    template_handoffs = read_template(fabric_root, "templates/group/handoffs.template.yaml")
    template_allowlist = read_template(fabric_root, "templates/group/tools/allowlist.template.yaml")
    template_head_skill = read_template(
        fabric_root, "templates/group/skills/head/SKILL.template.md"
    )
    template_spec_skill = read_template(
        fabric_root, "templates/group/skills/specialist/SKILL.template.md"
    )
    template_specialist_agents = read_template(
        fabric_root, "templates/group/specialist-AGENTS.template.md"
    )
    gate_checklist = read_template(
        fabric_root, "templates/group/references/gate-checklist.template.md"
    )
    citation_policy = read_template(
        fabric_root, "templates/group/references/citation-policy.template.md"
    )
    wrappers_readme = read_template(fabric_root, "templates/group/tools/wrappers/README.txt")
    persona = resolve_head_persona(group)
    expert_profile = synthesize_expert_profile(
        group_id=group_id,
        display_name=group.get("display_name"),
        domain=group.get("domain"),
        purpose=group.get("purpose") or group.get("head", {}).get("mission"),
        success_criteria=group.get("success_criteria"),
        specialists=group.get("specialists"),
        gate_checks=list((group.get("gate_profile", {}).get("checks", {}) or {}).keys()),
        provided_profile=(group.get("head", {}) or {}).get("expert_profile"),
    )
    if isinstance(group.get("head"), dict):
        group["head"]["expert_profile"] = expert_profile

    context = {
        "PROJECT_ID": project_id,
        "GROUP_ID": group_id,
        "DISPLAY_NAME": group["display_name"],
        "TEMPLATE_VERSION": group.get("template_version", TEMPLATE_VERSION),
        "TOOL_PROFILE": group["tool_profile"],
        "HEAD_AGENT_ID": group["head"]["agent_id"],
        "HEAD_SKILL_NAME": group["head"]["effective_skill_name"],
        "GROUP_MISSION": group["head"].get("mission", ""),
        "HEAD_PERSONA_ID": persona["persona_id"],
        "HEAD_PERSONA_TONE": persona["tone"],
        "HEAD_PERSONA_AGGRESSION": persona["aggression"],
        "HEAD_PERSONA_PRIDE_STATEMENT": persona["pride_statement"],
        "HEAD_PERSONA_DOCTRINE_BLOCK": format_bullet(persona["domain_doctrine"]),
        "HEAD_PERSONA_CHALLENGE_STYLE": persona["challenge_style"],
        "HEAD_PERSONA_VISIBILITY": persona["visibility"],
        "HEAD_PERSONA_CONFIDENCE_THRESHOLD": "{0:.2f}".format(
            float(persona["confidence_threshold"])
        ),
        "HEAD_PERSONA_OVERRIDE_POLICY": persona["override_policy"],
        "HEAD_EXPERT_FIELD_IDENTITY": expert_profile["field_identity"],
        "HEAD_EXPERT_SIGNATURE_COMMITMENT": expert_profile["signature_commitment"],
        "HEAD_EXPERT_ANALYSIS_PROTOCOL_BLOCK": format_bullet(expert_profile["analysis_protocol"]),
        "HEAD_EXPERT_EVIDENCE_HIERARCHY_BLOCK": format_bullet(
            expert_profile["evidence_hierarchy"]
        ),
        "HEAD_EXPERT_PRESSURE_QUESTIONS_BLOCK": format_bullet(
            expert_profile["pressure_questions"]
        ),
        "HEAD_EXPERT_REFUSAL_CONDITIONS_BLOCK": format_bullet(
            expert_profile["refusal_conditions"]
        ),
        "HEAD_EXPERT_PUBLICATION_BAR_BLOCK": format_bullet(expert_profile["publication_bar"]),
        "SPECIALIST_BLOCK": render_specialist_block(group["specialists"]),
        "WORKDIR_BLOCK": render_workdirs_block(project_id, group_id, group["specialists"]),
        "QUALITY_GATE_BLOCK": render_quality_gate_block(group["quality_gates"]),
        "DELIVERABLE_BLOCK": render_deliverable_block(group["specialists"]),
    }

    write_text(group_dir / "AGENTS.md", render_template(template_agents, context))
    write_text(
        group_dir / "handoffs.yaml",
        render_template(
            template_handoffs,
            {
                "GROUP_ID": group_id,
                "HEAD_AGENT_ID": group["head"]["agent_id"],
                "HANDOFF_BLOCK": render_handoff_block(group["specialists"]),
            },
        ),
    )
    write_text(
        group_dir / "tools" / "allowlist.yaml",
        render_template(template_allowlist, {"TOOL_PROFILE": group["tool_profile"]}),
    )
    write_text(group_dir / "tools" / "wrappers" / "README.txt", wrappers_readme)
    write_text(group_dir / "references" / "gate-checklist.md", gate_checklist)
    write_text(group_dir / "references" / "citation-policy.md", citation_policy)

    # Group-scoped artifact partitioning.
    (group_dir / "exposed").mkdir(parents=True, exist_ok=True)
    write_text(group_dir / "exposed" / ".gitkeep", "")
    write_text(group_dir / "exposed" / "summary.md", "# Summary\n\nPending head publication.\n")
    write_text(
        group_dir / "exposed" / "handoff.json",
        '{\n  "schema_version": "3.0",\n  "status": "PENDING",\n  "artifacts": []\n}\n',
    )
    write_text(group_dir / "exposed" / "INTEGRATION_NOTES.md", "# Integration Notes\n\nPending.\n")
    for specialist in group["specialists"]:
        internal_dir = group_dir / "internal" / specialist["agent_id"]
        internal_dir.mkdir(parents=True, exist_ok=True)
        write_text(internal_dir / ".gitkeep", "")
        specialist_agents = render_template(
            template_specialist_agents,
            {
                "PROJECT_ID": project_id,
                "GROUP_ID": group_id,
                "DISPLAY_NAME": group["display_name"],
                "SPECIALIST_AGENT_ID": specialist["agent_id"],
                "SPECIALIST_ROLE": str(specialist.get("role") or "domain-core"),
                "SPECIALIST_FOCUS": str(specialist.get("focus") or ""),
                "SPECIALIST_SKILL_NAME": specialist["effective_skill_name"],
                "SPECIALIST_OUTPUT_BLOCK": format_bullet(specialist.get("required_outputs", [])),
                "SPECIALIST_REFERENCE_BLOCK": format_bullet(
                    specialist.get("required_references", [])
                ),
                "GATE_CHECKS_BLOCK": render_gate_checks_block(group),
            },
        )
        write_text(internal_dir / "AGENTS.md", specialist_agents)
        write_text(internal_dir / "work.md", "# Work\n\nPending specialist execution.\n")
        write_text(
            internal_dir / "handoff.json",
            '{\n  "schema_version": "4.0",\n  "status": "PENDING",\n  "claims": [],\n  "evidence_refs": [],\n  "repro_steps": [],\n  "risks": []\n}\n',
        )

    for specialist in group["specialists"]:
        for ref_rel in specialist.get("required_references", []):
            ref_path = group_dir / ref_rel
            if not ref_path.exists():
                starter_template = _load_reference_starter(
                    fabric_root,
                    str(specialist.get("role") or "domain-core"),
                )
                if starter_template:
                    write_text(
                        ref_path,
                        render_template(
                            starter_template,
                            {
                                "PROJECT_ID": project_id,
                                "GROUP_ID": group_id,
                                "DISPLAY_NAME": group["display_name"],
                                "SPECIALIST_AGENT_ID": specialist["agent_id"],
                                "SPECIALIST_ROLE": str(specialist.get("role") or "domain-core"),
                                "REFERENCE_TITLE": Path(ref_rel).stem.replace("-", " ").title(),
                            },
                        ),
                    )
                else:
                    title = Path(ref_rel).stem.replace("-", " ").title()
                    write_text(
                        ref_path,
                        "# {0}\n\nProject-specific reference placeholder for `{1}`.\n".format(
                            title,
                            specialist["agent_id"],
                        ),
                    )

    specialist_skill_block = format_bullet(
        [
            "{0}: `{1}`".format(spec["agent_id"], spec["effective_skill_name"])
            for spec in group["specialists"]
        ]
    )
    head_skill_text = render_template(
        template_head_skill,
        {
            "HEAD_SKILL_NAME": group["head"]["effective_skill_name"],
            "DISPLAY_NAME": group["display_name"],
            "GROUP_ID": group_id,
            "PROJECT_ID": project_id,
            "GROUP_PURPOSE": str(group.get("purpose") or group["head"].get("mission") or ""),
            "GROUP_SUCCESS_CRITERIA_BLOCK": format_bullet(group.get("success_criteria", [])),
            "GATE_CHECKS_BLOCK": render_gate_checks_block(group),
            "SPECIALIST_SKILL_BLOCK": specialist_skill_block,
            "HEAD_PERSONA_ID": persona["persona_id"],
            "HEAD_PERSONA_TONE": persona["tone"],
            "HEAD_PERSONA_AGGRESSION": persona["aggression"],
            "HEAD_PERSONA_PRIDE_STATEMENT": persona["pride_statement"],
            "HEAD_PERSONA_DOCTRINE_BLOCK": format_bullet(persona["domain_doctrine"]),
            "HEAD_PERSONA_CHALLENGE_STYLE": persona["challenge_style"],
            "HEAD_PERSONA_VISIBILITY": persona["visibility"],
            "HEAD_PERSONA_CONFIDENCE_THRESHOLD": "{0:.2f}".format(
                float(persona["confidence_threshold"])
            ),
            "HEAD_PERSONA_OVERRIDE_POLICY": persona["override_policy"],
            "HEAD_EXPERT_FIELD_IDENTITY": expert_profile["field_identity"],
            "HEAD_EXPERT_SIGNATURE_COMMITMENT": expert_profile["signature_commitment"],
            "HEAD_EXPERT_ANALYSIS_PROTOCOL_BLOCK": format_bullet(
                expert_profile["analysis_protocol"]
            ),
            "HEAD_EXPERT_EVIDENCE_HIERARCHY_BLOCK": format_bullet(
                expert_profile["evidence_hierarchy"]
            ),
            "HEAD_EXPERT_PRESSURE_QUESTIONS_BLOCK": format_bullet(
                expert_profile["pressure_questions"]
            ),
            "HEAD_EXPERT_REFUSAL_CONDITIONS_BLOCK": format_bullet(
                expert_profile["refusal_conditions"]
            ),
            "HEAD_EXPERT_PUBLICATION_BAR_BLOCK": format_bullet(
                expert_profile["publication_bar"]
            ),
        },
    )

    all_skill_dirs: List[str] = []
    specialist_skill_dirs: List[str] = []

    head_skill_dir = group_dir / "skills" / group["head"]["effective_skill_name"]
    write_text(head_skill_dir / "SKILL.md", head_skill_text)
    head_skill_rel = str(head_skill_dir.relative_to(project_dir))
    all_skill_dirs.append(head_skill_rel)

    for specialist in group["specialists"]:
        spec_skill_text = render_template(
            template_spec_skill,
            {
                "SPECIALIST_SKILL_NAME": specialist["effective_skill_name"],
                "SPECIALIST_AGENT_ID": specialist["agent_id"],
                "SPECIALIST_FOCUS": specialist["focus"],
                "SPECIALIST_ROLE": str(specialist.get("role") or "domain-core"),
                "DISPLAY_NAME": group["display_name"],
                "GROUP_ID": group_id,
                "PROJECT_ID": project_id,
                "GROUP_PURPOSE": str(group.get("purpose") or group["head"].get("mission") or ""),
                "GROUP_SUCCESS_CRITERIA_BLOCK": format_bullet(group.get("success_criteria", [])),
                "SPECIALIST_DONE_BLOCK": render_specialist_definition_of_done(group, specialist),
                "SPECIALIST_METHOD_BLOCK": render_specialist_method(specialist),
                "SPECIALIST_FAILURE_BLOCK": render_specialist_failure_modes(group),
                "GATE_CHECKS_BLOCK": render_gate_checks_block(group),
                "SPECIALIST_REFERENCE_BLOCK": format_bullet(
                    specialist.get("required_references", [])
                ),
                "SPECIALIST_OUTPUT_BLOCK": format_bullet(specialist.get("required_outputs", [])),
            },
        )
        spec_skill_dir = group_dir / "skills" / specialist["effective_skill_name"]
        write_text(spec_skill_dir / "SKILL.md", spec_skill_text)
        rel = str(spec_skill_dir.relative_to(project_dir))
        all_skill_dirs.append(rel)
        specialist_skill_dirs.append(rel)

    write_text(
        group_dir / "agents" / "head-controller.md",
        "# Head Controller\n\nAgent: `{0}`\nSkill: `{1}`\n".format(
            group["head"]["agent_id"], group["head"]["effective_skill_name"]
        ),
    )
    for specialist in group["specialists"]:
        write_text(
            group_dir / "agents" / "{0}.md".format(specialist["agent_id"]),
            "# Specialist\n\nAgent: `{0}`\nSkill: `{1}`\nFocus: {2}\n".format(
                specialist["agent_id"], specialist["effective_skill_name"], specialist["focus"]
            ),
        )

    group_manifest_path = group_dir / "group.yaml"
    dump_yaml(group_manifest_path, group)

    return str(group_manifest_path.relative_to(project_dir)), {
        "skill_dirs": all_skill_dirs,
        "head_skill_dir": head_skill_rel,
        "specialist_skill_dirs": specialist_skill_dirs,
    }


def main() -> int:
    args = parse_args()
    try:
        fabric_root = resolve_fabric_root(args.fabric_root)
        ensure_fabric_root_initialized(fabric_root)

        project_id = slugify(args.project_id)
        catalog = load_group_catalog(fabric_root)
        profiles = load_profiles(fabric_root)
        selected_groups = select_groups(catalog, profiles, args.groups, args.profile)

        project_dir = fabric_root / "generated" / "projects" / project_id
        if project_dir.exists() and not args.force:
            raise FabricError(f"project bundle already exists: {project_dir} (use --force)")
        if project_dir.exists() and args.force:
            for path in sorted(project_dir.rglob("*"), reverse=True):
                if path.is_file() or path.is_symlink():
                    path.unlink()
                elif path.is_dir():
                    path.rmdir()
        project_dir.mkdir(parents=True, exist_ok=True)

        group_entries = {}
        template_versions = {}

        for group_id in selected_groups:
            group = assign_effective_skill_names(project_id, catalog[group_id])
            manifest_rel, group_paths = write_group_assets(
                fabric_root, project_id, project_dir, group
            )
            group_entries[group_id] = {
                "manifest_path": manifest_rel,
                **group_paths,
            }
            template_versions[group_id] = group.get("template_version", TEMPLATE_VERSION)

        manifest = {
            "schema_version": "3.0",
            "project_id": project_id,
            "selected_groups": selected_groups,
            "runtime": {
                "execution_mode": normalize_execution_mode(args.execution_mode, default="light"),
            },
            "install_targets": {
                "codex_skill_dir": args.target_skill_dir,
            },
            "router_skill_name": ROUTER_SKILL_NAME,
            "bundle_version": BUNDLE_VERSION,
            "template_versions": template_versions,
            "visibility": {
                "mode": args.visibility_mode,
                "audit_override": bool(args.audit_override),
            },
            "overlays": {
                "allow_project_overrides": True,
                "protected_sections": [
                    "safety_policy",
                    "citation_gate",
                    "tool_restrictions",
                    "routing_audit",
                ],
            },
            "groups": group_entries,
        }

        manifest_path = project_dir / "manifest.yaml"
        dump_yaml(manifest_path, manifest)

        upsert_project_registry_entry(
            fabric_root,
            project_id,
            selected_groups,
            str(manifest_path.relative_to(fabric_root)),
        )

        print(f"generated project bundle: {project_dir}")
        print(f"manifest: {manifest_path}")
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
