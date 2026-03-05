from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, List

from agents_inc.core.fabric_lib import now_iso, stable_json, write_text

TOKEN_USAGE_SCHEMA_VERSION = "1.0"
TOKEN_USAGE_JSON_NAME = "token-usage-report.json"
TOKEN_USAGE_MD_NAME = "token-usage-report.md"


def _as_int(value: object) -> int:
    try:
        parsed = int(float(str(value)))
    except Exception:
        parsed = 0
    return max(0, parsed)


def _iter_dict_nodes(value: object) -> Iterable[dict]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _iter_dict_nodes(child)
        return
    if isinstance(value, list):
        for child in value:
            yield from _iter_dict_nodes(child)


def _iter_token_count_nodes(event: object) -> Iterable[dict]:
    for node in _iter_dict_nodes(event):
        event_type = str(node.get("type") or "").strip().lower()
        if event_type == "token_count":
            yield node


def _lookup_numeric(node: dict, keys: List[str]) -> int:
    best = 0
    for candidate in _iter_dict_nodes(node):
        for key in keys:
            if key not in candidate:
                continue
            best = max(best, _as_int(candidate.get(key)))
    return best


def _extract_usage(node: dict) -> dict:
    input_tokens = _lookup_numeric(
        node,
        ["input_tokens", "input", "input_token_count", "prompt_tokens"],
    )
    cached_input_tokens = _lookup_numeric(
        node,
        ["cached_input_tokens", "cached_input", "cache_read_input_tokens"],
    )
    output_tokens = _lookup_numeric(
        node,
        ["output_tokens", "output", "completion_tokens"],
    )
    reasoning_output_tokens = _lookup_numeric(
        node,
        ["reasoning_output_tokens", "reasoning_tokens", "reasoning_output"],
    )
    total_token_usage = _lookup_numeric(
        node,
        ["total_token_usage", "total_tokens", "total", "total_token_count"],
    )
    total_token_usage = max(total_token_usage, input_tokens + output_tokens)
    return {
        "input_tokens": input_tokens,
        "cached_input_tokens": cached_input_tokens,
        "output_tokens": output_tokens,
        "reasoning_output_tokens": reasoning_output_tokens,
        "total_token_usage": total_token_usage,
    }


def _select_session_usage(events: List[dict]) -> dict:
    with_total = [row for row in events if int(row.get("total_token_usage", 0)) > 0]
    selected = max(with_total, key=lambda row: int(row.get("total_token_usage", 0))) if with_total else events[-1]
    return {
        "input_tokens": _as_int(selected.get("input_tokens")),
        "cached_input_tokens": _as_int(selected.get("cached_input_tokens")),
        "output_tokens": _as_int(selected.get("output_tokens")),
        "reasoning_output_tokens": _as_int(selected.get("reasoning_output_tokens")),
        "total_token_usage": _as_int(selected.get("total_token_usage")),
        "event_count": len(events),
    }


def _parse_session_usage(session_file: Path) -> dict | None:
    events: List[dict] = []
    try:
        lines = session_file.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception:
        return None
    for line in lines:
        text = line.strip()
        if not text:
            continue
        try:
            payload = json.loads(text)
        except Exception:
            continue
        for node in _iter_token_count_nodes(payload):
            usage = _extract_usage(node)
            if usage["total_token_usage"] <= 0 and not any(
                int(usage[key]) > 0
                for key in (
                    "input_tokens",
                    "cached_input_tokens",
                    "output_tokens",
                    "reasoning_output_tokens",
                )
            ):
                continue
            events.append(usage)
    if not events:
        return None
    selected = _select_session_usage(events)
    selected["session_file"] = str(session_file)
    return selected


def _aggregate(rows: List[dict]) -> dict:
    input_tokens = sum(_as_int(row.get("input_tokens")) for row in rows)
    cached_input_tokens = sum(_as_int(row.get("cached_input_tokens")) for row in rows)
    output_tokens = sum(_as_int(row.get("output_tokens")) for row in rows)
    reasoning_output_tokens = sum(_as_int(row.get("reasoning_output_tokens")) for row in rows)
    total_token_usage = sum(_as_int(row.get("total_token_usage")) for row in rows)
    billable_token_estimate = max(0, input_tokens - cached_input_tokens) + output_tokens
    return {
        "input_tokens": input_tokens,
        "cached_input_tokens": cached_input_tokens,
        "output_tokens": output_tokens,
        "reasoning_output_tokens": reasoning_output_tokens,
        "total_token_usage": total_token_usage,
        "billable_token_estimate": billable_token_estimate,
        "sessions_with_usage": len(rows),
    }


def _render_markdown(*, turn_dir: Path, session_files: List[Path], rows: List[dict], summary: dict) -> str:
    lines = [
        "# Token Usage Report",
        "",
        f"- generated_at: `{now_iso()}`",
        f"- turn_dir: `{turn_dir}`",
        f"- scanned_session_files: `{len(session_files)}`",
        f"- sessions_with_usage: `{summary.get('sessions_with_usage', 0)}`",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| input_tokens | {summary.get('input_tokens', 0)} |",
        f"| cached_input_tokens | {summary.get('cached_input_tokens', 0)} |",
        f"| output_tokens | {summary.get('output_tokens', 0)} |",
        f"| reasoning_output_tokens | {summary.get('reasoning_output_tokens', 0)} |",
        f"| total_token_usage | {summary.get('total_token_usage', 0)} |",
        f"| billable_token_estimate | {summary.get('billable_token_estimate', 0)} |",
        "",
        "## Sessions",
        "",
    ]
    if not rows:
        lines.append("No `token_count` events were found in scanned session logs.")
        return "\n".join(lines).rstrip() + "\n"
    lines.extend(
        [
            "| Session File | Input | Cached Input | Output | Reasoning Output | Total | token_count events |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in rows:
        lines.append(
            "| {session} | {input_tokens} | {cached_input_tokens} | {output_tokens} | {reasoning_output_tokens} | {total_token_usage} | {event_count} |".format(
                session=str(row.get("session_file") or ""),
                input_tokens=_as_int(row.get("input_tokens")),
                cached_input_tokens=_as_int(row.get("cached_input_tokens")),
                output_tokens=_as_int(row.get("output_tokens")),
                reasoning_output_tokens=_as_int(row.get("reasoning_output_tokens")),
                total_token_usage=_as_int(row.get("total_token_usage")),
                event_count=_as_int(row.get("event_count")),
            )
        )
    return "\n".join(lines).rstrip() + "\n"


def write_turn_token_usage_report(*, turn_dir: Path) -> dict:
    root = Path(turn_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    session_files = sorted(root.glob("**/codex-home/sessions/**/*.jsonl"))
    rows: List[dict] = []
    for session_file in session_files:
        usage = _parse_session_usage(session_file)
        if usage is not None:
            rows.append(usage)
    summary = _aggregate(rows)
    payload = {
        "schema_version": TOKEN_USAGE_SCHEMA_VERSION,
        "generated_at": now_iso(),
        "turn_dir": str(root),
        "scanned_session_file_count": len(session_files),
        "sessions_with_usage": len(rows),
        "summary": summary,
        "sessions": rows,
    }
    json_path = root / TOKEN_USAGE_JSON_NAME
    md_path = root / TOKEN_USAGE_MD_NAME
    write_text(json_path, stable_json(payload) + "\n")
    write_text(
        md_path,
        _render_markdown(
            turn_dir=root,
            session_files=session_files,
            rows=rows,
            summary=summary,
        ),
    )
    return {
        "json_path": str(json_path),
        "md_path": str(md_path),
        "summary": summary,
    }
