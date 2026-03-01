from __future__ import annotations

import argparse
import json
from pathlib import Path

from agents_inc.core.config_state import default_config_path, get_projects_root
from agents_inc.core.fabric_lib import FabricError, ensure_json_serializable, slugify
from agents_inc.core.session_state import (
    default_project_index_path,
    get_index_project,
    set_index_project_status,
    sync_index_from_scan,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Deactivate a project by project-id")
    parser.add_argument("project_id", help="project id to deactivate")
    parser.add_argument("--project-index", default=None, help="global project index path")
    parser.add_argument(
        "--scan-root",
        default=None,
        help="scan root for project discovery",
    )
    parser.add_argument(
        "--config-path", default=None, help="config file path (default ~/.agents-inc/config.yaml)"
    )
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        project_id = slugify(str(args.project_id))
        project_index_path = default_project_index_path(args.project_index)
        scan_root = (
            Path(args.scan_root).expanduser().resolve()
            if args.scan_root
            else get_projects_root(default_config_path(args.config_path))
        )
        sync_index_from_scan(project_index_path, scan_root)

        row = get_index_project(project_index_path, project_id)
        if not isinstance(row, dict):
            raise FabricError(f"project '{project_id}' not found")

        updated = set_index_project_status(project_index_path, project_id, "inactive")
        payload = {
            "project_id": project_id,
            "status": str(updated.get("status") or ""),
            "root": str(updated.get("project_root") or ""),
            "updated_at": str(updated.get("updated_at") or ""),
        }
        if args.json:
            print(json.dumps(ensure_json_serializable(payload), indent=2, sort_keys=True))
        else:
            print(f"project_id: {payload['project_id']}")
            print(f"status: {payload['status']}")
            print(f"root: {payload['root']}")
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
