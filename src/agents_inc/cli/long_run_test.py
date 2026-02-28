from __future__ import annotations

import argparse
from pathlib import Path

from agents_inc.core.fabric_lib import FabricError, ensure_fabric_root_initialized, load_group_catalog, resolve_fabric_root, slugify
from agents_inc.core.long_run import CANONICAL_TASK, FULL_GROUPS, LongRunConfig, run_long_validation


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Long-run full-group interaction and isolation validator")
    parser.add_argument("--fabric-root", default=None, help="path to fabric root")
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--task", default=CANONICAL_TASK)
    parser.add_argument("--groups", default="all", help="'all' or comma-separated group ids")
    parser.add_argument("--duration-min", type=int, default=75)
    parser.add_argument("--strict-isolation", default="hard-fail", choices=["hard-fail"])
    parser.add_argument("--run-mode", default="local-sim", choices=["local-sim"])
    parser.add_argument("--seed", type=int, default=20260301)
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--project-index", default=None, help="global project index path for checkpoints")
    parser.add_argument("--audit", action="store_true", help="also install skills in audit mode for run diagnostics")
    parser.add_argument("--conflict-rate", type=float, default=0.1)
    parser.add_argument("--max-retries", type=int, default=3)
    parser.add_argument("--retry-backoff-ms", type=int, default=10)
    parser.add_argument("--ttl", type=int, default=120)

    parser.add_argument("--inject-isolation-violation", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--inject-lease-deadlock", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--inject-gate-expose-failure", action="store_true", help=argparse.SUPPRESS)
    return parser.parse_args()


def _select_groups(groups_arg: str, fabric_root: Path) -> list[str]:
    if groups_arg.strip().lower() == "all":
        return list(FULL_GROUPS)
    groups = [slugify(x) for x in groups_arg.split(",") if x.strip()]
    if not groups:
        raise FabricError("--groups must be 'all' or comma-separated group ids")

    catalog = load_group_catalog(fabric_root)
    unknown = [g for g in groups if g not in catalog]
    if unknown:
        raise FabricError("unknown groups: " + ", ".join(unknown))
    return groups


def main() -> int:
    args = parse_args()
    try:
        fabric_root = resolve_fabric_root(args.fabric_root)
        ensure_fabric_root_initialized(fabric_root)

        groups = _select_groups(args.groups, fabric_root)

        config = LongRunConfig(
            fabric_root=fabric_root,
            project_id=slugify(args.project_id),
            task=args.task,
            groups=groups,
            duration_min=int(args.duration_min),
            strict_isolation=args.strict_isolation,
            run_mode=args.run_mode,
            seed=int(args.seed),
            output_dir=Path(args.output_dir).expanduser().resolve() if args.output_dir else None,
            project_index_path=Path(args.project_index).expanduser().resolve() if args.project_index else None,
            audit=bool(args.audit),
            conflict_rate=float(args.conflict_rate),
            max_retries=int(args.max_retries),
            retry_backoff_ms=int(args.retry_backoff_ms),
            ttl=int(args.ttl),
            inject_isolation_violation=bool(args.inject_isolation_violation),
            inject_lease_deadlock=bool(args.inject_lease_deadlock),
            inject_gate_expose_failure=bool(args.inject_gate_expose_failure),
        )

        exit_code, report = run_long_validation(config)
        print("long-run report:")
        print(f"- exit_code: {exit_code}")
        print(f"- exit_reason: {report.get('exit_reason', '')}")
        print(f"- output_dir: {report.get('output_dir', '')}")
        print(f"- coverage_percent: {report.get('interaction', {}).get('coverage_percent', 0)}")
        print(f"- isolation_violations: {report.get('isolation', {}).get('violation_count', 0)}")
        return int(exit_code)
    except Exception as exc:  # noqa: BLE001
        print(f"error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
