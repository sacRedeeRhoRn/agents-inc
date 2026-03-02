from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

from agents_inc.core.negotiation_monitor import (
    NegotiationCycleRecord,
    evaluate_negotiation,
    write_negotiation_monitor,
)


def build_negotiation_monitor(
    *,
    selected_groups: List[str],
    cycle_records: List[NegotiationCycleRecord],
    require_negotiation: bool,
    final_all_satisfied: bool,
    meeting_dir: Path,
) -> Tuple[dict, dict]:
    monitor = evaluate_negotiation(
        selected_groups=selected_groups,
        cycles=cycle_records,
        require_negotiation=bool(require_negotiation),
        final_all_satisfied=final_all_satisfied,
    )
    paths = write_negotiation_monitor(monitor=monitor, meeting_dir=meeting_dir)
    return monitor, paths
