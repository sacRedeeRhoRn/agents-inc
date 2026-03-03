from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List

from agents_inc.core.fabric_lib import (
    ensure_fabric_root_initialized,
    load_group_catalog,
    resolve_fabric_root,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="List employable groups")
    parser.add_argument(
        "--fabric-root",
        default=None,
        help="path to fabric root (default: current directory)",
    )
    parser.add_argument("--json", action="store_true", help="emit JSON output")
    return parser.parse_args()


def _rows(catalog: Dict[str, dict]) -> List[dict]:
    rows: List[dict] = []
    for index, group_id in enumerate(sorted(catalog.keys()), start=1):
        rows.append({"index": index, "group_id": group_id})
    return rows


def _print_rows(rows: List[dict]) -> None:
    for row in rows:
        print(f"{row['index']}. {row['group_id']}")


def main() -> int:
    args = parse_args()
    try:
        fabric_root: Path = resolve_fabric_root(args.fabric_root)
        ensure_fabric_root_initialized(fabric_root)
        rows = _rows(load_group_catalog(fabric_root))
        if args.json:
            print(json.dumps({"count": len(rows), "groups": rows}, indent=2, sort_keys=True))
        else:
            _print_rows(rows)
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
