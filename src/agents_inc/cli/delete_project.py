from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from agents_inc.core.config_state import default_config_path, get_projects_root
from agents_inc.core.fabric_lib import FabricError, ensure_json_serializable, slugify
from agents_inc.core.session_state import (
    default_project_index_path,
    get_index_project,
    remove_index_project,
    sync_index_from_scan,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Delete a project by project-id")
    parser.add_argument("project_id", help="project id to delete")
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
        "--yes",
        action="store_true",
        help="required confirmation flag for deleting project files",
    )
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    return parser.parse_args()


def _assert_safe_delete_root(project_root: Path) -> None:
    if not project_root.exists():
        return
    home = Path.home().resolve()
    resolved = project_root.resolve()
    if resolved in {Path("/"), home}:
        raise FabricError(f"refusing to delete unsafe root: {resolved}")
    if not ((resolved / ".agents-inc").exists() or (resolved / "agent_group_fabric").exists()):
        raise FabricError(
            f"refusing to delete path that does not look like an agents-inc project: {resolved}"
        )


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

        project_root = Path(str(row.get("project_root") or "")).expanduser().resolve()
        _assert_safe_delete_root(project_root)
        if not args.yes:
            raise FabricError(
                "delete requires --yes confirmation. This command removes project files and index entry."
            )

        root_deleted = False
        if project_root.exists():
            shutil.rmtree(project_root)
            root_deleted = True

        index_removed = remove_index_project(project_index_path, project_id)
        payload = {
            "project_id": project_id,
            "root": str(project_root),
            "root_deleted": root_deleted,
            "index_removed": bool(index_removed),
        }
        if args.json:
            print(json.dumps(ensure_json_serializable(payload), indent=2, sort_keys=True))
        else:
            print(f"project_id: {payload['project_id']}")
            print(f"root: {payload['root']}")
            print(f"root_deleted: {payload['root_deleted']}")
            print(f"index_removed: {payload['index_removed']}")
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
