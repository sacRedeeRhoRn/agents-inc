from __future__ import annotations

import argparse
import json

from agents_inc.cli._project_context import resolve_project_context
from agents_inc.core.fabric_lib import FabricError, ensure_json_serializable, slugify
from agents_inc.core.orchestrator_chat import OrchestratorChatConfig, run_orchestrator_chat
from agents_inc.core.orchestrator_state import load_orchestrator_state
from agents_inc.core.session_state import default_project_index_path, set_index_project_status


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Resume agents-inc project orchestrator chat")
    parser.add_argument("project_id", help="project id to resume")
    parser.add_argument("--fabric-root", default=None, help="fabric root path")
    parser.add_argument("--project-index", default=None, help="global project index path")
    parser.add_argument("--scan-root", default=None, help="projects scan root")
    parser.add_argument("--config-path", default=None, help="config path")
    parser.add_argument(
        "--no-launch",
        action="store_true",
        help="reactivate project state but do not open managed chat",
    )
    parser.add_argument("--json", action="store_true", help="emit JSON output")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        project_id = slugify(args.project_id)
        if not project_id:
            raise FabricError("project id cannot be empty")
        fabric_root, project_root, _, _, _ = resolve_project_context(
            project_id=project_id,
            fabric_root=args.fabric_root,
            project_index=args.project_index,
            scan_root=args.scan_root,
            config_path=args.config_path,
        )

        # Mark as active when present in index; if not present, continue with local project state.
        try:
            set_index_project_status(default_project_index_path(args.project_index), project_id, "active")
        except Exception:  # noqa: BLE001
            pass

        state = load_orchestrator_state(project_root, project_id=project_id)
        resume_thread_id = str(state.get("thread_id") or "")
        chat = run_orchestrator_chat(
            OrchestratorChatConfig(
                fabric_root=fabric_root,
                project_root=project_root,
                project_id=project_id,
                resume_thread_id=resume_thread_id,
                no_launch=bool(args.no_launch),
            )
        )
        summary = {
            "project_id": project_id,
            "project_root": str(project_root),
            "fabric_root": str(fabric_root),
            "thread_id": str(chat.get("thread_id") or ""),
            "resumed_from_thread_id": resume_thread_id,
            "fallback_from_thread": str(chat.get("fallback_from_thread") or ""),
            "chat_log_path": str(chat.get("chat_log_path") or ""),
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
