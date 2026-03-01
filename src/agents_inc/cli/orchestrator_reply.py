from __future__ import annotations

import argparse
import json
from pathlib import Path

from agents_inc.core.config_state import default_config_path, get_projects_root
from agents_inc.core.fabric_lib import (
    ensure_fabric_root_initialized,
    resolve_fabric_root,
    slugify,
)
from agents_inc.core.orchestrator_reply import OrchestratorReplyConfig, run_orchestrator_reply
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
    return parser.parse_args()


def _resolve_project_fabric_root(args: argparse.Namespace, project_id: str) -> Path:
    if args.fabric_root:
        return resolve_fabric_root(args.fabric_root)

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
        fabric_root_raw = found.get("fabric_root")
        if isinstance(fabric_root_raw, str) and fabric_root_raw.strip():
            return Path(fabric_root_raw).expanduser().resolve()

    return resolve_fabric_root(None)


def main() -> int:
    args = parse_args()
    try:
        project_id = slugify(str(args.project_id))
        fabric_root = _resolve_project_fabric_root(args, project_id)
        ensure_fabric_root_initialized(fabric_root)
        config = OrchestratorReplyConfig(
            fabric_root=fabric_root,
            project_id=project_id,
            message=str(args.message),
            group=(
                "auto" if str(args.group or "auto") == "auto" else slugify(str(args.group or ""))
            ),
            output_dir=Path(args.output_dir).expanduser().resolve() if args.output_dir else None,
        )
        result = run_orchestrator_reply(config)
        if args.json:
            print(json.dumps(result, indent=2, sort_keys=True))
        else:
            print(f"mode: {result.get('mode')}")
            print(f"turn_dir: {result.get('turn_dir')}")
            print(f"final_answer: {result.get('final_answer_path')}")
            print(f"quality: {result.get('quality_path')}")
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
