from __future__ import annotations

import sys
from typing import Callable, Dict, List

from agents_inc import __version__
from agents_inc.cli import (
    create_project,
    deactivate_project,
    delete_project,
    group_list,
    init_session,
    list_sessions,
    new_group,
    project_groups,
    resume,
    save_project,
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
    print("Commands:")
    print("  init                    bootstrap agents-inc configuration")
    print("  group-list              list employable groups")
    print("  create <project-id>     create project and launch orchestrator chat")
    print("  save <project-id>       save project state snapshot")
    print("  deactivate <project-id> deactivate project")
    print("  list                    list projects")
    print("  resume <project-id>     resume project orchestrator chat")
    print("  project-groups          list/add/remove groups for a project")
    print("  delete <project-id>     delete project data (requires confirmation)")
    print("  new-group               launch group creation flow")
    print("")
    print("Run 'agents-inc <command> --help' for command-specific options.")


def main() -> int:
    commands: Dict[str, Callable[[], int]] = {
        "init": init_session.main,
        "group-list": group_list.main,
        "create": create_project.main,
        "save": save_project.main,
        "list": list_sessions.main,
        "resume": resume.main,
        "deactivate": deactivate_project.main,
        "delete": delete_project.main,
        "project-groups": project_groups.main,
        "new-group": new_group.main,
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
