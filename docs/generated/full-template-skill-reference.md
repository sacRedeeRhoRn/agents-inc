# Full Template and Skill Reference

Generated at: `2026-02-28T15:37:55Z`
Fabric root: `/Users/moon.s.june/Documents/Playground/agent_group_fabric`
Include generated projects: `True`

## Scope
This document inventories and inlines templates, schemas, catalog definitions, and selected generated artifacts.
It is intended for publication-grade audit and onboarding readiness checks.

## Inventory
| # | File | Type | Purpose | Locked Sections | Validation | Exposure |
|---|---|---|---|---|---|---|
| 1 | `templates/group/AGENTS.template.md` | template | Template used for generated groups/router | `safety_policy, citation_gate, routing_audit, exposure_policy` | content-reviewed | group-scoped |
| 2 | `templates/group/handoffs.template.yaml` | template | Template used for generated groups/router | `-` | content-reviewed | group-scoped |
| 3 | `templates/group/references/citation-policy.template.md` | template | Template used for generated groups/router | `-` | content-reviewed | group-scoped |
| 4 | `templates/group/references/gate-checklist.template.md` | template | Template used for generated groups/router | `-` | content-reviewed | group-scoped |
| 5 | `templates/group/skills/head/SKILL.template.md` | template | Template used for generated groups/router | `-` | content-reviewed | group-scoped |
| 6 | `templates/group/skills/specialist/SKILL.template.md` | template | Template used for generated groups/router | `-` | content-reviewed | group-scoped |
| 7 | `templates/group/tools/allowlist.template.yaml` | template | Template used for generated groups/router | `tool_restrictions` | content-reviewed | group-scoped |
| 8 | `templates/group/tools/wrappers/README.txt` | template | Template used for generated groups/router | `-` | content-reviewed | group-scoped |
| 9 | `templates/router/research-router/SKILL.template.md` | template | Template used for generated groups/router | `-` | content-reviewed | group-scoped |
| 10 | `schemas/dispatch.schema.yaml` | schema | Validation schema for manifests and dispatch contracts | `-` | schema-validated | source |
| 11 | `schemas/group.schema.yaml` | schema | Validation schema for manifests and dispatch contracts | `-` | schema-validated | source |
| 12 | `schemas/project.schema.yaml` | schema | Validation schema for manifests and dispatch contracts | `-` | schema-validated | source |
| 13 | `schemas/tool_policy.schema.yaml` | schema | Validation schema for manifests and dispatch contracts | `-` | schema-validated | source |
| 14 | `catalog/groups/atomistic-hpc-simulation.yaml` | catalog | Reusable source-of-truth group/profile/registry metadata | `-` | schema-validated | source |
| 15 | `catalog/groups/data-curation.yaml` | catalog | Reusable source-of-truth group/profile/registry metadata | `-` | schema-validated | source |
| 16 | `catalog/groups/designer.yaml` | catalog | Reusable source-of-truth group/profile/registry metadata | `-` | schema-validated | source |
| 17 | `catalog/groups/developer.yaml` | catalog | Reusable source-of-truth group/profile/registry metadata | `-` | schema-validated | source |
| 18 | `catalog/groups/literature-intelligence.yaml` | catalog | Reusable source-of-truth group/profile/registry metadata | `-` | schema-validated | source |
| 19 | `catalog/groups/material-engineer.yaml` | catalog | Reusable source-of-truth group/profile/registry metadata | `-` | schema-validated | source |
| 20 | `catalog/groups/material-scientist.yaml` | catalog | Reusable source-of-truth group/profile/registry metadata | `-` | schema-validated | source |
| 21 | `catalog/groups/publication-packaging.yaml` | catalog | Reusable source-of-truth group/profile/registry metadata | `-` | schema-validated | source |
| 22 | `catalog/groups/quality-assurance.yaml` | catalog | Reusable source-of-truth group/profile/registry metadata | `-` | schema-validated | source |
| 23 | `catalog/profiles/experiment-driven.yaml` | catalog | Reusable source-of-truth group/profile/registry metadata | `-` | schema-validated | source |
| 24 | `catalog/profiles/hpc-simulation-core.yaml` | catalog | Reusable source-of-truth group/profile/registry metadata | `-` | schema-validated | source |
| 25 | `catalog/profiles/publication-push.yaml` | catalog | Reusable source-of-truth group/profile/registry metadata | `-` | schema-validated | source |
| 26 | `catalog/profiles/rapid-debug.yaml` | catalog | Reusable source-of-truth group/profile/registry metadata | `-` | schema-validated | source |
| 27 | `catalog/profiles/reproduction-core.yaml` | catalog | Reusable source-of-truth group/profile/registry metadata | `-` | schema-validated | source |
| 28 | `catalog/project-registry.yaml` | catalog | Reusable source-of-truth group/profile/registry metadata | `-` | schema-validated | source |
| 29 | `generated/projects/proj-battery-001/agent-groups/developer/AGENTS.md` | agents | Group operating contract and policy | `safety_policy, citation_gate, routing_audit, exposure_policy` | content-reviewed | source |
| 30 | `generated/projects/proj-battery-001/agent-groups/developer/group.yaml` | manifest | Project or group manifest instance | `-` | schema-validated | source |
| 31 | `generated/projects/proj-battery-001/agent-groups/developer/handoffs.yaml` | handoff | Intra-group handoff protocol | `-` | content-reviewed | source |
| 32 | `generated/projects/proj-battery-001/agent-groups/developer/skills/proj-proj-battery-001-developer-developer-head/SKILL.md` | skill | Operational skill definition for an agent or router | `-` | content-reviewed | source |
| 33 | `generated/projects/proj-battery-001/agent-groups/developer/skills/proj-proj-battery-001-developer-python-expert/SKILL.md` | skill | Operational skill definition for an agent or router | `-` | content-reviewed | source |
| 34 | `generated/projects/proj-battery-001/agent-groups/developer/skills/proj-proj-battery-001-developer-shell-expert/SKILL.md` | skill | Operational skill definition for an agent or router | `-` | content-reviewed | source |
| 35 | `generated/projects/proj-battery-001/agent-groups/developer/skills/proj-proj-battery-001-developer-ssh-remote-ops-expert/SKILL.md` | skill | Operational skill definition for an agent or router | `-` | content-reviewed | source |
| 36 | `generated/projects/proj-battery-001/agent-groups/developer/tools/allowlist.yaml` | tool-policy | Command/tool policy for group operations | `tool_restrictions` | schema-validated | source |
| 37 | `generated/projects/proj-battery-001/agent-groups/material-scientist/AGENTS.md` | agents | Group operating contract and policy | `safety_policy, citation_gate, routing_audit, exposure_policy` | content-reviewed | source |
| 38 | `generated/projects/proj-battery-001/agent-groups/material-scientist/group.yaml` | manifest | Project or group manifest instance | `-` | schema-validated | source |
| 39 | `generated/projects/proj-battery-001/agent-groups/material-scientist/handoffs.yaml` | handoff | Intra-group handoff protocol | `-` | content-reviewed | source |
| 40 | `generated/projects/proj-battery-001/agent-groups/material-scientist/skills/proj-proj-battery-001-material-scientist-atomistic-simu-a6a50b3f/SKILL.md` | skill | Operational skill definition for an agent or router | `-` | content-reviewed | source |
| 41 | `generated/projects/proj-battery-001/agent-groups/material-scientist/skills/proj-proj-battery-001-material-scientist-electronic-str-d41bc6b7/SKILL.md` | skill | Operational skill definition for an agent or router | `-` | content-reviewed | source |
| 42 | `generated/projects/proj-battery-001/agent-groups/material-scientist/skills/proj-proj-battery-001-material-scientist-material-scientist-head/SKILL.md` | skill | Operational skill definition for an agent or router | `-` | content-reviewed | source |
| 43 | `generated/projects/proj-battery-001/agent-groups/material-scientist/skills/proj-proj-battery-001-material-scientist-thermodynamics-6ace8773/SKILL.md` | skill | Operational skill definition for an agent or router | `-` | content-reviewed | source |
| 44 | `generated/projects/proj-battery-001/agent-groups/material-scientist/tools/allowlist.yaml` | tool-policy | Command/tool policy for group operations | `tool_restrictions` | schema-validated | source |
| 45 | `generated/projects/proj-battery-001/agent-groups/quality-assurance/AGENTS.md` | agents | Group operating contract and policy | `safety_policy, citation_gate, routing_audit, exposure_policy` | content-reviewed | source |
| 46 | `generated/projects/proj-battery-001/agent-groups/quality-assurance/group.yaml` | manifest | Project or group manifest instance | `-` | schema-validated | source |
| 47 | `generated/projects/proj-battery-001/agent-groups/quality-assurance/handoffs.yaml` | handoff | Intra-group handoff protocol | `-` | content-reviewed | source |
| 48 | `generated/projects/proj-battery-001/agent-groups/quality-assurance/skills/proj-proj-battery-001-quality-assurance-consistency-auditor/SKILL.md` | skill | Operational skill definition for an agent or router | `-` | content-reviewed | source |
| 49 | `generated/projects/proj-battery-001/agent-groups/quality-assurance/skills/proj-proj-battery-001-quality-assurance-quality-assurance-head/SKILL.md` | skill | Operational skill definition for an agent or router | `-` | content-reviewed | source |
| 50 | `generated/projects/proj-battery-001/agent-groups/quality-assurance/skills/proj-proj-battery-001-quality-assurance-reproducibility-auditor/SKILL.md` | skill | Operational skill definition for an agent or router | `-` | content-reviewed | source |
| 51 | `generated/projects/proj-battery-001/agent-groups/quality-assurance/skills/proj-proj-battery-001-quality-assurance-risk-auditor/SKILL.md` | skill | Operational skill definition for an agent or router | `-` | content-reviewed | source |
| 52 | `generated/projects/proj-battery-001/agent-groups/quality-assurance/tools/allowlist.yaml` | tool-policy | Command/tool policy for group operations | `tool_restrictions` | schema-validated | source |
| 53 | `generated/projects/proj-battery-001/manifest.yaml` | manifest | Project or group manifest instance | `-` | schema-validated | source |

## Inlined Contents
## 1. `templates/group/AGENTS.template.md`

- Type: `template`
- Purpose: Template used for generated groups/router
- Locked Sections: `safety_policy, citation_gate, routing_audit, exposure_policy`
- Validation Check: content-reviewed
- Exposure Policy: group-scoped

```md
# {{DISPLAY_NAME}} - {{PROJECT_ID}}

## Mission
{{GROUP_MISSION}}

## Group Identity
- `group_id`: `{{GROUP_ID}}`
- `template_version`: `{{TEMPLATE_VERSION}}`
- `tool_profile`: `{{TOOL_PROFILE}}`
- `head_agent`: `{{HEAD_AGENT_ID}}`
- `head_skill`: `{{HEAD_SKILL_NAME}}`

## Specialist Roster
{{SPECIALIST_BLOCK}}

## Work Directories
{{WORKDIR_BLOCK}}

## Artifact Partition
- Internal specialist artifacts: `agent-groups/{{GROUP_ID}}/internal/<specialist>/...`
- Exposed group artifacts: `agent-groups/{{GROUP_ID}}/exposed/...`
- Visibility mode is controlled at project manifest level.

## Head Controller Protocol
1. Decompose objective into specialist tasks.
2. Dispatch hybrid execution (parallel for independent tasks, sequential for dependencies).
3. Enforce quality gates before accepting specialist outputs.
4. Merge outputs and publish decision log to exposed artifacts only.

BEGIN_LOCKED:safety_policy
## Safety Policy (Locked)
- Specialists work only inside assigned project workdirs.
- Potentially destructive commands must follow project tool policy and escalation rules.
- Head controller records command intent for each specialist stage.
END_LOCKED:safety_policy

BEGIN_LOCKED:citation_gate
## Citation Gate (Locked)
- Every key claim must include at least one citation.
- Allowed evidence sources: local references and verified web sources.
- If citations are missing for key claims, output status is `BLOCKED_UNCITED`.
- If web evidence is required but unavailable, output status is `BLOCKED_NEEDS_EVIDENCE`.
END_LOCKED:citation_gate

BEGIN_LOCKED:routing_audit
## Routing Audit (Locked)
- Head must record task graph, dependencies, and final merge rationale.
- Cross-domain final decisions require explicit head-controller sign-off.
END_LOCKED:routing_audit

BEGIN_LOCKED:exposure_policy
## Exposure Policy (Locked)
- Group-level outputs are user-visible by default.
- Specialist artifacts remain internal unless explicit audit mode is enabled.
END_LOCKED:exposure_policy

## Expected Deliverables
{{DELIVERABLE_BLOCK}}

## Quality Gates
{{QUALITY_GATE_BLOCK}}
```

## 2. `templates/group/handoffs.template.yaml`

- Type: `template`
- Purpose: Template used for generated groups/router
- Locked Sections: `-`
- Validation Check: content-reviewed
- Exposure Policy: group-scoped

```yaml
group_id: "{{GROUP_ID}}"
head_agent_id: "{{HEAD_AGENT_ID}}"
handoffs:
{{HANDOFF_BLOCK}}
```

## 3. `templates/group/references/citation-policy.template.md`

- Type: `template`
- Purpose: Template used for generated groups/router
- Locked Sections: `-`
- Validation Check: content-reviewed
- Exposure Policy: group-scoped

```md
# Citation Policy

## Allowed evidence
- Local references shipped with the group.
- Verified web sources when local references are insufficient.

## Minimum standard
- Each key claim must have at least one citation.
- Quantitative claims should provide source and context.
- If a claim cannot be supported, mark as unresolved.

## Required output fields
- `claim`
- `citation`
- `confidence`
- `notes`
```

## 4. `templates/group/references/gate-checklist.template.md`

- Type: `template`
- Purpose: Template used for generated groups/router
- Locked Sections: `-`
- Validation Check: content-reviewed
- Exposure Policy: group-scoped

```md
# Hard Gate Checklist

1. Citation gate: all key claims include citations.
2. Consistency gate: assumptions are explicit and contradiction-free.
3. Scope gate: output remains within specialist boundary.
4. Reproducibility gate: steps, parameters, and artifacts are included.

Block conditions:
- Missing citations for key claims -> `BLOCKED_UNCITED`
- Required web evidence unavailable -> `BLOCKED_NEEDS_EVIDENCE`
- Internal contradiction -> `BLOCKED_INCONSISTENT`
- Scope violation -> `BLOCKED_SCOPE`
```

## 5. `templates/group/skills/head/SKILL.template.md`

- Type: `template`
- Purpose: Template used for generated groups/router
- Locked Sections: `-`
- Validation Check: content-reviewed
- Exposure Policy: group-scoped

```md
---
name: {{HEAD_SKILL_NAME}}
description: Orchestrate {{DISPLAY_NAME}} for project {{PROJECT_ID}}. Use when routing objective-level work to specialist agents with strict expert quality gates.
---

# {{DISPLAY_NAME}} Head Controller

## Scope
Route and merge specialist outputs for `{{GROUP_ID}}` in project `{{PROJECT_ID}}`.

## Responsibilities
1. Build a task graph from the objective.
2. Dispatch hybrid execution: parallel for independent branches, sequential for dependencies.
3. Enforce citation/consistency/scope/reproducibility gates.
4. Publish final merged artifact index and decision log.

## Required Inputs
- `objective`
- `project_id`
- `group_id`
- current registry entry in `catalog/project-registry.yaml`

## Execution Contract
- Acquire per-agent workdir lease before write.
- Retry or reroute on lease conflict.
- Reject outputs that fail any hard gate.
- Consolidate specialist internal outputs before publishing group-exposed artifacts.

## Specialists
{{SPECIALIST_SKILL_BLOCK}}

## Output Contract
- `dispatch_plan.json`
- `decision_log.md`
- `artifact_index.md`
```

## 6. `templates/group/skills/specialist/SKILL.template.md`

- Type: `template`
- Purpose: Template used for generated groups/router
- Locked Sections: `-`
- Validation Check: content-reviewed
- Exposure Policy: group-scoped

```md
---
name: {{SPECIALIST_SKILL_NAME}}
description: Specialist agent for {{SPECIALIST_FOCUS}} in {{DISPLAY_NAME}} (project {{PROJECT_ID}}). Use for narrow-domain expert analysis with claim-level citations.
---

# {{SPECIALIST_AGENT_ID}}

## Scope
{{SPECIALIST_FOCUS}}

## Hard Gate Requirements
1. Every key claim must include a citation.
2. Assumptions must be explicit.
3. Output must stay within specialist scope.
4. Reproducibility details are mandatory.

If web evidence is unavailable and needed, return `BLOCKED_NEEDS_EVIDENCE`.

## Required References
{{SPECIALIST_REFERENCE_BLOCK}}

## Required Outputs
{{SPECIALIST_OUTPUT_BLOCK}}

## Response Format
- `status`: `PASS` or blocked reason.
- `assumptions`
- `claims_with_citations`
- `repro_steps`
- `artifact_paths`

## Artifact Scope
- Write specialist artifacts under internal group paths.
- Do not publish user-facing artifacts directly.
- Head controller decides what is exposed.
```

## 7. `templates/group/tools/allowlist.template.yaml`

- Type: `template`
- Purpose: Template used for generated groups/router
- Locked Sections: `tool_restrictions`
- Validation Check: content-reviewed
- Exposure Policy: group-scoped

```yaml
allowed_prefixes:
  - "python3"
  - "bash"
  - "sh"
  - "rg"
  - "sed"
  - "awk"
  - "cat"
  - "ls"
  - "git"
  - "pytest"
escalation_prefixes:
  - "ssh"
  - "sshpass"
  - "scp"
# BEGIN_LOCKED:tool_restrictions
forbidden_prefixes:
  - "rm -rf /"
  - "git reset --hard"
  - "mkfs"
  - "dd if="
wrapper_required_prefixes:
  - "pip install"
  - "conda install"
# END_LOCKED:tool_restrictions
tool_profile: "{{TOOL_PROFILE}}"
```

## 8. `templates/group/tools/wrappers/README.txt`

- Type: `template`
- Purpose: Template used for generated groups/router
- Locked Sections: `-`
- Validation Check: content-reviewed
- Exposure Policy: group-scoped

```txt
Place project-specific safe wrappers in this directory.
Examples:
- run_calphad_safe.sh
- run_remote_sync_safe.sh
- run_plot_pipeline_safe.sh
```

## 9. `templates/router/research-router/SKILL.template.md`

- Type: `template`
- Purpose: Template used for generated groups/router
- Locked Sections: `-`
- Validation Check: content-reviewed
- Exposure Policy: group-scoped

```md
---
name: research-router
description: Global router for expert multi-agent group bundles. Use to dispatch project objectives to the correct group head and enforce hard quality gates.
---

# Research Router

## Usage
Use this skill as:

`Use $research-router for project <project-id> group <group-id>: <objective>.`

## Routing Workflow
1. Resolve project in `{{FABRIC_ROOT}}/catalog/project-registry.yaml`.
2. Resolve group under `{{FABRIC_ROOT}}/generated/projects/<project-id>/agent-groups`.
3. Build deterministic dispatch plan via `scripts/dispatch_dry_run.py`.
4. Route to the group's head skill and enforce hard gates.
5. Return final artifact index and gate summary.

## Hard Requirements
- Block uncited key claims.
- Block unresolved cross-domain decisions.
- Use lease-based workdir coordination for all write tasks.
- Keep specialist artifacts internal unless audit mode is explicitly enabled.

## Quick Command
```bash
python {{FABRIC_ROOT}}/scripts/dispatch_dry_run.py --project-id <project-id> --group <group-id> --objective "<objective>"
```
```

## 10. `schemas/dispatch.schema.yaml`

- Type: `schema`
- Purpose: Validation schema for manifests and dispatch contracts
- Locked Sections: `-`
- Validation Check: schema-validated
- Exposure Policy: source

```yaml
$schema: "https://json-schema.org/draft/2020-12/schema"
title: "Dispatch Plan"
type: object
required:
  - project_id
  - group_id
  - objective
  - dispatch_mode
  - session_mode
  - phases
properties:
  project_id: {type: string}
  group_id: {type: string}
  objective: {type: string}
  dispatch_mode:
    type: string
    enum: [hybrid]
  session_mode:
    type: string
    enum: [interactive-separated]
  phases:
    type: array
    minItems: 1
    items:
      type: object
      required: [phase_id, mode, tasks]
      properties:
        phase_id: {type: integer}
        mode:
          type: string
          enum: [parallel, sequential]
        tasks:
          type: array
          minItems: 1
          items:
            type: object
            required: [agent_id, focus, skill_name, workdir]
            properties:
              agent_id: {type: string}
              focus: {type: string}
              skill_name: {type: string}
              workdir: {type: string}
              transport:
                type: string
                enum: [local, ssh]
              scheduler: {type: string}
              hardware: {type: string}
              requires_gpu: {type: boolean}
              depends_on:
                type: array
                items: {type: string}
  quality_gates:
    type: object
    additionalProperties: {type: boolean}
additionalProperties: true
```

## 11. `schemas/group.schema.yaml`

- Type: `schema`
- Purpose: Validation schema for manifests and dispatch contracts
- Locked Sections: `-`
- Validation Check: schema-validated
- Exposure Policy: source

```yaml
$schema: "https://json-schema.org/draft/2020-12/schema"
title: "Group Manifest"
type: object
required:
  - group_id
  - display_name
  - template_version
  - domain
  - head
  - specialists
  - tool_profile
  - default_workdirs
  - quality_gates
properties:
  group_id:
    type: string
    pattern: "^[a-z0-9-]+$"
  display_name:
    type: string
    minLength: 3
  template_version:
    type: string
  domain:
    type: string
  head:
    type: object
    required: [agent_id, skill_name, mission]
    properties:
      agent_id: {type: string}
      skill_name: {type: string}
      mission: {type: string}
  specialists:
    type: array
    minItems: 1
    items:
      type: object
      required: [agent_id, skill_name, focus, required_references, required_outputs]
      properties:
        agent_id: {type: string}
        skill_name: {type: string}
        focus: {type: string}
        depends_on:
          type: array
          items: {type: string}
        required_references:
          type: array
          minItems: 1
          items: {type: string}
        required_outputs:
          type: array
          minItems: 1
          items: {type: string}
        execution:
          type: object
          properties:
            remote_transport:
              type: string
              enum: [local, ssh]
            scheduler:
              type: string
            hardware:
              type: string
            requires_gpu:
              type: boolean
  tool_profile:
    type: string
  interaction:
    type: object
    properties:
      mode:
        type: string
        enum: [interactive-separated]
      linked_groups:
        type: array
        items: {type: string}
  execution_defaults:
    type: object
    properties:
      remote_transport:
        type: string
        enum: [local, ssh]
      schedulers:
        type: array
        items: {type: string}
      hardware:
        type: array
        items: {type: string}
  default_workdirs:
    type: array
    minItems: 1
    items: {type: string}
  quality_gates:
    type: object
    required:
      - citation_required
      - unresolved_claims_block
      - peer_check_required
      - consistency_required
      - scope_required
      - reproducibility_required
    properties:
      citation_required: {type: boolean}
      unresolved_claims_block: {type: boolean}
      peer_check_required: {type: boolean}
      consistency_required: {type: boolean}
      scope_required: {type: boolean}
      reproducibility_required: {type: boolean}
additionalProperties: true
```

## 12. `schemas/project.schema.yaml`

- Type: `schema`
- Purpose: Validation schema for manifests and dispatch contracts
- Locked Sections: `-`
- Validation Check: schema-validated
- Exposure Policy: source

```yaml
$schema: "https://json-schema.org/draft/2020-12/schema"
title: "Generated Project Manifest"
type: object
required:
  - project_id
  - selected_groups
  - install_targets
  - router_skill_name
  - bundle_version
  - template_versions
  - overlays
  - visibility
properties:
  project_id:
    type: string
    pattern: "^[a-z0-9-]+$"
  selected_groups:
    type: array
    minItems: 1
    items: {type: string}
  install_targets:
    type: object
    required: [codex_skill_dir]
    properties:
      codex_skill_dir: {type: string}
  router_skill_name:
    type: string
  bundle_version:
    type: string
  template_versions:
    type: object
    additionalProperties: {type: string}
  overlays:
    type: object
    required: [allow_project_overrides, protected_sections]
    properties:
      allow_project_overrides: {type: boolean}
      protected_sections:
        type: array
        minItems: 1
        items: {type: string}
  visibility:
    type: object
    required: [mode, audit_override]
    properties:
      mode:
        type: string
        enum: [group-only, full]
      audit_override:
        type: boolean
  groups:
    type: object
    additionalProperties:
      type: object
      required: [manifest_path, skill_dirs, head_skill_dir, specialist_skill_dirs]
      properties:
        manifest_path: {type: string}
        skill_dirs:
          type: array
          minItems: 1
          items: {type: string}
        head_skill_dir:
          type: string
        specialist_skill_dirs:
          type: array
          items: {type: string}
additionalProperties: true
```

## 13. `schemas/tool_policy.schema.yaml`

- Type: `schema`
- Purpose: Validation schema for manifests and dispatch contracts
- Locked Sections: `-`
- Validation Check: schema-validated
- Exposure Policy: source

```yaml
$schema: "https://json-schema.org/draft/2020-12/schema"
title: "Tool Policy"
type: object
required:
  - allowed_prefixes
  - escalation_prefixes
  - forbidden_prefixes
  - wrapper_required_prefixes
properties:
  allowed_prefixes:
    type: array
    items: {type: string}
  escalation_prefixes:
    type: array
    items: {type: string}
  forbidden_prefixes:
    type: array
    items: {type: string}
  wrapper_required_prefixes:
    type: array
    items: {type: string}
  tool_profile:
    type: string
additionalProperties: true
```

## 14. `catalog/groups/atomistic-hpc-simulation.yaml`

- Type: `catalog`
- Purpose: Reusable source-of-truth group/profile/registry metadata
- Locked Sections: `-`
- Validation Check: schema-validated
- Exposure Policy: source

```yaml
group_id: "atomistic-hpc-simulation"
display_name: "Atomistic HPC Simulation Group"
template_version: "1.0.0"
domain: "hpc-atomistic-simulation"
head:
  agent_id: "atomistic-hpc-simulation-head"
  skill_name: "grp-atomistic-hpc-simulation-head"
  mission: "Coordinate high-fidelity atomistic simulation workflows across remote HPC resources with strict evidence and reproducibility controls."
specialists:
  - agent_id: "vasp-expert"
    skill_name: "grp-atomistic-hpc-simulation-vasp"
    focus: "VASP workflows including DFT setup, convergence policy, and electronic structure outputs"
    required_references:
      - "references/vasp-core.md"
    required_outputs:
      - "assumptions.md"
      - "claims_with_citations.md"
      - "vasp-plan.md"
    execution:
      remote_transport: "ssh"
      scheduler: "pbs"
      hardware: "cpu"
      requires_gpu: false
  - agent_id: "lammps-expert"
    skill_name: "grp-atomistic-hpc-simulation-lammps"
    focus: "LAMMPS MD configuration, potential selection, and production run strategy"
    required_references:
      - "references/lammps-core.md"
    required_outputs:
      - "assumptions.md"
      - "claims_with_citations.md"
      - "lammps-plan.md"
    execution:
      remote_transport: "ssh"
      scheduler: "pbs"
      hardware: "cpu"
      requires_gpu: false
  - agent_id: "metadynamics-expert"
    skill_name: "grp-atomistic-hpc-simulation-metadynamics"
    focus: "Enhanced sampling with metadynamics, CV design, and free-energy surface interpretation"
    depends_on:
      - "lammps-expert"
    required_references:
      - "references/metadynamics-core.md"
    required_outputs:
      - "assumptions.md"
      - "claims_with_citations.md"
      - "metadynamics-plan.md"
    execution:
      remote_transport: "ssh"
      scheduler: "pbs"
      hardware: "cpu"
      requires_gpu: false
  - agent_id: "scheduler-remote-ops-expert"
    skill_name: "grp-atomistic-hpc-simulation-scheduler-ops"
    focus: "SSH orchestration, PBS-first and Slurm-compatible job submission strategy, failure recovery"
    required_references:
      - "references/hpc-scheduler-core.md"
    required_outputs:
      - "remote-ops-plan.md"
      - "claims_with_citations.md"
    execution:
      remote_transport: "ssh"
      scheduler: "pbs"
      hardware: "cpu"
      requires_gpu: false
  - agent_id: "cuda-performance-expert"
    skill_name: "grp-atomistic-hpc-simulation-cuda"
    focus: "CUDA queue usage, GPU performance tuning, memory and throughput diagnostics"
    depends_on:
      - "scheduler-remote-ops-expert"
    required_references:
      - "references/cuda-performance-core.md"
    required_outputs:
      - "cuda-plan.md"
      - "claims_with_citations.md"
    execution:
      remote_transport: "ssh"
      scheduler: "slurm"
      hardware: "cuda-gpu"
      requires_gpu: true
  - agent_id: "simulation-postprocessing-expert"
    skill_name: "grp-atomistic-hpc-simulation-postprocessing"
    focus: "Trajectory/post-processing pipelines and uncertainty-aware summary extraction"
    depends_on:
      - "vasp-expert"
      - "lammps-expert"
      - "metadynamics-expert"
    required_references:
      - "references/postprocessing-core.md"
    required_outputs:
      - "postprocessing-summary.md"
      - "claims_with_citations.md"
    execution:
      remote_transport: "ssh"
      scheduler: "pbs"
      hardware: "cpu"
      requires_gpu: false
  - agent_id: "developer-bridge-expert"
    skill_name: "grp-atomistic-hpc-simulation-developer-bridge"
    focus: "Cross-group integration with developer group for scripts, SSH tooling, and reliability hardening"
    depends_on:
      - "scheduler-remote-ops-expert"
    required_references:
      - "references/developer-bridge-core.md"
    required_outputs:
      - "integration-plan.md"
      - "claims_with_citations.md"
    execution:
      remote_transport: "ssh"
      scheduler: "pbs"
      hardware: "cpu"
      requires_gpu: false
interaction:
  mode: "interactive-separated"
  linked_groups:
    - "developer"
execution_defaults:
  remote_transport: "ssh"
  schedulers:
    - "pbs"
    - "slurm"
  hardware:
    - "cpu"
    - "cuda-gpu"
tool_profile: "hpc-simulation-default"
default_workdirs:
  - "inputs"
  - "analysis"
  - "outputs"
quality_gates:
  citation_required: true
  unresolved_claims_block: true
  peer_check_required: true
  consistency_required: true
  scope_required: true
  reproducibility_required: true
```

## 15. `catalog/groups/data-curation.yaml`

- Type: `catalog`
- Purpose: Reusable source-of-truth group/profile/registry metadata
- Locked Sections: `-`
- Validation Check: schema-validated
- Exposure Policy: source

```yaml
group_id: "data-curation"
display_name: "Data Curation Group"
template_version: "1.0.0"
domain: "data-pipelines"
head:
  agent_id: "data-curation-head"
  skill_name: "grp-data-curation-head"
  mission: "Ensure trustworthy, traceable research data pipelines and metadata quality."
specialists:
  - agent_id: "data-ingest-specialist"
    skill_name: "grp-data-curation-ingest"
    focus: "Data ingest strategy, provenance capture, and schema conformance"
    required_references:
      - "references/data-ingest-core.md"
    required_outputs:
      - "ingest_report.md"
      - "claims_with_citations.md"
  - agent_id: "metadata-specialist"
    skill_name: "grp-data-curation-metadata"
    focus: "Metadata normalization, ontologies, and traceability annotations"
    depends_on:
      - "data-ingest-specialist"
    required_references:
      - "references/metadata-core.md"
    required_outputs:
      - "metadata_dictionary.md"
      - "claims_with_citations.md"
  - agent_id: "data-quality-specialist"
    skill_name: "grp-data-curation-quality"
    focus: "Data quality checks, anomaly detection heuristics, and acceptance thresholds"
    depends_on:
      - "metadata-specialist"
    required_references:
      - "references/data-quality-core.md"
    required_outputs:
      - "quality_report.md"
      - "claims_with_citations.md"
tool_profile: "data-default"
default_workdirs:
  - "inputs"
  - "analysis"
  - "outputs"
quality_gates:
  citation_required: true
  unresolved_claims_block: true
  peer_check_required: true
  consistency_required: true
  scope_required: true
  reproducibility_required: true
```

## 16. `catalog/groups/designer.yaml`

- Type: `catalog`
- Purpose: Reusable source-of-truth group/profile/registry metadata
- Locked Sections: `-`
- Validation Check: schema-validated
- Exposure Policy: source

```yaml
group_id: "designer"
display_name: "Designer Group"
template_version: "1.0.0"
domain: "workflow-and-communication"
head:
  agent_id: "designer-head"
  skill_name: "grp-designer-head"
  mission: "Design coherent research workflows and high-impact audience communication artifacts."
specialists:
  - agent_id: "workflow-architect"
    skill_name: "grp-designer-workflow"
    focus: "Workflow architecture, dependency mapping, and execution sequencing"
    required_references:
      - "references/workflow-design-core.md"
    required_outputs:
      - "workflow_map.md"
      - "claims_with_citations.md"
  - agent_id: "visual-narrative-specialist"
    skill_name: "grp-designer-visual-narrative"
    focus: "Figure storytelling, message hierarchy, and audience-oriented narrative structure"
    required_references:
      - "references/visual-narrative-core.md"
    required_outputs:
      - "storyline.md"
      - "claims_with_citations.md"
  - agent_id: "presentation-specialist"
    skill_name: "grp-designer-presentation"
    focus: "Slide architecture, delivery pacing, and presentation readability"
    depends_on:
      - "visual-narrative-specialist"
    required_references:
      - "references/presentation-core.md"
    required_outputs:
      - "slide_spec.md"
      - "claims_with_citations.md"
tool_profile: "design-default"
default_workdirs:
  - "inputs"
  - "analysis"
  - "outputs"
quality_gates:
  citation_required: true
  unresolved_claims_block: true
  peer_check_required: true
  consistency_required: true
  scope_required: true
  reproducibility_required: true
```

## 17. `catalog/groups/developer.yaml`

- Type: `catalog`
- Purpose: Reusable source-of-truth group/profile/registry metadata
- Locked Sections: `-`
- Validation Check: schema-validated
- Exposure Policy: source

```yaml
group_id: "developer"
display_name: "Developer Group"
template_version: "1.0.0"
domain: "software-and-infra"
head:
  agent_id: "developer-head"
  skill_name: "grp-developer-head"
  mission: "Deliver robust implementation, debugging, and automation support for research projects."
specialists:
  - agent_id: "python-expert"
    skill_name: "grp-developer-python"
    focus: "Python architecture, package reliability, tests, and runtime debugging"
    required_references:
      - "references/python-engineering-core.md"
    required_outputs:
      - "implementation_patch.md"
      - "test_plan.md"
      - "claims_with_citations.md"
  - agent_id: "shell-expert"
    skill_name: "grp-developer-shell"
    focus: "Shell automation, reproducible scripts, CLI hardening"
    required_references:
      - "references/shell-engineering-core.md"
    required_outputs:
      - "automation_scripts.md"
      - "claims_with_citations.md"
  - agent_id: "ssh-remote-ops-expert"
    skill_name: "grp-developer-ssh"
    focus: "Remote operations, secure SSH workflows, transfer and execution protocols"
    required_references:
      - "references/ssh-ops-core.md"
    required_outputs:
      - "remote_ops_plan.md"
      - "claims_with_citations.md"
tool_profile: "developer-default"
default_workdirs:
  - "inputs"
  - "analysis"
  - "outputs"
quality_gates:
  citation_required: true
  unresolved_claims_block: true
  peer_check_required: true
  consistency_required: true
  scope_required: true
  reproducibility_required: true
```

## 18. `catalog/groups/literature-intelligence.yaml`

- Type: `catalog`
- Purpose: Reusable source-of-truth group/profile/registry metadata
- Locked Sections: `-`
- Validation Check: schema-validated
- Exposure Policy: source

```yaml
group_id: "literature-intelligence"
display_name: "Literature Intelligence Group"
template_version: "1.0.0"
domain: "literature-analysis"
head:
  agent_id: "literature-intelligence-head"
  skill_name: "grp-literature-intelligence-head"
  mission: "Extract, compare, and evidence-grade literature claims for project decision support."
specialists:
  - agent_id: "retrieval-specialist"
    skill_name: "grp-literature-intelligence-retrieval"
    focus: "Paper retrieval strategy, inclusion criteria, and source tracking"
    required_references:
      - "references/retrieval-core.md"
    required_outputs:
      - "source_inventory.md"
      - "claims_with_citations.md"
  - agent_id: "evidence-grading-specialist"
    skill_name: "grp-literature-intelligence-evidence"
    focus: "Evidence grading, study quality interpretation, and confidence assignment"
    depends_on:
      - "retrieval-specialist"
    required_references:
      - "references/evidence-grading-core.md"
    required_outputs:
      - "evidence_matrix.md"
      - "claims_with_citations.md"
  - agent_id: "gap-analysis-specialist"
    skill_name: "grp-literature-intelligence-gap"
    focus: "Research gap mapping and risk-aware recommendation framing"
    depends_on:
      - "evidence-grading-specialist"
    required_references:
      - "references/gap-analysis-core.md"
    required_outputs:
      - "gap_map.md"
      - "claims_with_citations.md"
tool_profile: "literature-default"
default_workdirs:
  - "inputs"
  - "analysis"
  - "outputs"
quality_gates:
  citation_required: true
  unresolved_claims_block: true
  peer_check_required: true
  consistency_required: true
  scope_required: true
  reproducibility_required: true
```

## 19. `catalog/groups/material-engineer.yaml`

- Type: `catalog`
- Purpose: Reusable source-of-truth group/profile/registry metadata
- Locked Sections: `-`
- Validation Check: schema-validated
- Exposure Policy: source

```yaml
group_id: "material-engineer"
display_name: "Material Engineer Group"
template_version: "1.0.0"
domain: "experiment-and-process"
head:
  agent_id: "material-engineer-head"
  skill_name: "grp-material-engineer-head"
  mission: "Coordinate experiment-first engineering workflows from synthesis to characterization."
specialists:
  - agent_id: "synthesis-specialist"
    skill_name: "grp-material-engineer-synthesis"
    focus: "Synthesis route design, process windows, precursor handling"
    required_references:
      - "references/synthesis-core.md"
    required_outputs:
      - "synthesis_protocol.md"
      - "risk_notes.md"
      - "claims_with_citations.md"
  - agent_id: "characterization-specialist"
    skill_name: "grp-material-engineer-characterization"
    focus: "Characterization plan (XRD/SEM/TEM/spectroscopy) and interpretation constraints"
    depends_on:
      - "synthesis-specialist"
    required_references:
      - "references/characterization-core.md"
    required_outputs:
      - "characterization_matrix.md"
      - "claims_with_citations.md"
  - agent_id: "scaleup-specialist"
    skill_name: "grp-material-engineer-scaleup"
    focus: "Scale-up risks, process transfer, manufacturability constraints"
    depends_on:
      - "synthesis-specialist"
    required_references:
      - "references/scaleup-core.md"
    required_outputs:
      - "scaleup_constraints.md"
      - "claims_with_citations.md"
tool_profile: "engineering-default"
default_workdirs:
  - "inputs"
  - "analysis"
  - "outputs"
quality_gates:
  citation_required: true
  unresolved_claims_block: true
  peer_check_required: true
  consistency_required: true
  scope_required: true
  reproducibility_required: true
```

## 20. `catalog/groups/material-scientist.yaml`

- Type: `catalog`
- Purpose: Reusable source-of-truth group/profile/registry metadata
- Locked Sections: `-`
- Validation Check: schema-validated
- Exposure Policy: source

```yaml
group_id: "material-scientist"
display_name: "Material Scientist Group"
template_version: "1.0.0"
domain: "materials-research"
head:
  agent_id: "material-scientist-head"
  skill_name: "grp-material-scientist-head"
  mission: "Route and quality-gate specialist outputs for theoretical and computational materials science."
specialists:
  - agent_id: "thermodynamics-specialist"
    skill_name: "grp-material-scientist-thermodynamics"
    focus: "Phase stability, CALPHAD logic, free-energy reasoning"
    required_references:
      - "references/thermodynamics-core.md"
    required_outputs:
      - "assumptions.md"
      - "claims_with_citations.md"
      - "phase_stability_notes.md"
  - agent_id: "electronic-structure-specialist"
    skill_name: "grp-material-scientist-electronic-structure"
    focus: "DFT setup, band structure interpretation, density-of-states analysis"
    depends_on:
      - "thermodynamics-specialist"
    required_references:
      - "references/electronic-structure-core.md"
    required_outputs:
      - "assumptions.md"
      - "claims_with_citations.md"
      - "electronic_summary.md"
  - agent_id: "atomistic-simulation-specialist"
    skill_name: "grp-material-scientist-atomistic"
    focus: "Atomistic simulation strategy, interatomic potential reasoning, trajectory interpretation"
    required_references:
      - "references/atomistic-simulation-core.md"
    required_outputs:
      - "assumptions.md"
      - "claims_with_citations.md"
      - "simulation_plan.md"
tool_profile: "science-default"
default_workdirs:
  - "inputs"
  - "analysis"
  - "outputs"
quality_gates:
  citation_required: true
  unresolved_claims_block: true
  peer_check_required: true
  consistency_required: true
  scope_required: true
  reproducibility_required: true
```

## 21. `catalog/groups/publication-packaging.yaml`

- Type: `catalog`
- Purpose: Reusable source-of-truth group/profile/registry metadata
- Locked Sections: `-`
- Validation Check: schema-validated
- Exposure Policy: source

```yaml
group_id: "publication-packaging"
display_name: "Publication Packaging Group"
template_version: "1.0.0"
domain: "publication-delivery"
head:
  agent_id: "publication-packaging-head"
  skill_name: "grp-publication-packaging-head"
  mission: "Package validated research outputs into publication-ready narrative, figures, and supplements."
specialists:
  - agent_id: "manuscript-structure-specialist"
    skill_name: "grp-publication-packaging-manuscript"
    focus: "Manuscript structure, argument flow, and section-level coherence"
    required_references:
      - "references/manuscript-core.md"
    required_outputs:
      - "manuscript_outline.md"
      - "claims_with_citations.md"
  - agent_id: "figure-table-specialist"
    skill_name: "grp-publication-packaging-figures"
    focus: "Figure/table completeness, annotation quality, and caption evidence coverage"
    required_references:
      - "references/figure-table-core.md"
    required_outputs:
      - "figure_table_index.md"
      - "claims_with_citations.md"
  - agent_id: "supplement-specialist"
    skill_name: "grp-publication-packaging-supplement"
    focus: "Supplementary methods, robustness notes, and reproducibility appendices"
    depends_on:
      - "manuscript-structure-specialist"
    required_references:
      - "references/supplement-core.md"
    required_outputs:
      - "supplement_plan.md"
      - "claims_with_citations.md"
tool_profile: "publication-default"
default_workdirs:
  - "inputs"
  - "analysis"
  - "outputs"
quality_gates:
  citation_required: true
  unresolved_claims_block: true
  peer_check_required: true
  consistency_required: true
  scope_required: true
  reproducibility_required: true
```

## 22. `catalog/groups/quality-assurance.yaml`

- Type: `catalog`
- Purpose: Reusable source-of-truth group/profile/registry metadata
- Locked Sections: `-`
- Validation Check: schema-validated
- Exposure Policy: source

```yaml
group_id: "quality-assurance"
display_name: "Quality Assurance Group"
template_version: "1.0.0"
domain: "verification-and-risk"
head:
  agent_id: "quality-assurance-head"
  skill_name: "grp-quality-assurance-head"
  mission: "Audit technical outputs for reproducibility, consistency, and decision-risk control."
specialists:
  - agent_id: "reproducibility-auditor"
    skill_name: "grp-quality-assurance-repro"
    focus: "Reproducibility checks, parameter traceability, and artifact completeness"
    required_references:
      - "references/reproducibility-core.md"
    required_outputs:
      - "repro_audit.md"
      - "claims_with_citations.md"
  - agent_id: "consistency-auditor"
    skill_name: "grp-quality-assurance-consistency"
    focus: "Cross-document consistency checks and contradiction detection"
    required_references:
      - "references/consistency-core.md"
    required_outputs:
      - "consistency_audit.md"
      - "claims_with_citations.md"
  - agent_id: "risk-auditor"
    skill_name: "grp-quality-assurance-risk"
    focus: "Risk classification, severity tagging, and mitigation recommendation framing"
    depends_on:
      - "consistency-auditor"
    required_references:
      - "references/risk-core.md"
    required_outputs:
      - "risk_register.md"
      - "claims_with_citations.md"
tool_profile: "qa-default"
default_workdirs:
  - "inputs"
  - "analysis"
  - "outputs"
quality_gates:
  citation_required: true
  unresolved_claims_block: true
  peer_check_required: true
  consistency_required: true
  scope_required: true
  reproducibility_required: true
```

## 23. `catalog/profiles/experiment-driven.yaml`

- Type: `catalog`
- Purpose: Reusable source-of-truth group/profile/registry metadata
- Locked Sections: `-`
- Validation Check: schema-validated
- Exposure Policy: source

```yaml
profile_id: "experiment-driven"
display_name: "Experiment Driven"
groups:
  - "material-engineer"
  - "data-curation"
  - "developer"
```

## 24. `catalog/profiles/hpc-simulation-core.yaml`

- Type: `catalog`
- Purpose: Reusable source-of-truth group/profile/registry metadata
- Locked Sections: `-`
- Validation Check: schema-validated
- Exposure Policy: source

```yaml
profile_id: "hpc-simulation-core"
display_name: "HPC Simulation Core"
groups:
  - "atomistic-hpc-simulation"
  - "developer"
  - "quality-assurance"
```

## 25. `catalog/profiles/publication-push.yaml`

- Type: `catalog`
- Purpose: Reusable source-of-truth group/profile/registry metadata
- Locked Sections: `-`
- Validation Check: schema-validated
- Exposure Policy: source

```yaml
profile_id: "publication-push"
display_name: "Publication Push"
groups:
  - "material-scientist"
  - "designer"
  - "publication-packaging"
  - "quality-assurance"
```

## 26. `catalog/profiles/rapid-debug.yaml`

- Type: `catalog`
- Purpose: Reusable source-of-truth group/profile/registry metadata
- Locked Sections: `-`
- Validation Check: schema-validated
- Exposure Policy: source

```yaml
profile_id: "rapid-debug"
display_name: "Rapid Debug"
groups:
  - "developer"
  - "quality-assurance"
  - "literature-intelligence"
```

## 27. `catalog/profiles/reproduction-core.yaml`

- Type: `catalog`
- Purpose: Reusable source-of-truth group/profile/registry metadata
- Locked Sections: `-`
- Validation Check: schema-validated
- Exposure Policy: source

```yaml
profile_id: "reproduction-core"
display_name: "Reproduction Core"
groups:
  - "material-scientist"
  - "developer"
  - "quality-assurance"
```

## 28. `catalog/project-registry.yaml`

- Type: `catalog`
- Purpose: Reusable source-of-truth group/profile/registry metadata
- Locked Sections: `-`
- Validation Check: schema-validated
- Exposure Policy: source

```yaml
router_skill_name: research-router
projects:
  proj-battery-001:
    manifest_path: generated/projects/proj-battery-001/manifest.yaml
    selected_groups:
    - material-scientist
    - developer
    - quality-assurance
    updated_at: '2026-02-28T14:34:59Z'
```

## 29. `generated/projects/proj-battery-001/agent-groups/developer/AGENTS.md`

- Type: `agents`
- Purpose: Group operating contract and policy
- Locked Sections: `safety_policy, citation_gate, routing_audit, exposure_policy`
- Validation Check: content-reviewed
- Exposure Policy: source

```md
# Developer Group - proj-battery-001

## Mission
Deliver robust implementation, debugging, and automation support for research projects.

## Group Identity
- `group_id`: `developer`
- `template_version`: `1.0.0`
- `tool_profile`: `developer-default`
- `head_agent`: `developer-head`
- `head_skill`: `proj-proj-battery-001-developer-developer-head`

## Specialist Roster
- `python-expert`: Python architecture, package reliability, tests, and runtime debugging (skill: `proj-proj-battery-001-developer-python-expert`)
- `shell-expert`: Shell automation, reproducible scripts, CLI hardening (skill: `proj-proj-battery-001-developer-shell-expert`)
- `ssh-remote-ops-expert`: Remote operations, secure SSH workflows, transfer and execution protocols (skill: `proj-proj-battery-001-developer-ssh-remote-ops-expert`)

## Work Directories
- `generated/projects/proj-battery-001/work/developer/python-expert`
- `generated/projects/proj-battery-001/work/developer/shell-expert`
- `generated/projects/proj-battery-001/work/developer/ssh-remote-ops-expert`

## Artifact Partition
- Internal specialist artifacts: `agent-groups/developer/internal/<specialist>/...`
- Exposed group artifacts: `agent-groups/developer/exposed/...`
- Visibility mode is controlled at project manifest level.

## Head Controller Protocol
1. Decompose objective into specialist tasks.
2. Dispatch hybrid execution (parallel for independent tasks, sequential for dependencies).
3. Enforce quality gates before accepting specialist outputs.
4. Merge outputs and publish decision log to exposed artifacts only.

BEGIN_LOCKED:safety_policy
## Safety Policy (Locked)
- Specialists work only inside assigned project workdirs.
- Potentially destructive commands must follow project tool policy and escalation rules.
- Head controller records command intent for each specialist stage.
END_LOCKED:safety_policy

BEGIN_LOCKED:citation_gate
## Citation Gate (Locked)
- Every key claim must include at least one citation.
- Allowed evidence sources: local references and verified web sources.
- If citations are missing for key claims, output status is `BLOCKED_UNCITED`.
- If web evidence is required but unavailable, output status is `BLOCKED_NEEDS_EVIDENCE`.
END_LOCKED:citation_gate

BEGIN_LOCKED:routing_audit
## Routing Audit (Locked)
- Head must record task graph, dependencies, and final merge rationale.
- Cross-domain final decisions require explicit head-controller sign-off.
END_LOCKED:routing_audit

BEGIN_LOCKED:exposure_policy
## Exposure Policy (Locked)
- Group-level outputs are user-visible by default.
- Specialist artifacts remain internal unless explicit audit mode is enabled.
END_LOCKED:exposure_policy

## Expected Deliverables
- `implementation_patch.md` from `python-expert`
- `test_plan.md` from `python-expert`
- `claims_with_citations.md` from `python-expert`
- `automation_scripts.md` from `shell-expert`
- `claims_with_citations.md` from `shell-expert`
- `remote_ops_plan.md` from `ssh-remote-ops-expert`
- `claims_with_citations.md` from `ssh-remote-ops-expert`

## Quality Gates
- `citation_required`: `True`
- `unresolved_claims_block`: `True`
- `peer_check_required`: `True`
- `consistency_required`: `True`
- `scope_required`: `True`
- `reproducibility_required`: `True`
```

## 30. `generated/projects/proj-battery-001/agent-groups/developer/group.yaml`

- Type: `manifest`
- Purpose: Project or group manifest instance
- Locked Sections: `-`
- Validation Check: schema-validated
- Exposure Policy: source

```yaml
group_id: developer
display_name: Developer Group
template_version: 1.0.0
domain: software-and-infra
head:
  agent_id: developer-head
  skill_name: grp-developer-head
  mission: Deliver robust implementation, debugging, and automation support for research
    projects.
  effective_skill_name: proj-proj-battery-001-developer-developer-head
specialists:
- agent_id: python-expert
  skill_name: grp-developer-python
  focus: Python architecture, package reliability, tests, and runtime debugging
  required_references:
  - references/python-engineering-core.md
  required_outputs:
  - implementation_patch.md
  - test_plan.md
  - claims_with_citations.md
  effective_skill_name: proj-proj-battery-001-developer-python-expert
- agent_id: shell-expert
  skill_name: grp-developer-shell
  focus: Shell automation, reproducible scripts, CLI hardening
  required_references:
  - references/shell-engineering-core.md
  required_outputs:
  - automation_scripts.md
  - claims_with_citations.md
  effective_skill_name: proj-proj-battery-001-developer-shell-expert
- agent_id: ssh-remote-ops-expert
  skill_name: grp-developer-ssh
  focus: Remote operations, secure SSH workflows, transfer and execution protocols
  required_references:
  - references/ssh-ops-core.md
  required_outputs:
  - remote_ops_plan.md
  - claims_with_citations.md
  effective_skill_name: proj-proj-battery-001-developer-ssh-remote-ops-expert
tool_profile: developer-default
default_workdirs:
- inputs
- analysis
- outputs
quality_gates:
  citation_required: true
  unresolved_claims_block: true
  peer_check_required: true
  consistency_required: true
  scope_required: true
  reproducibility_required: true
```

## 31. `generated/projects/proj-battery-001/agent-groups/developer/handoffs.yaml`

- Type: `handoff`
- Purpose: Intra-group handoff protocol
- Locked Sections: `-`
- Validation Check: content-reviewed
- Exposure Policy: source

```yaml
group_id: "developer"
head_agent_id: "developer-head"
handoffs:
  - from: "python-expert"
    to: "head-controller"
    condition: "after task completion"
  - from: "shell-expert"
    to: "head-controller"
    condition: "after task completion"
  - from: "ssh-remote-ops-expert"
    to: "head-controller"
    condition: "after task completion"
```

## 32. `generated/projects/proj-battery-001/agent-groups/developer/skills/proj-proj-battery-001-developer-developer-head/SKILL.md`

- Type: `skill`
- Purpose: Operational skill definition for an agent or router
- Locked Sections: `-`
- Validation Check: content-reviewed
- Exposure Policy: source

```md
---
name: proj-proj-battery-001-developer-developer-head
description: Orchestrate Developer Group for project proj-battery-001. Use when routing objective-level work to specialist agents with strict expert quality gates.
---

# Developer Group Head Controller

## Scope
Route and merge specialist outputs for `developer` in project `proj-battery-001`.

## Responsibilities
1. Build a task graph from the objective.
2. Dispatch hybrid execution: parallel for independent branches, sequential for dependencies.
3. Enforce citation/consistency/scope/reproducibility gates.
4. Publish final merged artifact index and decision log.

## Required Inputs
- `objective`
- `project_id`
- `group_id`
- current registry entry in `catalog/project-registry.yaml`

## Execution Contract
- Acquire per-agent workdir lease before write.
- Retry or reroute on lease conflict.
- Reject outputs that fail any hard gate.
- Consolidate specialist internal outputs before publishing group-exposed artifacts.

## Specialists
- python-expert: `proj-proj-battery-001-developer-python-expert`
- shell-expert: `proj-proj-battery-001-developer-shell-expert`
- ssh-remote-ops-expert: `proj-proj-battery-001-developer-ssh-remote-ops-expert`

## Output Contract
- `dispatch_plan.json`
- `decision_log.md`
- `artifact_index.md`
```

## 33. `generated/projects/proj-battery-001/agent-groups/developer/skills/proj-proj-battery-001-developer-python-expert/SKILL.md`

- Type: `skill`
- Purpose: Operational skill definition for an agent or router
- Locked Sections: `-`
- Validation Check: content-reviewed
- Exposure Policy: source

```md
---
name: proj-proj-battery-001-developer-python-expert
description: Specialist agent for Python architecture, package reliability, tests, and runtime debugging in Developer Group (project proj-battery-001). Use for narrow-domain expert analysis with claim-level citations.
---

# python-expert

## Scope
Python architecture, package reliability, tests, and runtime debugging

## Hard Gate Requirements
1. Every key claim must include a citation.
2. Assumptions must be explicit.
3. Output must stay within specialist scope.
4. Reproducibility details are mandatory.

If web evidence is unavailable and needed, return `BLOCKED_NEEDS_EVIDENCE`.

## Required References
- references/python-engineering-core.md

## Required Outputs
- implementation_patch.md
- test_plan.md
- claims_with_citations.md

## Response Format
- `status`: `PASS` or blocked reason.
- `assumptions`
- `claims_with_citations`
- `repro_steps`
- `artifact_paths`

## Artifact Scope
- Write specialist artifacts under internal group paths.
- Do not publish user-facing artifacts directly.
- Head controller decides what is exposed.
```

## 34. `generated/projects/proj-battery-001/agent-groups/developer/skills/proj-proj-battery-001-developer-shell-expert/SKILL.md`

- Type: `skill`
- Purpose: Operational skill definition for an agent or router
- Locked Sections: `-`
- Validation Check: content-reviewed
- Exposure Policy: source

```md
---
name: proj-proj-battery-001-developer-shell-expert
description: Specialist agent for Shell automation, reproducible scripts, CLI hardening in Developer Group (project proj-battery-001). Use for narrow-domain expert analysis with claim-level citations.
---

# shell-expert

## Scope
Shell automation, reproducible scripts, CLI hardening

## Hard Gate Requirements
1. Every key claim must include a citation.
2. Assumptions must be explicit.
3. Output must stay within specialist scope.
4. Reproducibility details are mandatory.

If web evidence is unavailable and needed, return `BLOCKED_NEEDS_EVIDENCE`.

## Required References
- references/shell-engineering-core.md

## Required Outputs
- automation_scripts.md
- claims_with_citations.md

## Response Format
- `status`: `PASS` or blocked reason.
- `assumptions`
- `claims_with_citations`
- `repro_steps`
- `artifact_paths`

## Artifact Scope
- Write specialist artifacts under internal group paths.
- Do not publish user-facing artifacts directly.
- Head controller decides what is exposed.
```

## 35. `generated/projects/proj-battery-001/agent-groups/developer/skills/proj-proj-battery-001-developer-ssh-remote-ops-expert/SKILL.md`

- Type: `skill`
- Purpose: Operational skill definition for an agent or router
- Locked Sections: `-`
- Validation Check: content-reviewed
- Exposure Policy: source

```md
---
name: proj-proj-battery-001-developer-ssh-remote-ops-expert
description: Specialist agent for Remote operations, secure SSH workflows, transfer and execution protocols in Developer Group (project proj-battery-001). Use for narrow-domain expert analysis with claim-level citations.
---

# ssh-remote-ops-expert

## Scope
Remote operations, secure SSH workflows, transfer and execution protocols

## Hard Gate Requirements
1. Every key claim must include a citation.
2. Assumptions must be explicit.
3. Output must stay within specialist scope.
4. Reproducibility details are mandatory.

If web evidence is unavailable and needed, return `BLOCKED_NEEDS_EVIDENCE`.

## Required References
- references/ssh-ops-core.md

## Required Outputs
- remote_ops_plan.md
- claims_with_citations.md

## Response Format
- `status`: `PASS` or blocked reason.
- `assumptions`
- `claims_with_citations`
- `repro_steps`
- `artifact_paths`

## Artifact Scope
- Write specialist artifacts under internal group paths.
- Do not publish user-facing artifacts directly.
- Head controller decides what is exposed.
```

## 36. `generated/projects/proj-battery-001/agent-groups/developer/tools/allowlist.yaml`

- Type: `tool-policy`
- Purpose: Command/tool policy for group operations
- Locked Sections: `tool_restrictions`
- Validation Check: schema-validated
- Exposure Policy: source

```yaml
allowed_prefixes:
  - "python3"
  - "bash"
  - "sh"
  - "rg"
  - "sed"
  - "awk"
  - "cat"
  - "ls"
  - "git"
  - "pytest"
escalation_prefixes:
  - "ssh"
  - "sshpass"
  - "scp"
# BEGIN_LOCKED:tool_restrictions
forbidden_prefixes:
  - "rm -rf /"
  - "git reset --hard"
  - "mkfs"
  - "dd if="
wrapper_required_prefixes:
  - "pip install"
  - "conda install"
# END_LOCKED:tool_restrictions
tool_profile: "developer-default"
```

## 37. `generated/projects/proj-battery-001/agent-groups/material-scientist/AGENTS.md`

- Type: `agents`
- Purpose: Group operating contract and policy
- Locked Sections: `safety_policy, citation_gate, routing_audit, exposure_policy`
- Validation Check: content-reviewed
- Exposure Policy: source

```md
# Material Scientist Group - proj-battery-001

## Mission
Route and quality-gate specialist outputs for theoretical and computational materials science.

## Group Identity
- `group_id`: `material-scientist`
- `template_version`: `1.0.0`
- `tool_profile`: `science-default`
- `head_agent`: `material-scientist-head`
- `head_skill`: `proj-proj-battery-001-material-scientist-material-scientist-head`

## Specialist Roster
- `thermodynamics-specialist`: Phase stability, CALPHAD logic, free-energy reasoning (skill: `proj-proj-battery-001-material-scientist-thermodynamics-6ace8773`)
- `electronic-structure-specialist`: DFT setup, band structure interpretation, density-of-states analysis (skill: `proj-proj-battery-001-material-scientist-electronic-str-d41bc6b7`)
- `atomistic-simulation-specialist`: Atomistic simulation strategy, interatomic potential reasoning, trajectory interpretation (skill: `proj-proj-battery-001-material-scientist-atomistic-simu-a6a50b3f`)

## Work Directories
- `generated/projects/proj-battery-001/work/material-scientist/thermodynamics-specialist`
- `generated/projects/proj-battery-001/work/material-scientist/electronic-structure-specialist`
- `generated/projects/proj-battery-001/work/material-scientist/atomistic-simulation-specialist`

## Artifact Partition
- Internal specialist artifacts: `agent-groups/material-scientist/internal/<specialist>/...`
- Exposed group artifacts: `agent-groups/material-scientist/exposed/...`
- Visibility mode is controlled at project manifest level.

## Head Controller Protocol
1. Decompose objective into specialist tasks.
2. Dispatch hybrid execution (parallel for independent tasks, sequential for dependencies).
3. Enforce quality gates before accepting specialist outputs.
4. Merge outputs and publish decision log to exposed artifacts only.

BEGIN_LOCKED:safety_policy
## Safety Policy (Locked)
- Specialists work only inside assigned project workdirs.
- Potentially destructive commands must follow project tool policy and escalation rules.
- Head controller records command intent for each specialist stage.
END_LOCKED:safety_policy

BEGIN_LOCKED:citation_gate
## Citation Gate (Locked)
- Every key claim must include at least one citation.
- Allowed evidence sources: local references and verified web sources.
- If citations are missing for key claims, output status is `BLOCKED_UNCITED`.
- If web evidence is required but unavailable, output status is `BLOCKED_NEEDS_EVIDENCE`.
END_LOCKED:citation_gate

BEGIN_LOCKED:routing_audit
## Routing Audit (Locked)
- Head must record task graph, dependencies, and final merge rationale.
- Cross-domain final decisions require explicit head-controller sign-off.
END_LOCKED:routing_audit

BEGIN_LOCKED:exposure_policy
## Exposure Policy (Locked)
- Group-level outputs are user-visible by default.
- Specialist artifacts remain internal unless explicit audit mode is enabled.
END_LOCKED:exposure_policy

## Expected Deliverables
- `assumptions.md` from `thermodynamics-specialist`
- `claims_with_citations.md` from `thermodynamics-specialist`
- `phase_stability_notes.md` from `thermodynamics-specialist`
- `assumptions.md` from `electronic-structure-specialist`
- `claims_with_citations.md` from `electronic-structure-specialist`
- `electronic_summary.md` from `electronic-structure-specialist`
- `assumptions.md` from `atomistic-simulation-specialist`
- `claims_with_citations.md` from `atomistic-simulation-specialist`
- `simulation_plan.md` from `atomistic-simulation-specialist`

## Quality Gates
- `citation_required`: `True`
- `unresolved_claims_block`: `True`
- `peer_check_required`: `True`
- `consistency_required`: `True`
- `scope_required`: `True`
- `reproducibility_required`: `True`
```

## 38. `generated/projects/proj-battery-001/agent-groups/material-scientist/group.yaml`

- Type: `manifest`
- Purpose: Project or group manifest instance
- Locked Sections: `-`
- Validation Check: schema-validated
- Exposure Policy: source

```yaml
group_id: material-scientist
display_name: Material Scientist Group
template_version: 1.0.0
domain: materials-research
head:
  agent_id: material-scientist-head
  skill_name: grp-material-scientist-head
  mission: Route and quality-gate specialist outputs for theoretical and computational
    materials science.
  effective_skill_name: proj-proj-battery-001-material-scientist-material-scientist-head
specialists:
- agent_id: thermodynamics-specialist
  skill_name: grp-material-scientist-thermodynamics
  focus: Phase stability, CALPHAD logic, free-energy reasoning
  required_references:
  - references/thermodynamics-core.md
  required_outputs:
  - assumptions.md
  - claims_with_citations.md
  - phase_stability_notes.md
  effective_skill_name: proj-proj-battery-001-material-scientist-thermodynamics-6ace8773
- agent_id: electronic-structure-specialist
  skill_name: grp-material-scientist-electronic-structure
  focus: DFT setup, band structure interpretation, density-of-states analysis
  depends_on:
  - thermodynamics-specialist
  required_references:
  - references/electronic-structure-core.md
  required_outputs:
  - assumptions.md
  - claims_with_citations.md
  - electronic_summary.md
  effective_skill_name: proj-proj-battery-001-material-scientist-electronic-str-d41bc6b7
- agent_id: atomistic-simulation-specialist
  skill_name: grp-material-scientist-atomistic
  focus: Atomistic simulation strategy, interatomic potential reasoning, trajectory
    interpretation
  required_references:
  - references/atomistic-simulation-core.md
  required_outputs:
  - assumptions.md
  - claims_with_citations.md
  - simulation_plan.md
  effective_skill_name: proj-proj-battery-001-material-scientist-atomistic-simu-a6a50b3f
tool_profile: science-default
default_workdirs:
- inputs
- analysis
- outputs
quality_gates:
  citation_required: true
  unresolved_claims_block: true
  peer_check_required: true
  consistency_required: true
  scope_required: true
  reproducibility_required: true
```

## 39. `generated/projects/proj-battery-001/agent-groups/material-scientist/handoffs.yaml`

- Type: `handoff`
- Purpose: Intra-group handoff protocol
- Locked Sections: `-`
- Validation Check: content-reviewed
- Exposure Policy: source

```yaml
group_id: "material-scientist"
head_agent_id: "material-scientist-head"
handoffs:
  - from: "thermodynamics-specialist"
    to: "head-controller"
    condition: "after task completion"
  - from: "electronic-structure-specialist"
    to: "head-controller"
    condition: "after dependencies satisfied"
  - from: "atomistic-simulation-specialist"
    to: "head-controller"
    condition: "after task completion"
```

## 40. `generated/projects/proj-battery-001/agent-groups/material-scientist/skills/proj-proj-battery-001-material-scientist-atomistic-simu-a6a50b3f/SKILL.md`

- Type: `skill`
- Purpose: Operational skill definition for an agent or router
- Locked Sections: `-`
- Validation Check: content-reviewed
- Exposure Policy: source

```md
---
name: proj-proj-battery-001-material-scientist-atomistic-simu-a6a50b3f
description: Specialist agent for Atomistic simulation strategy, interatomic potential reasoning, trajectory interpretation in Material Scientist Group (project proj-battery-001). Use for narrow-domain expert analysis with claim-level citations.
---

# atomistic-simulation-specialist

## Scope
Atomistic simulation strategy, interatomic potential reasoning, trajectory interpretation

## Hard Gate Requirements
1. Every key claim must include a citation.
2. Assumptions must be explicit.
3. Output must stay within specialist scope.
4. Reproducibility details are mandatory.

If web evidence is unavailable and needed, return `BLOCKED_NEEDS_EVIDENCE`.

## Required References
- references/atomistic-simulation-core.md

## Required Outputs
- assumptions.md
- claims_with_citations.md
- simulation_plan.md

## Response Format
- `status`: `PASS` or blocked reason.
- `assumptions`
- `claims_with_citations`
- `repro_steps`
- `artifact_paths`

## Artifact Scope
- Write specialist artifacts under internal group paths.
- Do not publish user-facing artifacts directly.
- Head controller decides what is exposed.
```

## 41. `generated/projects/proj-battery-001/agent-groups/material-scientist/skills/proj-proj-battery-001-material-scientist-electronic-str-d41bc6b7/SKILL.md`

- Type: `skill`
- Purpose: Operational skill definition for an agent or router
- Locked Sections: `-`
- Validation Check: content-reviewed
- Exposure Policy: source

```md
---
name: proj-proj-battery-001-material-scientist-electronic-str-d41bc6b7
description: Specialist agent for DFT setup, band structure interpretation, density-of-states analysis in Material Scientist Group (project proj-battery-001). Use for narrow-domain expert analysis with claim-level citations.
---

# electronic-structure-specialist

## Scope
DFT setup, band structure interpretation, density-of-states analysis

## Hard Gate Requirements
1. Every key claim must include a citation.
2. Assumptions must be explicit.
3. Output must stay within specialist scope.
4. Reproducibility details are mandatory.

If web evidence is unavailable and needed, return `BLOCKED_NEEDS_EVIDENCE`.

## Required References
- references/electronic-structure-core.md

## Required Outputs
- assumptions.md
- claims_with_citations.md
- electronic_summary.md

## Response Format
- `status`: `PASS` or blocked reason.
- `assumptions`
- `claims_with_citations`
- `repro_steps`
- `artifact_paths`

## Artifact Scope
- Write specialist artifacts under internal group paths.
- Do not publish user-facing artifacts directly.
- Head controller decides what is exposed.
```

## 42. `generated/projects/proj-battery-001/agent-groups/material-scientist/skills/proj-proj-battery-001-material-scientist-material-scientist-head/SKILL.md`

- Type: `skill`
- Purpose: Operational skill definition for an agent or router
- Locked Sections: `-`
- Validation Check: content-reviewed
- Exposure Policy: source

```md
---
name: proj-proj-battery-001-material-scientist-material-scientist-head
description: Orchestrate Material Scientist Group for project proj-battery-001. Use when routing objective-level work to specialist agents with strict expert quality gates.
---

# Material Scientist Group Head Controller

## Scope
Route and merge specialist outputs for `material-scientist` in project `proj-battery-001`.

## Responsibilities
1. Build a task graph from the objective.
2. Dispatch hybrid execution: parallel for independent branches, sequential for dependencies.
3. Enforce citation/consistency/scope/reproducibility gates.
4. Publish final merged artifact index and decision log.

## Required Inputs
- `objective`
- `project_id`
- `group_id`
- current registry entry in `catalog/project-registry.yaml`

## Execution Contract
- Acquire per-agent workdir lease before write.
- Retry or reroute on lease conflict.
- Reject outputs that fail any hard gate.
- Consolidate specialist internal outputs before publishing group-exposed artifacts.

## Specialists
- thermodynamics-specialist: `proj-proj-battery-001-material-scientist-thermodynamics-6ace8773`
- electronic-structure-specialist: `proj-proj-battery-001-material-scientist-electronic-str-d41bc6b7`
- atomistic-simulation-specialist: `proj-proj-battery-001-material-scientist-atomistic-simu-a6a50b3f`

## Output Contract
- `dispatch_plan.json`
- `decision_log.md`
- `artifact_index.md`
```

## 43. `generated/projects/proj-battery-001/agent-groups/material-scientist/skills/proj-proj-battery-001-material-scientist-thermodynamics-6ace8773/SKILL.md`

- Type: `skill`
- Purpose: Operational skill definition for an agent or router
- Locked Sections: `-`
- Validation Check: content-reviewed
- Exposure Policy: source

```md
---
name: proj-proj-battery-001-material-scientist-thermodynamics-6ace8773
description: Specialist agent for Phase stability, CALPHAD logic, free-energy reasoning in Material Scientist Group (project proj-battery-001). Use for narrow-domain expert analysis with claim-level citations.
---

# thermodynamics-specialist

## Scope
Phase stability, CALPHAD logic, free-energy reasoning

## Hard Gate Requirements
1. Every key claim must include a citation.
2. Assumptions must be explicit.
3. Output must stay within specialist scope.
4. Reproducibility details are mandatory.

If web evidence is unavailable and needed, return `BLOCKED_NEEDS_EVIDENCE`.

## Required References
- references/thermodynamics-core.md

## Required Outputs
- assumptions.md
- claims_with_citations.md
- phase_stability_notes.md

## Response Format
- `status`: `PASS` or blocked reason.
- `assumptions`
- `claims_with_citations`
- `repro_steps`
- `artifact_paths`

## Artifact Scope
- Write specialist artifacts under internal group paths.
- Do not publish user-facing artifacts directly.
- Head controller decides what is exposed.
```

## 44. `generated/projects/proj-battery-001/agent-groups/material-scientist/tools/allowlist.yaml`

- Type: `tool-policy`
- Purpose: Command/tool policy for group operations
- Locked Sections: `tool_restrictions`
- Validation Check: schema-validated
- Exposure Policy: source

```yaml
allowed_prefixes:
  - "python3"
  - "bash"
  - "sh"
  - "rg"
  - "sed"
  - "awk"
  - "cat"
  - "ls"
  - "git"
  - "pytest"
escalation_prefixes:
  - "ssh"
  - "sshpass"
  - "scp"
# BEGIN_LOCKED:tool_restrictions
forbidden_prefixes:
  - "rm -rf /"
  - "git reset --hard"
  - "mkfs"
  - "dd if="
wrapper_required_prefixes:
  - "pip install"
  - "conda install"
# END_LOCKED:tool_restrictions
tool_profile: "science-default"
```

## 45. `generated/projects/proj-battery-001/agent-groups/quality-assurance/AGENTS.md`

- Type: `agents`
- Purpose: Group operating contract and policy
- Locked Sections: `safety_policy, citation_gate, routing_audit, exposure_policy`
- Validation Check: content-reviewed
- Exposure Policy: source

```md
# Quality Assurance Group - proj-battery-001

## Mission
Audit technical outputs for reproducibility, consistency, and decision-risk control.

## Group Identity
- `group_id`: `quality-assurance`
- `template_version`: `1.0.0`
- `tool_profile`: `qa-default`
- `head_agent`: `quality-assurance-head`
- `head_skill`: `proj-proj-battery-001-quality-assurance-quality-assurance-head`

## Specialist Roster
- `reproducibility-auditor`: Reproducibility checks, parameter traceability, and artifact completeness (skill: `proj-proj-battery-001-quality-assurance-reproducibility-auditor`)
- `consistency-auditor`: Cross-document consistency checks and contradiction detection (skill: `proj-proj-battery-001-quality-assurance-consistency-auditor`)
- `risk-auditor`: Risk classification, severity tagging, and mitigation recommendation framing (skill: `proj-proj-battery-001-quality-assurance-risk-auditor`)

## Work Directories
- `generated/projects/proj-battery-001/work/quality-assurance/reproducibility-auditor`
- `generated/projects/proj-battery-001/work/quality-assurance/consistency-auditor`
- `generated/projects/proj-battery-001/work/quality-assurance/risk-auditor`

## Artifact Partition
- Internal specialist artifacts: `agent-groups/quality-assurance/internal/<specialist>/...`
- Exposed group artifacts: `agent-groups/quality-assurance/exposed/...`
- Visibility mode is controlled at project manifest level.

## Head Controller Protocol
1. Decompose objective into specialist tasks.
2. Dispatch hybrid execution (parallel for independent tasks, sequential for dependencies).
3. Enforce quality gates before accepting specialist outputs.
4. Merge outputs and publish decision log to exposed artifacts only.

BEGIN_LOCKED:safety_policy
## Safety Policy (Locked)
- Specialists work only inside assigned project workdirs.
- Potentially destructive commands must follow project tool policy and escalation rules.
- Head controller records command intent for each specialist stage.
END_LOCKED:safety_policy

BEGIN_LOCKED:citation_gate
## Citation Gate (Locked)
- Every key claim must include at least one citation.
- Allowed evidence sources: local references and verified web sources.
- If citations are missing for key claims, output status is `BLOCKED_UNCITED`.
- If web evidence is required but unavailable, output status is `BLOCKED_NEEDS_EVIDENCE`.
END_LOCKED:citation_gate

BEGIN_LOCKED:routing_audit
## Routing Audit (Locked)
- Head must record task graph, dependencies, and final merge rationale.
- Cross-domain final decisions require explicit head-controller sign-off.
END_LOCKED:routing_audit

BEGIN_LOCKED:exposure_policy
## Exposure Policy (Locked)
- Group-level outputs are user-visible by default.
- Specialist artifacts remain internal unless explicit audit mode is enabled.
END_LOCKED:exposure_policy

## Expected Deliverables
- `repro_audit.md` from `reproducibility-auditor`
- `claims_with_citations.md` from `reproducibility-auditor`
- `consistency_audit.md` from `consistency-auditor`
- `claims_with_citations.md` from `consistency-auditor`
- `risk_register.md` from `risk-auditor`
- `claims_with_citations.md` from `risk-auditor`

## Quality Gates
- `citation_required`: `True`
- `unresolved_claims_block`: `True`
- `peer_check_required`: `True`
- `consistency_required`: `True`
- `scope_required`: `True`
- `reproducibility_required`: `True`
```

## 46. `generated/projects/proj-battery-001/agent-groups/quality-assurance/group.yaml`

- Type: `manifest`
- Purpose: Project or group manifest instance
- Locked Sections: `-`
- Validation Check: schema-validated
- Exposure Policy: source

```yaml
group_id: quality-assurance
display_name: Quality Assurance Group
template_version: 1.0.0
domain: verification-and-risk
head:
  agent_id: quality-assurance-head
  skill_name: grp-quality-assurance-head
  mission: Audit technical outputs for reproducibility, consistency, and decision-risk
    control.
  effective_skill_name: proj-proj-battery-001-quality-assurance-quality-assurance-head
specialists:
- agent_id: reproducibility-auditor
  skill_name: grp-quality-assurance-repro
  focus: Reproducibility checks, parameter traceability, and artifact completeness
  required_references:
  - references/reproducibility-core.md
  required_outputs:
  - repro_audit.md
  - claims_with_citations.md
  effective_skill_name: proj-proj-battery-001-quality-assurance-reproducibility-auditor
- agent_id: consistency-auditor
  skill_name: grp-quality-assurance-consistency
  focus: Cross-document consistency checks and contradiction detection
  required_references:
  - references/consistency-core.md
  required_outputs:
  - consistency_audit.md
  - claims_with_citations.md
  effective_skill_name: proj-proj-battery-001-quality-assurance-consistency-auditor
- agent_id: risk-auditor
  skill_name: grp-quality-assurance-risk
  focus: Risk classification, severity tagging, and mitigation recommendation framing
  depends_on:
  - consistency-auditor
  required_references:
  - references/risk-core.md
  required_outputs:
  - risk_register.md
  - claims_with_citations.md
  effective_skill_name: proj-proj-battery-001-quality-assurance-risk-auditor
tool_profile: qa-default
default_workdirs:
- inputs
- analysis
- outputs
quality_gates:
  citation_required: true
  unresolved_claims_block: true
  peer_check_required: true
  consistency_required: true
  scope_required: true
  reproducibility_required: true
```

## 47. `generated/projects/proj-battery-001/agent-groups/quality-assurance/handoffs.yaml`

- Type: `handoff`
- Purpose: Intra-group handoff protocol
- Locked Sections: `-`
- Validation Check: content-reviewed
- Exposure Policy: source

```yaml
group_id: "quality-assurance"
head_agent_id: "quality-assurance-head"
handoffs:
  - from: "reproducibility-auditor"
    to: "head-controller"
    condition: "after task completion"
  - from: "consistency-auditor"
    to: "head-controller"
    condition: "after task completion"
  - from: "risk-auditor"
    to: "head-controller"
    condition: "after dependencies satisfied"
```

## 48. `generated/projects/proj-battery-001/agent-groups/quality-assurance/skills/proj-proj-battery-001-quality-assurance-consistency-auditor/SKILL.md`

- Type: `skill`
- Purpose: Operational skill definition for an agent or router
- Locked Sections: `-`
- Validation Check: content-reviewed
- Exposure Policy: source

```md
---
name: proj-proj-battery-001-quality-assurance-consistency-auditor
description: Specialist agent for Cross-document consistency checks and contradiction detection in Quality Assurance Group (project proj-battery-001). Use for narrow-domain expert analysis with claim-level citations.
---

# consistency-auditor

## Scope
Cross-document consistency checks and contradiction detection

## Hard Gate Requirements
1. Every key claim must include a citation.
2. Assumptions must be explicit.
3. Output must stay within specialist scope.
4. Reproducibility details are mandatory.

If web evidence is unavailable and needed, return `BLOCKED_NEEDS_EVIDENCE`.

## Required References
- references/consistency-core.md

## Required Outputs
- consistency_audit.md
- claims_with_citations.md

## Response Format
- `status`: `PASS` or blocked reason.
- `assumptions`
- `claims_with_citations`
- `repro_steps`
- `artifact_paths`

## Artifact Scope
- Write specialist artifacts under internal group paths.
- Do not publish user-facing artifacts directly.
- Head controller decides what is exposed.
```

## 49. `generated/projects/proj-battery-001/agent-groups/quality-assurance/skills/proj-proj-battery-001-quality-assurance-quality-assurance-head/SKILL.md`

- Type: `skill`
- Purpose: Operational skill definition for an agent or router
- Locked Sections: `-`
- Validation Check: content-reviewed
- Exposure Policy: source

```md
---
name: proj-proj-battery-001-quality-assurance-quality-assurance-head
description: Orchestrate Quality Assurance Group for project proj-battery-001. Use when routing objective-level work to specialist agents with strict expert quality gates.
---

# Quality Assurance Group Head Controller

## Scope
Route and merge specialist outputs for `quality-assurance` in project `proj-battery-001`.

## Responsibilities
1. Build a task graph from the objective.
2. Dispatch hybrid execution: parallel for independent branches, sequential for dependencies.
3. Enforce citation/consistency/scope/reproducibility gates.
4. Publish final merged artifact index and decision log.

## Required Inputs
- `objective`
- `project_id`
- `group_id`
- current registry entry in `catalog/project-registry.yaml`

## Execution Contract
- Acquire per-agent workdir lease before write.
- Retry or reroute on lease conflict.
- Reject outputs that fail any hard gate.
- Consolidate specialist internal outputs before publishing group-exposed artifacts.

## Specialists
- reproducibility-auditor: `proj-proj-battery-001-quality-assurance-reproducibility-auditor`
- consistency-auditor: `proj-proj-battery-001-quality-assurance-consistency-auditor`
- risk-auditor: `proj-proj-battery-001-quality-assurance-risk-auditor`

## Output Contract
- `dispatch_plan.json`
- `decision_log.md`
- `artifact_index.md`
```

## 50. `generated/projects/proj-battery-001/agent-groups/quality-assurance/skills/proj-proj-battery-001-quality-assurance-reproducibility-auditor/SKILL.md`

- Type: `skill`
- Purpose: Operational skill definition for an agent or router
- Locked Sections: `-`
- Validation Check: content-reviewed
- Exposure Policy: source

```md
---
name: proj-proj-battery-001-quality-assurance-reproducibility-auditor
description: Specialist agent for Reproducibility checks, parameter traceability, and artifact completeness in Quality Assurance Group (project proj-battery-001). Use for narrow-domain expert analysis with claim-level citations.
---

# reproducibility-auditor

## Scope
Reproducibility checks, parameter traceability, and artifact completeness

## Hard Gate Requirements
1. Every key claim must include a citation.
2. Assumptions must be explicit.
3. Output must stay within specialist scope.
4. Reproducibility details are mandatory.

If web evidence is unavailable and needed, return `BLOCKED_NEEDS_EVIDENCE`.

## Required References
- references/reproducibility-core.md

## Required Outputs
- repro_audit.md
- claims_with_citations.md

## Response Format
- `status`: `PASS` or blocked reason.
- `assumptions`
- `claims_with_citations`
- `repro_steps`
- `artifact_paths`

## Artifact Scope
- Write specialist artifacts under internal group paths.
- Do not publish user-facing artifacts directly.
- Head controller decides what is exposed.
```

## 51. `generated/projects/proj-battery-001/agent-groups/quality-assurance/skills/proj-proj-battery-001-quality-assurance-risk-auditor/SKILL.md`

- Type: `skill`
- Purpose: Operational skill definition for an agent or router
- Locked Sections: `-`
- Validation Check: content-reviewed
- Exposure Policy: source

```md
---
name: proj-proj-battery-001-quality-assurance-risk-auditor
description: Specialist agent for Risk classification, severity tagging, and mitigation recommendation framing in Quality Assurance Group (project proj-battery-001). Use for narrow-domain expert analysis with claim-level citations.
---

# risk-auditor

## Scope
Risk classification, severity tagging, and mitigation recommendation framing

## Hard Gate Requirements
1. Every key claim must include a citation.
2. Assumptions must be explicit.
3. Output must stay within specialist scope.
4. Reproducibility details are mandatory.

If web evidence is unavailable and needed, return `BLOCKED_NEEDS_EVIDENCE`.

## Required References
- references/risk-core.md

## Required Outputs
- risk_register.md
- claims_with_citations.md

## Response Format
- `status`: `PASS` or blocked reason.
- `assumptions`
- `claims_with_citations`
- `repro_steps`
- `artifact_paths`

## Artifact Scope
- Write specialist artifacts under internal group paths.
- Do not publish user-facing artifacts directly.
- Head controller decides what is exposed.
```

## 52. `generated/projects/proj-battery-001/agent-groups/quality-assurance/tools/allowlist.yaml`

- Type: `tool-policy`
- Purpose: Command/tool policy for group operations
- Locked Sections: `tool_restrictions`
- Validation Check: schema-validated
- Exposure Policy: source

```yaml
allowed_prefixes:
  - "python3"
  - "bash"
  - "sh"
  - "rg"
  - "sed"
  - "awk"
  - "cat"
  - "ls"
  - "git"
  - "pytest"
escalation_prefixes:
  - "ssh"
  - "sshpass"
  - "scp"
# BEGIN_LOCKED:tool_restrictions
forbidden_prefixes:
  - "rm -rf /"
  - "git reset --hard"
  - "mkfs"
  - "dd if="
wrapper_required_prefixes:
  - "pip install"
  - "conda install"
# END_LOCKED:tool_restrictions
tool_profile: "qa-default"
```

## 53. `generated/projects/proj-battery-001/manifest.yaml`

- Type: `manifest`
- Purpose: Project or group manifest instance
- Locked Sections: `-`
- Validation Check: schema-validated
- Exposure Policy: source

```yaml
project_id: proj-battery-001
selected_groups:
- material-scientist
- developer
- quality-assurance
install_targets:
  codex_skill_dir: /Users/moon.s.june/.codex/skills/local
router_skill_name: research-router
bundle_version: 1.0.0
template_versions:
  material-scientist: 1.0.0
  developer: 1.0.0
  quality-assurance: 1.0.0
visibility:
  mode: group-only
  audit_override: true
overlays:
  allow_project_overrides: true
  protected_sections:
  - safety_policy
  - citation_gate
  - tool_restrictions
  - routing_audit
groups:
  material-scientist:
    manifest_path: agent-groups/material-scientist/group.yaml
    skill_dirs:
    - agent-groups/material-scientist/skills/proj-proj-battery-001-material-scientist-material-scientist-head
    - agent-groups/material-scientist/skills/proj-proj-battery-001-material-scientist-thermodynamics-6ace8773
    - agent-groups/material-scientist/skills/proj-proj-battery-001-material-scientist-electronic-str-d41bc6b7
    - agent-groups/material-scientist/skills/proj-proj-battery-001-material-scientist-atomistic-simu-a6a50b3f
    head_skill_dir: agent-groups/material-scientist/skills/proj-proj-battery-001-material-scientist-material-scientist-head
    specialist_skill_dirs:
    - agent-groups/material-scientist/skills/proj-proj-battery-001-material-scientist-thermodynamics-6ace8773
    - agent-groups/material-scientist/skills/proj-proj-battery-001-material-scientist-electronic-str-d41bc6b7
    - agent-groups/material-scientist/skills/proj-proj-battery-001-material-scientist-atomistic-simu-a6a50b3f
  developer:
    manifest_path: agent-groups/developer/group.yaml
    skill_dirs:
    - agent-groups/developer/skills/proj-proj-battery-001-developer-developer-head
    - agent-groups/developer/skills/proj-proj-battery-001-developer-python-expert
    - agent-groups/developer/skills/proj-proj-battery-001-developer-shell-expert
    - agent-groups/developer/skills/proj-proj-battery-001-developer-ssh-remote-ops-expert
    head_skill_dir: agent-groups/developer/skills/proj-proj-battery-001-developer-developer-head
    specialist_skill_dirs:
    - agent-groups/developer/skills/proj-proj-battery-001-developer-python-expert
    - agent-groups/developer/skills/proj-proj-battery-001-developer-shell-expert
    - agent-groups/developer/skills/proj-proj-battery-001-developer-ssh-remote-ops-expert
  quality-assurance:
    manifest_path: agent-groups/quality-assurance/group.yaml
    skill_dirs:
    - agent-groups/quality-assurance/skills/proj-proj-battery-001-quality-assurance-quality-assurance-head
    - agent-groups/quality-assurance/skills/proj-proj-battery-001-quality-assurance-reproducibility-auditor
    - agent-groups/quality-assurance/skills/proj-proj-battery-001-quality-assurance-consistency-auditor
    - agent-groups/quality-assurance/skills/proj-proj-battery-001-quality-assurance-risk-auditor
    head_skill_dir: agent-groups/quality-assurance/skills/proj-proj-battery-001-quality-assurance-quality-assurance-head
    specialist_skill_dirs:
    - agent-groups/quality-assurance/skills/proj-proj-battery-001-quality-assurance-reproducibility-auditor
    - agent-groups/quality-assurance/skills/proj-proj-battery-001-quality-assurance-consistency-auditor
    - agent-groups/quality-assurance/skills/proj-proj-battery-001-quality-assurance-risk-auditor
```

