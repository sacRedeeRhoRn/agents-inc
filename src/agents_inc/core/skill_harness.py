from __future__ import annotations

from pathlib import Path
from typing import List

from agents_inc.core.fabric_lib import parse_skill_frontmatter


def validate_skill_contract(path: Path) -> List[str]:
    errors: List[str] = []
    try:
        frontmatter, body = parse_skill_frontmatter(path)
    except Exception as exc:  # noqa: BLE001
        return [str(exc)]

    role = str(frontmatter.get("role") or "")
    text = body.lower()

    if role == "head":
        for token in ["exposed/summary.md", "exposed/handoff.json", "integration_notes"]:
            if token not in text and token.replace("_", " ") not in text:
                errors.append(f"{path}: head skill body missing required contract token '{token}'")
    elif role == "specialist":
        for token in ["work.md", "handoff.json"]:
            if token not in text:
                errors.append(
                    f"{path}: specialist skill body missing required contract token '{token}'"
                )
    elif role == "router":
        if "use $research-router" not in text:
            errors.append(f"{path}: router skill must include canonical usage line")

    metadata = frontmatter.get("metadata")
    if isinstance(metadata, dict):
        refs = metadata.get("references", [])
        if isinstance(refs, list):
            for ref in refs:
                candidate = path.parent / str(ref)
                if not candidate.exists():
                    errors.append(f"{path}: metadata reference not found: {candidate}")

    return errors


def skill_card(path: Path) -> dict:
    frontmatter, _ = parse_skill_frontmatter(path)
    return {
        "path": str(path),
        "name": frontmatter.get("name", ""),
        "role": frontmatter.get("role", ""),
        "version": frontmatter.get("version", ""),
        "description": frontmatter.get("description", ""),
    }
