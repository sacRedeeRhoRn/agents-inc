from __future__ import annotations

from typing import Iterable


def _join_groups(values: Iterable[object], *, limit: int = 4) -> str:
    out = [str(item).strip() for item in values if str(item).strip()]
    if not out:
        return "-"
    if len(out) <= limit:
        return ", ".join(out)
    head = ", ".join(out[:limit])
    return f"{head} (+{len(out) - limit} more)"


def format_progress_event(event: dict) -> str:
    kind = str(event.get("event") or "").strip().lower()
    if not kind:
        return ""

    if kind == "turn_started":
        groups = _join_groups(event.get("selected_groups", []))
        max_cycles = int(event.get("max_cycles", 0) or 0)
        cap = "unlimited" if max_cycles <= 0 else str(max_cycles)
        return "live: turn started | groups={0} | max_cycles={1}".format(groups, cap)
    if kind == "cycle_started":
        cycle = int(event.get("cycle", 0) or 0)
        return f"live: cycle {cycle} started"
    if kind == "runtime_heartbeat":
        cycle = int(event.get("cycle", 0) or 0)
        completed = int(event.get("completed_groups", 0) or 0)
        total = int(event.get("total_groups", 0) or 0)
        pending = _join_groups(event.get("pending_groups", []))
        return "live: cycle {0} heartbeat | groups {1}/{2} complete | pending={3}".format(
            cycle,
            completed,
            total,
            pending,
        )
    if kind == "runtime_group_started":
        cycle = int(event.get("cycle", 0) or 0)
        group_id = str(event.get("group_id") or "").strip() or "unknown"
        return f"live: cycle {cycle} group {group_id} started"
    if kind == "runtime_group_waiting":
        cycle = int(event.get("cycle", 0) or 0)
        group_id = str(event.get("group_id") or "").strip() or "unknown"
        summary = str(event.get("summary") or "").strip() or "waiting on specialists"
        return f"live: cycle {cycle} group {group_id} waiting | {summary}"
    if kind == "runtime_group_note":
        cycle = int(event.get("cycle", 0) or 0)
        group_id = str(event.get("group_id") or "").strip() or "unknown"
        text = str(event.get("text") or "").strip()
        if not text:
            return ""
        return f"live: cycle {cycle} group {group_id} note | {text}"
    if kind == "runtime_group_done":
        cycle = int(event.get("cycle", 0) or 0)
        group_id = str(event.get("group_id") or "").strip() or "unknown"
        status = str(event.get("status") or "").strip() or "UNKNOWN"
        return f"live: cycle {cycle} group {group_id} -> {status}"
    if kind == "meeting_started":
        cycle = int(event.get("cycle", 0) or 0)
        return f"live: cycle {cycle} head meeting started"
    if kind == "meeting_result":
        cycle = int(event.get("cycle", 0) or 0)
        if bool(event.get("all_satisfied")):
            return f"live: cycle {cycle} meeting satisfied all groups"
        unsatisfied = _join_groups(event.get("unsatisfied_groups", []))
        return f"live: cycle {cycle} meeting needs more work | unsatisfied={unsatisfied}"
    if kind == "meeting_room_note":
        cycle = int(event.get("cycle", 0) or 0)
        text = str(event.get("text") or "").strip()
        if not text:
            return ""
        return f"live: cycle {cycle} meeting room | {text}"
    if kind == "turn_blocked":
        status = str(event.get("status") or "").strip() or "BLOCKED"
        reason_count = int(event.get("reason_count", 0) or 0)
        return f"live: blocked {status} | reasons={reason_count}"
    if kind == "turn_completed":
        cycles = int(event.get("cycles_executed", 0) or 0)
        return f"live: completed | cycles={cycles}"
    return ""
