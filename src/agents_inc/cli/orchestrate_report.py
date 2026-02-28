from __future__ import annotations

import argparse
import json
from pathlib import Path

from agents_inc.core.orchestrator_campaign import render_report_from_run_dir


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Regenerate orchestrator report from run directory"
    )
    parser.add_argument("--run-dir", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        run_dir = Path(args.run_dir).expanduser().resolve()
        report = render_report_from_run_dir(run_dir)
        print("orchestrate report regenerated")
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
