from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple

from agents_inc.core.config_state import default_config_path, get_projects_root
from agents_inc.core.fabric_lib import (
    FabricError,
    load_project_manifest,
    resolve_fabric_root,
    slugify,
)
from agents_inc.core.session_state import default_project_index_path, find_resume_project


def resolve_project_context(
    *,
    project_id: str,
    fabric_root: Optional[str] = None,
    project_index: Optional[str] = None,
    scan_root: Optional[str] = None,
    config_path: Optional[str] = None,
) -> Tuple[Path, Path, Path, Path, dict]:
    normalized_project_id = slugify(project_id)
    if not normalized_project_id:
        raise FabricError("project id cannot be empty")

    if fabric_root:
        resolved_fabric_root = resolve_fabric_root(fabric_root)
        project_dir, manifest = load_project_manifest(resolved_fabric_root, normalized_project_id)
        project_root = project_dir
        manifest_path = project_dir / "manifest.yaml"
        return resolved_fabric_root, project_root, project_dir, manifest_path, manifest

    index_path = default_project_index_path(project_index)
    resolved_scan_root = (
        Path(str(scan_root)).expanduser().resolve()
        if scan_root
        else get_projects_root(default_config_path(config_path))
    )
    found = find_resume_project(
        index_path=index_path,
        project_id=normalized_project_id,
        fallback_scan_root=resolved_scan_root,
    )
    if not found:
        raise FabricError(f"could not locate project '{normalized_project_id}'")
    project_root = Path(str(found["project_root"])).expanduser().resolve()
    resolved_fabric_root = (
        Path(str(found.get("fabric_root") or (project_root / "agent_group_fabric")))
        .expanduser()
        .resolve()
    )
    project_dir, manifest = load_project_manifest(resolved_fabric_root, normalized_project_id)
    manifest_path = project_dir / "manifest.yaml"
    return resolved_fabric_root, project_root, project_dir, manifest_path, manifest
