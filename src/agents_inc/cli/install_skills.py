from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List, Optional

from agents_inc.core.fabric_lib import (
    FabricError,
    collect_project_skill_records,
    copy_dir,
    ensure_fabric_root_initialized,
    find_managed_skill_dirs,
    load_project_manifest,
    parse_skill_frontmatter,
    render_template,
    resolve_fabric_root,
    slugify,
    write_text,
)

STATE_FILE = ".fabric-install-state.json"
MARKER_FILE = ".fabric-managed.json"


def _parse_groups(value: str) -> List[str]:
    out: List[str] = []
    for raw in str(value or "").split(","):
        group_id = raw.strip()
        if group_id and group_id not in out:
            out.append(group_id)
    return out


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Install generated project skills into Codex skill directory"
    )
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--fabric-root", default=None, help="path to fabric root")
    parser.add_argument("--sync", action="store_true", help="remove stale skills for the project")
    parser.add_argument("--target", default=None, help="override install target")
    parser.add_argument(
        "--groups",
        default="",
        help="optional comma-separated groups to install head skills for (default: all active groups)",
    )
    parser.add_argument(
        "--specialist-groups",
        default="",
        help="optional comma-separated groups to install specialist skills for",
    )
    parser.add_argument(
        "--include-specialists",
        action="store_true",
        help="install specialist skills for selected groups",
    )
    parser.add_argument(
        "--audit",
        action="store_true",
        help="alias for --include-specialists when audit visibility is needed",
    )
    return parser.parse_args()


def _remove_tree(path: Path) -> None:
    if not path.exists() and not path.is_symlink():
        return
    if path.is_symlink() or path.is_file():
        path.unlink()
        return
    for item in sorted(path.rglob("*"), reverse=True):
        if item.is_file() or item.is_symlink():
            item.unlink()
        elif item.is_dir():
            item.rmdir()
    path.rmdir()


def load_state(path: Path) -> dict:
    if not path.exists():
        return {"projects": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def save_state(path: Path, state: dict) -> None:
    path.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")


def install_router_skill(fabric_root: Path, target: Path) -> None:
    template = (
        fabric_root / "templates" / "router" / "research-router" / "SKILL.template.md"
    ).read_text(encoding="utf-8")
    rendered = render_template(template, {"FABRIC_ROOT": str(fabric_root)})
    router_dir = target / "research-router"
    router_dir.mkdir(parents=True, exist_ok=True)
    write_text(router_dir / "SKILL.md", rendered)
    write_text(
        router_dir / "references.md",
        "# Router References\n\nThis router resolves project/group skills generated under `generated/projects`.\n",
    )


def _resolve_group_selection(
    manifest: dict,
    groups: List[str],
    *,
    default_to_all: bool,
) -> List[str]:
    active = manifest.get("selected_groups", [])
    if not isinstance(active, list):
        active = []
    active = [str(group_id) for group_id in active if str(group_id).strip()]
    if not groups:
        return active if default_to_all else []
    group_map = manifest.get("groups", {})
    if not isinstance(group_map, dict):
        raise FabricError("project manifest missing groups map")
    unknown = [group_id for group_id in groups if group_id not in group_map]
    if unknown:
        raise FabricError("unknown group(s): " + ", ".join(sorted(unknown)))
    return groups


def install_project_skills(
    *,
    fabric_root: Path,
    project_id: str,
    target: Optional[Path] = None,
    sync: bool = True,
    head_groups: Optional[List[str]] = None,
    specialist_groups: Optional[List[str]] = None,
    include_specialists: bool = False,
) -> Dict[str, object]:
    ensure_fabric_root_initialized(fabric_root)
    project_dir, manifest = load_project_manifest(fabric_root, project_id)

    manifest_target = manifest.get("install_targets", {}).get("codex_skill_dir")
    target_path = str(target) if target else str(manifest_target or "").strip()
    if not target_path:
        raise FabricError("could not resolve target skill dir (use --target)")
    target_dir = Path(target_path).expanduser().resolve()
    target_dir.mkdir(parents=True, exist_ok=True)

    selected_head_groups = _resolve_group_selection(
        manifest, head_groups or [], default_to_all=True
    )
    selected_specialist_groups = _resolve_group_selection(
        manifest, specialist_groups or [], default_to_all=False
    )
    effective_include_specialists = bool(include_specialists or selected_specialist_groups)

    visibility = manifest.get("visibility", {})
    if isinstance(visibility, dict) and visibility.get("mode") == "full":
        effective_include_specialists = True
        if not selected_specialist_groups:
            selected_specialist_groups = list(selected_head_groups)

    records = collect_project_skill_records(
        project_dir,
        manifest,
        include_specialists=effective_include_specialists,
        groups=selected_head_groups,
        specialist_groups=selected_specialist_groups,
    )
    if not records:
        raise FabricError("no skill records found for selected groups")

    installed: List[str] = []
    for record in records:
        destination = target_dir / record.skill_name
        copy_dir(record.source_dir, destination)
        marker = {
            "project_id": slugify(project_id),
            "skill_name": record.skill_name,
            "source": str(record.source_dir),
            "group_id": record.group_id,
            "role": record.role,
        }
        (destination / MARKER_FILE).write_text(
            json.dumps(marker, indent=2, sort_keys=True), encoding="utf-8"
        )
        installed.append(record.skill_name)
        parse_skill_frontmatter(destination / "SKILL.md")

    install_router_skill(fabric_root, target_dir)

    state_path = target_dir / STATE_FILE
    state = load_state(state_path)
    project_key = slugify(project_id)
    previous = set(state.setdefault("projects", {}).get(project_key, []))

    if sync:
        stale = sorted(previous - set(installed))
        for stale_skill in stale:
            stale_path = target_dir / stale_skill
            marker_path = stale_path / MARKER_FILE
            if stale_path.exists() and marker_path.exists():
                marker = json.loads(marker_path.read_text(encoding="utf-8"))
                if marker.get("project_id") == project_key:
                    _remove_tree(stale_path)

    state["projects"][project_key] = sorted(installed)
    save_state(state_path, state)

    return {
        "project_id": project_key,
        "target": str(target_dir),
        "installed": sorted(installed),
        "head_groups": selected_head_groups,
        "specialist_groups": selected_specialist_groups,
        "include_specialists": effective_include_specialists,
        "router": str(target_dir / "research-router"),
    }


def cleanup_managed_skills(
    *,
    target: Path,
    apply: bool,
    project_id: Optional[str] = None,
) -> Dict[str, object]:
    project_key = slugify(project_id) if project_id else ""
    managed_dirs = find_managed_skill_dirs(target, marker_file=MARKER_FILE)
    matched: List[str] = []
    removed: List[str] = []

    for skill_dir in managed_dirs:
        marker_path = skill_dir / MARKER_FILE
        try:
            marker = json.loads(marker_path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        if project_key and marker.get("project_id") != project_key:
            continue
        matched.append(skill_dir.name)
        if apply:
            _remove_tree(skill_dir)
            removed.append(skill_dir.name)

    return {
        "target": str(target),
        "project_id": project_key,
        "matched": sorted(matched),
        "removed": sorted(removed),
        "apply": bool(apply),
    }


def main() -> int:
    args = parse_args()
    try:
        fabric_root = resolve_fabric_root(args.fabric_root)

        selected_groups = _parse_groups(args.groups)
        specialist_groups = _parse_groups(args.specialist_groups)
        include_specialists = bool(args.include_specialists or args.audit)
        if include_specialists and not specialist_groups:
            specialist_groups = list(selected_groups)

        result = install_project_skills(
            fabric_root=fabric_root,
            project_id=args.project_id,
            target=Path(args.target).expanduser().resolve() if args.target else None,
            sync=bool(args.sync),
            head_groups=selected_groups,
            specialist_groups=specialist_groups,
            include_specialists=include_specialists,
        )

        print("installed skills:")
        for name in result["installed"]:
            print(f"- {name}")
        print(f"head_groups: {','.join(result['head_groups'])}")
        print(f"specialist_groups: {','.join(result['specialist_groups'])}")
        print(f"include_specialists: {result['include_specialists']}")
        print(f"router installed: {result['router']}")
        print(f"target: {result['target']}")
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
