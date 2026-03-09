from __future__ import annotations

import argparse
import json

from agents_inc.cli._project_context import resolve_project_context
from agents_inc.core.fabric_lib import FabricError, ensure_json_serializable, slugify
from agents_inc.core.live_dashboard import clear_interactive_terminal
from agents_inc.core.orchestrator_chat import OrchestratorChatConfig, run_orchestrator_chat
from agents_inc.core.orchestrator_state import load_orchestrator_state
from agents_inc.core.session_state import (
    default_project_index_path,
    load_checkpoint,
    set_index_project_status,
)


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
        if not bool(args.json) and not bool(args.no_launch):
            clear_interactive_terminal()
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
        project_index_path = default_project_index_path(args.project_index)

        # Mark as active when present in index; if not present, continue with local project state.
        try:
            set_index_project_status(project_index_path, project_id, "active")
        except Exception:  # noqa: BLE001
            pass

        state = load_orchestrator_state(project_root, project_id=project_id)
        resume_thread_id = str(state.get("thread_id") or "")
        auto_restart_checkpoint_id = ""
        auto_restart_objective = ""
        auto_restart_turn_dir = ""
        auto_restart_from_cycle = 0
        auto_restart_group_objectives = None
        auto_restart_cycle_summaries = None
        auto_restart_source = ""
        latest_checkpoint_id = ""
        try:
            latest_checkpoint = load_checkpoint(project_root, "latest")
        except Exception:
            latest_checkpoint = {}
        if isinstance(latest_checkpoint, dict):
            latest_checkpoint_id = str(latest_checkpoint.get("checkpoint_id") or "").strip()
            blocked_resume = latest_checkpoint.get("blocked_resume")
            already_resumed = str(state.get("last_auto_resume_checkpoint_id") or "").strip()
            if (
                not bool(args.no_launch)
                and isinstance(blocked_resume, dict)
                and bool(blocked_resume.get("enabled"))
                and latest_checkpoint_id
                and latest_checkpoint_id != already_resumed
            ):
                objective = str(blocked_resume.get("objective") or "").strip()
                if objective:
                    auto_restart_checkpoint_id = latest_checkpoint_id
                    auto_restart_objective = objective
                    auto_restart_turn_dir = str(blocked_resume.get("turn_dir") or "").strip()
                    try:
                        auto_restart_from_cycle = max(
                            0, int(blocked_resume.get("resume_from_cycle", 0) or 0)
                        )
                    except Exception:
                        auto_restart_from_cycle = 0
                    group_objectives = blocked_resume.get("group_objectives")
                    if isinstance(group_objectives, dict):
                        auto_restart_group_objectives = dict(group_objectives)
                    cycle_summaries = blocked_resume.get("cycle_summaries")
                    if isinstance(cycle_summaries, list):
                        auto_restart_cycle_summaries = list(cycle_summaries)
                    auto_restart_source = "checkpoint"
        pending_orchestration = state.get("pending_orchestration")
        if (
            not bool(args.no_launch)
            and not auto_restart_objective
            and isinstance(pending_orchestration, dict)
        ):
            pending_objective = str(pending_orchestration.get("objective") or "").strip()
            if pending_objective:
                auto_restart_checkpoint_id = (
                    str(pending_orchestration.get("checkpoint_id") or "").strip()
                    or latest_checkpoint_id
                    or "pending-interrupted-turn"
                )
                auto_restart_objective = pending_objective
                auto_restart_turn_dir = str(pending_orchestration.get("turn_dir") or "").strip()
                try:
                    auto_restart_from_cycle = max(
                        0, int(pending_orchestration.get("resume_from_cycle", 0) or 0)
                    )
                except Exception:
                    auto_restart_from_cycle = 0
                group_objectives = pending_orchestration.get("group_objectives")
                if isinstance(group_objectives, dict):
                    auto_restart_group_objectives = dict(group_objectives)
                cycle_summaries = pending_orchestration.get("cycle_summaries")
                if isinstance(cycle_summaries, list):
                    auto_restart_cycle_summaries = list(cycle_summaries)
                auto_restart_source = "pending-state"
        chat = run_orchestrator_chat(
            OrchestratorChatConfig(
                fabric_root=fabric_root,
                project_root=project_root,
                project_id=project_id,
                resume_thread_id=resume_thread_id,
                no_launch=bool(args.no_launch),
                project_index_path=project_index_path,
                auto_restart_checkpoint_id=auto_restart_checkpoint_id,
                auto_restart_objective=auto_restart_objective,
                auto_restart_turn_dir=auto_restart_turn_dir,
                auto_restart_from_cycle=auto_restart_from_cycle,
                auto_restart_group_objectives=auto_restart_group_objectives,
                auto_restart_cycle_summaries=auto_restart_cycle_summaries,
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
            "latest_checkpoint_id": latest_checkpoint_id,
            "auto_restart_checkpoint_id": auto_restart_checkpoint_id,
            "auto_restart_turn_dir": auto_restart_turn_dir,
            "auto_restart_from_cycle": auto_restart_from_cycle,
            "auto_restart_source": auto_restart_source,
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
