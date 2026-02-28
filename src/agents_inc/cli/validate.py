from __future__ import annotations

import argparse
from pathlib import Path
from typing import List

from agents_inc.core.fabric_lib import (
    build_dispatch_plan,
    ensure_fabric_root_initialized,
    ensure_group_shape,
    ensure_project_shape,
    ensure_tool_policy_shape,
    load_group_catalog,
    load_profiles,
    load_project_registry,
    load_yaml,
    resolve_fabric_root,
    stable_json,
    validate_skill_markdown,
)
from agents_inc.core.skill_harness import validate_skill_contract

REQUIRED_TEMPLATE_FILES = [
    "templates/group/AGENTS.template.md",
    "templates/group/handoffs.template.yaml",
    "templates/group/tools/allowlist.template.yaml",
    "templates/group/skills/head/SKILL.template.md",
    "templates/group/skills/specialist/SKILL.template.md",
    "templates/group/references/gate-checklist.template.md",
    "templates/group/references/citation-policy.template.md",
    "templates/router/research-router/SKILL.template.md",
]

REQUIRED_SCHEMA_FILES = [
    "schemas/group.schema.yaml",
    "schemas/project.schema.yaml",
    "schemas/tool_policy.schema.yaml",
    "schemas/dispatch.schema.yaml",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Strict validation for agent group fabric")
    parser.add_argument("--fabric-root", default=None, help="path to fabric root")
    parser.add_argument(
        "--all", action="store_true", help="validate catalog, templates, and all generated projects"
    )
    parser.add_argument("--project-id", default=None, help="validate a single generated project")
    return parser.parse_args()


def validate_templates_and_schemas(fabric_root: Path) -> List[str]:
    errors: List[str] = []
    for rel in REQUIRED_TEMPLATE_FILES + REQUIRED_SCHEMA_FILES:
        path = fabric_root / rel
        if not path.exists():
            errors.append(f"missing required file: {path}")
    for path in sorted((fabric_root / "templates").glob("**/*.swp")):
        errors.append(f"temporary editor file must be removed: {path}")
    for path in sorted(
        (fabric_root / "src" / "agents_inc" / "resources" / "templates").glob("**/*.swp")
    ):
        errors.append(f"temporary editor file must be removed: {path}")
    return errors


def validate_lock_dependency(fabric_root: Path) -> List[str]:
    warnings: List[str] = []
    try:
        from controller import DirectoryController  # type: ignore # noqa: F401

        return warnings
    except Exception:
        pass
    candidate = fabric_root.parent / "multi_agent_dirs" / "controller.py"
    if not candidate.exists():
        warnings.append(
            "multi_agent_dirs dependency not detected; dispatch lock plans require --locking-mode auto/off until installed"
        )
    return warnings


def validate_catalog(fabric_root: Path) -> List[str]:
    errors: List[str] = []
    groups = load_group_catalog(fabric_root)
    profiles = load_profiles(fabric_root)

    known_groups = set(groups.keys())

    for group_id, manifest in groups.items():
        errors.extend(ensure_group_shape(manifest, source=f"catalog/groups/{group_id}.yaml"))
        interaction = manifest.get("interaction", {})
        if isinstance(interaction, dict):
            linked = interaction.get("linked_groups", [])
            if isinstance(linked, list):
                for linked_group in linked:
                    if linked_group not in known_groups:
                        errors.append(
                            f"catalog/groups/{group_id}.yaml: linked group '{linked_group}' not found"
                        )

    for profile_id, profile in profiles.items():
        profile_groups = profile.get("groups")
        if not isinstance(profile_groups, list) or not profile_groups:
            errors.append(f"catalog/profiles/{profile_id}.yaml: groups must be a non-empty list")
            continue
        for group in profile_groups:
            if group not in known_groups:
                errors.append(f"catalog/profiles/{profile_id}.yaml: unknown group '{group}'")

    registry = load_project_registry(fabric_root)
    projects = registry.get("projects", {})
    if not isinstance(projects, dict):
        errors.append("catalog/project-registry.yaml: projects must be a map")
    else:
        for project_id, payload in projects.items():
            if not isinstance(payload, dict):
                errors.append(f"project-registry: projects.{project_id} must be map")
                continue
            manifest_rel = payload.get("manifest_path")
            if not manifest_rel:
                errors.append(f"project-registry: projects.{project_id}.manifest_path is required")
            else:
                if not (fabric_root / manifest_rel).exists():
                    errors.append(
                        f"project-registry: projects.{project_id}.manifest_path missing on disk ({manifest_rel})"
                    )

    return errors


def validate_project(fabric_root: Path, project_dir: Path) -> List[str]:
    errors: List[str] = []
    manifest_path = project_dir / "manifest.yaml"
    if not manifest_path.exists():
        return [f"missing project manifest: {manifest_path}"]

    manifest = load_yaml(manifest_path)
    if not isinstance(manifest, dict):
        return [f"project manifest must be map: {manifest_path}"]

    errors.extend(ensure_project_shape(manifest, source=str(manifest_path)))

    groups_map = manifest.get("groups", {})
    if not isinstance(groups_map, dict):
        return errors

    for group_id, payload in groups_map.items():
        if not isinstance(payload, dict):
            errors.append(f"{manifest_path}: groups.{group_id} must be map")
            continue

        group_manifest_rel = payload.get("manifest_path")
        if not group_manifest_rel:
            errors.append(f"{manifest_path}: groups.{group_id}.manifest_path missing")
            continue

        group_manifest_path = project_dir / group_manifest_rel
        if not group_manifest_path.exists():
            errors.append(f"missing group manifest: {group_manifest_path}")
            continue

        group_manifest = load_yaml(group_manifest_path)
        if not isinstance(group_manifest, dict):
            errors.append(f"group manifest must be map: {group_manifest_path}")
            continue

        errors.extend(ensure_group_shape(group_manifest, source=str(group_manifest_path)))

        allowlist_path = group_manifest_path.parent / "tools" / "allowlist.yaml"
        agents_md = group_manifest_path.parent / "AGENTS.md"
        handoffs_yaml = group_manifest_path.parent / "handoffs.yaml"
        if not allowlist_path.exists():
            errors.append(f"missing tool policy: {allowlist_path}")
        else:
            policy = load_yaml(allowlist_path)
            if not isinstance(policy, dict):
                errors.append(f"tool policy must be map: {allowlist_path}")
            else:
                errors.extend(ensure_tool_policy_shape(policy, source=str(allowlist_path)))

        required_group_files = [agents_md, handoffs_yaml]
        if manifest.get("visibility"):
            required_group_files.append(group_manifest_path.parent / "exposed")
            required_group_files.extend(
                [
                    group_manifest_path.parent / "exposed" / "summary.md",
                    group_manifest_path.parent / "exposed" / "handoff.json",
                    group_manifest_path.parent / "exposed" / "INTEGRATION_NOTES.md",
                ]
            )
        specialists = group_manifest.get("specialists", [])
        if isinstance(specialists, list):
            for specialist in specialists:
                if not isinstance(specialist, dict):
                    continue
                aid = specialist.get("agent_id")
                if not isinstance(aid, str) or not aid:
                    continue
                required_group_files.extend(
                    [
                        group_manifest_path.parent / "internal" / aid / "work.md",
                        group_manifest_path.parent / "internal" / aid / "handoff.json",
                    ]
                )
        for required_file in required_group_files:
            if not required_file.exists():
                errors.append(f"missing required group artifact: {required_file}")

        head_skill_dir = payload.get("head_skill_dir")
        specialist_skill_dirs = payload.get("specialist_skill_dirs", [])
        skill_dirs = payload.get("skill_dirs", [])
        if not skill_dirs:
            errors.append(f"{manifest_path}: groups.{group_id}.skill_dirs must be non-empty list")
        if head_skill_dir is not None and not isinstance(head_skill_dir, str):
            errors.append(f"{manifest_path}: groups.{group_id}.head_skill_dir must be string")
        if specialist_skill_dirs is not None and not isinstance(specialist_skill_dirs, list):
            errors.append(f"{manifest_path}: groups.{group_id}.specialist_skill_dirs must be list")
            specialist_skill_dirs = []

        for rel_skill in skill_dirs:
            skill_md = project_dir / rel_skill / "SKILL.md"
            if not skill_md.exists():
                errors.append(f"missing SKILL.md: {skill_md}")
                continue
            errors.extend(validate_skill_markdown(skill_md))
            errors.extend(validate_skill_contract(skill_md))

        try:
            first = build_dispatch_plan(
                manifest["project_id"],
                group_id,
                "validation objective",
                group_manifest,
            )
            second = build_dispatch_plan(
                manifest["project_id"],
                group_id,
                "validation objective",
                group_manifest,
            )
            if stable_json(first) != stable_json(second):
                errors.append(
                    f"dispatch plan non-deterministic for group {group_id} in {manifest_path}"
                )
        except Exception as exc:  # noqa: BLE001
            errors.append(f"dispatch plan failed for group {group_id} in {manifest_path}: {exc}")

    return errors


def main() -> int:
    args = parse_args()
    try:
        fabric_root = resolve_fabric_root(args.fabric_root)
        ensure_fabric_root_initialized(fabric_root)

        errors: List[str] = []
        errors.extend(validate_templates_and_schemas(fabric_root))
        errors.extend(validate_catalog(fabric_root))

        if args.project_id:
            project_dir = fabric_root / "generated" / "projects" / args.project_id
            errors.extend(validate_project(fabric_root, project_dir))
        elif args.all:
            project_root = fabric_root / "generated" / "projects"
            if project_root.exists():
                for project_dir in sorted(project_root.iterdir()):
                    if project_dir.is_dir():
                        errors.extend(validate_project(fabric_root, project_dir))

        if errors:
            print("validation failed:")
            for err in errors:
                print(f"- {err}")
            return 1

        lock_warnings = validate_lock_dependency(fabric_root)
        if lock_warnings:
            print("validation warnings:")
            for warning in lock_warnings:
                print(f"- {warning}")

        print("validation passed")
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
