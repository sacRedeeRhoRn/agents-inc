from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List

from agents_inc.cli.install_skills import cleanup_managed_skills, install_project_skills
from agents_inc.core.codex_home import (
    ensure_project_codex_home,
    ensure_skill_activation_state,
    resolve_project_skill_target,
    save_skill_activation_state,
)
from agents_inc.core.config_state import default_config_path, get_projects_root
from agents_inc.core.fabric_lib import (
    FabricError,
    find_managed_skill_dirs,
    load_project_manifest,
    slugify,
)
from agents_inc.core.session_state import default_project_index_path, find_resume_project


def _parse_groups(value: str) -> List[str]:
    out: List[str] = []
    for raw in str(value or "").split(","):
        group_id = raw.strip()
        if group_id and group_id not in out:
            out.append(group_id)
    return out


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Manage project-scoped skill activation")
    sub = parser.add_subparsers(dest="command", required=True)

    list_parser = sub.add_parser("list", help="list installed skills for one project")
    list_parser.add_argument("--project-id", required=True)
    list_parser.add_argument("--project-index", default=None)
    list_parser.add_argument("--scan-root", default=None)
    list_parser.add_argument("--config-path", default=None)
    list_parser.add_argument("--json", action="store_true")

    activate = sub.add_parser("activate", help="activate group skills for one project")
    activate.add_argument("--project-id", required=True)
    activate.add_argument("--groups", required=True, help="comma-separated group ids")
    activate.add_argument("--specialists", action="store_true", help="include specialists")
    activate.add_argument("--project-index", default=None)
    activate.add_argument("--scan-root", default=None)
    activate.add_argument("--config-path", default=None)
    activate.add_argument("--sync", dest="sync", action="store_true", default=True)
    activate.add_argument("--no-sync", dest="sync", action="store_false")

    deactivate = sub.add_parser("deactivate", help="deactivate group skills for one project")
    deactivate.add_argument("--project-id", required=True)
    deactivate.add_argument("--groups", required=True, help="comma-separated group ids")
    deactivate.add_argument("--project-index", default=None)
    deactivate.add_argument("--scan-root", default=None)
    deactivate.add_argument("--config-path", default=None)
    deactivate.add_argument("--sync", dest="sync", action="store_true", default=True)
    deactivate.add_argument("--no-sync", dest="sync", action="store_false")

    cleanup = sub.add_parser("cleanup-global", help="remove globally managed fabric skills")
    cleanup.add_argument("--target", default=str(Path.home() / ".codex" / "skills" / "local"))
    cleanup.add_argument("--project-id", default=None)
    cleanup.add_argument("--dry-run", action="store_true")
    cleanup.add_argument("--apply", action="store_true")

    return parser.parse_args()


def _resolve_project(args: argparse.Namespace) -> tuple[str, Path, Path]:
    project_id = slugify(args.project_id)
    index_path = default_project_index_path(getattr(args, "project_index", None))
    scan_root = (
        Path(args.scan_root).expanduser().resolve()
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
    return project_id, project_root, fabric_root


def _load_project_group_ids(fabric_root: Path, project_id: str) -> List[str]:
    _, manifest = load_project_manifest(fabric_root, project_id)
    selected = manifest.get("selected_groups", [])
    if not isinstance(selected, list):
        return []
    return [str(group_id) for group_id in selected if str(group_id).strip()]


def _collect_installed_skills(target: Path) -> List[dict]:
    rows: List[dict] = []
    for skill_dir in find_managed_skill_dirs(target):
        marker_path = skill_dir / ".fabric-managed.json"
        try:
            marker = json.loads(marker_path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        rows.append(
            {
                "skill_name": skill_dir.name,
                "project_id": str(marker.get("project_id") or ""),
                "group_id": str(marker.get("group_id") or ""),
                "role": str(marker.get("role") or ""),
                "source": str(marker.get("source") or ""),
            }
        )
    rows.sort(key=lambda row: (row["group_id"], row["role"], row["skill_name"]))
    return rows


def _print_list(payload: dict) -> None:
    print(f"project_id: {payload['project_id']}")
    print(f"project_root: {payload['project_root']}")
    print(f"skills_dir: {payload['skills_dir']}")
    print(f"active_head_groups: {','.join(payload['active_head_groups'])}")
    print(f"active_specialist_groups: {','.join(payload['active_specialist_groups'])}")
    print("skills:")
    if not payload["skills"]:
        print("- (none)")
        return
    for row in payload["skills"]:
        print(
            "- {0} ({1}/{2})".format(
                row["skill_name"],
                row["group_id"],
                row["role"],
            )
        )


def _run_list(args: argparse.Namespace) -> int:
    project_id, project_root, fabric_root = _resolve_project(args)
    ensure_project_codex_home(project_root, project_id=project_id)
    activation = ensure_skill_activation_state(project_root, default_head_groups=[])
    target = resolve_project_skill_target(project_root)

    payload = {
        "project_id": project_id,
        "project_root": str(project_root),
        "fabric_root": str(fabric_root),
        "skills_dir": str(target),
        "active_head_groups": activation.get("active_head_groups", []),
        "active_specialist_groups": activation.get("active_specialist_groups", []),
        "skills": _collect_installed_skills(target),
    }
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        _print_list(payload)
    return 0


def _run_activate(args: argparse.Namespace) -> int:
    project_id, project_root, fabric_root = _resolve_project(args)
    selected_groups = _load_project_group_ids(fabric_root, project_id)
    allowed = set(selected_groups)
    requested = _parse_groups(args.groups)
    unknown = [group_id for group_id in requested if group_id not in allowed]
    if unknown:
        raise FabricError("unknown group(s) for project: " + ", ".join(sorted(unknown)))

    codex_home_state = ensure_project_codex_home(project_root, project_id=project_id)
    current = ensure_skill_activation_state(project_root, default_head_groups=selected_groups)

    head_groups = [
        group_id for group_id in current.get("active_head_groups", []) if group_id in allowed
    ]
    for group_id in requested:
        if group_id not in head_groups:
            head_groups.append(group_id)

    specialist_groups = [
        group_id for group_id in current.get("active_specialist_groups", []) if group_id in allowed
    ]
    if args.specialists:
        for group_id in requested:
            if group_id not in specialist_groups:
                specialist_groups.append(group_id)

    activation = save_skill_activation_state(
        project_root,
        active_head_groups=head_groups,
        active_specialist_groups=specialist_groups,
    )

    result = install_project_skills(
        fabric_root=fabric_root,
        project_id=project_id,
        target=Path(str(codex_home_state["skills_dir"])),
        sync=bool(args.sync),
        head_groups=activation["active_head_groups"],
        specialist_groups=activation["active_specialist_groups"],
        include_specialists=bool(activation["active_specialist_groups"]),
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def _run_deactivate(args: argparse.Namespace) -> int:
    project_id, project_root, fabric_root = _resolve_project(args)
    selected_groups = _load_project_group_ids(fabric_root, project_id)
    allowed = set(selected_groups)
    requested = _parse_groups(args.groups)
    unknown = [group_id for group_id in requested if group_id not in allowed]
    if unknown:
        raise FabricError("unknown group(s) for project: " + ", ".join(sorted(unknown)))

    codex_home_state = ensure_project_codex_home(project_root, project_id=project_id)
    current = ensure_skill_activation_state(project_root, default_head_groups=selected_groups)
    requested_set = set(requested)

    head_groups = [
        group_id
        for group_id in current.get("active_head_groups", [])
        if group_id in allowed and group_id not in requested_set
    ]
    specialist_groups = [
        group_id
        for group_id in current.get("active_specialist_groups", [])
        if group_id in allowed and group_id not in requested_set
    ]
    activation = save_skill_activation_state(
        project_root,
        active_head_groups=head_groups,
        active_specialist_groups=specialist_groups,
    )

    result = install_project_skills(
        fabric_root=fabric_root,
        project_id=project_id,
        target=Path(str(codex_home_state["skills_dir"])),
        sync=bool(args.sync),
        head_groups=activation["active_head_groups"],
        specialist_groups=activation["active_specialist_groups"],
        include_specialists=bool(activation["active_specialist_groups"]),
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def _run_cleanup_global(args: argparse.Namespace) -> int:
    target = Path(args.target).expanduser().resolve()
    dry_run = bool(args.dry_run) or not bool(args.apply)
    result = cleanup_managed_skills(
        target=target,
        apply=not dry_run,
        project_id=args.project_id,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def main() -> int:
    args = parse_args()
    try:
        if args.command == "list":
            return _run_list(args)
        if args.command == "activate":
            return _run_activate(args)
        if args.command == "deactivate":
            return _run_deactivate(args)
        if args.command == "cleanup-global":
            return _run_cleanup_global(args)
        raise FabricError(f"unsupported command: {args.command}")
    except Exception as exc:  # noqa: BLE001
        print(f"error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
