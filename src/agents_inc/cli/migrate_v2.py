from __future__ import annotations

import argparse
import json
from pathlib import Path

from agents_inc.core.fabric_lib import (
    FabricError,
    ensure_fabric_root_initialized,
    resolve_fabric_root,
)
from agents_inc.core.migrate_v2 import run_migration
from agents_inc.core.session_state import default_project_index_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Migrate agents-inc artifacts to strict v2 schema")
    parser.add_argument("--fabric-root", default=None, help="path to fabric root")
    parser.add_argument("--project-index", default=None, help="project index path")
    parser.add_argument(
        "--dry-run", action="store_true", help="print migration plan without applying"
    )
    parser.add_argument("--apply", action="store_true", help="apply migration changes")
    parser.add_argument("--backup-dir", default=None, help="backup directory for changed files")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.dry_run and args.apply:
            raise FabricError("use either --dry-run or --apply")
        if not args.dry_run and not args.apply:
            raise FabricError("one of --dry-run or --apply is required")

        fabric_root = resolve_fabric_root(args.fabric_root)
        ensure_fabric_root_initialized(fabric_root)
        project_index = default_project_index_path(args.project_index)
        backup_dir = (
            Path(args.backup_dir).expanduser().resolve()
            if args.backup_dir
            else (fabric_root / ".migrations" / "v2-backups")
        )

        report = run_migration(
            fabric_root=fabric_root,
            project_index_path=project_index,
            apply=bool(args.apply),
            backup_dir=backup_dir,
        )

        mode = "apply" if args.apply else "dry-run"
        print(f"migration mode: {mode}")
        print(json.dumps(report, indent=2, sort_keys=True))

        if report.get("errors"):
            return 1
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
