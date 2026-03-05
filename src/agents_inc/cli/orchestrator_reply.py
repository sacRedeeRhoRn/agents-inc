from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from agents_inc.cli.escalation_prompt import resolve_escalations
from agents_inc.core.config_state import default_config_path, get_projects_root
from agents_inc.core.fabric_lib import (
    FabricError,
    ensure_fabric_root_initialized,
    resolve_fabric_root,
    slugify,
)
from agents_inc.core.model_profiles import (
    DEFAULT_HEAD_MODEL,
    DEFAULT_HEAD_REASONING_EFFORT,
    DEFAULT_SPECIALIST_MODEL,
    DEFAULT_SPECIALIST_REASONING_EFFORT,
    normalize_model_slug,
    normalize_reasoning_effort,
)
from agents_inc.core.orchestrator_reply import OrchestratorReplyConfig, run_orchestrator_reply
from agents_inc.core.progress_notes import format_progress_event
from agents_inc.core.session_state import default_project_index_path, find_resume_project


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate one orchestrator turn reply with strict mode split"
    )
    parser.add_argument("--fabric-root", default=None, help="path to fabric root")
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--message", required=True, help="user message")
    parser.add_argument("--group", default="auto", help="group id or auto")
    parser.add_argument(
        "--output-dir",
        default=None,
        help="optional explicit turn output directory",
    )
    parser.add_argument(
        "--project-index",
        default=None,
        help="global project index path used when --fabric-root is omitted",
    )
    parser.add_argument(
        "--scan-root",
        default=None,
        help="fallback scan root used when project index lookup misses",
    )
    parser.add_argument(
        "--config-path",
        default=None,
        help="config file path (default ~/.agents-inc/config.yaml)",
    )
    parser.add_argument("--json", action="store_true", help="emit JSON result")
    parser.add_argument(
        "--max-parallel",
        type=int,
        default=None,
        help="max concurrent sessions (0 = uncapped)",
    )
    parser.add_argument(
        "--retry-attempts",
        type=int,
        default=None,
        help="retry attempts per specialist session",
    )
    parser.add_argument(
        "--retry-backoff-sec",
        type=int,
        default=None,
        help="retry backoff seconds between attempts",
    )
    parser.add_argument(
        "--agent-timeout-sec",
        type=int,
        default=None,
        help="timeout in seconds for each specialist/head session (omit or 0 = unlimited)",
    )
    parser.add_argument(
        "--specialist-model",
        default=None,
        help=f"specialist model slug (default: {DEFAULT_SPECIALIST_MODEL})",
    )
    parser.add_argument(
        "--head-model",
        default=None,
        help=f"group head model slug (default: {DEFAULT_HEAD_MODEL})",
    )
    parser.add_argument(
        "--specialist-reasoning-effort",
        default=None,
        help=(
            "specialist reasoning effort override "
            f"(default: {DEFAULT_SPECIALIST_REASONING_EFFORT}; low|medium|high|xhigh)"
        ),
    )
    parser.add_argument(
        "--head-reasoning-effort",
        default=None,
        help=f"group head reasoning effort override (default: {DEFAULT_HEAD_REASONING_EFFORT})",
    )
    parser.add_argument(
        "--web-search-policy",
        default="web-role-only",
        choices=["web-role-only", "all-enabled"],
        help="web search policy for specialist runs",
    )
    parser.add_argument(
        "--live-profile",
        default="bounded",
        choices=["bounded", "custom"],
        help="runtime profile for cooperative loop",
    )
    parser.add_argument(
        "--audit",
        action="store_true",
        help="include specialist-level details in exposed response when available",
    )
    parser.add_argument(
        "--loop-mode",
        default="cooperative",
        choices=["cooperative"],
        help="group runtime loop mode",
    )
    parser.add_argument(
        "--meeting-enabled",
        dest="meeting_enabled",
        action="store_true",
        default=True,
        help="enable inter-group head meeting phase between cycles",
    )
    parser.add_argument(
        "--no-meeting",
        dest="meeting_enabled",
        action="store_false",
        help="disable inter-group head meeting phase",
    )
    parser.add_argument(
        "--stop-rule",
        default="unanimous-head-satisfied",
        choices=["unanimous-head-satisfied"],
        help="loop stop rule",
    )
    parser.add_argument(
        "--max-cycles",
        type=int,
        default=None,
        help="max cycles before hard block (omit or 0 = unlimited)",
    )
    parser.add_argument(
        "--heartbeat-sec",
        type=int,
        default=None,
        help="heartbeat interval seconds for cooperative loop",
    )
    parser.add_argument(
        "--require-negotiation",
        default=None,
        choices=["true", "false"],
        help="require observed group-head negotiation in group mode",
    )
    parser.add_argument(
        "--abort-file",
        default=None,
        help="if this file exists during runtime, cooperative loop stops with hard block",
    )
    parser.add_argument(
        "--non-interactive-escalation",
        action="store_true",
        help="do not prompt for escalation values when blocked by escalation requests",
    )
    return parser.parse_args()


def _manifest_exists(fabric_root: Path, project_id: str) -> bool:
    manifest = fabric_root / "generated" / "projects" / project_id / "manifest.yaml"
    return manifest.exists()


def _resolve_project_fabric_root(args: argparse.Namespace, project_id: str) -> Path:
    attempted: list[str] = []

    if args.fabric_root:
        explicit = resolve_fabric_root(args.fabric_root)
        if _manifest_exists(explicit, project_id):
            return explicit
        attempted.append(f"--fabric-root={explicit} (manifest not found)")

    index_path = default_project_index_path(args.project_index)
    scan_root = (
        Path(str(args.scan_root)).expanduser().resolve()
        if args.scan_root
        else get_projects_root(default_config_path(args.config_path))
    )
    found = find_resume_project(
        index_path=index_path,
        project_id=project_id,
        fallback_scan_root=scan_root,
    )
    if isinstance(found, dict):
        fabric_root_raw = str(found.get("fabric_root") or "").strip()
        if fabric_root_raw:
            indexed_fabric = Path(fabric_root_raw).expanduser().resolve()
            if _manifest_exists(indexed_fabric, project_id) or not args.fabric_root:
                return indexed_fabric
            attempted.append(f"index.fabric_root={indexed_fabric} (manifest not found)")

        project_root_raw = str(found.get("project_root") or "").strip()
        if project_root_raw:
            project_root = Path(project_root_raw).expanduser().resolve()
            derived = (project_root / "agent_group_fabric").resolve()
            if _manifest_exists(derived, project_id) or not args.fabric_root:
                return derived
            attempted.append(f"project_root/agent_group_fabric={derived} (manifest not found)")

    default_root = resolve_fabric_root(None)
    if _manifest_exists(default_root, project_id):
        return default_root
    attempted.append(f"default={default_root} (manifest not found)")

    raise FabricError(
        "could not resolve fabric root for project '{0}'. attempted: {1}".format(
            project_id,
            "; ".join(attempted) if attempted else "none",
        )
    )


def _is_non_group_message(message: str) -> bool:
    return str(message).startswith("[non-group]")


def _parse_bool_text(value: str | None, *, default: bool) -> bool:
    if value is None:
        return default
    return str(value).strip().lower() == "true"


def _resolve_runtime_settings(args: argparse.Namespace) -> dict:
    profile = str(args.live_profile or "bounded").strip().lower()
    if profile == "bounded":
        defaults = {
            "max_parallel": 6,
            "retry_attempts": 1,
            "retry_backoff_sec": 3,
            "agent_timeout_sec": 0,
            "max_cycles": 0,
            "heartbeat_sec": 30,
        }
    else:
        defaults = {
            "max_parallel": 0,
            "retry_attempts": 2,
            "retry_backoff_sec": 5,
            "agent_timeout_sec": 0,
            "max_cycles": 0,
            "heartbeat_sec": 30,
        }

    return {
        "profile": profile,
        "max_parallel": (
            max(0, int(args.max_parallel))
            if args.max_parallel is not None
            else defaults["max_parallel"]
        ),
        "retry_attempts": (
            max(0, int(args.retry_attempts))
            if args.retry_attempts is not None
            else defaults["retry_attempts"]
        ),
        "retry_backoff_sec": (
            max(0, int(args.retry_backoff_sec))
            if args.retry_backoff_sec is not None
            else defaults["retry_backoff_sec"]
        ),
        "agent_timeout_sec": (
            max(0, int(args.agent_timeout_sec))
            if args.agent_timeout_sec is not None
            else defaults["agent_timeout_sec"]
        ),
        "max_cycles": (
            max(0, int(args.max_cycles)) if args.max_cycles is not None else defaults["max_cycles"]
        ),
        "heartbeat_sec": (
            max(5, int(args.heartbeat_sec))
            if args.heartbeat_sec is not None
            else defaults["heartbeat_sec"]
        ),
    }


def _resolve_model_settings(args: argparse.Namespace) -> dict:
    return {
        "specialist_model": normalize_model_slug(
            args.specialist_model,
            default=DEFAULT_SPECIALIST_MODEL,
        ),
        "head_model": normalize_model_slug(
            args.head_model,
            default=DEFAULT_HEAD_MODEL,
        ),
        "specialist_reasoning_effort": normalize_reasoning_effort(
            args.specialist_reasoning_effort,
            default=DEFAULT_SPECIALIST_REASONING_EFFORT,
        ),
        "head_reasoning_effort": normalize_reasoning_effort(
            args.head_reasoning_effort,
            default=DEFAULT_HEAD_REASONING_EFFORT,
        ),
    }


_BLOCKED_RE = re.compile(
    r"BLOCKED\[(?P<status>[^\]]+)\]\s+blocked_report=(?P<report>\S+)\s+blocked_reasons=(?P<reasons>\S+)"
)


def _parse_blocked_error(text: str) -> dict | None:
    match = _BLOCKED_RE.search(str(text))
    if not match:
        return None
    return {
        "status": match.group("status"),
        "blocked_report": match.group("report"),
        "blocked_reasons": match.group("reasons"),
    }


def _load_json(path: str) -> dict:
    p = Path(str(path or "").strip())
    if not p.exists():
        return {}
    try:
        payload = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if isinstance(payload, dict):
        return payload
    return {}


def _handle_blocked_escalations(
    *,
    blocked_payload_path: str,
    interactive: bool,
) -> dict:
    payload = _load_json(blocked_payload_path)
    escalations = payload.get("escalations", [])
    if not isinstance(escalations, list) or not escalations:
        return {"resolved_count": 0, "unresolved_count": 0, "resolved": [], "unresolved": []}
    return resolve_escalations(escalations, interactive=interactive)


def main() -> int:
    args = parse_args()
    try:
        project_id = slugify(str(args.project_id))
        fabric_root = _resolve_project_fabric_root(args, project_id)
        ensure_fabric_root_initialized(fabric_root)
        is_non_group = _is_non_group_message(str(args.message))
        runtime = _resolve_runtime_settings(args)
        model_settings = _resolve_model_settings(args)
        require_negotiation = _parse_bool_text(
            args.require_negotiation,
            default=(not is_non_group),
        )
        if not is_non_group:
            if not bool(args.meeting_enabled):
                raise FabricError(
                    "group mode requires meeting loop. Remove --no-meeting or use [non-group] prefix."
                )

        def _print_live_event_stdout(event: dict) -> None:
            line = format_progress_event(event)
            if line:
                print(line, flush=True)

        def _print_live_event_stderr(event: dict) -> None:
            line = format_progress_event(event)
            if line:
                print(line, file=sys.stderr, flush=True)

        config = OrchestratorReplyConfig(
            fabric_root=fabric_root,
            project_id=project_id,
            message=str(args.message),
            group=(
                "auto" if str(args.group or "auto") == "auto" else slugify(str(args.group or ""))
            ),
            output_dir=Path(args.output_dir).expanduser().resolve() if args.output_dir else None,
            max_parallel=int(runtime["max_parallel"]),
            retry_attempts=int(runtime["retry_attempts"]),
            retry_backoff_sec=int(runtime["retry_backoff_sec"]),
            agent_timeout_sec=int(runtime["agent_timeout_sec"]),
            loop_mode=str(args.loop_mode or "cooperative"),
            meeting_enabled=bool(args.meeting_enabled),
            stop_rule=str(args.stop_rule or "unanimous-head-satisfied"),
            max_cycles=int(runtime["max_cycles"]),
            heartbeat_sec=int(runtime["heartbeat_sec"]),
            abort_file=Path(args.abort_file).expanduser().resolve() if args.abort_file else None,
            require_negotiation=bool(require_negotiation),
            audit=bool(args.audit),
            specialist_model=str(model_settings["specialist_model"]),
            specialist_reasoning_effort=model_settings["specialist_reasoning_effort"],
            head_model=str(model_settings["head_model"]),
            head_reasoning_effort=model_settings["head_reasoning_effort"],
            web_search_policy=str(args.web_search_policy or "web-role-only"),
            progress_callback=(_print_live_event_stderr if args.json else _print_live_event_stdout),
        )
        result = run_orchestrator_reply(config)
        if args.json:
            print(json.dumps(result, indent=2, sort_keys=True))
        else:
            key_points_path = str(result.get("key_points_path") or "").strip()
            if key_points_path:
                key_points_text = Path(key_points_path).read_text(
                    encoding="utf-8", errors="replace"
                )
                print(key_points_text.strip())
            else:
                print(f"project_id: {result.get('project_id')}")
                print(f"turn_dir: {result.get('turn_dir')}")
                print(f"full_report_path: {result.get('full_report_path')}")
        return 0
    except Exception as exc:  # noqa: BLE001
        blocked = _parse_blocked_error(str(exc))
        if blocked:
            escalation_summary = {}
            if blocked.get("status") == "BLOCKED_ESCALATION_REQUIRED":
                interactive = bool(
                    not args.non_interactive_escalation
                    and not args.json
                    and sys.stdin.isatty()
                    and sys.stdout.isatty()
                )
                escalation_summary = _handle_blocked_escalations(
                    blocked_payload_path=blocked.get("blocked_reasons", ""),
                    interactive=interactive,
                )
            if args.json:
                print(
                    json.dumps(
                        {"error": "blocked", **blocked, "escalation_summary": escalation_summary},
                        indent=2,
                        sort_keys=True,
                    )
                )
            else:
                print(f"blocked_status: {blocked['status']}")
                print(f"blocked_report: {blocked['blocked_report']}")
                print(f"blocked_reasons: {blocked['blocked_reasons']}")
                if escalation_summary:
                    print(
                        "escalations_resolved: {0} unresolved: {1}".format(
                            escalation_summary.get("resolved_count", 0),
                            escalation_summary.get("unresolved_count", 0),
                        )
                    )
                print(
                    f'rerun: agents-inc orchestrator-reply --project-id {slugify(str(args.project_id))} --message "{str(args.message).replace(chr(34), chr(39))}"'
                )
            return 1
        print(f"error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
