from __future__ import annotations

import argparse
import json
from pathlib import Path

from agents_inc.core.fabric_lib import (
    ensure_fabric_root_initialized,
    resolve_fabric_root,
    slugify,
)
from agents_inc.core.orchestrator_reply import OrchestratorReplyConfig, run_orchestrator_reply


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
    parser.add_argument("--json", action="store_true", help="emit JSON result")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        fabric_root = resolve_fabric_root(args.fabric_root)
        ensure_fabric_root_initialized(fabric_root)
        config = OrchestratorReplyConfig(
            fabric_root=fabric_root,
            project_id=slugify(str(args.project_id)),
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
