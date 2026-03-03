from __future__ import annotations

import argparse
import json

from agents_inc.cli._project_context import resolve_project_context
from agents_inc.core.fabric_lib import ensure_json_serializable, now_iso, slugify
from agents_inc.core.orchestrator_state import mark_orchestrator_saved
from agents_inc.core.session_compaction import compact_session
from agents_inc.core.session_state import (
    default_project_index_path,
    load_checkpoint,
    write_checkpoint,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Save a project state snapshot")
    parser.add_argument("project_id", help="project identifier")
    parser.add_argument("--fabric-root", default=None, help="fabric root path")
    parser.add_argument("--project-index", default=None, help="project index path")
    parser.add_argument("--scan-root", default=None, help="projects scan root")
    parser.add_argument("--config-path", default=None, help="config path")
    parser.add_argument("--json", action="store_true", help="emit JSON output")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        project_id = slugify(args.project_id)
        fabric_root, project_root, _, _, manifest = resolve_project_context(
            project_id=project_id,
            fabric_root=args.fabric_root,
            project_index=args.project_index,
            scan_root=args.scan_root,
            config_path=args.config_path,
        )
        try:
            latest = load_checkpoint(project_root, "latest")
        except Exception:  # noqa: BLE001
            latest = {
                "project_id": project_id,
                "project_root": str(project_root),
                "fabric_root": str(fabric_root),
                "selected_groups": manifest.get("selected_groups", []),
                "constraints": {},
                "latest_artifacts": {},
                "pending_actions": [],
            }

        payload = dict(latest)
        payload["project_id"] = project_id
        payload["project_root"] = str(project_root)
        payload["fabric_root"] = str(fabric_root)
        payload["updated_at"] = now_iso()
        selected_groups = payload.get("selected_groups")
        if not isinstance(selected_groups, list):
            selected_groups = manifest.get("selected_groups", [])
        checkpoint = write_checkpoint(
            project_root=project_root,
            payload=payload,
            project_index_path=default_project_index_path(args.project_index),
        )
        compact = compact_session(
            project_root=project_root,
            payload=payload,
            selected_groups=[str(item) for item in selected_groups if str(item).strip()],
        )
        mark_orchestrator_saved(
            project_root,
            project_id=project_id,
            checkpoint_id=str(checkpoint["checkpoint_id"]),
        )
        summary = {
            "project_id": project_id,
            "project_root": str(project_root),
            "checkpoint_id": str(checkpoint["checkpoint_id"]),
            "checkpoint_path": str(checkpoint["checkpoint_path"]),
            "compact_id": str(compact["compact_id"]),
            "compact_path": str(compact["compact_path"]),
        }
        if args.json:
            print(json.dumps(ensure_json_serializable(summary), indent=2, sort_keys=True))
        else:
            print(json.dumps(ensure_json_serializable(summary), indent=2, sort_keys=True))
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
