from __future__ import annotations

from collections import deque
from contextlib import AbstractContextManager
from dataclasses import dataclass, field
import sys
from typing import Deque, Dict, Iterable, List, Optional

try:
    from rich.console import Group
    from rich.live import Live
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    _RICH_AVAILABLE = True
except Exception:  # pragma: no cover - optional runtime dependency fallback
    Group = None  # type: ignore[assignment]
    Live = None  # type: ignore[assignment]
    Panel = None  # type: ignore[assignment]
    Table = None  # type: ignore[assignment]
    Text = None  # type: ignore[assignment]
    _RICH_AVAILABLE = False


@dataclass
class _GroupPaneState:
    group_id: str
    status: str = "pending"
    lines: Deque[str] = field(default_factory=lambda: deque(maxlen=12))
    completed_specialists: int = 0
    total_specialists: int = 0


class LiveDashboard(AbstractContextManager["LiveDashboard"]):
    def __init__(self, *, screen: bool = True):
        if not _RICH_AVAILABLE:
            raise RuntimeError("rich is not available")
        self._screen = bool(screen)
        self._live: Live | None = None
        self._reset_state()

    def _reset_state(self) -> None:
        self._project_id = ""
        self._execution_mode = ""
        self._cycle = 0
        self._max_cycles = 0
        self._heartbeat_sec = 0
        self._turn_state = "idle"
        self._blocked_status = ""
        self._meeting_lines: Deque[str] = deque(maxlen=14)
        self._groups: Dict[str, _GroupPaneState] = {}

    def __enter__(self) -> "LiveDashboard":
        self.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # type: ignore[override]
        self.stop()

    @staticmethod
    def supported() -> bool:
        return bool(_RICH_AVAILABLE)

    def start(self) -> None:
        if self._live is not None:
            return
        self._live = Live(self._render(), refresh_per_second=8, screen=self._screen, transient=True)
        self._live.start()

    def stop(self) -> None:
        if self._live is None:
            return
        live = self._live
        console = getattr(live, "console", None)
        used_alt_screen = bool(getattr(live, "_alt_screen", False))
        live.stop()
        if (
            self._screen
            and not used_alt_screen
            and console is not None
            and bool(getattr(console, "is_terminal", False))
        ):
            try:
                console.clear(home=True)
            except Exception:
                pass
        self._live = None

    def handle_event(self, event: dict) -> None:
        kind = str(event.get("event") or "").strip().lower()
        if not kind:
            return

        if kind == "turn_started":
            self._reset_state()
            self._project_id = str(event.get("project_id") or "").strip()
            self._execution_mode = str(event.get("execution_mode") or "").strip()
            self._max_cycles = int(event.get("max_cycles", 0) or 0)
            self._heartbeat_sec = int(event.get("heartbeat_sec", 0) or 0)
            self._turn_state = "running"
            self._ensure_groups(event.get("selected_groups", []))
        elif kind == "cycle_started":
            self._cycle = int(event.get("cycle", 0) or 0)
            self._turn_state = "running"
        elif kind == "runtime_group_started":
            state = self._group_state(str(event.get("group_id") or "unknown"))
            state.status = "running"
            self._append_group_line(state, "session dispatched")
        elif kind == "runtime_group_waiting":
            state = self._group_state(str(event.get("group_id") or "unknown"))
            state.status = "waiting"
            state.completed_specialists = int(event.get("completed_specialists", 0) or 0)
            state.total_specialists = int(event.get("total_specialists", 0) or 0)
            summary = str(event.get("summary") or "waiting on specialists").strip()
            self._append_group_line(state, summary)
        elif kind == "runtime_group_note":
            state = self._group_state(str(event.get("group_id") or "unknown"))
            state.status = "running"
            self._append_group_line(state, str(event.get("text") or "").strip())
        elif kind == "runtime_group_done":
            state = self._group_state(str(event.get("group_id") or "unknown"))
            state.status = str(event.get("status") or "unknown").strip().lower()
            self._append_group_line(state, f"status -> {str(event.get('status') or 'UNKNOWN').strip()}")
        elif kind == "meeting_started":
            self._meeting_lines.clear()
        elif kind == "meeting_room_note":
            self._append_meeting_line(str(event.get("text") or "").strip())
        elif kind == "meeting_result":
            if bool(event.get("all_satisfied")):
                self._append_meeting_line("meeting satisfied all groups")
            else:
                unsatisfied = ", ".join(
                    str(item).strip()
                    for item in event.get("unsatisfied_groups", [])
                    if str(item).strip()
                )
                self._append_meeting_line(
                    "meeting needs more work" + (f" | unsatisfied={unsatisfied}" if unsatisfied else "")
                )
        elif kind == "turn_blocked":
            self._turn_state = "blocked"
            self._blocked_status = str(event.get("status") or "BLOCKED").strip()
            self._append_meeting_line(f"turn blocked: {self._blocked_status}")
        elif kind == "turn_completed":
            self._turn_state = "completed"
            cycles = int(event.get("cycles_executed", 0) or 0)
            self._append_meeting_line(f"turn completed after {cycles} cycle(s)")

        if self._live is not None:
            self._live.update(self._render(), refresh=True)

    def _ensure_groups(self, groups: Iterable[object]) -> None:
        for raw in groups:
            group_id = str(raw or "").strip()
            if not group_id:
                continue
            self._group_state(group_id)

    def _group_state(self, group_id: str) -> _GroupPaneState:
        group_key = str(group_id or "unknown").strip() or "unknown"
        state = self._groups.get(group_key)
        if state is None:
            state = _GroupPaneState(group_id=group_key)
            self._groups[group_key] = state
        return state

    @staticmethod
    def _append_group_line(state: _GroupPaneState, text: str) -> None:
        note = str(text or "").strip()
        if not note:
            return
        if state.lines and state.lines[-1] == note:
            return
        state.lines.append(note)

    def _append_meeting_line(self, text: str) -> None:
        note = str(text or "").strip()
        if not note:
            return
        if self._meeting_lines and self._meeting_lines[-1] == note:
            return
        self._meeting_lines.append(note)

    def _render(self):
        status_panel = Panel(
            self._render_status_text(),
            title="project status",
            border_style="cyan",
        )
        meeting_body = (
            "\n".join(self._meeting_lines)
            if self._meeting_lines
            else "[dim]waiting for group meeting[/dim]"
        )
        meeting_panel = Panel(meeting_body, title="group-meeting room", border_style="magenta")
        group_grid = self._render_group_grid()
        return Group(status_panel, meeting_panel, group_grid)

    def _render_status_text(self):
        cap = "unlimited" if self._max_cycles <= 0 else str(self._max_cycles)
        rows = [
            f"project={self._project_id or '-'}",
            f"mode={self._execution_mode or '-'}",
            f"cycle={self._cycle}",
            f"max_cycles={cap}",
            f"heartbeat={self._heartbeat_sec or '-'}s",
            f"turn_state={self._turn_state}",
            "interrupt=double ESC",
        ]
        if self._blocked_status:
            rows.append(f"blocked_status={self._blocked_status}")
        return "  |  ".join(rows)

    def _render_group_grid(self):
        groups = [self._groups[key] for key in sorted(self._groups.keys())]
        if not groups:
            return Panel("[dim]no active groups[/dim]", title="group headers", border_style="blue")

        width = getattr(getattr(self._live, "console", None), "width", 120) if self._live else 120
        columns = self._resolve_columns(len(groups), width)
        table = Table.grid(expand=True)
        for _ in range(columns):
            table.add_column(ratio=1)
        panels = [self._render_group_panel(state) for state in groups]
        while len(panels) % columns != 0:
            panels.append(Panel("", title="", border_style="black"))
        for start in range(0, len(panels), columns):
            table.add_row(*panels[start : start + columns])
        return table

    @staticmethod
    def _resolve_columns(group_count: int, width: int) -> int:
        if group_count <= 1:
            return 1
        if width >= 200 and group_count >= 4:
            return 4
        if width >= 150 and group_count >= 3:
            return 3
        if width >= 100 and group_count >= 2:
            return 2
        return 1

    def _render_group_panel(self, state: _GroupPaneState):
        title = f"{state.group_id} [{state.status}]"
        header = ""
        if state.total_specialists > 0 and state.status == "waiting":
            header = f"specialists: {state.completed_specialists}/{state.total_specialists}\n\n"
        body = "\n".join(state.lines) if state.lines else "[dim]waiting for worklog[/dim]"
        return Panel(header + body, title=title, border_style=self._border_style_for_status(state.status))

    @staticmethod
    def _border_style_for_status(status: str) -> str:
        normalized = str(status or "pending").strip().lower()
        if normalized in {"complete", "complete_with_warnings"}:
            return "green"
        if normalized in {"blocked", "failed"}:
            return "red"
        if normalized == "running":
            return "cyan"
        if normalized == "waiting":
            return "yellow"
        return "blue"


def should_enable_dashboard(mode: str, *, interactive: bool, json_mode: bool = False) -> bool:
    normalized = str(mode or "auto").strip().lower()
    if json_mode:
        return False
    if normalized == "off":
        return False
    if normalized == "on":
        return LiveDashboard.supported()
    return interactive and LiveDashboard.supported()


def clear_interactive_terminal(*, clear_scrollback: bool = True) -> bool:
    stream = getattr(sys, "stdout", None)
    if stream is None or not bool(getattr(stream, "isatty", lambda: False)()):
        return False
    sequence = "\x1b[2J\x1b[H"
    if clear_scrollback:
        sequence = "\x1b[3J" + sequence
    try:
        stream.write(sequence)
        stream.flush()
        return True
    except Exception:
        return False
