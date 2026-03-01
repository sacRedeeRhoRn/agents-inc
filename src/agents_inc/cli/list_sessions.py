from __future__ import annotations

import argparse
import json
from pathlib import Path

from agents_inc.core.config_state import default_config_path, get_projects_root
from agents_inc.core.fabric_lib import ensure_json_serializable
from agents_inc.core.session_state import (
    default_project_index_path,
    list_index_projects,
    sync_index_from_scan,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="List resumable orchestrator sessions")
    parser.add_argument("--project-index", default=None, help="global project index path")
    parser.add_argument(
        "--scan-root",
        default=None,
        help="scan root for project discovery",
    )
    parser.add_argument(
        "--config-path", default=None, help="config file path (default ~/.agents-inc/config.yaml)"
    )
    parser.add_argument(
        "--no-scan",
        action="store_true",
        help="skip filesystem scan and use index data only",
    )
    parser.add_argument(
        "--include-stale",
        action="store_true",
        help="include stale entries (paths no longer found)",
    )
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    return parser.parse_args()


def _simplify_rows(rows: list[dict]) -> list[dict]:
    simplified: list[dict] = []
    for row in rows:
        simplified.append(
            {
                "project_id": str(row.get("project_id") or ""),
                "status": str(row.get("status") or ""),
                "root": str(row.get("project_root") or ""),
            }
        )
    return simplified


def _print_table(rows: list[dict]) -> None:
    if not rows:
        print("no sessions found")
        return

    print("project_id | status | root")
    print("--- | --- | ---")
    for row in rows:
        print(
            "{0} | {1} | {2}".format(
                row.get("project_id", ""),
                row.get("status", ""),
                row.get("root", ""),
            )
        )


def main() -> int:
    args = parse_args()
    try:
        project_index_path = default_project_index_path(args.project_index)
        scan_root = (
            Path(args.scan_root).expanduser().resolve()
            if args.scan_root
            else get_projects_root(default_config_path(args.config_path))
        )
        if not args.no_scan:
            sync_index_from_scan(project_index_path, scan_root)

        rows = _simplify_rows(
            list_index_projects(
                project_index_path,
                include_stale=bool(args.include_stale),
            )
        )
        payload = {
            "count": len(rows),
            "sessions": rows,
        }
        if args.json:
            print(json.dumps(ensure_json_serializable(payload), indent=2, sort_keys=True))
        else:
            _print_table(rows)
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
