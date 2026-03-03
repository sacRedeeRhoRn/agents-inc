from __future__ import annotations

from pathlib import Path
from typing import List


def render_blocked_report(
    *,
    project_id: str,
    message: str,
    status: str,
    reasons: List[str],
    contributions: List[dict],
    web_evidence_count: int,
    artifact_citation_count: int,
    turn_dir: Path,
    timed_out_specialists: List[dict] | None = None,
    escalations: List[dict] | None = None,
) -> str:
    lines = [
        f"# BLOCKED Turn - {project_id}",
        "",
        "## Objective",
        message,
        "",
        "## Block Status",
        f"- status: `{status}`",
        "",
        "## Reasons",
    ]
    for reason in reasons:
        lines.append(f"- {reason}")

    lines.extend(
        [
            "",
            "## Contributor Status",
            "| Group | Status | Artifact Count | Claim Count | Citation Count | Reasons |",
            "|---|---|---:|---:|---:|---|",
        ]
    )
    for row in contributions:
        reason_text = "; ".join(str(item) for item in row.get("reasons", []))
        lines.append(
            "| {0} | {1} | {2} | {3} | {4} | {5} |".format(
                row.get("group_id", ""),
                "valid" if row.get("valid") else "blocked",
                row.get("artifact_count", 0),
                row.get("claim_count", 0),
                row.get("citation_count", 0),
                reason_text.replace("|", "/"),
            )
        )

    lines.extend(
        [
            "",
            "## Evidence Summary",
            f"- web evidence URLs: `{web_evidence_count}`",
            f"- artifact citation refs: `{artifact_citation_count}`",
        ]
    )

    if timed_out_specialists:
        lines.extend(
            [
                "",
                "## Timed Out Specialists",
                "| Group | Specialist | Attempts | Raw Log | Redacted Log |",
                "|---|---|---:|---|---|",
            ]
        )
        for row in timed_out_specialists:
            lines.append(
                "| {0} | {1} | {2} | {3} | {4} |".format(
                    row.get("group_id", ""),
                    row.get("specialist_id", ""),
                    row.get("attempts", ""),
                    row.get("raw_log_path", ""),
                    row.get("redacted_log_path", ""),
                )
            )

    if escalations:
        lines.extend(
            [
                "",
                "## Escalations",
                "| Group | Specialist | Type | Reason | Request ID |",
                "|---|---|---|---|---|",
            ]
        )
        for row in escalations:
            lines.append(
                "| {0} | {1} | {2} | {3} | {4} |".format(
                    row.get("group_id", ""),
                    row.get("specialist_id", ""),
                    row.get("type", ""),
                    str(row.get("reason", "")).replace("|", "/"),
                    row.get("request_id", ""),
                )
            )

    lines.extend(["", "## Recovery Commands"])
    for row in contributions:
        if row.get("valid"):
            continue
        group_id = str(row.get("group_id") or "")
        if not group_id:
            continue
        lines.append(
            '- `agents-inc dispatch --project-id {0} --group {1} --objective "{2}" --locking-mode auto`'.format(
                project_id,
                group_id,
                message.replace('"', "'"),
            )
        )

    lines.extend(
        [
            (
                '- `agents-inc orchestrator-reply --project-id {0} --message "{1}" '
                "--meeting-enabled --require-negotiation true`"
            ).format(
                project_id,
                message.replace('"', "'"),
            ),
            "",
            "## Artifact Index",
            f"- turn_dir: `{turn_dir}`",
            f"- blocked reasons: `{turn_dir / 'blocked-reasons.json'}`",
            f"- quality report: `{turn_dir / 'final-answer-quality.json'}`",
        ]
    )
    return "\n".join(lines).strip() + "\n"


def render_key_points(
    *,
    project_id: str,
    selected_groups: List[str],
    final_report_path: Path,
    turn_dir: Path,
) -> str:
    lines = [
        f"project_id: {project_id}",
        f"active_groups: {', '.join(selected_groups)}",
        f"full_report_path: {final_report_path}",
        f"turn_dir: {turn_dir}",
    ]
    return "\n".join(lines).strip() + "\n"
