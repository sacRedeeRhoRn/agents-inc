from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Optional

from agents_inc.core.fabric_lib import now_iso, write_text

SENSITIVE_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key\s*[:=]\s*)[A-Za-z0-9_\-]{8,}"),
    re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._\-]{12,}"),
    re.compile(r"(?i)(token\s*[:=]\s*)[A-Za-z0-9._\-]{12,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----"),
]

ANSI_ESCAPE = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")
FINAL_PLAN_BLOCK = re.compile(
    r"BEGIN_FINAL_PLAN\s*(.*?)\s*END_FINAL_PLAN",
    flags=re.DOTALL | re.IGNORECASE,
)


def capture_with_script(
    *,
    raw_log_path: Path,
    command: list[str],
    cwd: Path,
    env: Optional[dict] = None,
    timeout_sec: int = 300,
) -> subprocess.CompletedProcess:
    raw_log_path.parent.mkdir(parents=True, exist_ok=True)
    script_cmd = ["script", "-q", str(raw_log_path), *command]
    run_env = dict(env or {})
    term_value = str(run_env.get("TERM", "")).strip().lower()
    if term_value in {"", "dumb"}:
        run_env["TERM"] = "xterm-256color"
    return subprocess.run(
        script_cmd,
        cwd=str(cwd),
        env=run_env,
        text=True,
        capture_output=True,
        timeout=timeout_sec,
    )


def _cleanup_control_sequences(text: str) -> str:
    # Remove ANSI escapes and terminal backspace effects from macOS `script` logs.
    cleaned = ANSI_ESCAPE.sub("", text)
    while "\b" in cleaned:
        cleaned = re.sub(r".\x08", "", cleaned)
    cleaned = cleaned.replace("\r", "")
    return cleaned


def redact_text(text: str) -> str:
    redacted = _cleanup_control_sequences(text)
    for pattern in SENSITIVE_PATTERNS:
        redacted = pattern.sub(r"\1[REDACTED]" if pattern.groups else "[REDACTED]", redacted)
    return redacted


def redact_log(raw_log_path: Path, redacted_log_path: Path) -> None:
    raw_text = raw_log_path.read_text(encoding="utf-8", errors="replace")
    redacted_log_path.parent.mkdir(parents=True, exist_ok=True)
    redacted_log_path.write_text(redact_text(raw_text), encoding="utf-8")


def write_command_log(path: Path, commands: list[dict]) -> None:
    lines = [
        "# Command Timeline",
        "",
        f"- generated_at: {now_iso()}",
        "",
    ]
    for row in commands:
        lines.extend(
            [
                f"## {row.get('name', 'command')}",
                f"- command: `{row.get('command', '')}`",
                f"- return_code: `{row.get('return_code', '')}`",
                f"- started_at: `{row.get('started_at', '')}`",
                f"- finished_at: `{row.get('finished_at', '')}`",
                "",
                "```text",
                str(row.get("stdout", "")).strip(),
                "```",
                "",
                "```text",
                str(row.get("stderr", "")).strip(),
                "```",
                "",
            ]
        )
    write_text(path, "\n".join(lines).strip() + "\n")


def extract_final_plan_block(raw_text: str) -> str:
    cleaned = redact_text(raw_text)
    matches = list(FINAL_PLAN_BLOCK.finditer(cleaned))
    if not matches:
        return ""
    candidates: list[str] = []
    for match in matches:
        text = match.group(1).strip()
        if len(text) < 80:
            continue
        if text.strip(". ").strip() == "":
            continue
        candidates.append(text)
    if not candidates:
        return ""
    return candidates[-1]
