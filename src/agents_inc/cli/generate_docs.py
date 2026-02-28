from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Tuple

from agents_inc.core.fabric_lib import ensure_fabric_root_initialized, resolve_fabric_root, write_text


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate publication-grade inlined fabric reference docs")
    parser.add_argument("--fabric-root", default=None, help="path to fabric root")
    parser.add_argument(
        "--output",
        default="docs/generated/full-template-skill-reference.md",
        help="output markdown path (relative to fabric root unless absolute)",
    )
    parser.add_argument(
        "--include-generated-projects",
        action="store_true",
        help="include generated project skills/manifests in reference",
    )
    return parser.parse_args()


def classify(path: Path, rel: str) -> Tuple[str, str]:
    if rel.startswith("templates/"):
        return ("template", "Template used for generated groups/router")
    if rel.startswith("schemas/"):
        return ("schema", "Validation schema for manifests and dispatch contracts")
    if rel.startswith("catalog/"):
        return ("catalog", "Reusable source-of-truth group/profile/registry metadata")
    if "/skills/" in rel and rel.endswith("SKILL.md"):
        return ("skill", "Operational skill definition for an agent or router")
    if rel.endswith("AGENTS.md"):
        return ("agents", "Group operating contract and policy")
    if rel.endswith("allowlist.yaml"):
        return ("tool-policy", "Command/tool policy for group operations")
    if rel.endswith("handoffs.yaml"):
        return ("handoff", "Intra-group handoff protocol")
    if rel.endswith("manifest.yaml") or rel.endswith("group.yaml"):
        return ("manifest", "Project or group manifest instance")
    return ("resource", "Supporting resource")


def detect_locks(text: str) -> str:
    locks = []
    for line in text.splitlines():
        line = line.strip()
        if "BEGIN_LOCKED:" in line:
            locks.append(line.split("BEGIN_LOCKED:", 1)[1].strip())
    return ", ".join(locks) if locks else "-"


def collect_files(fabric_root: Path, include_generated_projects: bool) -> List[Path]:
    files: List[Path] = []

    for base in ["templates", "schemas", "catalog"]:
        for path in sorted((fabric_root / base).rglob("*")):
            if path.is_file() and not path.name.startswith(".") and not path.name.endswith(".swp"):
                files.append(path)

    if include_generated_projects:
        gen_root = fabric_root / "generated" / "projects"
        if gen_root.exists():
            for path in sorted(gen_root.rglob("*")):
                if not path.is_file():
                    continue
                rel = path.relative_to(fabric_root).as_posix()
                if any(
                    rel.endswith(suffix)
                    for suffix in ["SKILL.md", "AGENTS.md", "allowlist.yaml", "handoffs.yaml", "manifest.yaml", "group.yaml"]
                ) and not path.name.startswith(".") and not path.name.endswith(".swp"):
                    files.append(path)
    return files


def main() -> int:
    args = parse_args()
    try:
        fabric_root = resolve_fabric_root(args.fabric_root)
        ensure_fabric_root_initialized(fabric_root)

        output_path = Path(args.output)
        if not output_path.is_absolute():
            output_path = (fabric_root / output_path).resolve()

        files = collect_files(fabric_root, args.include_generated_projects)
        if not files:
            raise RuntimeError("no files collected for documentation")

        rows = []
        sections = []
        for idx, path in enumerate(files, start=1):
            rel = path.relative_to(fabric_root).as_posix()
            ftype, purpose = classify(path, rel)
            text = path.read_text(encoding="utf-8")
            locks = detect_locks(text)
            validation = "schema-validated" if ftype in {"manifest", "catalog", "tool-policy", "schema"} else "content-reviewed"
            exposure = "group-scoped" if "/generated/projects/" in rel or rel.startswith("templates/") else "source"

            rows.append(
                f"| {idx} | `{rel}` | {ftype} | {purpose} | `{locks}` | {validation} | {exposure} |"
            )

            ext = path.suffix.lstrip(".") or "txt"
            sections.append(
                "\n".join(
                    [
                        f"## {idx}. `{rel}`",
                        "",
                        f"- Type: `{ftype}`",
                        f"- Purpose: {purpose}",
                        f"- Locked Sections: `{locks}`",
                        f"- Validation Check: {validation}",
                        f"- Exposure Policy: {exposure}",
                        "",
                        f"```{ext}",
                        text.rstrip(),
                        "```",
                        "",
                    ]
                )
            )

        now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        doc = "\n".join(
            [
                "# Full Template and Skill Reference",
                "",
                f"Generated at: `{now}`",
                f"Fabric root: `{fabric_root}`",
                f"Include generated projects: `{bool(args.include_generated_projects)}`",
                "",
                "## Scope",
                "This document inventories and inlines templates, schemas, catalog definitions, and selected generated artifacts.",
                "It is intended for publication-grade audit and onboarding readiness checks.",
                "",
                "## Inventory",
                "| # | File | Type | Purpose | Locked Sections | Validation | Exposure |",
                "|---|---|---|---|---|---|---|",
                *rows,
                "",
                "## Inlined Contents",
                *sections,
            ]
        )

        write_text(output_path, doc + "\n")
        print(f"generated: {output_path}")
        print(f"files_included: {len(files)}")
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
