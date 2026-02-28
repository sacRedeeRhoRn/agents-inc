from __future__ import annotations

import sys
from typing import List

from agents_inc.cli.main import main as router_main


def _run_alias(old_name: str, new_cmd: str, argv: List[str]) -> int:
    print(
        f"deprecated: '{old_name}' is an alias and will be removed after v2.0.x. Use 'agents-inc {new_cmd}' instead.",
        file=sys.stderr,
    )
    prev = sys.argv
    try:
        sys.argv = ["agents-inc", new_cmd, *argv]
        return int(router_main())
    finally:
        sys.argv = prev


def init_session_alias() -> int:
    return _run_alias("agents-inc-init-session", "init", sys.argv[1:])


def list_sessions_alias() -> int:
    return _run_alias("agents-inc-list-sessions", "list", sys.argv[1:])


def dispatch_dry_run_alias() -> int:
    return _run_alias("agents-inc-dispatch-dry-run", "dispatch", sys.argv[1:])


def long_run_test_alias() -> int:
    return _run_alias("agents-inc-long-run-test", "long-run", sys.argv[1:])


def validate_alias() -> int:
    return _run_alias("agents-inc-validate", "validate", sys.argv[1:])


def generate_docs_alias() -> int:
    return _run_alias("agents-inc-generate-docs", "docs", sys.argv[1:])


def install_skills_alias() -> int:
    return _run_alias("agents-inc-install-skills", "install-skills", sys.argv[1:])


def sync_overlays_alias() -> int:
    return _run_alias("agents-inc-sync-overlays", "sync-overlays", sys.argv[1:])


def new_group_alias() -> int:
    return _run_alias("agents-inc-new-group", "groups", ["new", *sys.argv[1:]])


def new_project_alias() -> int:
    return _run_alias("agents-inc-new-project", "new-project", sys.argv[1:])
