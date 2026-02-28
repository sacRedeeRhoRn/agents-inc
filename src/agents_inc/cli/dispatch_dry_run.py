from __future__ import annotations

import argparse
import json
from pathlib import Path

from agents_inc.core.fabric_lib import (
    FabricError,
    build_dispatch_plan,
    ensure_fabric_root_initialized,
    load_project_manifest,
    load_yaml,
    resolve_fabric_root,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Dry-run deterministic dispatch plan for project/group objective")
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--group", required=True, help="group_id")
    parser.add_argument("--objective", required=True)
    parser.add_argument("--fabric-root", default=None, help="path to fabric root")
    parser.add_argument("--json-out", default=None, help="optional path for output json")
    parser.add_argument(
        "--multi-agent-cli",
        default="python3 multi_agent_dirs/cli.py",
        help="command prefix to multi_agent_dirs cli",
    )
    parser.add_argument(
        "--multi-agent-root",
        default=None,
        help="workspace root argument for multi_agent_dirs (defaults to fabric root parent)",
    )
    parser.add_argument("--ttl", type=int, default=900)
    return parser.parse_args()


def make_lock_commands(
    project_id: str,
    group_id: str,
    agent_id: str,
    ttl: int,
    multi_agent_cli: str,
    multi_agent_root: str,
) -> dict:
    workdir = "generated/projects/{0}/work/{1}/{2}".format(project_id, group_id, agent_id)
    base = f"{multi_agent_cli} --root {multi_agent_root}"
    return {
        "workdir": workdir,
        "acquire": "{0} acquire {1} {2} --ttl {3}".format(base, agent_id, workdir, ttl),
        "heartbeat": "{0} heartbeat <lease_token> --ttl {1}".format(base, ttl),
        "release": "{0} release {1} {2}".format(base, agent_id, workdir),
    }


def main() -> int:
    args = parse_args()
    try:
        fabric_root = resolve_fabric_root(args.fabric_root)
        ensure_fabric_root_initialized(fabric_root)
        project_dir, manifest = load_project_manifest(fabric_root, args.project_id)

        group_id = args.group
        group_entry = manifest.get("groups", {}).get(group_id)
        if not group_entry:
            raise FabricError(f"group '{group_id}' is not part of project '{manifest['project_id']}'")

        group_manifest_path = project_dir / group_entry["manifest_path"]
        group_manifest = load_yaml(group_manifest_path)
        if not isinstance(group_manifest, dict):
            raise FabricError(f"invalid group manifest: {group_manifest_path}")

        dispatch = build_dispatch_plan(manifest["project_id"], group_id, args.objective, group_manifest)

        multi_agent_root = args.multi_agent_root or str(fabric_root.parent)
        lock_plan = []
        for phase in dispatch["phases"]:
            phase_locks = []
            for task in phase["tasks"]:
                phase_locks.append(
                    make_lock_commands(
                        manifest["project_id"],
                        group_id,
                        task["agent_id"],
                        args.ttl,
                        args.multi_agent_cli,
                        multi_agent_root,
                    )
                )
            lock_plan.append({"phase_id": phase["phase_id"], "locks": phase_locks})

        dispatch["lock_plan"] = lock_plan

        text = json.dumps(dispatch, indent=2, sort_keys=True)
        print(text)
        if args.json_out:
            out_path = Path(args.json_out)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(text + "\n", encoding="utf-8")
            print(f"written: {out_path}")

        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
