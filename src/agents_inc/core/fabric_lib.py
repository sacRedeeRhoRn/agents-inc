"""agents_inc fabric library — domain-level logic and backward-compat shim.

Pure utility functions (now_iso, slugify, load_yaml, build_dispatch_plan, …)
have been moved to agents_inc.core.util.*  They are re-exported here so that
existing ``from agents_inc.core.fabric_lib import X`` call-sites continue to
work without change during the migration.

What stays here (to be split in later phases):
  - Skill frontmatter parsing and validation
  - Group / project / tool-policy schema validation
  - Catalog and project-registry I/O
  - Fabric-root initialisation
  - Skill record collection and managed-dir helpers
  - Locked-section overlay merge
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml

# ── canonical utility imports (single source of truth) ────────────────────
from agents_inc.core.util.constants import (  # noqa: F401  (re-exported)
    BUNDLE_VERSION,
    DEFAULT_INSTALL_TARGET,
    ROUTER_SKILL_NAME,
    SCHEMA_VERSION,
    TEMPLATE_VERSION,
)
from agents_inc.core.util.dispatch import (  # noqa: F401  (re-exported)
    build_dispatch_plan,
    gate_specialist_output,
    resolve_task_execution,
    suggest_groups,
)
from agents_inc.core.util.errors import FabricError  # noqa: F401  (re-exported)
from agents_inc.core.util.fs import (  # noqa: F401  (re-exported)
    atomic_dump_yaml,
    atomic_write,
    copy_dir,
    delete_dir,
    dump_yaml,
    load_yaml,
    load_yaml_map,
    read_text,
    write_text,
)
from agents_inc.core.util.text import (  # noqa: F401  (re-exported)
    ensure_json_serializable,
    ensure_unique_names,
    format_bullet,
    render_template,
    slugify,
    stable_json,
)
from agents_inc.core.util.time import now_iso  # noqa: F401  (re-exported)

# ── module-level constants that stay here for now ─────────────────────────
LOCKED_SECTION_PATTERN = re.compile(
    r"(^[ \t]*(?:#\s*)?BEGIN_LOCKED:(?P<name>[A-Za-z0-9_-]+)[ \t]*\n)"
    r"(?P<body>.*?)"
    r"(^[ \t]*(?:#\s*)?END_LOCKED:(?P=name)[ \t]*$)",
    re.MULTILINE | re.DOTALL,
)
SKILL_ALLOWED_FRONTMATTER_KEYS = {
    "name",
    "version",
    "role",
    "description",
    "scope",
    "inputs",
    "outputs",
    "failure_modes",
    "autouse_triggers",
    "allowed-tools",
    "metadata",
}
SKILL_REQUIRED_FRONTMATTER_KEYS = {
    "name",
    "version",
    "role",
    "description",
    "scope",
    "inputs",
    "outputs",
    "failure_modes",
    "autouse_triggers",
}
REQUIRED_FABRIC_DIRS = ["catalog", "templates", "schemas", "generated/projects"]


@dataclass
class SkillRecord:
    skill_name: str
    source_dir: Path
    relative_dir: str
    group_id: str
    role: str  # head|specialist|router


# ── Package path helpers ───────────────────────────────────────────────────


def package_root() -> Path:
    return Path(__file__).resolve().parents[1]


def package_resources_root() -> Path:
    return package_root() / "resources"


# ── Fabric-root resolution ─────────────────────────────────────────────────


def default_fabric_root(cwd: Optional[Path] = None) -> Path:
    base = (cwd or Path.cwd()).resolve()
    if (
        (base / "catalog").exists()
        and (base / "templates").exists()
        and (base / "schemas").exists()
    ):
        return base
    if (base / "agent_group_fabric").exists():
        candidate = (base / "agent_group_fabric").resolve()
        if (candidate / "catalog").exists() and (candidate / "templates").exists():
            return candidate
    return (base / "agent_group_fabric").resolve()


def resolve_fabric_root(fabric_root: Optional[str]) -> Path:
    if fabric_root:
        return Path(fabric_root).expanduser().resolve()
    return default_fabric_root()


def ensure_fabric_root_initialized(fabric_root: Path) -> None:
    fabric_root.mkdir(parents=True, exist_ok=True)
    resources_root = package_resources_root()
    if not resources_root.exists():
        raise FabricError(f"package resources missing: {resources_root}")

    for rel in ["catalog", "templates", "schemas"]:
        src = resources_root / rel
        dst = fabric_root / rel
        if not dst.exists():
            copy_dir(src, dst)

    (fabric_root / "generated" / "projects").mkdir(parents=True, exist_ok=True)

    project_registry = fabric_root / "catalog" / "project-registry.yaml"
    if not project_registry.exists():
        dump_yaml(project_registry, {"router_skill_name": ROUTER_SKILL_NAME, "projects": {}})


# ── Skill helpers ──────────────────────────────────────────────────────────


def make_skill_name(project_id: str, group_id: str, agent_id: str) -> str:
    base = "{0}-{1}--{2}".format(slugify(group_id), slugify(agent_id), slugify(project_id))
    if len(base) <= 64:
        return base
    digest = hashlib.sha1(base.encode("utf-8")).hexdigest()[:8]
    keep = 64 - len(digest) - 1
    return base[:keep].rstrip("-") + "-" + digest


def parse_skill_frontmatter(path: Path) -> Tuple[dict, str]:
    text = read_text(path)
    if not text.startswith("---\n"):
        raise FabricError(f"{path}: missing YAML frontmatter")
    end = text.find("\n---", 4)
    if end == -1:
        raise FabricError(f"{path}: malformed YAML frontmatter")
    frontmatter_text = text[4:end]
    body = text[end + 4 :].lstrip("\n")
    frontmatter = yaml.safe_load(frontmatter_text)
    if not isinstance(frontmatter, dict):
        raise FabricError(f"{path}: frontmatter must parse to a mapping")
    return frontmatter, body


def validate_skill_markdown(path: Path) -> List[str]:
    errors: List[str] = []
    try:
        frontmatter, _ = parse_skill_frontmatter(path)
    except Exception as exc:  # noqa: BLE001
        return [str(exc)]

    missing = sorted(SKILL_REQUIRED_FRONTMATTER_KEYS - set(frontmatter.keys()))
    if missing:
        errors.append(
            "{0}: missing required frontmatter key(s): {1}".format(path, ", ".join(missing))
        )

    unexpected = sorted(set(frontmatter.keys()) - SKILL_ALLOWED_FRONTMATTER_KEYS)
    if unexpected:
        errors.append(
            "{0}: unexpected frontmatter key(s): {1}".format(path, ", ".join(unexpected))
        )

    name = frontmatter.get("name")
    version = frontmatter.get("version")
    role = frontmatter.get("role")
    description = frontmatter.get("description")
    scope = frontmatter.get("scope")
    inputs = frontmatter.get("inputs")
    outputs = frontmatter.get("outputs")
    failure_modes = frontmatter.get("failure_modes")
    autouse_triggers = frontmatter.get("autouse_triggers")

    if not isinstance(name, str) or not re.match(r"^[a-z0-9-]+$", name):
        errors.append(f"{path}: frontmatter.name must be hyphen-case")
    elif len(name) > 64:
        errors.append(f"{path}: frontmatter.name too long ({len(name)} > 64)")

    if not isinstance(version, str) or not re.match(r"^[0-9]+\.[0-9]+(?:\.[0-9]+)?$", version):
        errors.append(f"{path}: frontmatter.version must be semantic version-like")

    if role not in {"head", "specialist", "router"}:
        errors.append(f"{path}: frontmatter.role must be one of head|specialist|router")

    if not isinstance(description, str) or len(description.strip()) < 10:
        errors.append(f"{path}: frontmatter.description must be a meaningful string")

    if not isinstance(scope, str) or len(scope.strip()) < 3:
        errors.append(f"{path}: frontmatter.scope must be a meaningful string")

    if not isinstance(inputs, list) or not inputs:
        errors.append(f"{path}: frontmatter.inputs must be non-empty list")

    if not isinstance(outputs, list) or not outputs:
        errors.append(f"{path}: frontmatter.outputs must be non-empty list")

    if not isinstance(failure_modes, list) or not failure_modes:
        errors.append(f"{path}: frontmatter.failure_modes must be non-empty list")

    if not isinstance(autouse_triggers, list) or not autouse_triggers:
        errors.append(f"{path}: frontmatter.autouse_triggers must be non-empty list")

    return errors


# ── Group / project / tool-policy validation ──────────────────────────────


def ensure_group_shape(group: dict, source: str = "<unknown>") -> List[str]:
    errors: List[str] = []
    required = [
        "schema_version",
        "group_id",
        "display_name",
        "template_version",
        "domain",
        "purpose",
        "success_criteria",
        "head",
        "specialists",
        "required_artifacts",
        "gate_profile",
        "tool_profile",
        "default_workdirs",
        "quality_gates",
    ]
    for key in required:
        if key not in group:
            errors.append(f"{source}: missing '{key}'")

    if errors:
        return errors

    if str(group.get("schema_version") or "") != SCHEMA_VERSION:
        errors.append(f"{source}: schema_version must be '{SCHEMA_VERSION}'")

    group_id = group.get("group_id")
    if not isinstance(group_id, str) or not re.match(r"^[a-z0-9-]+$", group_id):
        errors.append(f"{source}: group_id must match ^[a-z0-9-]+$")

    if not isinstance(group.get("display_name"), str) or len(group["display_name"].strip()) < 3:
        errors.append(f"{source}: display_name must be a non-trivial string")

    if not isinstance(group.get("purpose"), str) or len(group["purpose"].strip()) < 8:
        errors.append(f"{source}: purpose must be a meaningful string")

    success = group.get("success_criteria")
    if not isinstance(success, list) or not success:
        errors.append(f"{source}: success_criteria must be non-empty list")

    head = group.get("head")
    if not isinstance(head, dict):
        errors.append(f"{source}: head must be a map")
    else:
        for head_key in ["agent_id", "skill_name", "mission", "publish_contract"]:
            if not head.get(head_key):
                errors.append(f"{source}: head.{head_key} is required")
        publish_contract = head.get("publish_contract")
        if not isinstance(publish_contract, dict):
            errors.append(f"{source}: head.publish_contract must be a map")
        else:
            required_exposed = publish_contract.get("exposed_required")
            if not isinstance(required_exposed, list) or not required_exposed:
                errors.append(
                    f"{source}: head.publish_contract.exposed_required must be non-empty list"
                )
            if publish_contract.get("visibility") not in {"group-only", "full"}:
                errors.append(
                    f"{source}: head.publish_contract.visibility must be 'group-only' or 'full'"
                )

    specialists = group.get("specialists")
    if not isinstance(specialists, list) or len(specialists) < 4:
        errors.append(f"{source}: specialists must be a list with at least 4 entries")
        return errors

    specialist_ids: set = set()
    all_agent_ids: set = set()
    specialist_roles: set = set()

    if isinstance(head, dict) and head.get("agent_id"):
        all_agent_ids.add(head["agent_id"])

    for idx, specialist in enumerate(specialists):
        label = f"{source}: specialists[{idx}]"
        if not isinstance(specialist, dict):
            errors.append(f"{label} must be a map")
            continue
        for spec_key in [
            "agent_id",
            "skill_name",
            "role",
            "focus",
            "required_references",
            "required_outputs",
            "contract",
            "depends_on",
        ]:
            if spec_key not in specialist:
                errors.append(f"{label}: missing '{spec_key}'")

        agent_id = specialist.get("agent_id")
        if isinstance(agent_id, str):
            if agent_id in specialist_ids:
                errors.append(f"{label}: duplicate specialist agent_id '{agent_id}'")
            specialist_ids.add(agent_id)
            if agent_id in all_agent_ids:
                errors.append(f"{label}: agent_id '{agent_id}' conflicts with existing agent")
            all_agent_ids.add(agent_id)
        else:
            errors.append(f"{label}: agent_id must be string")

        role = specialist.get("role")
        if isinstance(role, str):
            specialist_roles.add(role)
        else:
            errors.append(f"{label}: role must be string")

        refs = specialist.get("required_references", [])
        outs = specialist.get("required_outputs", [])
        if not isinstance(refs, list) or not refs:
            errors.append(f"{label}: required_references must be non-empty list")
        if not isinstance(outs, list) or not outs:
            errors.append(f"{label}: required_outputs must be non-empty list")
        elif "handoff.json" not in [str(x) for x in outs]:
            errors.append(f"{label}: required_outputs must include handoff.json")

        execution = specialist.get("execution", {})
        if execution and not isinstance(execution, dict):
            errors.append(f"{label}.execution must be a map")
        elif isinstance(execution, dict):
            if "web_search_enabled" in execution and not isinstance(
                execution["web_search_enabled"], bool
            ):
                errors.append(f"{label}.execution.web_search_enabled must be boolean")

        contract = specialist.get("contract")
        if not isinstance(contract, dict):
            errors.append(f"{label}: contract must be map")
        else:
            cin = contract.get("inputs")
            cout = contract.get("outputs")
            if not isinstance(cin, list) or not cin:
                errors.append(f"{label}: contract.inputs must be non-empty list")
            if not isinstance(cout, list) or not cout:
                errors.append(f"{label}: contract.outputs must be non-empty list")
            if not isinstance(contract.get("output_schema"), str) or not contract.get(
                "output_schema"
            ):
                errors.append(f"{label}: contract.output_schema is required")

    specialist_id_set = {
        s.get("agent_id") for s in specialists if isinstance(s, dict) and s.get("agent_id")
    }
    for idx, specialist in enumerate(specialists):
        deps = specialist.get("depends_on", []) if isinstance(specialist, dict) else []
        if deps and not isinstance(deps, list):
            errors.append(f"{source}: specialists[{idx}].depends_on must be a list")
            continue
        for dep in deps:
            if not isinstance(dep, dict):
                errors.append(
                    f"{source}: specialists[{idx}].depends_on entries must be maps"
                )
                continue
            dep_agent = dep.get("agent_id")
            if dep_agent not in specialist_id_set:
                errors.append(
                    f"{source}: specialists[{idx}] depends_on unknown agent '{dep_agent}'"
                )
            required_artifacts = dep.get("required_artifacts")
            if not isinstance(required_artifacts, list) or not required_artifacts:
                errors.append(
                    f"{source}: specialists[{idx}].depends_on.required_artifacts "
                    "must be non-empty list"
                )
            validate_with = dep.get("validate_with")
            if not isinstance(validate_with, str) or not (
                validate_with in {"exists", "json-parse"}
                or validate_with.startswith("schema:")
            ):
                errors.append(
                    f"{source}: specialists[{idx}].depends_on.validate_with must be "
                    "exists|json-parse|schema:<id>"
                )
            on_missing = dep.get("on_missing")
            if on_missing not in {"request-rerun", "regenerate", "block"}:
                errors.append(
                    f"{source}: specialists[{idx}].depends_on.on_missing must be "
                    "request-rerun|regenerate|block"
                )

    for role in {"domain-core", "web-research", "integration", "evidence-review", "repro-qa"}:
        if role not in specialist_roles:
            errors.append(f"{source}: specialists must include role '{role}'")

    interaction = group.get("interaction", {})
    if interaction:
        if not isinstance(interaction, dict):
            errors.append(f"{source}: interaction must be a map")
        else:
            mode = interaction.get("mode")
            if mode and mode not in {"interactive-separated"}:
                errors.append(
                    f"{source}: interaction.mode must be 'interactive-separated' when provided"
                )
            linked = interaction.get("linked_groups")
            if linked is not None and (
                not isinstance(linked, list) or not all(isinstance(x, str) for x in linked)
            ):
                errors.append(f"{source}: interaction.linked_groups must be a list of strings")

    execution_defaults = group.get("execution_defaults", {})
    if not isinstance(execution_defaults, dict):
        errors.append(f"{source}: execution_defaults must be a map")
    else:
        if "web_search_enabled" not in execution_defaults:
            errors.append(f"{source}: execution_defaults.web_search_enabled is required")
        elif not isinstance(execution_defaults.get("web_search_enabled"), bool):
            errors.append(f"{source}: execution_defaults.web_search_enabled must be boolean")

    required_artifacts = group.get("required_artifacts")
    if not isinstance(required_artifacts, dict):
        errors.append(f"{source}: required_artifacts must be a map")

    gate_profile = group.get("gate_profile")
    if not isinstance(gate_profile, dict):
        errors.append(f"{source}: gate_profile must be a map")
    else:
        if not isinstance(gate_profile.get("profile_id"), str) or not gate_profile.get(
            "profile_id"
        ):
            errors.append(f"{source}: gate_profile.profile_id is required")
        if not isinstance(
            gate_profile.get("specialist_output_schema"), str
        ) or not gate_profile.get("specialist_output_schema"):
            errors.append(f"{source}: gate_profile.specialist_output_schema is required")
        if not isinstance(gate_profile.get("checks"), dict):
            errors.append(f"{source}: gate_profile.checks must be a map")

    workdirs = group.get("default_workdirs")
    if not isinstance(workdirs, list) or not workdirs:
        errors.append(f"{source}: default_workdirs must be non-empty list")

    gates = group.get("quality_gates")
    required_gates = [
        "citation_required",
        "unresolved_claims_block",
        "peer_check_required",
        "consistency_required",
        "scope_required",
        "reproducibility_required",
    ]
    if not isinstance(gates, dict):
        errors.append(f"{source}: quality_gates must be a map")
    else:
        for gate in required_gates:
            if gate not in gates:
                errors.append(f"{source}: quality_gates missing '{gate}'")
            elif not isinstance(gates[gate], bool):
                errors.append(f"{source}: quality_gates.{gate} must be boolean")

    return errors


def ensure_tool_policy_shape(policy: dict, source: str = "<unknown>") -> List[str]:
    errors: List[str] = []
    required = [
        "allowed_prefixes",
        "escalation_prefixes",
        "forbidden_prefixes",
        "wrapper_required_prefixes",
    ]
    for key in required:
        if key not in policy:
            errors.append(f"{source}: missing '{key}'")
        elif not isinstance(policy[key], list):
            errors.append(f"{source}: '{key}' must be a list")
    return errors


def ensure_project_shape(project: dict, source: str = "<unknown>") -> List[str]:
    errors: List[str] = []
    required = [
        "schema_version",
        "project_id",
        "selected_groups",
        "install_targets",
        "router_skill_name",
        "bundle_version",
        "template_versions",
        "overlays",
        "visibility",
    ]
    for key in required:
        if key not in project:
            errors.append(f"{source}: missing '{key}'")
    if errors:
        return errors

    if str(project.get("schema_version") or "") != SCHEMA_VERSION:
        errors.append(f"{source}: schema_version must be '{SCHEMA_VERSION}'")

    if not isinstance(project.get("project_id"), str) or not re.match(
        r"^[a-z0-9-]+$", project["project_id"]
    ):
        errors.append(f"{source}: project_id must match ^[a-z0-9-]+$")

    groups = project.get("selected_groups")
    if not isinstance(groups, list) or not groups:
        errors.append(f"{source}: selected_groups must be non-empty list")

    install_targets = project.get("install_targets")
    if not isinstance(install_targets, dict) or "codex_skill_dir" not in install_targets:
        errors.append(f"{source}: install_targets.codex_skill_dir is required")

    overlays = project.get("overlays")
    if not isinstance(overlays, dict):
        errors.append(f"{source}: overlays must be map")
    else:
        if not isinstance(overlays.get("allow_project_overrides"), bool):
            errors.append(f"{source}: overlays.allow_project_overrides must be bool")
        protected = overlays.get("protected_sections")
        if not isinstance(protected, list) or not protected:
            errors.append(f"{source}: overlays.protected_sections must be non-empty list")

    visibility = project.get("visibility")
    if visibility is not None:
        if not isinstance(visibility, dict):
            errors.append(f"{source}: visibility must be map")
        else:
            if visibility.get("mode") not in {"group-only", "full"}:
                errors.append(f"{source}: visibility.mode must be 'group-only' or 'full'")
            if not isinstance(visibility.get("audit_override"), bool):
                errors.append(f"{source}: visibility.audit_override must be bool")

    groups_map = project.get("groups", {})
    if groups_map and isinstance(groups_map, dict):
        for group_id, payload in groups_map.items():
            if not isinstance(payload, dict):
                errors.append(f"{source}: groups.{group_id} must be map")
                continue
            if "manifest_path" not in payload:
                errors.append(f"{source}: groups.{group_id}.manifest_path is required")
            if (
                "skill_dirs" not in payload
                or not isinstance(payload["skill_dirs"], list)
                or not payload["skill_dirs"]
            ):
                errors.append(f"{source}: groups.{group_id}.skill_dirs must be non-empty list")
            if "head_skill_dir" in payload and not isinstance(payload["head_skill_dir"], str):
                errors.append(f"{source}: groups.{group_id}.head_skill_dir must be string")
            if "specialist_skill_dirs" in payload and not isinstance(
                payload["specialist_skill_dirs"], list
            ):
                errors.append(f"{source}: groups.{group_id}.specialist_skill_dirs must be list")

    return errors


# ── Catalog I/O ────────────────────────────────────────────────────────────


def load_group_catalog(fabric_root: Path) -> Dict[str, dict]:
    catalog_dir = fabric_root / "catalog" / "groups"
    out: Dict[str, dict] = {}
    for path in sorted(catalog_dir.glob("*.yaml")):
        data = load_yaml(path)
        if not isinstance(data, dict):
            raise FabricError(f"invalid yaml object: {path}")
        gid = data.get("group_id")
        if not gid:
            raise FabricError(f"group manifest missing group_id: {path}")
        out[gid] = data
    return out


def load_profiles(fabric_root: Path) -> Dict[str, dict]:
    profile_dir = fabric_root / "catalog" / "profiles"
    out: Dict[str, dict] = {}
    for path in sorted(profile_dir.glob("*.yaml")):
        data = load_yaml(path)
        if not isinstance(data, dict):
            raise FabricError(f"invalid profile yaml object: {path}")
        profile_id = data.get("profile_id")
        if not profile_id:
            raise FabricError(f"profile missing profile_id: {path}")
        out[profile_id] = data
    return out


def select_groups(
    available_groups: Dict[str, dict],
    profiles: Dict[str, dict],
    groups_csv: Optional[str],
    profile_id: Optional[str],
) -> List[str]:
    selected: List[str] = []
    if groups_csv:
        for raw in groups_csv.split(","):
            gid = raw.strip()
            if gid:
                selected.append(gid)

    if profile_id:
        if profile_id not in profiles:
            raise FabricError(f"unknown profile: {profile_id}")
        profile_groups = profiles[profile_id].get("groups", [])
        if not isinstance(profile_groups, list):
            raise FabricError(f"profile '{profile_id}' groups must be a list")
        selected.extend([str(item) for item in profile_groups])

    deduped: List[str] = []
    seen: set = set()
    for gid in selected:
        if gid not in seen:
            deduped.append(gid)
            seen.add(gid)

    if not deduped:
        raise FabricError("no groups selected: provide --groups and/or --profile")

    missing = [gid for gid in deduped if gid not in available_groups]
    if missing:
        raise FabricError("unknown groups: " + ", ".join(missing))
    return deduped


def load_project_registry(fabric_root: Path) -> dict:
    path = fabric_root / "catalog" / "project-registry.yaml"
    if not path.exists():
        return {"router_skill_name": ROUTER_SKILL_NAME, "projects": {}}
    data = load_yaml(path)
    if not isinstance(data, dict):
        raise FabricError(f"invalid project registry: {path}")
    if "projects" not in data or not isinstance(data["projects"], dict):
        data["projects"] = {}
    if "router_skill_name" not in data:
        data["router_skill_name"] = ROUTER_SKILL_NAME
    return data


def save_project_registry(fabric_root: Path, registry: dict) -> None:
    dump_yaml(fabric_root / "catalog" / "project-registry.yaml", registry)


def upsert_project_registry_entry(
    fabric_root: Path,
    project_id: str,
    selected_groups: List[str],
    manifest_rel: str,
) -> None:
    registry = load_project_registry(fabric_root)
    registry.setdefault("projects", {})[project_id] = {
        "manifest_path": manifest_rel,
        "selected_groups": selected_groups,
        "updated_at": now_iso(),
    }
    save_project_registry(fabric_root, registry)


def remove_project_registry_entry(fabric_root: Path, project_id: str) -> None:
    registry = load_project_registry(fabric_root)
    projects = registry.get("projects", {})
    if isinstance(projects, dict) and project_id in projects:
        projects.pop(project_id, None)
        registry["projects"] = projects
        save_project_registry(fabric_root, registry)


def load_project_manifest(fabric_root: Path, project_id: str) -> Tuple[Path, dict]:
    project_dir = fabric_root / "generated" / "projects" / slugify(project_id)
    manifest_path = project_dir / "manifest.yaml"
    manifest = load_yaml(manifest_path)
    if not isinstance(manifest, dict):
        raise FabricError(f"invalid project manifest: {manifest_path}")
    return project_dir, manifest


# ── Skill record collection ────────────────────────────────────────────────


def collect_project_skill_records(
    project_dir: Path,
    manifest: dict,
    include_specialists: bool,
    groups: Optional[List[str]] = None,
    specialist_groups: Optional[List[str]] = None,
) -> List[SkillRecord]:
    records: List[SkillRecord] = []
    manifest_groups = manifest.get("groups", {})
    if not isinstance(manifest_groups, dict):
        return records

    available_group_ids = [str(group_id) for group_id in manifest_groups.keys()]
    head_group_set = set(available_group_ids)
    if isinstance(groups, list) and groups:
        head_group_set = {str(g).strip() for g in groups if str(g).strip()}

    specialist_group_set: set = set()
    if include_specialists:
        if isinstance(specialist_groups, list) and specialist_groups:
            specialist_group_set = {str(g).strip() for g in specialist_groups if str(g).strip()}
        else:
            specialist_group_set = set(head_group_set)

    for group_id, payload in manifest_groups.items():
        if not isinstance(payload, dict):
            continue
        if group_id not in head_group_set and group_id not in specialist_group_set:
            continue

        head_dir = payload.get("head_skill_dir")
        spec_dirs = payload.get("specialist_skill_dirs", [])
        selected_dirs: List[Tuple[str, str]] = []
        if head_dir and group_id in head_group_set:
            selected_dirs.append((head_dir, "head"))
        if include_specialists and group_id in specialist_group_set:
            for rel in spec_dirs:
                selected_dirs.append((rel, "specialist"))

        # Backward compatibility: old manifests only have skill_dirs.
        if not selected_dirs:
            for rel in payload.get("skill_dirs", []):
                role = "head" if rel.endswith("-head") else "specialist"
                if role == "specialist" and not include_specialists:
                    continue
                selected_dirs.append((rel, role))

        for rel, role in selected_dirs:
            source_dir = project_dir / rel
            skill_md = source_dir / "SKILL.md"
            if not skill_md.exists():
                raise FabricError(f"missing SKILL.md: {skill_md}")
            frontmatter, _ = parse_skill_frontmatter(skill_md)
            skill_name = frontmatter.get("name")
            if not isinstance(skill_name, str):
                raise FabricError(f"invalid skill name in {skill_md}")
            records.append(
                SkillRecord(
                    skill_name=skill_name,
                    source_dir=source_dir,
                    relative_dir=rel,
                    group_id=group_id,
                    role=role,
                )
            )
    return records


def find_managed_skill_dirs(
    target: Path, marker_file: str = ".fabric-managed.json"
) -> List[Path]:
    if not target.exists():
        return []
    out: List[Path] = []
    for entry in sorted(target.iterdir()):
        if not entry.is_dir():
            continue
        if (entry / marker_file).exists():
            out.append(entry)
    return out


# ── Locked-section overlay helpers ────────────────────────────────────────


def extract_locked_sections(text: str) -> Dict[str, str]:
    sections: Dict[str, str] = {}
    for match in LOCKED_SECTION_PATTERN.finditer(text):
        name = match.group("name")
        sections[name] = match.group(0)
    return sections


def merge_locked_sections(existing_text: str, canonical_text: str) -> str:
    canonical = extract_locked_sections(canonical_text)
    merged = existing_text
    for name, replacement_block in canonical.items():
        pattern = re.compile(
            r"^[ \t]*(?:#\s*)?BEGIN_LOCKED:{0}[ \t]*\n.*?"
            r"^[ \t]*(?:#\s*)?END_LOCKED:{0}[ \t]*$".format(re.escape(name)),
            re.MULTILINE | re.DOTALL,
        )
        if pattern.search(merged):
            merged = pattern.sub(replacement_block, merged)
        else:
            merged = merged.rstrip() + "\n\n" + replacement_block + "\n"
    return merged
