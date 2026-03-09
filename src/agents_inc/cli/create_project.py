from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Dict, List, Set

import yaml

from agents_inc.cli.install_skills import install_project_skills
from agents_inc.core.codex_home import (
    ensure_project_codex_home,
    save_skill_activation_state,
    skill_activation_state_path,
)
from agents_inc.core.config_state import default_config_path, get_projects_root, set_projects_root
from agents_inc.core.fabric_lib import (
    FabricError,
    ensure_fabric_root_initialized,
    execution_mode_from_manifest,
    ensure_json_serializable,
    load_group_catalog,
    now_iso,
    resolve_fabric_root,
    slugify,
)
from agents_inc.core.orchestrator_chat import OrchestratorChatConfig, run_orchestrator_chat
from agents_inc.core.live_dashboard import clear_interactive_terminal
from agents_inc.core.response_policy import ensure_response_policy, upsert_specialist_sessions
from agents_inc.core.session_compaction import compact_session
from agents_inc.core.session_state import default_project_index_path, write_checkpoint


def _parse_groups(value: str) -> List[str]:
    out: List[str] = []
    for raw in value.split(","):
        gid = slugify(raw)
        if gid and gid not in out:
            out.append(gid)
    return out


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a new agents-inc project")
    parser.add_argument("project_id", help="project identifier")
    parser.add_argument("--fabric-root", default=None, help="path to fabric root")
    parser.add_argument("--projects-root", default=None, help="projects root path")
    parser.add_argument("--config-path", default=None, help="config path")
    parser.add_argument("--project-index", default=None, help="project index path")
    parser.add_argument(
        "--groups", default="", help="comma-separated group ids (skip interactive picker)"
    )
    parser.add_argument("--no-launch", action="store_true", help="skip launching managed chat")
    parser.add_argument("--json", action="store_true", help="emit summary as JSON")
    parser.add_argument(
        "--force",
        action="store_true",
        help="overwrite existing generated project bundle if present",
    )
    parser.add_argument(
        "--execution-mode",
        default="light",
        choices=["light", "full"],
        help="project runtime execution mode for generated manifest",
    )
    return parser.parse_args()


def _group_rows(catalog: Dict[str, dict]) -> List[str]:
    return sorted(catalog.keys())


def _print_picker(rows: List[str], selected: Set[str]) -> None:
    print("Employable groups:")
    for index, gid in enumerate(rows, start=1):
        mark = "[x]" if gid in selected else "[ ]"
        print(f"{index:>2}. {mark} {gid}")
    print("")
    print("Selection commands:")
    print("- enter index numbers or group ids (e.g. 1 or developer,material-scientist) to toggle")
    print("- 'all' to select all")
    print("- 'none' to clear")
    print("- 'show' to reprint list")
    print("- 'done' to finish")
    print("- 'cancel' to abort")


def _interactive_select_groups(rows: List[str]) -> List[str]:
    selected: Set[str] = set()
    available = set(rows)
    _print_picker(rows, selected)
    while True:
        try:
            raw = input("select> ").strip().lower()
        except EOFError as exc:  # pragma: no cover - shell-dependent
            raise FabricError("group selection aborted (stdin closed)") from exc
        if not raw:
            continue
        if raw == "show":
            _print_picker(rows, selected)
            continue
        if raw in {"help", "?"}:
            _print_picker(rows, selected)
            continue
        if raw == "all":
            selected = set(rows)
            print(f"selected all {len(selected)} groups")
            continue
        if raw == "none":
            selected = set()
            print("cleared selection")
            continue
        if raw in {"cancel", "quit", "exit", "q"}:
            raise FabricError("group selection cancelled by user")
        if raw == "done":
            if not selected:
                print("select at least one group before 'done'")
                continue
            return [gid for gid in rows if gid in selected]
        parts = [part.strip() for part in raw.split(",") if part.strip()]
        toggled = []
        bad = []
        for part in parts:
            gid = ""
            if part.isdigit():
                index = int(part)
                if index < 1 or index > len(rows):
                    bad.append(part)
                    continue
                gid = rows[index - 1]
            else:
                candidate = slugify(part)
                if candidate in available:
                    gid = candidate
                else:
                    bad.append(part)
                    continue
            if gid in selected:
                selected.remove(gid)
            else:
                selected.add(gid)
            toggled.append(gid)
        if bad:
            print(
                "invalid tokens: {0} (use index numbers or exact group ids)".format(", ".join(bad))
            )
        if toggled:
            print("toggled:", ", ".join(toggled))


def _run_new_project_bundle(
    *,
    project_fabric_root: Path,
    project_id: str,
    selected_groups: List[str],
    target_skill_dir: Path,
    execution_mode: str,
    force: bool,
) -> None:
    argv = [
        "agents-inc-new-project",
        "--fabric-root",
        str(project_fabric_root),
        "--project-id",
        project_id,
        "--groups",
        ",".join(selected_groups),
        "--visibility-mode",
        "group-only",
        "--audit-override",
        "--target-skill-dir",
        str(target_skill_dir),
        "--execution-mode",
        str(execution_mode),
    ]
    if force:
        argv.append("--force")
    prev = sys.argv
    try:
        from agents_inc.cli import new_project as new_project_cli

        sys.argv = argv
        rc = int(new_project_cli.main())
    finally:
        sys.argv = prev
    if rc != 0:
        raise FabricError("failed to generate project bundle")


def _sync_catalog_group_manifests(*, source_fabric_root: Path, target_fabric_root: Path) -> None:
    src_catalog = source_fabric_root / "catalog" / "groups"
    if not src_catalog.exists():
        return
    dst_catalog = target_fabric_root / "catalog" / "groups"
    dst_catalog.mkdir(parents=True, exist_ok=True)
    for src in sorted(src_catalog.glob("*.yaml")):
        dst = dst_catalog / src.name
        try:
            shutil.copy2(src, dst)
        except Exception as exc:  # noqa: BLE001
            raise FabricError(f"failed to sync group manifest '{src}' -> '{dst}': {exc}") from exc


def _checkpoint_payload(
    *,
    project_id: str,
    project_root: Path,
    project_fabric_root: Path,
    selected_groups: List[str],
) -> dict:
    return {
        "schema_version": "3.0",
        "project_id": project_id,
        "project_root": str(project_root),
        "fabric_root": str(project_fabric_root),
        "task": "",
        "constraints": {},
        "selected_groups": selected_groups,
        "router_call": "",
        "latest_artifacts": {},
        "pending_actions": [],
        "updated_at": now_iso(),
    }


def main() -> int:
    args = parse_args()
    try:
        if not bool(args.json):
            clear_interactive_terminal()
        project_id = slugify(args.project_id)
        if not project_id:
            raise FabricError("project id resolved to empty value")

        fabric_root = resolve_fabric_root(args.fabric_root)
        ensure_fabric_root_initialized(fabric_root)

        config_path = default_config_path(args.config_path)
        projects_root = (
            Path(str(args.projects_root)).expanduser().resolve()
            if args.projects_root
            else get_projects_root(config_path)
        )
        set_projects_root(config_path, projects_root)
        project_root = projects_root / project_id
        project_root.mkdir(parents=True, exist_ok=True)
        project_fabric_root = project_root / "agent_group_fabric"
        ensure_fabric_root_initialized(project_fabric_root)
        _sync_catalog_group_manifests(
            source_fabric_root=fabric_root,
            target_fabric_root=project_fabric_root,
        )

        catalog = load_group_catalog(project_fabric_root)
        rows = _group_rows(catalog)
        if not rows:
            raise FabricError("group catalog is empty")

        if args.groups:
            selected_groups = _parse_groups(args.groups)
            missing = [gid for gid in selected_groups if gid not in catalog]
            if missing:
                raise FabricError("unknown groups: " + ", ".join(missing))
        else:
            selected_groups = _interactive_select_groups(rows)
        if not selected_groups:
            raise FabricError("no groups selected")

        codex_home_state = ensure_project_codex_home(project_root, project_id=project_id)
        target_skill_dir = Path(str(codex_home_state["skills_dir"])).expanduser().resolve()
        _run_new_project_bundle(
            project_fabric_root=project_fabric_root,
            project_id=project_id,
            selected_groups=selected_groups,
            target_skill_dir=target_skill_dir,
            execution_mode=str(args.execution_mode or "light"),
            force=bool(args.force),
        )
        project_manifest = (
            project_fabric_root / "generated" / "projects" / project_id / "manifest.yaml"
        )
        manifest_payload = {}
        if project_manifest.exists():
            loaded = yaml.safe_load(project_manifest.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                manifest_payload = loaded
        execution_mode = execution_mode_from_manifest(manifest_payload, default="light")
        ensure_response_policy(project_root)
        if execution_mode == "full":
            upsert_specialist_sessions(
                project_root=project_root,
                project_fabric_root=project_fabric_root,
                project_id=project_id,
                selected_groups=selected_groups,
            )
        activation = save_skill_activation_state(
            project_root,
            active_head_groups=selected_groups,
            active_specialist_groups=(selected_groups if execution_mode == "full" else []),
        )
        install_result = install_project_skills(
            fabric_root=project_fabric_root,
            project_id=project_id,
            target=Path(str(codex_home_state["skills_dir"])),
            sync=True,
            head_groups=activation["active_head_groups"],
            specialist_groups=activation["active_specialist_groups"],
            include_specialists=(execution_mode == "full"),
        )
        if not args.json:
            print(
                "installed managed skills: {0} (head groups: {1}; specialist groups: {2})".format(
                    len(install_result.get("installed", [])),
                    ",".join(activation["active_head_groups"]),
                    ",".join(activation["active_specialist_groups"]),
                )
            )

        payload = _checkpoint_payload(
            project_id=project_id,
            project_root=project_root,
            project_fabric_root=project_fabric_root,
            selected_groups=selected_groups,
        )
        checkpoint = write_checkpoint(
            project_root=project_root,
            payload=payload,
            project_index_path=default_project_index_path(args.project_index),
        )
        compact = compact_session(
            project_root=project_root,
            payload=payload,
            selected_groups=selected_groups,
        )

        chat = run_orchestrator_chat(
            OrchestratorChatConfig(
                fabric_root=project_fabric_root,
                project_root=project_root,
                project_id=project_id,
                no_launch=bool(args.no_launch),
            )
        )
        summary = {
            "project_id": project_id,
            "project_root": str(project_root),
            "fabric_root": str(project_fabric_root),
            "selected_groups": selected_groups,
            "checkpoint_id": str(checkpoint["checkpoint_id"]),
            "compact_id": str(compact["compact_id"]),
            "thread_id": str(chat.get("thread_id") or ""),
            "chat_log_path": str(chat.get("chat_log_path") or ""),
            "skill_refresh": {
                "target": install_result.get("target", ""),
                "router_version": install_result.get("router_version", ""),
                "router_template_source": install_result.get("router_template_source", ""),
                "installed_skill_count": len(install_result.get("installed", [])),
            },
            "skill_activation": {
                "path": str(skill_activation_state_path(project_root)),
                "active_head_groups": activation["active_head_groups"],
                "active_specialist_groups": activation["active_specialist_groups"],
            },
            "runtime": {
                "execution_mode": execution_mode,
            },
        }
        if args.json:
            print(json.dumps(ensure_json_serializable(summary), indent=2, sort_keys=True))
        else:
            print(json.dumps(ensure_json_serializable(summary), indent=2, sort_keys=True))
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
