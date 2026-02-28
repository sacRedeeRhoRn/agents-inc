from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from agents_inc.core.fabric_lib import (
    FabricError,
    ensure_fabric_root_initialized,
    ensure_json_serializable,
    load_project_manifest,
    package_root,
    read_text,
    resolve_fabric_root,
    slugify,
    suggest_groups,
    write_text,
)


def _ask(prompt: str, default: str = "") -> str:
    label = f"{prompt}"
    if default:
        label += f" [{default}]"
    label += ": "
    value = input(label).strip()
    return value or default


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Interactive intake and project bootstrap for agents-inc")
    parser.add_argument("--fabric-root", default=None, help="path to fabric root")
    parser.add_argument("--project-root", default=None, help="default long-term project root path")
    parser.add_argument("--project-id", default=None)
    parser.add_argument("--task", default=None)
    parser.add_argument("--timeline", default=None)
    parser.add_argument("--compute", default=None, choices=["cpu", "gpu", "cuda"])
    parser.add_argument("--remote-cluster", default=None, choices=["yes", "no"])
    parser.add_argument("--output-target", default=None)
    parser.add_argument("--non-interactive", action="store_true", help="require all prompt fields via args")
    parser.add_argument("--target-skill-dir", default=None)
    return parser.parse_args()


def run_cmd(cmd: list[str], env: dict) -> None:
    proc = subprocess.run(cmd, text=True, capture_output=True, env=env)
    if proc.returncode != 0:
        raise FabricError(
            "command failed: {0}\nstdout:\n{1}\nstderr:\n{2}".format(
                " ".join(cmd), proc.stdout.strip(), proc.stderr.strip()
            )
        )


def main() -> int:
    args = parse_args()
    try:
        fabric_root = resolve_fabric_root(args.fabric_root)
        ensure_fabric_root_initialized(fabric_root)

        if args.non_interactive:
            missing = [
                key
                for key, value in {
                    "task": args.task,
                    "timeline": args.timeline,
                    "compute": args.compute,
                    "remote_cluster": args.remote_cluster,
                    "output_target": args.output_target,
                }.items()
                if not value
            ]
            if missing:
                raise FabricError("missing required args in non-interactive mode: " + ", ".join(missing))
            task = args.task or ""
            timeline = args.timeline or ""
            compute = args.compute or "cpu"
            remote_cluster = args.remote_cluster or "no"
            output_target = args.output_target or "report"
        else:
            print("agents-inc intake wizard")
            task = args.task or _ask("What task do you want to start")
            timeline = args.timeline or _ask("Timeline", "2 weeks")
            compute = args.compute or _ask("Compute requirement (cpu/gpu/cuda)", "cpu").lower()
            remote_cluster = args.remote_cluster or _ask("Remote cluster over SSH? (yes/no)", "yes").lower()
            output_target = args.output_target or _ask("Output target", "technical report")

        project_id = slugify(args.project_id or task)
        project_root = Path(args.project_root).expanduser().resolve() if args.project_root else (Path.home() / "codex-projects" / project_id)
        project_root.mkdir(parents=True, exist_ok=True)

        project_fabric_root = project_root / "agent_group_fabric"
        ensure_fabric_root_initialized(project_fabric_root)

        groups, rationale = suggest_groups(task, compute, remote_cluster, output_target)
        group_csv = ",".join(groups)

        cmd_env = os.environ.copy()
        src_root = str(package_root().parents[1])
        current_path = cmd_env.get("PYTHONPATH", "")
        cmd_env["PYTHONPATH"] = f"{src_root}:{current_path}" if current_path else src_root

        new_project_cmd = [
            sys.executable,
            "-m",
            "agents_inc.cli.new_project",
            "--fabric-root",
            str(project_fabric_root),
            "--project-id",
            project_id,
            "--groups",
            group_csv,
            "--visibility-mode",
            "group-only",
            "--audit-override",
            "--force",
        ]
        if args.target_skill_dir:
            new_project_cmd.extend(["--target-skill-dir", args.target_skill_dir])

        run_cmd(new_project_cmd, env=cmd_env)

        install_cmd = [
            sys.executable,
            "-m",
            "agents_inc.cli.install_skills",
            "--fabric-root",
            str(project_fabric_root),
            "--project-id",
            project_id,
            "--sync",
        ]
        if args.target_skill_dir:
            install_cmd.extend(["--target", args.target_skill_dir])
        run_cmd(install_cmd, env=cmd_env)

        _, manifest = load_project_manifest(project_fabric_root, project_id)

        primary_group = groups[0]
        router_call = (
            f"Use $research-router for project {project_id} group {primary_group}: {task}."
        )

        kickoff_md = "\n".join(
            [
                f"# Kickoff - {project_id}",
                "",
                "## Task",
                task,
                "",
                "## Constraints",
                f"- timeline: {timeline}",
                f"- compute: {compute}",
                f"- remote_cluster: {remote_cluster}",
                f"- output_target: {output_target}",
                "",
                "## Suggested Groups",
                *[f"- {g}" for g in groups],
                "",
                "## Rationale",
                *[f"- {r}" for r in rationale],
                "",
                "## Connector Guidance",
                "- user <-> head-controller: objective refinement and acceptance",
                "- head-controller <-> specialists: internal execution and cross-checking",
                "- specialist artifacts stay internal by default; only exposed outputs are surfaced",
                "",
                "## Router Call",
                f"`{router_call}`",
            ]
        )

        write_text(project_root / "kickoff.md", kickoff_md + "\n")
        write_text(project_root / "router-call.txt", router_call + "\n")
        write_text(project_root / "project-manifest.yaml", read_text(project_fabric_root / "generated" / "projects" / project_id / "manifest.yaml"))

        summary = {
            "project_id": project_id,
            "project_root": project_root,
            "fabric_root": project_fabric_root,
            "selected_groups": groups,
            "rationale": rationale,
            "router_call": router_call,
            "artifacts": {
                "kickoff": project_root / "kickoff.md",
                "router_call": project_root / "router-call.txt",
                "project_manifest": project_root / "project-manifest.yaml",
            },
            "visibility": manifest.get("visibility", {}),
            "next_actions": [
                "Paste router-call.txt into the Codex session.",
                "Use --audit in install command only when specialist-level inspection is required.",
            ],
        }

        print(json.dumps(ensure_json_serializable(summary), indent=2, sort_keys=True))
        print("\n---\n")
        print(kickoff_md)
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
