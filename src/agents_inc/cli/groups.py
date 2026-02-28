from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

from agents_inc.core.fabric_lib import (
    FabricError,
    dump_yaml,
    ensure_fabric_root_initialized,
    ensure_group_shape,
    load_yaml,
    resolve_fabric_root,
    slugify,
)
from agents_inc.core.group_wizard import (
    MANDATORY_ROLES,
    GroupDraft,
    build_manifest_v2,
    propose_specialists,
    run_interactive_wizard,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Catalog group management (v2)")
    sub = parser.add_subparsers(dest="subcommand")

    list_parser = sub.add_parser("list", help="list catalog groups")
    list_parser.add_argument("--fabric-root", default=None, help="path to fabric root")
    list_parser.add_argument(
        "--include-invalid", action="store_true", help="include invalid manifests"
    )
    list_parser.add_argument("--json", action="store_true", help="emit JSON output")

    show_parser = sub.add_parser("show", help="show one catalog group")
    show_parser.add_argument("group_id", help="catalog group id")
    show_parser.add_argument("--fabric-root", default=None, help="path to fabric root")
    show_parser.add_argument("--json", action="store_true", help="emit JSON output")

    new_parser = sub.add_parser("new", help="create catalog group manifest")
    new_parser.add_argument("--fabric-root", default=None, help="path to fabric root")
    new_parser.add_argument(
        "--interactive", action="store_true", help="run codex-friendly interactive wizard"
    )
    new_parser.add_argument("--group-id", default=None, help="hyphen-case group id")
    new_parser.add_argument("--display-name", default=None, help="human-readable group title")
    new_parser.add_argument("--domain", default=None, help="domain label")
    new_parser.add_argument("--purpose", default=None, help="group purpose")
    new_parser.add_argument(
        "--success-criteria",
        default=None,
        help="comma-separated success criteria",
    )
    new_parser.add_argument(
        "--extra-roles",
        default="",
        help="comma-separated optional extra specialist roles",
    )
    new_parser.add_argument("--force", action="store_true", help="overwrite existing manifest")
    new_parser.add_argument(
        "--mirror-resources",
        action="store_true",
        default=True,
        help="also mirror manifest to src/agents_inc/resources/catalog/groups when available",
    )
    new_parser.add_argument(
        "--no-mirror-resources",
        dest="mirror_resources",
        action="store_false",
        help="do not mirror to package resources path",
    )

    templates_parser = sub.add_parser("templates", help="show group template archetypes")
    templates_parser.add_argument("--json", action="store_true", help="emit JSON output")

    return parser.parse_args()


def _catalog_groups_dir(fabric_root: Path) -> Path:
    return fabric_root / "catalog" / "groups"


def _iter_group_records(fabric_root: Path) -> List[Dict[str, Any]]:
    groups_dir = _catalog_groups_dir(fabric_root)
    if not groups_dir.exists():
        return []

    rows: List[Dict[str, Any]] = []
    for path in sorted(groups_dir.glob("*.yaml")):
        row: Dict[str, Any] = {
            "source_path": str(path.resolve()),
            "group_id": path.stem,
            "display_name": "",
            "domain": "",
            "specialist_count": 0,
            "template_version": "",
            "schema_version": "",
            "status": "invalid",
            "head_agent_id": "",
            "errors": [],
        }
        try:
            data = load_yaml(path)
            if not isinstance(data, dict):
                row["errors"] = ["manifest is not a mapping"]
                rows.append(row)
                continue
            errs = ensure_group_shape(data, source=str(path))
            row["group_id"] = str(data.get("group_id") or row["group_id"])
            row["display_name"] = str(data.get("display_name") or "")
            row["domain"] = str(data.get("domain") or "")
            row["specialist_count"] = len(data.get("specialists") or [])
            row["template_version"] = str(data.get("template_version") or "")
            row["schema_version"] = str(data.get("schema_version") or "")
            head = data.get("head") if isinstance(data.get("head"), dict) else {}
            row["head_agent_id"] = str(head.get("agent_id") or "")
            row["status"] = "valid" if not errs else "invalid"
            row["errors"] = errs
        except Exception as exc:  # noqa: BLE001
            row["errors"] = [str(exc)]
        rows.append(row)
    return rows


def _print_table(rows: List[Dict[str, Any]]) -> None:
    print(
        "group_id | display_name | domain | specialist_count | template_version | schema_version | status | head_agent_id | source_path"
    )
    print("--- | --- | --- | --- | --- | --- | --- | --- | ---")
    for row in rows:
        print(
            "{0} | {1} | {2} | {3} | {4} | {5} | {6} | {7} | {8}".format(
                row.get("group_id", ""),
                row.get("display_name", ""),
                row.get("domain", ""),
                row.get("specialist_count", 0),
                row.get("template_version", ""),
                row.get("schema_version", ""),
                row.get("status", ""),
                row.get("head_agent_id", ""),
                row.get("source_path", ""),
            )
        )


def _ask(prompt: str, default: str | None = None) -> str:
    suffix = "" if default is None else f" [{default}]"
    answer = input(f"{prompt}{suffix}: ").strip()
    if not answer and default is not None:
        return default
    return answer


def _build_non_interactive_draft(args: argparse.Namespace) -> GroupDraft:
    if not args.group_id or not args.display_name or not args.domain:
        raise FabricError("non-interactive mode requires --group-id, --display-name, and --domain")
    group_id = slugify(args.group_id)
    display_name = args.display_name.strip()
    domain = slugify(args.domain)
    purpose = (
        args.purpose or f"Coordinate expert specialists for {display_name} objectives."
    ).strip()
    success_raw = (
        args.success_criteria
        or "All required artifacts produced, Gate profile satisfied, Exposed handoff consumable"
    )
    success_criteria = [item.strip() for item in success_raw.split(",") if item.strip()]
    extra_roles = [item.strip() for item in str(args.extra_roles or "").split(",") if item.strip()]
    specialists = propose_specialists(group_id, display_name, domain, extra_roles=extra_roles)
    return GroupDraft(
        group_id=group_id,
        display_name=display_name,
        domain=domain,
        purpose=purpose,
        success_criteria=success_criteria,
        specialists=specialists,
    )


def _mirror_resource_manifest(fabric_root: Path, group_id: str, manifest: dict) -> str | None:
    resource_target = (
        fabric_root / "src" / "agents_inc" / "resources" / "catalog" / "groups" / f"{group_id}.yaml"
    )
    if not resource_target.parent.exists():
        return None
    dump_yaml(resource_target, manifest)
    return str(resource_target.resolve())


def _cmd_list(args: argparse.Namespace) -> int:
    fabric_root = resolve_fabric_root(args.fabric_root)
    ensure_fabric_root_initialized(fabric_root)
    rows = _iter_group_records(fabric_root)
    if not args.include_invalid:
        rows = [row for row in rows if row.get("status") == "valid"]

    payload = {
        "fabric_root": str(fabric_root),
        "count": len(rows),
        "groups": rows,
    }
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        _print_table(rows)
    return 0


def _cmd_show(args: argparse.Namespace) -> int:
    fabric_root = resolve_fabric_root(args.fabric_root)
    ensure_fabric_root_initialized(fabric_root)
    group_id = slugify(args.group_id)
    path = _catalog_groups_dir(fabric_root) / f"{group_id}.yaml"
    if not path.exists():
        raise FabricError(f"group not found: {group_id}")
    manifest = load_yaml(path)
    if not isinstance(manifest, dict):
        raise FabricError(f"invalid group manifest: {path}")
    errors = ensure_group_shape(manifest, source=str(path))
    payload = {
        "group_id": group_id,
        "source_path": str(path.resolve()),
        "status": "valid" if not errors else "invalid",
        "errors": errors,
        "manifest": manifest,
    }
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"group_id: {group_id}")
        print(f"status: {payload['status']}")
        print(f"source_path: {payload['source_path']}")
        print(f"specialists: {len(manifest.get('specialists') or [])}")
        print(f"schema_version: {manifest.get('schema_version', '')}")
        if errors:
            print("errors:")
            for err in errors:
                print(f"- {err}")
    return 0


def _cmd_new(args: argparse.Namespace) -> int:
    fabric_root = resolve_fabric_root(args.fabric_root)
    ensure_fabric_root_initialized(fabric_root)

    if args.interactive:
        draft = run_interactive_wizard(
            _ask,
            group_id=args.group_id,
            display_name=args.display_name,
            domain=args.domain,
        )
    else:
        draft = _build_non_interactive_draft(args)

    if args.purpose:
        draft.purpose = args.purpose.strip()
    if args.success_criteria:
        parsed = [item.strip() for item in args.success_criteria.split(",") if item.strip()]
        if parsed:
            draft.success_criteria = parsed

    manifest = build_manifest_v2(draft)
    group_id = manifest["group_id"]
    target = _catalog_groups_dir(fabric_root) / f"{group_id}.yaml"
    if target.exists() and not args.force:
        raise FabricError(f"manifest already exists: {target} (use --force)")

    dump_yaml(target, manifest)
    mirrored = (
        _mirror_resource_manifest(fabric_root, group_id, manifest)
        if args.mirror_resources
        else None
    )
    print(f"created group manifest: {target}")
    if mirrored:
        print(f"mirrored package resource manifest: {mirrored}")
    return 0


def _cmd_templates(args: argparse.Namespace) -> int:
    payload = {
        "schema_version": "2.0",
        "archetypes": [
            {
                "id": "domain-integration-review-qa",
                "description": "Baseline expert group with mandatory integration/evidence/repro roles",
                "mandatory_roles": MANDATORY_ROLES,
            }
        ],
    }
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print("available group archetypes:")
        for archetype in payload["archetypes"]:
            print(f"- {archetype['id']}: {archetype['description']}")
            print("  mandatory_roles: " + ", ".join(archetype["mandatory_roles"]))
    return 0


def main() -> int:
    args = parse_args()
    try:
        if args.subcommand == "list":
            return _cmd_list(args)
        if args.subcommand == "show":
            return _cmd_show(args)
        if args.subcommand == "new":
            return _cmd_new(args)
        if args.subcommand == "templates":
            return _cmd_templates(args)
        raise FabricError("usage: agents-inc groups <list|show|new|templates> ...")
    except Exception as exc:  # noqa: BLE001
        print(f"error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
