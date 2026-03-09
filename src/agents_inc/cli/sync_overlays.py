from __future__ import annotations

import argparse
from pathlib import Path

from agents_inc.core.fabric_lib import (
    FabricError,
    ensure_fabric_root_initialized,
    load_project_manifest,
    load_yaml,
    merge_locked_sections,
    render_template,
    resolve_fabric_root,
    write_text,
)
from agents_inc.core.persona_tools import synthesize_domain_doctrine, synthesize_expert_profile


def _resolve_head_persona(group: dict) -> dict:
    head = group.get("head", {}) if isinstance(group, dict) else {}
    if not isinstance(head, dict):
        head = {}
    persona = head.get("persona", {})
    if not isinstance(persona, dict):
        persona = {}
    group_id = str(group.get("group_id") or "group").strip() or "group"
    display_name = str(group.get("display_name") or group_id).strip() or group_id
    domain = str(group.get("domain") or "general-domain").strip().replace("-", " ")
    doctrine_rows = synthesize_domain_doctrine(
        success_criteria=group.get("success_criteria"),
        specialists=group.get("specialists"),
        provided_doctrine=persona.get("domain_doctrine"),
    )
    return {
        "persona_id": str(persona.get("persona_id") or f"persona-{group_id}-head").strip(),
        "tone": str(persona.get("tone") or "authoritative").strip(),
        "aggression": str(persona.get("aggression") or "unrestricted-confrontation").strip(),
        "pride_statement": str(
            persona.get("pride_statement")
            or f"I represent {display_name} and defend {domain} standards with uncompromising rigor."
        ).strip(),
        "domain_doctrine": doctrine_rows[:6],
        "challenge_style": str(
            persona.get("challenge_style")
            or "Confront weak assumptions directly and demand stronger domain-grounded support."
        ).strip(),
        "visibility": str(persona.get("visibility") or "moderate").strip(),
        "confidence_threshold": float(persona.get("confidence_threshold") or 0.8),
        "override_policy": str(persona.get("override_policy") or "head-meeting-only").strip(),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sync locked sections from templates into generated project overlays"
    )
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--fabric-root", default=None, help="path to fabric root")
    parser.add_argument(
        "--from-template-version",
        required=False,
        default=None,
        help="only sync groups with matching template_version",
    )
    return parser.parse_args()


def render_agents_template(fabric_root: Path, project_id: str, group: dict) -> str:
    template = (fabric_root / "templates" / "group" / "AGENTS.template.md").read_text(
        encoding="utf-8"
    )
    specialist_block = "\n".join(
        [
            "- `{0}`: {1} (skill: `{2}`)".format(
                s["agent_id"], s["focus"], s.get("effective_skill_name", s["skill_name"])
            )
            for s in group["specialists"]
        ]
    )
    workdir_block = "\n".join(
        [
            "- `generated/projects/{0}/work/{1}/{2}`".format(
                project_id, group["group_id"], s["agent_id"]
            )
            for s in group["specialists"]
        ]
    )
    quality_block = "\n".join(
        ["- `{0}`: `{1}`".format(k, bool(v)) for k, v in group.get("quality_gates", {}).items()]
    )
    deliverable_block = "\n".join(
        [
            "- `{0}` from `{1}`".format(output, s["agent_id"])
            for s in group["specialists"]
            for output in s.get("required_outputs", [])
        ]
    )
    persona = _resolve_head_persona(group)
    doctrine_block = "\n".join(["- {0}".format(item) for item in persona["domain_doctrine"]])
    expert_profile = synthesize_expert_profile(
        group_id=group.get("group_id"),
        display_name=group.get("display_name"),
        domain=group.get("domain"),
        purpose=group.get("purpose") or group.get("head", {}).get("mission"),
        success_criteria=group.get("success_criteria"),
        specialists=group.get("specialists"),
        gate_checks=list((group.get("gate_profile", {}).get("checks", {}) or {}).keys()),
        provided_profile=(group.get("head", {}) or {}).get("expert_profile"),
    )
    expert_protocol_block = "\n".join(
        ["- {0}".format(item) for item in expert_profile["analysis_protocol"]]
    )
    expert_evidence_block = "\n".join(
        ["- {0}".format(item) for item in expert_profile["evidence_hierarchy"]]
    )
    expert_questions_block = "\n".join(
        ["- {0}".format(item) for item in expert_profile["pressure_questions"]]
    )
    expert_refusal_block = "\n".join(
        ["- {0}".format(item) for item in expert_profile["refusal_conditions"]]
    )
    expert_publication_block = "\n".join(
        ["- {0}".format(item) for item in expert_profile["publication_bar"]]
    )
    return render_template(
        template,
        {
            "PROJECT_ID": project_id,
            "GROUP_ID": group["group_id"],
            "DISPLAY_NAME": group["display_name"],
            "TEMPLATE_VERSION": group.get("template_version", "1.0.0"),
            "TOOL_PROFILE": group.get("tool_profile", "default"),
            "HEAD_AGENT_ID": group["head"]["agent_id"],
            "HEAD_SKILL_NAME": group["head"].get(
                "effective_skill_name", group["head"]["skill_name"]
            ),
            "GROUP_MISSION": group["head"].get("mission", ""),
            "HEAD_PERSONA_ID": persona["persona_id"],
            "HEAD_PERSONA_TONE": persona["tone"],
            "HEAD_PERSONA_AGGRESSION": persona["aggression"],
            "HEAD_PERSONA_PRIDE_STATEMENT": persona["pride_statement"],
            "HEAD_PERSONA_DOCTRINE_BLOCK": doctrine_block,
            "HEAD_PERSONA_CHALLENGE_STYLE": persona["challenge_style"],
            "HEAD_PERSONA_VISIBILITY": persona["visibility"],
            "HEAD_PERSONA_CONFIDENCE_THRESHOLD": "{0:.2f}".format(
                float(persona["confidence_threshold"])
            ),
            "HEAD_PERSONA_OVERRIDE_POLICY": persona["override_policy"],
            "HEAD_EXPERT_FIELD_IDENTITY": expert_profile["field_identity"],
            "HEAD_EXPERT_SIGNATURE_COMMITMENT": expert_profile["signature_commitment"],
            "HEAD_EXPERT_ANALYSIS_PROTOCOL_BLOCK": expert_protocol_block,
            "HEAD_EXPERT_EVIDENCE_HIERARCHY_BLOCK": expert_evidence_block,
            "HEAD_EXPERT_PRESSURE_QUESTIONS_BLOCK": expert_questions_block,
            "HEAD_EXPERT_REFUSAL_CONDITIONS_BLOCK": expert_refusal_block,
            "HEAD_EXPERT_PUBLICATION_BAR_BLOCK": expert_publication_block,
            "SPECIALIST_BLOCK": specialist_block,
            "WORKDIR_BLOCK": workdir_block,
            "QUALITY_GATE_BLOCK": quality_block,
            "DELIVERABLE_BLOCK": deliverable_block,
        },
    )


def main() -> int:
    args = parse_args()
    try:
        fabric_root = resolve_fabric_root(args.fabric_root)
        ensure_fabric_root_initialized(fabric_root)
        project_dir, manifest = load_project_manifest(fabric_root, args.project_id)

        template_allowlist = (
            fabric_root / "templates" / "group" / "tools" / "allowlist.template.yaml"
        ).read_text(encoding="utf-8")

        updates = 0
        skipped = 0

        for group_id in manifest.get("selected_groups", []):
            group_entry = manifest.get("groups", {}).get(group_id, {})
            group_manifest_rel = group_entry.get("manifest_path")
            if not group_manifest_rel:
                raise FabricError(f"missing groups.{group_id}.manifest_path in project manifest")
            group_manifest_path = project_dir / group_manifest_rel
            group = load_yaml(group_manifest_path)
            if not isinstance(group, dict):
                raise FabricError(f"invalid group manifest: {group_manifest_path}")

            if (
                args.from_template_version
                and group.get("template_version") != args.from_template_version
            ):
                skipped += 1
                continue

            agents_path = group_manifest_path.parent / "AGENTS.md"
            allowlist_path = group_manifest_path.parent / "tools" / "allowlist.yaml"

            canonical_agents = render_agents_template(fabric_root, manifest["project_id"], group)
            canonical_allowlist = render_template(
                template_allowlist, {"TOOL_PROFILE": group.get("tool_profile", "default")}
            )

            merged_agents = merge_locked_sections(
                agents_path.read_text(encoding="utf-8"), canonical_agents
            )
            merged_allowlist = merge_locked_sections(
                allowlist_path.read_text(encoding="utf-8"), canonical_allowlist
            )

            if merged_agents != agents_path.read_text(encoding="utf-8"):
                write_text(agents_path, merged_agents)
                updates += 1
            if merged_allowlist != allowlist_path.read_text(encoding="utf-8"):
                write_text(allowlist_path, merged_allowlist)
                updates += 1

        print(f"sync complete: updated_files={updates} skipped_groups={skipped}")
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
