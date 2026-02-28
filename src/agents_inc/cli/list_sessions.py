from __future__ import annotations

import argparse
import json
from pathlib import Path

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
        default=str(Path.home() / "codex-projects"),
        help="scan root for project discovery",
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


def _print_table(rows: list[dict], project_index_path: Path, scan_stats: dict) -> None:
    print(f"project_index: {project_index_path}")
    print(f"scan_created: {scan_stats.get('created', 0)}")
    print(f"scan_updated: {scan_stats.get('updated', 0)}")
    print(f"sessions: {len(rows)}")
    if not rows:
        print("(no sessions found)")
        return

    print("")
    print("project_id | status | last_checkpoint | updated_at | project_root")
    print("--- | --- | --- | --- | ---")
    for row in rows:
        print(
            "{0} | {1} | {2} | {3} | {4}".format(
                row.get("project_id", ""),
                row.get("status", ""),
                row.get("last_checkpoint", ""),
                row.get("updated_at", ""),
                row.get("project_root", ""),
            )
        )


def main() -> int:
    args = parse_args()
    try:
        project_index_path = default_project_index_path(args.project_index)
        scan_stats = {"created": 0, "updated": 0}
        if not args.no_scan:
            scan_stats = sync_index_from_scan(
                project_index_path,
                Path(args.scan_root).expanduser().resolve(),
            )

        rows = list_index_projects(
            project_index_path,
            include_stale=bool(args.include_stale),
        )
        payload = {
            "project_index": project_index_path,
            "scan": scan_stats,
            "count": len(rows),
            "sessions": rows,
        }
        if args.json:
            print(json.dumps(ensure_json_serializable(payload), indent=2, sort_keys=True))
        else:
            _print_table(rows, project_index_path, scan_stats)
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
