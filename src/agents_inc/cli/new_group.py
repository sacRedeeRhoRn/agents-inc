from __future__ import annotations

import argparse

from agents_inc.core.fabric_lib import (
    FabricError,
    TEMPLATE_VERSION,
    dump_yaml,
    ensure_fabric_root_initialized,
    resolve_fabric_root,
    slugify,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a new group manifest template")
    parser.add_argument("--group-id", required=True, help="hyphen-case group id")
    parser.add_argument("--display-name", required=True, help="human-readable group title")
    parser.add_argument("--domain", required=True, help="domain label, e.g. materials-research")
    parser.add_argument("--fabric-root", default=None, help="path to fabric root")
    parser.add_argument("--force", action="store_true", help="overwrite existing manifest")
    return parser.parse_args()


def build_manifest(group_id: str, display_name: str, domain: str) -> dict:
    return {
        "group_id": group_id,
        "display_name": display_name,
        "template_version": TEMPLATE_VERSION,
        "domain": domain,
        "head": {
            "agent_id": f"{group_id}-head",
            "skill_name": f"grp-{group_id}-head",
            "mission": f"Coordinate specialist outputs for {display_name}.",
        },
        "specialists": [
            {
                "agent_id": "core-specialist",
                "skill_name": f"grp-{group_id}-core",
                "focus": "Primary expert analysis for the group domain",
                "required_references": ["references/domain-core.md"],
                "required_outputs": ["assumptions.md", "claims_with_citations.md"],
                "execution": {
                    "remote_transport": "local",
                    "scheduler": "local",
                    "hardware": "cpu",
                    "requires_gpu": False,
                },
            },
            {
                "agent_id": "review-specialist",
                "skill_name": f"grp-{group_id}-review",
                "focus": "Critical review and consistency checks",
                "depends_on": ["core-specialist"],
                "required_references": ["references/review-core.md"],
                "required_outputs": ["review_notes.md", "claims_with_citations.md"],
                "execution": {
                    "remote_transport": "local",
                    "scheduler": "local",
                    "hardware": "cpu",
                    "requires_gpu": False,
                },
            },
        ],
        "interaction": {
            "mode": "interactive-separated",
            "linked_groups": [],
        },
        "execution_defaults": {
            "remote_transport": "local",
            "schedulers": ["local"],
            "hardware": ["cpu"],
        },
        "tool_profile": "default",
        "default_workdirs": ["inputs", "analysis", "outputs"],
        "quality_gates": {
            "citation_required": True,
            "unresolved_claims_block": True,
            "peer_check_required": True,
            "consistency_required": True,
            "scope_required": True,
            "reproducibility_required": True,
        },
    }


def main() -> int:
    args = parse_args()
    try:
        fabric_root = resolve_fabric_root(args.fabric_root)
        ensure_fabric_root_initialized(fabric_root)
        group_id = slugify(args.group_id)
        path = fabric_root / "catalog" / "groups" / f"{group_id}.yaml"
        if path.exists() and not args.force:
            raise FabricError(f"manifest already exists: {path} (use --force to overwrite)")

        manifest = build_manifest(group_id, args.display_name.strip(), args.domain.strip())
        dump_yaml(path, manifest)
        print(f"created group manifest: {path}")
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
