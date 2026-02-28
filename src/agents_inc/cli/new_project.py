from __future__ import annotations

import argparse
import copy
from pathlib import Path
from typing import List, Tuple

from agents_inc.core.fabric_lib import (
    BUNDLE_VERSION,
    DEFAULT_INSTALL_TARGET,
    FabricError,
    ROUTER_SKILL_NAME,
    TEMPLATE_VERSION,
    dump_yaml,
    ensure_fabric_root_initialized,
    ensure_unique_names,
    format_bullet,
    load_group_catalog,
    load_profiles,
    make_skill_name,
    render_template,
    resolve_fabric_root,
    select_groups,
    slugify,
    upsert_project_registry_entry,
    write_text,
)


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


def render_workdirs_block(project_id: str, group_id: str, specialists: List[dict]) -> str:
    rows = [
        "- `generated/projects/{0}/work/{1}/{2}`".format(project_id, group_id, specialist["agent_id"])
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
        rows.append(
            "  - from: \"{0}\"\n    to: \"{1}\"\n    condition: \"{2}\"".format(
                specialist["agent_id"],
                "head-controller",
                "after dependencies satisfied" if deps else "after task completion",
            )
        )
    return "\n".join(rows)


def assign_effective_skill_names(project_id: str, group: dict) -> dict:
    group_copy = copy.deepcopy(group)
    base_names = [
        make_skill_name(project_id, group_copy["group_id"], group_copy["head"]["agent_id"])
    ]
    for specialist in group_copy["specialists"]:
        base_names.append(make_skill_name(project_id, group_copy["group_id"], specialist["agent_id"]))
    unique = ensure_unique_names(base_names)

    group_copy["head"]["effective_skill_name"] = unique[0]
    for idx, specialist in enumerate(group_copy["specialists"]):
        specialist["effective_skill_name"] = unique[idx + 1]

    return group_copy


def write_group_assets(fabric_root: Path, project_id: str, project_dir: Path, group: dict) -> Tuple[str, dict]:
    group_id = group["group_id"]
    group_dir = project_dir / "agent-groups" / group_id
    group_dir.mkdir(parents=True, exist_ok=True)

    template_agents = read_template(fabric_root, "templates/group/AGENTS.template.md")
    template_handoffs = read_template(fabric_root, "templates/group/handoffs.template.yaml")
    template_allowlist = read_template(fabric_root, "templates/group/tools/allowlist.template.yaml")
    template_head_skill = read_template(fabric_root, "templates/group/skills/head/SKILL.template.md")
    template_spec_skill = read_template(fabric_root, "templates/group/skills/specialist/SKILL.template.md")
    gate_checklist = read_template(fabric_root, "templates/group/references/gate-checklist.template.md")
    citation_policy = read_template(fabric_root, "templates/group/references/citation-policy.template.md")
    wrappers_readme = read_template(fabric_root, "templates/group/tools/wrappers/README.txt")

    context = {
        "PROJECT_ID": project_id,
        "GROUP_ID": group_id,
        "DISPLAY_NAME": group["display_name"],
        "TEMPLATE_VERSION": group.get("template_version", TEMPLATE_VERSION),
        "TOOL_PROFILE": group["tool_profile"],
        "HEAD_AGENT_ID": group["head"]["agent_id"],
        "HEAD_SKILL_NAME": group["head"]["effective_skill_name"],
        "GROUP_MISSION": group["head"].get("mission", ""),
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
    for specialist in group["specialists"]:
        (group_dir / "internal" / specialist["agent_id"]).mkdir(parents=True, exist_ok=True)

    for specialist in group["specialists"]:
        for ref_rel in specialist.get("required_references", []):
            ref_path = group_dir / ref_rel
            if not ref_path.exists():
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
            "SPECIALIST_SKILL_BLOCK": specialist_skill_block,
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
                "DISPLAY_NAME": group["display_name"],
                "PROJECT_ID": project_id,
                "SPECIALIST_REFERENCE_BLOCK": format_bullet(specialist.get("required_references", [])),
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
            manifest_rel, group_paths = write_group_assets(fabric_root, project_id, project_dir, group)
            group_entries[group_id] = {
                "manifest_path": manifest_rel,
                **group_paths,
            }
            template_versions[group_id] = group.get("template_version", TEMPLATE_VERSION)

        manifest = {
            "project_id": project_id,
            "selected_groups": selected_groups,
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
