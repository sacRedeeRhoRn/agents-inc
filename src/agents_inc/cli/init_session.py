from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path
from typing import Optional

from agents_inc.cli.install_skills import install_project_skills
from agents_inc.core.codex_home import (
    ensure_project_codex_home,
    ensure_skill_activation_state,
    save_skill_activation_state,
    skill_activation_state_path,
)
from agents_inc.core.config_state import (
    default_config_path,
    get_projects_root,
    set_projects_root,
)
from agents_inc.core.context_state import save_global_context
from agents_inc.core.fabric_lib import (
    FabricError,
    ensure_fabric_root_initialized,
    ensure_json_serializable,
    load_project_manifest,
    now_iso,
    read_text,
    resolve_fabric_root,
    slugify,
    write_text,
)
from agents_inc.core.response_policy import ensure_response_policy, upsert_specialist_sessions
from agents_inc.core.session_compaction import compact_session, load_compacted
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
    parser = argparse.ArgumentParser(
        description="Interactive intake and project bootstrap for agents-inc"
    )
    parser.add_argument("--fabric-root", default=None, help="path to fabric root")
    parser.add_argument("--project-root", default=None, help="explicit project directory path")
    parser.add_argument(
        "--projects-root", default=None, help="base directory containing all project roots"
    )
    parser.add_argument(
        "--config-path", default=None, help="config file path (default ~/.agents-inc/config.yaml)"
    )
    parser.add_argument("--project-id", default=None)
    parser.add_argument("--groups", default=None, help="comma-separated group ids to activate")
    parser.add_argument("--task", default=None)
    parser.add_argument("--timeline", default=None)
    parser.add_argument("--compute", default=None, choices=["cpu", "gpu", "cuda"])
    parser.add_argument("--remote-cluster", default=None, choices=["yes", "no"])
    parser.add_argument("--output-target", default=None)
    parser.add_argument(
        "--non-interactive", action="store_true", help="require all prompt fields via args"
    )
    parser.add_argument("--target-skill-dir", default=None)
    parser.add_argument("--mode", default="ask", choices=["ask", "new", "resume"])
    parser.add_argument("--resume-project-id", default=None)
    parser.add_argument("--resume-checkpoint", default="latest")
    parser.add_argument("--resume-mode", default="auto", choices=["auto", "compact", "rehydrate"])
    parser.add_argument("--project-index", default=None, help="global project index path")
    parser.add_argument(
        "--no-launch",
        action="store_true",
        help="prepare bootstrap state only and skip Codex launch",
    )
    parser.add_argument(
        "--overwrite-existing",
        action="store_true",
        help="allow destructive re-generation when project already exists",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="emit machine-readable JSON output",
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


def _parse_groups(value: str) -> list[str]:
    out: list[str] = []
    for raw in value.split(","):
        gid = slugify(raw)
        if gid and gid not in out:
            out.append(gid)
    return out


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


def _build_bootstrap_prompt(*, fabric_root: Path, projects_root: Path, config_path: Path) -> str:
    return "\n".join(
        [
            "Bootstrap agents-inc for first use.",
            f"Workspace root: {fabric_root}",
            f"Projects root default: {projects_root}",
            f"Config file: {config_path}",
            "",
            "Explain this startup sequence to the user in concise steps:",
            "1) List employable groups with `agents-inc group-list`.",
            "2) Create a project with `agents-inc create <project-id>`.",
            "3) Save progress with `agents-inc save <project-id>`.",
            "4) Resume with `agents-inc resume <project-id>`.",
            "5) Manage groups with `agents-inc project-groups`.",
            "",
            "When the user asks a normal question, answer directly.",
            "When the user starts input with `/agents-inc`, route through agents-inc orchestration workflow.",
        ]
    )


def _print_bootstrap_human(summary: dict, *, launch: str) -> None:
    print("agents-inc init complete.")
    print("")
    print("workspace:")
    print(f"- fabric root: {summary['fabric_root']}")
    print(f"- projects root: {summary['projects_root']}")
    print(f"- config: {summary['config_path']}")
    print(f"- bootstrap state: {summary['bootstrap_state']}")
    print("")
    print("next:")
    print("1. agents-inc group-list")
    print("2. agents-inc create <project-id>")
    print("3. agents-inc list")
    print("4. agents-inc deactivate <project-id>")
    print("5. agents-inc resume <project-id>")
    print("")
    if launch == "no-launch":
        print("codex launch skipped (--no-launch).")
    elif launch == "missing-codex":
        print("codex was not found on PATH. bootstrap is ready; launch codex manually when ready.")
    elif launch == "launching":
        print("launching codex now with the bootstrap prompt.")
    print("")
    print("tip: use `agents-inc init --json` for machine-readable output.")


def _build_long_run_command(fabric_root: Path, project_id: str, task: str) -> str:
    return "\n".join(
        [
            "agents-inc long-run \\",
            f"  --fabric-root {fabric_root} \\",
            f"  --project-id {project_id} \\",
            f'  --task "{task}" \\',
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
    resume_source: str,
    session_code: str,
    group_session_map: dict,
    skill_refresh: dict,
) -> dict:
    return {
        "mode": "resume",
        "project_id": project_id,
        "project_root": project_root,
        "fabric_root": project_fabric_root,
        "selected_groups": groups,
        "active_groups": groups,
        "router_call": router_call,
        "resumed_checkpoint": checkpoint_id,
        "resume_source": resume_source,
        "session_code": session_code,
        "group_session_map": group_session_map,
        "project_index": project_index,
        "artifacts": artifacts,
        "skill_refresh": skill_refresh,
        "visibility": visibility,
        "next_actions": [
            "Paste router-call.txt into the Codex session.",
            "Use agents-inc orchestrator-reply for strict artifact-grounded turn execution.",
            "Run long-run-command.sh to validate all-group interaction and isolation.",
            "Use agents-inc dispatch to continue a specific group objective.",
        ],
    }


def _build_resume_kickoff(
    *,
    project_id: str,
    task: str,
    groups: list[str],
    checkpoint_id: str,
    router_call: str,
    long_run_command: str,
    resume_source: str,
    session_code: str,
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
            f"- resume source: {resume_source}",
            f"- session code: {session_code}",
            f"- resumed at: {now_iso()}",
            "",
            "## Active Groups",
            *[f"- {group_id}" for group_id in groups],
            "",
            "## Connector Guidance",
            "- user <-> head-controller: objective refinement and acceptance",
            "- head-controller <-> specialists: internal execution and cross-checking",
            "- specialist artifacts stay internal by default; only exposed outputs are surfaced",
            "- each project uses isolated CODEX_HOME under `.agents-inc/codex-home`",
            "- specialist skills are group-selective; activate explicitly via `agents-inc skills activate --project-id {0} --groups <group-id> --specialists`".format(
                project_id
            ),
            "- requests starting with `[non-group]` run concise direct reasoning without delegation",
            "- all other requests run group-routed strict artifact-grounded orchestration",
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
    projects_root: Path,
    session_code: str,
) -> str:
    return "\n".join(
        [
            f"# Kickoff - {project_id}",
            "",
            "## Task",
            task,
            "",
            "## Workspace",
            f"- projects_root: {projects_root}",
            f"- session_code: {session_code}",
            "",
            "## Constraints",
            f"- timeline: {timeline}",
            f"- compute: {compute}",
            f"- remote_cluster: {remote_cluster}",
            f"- output_target: {output_target}",
            "",
            "## Active Groups",
            *[f"- {g}" for g in groups],
            "",
            "## Recommendation Rationale",
            *[f"- {r}" for r in rationale],
            "",
            "## Connector Guidance",
            "- user <-> head-controller: objective refinement and acceptance",
            "- head-controller <-> specialists: internal execution and cross-checking",
            "- specialist artifacts stay internal by default; only exposed outputs are surfaced",
            "- each project uses isolated CODEX_HOME under `.agents-inc/codex-home`",
            "- specialist skills are group-selective; activate explicitly via `agents-inc skills activate --project-id {0} --groups <group-id> --specialists`".format(
                project_id
            ),
            "- requests starting with `[non-group]` run concise direct reasoning without delegation",
            "- all other requests run group-routed strict artifact-grounded orchestration",
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


def _write_session_records(
    *,
    args: argparse.Namespace,
    project_root: Path,
    project_fabric_root: Path,
    payload: dict,
) -> dict:
    checkpoint_meta = write_checkpoint(
        project_root=project_root,
        payload=payload,
        project_index_path=default_project_index_path(args.project_index),
    )
    compact_meta = compact_session(
        project_root=project_root,
        payload={
            **payload,
            "latest_checkpoint_id": str(checkpoint_meta["checkpoint_id"]),
            "latest_checkpoint_path": str(checkpoint_meta["checkpoint_path"]),
        },
        selected_groups=[str(g) for g in payload.get("selected_groups", []) if str(g).strip()],
    )
    return {
        "checkpoint": checkpoint_meta,
        "compact": compact_meta,
    }


def _build_checkpoint_payload(
    *,
    project_id: str,
    project_root: Path,
    project_fabric_root: Path,
    task: str,
    constraints: dict,
    selected_groups: list[str],
    router_call: str,
    latest_artifacts: dict,
    pending_actions: list[str],
    quality_summary: Optional[dict] = None,
    isolation_summary: Optional[dict] = None,
) -> dict:
    payload = {
        "schema_version": "3.0",
        "project_id": project_id,
        "project_root": str(project_root),
        "fabric_root": str(project_fabric_root),
        "task": task,
        "constraints": constraints,
        "selected_groups": selected_groups,
        "primary_group": selected_groups[0] if selected_groups else "",
        "group_order_recommendation": selected_groups,
        "router_call": router_call,
        "latest_artifacts": latest_artifacts,
        "pending_actions": pending_actions,
    }
    if quality_summary is not None:
        payload["quality_summary"] = quality_summary
    if isolation_summary is not None:
        payload["isolation_summary"] = isolation_summary
    return payload


def _load_from_checkpoint(
    *,
    project_root: Path,
    project_fabric_root: Path,
    project_id: str,
    checkpoint_ref: str,
    task_override: Optional[str],
) -> tuple[dict, list[str], str, str, str, dict]:
    checkpoint = load_checkpoint(project_root, checkpoint_ref)
    _, manifest = load_project_manifest(project_fabric_root, project_id)
    visibility = manifest.get("visibility", {})

    selected_groups = checkpoint.get("selected_groups")
    if not isinstance(selected_groups, list) or not selected_groups:
        selected_groups = manifest.get("selected_groups", [])
    selected_groups = [str(item) for item in selected_groups]

    task = str(task_override or checkpoint.get("task") or "Continue orchestrator workflow")
    primary_group = str(
        checkpoint.get("primary_group") or (selected_groups[0] if selected_groups else "developer")
    )
    router_call = str(
        checkpoint.get("router_call")
        or f"Use $research-router for project {project_id} group {primary_group}: {task}."
    )
    checkpoint_id = str(checkpoint.get("checkpoint_id") or checkpoint_ref)
    return visibility, selected_groups, task, router_call, checkpoint_id, checkpoint


def _load_from_compacted(
    *,
    project_root: Path,
    project_fabric_root: Path,
    project_id: str,
    compact_ref: str,
    task_override: Optional[str],
) -> tuple[dict, list[str], str, str, str, dict]:
    compact = load_compacted(project_root, compact_ref)
    _, manifest = load_project_manifest(project_fabric_root, project_id)
    visibility = manifest.get("visibility", {})

    selected_groups = compact.get("selected_groups")
    if not isinstance(selected_groups, list) or not selected_groups:
        selected_groups = manifest.get("selected_groups", [])
    selected_groups = [str(item) for item in selected_groups]

    task = str(task_override or compact.get("task") or "Continue orchestrator workflow")
    primary_group = str(
        compact.get("primary_group") or (selected_groups[0] if selected_groups else "developer")
    )
    router_call = str(
        compact.get("router_call")
        or f"Use $research-router for project {project_id} group {primary_group}: {task}."
    )
    checkpoint_id = str(
        compact.get("latest_checkpoint_id") or compact.get("compact_id") or compact_ref
    )
    return visibility, selected_groups, task, router_call, checkpoint_id, compact


def run_resume_flow(
    args: argparse.Namespace,
    *,
    requested_project_id: Optional[str] = None,
    emit_output: bool = True,
) -> dict:
    project_index = default_project_index_path(args.project_index)
    config_path = default_config_path(getattr(args, "config_path", None))
    fallback_scan_root = get_projects_root(config_path)
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
        fallback_scan_root=fallback_scan_root,
    )
    if not found:
        label = resume_project_id or "<unspecified>"
        raise FabricError(
            "could not locate resumable project '{0}'. Use --project-id/--resume-project-id and ensure project exists under configured projects root".format(
                label
            )
        )

    project_id = str(found["project_id"])
    project_root = Path(str(found["project_root"])).expanduser().resolve()
    project_fabric_root = (
        Path(str(found.get("fabric_root") or (project_root / "agent_group_fabric")))
        .expanduser()
        .resolve()
    )
    ensure_fabric_root_initialized(project_fabric_root)
    _, loaded_manifest = load_project_manifest(project_fabric_root, project_id)
    schema_version = str(loaded_manifest.get("schema_version") or "")
    if not schema_version.startswith("3."):
        raise FabricError(
            "project manifest schema_version '{0}' is not resume-compatible. "
            "Run 'agents-inc migrate-v2 --apply' and retry.".format(schema_version or "<missing>")
        )
    ensure_response_policy(project_root)

    checkpoint_ref = str(args.resume_checkpoint or "latest")
    resume_mode = str(args.resume_mode or "auto")
    resume_source = "rehydrate"

    visibility: dict
    groups: list[str]
    task: str
    router_call: str
    checkpoint_id: str
    loaded_payload: dict

    if resume_mode == "compact":
        visibility, groups, task, router_call, checkpoint_id, loaded_payload = _load_from_compacted(
            project_root=project_root,
            project_fabric_root=project_fabric_root,
            project_id=project_id,
            compact_ref=checkpoint_ref,
            task_override=args.task,
        )
        resume_source = "compact"
    elif resume_mode == "rehydrate":
        visibility, groups, task, router_call, checkpoint_id, loaded_payload = (
            _load_from_checkpoint(
                project_root=project_root,
                project_fabric_root=project_fabric_root,
                project_id=project_id,
                checkpoint_ref=checkpoint_ref,
                task_override=args.task,
            )
        )
        resume_source = "rehydrate"
    else:
        used_compact = False
        if checkpoint_ref == "latest":
            try:
                visibility, groups, task, router_call, checkpoint_id, loaded_payload = (
                    _load_from_compacted(
                        project_root=project_root,
                        project_fabric_root=project_fabric_root,
                        project_id=project_id,
                        compact_ref="latest",
                        task_override=args.task,
                    )
                )
                used_compact = True
                resume_source = "compact"
            except Exception:
                used_compact = False

        if not used_compact:
            visibility, groups, task, router_call, checkpoint_id, loaded_payload = (
                _load_from_checkpoint(
                    project_root=project_root,
                    project_fabric_root=project_fabric_root,
                    project_id=project_id,
                    checkpoint_ref=checkpoint_ref,
                    task_override=args.task,
                )
            )
            resume_source = "rehydrate"

    codex_home_state = ensure_project_codex_home(project_root, project_id=project_id)
    activation_state = ensure_skill_activation_state(
        project_root,
        default_head_groups=groups,
    )
    allowed_groups = set(groups)
    active_head_groups = [
        group_id
        for group_id in activation_state.get("active_head_groups", [])
        if group_id in allowed_groups
    ]
    if not active_head_groups:
        active_head_groups = list(groups)
    active_specialist_groups = [
        group_id
        for group_id in activation_state.get("active_specialist_groups", [])
        if group_id in allowed_groups
    ]
    activation_state = save_skill_activation_state(
        project_root,
        active_head_groups=active_head_groups,
        active_specialist_groups=active_specialist_groups,
    )
    install_result = install_project_skills(
        fabric_root=project_fabric_root,
        project_id=project_id,
        target=Path(str(codex_home_state["skills_dir"])),
        sync=True,
        head_groups=activation_state["active_head_groups"],
        specialist_groups=activation_state["active_specialist_groups"],
        include_specialists=bool(activation_state["active_specialist_groups"]),
    )

    upsert_specialist_sessions(
        project_root=project_root,
        project_fabric_root=project_fabric_root,
        project_id=project_id,
        selected_groups=groups,
    )

    long_run_command = _build_long_run_command(project_fabric_root, project_id, task)
    kickoff_md = _build_resume_kickoff(
        project_id=project_id,
        task=task,
        groups=groups,
        checkpoint_id=checkpoint_id,
        router_call=router_call,
        long_run_command=long_run_command,
        resume_source=resume_source,
        session_code=str(
            loaded_payload.get("session_code") or loaded_payload.get("compact_id") or ""
        ),
    )

    manifest_path = project_fabric_root / "generated" / "projects" / project_id / "manifest.yaml"
    _write_common_project_artifacts(
        project_root=project_root,
        router_call=router_call,
        long_run_command=long_run_command,
        kickoff_md=kickoff_md,
        project_manifest_src=manifest_path,
    )

    latest_artifacts = {
        "kickoff": str(project_root / "kickoff.md"),
        "router_call": str(project_root / "router-call.txt"),
        "long_run_command": str(project_root / "long-run-command.sh"),
        "project_manifest": str(project_root / "project-manifest.yaml"),
        "response_policy": str(project_root / ".agents-inc" / "state" / "response-policy.yaml"),
        "specialist_sessions": str(
            project_root / ".agents-inc" / "state" / "specialist-sessions.yaml"
        ),
        "codex_home_state": str(project_root / ".agents-inc" / "state" / "codex-home.yaml"),
        "skill_activation": str(skill_activation_state_path(project_root)),
        "router_skill": str(
            Path(str(codex_home_state["skills_dir"])) / "research-router" / "SKILL.md"
        ),
    }

    payload = _build_checkpoint_payload(
        project_id=project_id,
        project_root=project_root,
        project_fabric_root=project_fabric_root,
        task=task,
        constraints={"mode": "resume", "resume_mode": resume_mode, "resume_source": resume_source},
        selected_groups=groups,
        router_call=router_call,
        latest_artifacts=latest_artifacts,
        pending_actions=[
            "Paste router-call.txt into the Codex session.",
            "Use agents-inc orchestrator-reply for strict artifact-grounded group responses.",
            "Run long-run-command.sh to validate all-group interaction and isolation.",
            "Use agents-inc skills activate --project-id <id> --groups <group-id> --specialists for group-selective specialist skills.",
            "Continue with agents-inc dispatch for focused group objectives.",
        ],
    )
    records = _write_session_records(
        args=args,
        project_root=project_root,
        project_fabric_root=project_fabric_root,
        payload=payload,
    )

    summary = _resume_summary(
        project_id=project_id,
        project_root=project_root,
        project_fabric_root=project_fabric_root,
        groups=groups,
        router_call=router_call,
        checkpoint_id=str(records["checkpoint"]["checkpoint_id"]),
        artifacts={
            "kickoff": project_root / "kickoff.md",
            "router_call": project_root / "router-call.txt",
            "long_run_command": project_root / "long-run-command.sh",
            "project_manifest": project_root / "project-manifest.yaml",
            "response_policy": project_root / ".agents-inc" / "state" / "response-policy.yaml",
            "specialist_sessions": project_root
            / ".agents-inc"
            / "state"
            / "specialist-sessions.yaml",
            "codex_home_state": project_root / ".agents-inc" / "state" / "codex-home.yaml",
            "skill_activation": skill_activation_state_path(project_root),
            "router_skill": Path(str(codex_home_state["skills_dir"]))
            / "research-router"
            / "SKILL.md",
            "checkpoint": records["checkpoint"]["checkpoint_path"],
            "compact": records["compact"]["compact_path"],
            "project_index": records["checkpoint"]["project_index_path"],
        },
        visibility=visibility if isinstance(visibility, dict) else {},
        project_index=project_index,
        resume_source=resume_source,
        session_code=str(records["compact"]["session_code"]),
        group_session_map=records["compact"].get("group_session_map", {}),
        skill_refresh={
            "target": install_result.get("target", ""),
            "router_version": install_result.get("router_version", ""),
            "router_template_source": install_result.get("router_template_source", ""),
            "installed_skill_count": len(install_result.get("installed", [])),
        },
    )

    if emit_output:
        print(json.dumps(ensure_json_serializable(summary), indent=2, sort_keys=True))
        print("\n---\n")
        print(kickoff_md)
    return summary


def main() -> int:
    args = parse_args()
    try:
        fabric_root = resolve_fabric_root(args.fabric_root)
        ensure_fabric_root_initialized(fabric_root)

        config_path = default_config_path(args.config_path)
        projects_root = (
            Path(str(args.projects_root)).expanduser().resolve()
            if args.projects_root
            else get_projects_root(config_path)
        )
        set_projects_root(config_path, projects_root)
        context_project_index = (
            default_project_index_path(args.project_index)
            if args.project_index
            else default_project_index_path(str(config_path.parent / "projects" / "index.yaml"))
        )
        save_global_context(
            {
                "config_path": str(config_path),
                "project_index": str(context_project_index),
                "projects_root": str(projects_root),
                "fabric_root": str(fabric_root),
            }
        )

        bootstrap_state_path = config_path.parent / "bootstrap.yaml"
        bootstrap_payload = {
            "schema_version": "1.0",
            "initialized_at": now_iso(),
            "fabric_root": str(fabric_root),
            "projects_root": str(projects_root),
            "config_path": str(config_path),
        }
        bootstrap_state_path.parent.mkdir(parents=True, exist_ok=True)
        bootstrap_state_path.write_text(
            json.dumps(bootstrap_payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        prompt = _build_bootstrap_prompt(
            fabric_root=fabric_root,
            projects_root=projects_root,
            config_path=config_path,
        )

        summary = {
            "mode": "bootstrap",
            "fabric_root": str(fabric_root),
            "projects_root": str(projects_root),
            "config_path": str(config_path),
            "bootstrap_state": str(bootstrap_state_path),
            "launch_prompt": prompt,
        }

        if args.no_launch:
            if args.json:
                print(json.dumps(ensure_json_serializable(summary), indent=2, sort_keys=True))
            else:
                _print_bootstrap_human(summary, launch="no-launch")
            return 0

        codex_bin = shutil.which("codex")
        if not codex_bin:
            if args.json:
                print(json.dumps(ensure_json_serializable(summary), indent=2, sort_keys=True))
            else:
                _print_bootstrap_human(summary, launch="missing-codex")
            return 0

        if args.json:
            print(json.dumps(ensure_json_serializable(summary), indent=2, sort_keys=True))
            print("\n---\n")
        else:
            _print_bootstrap_human(summary, launch="launching")
        cmd = [codex_bin, "-C", str(fabric_root), prompt]
        print(f"launching: {' '.join(cmd[:3])} <prompt>")
        proc = subprocess.run(cmd)
        return int(proc.returncode)
    except Exception as exc:  # noqa: BLE001
        print(f"error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
