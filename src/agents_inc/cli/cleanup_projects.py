from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from agents_inc.core.fabric_lib import FabricError, ensure_json_serializable
from agents_inc.core.session_state import (
    default_project_index_path,
    load_project_index,
    save_project_index,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Hard delete indexed agents-inc projects")
    parser.add_argument(
        "--all-indexed",
        action="store_true",
        help="delete all projects currently listed in the project index",
    )
    parser.add_argument("--project-index", default=None, help="project index path")
    parser.add_argument("--yes", action="store_true", help="required confirmation flag")
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    return parser.parse_args()


def _assert_safe_root(project_root: Path) -> None:
    if not project_root.exists():
        return
    resolved = project_root.resolve()
    home = Path.home().resolve()
    if resolved in {Path("/"), home}:
        raise FabricError(f"refusing unsafe delete root: {resolved}")
    if not ((resolved / ".agents-inc").exists() or (resolved / "agent_group_fabric").exists()):
        raise FabricError(f"refusing to delete non-agents-inc-looking root: {resolved}")


def main() -> int:
    args = parse_args()
    try:
        if not args.all_indexed:
            raise FabricError("cleanup-projects currently requires --all-indexed")
        if not args.yes:
            raise FabricError("cleanup-projects requires --yes confirmation")

        index_path = default_project_index_path(args.project_index)
        index_payload = load_project_index(index_path)
        projects = index_payload.get("projects", {})
        if not isinstance(projects, dict):
            projects = {}

        deleted: list[str] = []
        missing: list[str] = []
        failed: list[dict] = []

        for project_id, row in list(projects.items()):
            if not isinstance(row, dict):
                projects.pop(project_id, None)
                continue
            root_raw = str(row.get("project_root") or "").strip()
            if not root_raw:
                projects.pop(project_id, None)
                continue
            root = Path(root_raw).expanduser()
            try:
                _assert_safe_root(root)
                if root.exists():
                    shutil.rmtree(root)
                    deleted.append(project_id)
                else:
                    missing.append(project_id)
                projects.pop(project_id, None)
            except Exception as exc:  # noqa: BLE001
                failed.append(
                    {
                        "project_id": project_id,
                        "root": str(root),
                        "error": str(exc),
                    }
                )

        index_payload["projects"] = projects
        save_project_index(index_path, index_payload)

        report = {
            "project_index": str(index_path),
            "deleted": deleted,
            "missing": missing,
            "failed": failed,
            "final_index_count": len(projects),
        }
        if args.json:
            print(json.dumps(ensure_json_serializable(report), indent=2, sort_keys=True))
        else:
            print(f"project_index: {index_path}")
            print(f"deleted_count: {len(deleted)}")
            print(f"missing_count: {len(missing)}")
            print(f"failed_count: {len(failed)}")
            print(f"final_index_count: {len(projects)}")
        return 0 if not failed else 1
    except Exception as exc:  # noqa: BLE001
        print(f"error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
