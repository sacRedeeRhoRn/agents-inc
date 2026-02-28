from __future__ import annotations

import argparse
import json
from pathlib import Path

from agents_inc.core.fabric_lib import (
    FabricError,
    collect_project_skill_records,
    copy_dir,
    ensure_fabric_root_initialized,
    load_project_manifest,
    parse_skill_frontmatter,
    render_template,
    resolve_fabric_root,
    slugify,
    write_text,
)

STATE_FILE = ".fabric-install-state.json"
MARKER_FILE = ".fabric-managed.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Install generated project skills into Codex local skill directory"
    )
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--fabric-root", default=None, help="path to fabric root")
    parser.add_argument("--sync", action="store_true", help="remove stale skills for the project")
    parser.add_argument("--target", default=None, help="override install target")
    parser.add_argument(
        "--include-specialists",
        action="store_true",
        help="install specialist skills (default installs head skills only)",
    )
    parser.add_argument(
        "--audit",
        action="store_true",
        help="alias for --include-specialists when audit visibility is needed",
    )
    return parser.parse_args()


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


def main() -> int:
    args = parse_args()
    try:
        fabric_root = resolve_fabric_root(args.fabric_root)
        ensure_fabric_root_initialized(fabric_root)

        project_dir, manifest = load_project_manifest(fabric_root, args.project_id)

        target_path = args.target or manifest.get("install_targets", {}).get("codex_skill_dir")
        if not target_path:
            raise FabricError("could not resolve target skill dir (use --target)")
        target = Path(target_path).expanduser().resolve()
        target.mkdir(parents=True, exist_ok=True)

        visibility = manifest.get("visibility", {})
        include_specialists = bool(
            args.include_specialists
            or args.audit
            or (isinstance(visibility, dict) and visibility.get("mode") == "full")
        )

        records = collect_project_skill_records(
            project_dir, manifest, include_specialists=include_specialists
        )
        if not records:
            raise FabricError("no skill records found in project manifest")

        installed = []
        for record in records:
            destination = target / record.skill_name
            copy_dir(record.source_dir, destination)
            marker = {
                "project_id": slugify(args.project_id),
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

        install_router_skill(fabric_root, target)

        state_path = target / STATE_FILE
        state = load_state(state_path)
        project_key = slugify(args.project_id)
        previous = set(state.setdefault("projects", {}).get(project_key, []))

        if args.sync:
            stale = sorted(previous - set(installed))
            for stale_skill in stale:
                stale_path = target / stale_skill
                marker_path = stale_path / MARKER_FILE
                if stale_path.exists() and marker_path.exists():
                    marker = json.loads(marker_path.read_text(encoding="utf-8"))
                    if marker.get("project_id") == project_key:
                        for path in sorted(stale_path.rglob("*"), reverse=True):
                            if path.is_file() or path.is_symlink():
                                path.unlink()
                            elif path.is_dir():
                                path.rmdir()
                        stale_path.rmdir()

        state["projects"][project_key] = sorted(installed)
        save_state(state_path, state)

        print("installed skills:")
        for name in sorted(installed):
            print(f"- {name}")
        print(f"include_specialists: {include_specialists}")
        print(f"router installed: {target / 'research-router'}")
        print(f"target: {target}")
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
