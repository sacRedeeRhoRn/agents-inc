from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List

from agents_inc.core.fabric_lib import (
    FabricError,
    ensure_fabric_root_initialized,
    ensure_json_serializable,
    resolve_fabric_root,
    slugify,
)
from agents_inc.core.group_generation_engine import generate_group_draft
from agents_inc.core.group_wizard import build_manifest_v2
from agents_inc.core.live_dashboard import clear_interactive_terminal
from agents_inc.core.util.fs import dump_yaml, load_yaml


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create catalog groups with specialist generation")
    parser.add_argument("--fabric-root", default=None, help="path to fabric root")
    parser.add_argument("--group-id", default=None, help="group id (hyphen-case)")
    parser.add_argument("--display-name", default=None, help="display name")
    parser.add_argument("--domain", default=None, help="domain label")
    parser.add_argument("--purpose", default=None, help="group purpose")
    parser.add_argument("--success-criteria", default="", help="comma-separated success criteria")
    parser.add_argument("--extra-roles", default="", help="comma-separated additional roles")
    parser.add_argument("--force", action="store_true", help="overwrite existing manifest")
    parser.add_argument(
        "--use-codex",
        dest="use_codex",
        action="store_true",
        default=True,
        help="use live Codex app-server role suggestion",
    )
    parser.add_argument(
        "--no-codex",
        dest="use_codex",
        action="store_false",
        help="disable codex role suggestion and use deterministic defaults only",
    )
    parser.add_argument("--json", action="store_true", help="emit JSON output")
    parser.add_argument(
        "--regenerate-core",
        action="store_true",
        help="regenerate core group manifests from seed definitions",
    )
    parser.add_argument(
        "--core-seed-file",
        default="catalog/core-group-seeds.yaml",
        help="seed manifest path for core regeneration",
    )
    return parser.parse_args()


def _ask(prompt: str, default: str = "") -> str:
    label = prompt
    if default:
        label += f" [{default}]"
    label += ": "
    value = input(label).strip()
    return value or default


def _parse_csv(value: str) -> List[str]:
    out: List[str] = []
    for raw in str(value or "").split(","):
        token = str(raw).strip()
        if token and token not in out:
            out.append(token)
    return out


def _mirror_resource_manifest(fabric_root: Path, group_id: str, manifest: dict) -> str | None:
    target = (
        fabric_root / "src" / "agents_inc" / "resources" / "catalog" / "groups" / f"{group_id}.yaml"
    )
    if not target.parent.exists():
        return None
    dump_yaml(target, manifest)
    return str(target.resolve())


def _write_manifest(
    *,
    fabric_root: Path,
    group_id: str,
    manifest: dict,
    force: bool,
) -> tuple[str, str | None]:
    target = fabric_root / "catalog" / "groups" / f"{group_id}.yaml"
    if target.exists() and not force:
        raise FabricError(f"manifest already exists: {target} (use --force)")
    dump_yaml(target, manifest)
    mirrored = _mirror_resource_manifest(fabric_root, group_id, manifest)
    return str(target.resolve()), mirrored


def _build_single_group(args: argparse.Namespace, fabric_root: Path) -> dict:
    group_id = slugify(args.group_id or _ask("Group id", "new-group"))
    if not group_id:
        raise FabricError("group id cannot be empty")
    display_name = str(args.display_name or _ask("Display name", "New Group")).strip()
    domain = slugify(args.domain or _ask("Domain", "general-services"))
    purpose = str(
        args.purpose
        or _ask("Purpose", f"Coordinate expert specialists for {display_name} objectives.")
    ).strip()
    success_criteria = _parse_csv(
        args.success_criteria
        or _ask(
            "Success criteria (comma-separated)",
            "All required artifacts produced, Gate profile satisfied, Exposed handoff consumable",
        )
    )
    if not success_criteria:
        raise FabricError("success criteria cannot be empty")
    extra_roles = _parse_csv(args.extra_roles)

    outcome = generate_group_draft(
        cwd=fabric_root,
        group_id=group_id,
        display_name=display_name,
        domain=domain,
        purpose=purpose,
        success_criteria=success_criteria,
        use_codex=bool(args.use_codex),
        static_extra_roles=extra_roles,
    )
    manifest = build_manifest_v2(outcome.draft)
    written, mirrored = _write_manifest(
        fabric_root=fabric_root,
        group_id=group_id,
        manifest=manifest,
        force=bool(args.force),
    )
    return {
        "group_id": group_id,
        "manifest_path": written,
        "mirrored_manifest_path": mirrored or "",
        "codex_used": outcome.codex_used,
        "extra_roles": outcome.extra_roles,
        "specialist_count": len(outcome.draft.specialists),
    }


def _load_seed_entries(seed_path: Path) -> List[dict]:
    payload = load_yaml(seed_path)
    if not isinstance(payload, dict):
        raise FabricError(f"invalid core seed file: {seed_path}")
    entries = payload.get("groups")
    if not isinstance(entries, list):
        raise FabricError(f"invalid core seed groups list: {seed_path}")
    out: List[dict] = []
    for item in entries:
        if not isinstance(item, dict):
            continue
        out.append(item)
    return out


def _regenerate_core_groups(args: argparse.Namespace, fabric_root: Path) -> dict:
    seed_path = Path(str(args.core_seed_file)).expanduser().resolve()
    if not seed_path.is_absolute():
        seed_path = (fabric_root / args.core_seed_file).resolve()
    entries = _load_seed_entries(seed_path)
    if not entries:
        raise FabricError("core seed file has no groups")

    catalog_dir = fabric_root / "catalog" / "groups"
    for existing in sorted(catalog_dir.glob("*.yaml")):
        existing.unlink()
    resources_dir = fabric_root / "src" / "agents_inc" / "resources" / "catalog" / "groups"
    if resources_dir.exists():
        for existing in sorted(resources_dir.glob("*.yaml")):
            existing.unlink()

    results: List[dict] = []
    for seed in entries:
        group_id = slugify(str(seed.get("group_id") or ""))
        display_name = str(seed.get("display_name") or "").strip()
        domain = slugify(str(seed.get("domain") or ""))
        purpose = str(seed.get("purpose") or "").strip()
        success_criteria = [
            str(x).strip() for x in seed.get("success_criteria", []) if str(x).strip()
        ]
        extra_roles = [str(x).strip() for x in seed.get("extra_roles", []) if str(x).strip()]
        if not all([group_id, display_name, domain, purpose]) or not success_criteria:
            raise FabricError(f"invalid core seed entry: {seed}")
        outcome = generate_group_draft(
            cwd=fabric_root,
            group_id=group_id,
            display_name=display_name,
            domain=domain,
            purpose=purpose,
            success_criteria=success_criteria,
            use_codex=bool(args.use_codex),
            static_extra_roles=extra_roles,
        )
        manifest = build_manifest_v2(outcome.draft)
        written, mirrored = _write_manifest(
            fabric_root=fabric_root,
            group_id=group_id,
            manifest=manifest,
            force=True,
        )
        results.append(
            {
                "group_id": group_id,
                "manifest_path": written,
                "mirrored_manifest_path": mirrored or "",
                "codex_used": outcome.codex_used,
                "extra_roles": outcome.extra_roles,
                "specialist_count": len(outcome.draft.specialists),
            }
        )
    return {
        "mode": "regenerate-core",
        "seed_file": str(seed_path),
        "generated_count": len(results),
        "groups": results,
    }


def main() -> int:
    args = parse_args()
    try:
        if not bool(args.json):
            clear_interactive_terminal()
        fabric_root = resolve_fabric_root(args.fabric_root)
        ensure_fabric_root_initialized(fabric_root)
        if args.regenerate_core:
            payload = _regenerate_core_groups(args, fabric_root)
        else:
            payload = _build_single_group(args, fabric_root)
        if args.json:
            print(json.dumps(ensure_json_serializable(payload), indent=2, sort_keys=True))
        else:
            print(json.dumps(ensure_json_serializable(payload), indent=2, sort_keys=True))
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
