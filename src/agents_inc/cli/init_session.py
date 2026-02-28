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
    now_iso,
    package_root,
    read_text,
    resolve_fabric_root,
    slugify,
    suggest_groups,
    write_text,
)
from agents_inc.core.session_state import (
    default_project_index_path,
    find_resume_project,
    load_checkpoint,
    write_checkpoint,
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
    parser.add_argument("--mode", default="ask", choices=["ask", "new", "resume"])
    parser.add_argument("--resume-project-id", default=None)
    parser.add_argument("--resume-checkpoint", default="latest")
    parser.add_argument("--project-index", default=None, help="global project index path")
    parser.add_argument(
        "--overwrite-existing",
        action="store_true",
        help="allow destructive re-generation when project already exists",
    )
    return parser.parse_args()


def run_cmd(cmd: list[str], env: dict) -> None:
    proc = subprocess.run(cmd, text=True, capture_output=True, env=env)
    if proc.returncode != 0:
        raise FabricError(
            "command failed: {0}\nstdout:\n{1}\nstderr:\n{2}".format(
                " ".join(cmd), proc.stdout.strip(), proc.stderr.strip()
            )
        )


def _ask_mode(default: str = "new") -> str:
    while True:
        value = _ask("Start mode (new/resume)", default).strip().lower()
        if value in {"new", "resume"}:
            return value
        print("Please enter 'new' or 'resume'.")


def _ask_existing_project_action() -> str:
    while True:
        value = _ask("Project exists. Action (resume/overwrite/cancel)", "resume").strip().lower()
        if value in {"resume", "overwrite", "cancel"}:
            return value
        print("Please enter 'resume', 'overwrite', or 'cancel'.")


def _build_long_run_command(fabric_root: Path, project_id: str, task: str) -> str:
    return "\n".join(
        [
            "agents-inc-long-run-test \\",
            f"  --fabric-root {fabric_root} \\",
            f"  --project-id {project_id} \\",
            f"  --task \"{task}\" \\",
            "  --groups all \\",
            "  --duration-min 75 \\",
            "  --strict-isolation hard-fail \\",
            "  --run-mode local-sim \\",
            "  --seed 20260301",
        ]
    )


def _write_common_project_artifacts(
    *,
    project_root: Path,
    router_call: str,
    long_run_command: str,
    kickoff_md: str,
    project_manifest_src: Path,
) -> None:
    write_text(project_root / "kickoff.md", kickoff_md + "\n")
    write_text(project_root / "router-call.txt", router_call + "\n")
    write_text(project_root / "long-run-command.sh", long_run_command + "\n")
    write_text(project_root / "project-manifest.yaml", read_text(project_manifest_src))


def _resume_summary(
    *,
    project_id: str,
    project_root: Path,
    project_fabric_root: Path,
    groups: list[str],
    router_call: str,
    checkpoint_id: str,
    artifacts: dict,
    visibility: dict,
    project_index: Path,
) -> dict:
    return {
        "mode": "resume",
        "project_id": project_id,
        "project_root": project_root,
        "fabric_root": project_fabric_root,
        "selected_groups": groups,
        "router_call": router_call,
        "resumed_checkpoint": checkpoint_id,
        "project_index": project_index,
        "artifacts": artifacts,
        "visibility": visibility,
        "next_actions": [
            "Paste router-call.txt into the Codex session.",
            "Run long-run-command.sh to validate all-group interaction and isolation.",
            "Use agents-inc-dispatch-dry-run to continue a specific group objective.",
        ],
    }


def _load_checkpoint_project_context(
    *,
    project_root: Path,
    project_fabric_root: Path,
    project_id: str,
    checkpoint_ref: str,
    task_override: str | None,
) -> tuple[dict, list[str], str, str]:
    checkpoint = load_checkpoint(project_root, checkpoint_ref)
    _, manifest = load_project_manifest(project_fabric_root, project_id)
    visibility = manifest.get("visibility", {})

    selected_groups = checkpoint.get("selected_groups")
    if not isinstance(selected_groups, list) or not selected_groups:
        selected_groups = manifest.get("selected_groups", [])
    selected_groups = [str(item) for item in selected_groups]

    task = str(task_override or checkpoint.get("task") or "Continue orchestrator workflow")
    primary_group = str(
        checkpoint.get("primary_group")
        or (selected_groups[0] if selected_groups else "material-scientist")
    )
    router_call = str(
        checkpoint.get("router_call")
        or f"Use $research-router for project {project_id} group {primary_group}: {task}."
    )
    return visibility, selected_groups, task, router_call


def _build_resume_kickoff(
    *,
    project_id: str,
    task: str,
    groups: list[str],
    checkpoint_id: str,
    router_call: str,
    long_run_command: str,
) -> str:
    return "\n".join(
        [
            f"# Kickoff (Resumed) - {project_id}",
            "",
            "## Task",
            task,
            "",
            "## Resume Context",
            f"- resumed checkpoint: {checkpoint_id}",
            f"- resumed at: {now_iso()}",
            "",
            "## Active Groups",
            *[f"- {group_id}" for group_id in groups],
            "",
            "## Connector Guidance",
            "- user <-> head-controller: objective refinement and acceptance",
            "- head-controller <-> specialists: internal execution and cross-checking",
            "- specialist artifacts stay internal by default; only exposed outputs are surfaced",
            "",
            "## Router Call",
            f"`{router_call}`",
            "",
            "## Long-Run Validation",
            "Run this to re-validate all-group interaction with strict artifact isolation:",
            "```bash",
            long_run_command,
            "```",
        ]
    )


def _build_new_kickoff(
    *,
    project_id: str,
    task: str,
    timeline: str,
    compute: str,
    remote_cluster: str,
    output_target: str,
    groups: list[str],
    rationale: list[str],
    router_call: str,
    long_run_command: str,
) -> str:
    return "\n".join(
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
            "",
            "## Long-Run Validation",
            "Run this after initial setup to verify all groups interact correctly with strict artifact isolation:",
            "```bash",
            long_run_command,
            "```",
        ]
    )


def _write_checkpoint(
    *,
    args: argparse.Namespace,
    project_root: Path,
    project_fabric_root: Path,
    project_id: str,
    task: str,
    constraints: dict,
    selected_groups: list[str],
    router_call: str,
    long_run_artifact: Path,
    kickoff_artifact: Path,
    router_artifact: Path,
    project_manifest_artifact: Path,
    pending_actions: list[str],
    quality_summary: dict | None = None,
    isolation_summary: dict | None = None,
) -> dict:
    project_index = default_project_index_path(args.project_index)
    payload = {
        "schema_version": "1.0",
        "project_id": project_id,
        "project_root": str(project_root),
        "fabric_root": str(project_fabric_root),
        "task": task,
        "constraints": constraints,
        "selected_groups": selected_groups,
        "primary_group": selected_groups[0] if selected_groups else "",
        "group_order_recommendation": selected_groups,
        "router_call": router_call,
        "latest_artifacts": {
            "kickoff": str(kickoff_artifact),
            "router_call": str(router_artifact),
            "long_run_command": str(long_run_artifact),
            "project_manifest": str(project_manifest_artifact),
        },
        "pending_actions": pending_actions,
    }
    if quality_summary is not None:
        payload["quality_summary"] = quality_summary
    if isolation_summary is not None:
        payload["isolation_summary"] = isolation_summary
    return write_checkpoint(
        project_root=project_root,
        payload=payload,
        project_index_path=project_index,
    )


def _run_resume_mode(args: argparse.Namespace, requested_project_id: str | None = None) -> dict:
    project_index = default_project_index_path(args.project_index)
    resume_project_id = slugify(requested_project_id) if requested_project_id else None
    if not resume_project_id and args.resume_project_id:
        resume_project_id = slugify(args.resume_project_id)
    if not resume_project_id and args.project_id:
        resume_project_id = slugify(args.project_id)
    if not resume_project_id and not args.non_interactive:
        entered = _ask("Project id to resume (leave blank for auto-detect)", "")
        if entered.strip():
            resume_project_id = slugify(entered)

    found = find_resume_project(
        index_path=project_index,
        project_id=resume_project_id,
        fallback_scan_root=Path.home() / "codex-projects",
    )
    if not found:
        label = resume_project_id or "<unspecified>"
        raise FabricError(
            "could not locate resumable project '{0}'. Use --project-id/--resume-project-id and ensure project exists under ~/codex-projects".format(
                label
            )
        )

    project_id = str(found["project_id"])
    project_root = Path(str(found["project_root"])).expanduser().resolve()
    project_fabric_root = Path(str(found.get("fabric_root") or (project_root / "agent_group_fabric"))).expanduser().resolve()
    ensure_fabric_root_initialized(project_fabric_root)

    visibility, groups, task, router_call = _load_checkpoint_project_context(
        project_root=project_root,
        project_fabric_root=project_fabric_root,
        project_id=project_id,
        checkpoint_ref=str(args.resume_checkpoint or "latest"),
        task_override=args.task,
    )
    long_run_command = _build_long_run_command(project_fabric_root, project_id, task)
    checkpoint_id = str(args.resume_checkpoint or "latest")
    if checkpoint_id == "latest":
        checkpoint_id = str(load_checkpoint(project_root, "latest").get("checkpoint_id", "latest"))

    kickoff_md = _build_resume_kickoff(
        project_id=project_id,
        task=task,
        groups=groups,
        checkpoint_id=checkpoint_id,
        router_call=router_call,
        long_run_command=long_run_command,
    )

    manifest_path = project_fabric_root / "generated" / "projects" / project_id / "manifest.yaml"
    _write_common_project_artifacts(
        project_root=project_root,
        router_call=router_call,
        long_run_command=long_run_command,
        kickoff_md=kickoff_md,
        project_manifest_src=manifest_path,
    )

    checkpoint_meta = _write_checkpoint(
        args=args,
        project_root=project_root,
        project_fabric_root=project_fabric_root,
        project_id=project_id,
        task=task,
        constraints={"mode": "resume"},
        selected_groups=groups,
        router_call=router_call,
        long_run_artifact=project_root / "long-run-command.sh",
        kickoff_artifact=project_root / "kickoff.md",
        router_artifact=project_root / "router-call.txt",
        project_manifest_artifact=project_root / "project-manifest.yaml",
        pending_actions=[
            "Paste router-call.txt into the Codex session.",
            "Run long-run-command.sh to validate all-group interaction and isolation.",
            "Continue with agents-inc-dispatch-dry-run for focused group objectives.",
        ],
    )

    summary = _resume_summary(
        project_id=project_id,
        project_root=project_root,
        project_fabric_root=project_fabric_root,
        groups=groups,
        router_call=router_call,
        checkpoint_id=str(checkpoint_meta["checkpoint_id"]),
        artifacts={
            "kickoff": project_root / "kickoff.md",
            "router_call": project_root / "router-call.txt",
            "long_run_command": project_root / "long-run-command.sh",
            "project_manifest": project_root / "project-manifest.yaml",
            "checkpoint": checkpoint_meta["checkpoint_path"],
            "project_index": checkpoint_meta["project_index_path"],
        },
        visibility=visibility if isinstance(visibility, dict) else {},
        project_index=project_index,
    )

    print(json.dumps(ensure_json_serializable(summary), indent=2, sort_keys=True))
    print("\n---\n")
    print(kickoff_md)
    return summary


def main() -> int:
    args = parse_args()
    try:
        root_hint = resolve_fabric_root(args.fabric_root)
        ensure_fabric_root_initialized(root_hint)

        mode = str(args.mode)
        if args.non_interactive and mode == "ask":
            proposed_id = args.resume_project_id or args.project_id
            if proposed_id:
                candidate_project_root = (
                    Path(args.project_root).expanduser().resolve()
                    if args.project_root
                    else (Path.home() / "codex-projects" / slugify(proposed_id))
                )
                if (candidate_project_root / "agent_group_fabric" / "generated" / "projects" / slugify(proposed_id) / "manifest.yaml").exists():
                    mode = "resume"
                else:
                    mode = "new"
            else:
                mode = "new"

        if not args.non_interactive:
            print("agents-inc intake wizard")
            if mode == "ask":
                mode = _ask_mode("new")

        if mode == "resume":
            _run_resume_mode(args)
            return 0

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
            task = args.task or _ask("What task do you want to start")
            timeline = args.timeline or _ask("Timeline", "2 weeks")
            compute = args.compute or _ask("Compute requirement (cpu/gpu/cuda)", "cpu").lower()
            remote_cluster = args.remote_cluster or _ask("Remote cluster over SSH? (yes/no)", "yes").lower()
            output_target = args.output_target or _ask("Output target", "technical report")

        project_id = slugify(args.project_id or task)
        project_root = (
            Path(args.project_root).expanduser().resolve()
            if args.project_root
            else (Path.home() / "codex-projects" / project_id)
        )
        project_root.mkdir(parents=True, exist_ok=True)

        project_fabric_root = project_root / "agent_group_fabric"
        ensure_fabric_root_initialized(project_fabric_root)

        existing_manifest = project_fabric_root / "generated" / "projects" / project_id / "manifest.yaml"
        if existing_manifest.exists() and not args.overwrite_existing:
            if args.non_interactive:
                raise FabricError(
                    "project already exists and overwrite is disabled. Use --mode resume or pass --overwrite-existing."
                )
            action = _ask_existing_project_action()
            if action == "cancel":
                raise FabricError("cancelled by user")
            if action == "resume":
                _run_resume_mode(args, requested_project_id=project_id)
                return 0
            args.overwrite_existing = True

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
        ]
        if args.overwrite_existing:
            new_project_cmd.append("--force")
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
        router_call = f"Use $research-router for project {project_id} group {primary_group}: {task}."
        long_run_command = _build_long_run_command(project_fabric_root, project_id, task)
        kickoff_md = _build_new_kickoff(
            project_id=project_id,
            task=task,
            timeline=timeline,
            compute=compute,
            remote_cluster=remote_cluster,
            output_target=output_target,
            groups=groups,
            rationale=rationale,
            router_call=router_call,
            long_run_command=long_run_command,
        )
        manifest_src = project_fabric_root / "generated" / "projects" / project_id / "manifest.yaml"
        _write_common_project_artifacts(
            project_root=project_root,
            router_call=router_call,
            long_run_command=long_run_command,
            kickoff_md=kickoff_md,
            project_manifest_src=manifest_src,
        )

        checkpoint_meta = _write_checkpoint(
            args=args,
            project_root=project_root,
            project_fabric_root=project_fabric_root,
            project_id=project_id,
            task=task,
            constraints={
                "timeline": timeline,
                "compute": compute,
                "remote_cluster": remote_cluster,
                "output_target": output_target,
            },
            selected_groups=groups,
            router_call=router_call,
            long_run_artifact=project_root / "long-run-command.sh",
            kickoff_artifact=project_root / "kickoff.md",
            router_artifact=project_root / "router-call.txt",
            project_manifest_artifact=project_root / "project-manifest.yaml",
            pending_actions=[
                "Paste router-call.txt into the Codex session.",
                "Run long-run-command.sh to validate all-group interaction and isolation.",
                "Use --audit in install command only when specialist-level inspection is required.",
            ],
        )

        summary = {
            "mode": "new",
            "project_id": project_id,
            "project_root": project_root,
            "fabric_root": project_fabric_root,
            "selected_groups": groups,
            "rationale": rationale,
            "router_call": router_call,
            "artifacts": {
                "kickoff": project_root / "kickoff.md",
                "router_call": project_root / "router-call.txt",
                "long_run_command": project_root / "long-run-command.sh",
                "project_manifest": project_root / "project-manifest.yaml",
                "checkpoint": checkpoint_meta["checkpoint_path"],
                "project_index": checkpoint_meta["project_index_path"],
            },
            "visibility": manifest.get("visibility", {}),
            "next_actions": [
                "Paste router-call.txt into the Codex session.",
                "Run long-run-command.sh to validate all-group interaction and isolation.",
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
