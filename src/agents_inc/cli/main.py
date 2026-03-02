from __future__ import annotations

import sys
from typing import Callable, Dict, List

from agents_inc import __version__
from agents_inc.cli import (
    cleanup_projects,
    deactivate_project,
    delete_project,
    dispatch_dry_run,
    eval as eval_cli,
    generate_docs,
    groups,
    init_session,
    install_skills,
    list_sessions,
    long_run_test,
    migrate_v2,
    new_group,
    new_project,
    orchestrate,
    orchestrate_report,
    orchestrator_reply,
    project_groups,
    resume,
    skills,
    sync_overlays,
    validate,
)


def _invoke(entry: Callable[[], int], cmd: str, argv: List[str]) -> int:
    prev = sys.argv
    try:
        sys.argv = [f"{prev[0]} {cmd}", *argv]
        return int(entry())
    finally:
        sys.argv = prev


def _print_help() -> None:
    print("agents-inc command router")
    print("")
    print("Usage:")
    print("  agents-inc <command> [args]")
    print("  agents-inc --version")
    print("")
    print("Primary commands:")
    print("  init         interactive/new/resume project intake")
    print("  list         list resumable project sessions")
    print("  resume       resume a project and launch codex")
    print("  deactivate   deactivate a project by project-id")
    print("  delete       delete a project by project-id")
    print("  cleanup-projects hard-delete indexed project roots")
    print("  dispatch     dry-run project/group dispatch plan")
    print("  groups       catalog-level group management")
    print("  project-groups manage active groups within a project")
    print("  skills       project-scoped skill activation and cleanup")
    print("  orchestrator-reply one-turn orchestrator reply (group-detailed or [non-group])")
    print("  orchestrate  run live orchestrator evidence campaign")
    print("  orchestrate-report regenerate report from existing run directory")
    print("  migrate-v2   hard-cutover migration to schema v3")
    print("  long-run     run full-group isolation validation")
    print("  eval         score specialist outputs for a completed turn")
    print("  validate     validate catalog/templates/schemas")
    print("  docs         generate full docs reference")
    print("")
    print("Additional commands:")
    print("  new-group")
    print("  new-project")
    print("  install-skills")
    print("  sync-overlays")
    print("")
    print("Run 'agents-inc <command> --help' for command-specific options.")


def main() -> int:
    commands: Dict[str, Callable[[], int]] = {
        "init": init_session.main,
        "list": list_sessions.main,
        "resume": resume.main,
        "deactivate": deactivate_project.main,
        "delete": delete_project.main,
        "cleanup-projects": cleanup_projects.main,
        "dispatch": dispatch_dry_run.main,
        "groups": groups.main,
        "project-groups": project_groups.main,
        "skills": skills.main,
        "orchestrator-reply": orchestrator_reply.main,
        "orchestrate": orchestrate.main,
        "orchestrate-report": orchestrate_report.main,
        "migrate-v2": migrate_v2.main,
        "long-run": long_run_test.main,
        "eval": eval_cli.main,
        "validate": validate.main,
        "docs": generate_docs.main,
        "new-group": new_group.main,
        "new-project": new_project.main,
        "install-skills": install_skills.main,
        "sync-overlays": sync_overlays.main,
    }
    deprecated_aliases = {
        "init-session": "init",
        "list-sessions": "list",
        "dispatch-dry-run": "dispatch",
        "long-run-test": "long-run",
        "generate-docs": "docs",
    }

    if len(sys.argv) < 2 or sys.argv[1] in {"-h", "--help", "help"}:
        _print_help()
        return 0

    if sys.argv[1] in {"--version", "-V", "version"}:
        print(__version__)
        return 0

    cmd = str(sys.argv[1]).strip().lower()
    if cmd in deprecated_aliases:
        replacement = deprecated_aliases[cmd]
        print(
            f"deprecated: 'agents-inc {cmd}' will be removed in a future release. "
            f"Use 'agents-inc {replacement}' instead.",
            file=sys.stderr,
        )
        cmd = replacement
    if cmd not in commands:
        print(f"error: unknown command '{cmd}'")
        _print_help()
        return 2
    return _invoke(commands[cmd], cmd, sys.argv[2:])


if __name__ == "__main__":
    raise SystemExit(main())
