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
from agents_inc.core.session_compaction import compact_session
from agents_inc.core.session_state import (
    default_project_index_path,
    resolve_state_project_root,
    write_checkpoint,
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
    parser.add_argument("--project-index", default=None, help="global project index path")
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

        project_root = resolve_state_project_root(fabric_root, manifest["project_id"])
        payload = {
            "schema_version": "1.0",
            "project_id": manifest["project_id"],
            "project_root": str(project_root),
            "fabric_root": str(fabric_root),
            "task": args.objective,
            "constraints": {
                "dispatch_group": group_id,
                "ttl": args.ttl,
                "multi_agent_root": multi_agent_root,
            },
            "selected_groups": manifest.get("selected_groups", []),
            "primary_group": group_id,
            "group_order_recommendation": manifest.get("selected_groups", []),
            "router_call": f"Use $research-router for project {manifest['project_id']} group {group_id}: {args.objective}.",
            "latest_artifacts": {
                "dispatch_json_out": str(Path(args.json_out).expanduser().resolve()) if args.json_out else "",
            },
            "pending_actions": [
                "Route objective through $research-router using the generated dispatch plan.",
                "Acquire/release workdir leases according to lock_plan during execution.",
            ],
            "dispatch_summary": {
                "group_id": group_id,
                "objective": args.objective,
                "phase_count": len(dispatch.get("phases", [])),
                "lock_phase_count": len(lock_plan),
            },
        }

        checkpoint_meta = write_checkpoint(
            project_root=project_root,
            project_index_path=default_project_index_path(args.project_index),
            payload=payload,
        )
        compact_session(
            project_root=project_root,
            payload={
                **payload,
                "latest_checkpoint_id": str(checkpoint_meta["checkpoint_id"]),
                "latest_checkpoint_path": str(checkpoint_meta["checkpoint_path"]),
            },
            selected_groups=[str(group_id) for group_id in manifest.get("selected_groups", [])],
        )

        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
