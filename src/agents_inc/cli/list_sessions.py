from __future__ import annotations

import argparse
import json
from pathlib import Path

from agents_inc.core.config_state import default_config_path, get_projects_root
from agents_inc.core.fabric_lib import ensure_json_serializable
from agents_inc.core.session_compaction import load_latest_compacted_summary
from agents_inc.core.session_state import (
    default_project_index_path,
    list_index_projects,
    load_checkpoint,
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


def _safe_checkpoint_summary(project_root: Path) -> dict:
    try:
        checkpoint = load_checkpoint(project_root, "latest")
    except Exception:
        return {"session_code": "", "active_groups": []}
    groups = checkpoint.get("selected_groups")
    if not isinstance(groups, list):
        groups = []
    return {
        "session_code": str(checkpoint.get("checkpoint_id") or ""),
        "active_groups": [str(group_id) for group_id in groups],
    }


def _enrich_rows(rows: list[dict]) -> list[dict]:
    enriched: list[dict] = []
    for row in rows:
        payload = dict(row)
        root_raw = payload.get("project_root")
        project_root = Path(str(root_raw)).expanduser().resolve()
        compact = load_latest_compacted_summary(project_root)
        if compact is None:
            compact = _safe_checkpoint_summary(project_root)
            compact["group_session_map"] = {}
        payload["session_code"] = str(compact.get("session_code") or "")
        payload["active_groups"] = compact.get("active_groups", [])
        payload["group_session_map"] = compact.get("group_session_map", {})
        enriched.append(payload)
    return enriched


def _print_table(rows: list[dict], project_index_path: Path, scan_stats: dict) -> None:
    print(f"project_index: {project_index_path}")
    print(f"scan_created: {scan_stats.get('created', 0)}")
    print(f"scan_updated: {scan_stats.get('updated', 0)}")
    print(f"sessions: {len(rows)}")
    if not rows:
        print("(no sessions found)")
        return

    print("")
    print(
        "project_id | session_code | active_groups | status | last_checkpoint | updated_at | project_root"
    )
    print("--- | --- | --- | --- | --- | --- | ---")
    for row in rows:
        active_groups = row.get("active_groups", [])
        if not isinstance(active_groups, list):
            active_groups = []
        print(
            "{0} | {1} | {2} | {3} | {4} | {5} | {6}".format(
                row.get("project_id", ""),
                row.get("session_code", ""),
                ",".join(str(group_id) for group_id in active_groups),
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
        scan_root = (
            Path(args.scan_root).expanduser().resolve()
            if args.scan_root
            else get_projects_root(default_config_path(args.config_path))
        )
        scan_stats = {"created": 0, "updated": 0}
        if not args.no_scan:
            scan_stats = sync_index_from_scan(
                project_index_path,
                scan_root,
            )

        rows = _enrich_rows(
            list_index_projects(
                project_index_path,
                include_stale=bool(args.include_stale),
            )
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
