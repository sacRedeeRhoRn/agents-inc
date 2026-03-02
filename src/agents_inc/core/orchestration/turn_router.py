from __future__ import annotations

from typing import List

from agents_inc.core.fabric_lib import FabricError


def selected_groups_from_manifest(manifest: dict) -> List[str]:
    selected = manifest.get("selected_groups")
    if not isinstance(selected, list) or not selected:
        raise FabricError("project manifest missing selected_groups")
    groups: List[str] = []
    for item in selected:
        group_id = str(item).strip()
        if group_id and group_id not in groups:
            groups.append(group_id)
    return groups


def resolve_primary_group(groups: List[str], requested_group: str) -> str:
    if requested_group and requested_group != "auto":
        if requested_group not in groups:
            raise FabricError(f"group '{requested_group}' is not active in current project")
        return requested_group
    return groups[0]
