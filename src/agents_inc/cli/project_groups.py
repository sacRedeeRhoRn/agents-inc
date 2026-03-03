from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List, Optional, Tuple

from agents_inc.cli.install_skills import install_project_skills
from agents_inc.cli.new_project import assign_effective_skill_names, write_group_assets
from agents_inc.core.codex_home import (
    ensure_project_codex_home,
    ensure_skill_activation_state,
    save_skill_activation_state,
)
from agents_inc.core.config_state import default_config_path, get_projects_root
from agents_inc.core.fabric_lib import (
    FabricError,
    dump_yaml,
    load_group_catalog,
    load_project_manifest,
    slugify,
    upsert_project_registry_entry,
)
from agents_inc.core.group_wizard import (
    GroupDraft,
    build_manifest_v2,
    propose_specialists,
    run_interactive_wizard,
)
from agents_inc.core.response_policy import prune_specialist_sessions, upsert_specialist_sessions
from agents_inc.core.session_compaction import compact_session
from agents_inc.core.session_state import (
    default_project_index_path,
    find_resume_project,
    load_checkpoint,
    now_iso,
    resolve_state_project_root,
    write_checkpoint,
)


def _parse_groups(value: str) -> List[str]:
    out: List[str] = []
    for raw in str(value or "").split(","):
        group_id = slugify(raw)
        if group_id and group_id not in out:
            out.append(group_id)
    return out


def _ask(prompt: str, default: Optional[str] = None) -> str:
    suffix = "" if default is None else f" [{default}]"
    answer = input(f"{prompt}{suffix}: ").strip()
    if not answer and default is not None:
        return default
    return answer


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Manage active group set for an existing project")
    sub = parser.add_subparsers(dest="command", required=True)

    list_parser = sub.add_parser("list", help="list project-selected groups")
    list_parser.add_argument("--project-id", required=True)
    list_parser.add_argument("--fabric-root", default=None)
    list_parser.add_argument("--project-index", default=None)
    list_parser.add_argument("--scan-root", default=None)
    list_parser.add_argument("--config-path", default=None)
    list_parser.add_argument("--json", action="store_true")

    add_parser = sub.add_parser("add", help="add existing catalog groups to project")
    add_parser.add_argument("--project-id", required=True)
    add_parser.add_argument("--groups", required=True, help="comma-separated group ids")
    add_parser.add_argument("--fabric-root", default=None)
    add_parser.add_argument("--project-index", default=None)
    add_parser.add_argument("--scan-root", default=None)
    add_parser.add_argument("--config-path", default=None)
    add_parser.add_argument("--activate-heads", action="store_true")
    add_parser.add_argument("--activate-specialists", action="store_true")
    add_parser.add_argument("--json", action="store_true")

    remove_parser = sub.add_parser("remove", help="remove groups from project")
    remove_parser.add_argument("--project-id", required=True)
    remove_parser.add_argument("--groups", required=True, help="comma-separated group ids")
    remove_parser.add_argument("--fabric-root", default=None)
    remove_parser.add_argument("--project-index", default=None)
    remove_parser.add_argument("--scan-root", default=None)
    remove_parser.add_argument("--config-path", default=None)
    remove_parser.add_argument("--deactivate", action="store_true")
    remove_parser.add_argument("--json", action="store_true")

    return parser.parse_args()


def _resolve_project_context(
    args: argparse.Namespace,
    *,
    project_id: str,
) -> Tuple[Path, Path, Path, Path, dict]:
    if args.fabric_root:
        fabric_root = Path(str(args.fabric_root)).expanduser().resolve()
        project_root = resolve_state_project_root(fabric_root, project_id)
        project_dir, manifest = load_project_manifest(fabric_root, project_id)
        return fabric_root, project_root, project_dir, project_dir / "manifest.yaml", manifest

    index_path = default_project_index_path(getattr(args, "project_index", None))
    scan_root = (
        Path(str(args.scan_root)).expanduser().resolve()
        if getattr(args, "scan_root", None)
        else get_projects_root(default_config_path(getattr(args, "config_path", None)))
    )
    found = find_resume_project(
        index_path=index_path,
        project_id=project_id,
        fallback_scan_root=scan_root,
    )
    if not found:
        raise FabricError(f"could not locate project '{project_id}'")

    project_root = Path(str(found["project_root"])).expanduser().resolve()
    fabric_root = (
        Path(str(found.get("fabric_root") or (project_root / "agent_group_fabric")))
        .expanduser()
        .resolve()
    )
    project_dir, manifest = load_project_manifest(fabric_root, project_id)
    return fabric_root, project_root, project_dir, project_dir / "manifest.yaml", manifest


def _remove_tree(path: Path) -> None:
    if not path.exists() and not path.is_symlink():
        return
    if path.is_file() or path.is_symlink():
        path.unlink()
        return
    for item in sorted(path.rglob("*"), reverse=True):
        if item.is_file() or item.is_symlink():
            item.unlink()
        elif item.is_dir():
            item.rmdir()
    path.rmdir()


def _ensure_manifest_group_maps(manifest: dict) -> None:
    if not isinstance(manifest.get("groups"), dict):
        manifest["groups"] = {}
    if not isinstance(manifest.get("template_versions"), dict):
        manifest["template_versions"] = {}
    if not isinstance(manifest.get("selected_groups"), list):
        manifest["selected_groups"] = []


def _write_checkpoint_for_group_change(
    *,
    project_id: str,
    project_root: Path,
    fabric_root: Path,
    selected_groups: List[str],
    action: str,
    index_path: Path,
) -> dict:
    try:
        latest = load_checkpoint(project_root, "latest")
    except Exception:
        latest = {}

    task = str(latest.get("task") or "Project group lifecycle update")
    router_call = str(latest.get("router_call") or "")
    if not router_call and selected_groups:
        router_call = (
            f"Use $research-router for project {project_id} group {selected_groups[0]}: {task}."
        )

    payload = {
        "project_id": project_id,
        "project_root": str(project_root),
        "fabric_root": str(fabric_root),
        "task": task,
        "constraints": {
            "mode": "project-groups",
            "action": action,
        },
        "selected_groups": selected_groups,
        "primary_group": selected_groups[0] if selected_groups else "",
        "group_order_recommendation": selected_groups,
        "router_call": router_call,
        "latest_artifacts": {
            "project_manifest": str(project_root / "project-manifest.yaml"),
            "router_call": str(project_root / "router-call.txt"),
            "kickoff": str(project_root / "kickoff.md"),
        },
        "pending_actions": [
            "Use agents-inc skills activate to enable specialist skills for selected groups.",
            "Use agents-inc orchestrator-reply for strict artifact-grounded synthesis.",
        ],
        "updated_at": now_iso(),
    }
    checkpoint = write_checkpoint(
        project_root=project_root,
        payload=payload,
        project_index_path=index_path,
    )
    compact = compact_session(
        project_root=project_root, payload=payload, selected_groups=selected_groups
    )
    return {
        "checkpoint_id": checkpoint.get("checkpoint_id", ""),
        "checkpoint_path": str(checkpoint.get("checkpoint_path", "")),
        "compact_id": compact.get("compact_id", ""),
        "compact_path": str(compact.get("compact_path", "")),
    }


def _sync_skills(
    *,
    project_id: str,
    project_root: Path,
    fabric_root: Path,
    active_head_groups: List[str],
    active_specialist_groups: List[str],
) -> dict:
    codex_home_state = ensure_project_codex_home(project_root, project_id=project_id)
    return install_project_skills(
        fabric_root=fabric_root,
        project_id=project_id,
        target=Path(str(codex_home_state["skills_dir"])),
        sync=True,
        head_groups=active_head_groups,
        specialist_groups=active_specialist_groups,
        include_specialists=bool(active_specialist_groups),
    )


def _save_manifest_and_registry(
    *,
    fabric_root: Path,
    project_id: str,
    project_manifest_path: Path,
    manifest: dict,
) -> None:
    dump_yaml(project_manifest_path, manifest)
    upsert_project_registry_entry(
        fabric_root,
        project_id,
        [
            str(group_id)
            for group_id in manifest.get("selected_groups", [])
            if str(group_id).strip()
        ],
        str(project_manifest_path.relative_to(fabric_root)),
    )


def _create_group_manifest(args: argparse.Namespace, fabric_root: Path) -> str:
    if args.interactive:
        draft = run_interactive_wizard(
            _ask,
            group_id=args.group_id,
            display_name=args.display_name,
            domain=args.domain,
        )
    else:
        if not args.group_id or not args.display_name or not args.domain:
            raise FabricError(
                "non-interactive create requires --group-id, --display-name, and --domain"
            )
        group_id = slugify(args.group_id)
        display_name = str(args.display_name).strip()
        domain = slugify(args.domain)
        purpose = str(
            args.purpose or f"Coordinate expert specialists for {display_name} objectives."
        ).strip()
        success_raw = str(
            args.success_criteria
            or "All required artifacts produced, Gate profile satisfied, Exposed handoff consumable"
        )
        success_criteria = [item.strip() for item in success_raw.split(",") if item.strip()]
        specialists = propose_specialists(group_id, display_name, domain, extra_roles=[])
        draft = GroupDraft(
            group_id=group_id,
            display_name=display_name,
            domain=domain,
            purpose=purpose,
            success_criteria=success_criteria,
            specialists=specialists,
        )

    if args.purpose:
        draft.purpose = str(args.purpose).strip()
    if args.success_criteria:
        parsed = [item.strip() for item in str(args.success_criteria).split(",") if item.strip()]
        if parsed:
            draft.success_criteria = parsed

    manifest = build_manifest_v2(draft)
    group_id = manifest["group_id"]

    catalog_path = fabric_root / "catalog" / "groups" / f"{group_id}.yaml"
    if catalog_path.exists() and not args.force:
        raise FabricError(f"catalog group already exists: {catalog_path} (use --force)")
    dump_yaml(catalog_path, manifest)

    resource_path = (
        fabric_root / "src" / "agents_inc" / "resources" / "catalog" / "groups" / f"{group_id}.yaml"
    )
    if resource_path.parent.exists():
        dump_yaml(resource_path, manifest)

    return group_id


def _cmd_list(args: argparse.Namespace) -> int:
    project_id = slugify(args.project_id)
    _, project_root, _, _, manifest = _resolve_project_context(args, project_id=project_id)
    selected = [
        str(group_id) for group_id in manifest.get("selected_groups", []) if str(group_id).strip()
    ]
    payload = {
        "project_id": project_id,
        "project_root": str(project_root),
        "selected_groups": selected,
        "count": len(selected),
    }
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0

    print(f"project_id: {project_id}")
    print(f"project_root: {project_root}")
    print(f"selected_groups: {','.join(selected)}")
    print(f"count: {len(selected)}")
    return 0


def _cmd_add(args: argparse.Namespace) -> int:
    project_id = slugify(args.project_id)
    groups_to_add = _parse_groups(args.groups)
    if not groups_to_add:
        raise FabricError("--groups must include at least one group id")

    fabric_root, project_root, project_dir, manifest_path, manifest = _resolve_project_context(
        args,
        project_id=project_id,
    )
    catalog = load_group_catalog(fabric_root)
    unknown = [group_id for group_id in groups_to_add if group_id not in catalog]
    if unknown:
        raise FabricError("unknown group(s): " + ", ".join(sorted(unknown)))

    _ensure_manifest_group_maps(manifest)
    selected = [
        str(group_id) for group_id in manifest.get("selected_groups", []) if str(group_id).strip()
    ]
    selected_set = set(selected)

    added_groups: List[str] = []
    for group_id in groups_to_add:
        if group_id in selected_set:
            continue
        group = assign_effective_skill_names(project_id, catalog[group_id])
        manifest_rel, group_paths = write_group_assets(fabric_root, project_id, project_dir, group)
        manifest["groups"][group_id] = {
            "manifest_path": manifest_rel,
            **group_paths,
        }
        manifest["template_versions"][group_id] = group.get("template_version", "3.0.0")
        selected.append(group_id)
        selected_set.add(group_id)
        added_groups.append(group_id)

    manifest["selected_groups"] = selected
    _save_manifest_and_registry(
        fabric_root=fabric_root,
        project_id=project_id,
        project_manifest_path=manifest_path,
        manifest=manifest,
    )

    current = ensure_skill_activation_state(project_root, default_head_groups=selected)
    active_head_groups = [
        group_id for group_id in current.get("active_head_groups", []) if group_id in selected_set
    ]
    active_specialist_groups = [
        group_id
        for group_id in current.get("active_specialist_groups", [])
        if group_id in selected_set
    ]

    if args.activate_heads or args.activate_specialists:
        for group_id in groups_to_add:
            if group_id in selected_set and group_id not in active_head_groups:
                active_head_groups.append(group_id)

    if args.activate_specialists:
        for group_id in groups_to_add:
            if group_id in selected_set and group_id not in active_specialist_groups:
                active_specialist_groups.append(group_id)

    if not active_head_groups:
        active_head_groups = list(selected)

    activation = save_skill_activation_state(
        project_root,
        active_head_groups=active_head_groups,
        active_specialist_groups=active_specialist_groups,
    )

    upsert_specialist_sessions(
        project_root=project_root,
        project_fabric_root=fabric_root,
        project_id=project_id,
        selected_groups=selected,
    )

    install_result = _sync_skills(
        project_id=project_id,
        project_root=project_root,
        fabric_root=fabric_root,
        active_head_groups=activation["active_head_groups"],
        active_specialist_groups=activation["active_specialist_groups"],
    )

    index_path = default_project_index_path(getattr(args, "project_index", None))
    checkpoint = _write_checkpoint_for_group_change(
        project_id=project_id,
        project_root=project_root,
        fabric_root=fabric_root,
        selected_groups=selected,
        action="project-groups-add",
        index_path=index_path,
    )

    payload = {
        "project_id": project_id,
        "project_root": str(project_root),
        "added_groups": added_groups,
        "selected_groups": selected,
        "activation": activation,
        "install": {
            "target": install_result.get("target", ""),
            "router_version": install_result.get("router_version", ""),
            "installed_skill_count": len(install_result.get("installed", [])),
        },
        "checkpoint": checkpoint,
    }
    silent = bool(getattr(args, "_silent", False))
    if args.json and not silent:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0

    if not silent:
        print(f"project_id: {project_id}")
        print(f"added_groups: {','.join(added_groups) if added_groups else '(none)'}")
        print(f"selected_groups: {','.join(selected)}")
        print(f"router_version: {install_result.get('router_version', '')}")
        print(f"checkpoint_id: {checkpoint.get('checkpoint_id', '')}")
    return 0


def _cmd_create(args: argparse.Namespace) -> int:
    project_id = slugify(args.project_id)
    fabric_root, _, _, _, _ = _resolve_project_context(args, project_id=project_id)
    created_group_id = _create_group_manifest(args, fabric_root)

    add_args = argparse.Namespace(
        project_id=project_id,
        groups=created_group_id,
        fabric_root=str(fabric_root),
        project_index=args.project_index,
        scan_root=args.scan_root,
        config_path=args.config_path,
        activate_heads=bool(args.activate_heads or args.activate_specialists),
        activate_specialists=bool(args.activate_specialists),
        json=True,
        _silent=True,
    )
    _cmd_add(add_args)

    payload = {
        "project_id": project_id,
        "created_group_id": created_group_id,
        "catalog_manifest": str(fabric_root / "catalog" / "groups" / f"{created_group_id}.yaml"),
    }
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0

    print(f"project_id: {project_id}")
    print(f"created_group_id: {created_group_id}")
    print(
        "catalog_manifest: " + str(fabric_root / "catalog" / "groups" / f"{created_group_id}.yaml")
    )
    return 0


def _cmd_remove(args: argparse.Namespace) -> int:
    project_id = slugify(args.project_id)
    groups_to_remove = _parse_groups(args.groups)
    if not groups_to_remove:
        raise FabricError("--groups must include at least one group id")

    fabric_root, project_root, project_dir, manifest_path, manifest = _resolve_project_context(
        args,
        project_id=project_id,
    )
    _ensure_manifest_group_maps(manifest)

    selected = [
        str(group_id) for group_id in manifest.get("selected_groups", []) if str(group_id).strip()
    ]
    selected_set = set(selected)
    not_present = [group_id for group_id in groups_to_remove if group_id not in selected_set]
    if not_present:
        raise FabricError("group(s) not selected in project: " + ", ".join(sorted(not_present)))

    remaining = [group_id for group_id in selected if group_id not in set(groups_to_remove)]
    manifest["selected_groups"] = remaining

    groups_map = manifest.get("groups", {})
    template_versions = manifest.get("template_versions", {})
    for group_id in groups_to_remove:
        if isinstance(groups_map, dict):
            groups_map.pop(group_id, None)
        if isinstance(template_versions, dict):
            template_versions.pop(group_id, None)

        group_dir = project_dir / "agent-groups" / group_id
        _remove_tree(group_dir)

    manifest["groups"] = groups_map
    manifest["template_versions"] = template_versions
    _save_manifest_and_registry(
        fabric_root=fabric_root,
        project_id=project_id,
        project_manifest_path=manifest_path,
        manifest=manifest,
    )

    current = ensure_skill_activation_state(project_root, default_head_groups=remaining)
    remaining_set = set(remaining)
    active_head_groups = [
        group_id for group_id in current.get("active_head_groups", []) if group_id in remaining_set
    ]
    active_specialist_groups = [
        group_id
        for group_id in current.get("active_specialist_groups", [])
        if group_id in remaining_set
    ]
    if not active_head_groups:
        active_head_groups = list(remaining)

    activation = save_skill_activation_state(
        project_root,
        active_head_groups=active_head_groups,
        active_specialist_groups=active_specialist_groups,
    )

    prune_specialist_sessions(project_root, keep_groups=remaining)
    upsert_specialist_sessions(
        project_root=project_root,
        project_fabric_root=fabric_root,
        project_id=project_id,
        selected_groups=remaining,
    )

    install_result = _sync_skills(
        project_id=project_id,
        project_root=project_root,
        fabric_root=fabric_root,
        active_head_groups=activation["active_head_groups"],
        active_specialist_groups=activation["active_specialist_groups"],
    )

    index_path = default_project_index_path(getattr(args, "project_index", None))
    checkpoint = _write_checkpoint_for_group_change(
        project_id=project_id,
        project_root=project_root,
        fabric_root=fabric_root,
        selected_groups=remaining,
        action="project-groups-remove",
        index_path=index_path,
    )

    payload = {
        "project_id": project_id,
        "project_root": str(project_root),
        "removed_groups": groups_to_remove,
        "selected_groups": remaining,
        "activation": activation,
        "install": {
            "target": install_result.get("target", ""),
            "router_version": install_result.get("router_version", ""),
            "installed_skill_count": len(install_result.get("installed", [])),
        },
        "checkpoint": checkpoint,
    }
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0

    print(f"project_id: {project_id}")
    print(f"removed_groups: {','.join(groups_to_remove)}")
    print(f"selected_groups: {','.join(remaining)}")
    print(f"router_version: {install_result.get('router_version', '')}")
    print(f"checkpoint_id: {checkpoint.get('checkpoint_id', '')}")
    return 0


def main() -> int:
    args = parse_args()
    try:
        if args.command == "list":
            return _cmd_list(args)
        if args.command == "add":
            return _cmd_add(args)
        if args.command == "remove":
            return _cmd_remove(args)
        raise FabricError("usage: agents-inc project-groups <list|add|remove> ...")
    except Exception as exc:  # noqa: BLE001
        print(f"error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
