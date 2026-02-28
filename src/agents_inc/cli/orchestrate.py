from __future__ import annotations

import argparse
import json
from pathlib import Path

from agents_inc.core.fabric_lib import (
    FabricError,
    ensure_fabric_root_initialized,
    resolve_fabric_root,
)
from agents_inc.core.orchestrator_campaign import OrchestratorConfig, run_orchestrator_campaign


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run evidence-first orchestrator campaign with live session capture"
    )
    parser.add_argument("--fabric-root", default=None, help="path to fabric root")
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--task", required=True)
    parser.add_argument("--create-group", default=None)
    parser.add_argument(
        "--group-selection",
        default="recommended",
        choices=["recommended", "custom"],
    )
    parser.add_argument(
        "--groups", default=None, help="comma-separated list used when --group-selection custom"
    )
    parser.add_argument("--questions-min", type=int, default=12)
    parser.add_argument("--self-qa", default="router-self")
    parser.add_argument("--live-codex", action="store_true")
    parser.add_argument(
        "--report-root",
        default="/Users/moon.s.june/agents-inc-local-runs",
    )
    parser.add_argument("--until-pass", action="store_true")
    parser.add_argument("--timeline", default="4 weeks")
    parser.add_argument("--compute", default="cuda", choices=["cpu", "gpu", "cuda"])
    parser.add_argument("--remote-cluster", default="yes", choices=["yes", "no"])
    parser.add_argument("--output-target", default="procedure+python-package")
    parser.add_argument("--projects-root", default=None)
    parser.add_argument("--long-run-duration-min", type=int, default=5)
    parser.add_argument("--codex-timeout-sec", type=int, default=300)
    parser.add_argument(
        "--allow-live-fallback",
        action="store_true",
        help="allow fallback when live codex step fails or times out",
    )
    parser.add_argument(
        "--codex-web-search",
        dest="codex_web_search",
        action="store_true",
        default=True,
        help="enable web search in live codex exec phase (default: enabled)",
    )
    parser.add_argument(
        "--no-codex-web-search",
        dest="codex_web_search",
        action="store_false",
        help="disable web search in live codex exec phase",
    )
    parser.add_argument("--seed", type=int, default=20260301)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        fabric_root = resolve_fabric_root(args.fabric_root)
        ensure_fabric_root_initialized(fabric_root)

        groups = None
        if args.group_selection == "custom":
            if not args.groups:
                raise FabricError("--groups is required when --group-selection custom")
            groups = [item.strip() for item in args.groups.split(",") if item.strip()]

        config = OrchestratorConfig(
            fabric_root=fabric_root,
            project_id=args.project_id,
            task=args.task,
            create_group=args.create_group,
            group_selection=args.group_selection,
            groups=groups,
            questions_min=max(12, int(args.questions_min)),
            self_qa=str(args.self_qa or "router-self"),
            live_codex=bool(args.live_codex),
            report_root=Path(args.report_root).expanduser().resolve(),
            until_pass=bool(args.until_pass),
            timeline=str(args.timeline or "4 weeks"),
            compute=str(args.compute or "cuda"),
            remote_cluster=str(args.remote_cluster or "yes"),
            output_target=str(args.output_target or "procedure+python-package"),
            projects_root=(
                Path(args.projects_root).expanduser().resolve() if args.projects_root else None
            ),
            long_run_duration_min=max(1, int(args.long_run_duration_min)),
            codex_timeout_sec=max(30, int(args.codex_timeout_sec)),
            allow_live_fallback=bool(args.allow_live_fallback),
            codex_web_search=bool(args.codex_web_search),
            seed=int(args.seed),
        )
        report = run_orchestrator_campaign(config)
        print("orchestrator campaign completed")
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
