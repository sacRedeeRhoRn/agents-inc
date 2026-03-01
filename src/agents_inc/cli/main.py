from __future__ import annotations

import sys
from typing import Callable, Dict, List

from agents_inc import __version__
from agents_inc.cli import (
    deactivate_project,
    delete_project,
    dispatch_dry_run,
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
    print("  dispatch     dry-run project/group dispatch plan")
    print("  groups       catalog-level group management")
    print("  skills       project-scoped skill activation and cleanup")
    print("  orchestrator-reply one-turn orchestrator reply (group-detailed or [non-group])")
    print("  orchestrate  run live orchestrator evidence campaign")
    print("  orchestrate-report regenerate report from existing run directory")
    print("  migrate-v2   hard-cutover migration to schema v2")
    print("  long-run     run full-group isolation validation")
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
        "dispatch": dispatch_dry_run.main,
        "groups": groups.main,
        "skills": skills.main,
        "orchestrator-reply": orchestrator_reply.main,
        "orchestrate": orchestrate.main,
        "orchestrate-report": orchestrate_report.main,
        "migrate-v2": migrate_v2.main,
        "long-run": long_run_test.main,
        "validate": validate.main,
        "docs": generate_docs.main,
        "new-group": new_group.main,
        "new-project": new_project.main,
        "install-skills": install_skills.main,
        "sync-overlays": sync_overlays.main,
    }

    if len(sys.argv) < 2 or sys.argv[1] in {"-h", "--help", "help"}:
        _print_help()
        return 0

    if sys.argv[1] in {"--version", "-V", "version"}:
        print(__version__)
        return 0

    cmd = str(sys.argv[1]).strip().lower()
    if cmd not in commands:
        print(f"error: unknown command '{cmd}'")
        _print_help()
        return 2
    return _invoke(commands[cmd], cmd, sys.argv[2:])


if __name__ == "__main__":
    raise SystemExit(main())
