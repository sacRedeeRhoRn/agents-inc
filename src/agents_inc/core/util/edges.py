from __future__ import annotations

from typing import List, Sequence, Tuple


def resolve_handoff_edges(
    selected_groups: Sequence[str],
    configured_edges: Sequence[Tuple[str, str]] | Sequence[Sequence[str]] | None,
) -> List[Tuple[str, str]]:
    """Resolve active handoff edges with deterministic fallback.

    Rules:
    - If configured edges are valid and in-scope, use them.
    - If no valid configured edges exist and there are >=2 groups, build a ring.
    - Single-group runs have no handoff edges.
    """

    groups = [str(group_id).strip() for group_id in selected_groups if str(group_id).strip()]
    group_set = set(groups)
    out: List[Tuple[str, str]] = []

    if configured_edges:
        for row in configured_edges:
            if not isinstance(row, (list, tuple)) or len(row) != 2:
                continue
            src = str(row[0]).strip()
            dst = str(row[1]).strip()
            if not src or not dst:
                continue
            if src not in group_set or dst not in group_set:
                continue
            edge = (src, dst)
            if edge not in out:
                out.append(edge)

    if out:
        return out

    if len(groups) < 2:
        return []

    for idx, src in enumerate(groups):
        dst = groups[(idx + 1) % len(groups)]
        edge = (src, dst)
        if edge not in out:
            out.append(edge)
    return out

