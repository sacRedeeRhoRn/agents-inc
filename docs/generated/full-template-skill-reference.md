# Full Template and Skill Reference

Generated at: `2026-03-02T13:55:14Z`
Fabric root: `/home/msj/Desktop/playground/agents-inc_dev/agents-inc`
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
| 5 | `templates/group/references/starters/domain-core.md` | template | Template used for generated groups/router | `-` | content-reviewed | group-scoped |
| 6 | `templates/group/references/starters/evidence-review.md` | template | Template used for generated groups/router | `-` | content-reviewed | group-scoped |
| 7 | `templates/group/references/starters/integration.md` | template | Template used for generated groups/router | `-` | content-reviewed | group-scoped |
| 8 | `templates/group/references/starters/repro-qa.md` | template | Template used for generated groups/router | `-` | content-reviewed | group-scoped |
| 9 | `templates/group/references/starters/web-research.md` | template | Template used for generated groups/router | `-` | content-reviewed | group-scoped |
| 10 | `templates/group/skills/head/SKILL.template.md` | template | Template used for generated groups/router | `-` | content-reviewed | group-scoped |
| 11 | `templates/group/skills/specialist/SKILL.template.md` | template | Template used for generated groups/router | `-` | content-reviewed | group-scoped |
| 12 | `templates/group/specialist-AGENTS.template.md` | template | Template used for generated groups/router | `-` | content-reviewed | group-scoped |
| 13 | `templates/group/tools/allowlist.template.yaml` | template | Template used for generated groups/router | `tool_restrictions` | content-reviewed | group-scoped |
| 14 | `templates/group/tools/wrappers/README.txt` | template | Template used for generated groups/router | `-` | content-reviewed | group-scoped |
| 15 | `templates/router/research-router/SKILL.template.md` | template | Template used for generated groups/router | `-` | content-reviewed | group-scoped |
| 16 | `schemas/connection.schema.yaml` | schema | Validation schema for manifests and dispatch contracts | `-` | schema-validated | source |
| 17 | `schemas/dispatch.schema.yaml` | schema | Validation schema for manifests and dispatch contracts | `-` | schema-validated | source |
| 18 | `schemas/escalation.schema.yaml` | schema | Validation schema for manifests and dispatch contracts | `-` | schema-validated | source |
| 19 | `schemas/group.schema.yaml` | schema | Validation schema for manifests and dispatch contracts | `-` | schema-validated | source |
| 20 | `schemas/project.schema.yaml` | schema | Validation schema for manifests and dispatch contracts | `-` | schema-validated | source |
| 21 | `schemas/tool_policy.schema.yaml` | schema | Validation schema for manifests and dispatch contracts | `-` | schema-validated | source |
| 22 | `catalog/groups/data-curation.yaml` | catalog | Reusable source-of-truth group/profile/registry metadata | `-` | schema-validated | source |
| 23 | `catalog/groups/design-communication.yaml` | catalog | Reusable source-of-truth group/profile/registry metadata | `-` | schema-validated | source |
| 24 | `catalog/groups/developer.yaml` | catalog | Reusable source-of-truth group/profile/registry metadata | `-` | schema-validated | source |
| 25 | `catalog/groups/integration-delivery.yaml` | catalog | Reusable source-of-truth group/profile/registry metadata | `-` | schema-validated | source |
| 26 | `catalog/groups/literature-intelligence.yaml` | catalog | Reusable source-of-truth group/profile/registry metadata | `-` | schema-validated | source |
| 27 | `catalog/groups/quality-assurance.yaml` | catalog | Reusable source-of-truth group/profile/registry metadata | `-` | schema-validated | source |
| 28 | `catalog/profiles/delivery-core.yaml` | catalog | Reusable source-of-truth group/profile/registry metadata | `-` | schema-validated | source |
| 29 | `catalog/profiles/professional-services-core.yaml` | catalog | Reusable source-of-truth group/profile/registry metadata | `-` | schema-validated | source |
| 30 | `catalog/profiles/rapid-debug.yaml` | catalog | Reusable source-of-truth group/profile/registry metadata | `-` | schema-validated | source |
| 31 | `catalog/project-registry.yaml` | catalog | Reusable source-of-truth group/profile/registry metadata | `-` | schema-validated | source |
| 32 | `generated/projects/proj-test-alpha/agent-groups/integration-delivery/AGENTS.md` | agents | Group operating contract and policy | `safety_policy, citation_gate, routing_audit, exposure_policy` | content-reviewed | source |
| 33 | `generated/projects/proj-test-alpha/agent-groups/integration-delivery/group.yaml` | manifest | Project or group manifest instance | `-` | schema-validated | source |
| 34 | `generated/projects/proj-test-alpha/agent-groups/integration-delivery/handoffs.yaml` | handoff | Intra-group handoff protocol | `-` | content-reviewed | source |
| 35 | `generated/projects/proj-test-alpha/agent-groups/integration-delivery/internal/delivery-architect/AGENTS.md` | agents | Group operating contract and policy | `-` | content-reviewed | source |
| 36 | `generated/projects/proj-test-alpha/agent-groups/integration-delivery/internal/dependency-mapping-specialist/AGENTS.md` | agents | Group operating contract and policy | `-` | content-reviewed | source |
| 37 | `generated/projects/proj-test-alpha/agent-groups/integration-delivery/internal/evidence-review-specialist/AGENTS.md` | agents | Group operating contract and policy | `-` | content-reviewed | source |
| 38 | `generated/projects/proj-test-alpha/agent-groups/integration-delivery/internal/integration-specialist/AGENTS.md` | agents | Group operating contract and policy | `-` | content-reviewed | source |
| 39 | `generated/projects/proj-test-alpha/agent-groups/integration-delivery/internal/repro-qa-specialist/AGENTS.md` | agents | Group operating contract and policy | `-` | content-reviewed | source |
| 40 | `generated/projects/proj-test-alpha/agent-groups/integration-delivery/internal/web-research-specialist/AGENTS.md` | agents | Group operating contract and policy | `-` | content-reviewed | source |
| 41 | `generated/projects/proj-test-alpha/agent-groups/integration-delivery/skills/integration-delivery-delivery-architect--proj-test-alpha/SKILL.md` | skill | Operational skill definition for an agent or router | `-` | content-reviewed | source |
| 42 | `generated/projects/proj-test-alpha/agent-groups/integration-delivery/skills/integration-delivery-dependency-mapping-specialist--pro-acbf437d/SKILL.md` | skill | Operational skill definition for an agent or router | `-` | content-reviewed | source |
| 43 | `generated/projects/proj-test-alpha/agent-groups/integration-delivery/skills/integration-delivery-evidence-review-specialist--proj-test-alpha/SKILL.md` | skill | Operational skill definition for an agent or router | `-` | content-reviewed | source |
| 44 | `generated/projects/proj-test-alpha/agent-groups/integration-delivery/skills/integration-delivery-integration-delivery-head--proj-test-alpha/SKILL.md` | skill | Operational skill definition for an agent or router | `-` | content-reviewed | source |
| 45 | `generated/projects/proj-test-alpha/agent-groups/integration-delivery/skills/integration-delivery-integration-specialist--proj-test-alpha/SKILL.md` | skill | Operational skill definition for an agent or router | `-` | content-reviewed | source |
| 46 | `generated/projects/proj-test-alpha/agent-groups/integration-delivery/skills/integration-delivery-repro-qa-specialist--proj-test-alpha/SKILL.md` | skill | Operational skill definition for an agent or router | `-` | content-reviewed | source |
| 47 | `generated/projects/proj-test-alpha/agent-groups/integration-delivery/skills/integration-delivery-web-research-specialist--proj-test-alpha/SKILL.md` | skill | Operational skill definition for an agent or router | `-` | content-reviewed | source |
| 48 | `generated/projects/proj-test-alpha/agent-groups/integration-delivery/tools/allowlist.yaml` | tool-policy | Command/tool policy for group operations | `tool_restrictions` | schema-validated | source |
| 49 | `generated/projects/proj-test-alpha/manifest.yaml` | manifest | Project or group manifest instance | `-` | schema-validated | source |
| 50 | `generated/projects/proj-test-hpc/agent-groups/integration-delivery/AGENTS.md` | agents | Group operating contract and policy | `safety_policy, citation_gate, routing_audit, exposure_policy` | content-reviewed | source |
| 51 | `generated/projects/proj-test-hpc/agent-groups/integration-delivery/group.yaml` | manifest | Project or group manifest instance | `-` | schema-validated | source |
| 52 | `generated/projects/proj-test-hpc/agent-groups/integration-delivery/handoffs.yaml` | handoff | Intra-group handoff protocol | `-` | content-reviewed | source |
| 53 | `generated/projects/proj-test-hpc/agent-groups/integration-delivery/internal/delivery-architect/AGENTS.md` | agents | Group operating contract and policy | `-` | content-reviewed | source |
| 54 | `generated/projects/proj-test-hpc/agent-groups/integration-delivery/internal/dependency-mapping-specialist/AGENTS.md` | agents | Group operating contract and policy | `-` | content-reviewed | source |
| 55 | `generated/projects/proj-test-hpc/agent-groups/integration-delivery/internal/evidence-review-specialist/AGENTS.md` | agents | Group operating contract and policy | `-` | content-reviewed | source |
| 56 | `generated/projects/proj-test-hpc/agent-groups/integration-delivery/internal/integration-specialist/AGENTS.md` | agents | Group operating contract and policy | `-` | content-reviewed | source |
| 57 | `generated/projects/proj-test-hpc/agent-groups/integration-delivery/internal/repro-qa-specialist/AGENTS.md` | agents | Group operating contract and policy | `-` | content-reviewed | source |
| 58 | `generated/projects/proj-test-hpc/agent-groups/integration-delivery/internal/web-research-specialist/AGENTS.md` | agents | Group operating contract and policy | `-` | content-reviewed | source |
| 59 | `generated/projects/proj-test-hpc/agent-groups/integration-delivery/skills/integration-delivery-delivery-architect--proj-test-hpc/SKILL.md` | skill | Operational skill definition for an agent or router | `-` | content-reviewed | source |
| 60 | `generated/projects/proj-test-hpc/agent-groups/integration-delivery/skills/integration-delivery-dependency-mapping-specialist--pro-e1e000cd/SKILL.md` | skill | Operational skill definition for an agent or router | `-` | content-reviewed | source |
| 61 | `generated/projects/proj-test-hpc/agent-groups/integration-delivery/skills/integration-delivery-evidence-review-specialist--proj-test-hpc/SKILL.md` | skill | Operational skill definition for an agent or router | `-` | content-reviewed | source |
| 62 | `generated/projects/proj-test-hpc/agent-groups/integration-delivery/skills/integration-delivery-integration-delivery-head--proj-test-hpc/SKILL.md` | skill | Operational skill definition for an agent or router | `-` | content-reviewed | source |
| 63 | `generated/projects/proj-test-hpc/agent-groups/integration-delivery/skills/integration-delivery-integration-specialist--proj-test-hpc/SKILL.md` | skill | Operational skill definition for an agent or router | `-` | content-reviewed | source |
| 64 | `generated/projects/proj-test-hpc/agent-groups/integration-delivery/skills/integration-delivery-repro-qa-specialist--proj-test-hpc/SKILL.md` | skill | Operational skill definition for an agent or router | `-` | content-reviewed | source |
| 65 | `generated/projects/proj-test-hpc/agent-groups/integration-delivery/skills/integration-delivery-web-research-specialist--proj-test-hpc/SKILL.md` | skill | Operational skill definition for an agent or router | `-` | content-reviewed | source |
| 66 | `generated/projects/proj-test-hpc/agent-groups/integration-delivery/tools/allowlist.yaml` | tool-policy | Command/tool policy for group operations | `tool_restrictions` | schema-validated | source |
| 67 | `generated/projects/proj-test-hpc/manifest.yaml` | manifest | Project or group manifest instance | `-` | schema-validated | source |

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
- Specialist runtime instructions: `agent-groups/{{GROUP_ID}}/internal/<specialist>/AGENTS.md`
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
schema_version: "3.0"
group_id: "{{GROUP_ID}}"
handoffs:
{{HANDOFF_BLOCK}}
output_contract:
  specialist_internal:
    - "internal/<agent-id>/work.md"
    - "internal/<agent-id>/handoff.json"
  head_exposed:
    - "exposed/summary.md"
    - "exposed/handoff.json"
    - "exposed/INTEGRATION_NOTES.md"
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

## 5. `templates/group/references/starters/domain-core.md`

- Type: `template`
- Purpose: Template used for generated groups/router
- Locked Sections: `-`
- Validation Check: content-reviewed
- Exposure Policy: group-scoped

```md
# {{REFERENCE_TITLE}} - Domain Core Starter

## Scope
Covers foundational domain reasoning for `{{SPECIALIST_AGENT_ID}}` (`{{SPECIALIST_ROLE}}`) in `{{DISPLAY_NAME}}`.
Do not use this pack for cross-group integration decisions.

## Core Concepts & Key Checks
- Define assumptions explicitly before derived claims.
- Keep domain terminology and units consistent.
- Anchor each key claim with at least one local reference citation.

## Checklist
- Objective decomposed into domain sub-problems.
- Claim-level citations present for key assertions.
- Reproducibility path to generated artifacts is documented.

## Citation Guidance
Use local group references first (`references/*.md`).
When web sources are needed, include stable URLs and source context.

## Worked Micro-Example
Claim: "Derived quantity follows trend X under assumption Y."
Evidence: `local:references/{{REFERENCE_TITLE}}.md`
```

## 6. `templates/group/references/starters/evidence-review.md`

- Type: `template`
- Purpose: Template used for generated groups/router
- Locked Sections: `-`
- Validation Check: content-reviewed
- Exposure Policy: group-scoped

```md
# {{REFERENCE_TITLE}} - Evidence Review Starter

## Scope
Covers claim validation, contradiction detection, and evidence sufficiency review.

## Core Concepts & Key Checks
- Classify each claim as supported, unsupported, or contradictory.
- Trace each supported claim to explicit citations.
- Separate factual evidence from interpretation.

## Checklist
- `unsupported_claims` list produced.
- `contradictions` field set explicitly (`true`/`false`).
- Review rationale explains block/retry recommendations.

## Citation Guidance
A claim is supported only when at least one citation directly backs the exact assertion.

## Worked Micro-Example
Claim: "System guarantees exactly-once behavior."
Review: unsupported unless protocol-level evidence is cited.
```

## 7. `templates/group/references/starters/integration.md`

- Type: `template`
- Purpose: Template used for generated groups/router
- Locked Sections: `-`
- Validation Check: content-reviewed
- Exposure Policy: group-scoped

```md
# {{REFERENCE_TITLE}} - Integration Starter

## Scope
Covers cross-specialist artifact integration and dependency risk assessment.

## Core Concepts & Key Checks
- Identify all consumed upstream artifacts.
- Verify schema compatibility and path consistency.
- Record integration risks and mitigation actions.

## Checklist
- `dependencies_consumed` list is complete.
- `integration_risks` list is present (empty allowed).
- Final handoff references only validated upstream artifacts.

## Citation Guidance
Cite internal handoff artifacts directly by path and include any external dependency docs.

## Worked Micro-Example
Consumed: `agent-groups/<group>/internal/<agent>/handoff.json`
Risk: "Schema mismatch with downstream consumer".
```

## 8. `templates/group/references/starters/repro-qa.md`

- Type: `template`
- Purpose: Template used for generated groups/router
- Locked Sections: `-`
- Validation Check: content-reviewed
- Exposure Policy: group-scoped

```md
# {{REFERENCE_TITLE}} - Repro QA Starter

## Scope
Covers reproducibility command validation and expected-output checks.

## Core Concepts & Key Checks
- Commands must be runnable as provided.
- Preconditions (inputs, environment, paths) must be explicit.
- Expected outputs and pass/fail criteria must be measurable.

## Checklist
- `repro_commands` includes at least one executable command.
- `expected_outputs` specifies concrete success indicators.
- Artifact paths are valid and scoped correctly.

## Citation Guidance
When command behavior depends on tools/frameworks, cite the relevant official docs.

## Worked Micro-Example
Command: `python -m pytest tests/test_smoke.py`
Expected: "N passed" and exit code 0.
```

## 9. `templates/group/references/starters/web-research.md`

- Type: `template`
- Purpose: Template used for generated groups/router
- Locked Sections: `-`
- Validation Check: content-reviewed
- Exposure Policy: group-scoped

```md
# {{REFERENCE_TITLE}} - Web Research Starter

## Scope
Covers external-source discovery and citation-quality filtering for `{{SPECIALIST_AGENT_ID}}`.

## Core Concepts & Key Checks
- Use multiple independent sources for each critical claim.
- Prioritize primary sources and official documentation.
- Record publication date and provenance for each citation.

## Checklist
- At least three relevant web citations collected.
- Source quality notes added (authority, recency, bias).
- Contradictory sources flagged explicitly.

## Citation Guidance
Prefer `https://` references with identifiable publisher/author context.
Avoid low-confidence sources unless clearly labeled as tentative.

## Worked Micro-Example
Claim: "Interface behavior changed in version N."
Evidence:
- https://example.org/release-notes
- https://example.org/docs
- https://example.org/changelog
```

## 10. `templates/group/skills/head/SKILL.template.md`

- Type: `template`
- Purpose: Template used for generated groups/router
- Locked Sections: `-`
- Validation Check: content-reviewed
- Exposure Policy: group-scoped

```md
---
name: {{HEAD_SKILL_NAME}}
version: "3.1.1"
role: head
description: Head orchestrator for {{DISPLAY_NAME}} in project {{PROJECT_ID}} with negotiation and quality-gate control.
scope: Group-level orchestration, gate enforcement, and exposed artifact publication.
inputs:
  - objective
  - project_id
  - group_id
  - dispatch_plan
outputs:
  - exposed/summary.md
  - exposed/handoff.json
  - exposed/INTEGRATION_NOTES.md
failure_modes:
  - blocked_uncited_claims
  - unresolved_cross_domain_decision
  - missing_required_artifact
autouse_triggers:
  - group objective dispatch
  - specialist handoff aggregation
---

# {{DISPLAY_NAME}} Head Controller

## Mission
{{GROUP_PURPOSE}}

## When to Invoke
- Group-level objective requires orchestration across specialists.
- The active group is `{{GROUP_ID}}` in project `{{PROJECT_ID}}`.

## Definition of Done
{{GROUP_SUCCESS_CRITERIA_BLOCK}}

## Method
1. Build a dependency-aware dispatch plan from specialist roster and handoff constraints.
2. Execute independent tasks in parallel and dependency chains sequentially.
3. Enforce quality gates; reject, retry, or request clarification on blocked outputs.
4. Merge accepted specialist artifacts into exposed group deliverables with traceability.
5. Record integration notes, unresolved assumptions, and escalation requirements.

## Specialists
{{SPECIALIST_SKILL_BLOCK}}

## Gate Profile
{{GATE_CHECKS_BLOCK}}

## Exposed Deliverables
- `exposed/summary.md`
- `exposed/handoff.json`
- `exposed/INTEGRATION_NOTES.md`
```

## 11. `templates/group/skills/specialist/SKILL.template.md`

- Type: `template`
- Purpose: Template used for generated groups/router
- Locked Sections: `-`
- Validation Check: content-reviewed
- Exposure Policy: group-scoped

```md
---
name: {{SPECIALIST_SKILL_NAME}}
version: "3.1.1"
role: specialist
description: {{SPECIALIST_ROLE}} specialist for {{DISPLAY_NAME}} focused on {{SPECIALIST_FOCUS}} in project {{PROJECT_ID}}.
scope: Narrow specialist execution only; no cross-domain final decisions.
inputs:
  - objective
  - group-context.json
  - dependency artifacts
outputs:
  - internal/{{SPECIALIST_AGENT_ID}}/work.md
  - internal/{{SPECIALIST_AGENT_ID}}/handoff.json
failure_modes:
  - blocked_needs_evidence
  - blocked_uncited
  - scope_violation
autouse_triggers:
  - specialist dispatch task
  - dependency artifact ready
---

# {{SPECIALIST_AGENT_ID}}

## Mission
{{GROUP_PURPOSE}}

## Scope
{{SPECIALIST_FOCUS}}

## When to Invoke
- The objective requires `{{SPECIALIST_ROLE}}` expertise.
- Specialist focus applies: {{SPECIALIST_FOCUS}}
- Group context: `{{GROUP_ID}}` in project `{{PROJECT_ID}}`.

## Definition of Done
{{SPECIALIST_DONE_BLOCK}}

## Method
{{SPECIALIST_METHOD_BLOCK}}

## Artifacts to Produce
{{SPECIALIST_OUTPUT_BLOCK}}

## Failure Modes
{{SPECIALIST_FAILURE_BLOCK}}

## References
{{SPECIALIST_REFERENCE_BLOCK}}

## Gate Profile
{{GATE_CHECKS_BLOCK}}

## Output Contract
- Return `BEGIN_WORK/END_WORK` markdown notes.
- Return `BEGIN_HANDOFF_JSON/END_HANDOFF_JSON` JSON object.
- Include `claims_with_citations`, `execution_status`, `dependencies_satisfied`, and reproducibility details.
```

## 12. `templates/group/specialist-AGENTS.template.md`

- Type: `template`
- Purpose: Template used for generated groups/router
- Locked Sections: `-`
- Validation Check: content-reviewed
- Exposure Policy: group-scoped

```md
# {{DISPLAY_NAME}} Specialist - {{SPECIALIST_AGENT_ID}}

## Role Contract
- `project_id`: `{{PROJECT_ID}}`
- `group_id`: `{{GROUP_ID}}`
- `role`: `{{SPECIALIST_ROLE}}`
- `focus`: {{SPECIALIST_FOCUS}}
- `skill`: `{{SPECIALIST_SKILL_NAME}}`

## Activation
Activate and follow the `${{SPECIALIST_SKILL_NAME}}` skill before proceeding.

## Required Outputs
{{SPECIALIST_OUTPUT_BLOCK}}

## Required References
{{SPECIALIST_REFERENCE_BLOCK}}

## Hard Gate Checks
{{GATE_CHECKS_BLOCK}}

## Execution Boundaries
- Write only under `agent-groups/{{GROUP_ID}}/internal/{{SPECIALIST_AGENT_ID}}/`.
- Do not publish exposed artifacts directly.
- If key evidence is missing, return a blocked status with explicit reasons.
```

## 13. `templates/group/tools/allowlist.template.yaml`

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

## 14. `templates/group/tools/wrappers/README.txt`

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

## 15. `templates/router/research-router/SKILL.template.md`

- Type: `template`
- Purpose: Template used for generated groups/router
- Locked Sections: `-`
- Validation Check: content-reviewed
- Exposure Policy: group-scoped

```md
---
name: research-router
version: 3.1.1
role: router
description: Global router for expert multi-agent group bundles. Route to orchestrator-reply with strict artifact-grounded contracts.
scope: Project and group dispatch orchestration only.
inputs:
- project_id
- group_id
- objective
outputs:
- final-exposed-answer.md
- blocked-report.md
- delegation-ledger.json
- negotiation-sequence.md
- group-evidence-index.json
failure_modes:
- unknown_project
- unknown_group
- blocked_group_contributions
- blocked_needs_evidence
- blocked_quality_gate
autouse_triggers:
- router objective command
---

# Research Router

## Usage
Use this skill as:

`Use $research-router for project <project-id> group <group-id>: <objective>.`

Mode contract:
- If request starts with `[non-group]`, return concise direct state answer without delegation.
- Otherwise, execute full group delegation + negotiation + synthesis through `agents-inc orchestrator-reply`.

## Router Runtime Contract
1. Never synthesize the final research plan directly inside this skill.
2. Always run:

```bash
agents-inc orchestrator-reply --project-id <project-id> --group <group-id> --message "<objective>"
```

3. If command passes, read and return `<project-root>/.agents-inc/turns/<turn-id>/final-exposed-answer.md`.
4. If command blocks, read and return `<project-root>/.agents-inc/turns/<turn-id>/blocked-report.md`.
5. Do not bypass block status with freehand summaries.

## Hard Requirements
- Group-routed output must be artifact-grounded from exposed group artifacts.
- All active project groups must contribute valid exposed handoffs.
- Evidence must be present from web URLs and/or artifact citations.
- Specialist artifacts remain internal unless audit mode is explicitly enabled.
- Always include delegation and negotiation artifact references in group-routed responses.

## Notes
- `{{FABRIC_ROOT}}` is used for project resolution context only.
- Runtime execution should rely on `agents-inc` CLI, not hardcoded script paths.
```

## 16. `schemas/connection.schema.yaml`

- Type: `schema`
- Purpose: Validation schema for manifests and dispatch contracts
- Locked Sections: `-`
- Validation Check: schema-validated
- Exposure Policy: source

```yaml
$schema: "https://json-schema.org/draft/2020-12/schema"
title: "Connection Profile"
type: object
required:
  - schema_version
  - profile_name
  - type
properties:
  schema_version:
    type: string
  profile_name:
    type: string
  type:
    type: string
    enum: [ssh_connection, file_path, api_token, permission, custom]
  host:
    type: string
  port:
    type: integer
  user:
    type: string
  auth_method:
    type: string
  key_path:
    type: string
  keychain_key:
    type: string
  updated_at:
    type: string
additionalProperties: true
```

## 17. `schemas/dispatch.schema.yaml`

- Type: `schema`
- Purpose: Validation schema for manifests and dispatch contracts
- Locked Sections: `-`
- Validation Check: schema-validated
- Exposure Policy: source

```yaml
$schema: "https://json-schema.org/draft/2020-12/schema"
title: "Dispatch Plan v2"
type: object
required:
  - project_id
  - group_id
  - objective
  - dispatch_mode
  - session_mode
  - phases
  - gate_profile
  - specialist_output_schema
  - locking
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
  specialist_output_schema:
    type: string
  gate_profile:
    type: object
  group_web_search_default:
    type: boolean
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
            required: [agent_id, role, focus, skill_name, workdir]
            properties:
              agent_id: {type: string}
              role: {type: string}
              focus: {type: string}
              skill_name: {type: string}
              workdir: {type: string}
              transport:
                type: string
                enum: [local, ssh]
              scheduler: {type: string}
              hardware: {type: string}
              requires_gpu: {type: boolean}
              web_search_enabled: {type: boolean}
              depends_on:
                type: array
                items: {type: object}
              dependency_checks:
                type: array
                items: {type: object}
  locking:
    type: object
    required: [mode, backend, available]
    properties:
      mode:
        type: string
        enum: [required, auto, off]
      backend:
        type: string
      available:
        type: boolean
      note:
        type: string
  quality_gates:
    type: object
    additionalProperties: {type: boolean}
additionalProperties: true
```

## 18. `schemas/escalation.schema.yaml`

- Type: `schema`
- Purpose: Validation schema for manifests and dispatch contracts
- Locked Sections: `-`
- Validation Check: schema-validated
- Exposure Policy: source

```yaml
$schema: "https://json-schema.org/draft/2020-12/schema"
title: "Escalation Request"
type: object
required:
  - schema_version
  - request_id
  - type
  - reason
  - fields_needed
properties:
  schema_version:
    type: string
  request_id:
    type: string
  type:
    type: string
    enum: [ssh_connection, file_path, api_token, permission, custom]
  reason:
    type: string
  fields_needed:
    type: array
    items:
      type: string
  urgency:
    type: string
    enum: [blocking, normal, low]
additionalProperties: true
```

## 19. `schemas/group.schema.yaml`

- Type: `schema`
- Purpose: Validation schema for manifests and dispatch contracts
- Locked Sections: `-`
- Validation Check: schema-validated
- Exposure Policy: source

```yaml
$schema: "https://json-schema.org/draft/2020-12/schema"
title: "Group Manifest v2"
type: object
required:
  - schema_version
  - group_id
  - display_name
  - template_version
  - domain
  - purpose
  - success_criteria
  - head
  - specialists
  - required_artifacts
  - gate_profile
  - tool_profile
  - default_workdirs
  - quality_gates
properties:
  schema_version:
    type: string
    const: "2.0"
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
  purpose:
    type: string
    minLength: 8
  success_criteria:
    type: array
    minItems: 1
    items:
      type: string
      minLength: 3
  head:
    type: object
    required: [agent_id, skill_name, mission, publish_contract]
    properties:
      agent_id: {type: string}
      skill_name: {type: string}
      mission: {type: string}
      publish_contract:
        type: object
        required: [exposed_required, visibility]
        properties:
          exposed_required:
            type: array
            minItems: 1
            items: {type: string}
          visibility:
            type: string
            enum: [group-only, full]
  specialists:
    type: array
    minItems: 4
    allOf:
      - contains:
          type: object
          properties:
            role:
              const: domain-core
      - contains:
          type: object
          properties:
            role:
              const: web-research
      - contains:
          type: object
          properties:
            role:
              const: integration
      - contains:
          type: object
          properties:
            role:
              const: evidence-review
      - contains:
          type: object
          properties:
            role:
              const: repro-qa
    items:
      type: object
      required:
        - agent_id
        - skill_name
        - role
        - focus
        - contract
        - depends_on
        - required_references
        - required_outputs
      properties:
        agent_id: {type: string}
        skill_name: {type: string}
        role: {type: string}
        focus: {type: string}
        required_references:
          type: array
          minItems: 1
          items: {type: string}
        required_outputs:
          type: array
          minItems: 1
          items: {type: string}
        contract:
          type: object
          required: [inputs, outputs, output_schema]
          properties:
            inputs:
              type: array
              minItems: 1
              items: {type: string}
            outputs:
              type: array
              minItems: 1
              items: {type: string}
            output_schema:
              type: string
        depends_on:
          type: array
          items:
            type: object
            required: [agent_id, required_artifacts, validate_with, on_missing]
            properties:
              agent_id: {type: string}
              required_artifacts:
                type: array
                minItems: 1
                items: {type: string}
              validate_with:
                type: string
                pattern: "^(exists|json-parse|schema:[A-Za-z0-9._-]+)$"
              on_missing:
                type: string
                enum: [request-rerun, regenerate, block]
        execution:
          type: object
          properties:
            web_search_enabled:
              type: boolean
            remote_transport:
              type: string
              enum: [local, ssh]
            scheduler:
              type: string
            hardware:
              type: string
            requires_gpu:
              type: boolean
  required_artifacts:
    type: object
  gate_profile:
    type: object
    required: [profile_id, specialist_output_schema, checks]
    properties:
      profile_id: {type: string}
      specialist_output_schema: {type: string}
      checks:
        type: object
        additionalProperties: {type: boolean}
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
    required: [web_search_enabled]
    properties:
      web_search_enabled:
        type: boolean
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

## 20. `schemas/project.schema.yaml`

- Type: `schema`
- Purpose: Validation schema for manifests and dispatch contracts
- Locked Sections: `-`
- Validation Check: schema-validated
- Exposure Policy: source

```yaml
$schema: "https://json-schema.org/draft/2020-12/schema"
title: "Generated Project Manifest v2"
type: object
required:
  - schema_version
  - project_id
  - selected_groups
  - install_targets
  - router_skill_name
  - bundle_version
  - template_versions
  - overlays
  - visibility
properties:
  schema_version:
    type: string
    const: "2.0"
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

## 21. `schemas/tool_policy.schema.yaml`

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

## 22. `catalog/groups/data-curation.yaml`

- Type: `catalog`
- Purpose: Reusable source-of-truth group/profile/registry metadata
- Locked Sections: `-`
- Validation Check: schema-validated
- Exposure Policy: source

```yaml
group_id: data-curation
display_name: Data Curation Group
template_version: 3.0.0
domain: data-pipelines
head:
  agent_id: data-curation-head
  skill_name: grp-data-curation-head
  mission: Ensure trustworthy, traceable research data pipelines and metadata quality.
  publish_contract:
    exposed_required:
    - summary.md
    - handoff.json
    - INTEGRATION_NOTES.md
    visibility: group-only
specialists:
- agent_id: data-ingest-specialist
  skill_name: grp-data-curation-ingest
  focus: Data ingest strategy, provenance capture, and schema conformance
  required_references:
  - references/data-ingest-core.md
  required_outputs:
  - ingest_report.md
  - claims_with_citations.md
  - work.md
  - handoff.json
  role: domain-core
  contract:
    inputs:
    - objective.md
    - group-context.json
    outputs:
    - work.md
    - handoff.json
    output_schema: specialist-handoff-v2
  depends_on: []
  execution:
    remote_transport: local
    scheduler: local
    hardware: cpu
    requires_gpu: false
- agent_id: metadata-specialist
  skill_name: grp-data-curation-metadata
  focus: Metadata normalization, ontologies, and traceability annotations
  depends_on:
  - agent_id: data-ingest-specialist
    required_artifacts:
    - internal/data-ingest-specialist/handoff.json
    validate_with: json-parse
    on_missing: request-rerun
  required_references:
  - references/metadata-core.md
  required_outputs:
  - metadata_dictionary.md
  - claims_with_citations.md
  - work.md
  - handoff.json
  role: domain-core
  contract:
    inputs:
    - objective.md
    - group-context.json
    outputs:
    - work.md
    - handoff.json
    output_schema: specialist-handoff-v2
  execution:
    remote_transport: local
    scheduler: local
    hardware: cpu
    requires_gpu: false
- agent_id: data-quality-specialist
  skill_name: grp-data-curation-quality
  focus: Data quality checks, anomaly detection heuristics, and acceptance thresholds
  depends_on:
  - agent_id: metadata-specialist
    required_artifacts:
    - internal/metadata-specialist/handoff.json
    validate_with: json-parse
    on_missing: request-rerun
  - agent_id: data-ingest-specialist
    required_artifacts:
    - internal/data-ingest-specialist/handoff.json
    validate_with: json-parse
    on_missing: request-rerun
  required_references:
  - references/data-quality-core.md
  required_outputs:
  - quality_report.md
  - claims_with_citations.md
  - work.md
  - handoff.json
  role: repro-qa
  contract:
    inputs:
    - objective.md
    - group-context.json
    outputs:
    - work.md
    - handoff.json
    output_schema: specialist-handoff-v2
  execution:
    remote_transport: local
    scheduler: local
    hardware: cpu
    requires_gpu: false
- agent_id: integration-specialist
  skill_name: grp-data-curation-integration
  role: integration
  focus: Cross-artifact integration and consumability checks for Data Curation Group
  required_references:
  - references/integration-core.md
  required_outputs:
  - work.md
  - handoff.json
  contract:
    inputs:
    - objective.md
    - group-context.json
    outputs:
    - work.md
    - handoff.json
    output_schema: specialist-handoff-v2
  depends_on:
  - agent_id: data-ingest-specialist
    required_artifacts:
    - internal/data-ingest-specialist/handoff.json
    validate_with: json-parse
    on_missing: request-rerun
  execution:
    remote_transport: local
    scheduler: local
    hardware: cpu
    requires_gpu: false
- agent_id: evidence-review-specialist
  skill_name: grp-data-curation-evidence-review
  role: evidence-review
  focus: Claim-level evidence review and citation sufficiency for Data Curation Group
  required_references:
  - references/evidence-review-core.md
  required_outputs:
  - work.md
  - handoff.json
  contract:
    inputs:
    - objective.md
    - group-context.json
    outputs:
    - work.md
    - handoff.json
    output_schema: specialist-handoff-v2
  depends_on:
  - agent_id: data-ingest-specialist
    required_artifacts:
    - internal/data-ingest-specialist/handoff.json
    validate_with: json-parse
    on_missing: request-rerun
  execution:
    remote_transport: local
    scheduler: local
    hardware: cpu
    requires_gpu: false
- agent_id: web-research-specialist
  skill_name: grp-data-curation-web-research
  role: web-research
  focus: Gather web-published references and extract citation-ready evidence.
  required_references:
  - references/web-research-core.md
  required_outputs:
  - work.md
  - handoff.json
  contract:
    inputs:
    - objective.md
    - group-context.json
    outputs:
    - work.md
    - handoff.json
    output_schema: specialist-handoff-v2
  depends_on: []
  execution:
    remote_transport: local
    scheduler: local
    hardware: cpu
    requires_gpu: false
tool_profile: data-default
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
schema_version: '3.0'
purpose: Coordinate expert specialists for Data Curation Group objectives.
success_criteria:
- All required artifacts produced
- Gate profile satisfied
- Exposed handoff consumable
required_artifacts:
  objective_types:
    default:
      specialist_internal:
      - internal/<agent-id>/work.md
      - internal/<agent-id>/handoff.json
      head_exposed:
      - exposed/summary.md
      - exposed/handoff.json
      - exposed/INTEGRATION_NOTES.md
gate_profile:
  profile_id: standard-evidence-v2
  specialist_output_schema: specialist-handoff-v2
  checks:
    web_citations_required: true
    repro_command_required: true
    consistency_required: true
    scope_enforced: true
interaction:
  mode: interactive-separated
  linked_groups: []
execution_defaults:
  web_search_enabled: true
  remote_transport: local
  schedulers:
  - local
  hardware:
  - cpu
```

## 23. `catalog/groups/design-communication.yaml`

- Type: `catalog`
- Purpose: Reusable source-of-truth group/profile/registry metadata
- Locked Sections: `-`
- Validation Check: schema-validated
- Exposure Policy: source

```yaml
group_id: design-communication
display_name: Design Communication Group
template_version: 3.0.0
domain: design-and-communication
head:
  agent_id: design-communication-head
  skill_name: grp-design-communication-head
  mission: Shape clear narratives, communication assets, and stakeholder-facing deliverables across service workflows.
  publish_contract:
    exposed_required:
    - summary.md
    - handoff.json
    - INTEGRATION_NOTES.md
    visibility: group-only
specialists:
- agent_id: communication-strategy-specialist
  skill_name: grp-design-communication-strategy
  focus: Communication strategy, stakeholder alignment, and message intent mapping
  required_references:
  - references/communication-strategy-core.md
  required_outputs:
  - communication_strategy.md
  - claims_with_citations.md
  - work.md
  - handoff.json
  role: domain-core
  contract:
    inputs:
    - objective.md
    - group-context.json
    outputs:
    - work.md
    - handoff.json
    output_schema: specialist-handoff-v2
  depends_on: []
  execution:
    remote_transport: local
    scheduler: local
    hardware: cpu
    requires_gpu: false
- agent_id: narrative-design-specialist
  skill_name: grp-design-communication-narrative
  focus: Narrative flow, artifact framing, and audience-oriented readability
  required_references:
  - references/narrative-design-core.md
  required_outputs:
  - narrative_outline.md
  - claims_with_citations.md
  - work.md
  - handoff.json
  role: domain-core
  contract:
    inputs:
    - objective.md
    - group-context.json
    outputs:
    - work.md
    - handoff.json
    output_schema: specialist-handoff-v2
  depends_on:
  - agent_id: communication-strategy-specialist
    required_artifacts:
    - internal/communication-strategy-specialist/handoff.json
    validate_with: json-parse
    on_missing: request-rerun
  execution:
    remote_transport: local
    scheduler: local
    hardware: cpu
    requires_gpu: false
- agent_id: integration-specialist
  skill_name: grp-design-communication-integration
  role: integration
  focus: Cross-artifact integration and consumability checks for Design Communication Group
  required_references:
  - references/integration-core.md
  required_outputs:
  - work.md
  - handoff.json
  contract:
    inputs:
    - objective.md
    - group-context.json
    outputs:
    - work.md
    - handoff.json
    output_schema: specialist-handoff-v2
  depends_on:
  - agent_id: narrative-design-specialist
    required_artifacts:
    - internal/narrative-design-specialist/handoff.json
    validate_with: json-parse
    on_missing: request-rerun
  execution:
    remote_transport: local
    scheduler: local
    hardware: cpu
    requires_gpu: false
- agent_id: evidence-review-specialist
  skill_name: grp-design-communication-evidence-review
  role: evidence-review
  focus: Claim-level evidence review and citation sufficiency for Design Communication Group
  required_references:
  - references/evidence-review-core.md
  required_outputs:
  - work.md
  - handoff.json
  contract:
    inputs:
    - objective.md
    - group-context.json
    outputs:
    - work.md
    - handoff.json
    output_schema: specialist-handoff-v2
  depends_on:
  - agent_id: communication-strategy-specialist
    required_artifacts:
    - internal/communication-strategy-specialist/handoff.json
    validate_with: json-parse
    on_missing: request-rerun
  execution:
    remote_transport: local
    scheduler: local
    hardware: cpu
    requires_gpu: false
- agent_id: repro-qa-specialist
  skill_name: grp-design-communication-repro-qa
  role: repro-qa
  focus: Reproducibility and quality assurance checks for Design Communication Group
  required_references:
  - references/repro-qa-core.md
  required_outputs:
  - work.md
  - handoff.json
  contract:
    inputs:
    - objective.md
    - group-context.json
    outputs:
    - work.md
    - handoff.json
    output_schema: specialist-handoff-v2
  depends_on:
  - agent_id: communication-strategy-specialist
    required_artifacts:
    - internal/communication-strategy-specialist/handoff.json
    validate_with: json-parse
    on_missing: request-rerun
  execution:
    remote_transport: local
    scheduler: local
    hardware: cpu
    requires_gpu: false
- agent_id: web-research-specialist
  skill_name: grp-design-communication-web-research
  role: web-research
  focus: Gather web-published references and extract citation-ready evidence.
  required_references:
  - references/web-research-core.md
  required_outputs:
  - work.md
  - handoff.json
  contract:
    inputs:
    - objective.md
    - group-context.json
    outputs:
    - work.md
    - handoff.json
    output_schema: specialist-handoff-v2
  depends_on: []
  execution:
    remote_transport: local
    scheduler: local
    hardware: cpu
    requires_gpu: false
tool_profile: design-default
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
schema_version: '3.0'
purpose: Coordinate specialist design and communication workflows for service outcomes.
success_criteria:
- All required artifacts produced
- Gate profile satisfied
- Exposed handoff consumable
required_artifacts:
  objective_types:
    default:
      specialist_internal:
      - internal/<agent-id>/work.md
      - internal/<agent-id>/handoff.json
      head_exposed:
      - exposed/summary.md
      - exposed/handoff.json
      - exposed/INTEGRATION_NOTES.md
gate_profile:
  profile_id: standard-evidence-v2
  specialist_output_schema: specialist-handoff-v2
  checks:
    web_citations_required: true
    repro_command_required: true
    consistency_required: true
    scope_enforced: true
interaction:
  mode: interactive-separated
  linked_groups: []
execution_defaults:
  web_search_enabled: true
  remote_transport: local
  schedulers:
  - local
  hardware:
  - cpu
```

## 24. `catalog/groups/developer.yaml`

- Type: `catalog`
- Purpose: Reusable source-of-truth group/profile/registry metadata
- Locked Sections: `-`
- Validation Check: schema-validated
- Exposure Policy: source

```yaml
group_id: developer
display_name: Developer Group
template_version: 3.0.0
domain: software-and-infra
head:
  agent_id: developer-head
  skill_name: grp-developer-head
  mission: Deliver robust implementation, debugging, and automation support for research
    projects.
  publish_contract:
    exposed_required:
    - summary.md
    - handoff.json
    - INTEGRATION_NOTES.md
    visibility: group-only
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
  - work.md
  - handoff.json
  role: domain-core
  contract:
    inputs:
    - objective.md
    - group-context.json
    outputs:
    - work.md
    - handoff.json
    output_schema: specialist-handoff-v2
  depends_on: []
  execution:
    remote_transport: local
    scheduler: local
    hardware: cpu
    requires_gpu: false
- agent_id: shell-expert
  skill_name: grp-developer-shell
  focus: Shell automation, reproducible scripts, CLI hardening
  required_references:
  - references/shell-engineering-core.md
  required_outputs:
  - automation_scripts.md
  - claims_with_citations.md
  - work.md
  - handoff.json
  role: repro-qa
  contract:
    inputs:
    - objective.md
    - group-context.json
    outputs:
    - work.md
    - handoff.json
    output_schema: specialist-handoff-v2
  depends_on:
  - agent_id: python-expert
    required_artifacts:
    - internal/python-expert/handoff.json
    validate_with: json-parse
    on_missing: request-rerun
  execution:
    remote_transport: local
    scheduler: local
    hardware: cpu
    requires_gpu: false
- agent_id: ssh-remote-ops-expert
  skill_name: grp-developer-ssh
  focus: Remote operations, secure SSH workflows, transfer and execution protocols
  required_references:
  - references/ssh-ops-core.md
  required_outputs:
  - remote_ops_plan.md
  - claims_with_citations.md
  - work.md
  - handoff.json
  role: domain-core
  contract:
    inputs:
    - objective.md
    - group-context.json
    outputs:
    - work.md
    - handoff.json
    output_schema: specialist-handoff-v2
  depends_on: []
  execution:
    remote_transport: local
    scheduler: local
    hardware: cpu
    requires_gpu: false
- agent_id: integration-specialist
  skill_name: grp-developer-integration
  role: integration
  focus: Cross-artifact integration and consumability checks for Developer Group
  required_references:
  - references/integration-core.md
  required_outputs:
  - work.md
  - handoff.json
  contract:
    inputs:
    - objective.md
    - group-context.json
    outputs:
    - work.md
    - handoff.json
    output_schema: specialist-handoff-v2
  depends_on:
  - agent_id: python-expert
    required_artifacts:
    - internal/python-expert/handoff.json
    validate_with: json-parse
    on_missing: request-rerun
  execution:
    remote_transport: local
    scheduler: local
    hardware: cpu
    requires_gpu: false
- agent_id: evidence-review-specialist
  skill_name: grp-developer-evidence-review
  role: evidence-review
  focus: Claim-level evidence review and citation sufficiency for Developer Group
  required_references:
  - references/evidence-review-core.md
  required_outputs:
  - work.md
  - handoff.json
  contract:
    inputs:
    - objective.md
    - group-context.json
    outputs:
    - work.md
    - handoff.json
    output_schema: specialist-handoff-v2
  depends_on:
  - agent_id: python-expert
    required_artifacts:
    - internal/python-expert/handoff.json
    validate_with: json-parse
    on_missing: request-rerun
  execution:
    remote_transport: local
    scheduler: local
    hardware: cpu
    requires_gpu: false
- agent_id: web-research-specialist
  skill_name: grp-developer-web-research
  role: web-research
  focus: Gather web-published references and extract citation-ready evidence.
  required_references:
  - references/web-research-core.md
  required_outputs:
  - work.md
  - handoff.json
  contract:
    inputs:
    - objective.md
    - group-context.json
    outputs:
    - work.md
    - handoff.json
    output_schema: specialist-handoff-v2
  depends_on: []
  execution:
    remote_transport: local
    scheduler: local
    hardware: cpu
    requires_gpu: false
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
schema_version: '3.0'
purpose: Coordinate expert specialists for Developer Group objectives.
success_criteria:
- All required artifacts produced
- Gate profile satisfied
- Exposed handoff consumable
required_artifacts:
  objective_types:
    default:
      specialist_internal:
      - internal/<agent-id>/work.md
      - internal/<agent-id>/handoff.json
      head_exposed:
      - exposed/summary.md
      - exposed/handoff.json
      - exposed/INTEGRATION_NOTES.md
    material-focused:
      specialist_internal:
      - internal/<agent-id>/work.md
      - internal/<agent-id>/handoff.json
      head_exposed:
      - exposed/summary.md
      - exposed/handoff.json
      - exposed/INTEGRATION_NOTES.md
      required_outputs:
      - outputs/python/material_pipeline/__init__.py
      - outputs/python/material_pipeline/score.py
      - outputs/python/material_pipeline/cli.py
      - outputs/reports/material-ranking-rationale.md
gate_profile:
  profile_id: standard-evidence-v2
  specialist_output_schema: specialist-handoff-v2
  checks:
    web_citations_required: true
    repro_command_required: true
    consistency_required: true
    scope_enforced: true
    material_data_contract_required: true
    material_package_required: true
interaction:
  mode: interactive-separated
  linked_groups: []
execution_defaults:
  web_search_enabled: true
  remote_transport: local
  schedulers:
  - local
  hardware:
  - cpu
```

## 25. `catalog/groups/integration-delivery.yaml`

- Type: `catalog`
- Purpose: Reusable source-of-truth group/profile/registry metadata
- Locked Sections: `-`
- Validation Check: schema-validated
- Exposure Policy: source

```yaml
group_id: integration-delivery
display_name: Integration Delivery Group
template_version: 3.0.0
domain: integration-and-delivery
head:
  agent_id: integration-delivery-head
  skill_name: grp-integration-delivery-head
  mission: Coordinate cross-team integration, release readiness, and delivery quality for professional services workflows.
  publish_contract:
    exposed_required:
    - summary.md
    - handoff.json
    - INTEGRATION_NOTES.md
    visibility: group-only
specialists:
- agent_id: delivery-architect
  skill_name: grp-integration-delivery-architect
  focus: Delivery architecture, staged rollout plans, and dependency-aware release strategy
  required_references:
  - references/delivery-architecture-core.md
  required_outputs:
  - rollout_plan.md
  - claims_with_citations.md
  - work.md
  - handoff.json
  role: domain-core
  contract:
    inputs:
    - objective.md
    - group-context.json
    outputs:
    - work.md
    - handoff.json
    output_schema: specialist-handoff-v2
  depends_on: []
  execution:
    remote_transport: local
    scheduler: local
    hardware: cpu
    requires_gpu: false
- agent_id: dependency-mapping-specialist
  skill_name: grp-integration-delivery-dependencies
  focus: Dependency graph mapping, integration sequencing, and handoff risk detection
  required_references:
  - references/dependency-mapping-core.md
  required_outputs:
  - dependency_matrix.md
  - claims_with_citations.md
  - work.md
  - handoff.json
  role: domain-core
  contract:
    inputs:
    - objective.md
    - group-context.json
    outputs:
    - work.md
    - handoff.json
    output_schema: specialist-handoff-v2
  depends_on:
  - agent_id: delivery-architect
    required_artifacts:
    - internal/delivery-architect/handoff.json
    validate_with: json-parse
    on_missing: request-rerun
  execution:
    remote_transport: local
    scheduler: local
    hardware: cpu
    requires_gpu: false
- agent_id: integration-specialist
  skill_name: grp-integration-delivery-integration
  role: integration
  focus: Cross-artifact integration and consumability checks for Integration Delivery Group
  required_references:
  - references/integration-core.md
  required_outputs:
  - work.md
  - handoff.json
  contract:
    inputs:
    - objective.md
    - group-context.json
    outputs:
    - work.md
    - handoff.json
    output_schema: specialist-handoff-v2
  depends_on:
  - agent_id: dependency-mapping-specialist
    required_artifacts:
    - internal/dependency-mapping-specialist/handoff.json
    validate_with: json-parse
    on_missing: request-rerun
  execution:
    remote_transport: local
    scheduler: local
    hardware: cpu
    requires_gpu: false
- agent_id: evidence-review-specialist
  skill_name: grp-integration-delivery-evidence-review
  role: evidence-review
  focus: Claim-level evidence review and citation sufficiency for Integration Delivery Group
  required_references:
  - references/evidence-review-core.md
  required_outputs:
  - work.md
  - handoff.json
  contract:
    inputs:
    - objective.md
    - group-context.json
    outputs:
    - work.md
    - handoff.json
    output_schema: specialist-handoff-v2
  depends_on:
  - agent_id: delivery-architect
    required_artifacts:
    - internal/delivery-architect/handoff.json
    validate_with: json-parse
    on_missing: request-rerun
  execution:
    remote_transport: local
    scheduler: local
    hardware: cpu
    requires_gpu: false
- agent_id: repro-qa-specialist
  skill_name: grp-integration-delivery-repro-qa
  role: repro-qa
  focus: Reproducibility and quality assurance checks for Integration Delivery Group
  required_references:
  - references/repro-qa-core.md
  required_outputs:
  - work.md
  - handoff.json
  contract:
    inputs:
    - objective.md
    - group-context.json
    outputs:
    - work.md
    - handoff.json
    output_schema: specialist-handoff-v2
  depends_on:
  - agent_id: delivery-architect
    required_artifacts:
    - internal/delivery-architect/handoff.json
    validate_with: json-parse
    on_missing: request-rerun
  execution:
    remote_transport: local
    scheduler: local
    hardware: cpu
    requires_gpu: false
- agent_id: web-research-specialist
  skill_name: grp-integration-delivery-web-research
  role: web-research
  focus: Gather web-published references and extract citation-ready evidence.
  required_references:
  - references/web-research-core.md
  required_outputs:
  - work.md
  - handoff.json
  contract:
    inputs:
    - objective.md
    - group-context.json
    outputs:
    - work.md
    - handoff.json
    output_schema: specialist-handoff-v2
  depends_on: []
  execution:
    remote_transport: local
    scheduler: local
    hardware: cpu
    requires_gpu: false
tool_profile: delivery-default
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
schema_version: '3.0'
purpose: Coordinate specialist integration and delivery workflows for cross-team objectives.
success_criteria:
- All required artifacts produced
- Gate profile satisfied
- Exposed handoff consumable
required_artifacts:
  objective_types:
    default:
      specialist_internal:
      - internal/<agent-id>/work.md
      - internal/<agent-id>/handoff.json
      head_exposed:
      - exposed/summary.md
      - exposed/handoff.json
      - exposed/INTEGRATION_NOTES.md
gate_profile:
  profile_id: standard-evidence-v2
  specialist_output_schema: specialist-handoff-v2
  checks:
    web_citations_required: true
    repro_command_required: true
    consistency_required: true
    scope_enforced: true
interaction:
  mode: interactive-separated
  linked_groups: []
execution_defaults:
  web_search_enabled: true
  remote_transport: local
  schedulers:
  - local
  hardware:
  - cpu
```

## 26. `catalog/groups/literature-intelligence.yaml`

- Type: `catalog`
- Purpose: Reusable source-of-truth group/profile/registry metadata
- Locked Sections: `-`
- Validation Check: schema-validated
- Exposure Policy: source

```yaml
group_id: literature-intelligence
display_name: Literature Intelligence Group
template_version: 3.0.0
domain: literature-analysis
head:
  agent_id: literature-intelligence-head
  skill_name: grp-literature-intelligence-head
  mission: Extract, compare, and evidence-grade literature claims for project decision
    support.
  publish_contract:
    exposed_required:
    - summary.md
    - handoff.json
    - INTEGRATION_NOTES.md
    visibility: group-only
specialists:
- agent_id: retrieval-specialist
  skill_name: grp-literature-intelligence-retrieval
  focus: Paper retrieval strategy, inclusion criteria, and source tracking
  required_references:
  - references/retrieval-core.md
  required_outputs:
  - source_inventory.md
  - claims_with_citations.md
  - work.md
  - handoff.json
  role: domain-core
  contract:
    inputs:
    - objective.md
    - group-context.json
    outputs:
    - work.md
    - handoff.json
    output_schema: specialist-handoff-v2
  depends_on: []
  execution:
    remote_transport: local
    scheduler: local
    hardware: cpu
    requires_gpu: false
- agent_id: evidence-grading-specialist
  skill_name: grp-literature-intelligence-evidence
  focus: Evidence grading, study quality interpretation, and confidence assignment
  depends_on:
  - agent_id: retrieval-specialist
    required_artifacts:
    - internal/retrieval-specialist/handoff.json
    validate_with: json-parse
    on_missing: request-rerun
  required_references:
  - references/evidence-grading-core.md
  required_outputs:
  - evidence_matrix.md
  - claims_with_citations.md
  - work.md
  - handoff.json
  role: evidence-review
  contract:
    inputs:
    - objective.md
    - group-context.json
    outputs:
    - work.md
    - handoff.json
    output_schema: specialist-handoff-v2
  execution:
    remote_transport: local
    scheduler: local
    hardware: cpu
    requires_gpu: false
- agent_id: gap-analysis-specialist
  skill_name: grp-literature-intelligence-gap
  focus: Research gap mapping and risk-aware recommendation framing
  depends_on:
  - agent_id: evidence-grading-specialist
    required_artifacts:
    - internal/evidence-grading-specialist/handoff.json
    validate_with: json-parse
    on_missing: request-rerun
  - agent_id: retrieval-specialist
    required_artifacts:
    - internal/retrieval-specialist/handoff.json
    validate_with: json-parse
    on_missing: request-rerun
  required_references:
  - references/gap-analysis-core.md
  required_outputs:
  - gap_map.md
  - claims_with_citations.md
  - work.md
  - handoff.json
  role: repro-qa
  contract:
    inputs:
    - objective.md
    - group-context.json
    outputs:
    - work.md
    - handoff.json
    output_schema: specialist-handoff-v2
  execution:
    remote_transport: local
    scheduler: local
    hardware: cpu
    requires_gpu: false
- agent_id: integration-specialist
  skill_name: grp-literature-intelligence-integration
  role: integration
  focus: Cross-artifact integration and consumability checks for Literature Intelligence
    Group
  required_references:
  - references/integration-core.md
  required_outputs:
  - work.md
  - handoff.json
  contract:
    inputs:
    - objective.md
    - group-context.json
    outputs:
    - work.md
    - handoff.json
    output_schema: specialist-handoff-v2
  depends_on:
  - agent_id: retrieval-specialist
    required_artifacts:
    - internal/retrieval-specialist/handoff.json
    validate_with: json-parse
    on_missing: request-rerun
  execution:
    remote_transport: local
    scheduler: local
    hardware: cpu
    requires_gpu: false
- agent_id: web-research-specialist
  skill_name: grp-literature-intelligence-web-research
  role: web-research
  focus: Gather web-published references and extract citation-ready evidence.
  required_references:
  - references/web-research-core.md
  required_outputs:
  - work.md
  - handoff.json
  contract:
    inputs:
    - objective.md
    - group-context.json
    outputs:
    - work.md
    - handoff.json
    output_schema: specialist-handoff-v2
  depends_on: []
  execution:
    remote_transport: local
    scheduler: local
    hardware: cpu
    requires_gpu: false
tool_profile: literature-default
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
schema_version: '3.0'
purpose: Coordinate expert specialists for Literature Intelligence Group objectives.
success_criteria:
- All required artifacts produced
- Gate profile satisfied
- Exposed handoff consumable
required_artifacts:
  objective_types:
    default:
      specialist_internal:
      - internal/<agent-id>/work.md
      - internal/<agent-id>/handoff.json
      head_exposed:
      - exposed/summary.md
      - exposed/handoff.json
      - exposed/INTEGRATION_NOTES.md
gate_profile:
  profile_id: standard-evidence-v2
  specialist_output_schema: specialist-handoff-v2
  checks:
    web_citations_required: true
    repro_command_required: true
    consistency_required: true
    scope_enforced: true
interaction:
  mode: interactive-separated
  linked_groups: []
execution_defaults:
  web_search_enabled: true
  remote_transport: local
  schedulers:
  - local
  hardware:
  - cpu
```

## 27. `catalog/groups/quality-assurance.yaml`

- Type: `catalog`
- Purpose: Reusable source-of-truth group/profile/registry metadata
- Locked Sections: `-`
- Validation Check: schema-validated
- Exposure Policy: source

```yaml
group_id: quality-assurance
display_name: Quality Assurance Group
template_version: 3.0.0
domain: verification-and-risk
head:
  agent_id: quality-assurance-head
  skill_name: grp-quality-assurance-head
  mission: Audit technical outputs for reproducibility, consistency, and decision-risk
    control.
  publish_contract:
    exposed_required:
    - summary.md
    - handoff.json
    - INTEGRATION_NOTES.md
    visibility: group-only
specialists:
- agent_id: reproducibility-auditor
  skill_name: grp-quality-assurance-repro
  focus: Reproducibility checks, parameter traceability, and artifact completeness
  required_references:
  - references/reproducibility-core.md
  required_outputs:
  - repro_audit.md
  - claims_with_citations.md
  - work.md
  - handoff.json
  role: repro-qa
  contract:
    inputs:
    - objective.md
    - group-context.json
    outputs:
    - work.md
    - handoff.json
    output_schema: specialist-handoff-v2
  depends_on:
  - agent_id: consistency-auditor
    required_artifacts:
    - internal/consistency-auditor/handoff.json
    validate_with: json-parse
    on_missing: request-rerun
  execution:
    remote_transport: local
    scheduler: local
    hardware: cpu
    requires_gpu: false
- agent_id: consistency-auditor
  skill_name: grp-quality-assurance-consistency
  focus: Cross-document consistency checks and contradiction detection
  required_references:
  - references/consistency-core.md
  required_outputs:
  - consistency_audit.md
  - claims_with_citations.md
  - work.md
  - handoff.json
  role: domain-core
  contract:
    inputs:
    - objective.md
    - group-context.json
    outputs:
    - work.md
    - handoff.json
    output_schema: specialist-handoff-v2
  depends_on: []
  execution:
    remote_transport: local
    scheduler: local
    hardware: cpu
    requires_gpu: false
- agent_id: risk-auditor
  skill_name: grp-quality-assurance-risk
  focus: Risk classification, severity tagging, and mitigation recommendation framing
  depends_on:
  - agent_id: consistency-auditor
    required_artifacts:
    - internal/consistency-auditor/handoff.json
    validate_with: json-parse
    on_missing: request-rerun
  required_references:
  - references/risk-core.md
  required_outputs:
  - risk_register.md
  - claims_with_citations.md
  - work.md
  - handoff.json
  role: repro-qa
  contract:
    inputs:
    - objective.md
    - group-context.json
    outputs:
    - work.md
    - handoff.json
    output_schema: specialist-handoff-v2
  execution:
    remote_transport: local
    scheduler: local
    hardware: cpu
    requires_gpu: false
- agent_id: integration-specialist
  skill_name: grp-quality-assurance-integration
  role: integration
  focus: Cross-artifact integration and consumability checks for Quality Assurance
    Group
  required_references:
  - references/integration-core.md
  required_outputs:
  - work.md
  - handoff.json
  contract:
    inputs:
    - objective.md
    - group-context.json
    outputs:
    - work.md
    - handoff.json
    output_schema: specialist-handoff-v2
  depends_on:
  - agent_id: consistency-auditor
    required_artifacts:
    - internal/consistency-auditor/handoff.json
    validate_with: json-parse
    on_missing: request-rerun
  execution:
    remote_transport: local
    scheduler: local
    hardware: cpu
    requires_gpu: false
- agent_id: evidence-review-specialist
  skill_name: grp-quality-assurance-evidence-review
  role: evidence-review
  focus: Claim-level evidence review and citation sufficiency for Quality Assurance
    Group
  required_references:
  - references/evidence-review-core.md
  required_outputs:
  - work.md
  - handoff.json
  contract:
    inputs:
    - objective.md
    - group-context.json
    outputs:
    - work.md
    - handoff.json
    output_schema: specialist-handoff-v2
  depends_on:
  - agent_id: consistency-auditor
    required_artifacts:
    - internal/consistency-auditor/handoff.json
    validate_with: json-parse
    on_missing: request-rerun
  execution:
    remote_transport: local
    scheduler: local
    hardware: cpu
    requires_gpu: false
- agent_id: web-research-specialist
  skill_name: grp-quality-assurance-web-research
  role: web-research
  focus: Gather web-published references and extract citation-ready evidence.
  required_references:
  - references/web-research-core.md
  required_outputs:
  - work.md
  - handoff.json
  contract:
    inputs:
    - objective.md
    - group-context.json
    outputs:
    - work.md
    - handoff.json
    output_schema: specialist-handoff-v2
  depends_on: []
  execution:
    remote_transport: local
    scheduler: local
    hardware: cpu
    requires_gpu: false
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
schema_version: '3.0'
purpose: Coordinate expert specialists for Quality Assurance Group objectives.
success_criteria:
- All required artifacts produced
- Gate profile satisfied
- Exposed handoff consumable
required_artifacts:
  objective_types:
    default:
      specialist_internal:
      - internal/<agent-id>/work.md
      - internal/<agent-id>/handoff.json
      head_exposed:
      - exposed/summary.md
      - exposed/handoff.json
      - exposed/INTEGRATION_NOTES.md
gate_profile:
  profile_id: standard-evidence-v2
  specialist_output_schema: specialist-handoff-v2
  checks:
    web_citations_required: true
    repro_command_required: true
    consistency_required: true
    scope_enforced: true
interaction:
  mode: interactive-separated
  linked_groups: []
execution_defaults:
  web_search_enabled: true
  remote_transport: local
  schedulers:
  - local
  hardware:
  - cpu
```

## 28. `catalog/profiles/delivery-core.yaml`

- Type: `catalog`
- Purpose: Reusable source-of-truth group/profile/registry metadata
- Locked Sections: `-`
- Validation Check: schema-validated
- Exposure Policy: source

```yaml
profile_id: "delivery-core"
display_name: "Delivery Core"
groups:
  - "developer"
  - "integration-delivery"
  - "quality-assurance"
  - "data-curation"
```

## 29. `catalog/profiles/professional-services-core.yaml`

- Type: `catalog`
- Purpose: Reusable source-of-truth group/profile/registry metadata
- Locked Sections: `-`
- Validation Check: schema-validated
- Exposure Policy: source

```yaml
profile_id: "professional-services-core"
display_name: "Professional Services Core"
groups:
  - "developer"
  - "quality-assurance"
  - "literature-intelligence"
  - "data-curation"
  - "integration-delivery"
  - "design-communication"
```

## 30. `catalog/profiles/rapid-debug.yaml`

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

## 31. `catalog/project-registry.yaml`

- Type: `catalog`
- Purpose: Reusable source-of-truth group/profile/registry metadata
- Locked Sections: `-`
- Validation Check: schema-validated
- Exposure Policy: source

```yaml
router_skill_name: research-router
projects:
  proj-test-alpha:
    manifest_path: generated/projects/proj-test-alpha/manifest.yaml
    selected_groups:
    - integration-delivery
    updated_at: '2026-03-02T13:55:14Z'
  proj-test-hpc:
    manifest_path: generated/projects/proj-test-hpc/manifest.yaml
    selected_groups:
    - integration-delivery
    updated_at: '2026-03-02T13:55:14Z'
```

## 32. `generated/projects/proj-test-alpha/agent-groups/integration-delivery/AGENTS.md`

- Type: `agents`
- Purpose: Group operating contract and policy
- Locked Sections: `safety_policy, citation_gate, routing_audit, exposure_policy`
- Validation Check: content-reviewed
- Exposure Policy: source

```md
# Integration Delivery Group - proj-test-alpha

## Mission
Coordinate cross-team integration, release readiness, and delivery quality for professional services workflows.

## Group Identity
- `group_id`: `integration-delivery`
- `template_version`: `3.0.0`
- `tool_profile`: `delivery-default`
- `head_agent`: `integration-delivery-head`
- `head_skill`: `integration-delivery-integration-delivery-head--proj-test-alpha`

## Specialist Roster
- `delivery-architect`: Delivery architecture, staged rollout plans, and dependency-aware release strategy (skill: `integration-delivery-delivery-architect--proj-test-alpha`)
- `dependency-mapping-specialist`: Dependency graph mapping, integration sequencing, and handoff risk detection (skill: `integration-delivery-dependency-mapping-specialist--pro-acbf437d`)
- `integration-specialist`: Cross-artifact integration and consumability checks for Integration Delivery Group (skill: `integration-delivery-integration-specialist--proj-test-alpha`)
- `evidence-review-specialist`: Claim-level evidence review and citation sufficiency for Integration Delivery Group (skill: `integration-delivery-evidence-review-specialist--proj-test-alpha`)
- `repro-qa-specialist`: Reproducibility and quality assurance checks for Integration Delivery Group (skill: `integration-delivery-repro-qa-specialist--proj-test-alpha`)
- `web-research-specialist`: Gather web-published references and extract citation-ready evidence. (skill: `integration-delivery-web-research-specialist--proj-test-alpha`)

## Work Directories
- `generated/projects/proj-test-alpha/work/integration-delivery/delivery-architect`
- `generated/projects/proj-test-alpha/work/integration-delivery/dependency-mapping-specialist`
- `generated/projects/proj-test-alpha/work/integration-delivery/integration-specialist`
- `generated/projects/proj-test-alpha/work/integration-delivery/evidence-review-specialist`
- `generated/projects/proj-test-alpha/work/integration-delivery/repro-qa-specialist`
- `generated/projects/proj-test-alpha/work/integration-delivery/web-research-specialist`

## Artifact Partition
- Internal specialist artifacts: `agent-groups/integration-delivery/internal/<specialist>/...`
- Exposed group artifacts: `agent-groups/integration-delivery/exposed/...`
- Specialist runtime instructions: `agent-groups/integration-delivery/internal/<specialist>/AGENTS.md`
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
- `rollout_plan.md` from `delivery-architect`
- `claims_with_citations.md` from `delivery-architect`
- `work.md` from `delivery-architect`
- `handoff.json` from `delivery-architect`
- `dependency_matrix.md` from `dependency-mapping-specialist`
- `claims_with_citations.md` from `dependency-mapping-specialist`
- `work.md` from `dependency-mapping-specialist`
- `handoff.json` from `dependency-mapping-specialist`
- `work.md` from `integration-specialist`
- `handoff.json` from `integration-specialist`
- `work.md` from `evidence-review-specialist`
- `handoff.json` from `evidence-review-specialist`
- `work.md` from `repro-qa-specialist`
- `handoff.json` from `repro-qa-specialist`
- `work.md` from `web-research-specialist`
- `handoff.json` from `web-research-specialist`

## Quality Gates
- `citation_required`: `True`
- `unresolved_claims_block`: `True`
- `peer_check_required`: `True`
- `consistency_required`: `True`
- `scope_required`: `True`
- `reproducibility_required`: `True`
```

## 33. `generated/projects/proj-test-alpha/agent-groups/integration-delivery/group.yaml`

- Type: `manifest`
- Purpose: Project or group manifest instance
- Locked Sections: `-`
- Validation Check: schema-validated
- Exposure Policy: source

```yaml
group_id: integration-delivery
display_name: Integration Delivery Group
template_version: 3.0.0
domain: integration-and-delivery
head:
  agent_id: integration-delivery-head
  skill_name: grp-integration-delivery-head
  mission: Coordinate cross-team integration, release readiness, and delivery quality
    for professional services workflows.
  publish_contract:
    exposed_required:
    - summary.md
    - handoff.json
    - INTEGRATION_NOTES.md
    visibility: group-only
  effective_skill_name: integration-delivery-integration-delivery-head--proj-test-alpha
specialists:
- agent_id: delivery-architect
  skill_name: grp-integration-delivery-architect
  focus: Delivery architecture, staged rollout plans, and dependency-aware release
    strategy
  required_references:
  - references/delivery-architecture-core.md
  required_outputs:
  - rollout_plan.md
  - claims_with_citations.md
  - work.md
  - handoff.json
  role: domain-core
  contract:
    inputs:
    - objective.md
    - group-context.json
    outputs:
    - work.md
    - handoff.json
    output_schema: specialist-handoff-v2
  depends_on: []
  execution:
    remote_transport: local
    scheduler: local
    hardware: cpu
    requires_gpu: false
  effective_skill_name: integration-delivery-delivery-architect--proj-test-alpha
- agent_id: dependency-mapping-specialist
  skill_name: grp-integration-delivery-dependencies
  focus: Dependency graph mapping, integration sequencing, and handoff risk detection
  required_references:
  - references/dependency-mapping-core.md
  required_outputs:
  - dependency_matrix.md
  - claims_with_citations.md
  - work.md
  - handoff.json
  role: domain-core
  contract:
    inputs:
    - objective.md
    - group-context.json
    outputs:
    - work.md
    - handoff.json
    output_schema: specialist-handoff-v2
  depends_on:
  - agent_id: delivery-architect
    required_artifacts:
    - internal/delivery-architect/handoff.json
    validate_with: json-parse
    on_missing: request-rerun
  execution:
    remote_transport: local
    scheduler: local
    hardware: cpu
    requires_gpu: false
  effective_skill_name: integration-delivery-dependency-mapping-specialist--pro-acbf437d
- agent_id: integration-specialist
  skill_name: grp-integration-delivery-integration
  role: integration
  focus: Cross-artifact integration and consumability checks for Integration Delivery
    Group
  required_references:
  - references/integration-core.md
  required_outputs:
  - work.md
  - handoff.json
  contract:
    inputs:
    - objective.md
    - group-context.json
    outputs:
    - work.md
    - handoff.json
    output_schema: specialist-handoff-v2
  depends_on:
  - agent_id: dependency-mapping-specialist
    required_artifacts:
    - internal/dependency-mapping-specialist/handoff.json
    validate_with: json-parse
    on_missing: request-rerun
  execution:
    remote_transport: local
    scheduler: local
    hardware: cpu
    requires_gpu: false
  effective_skill_name: integration-delivery-integration-specialist--proj-test-alpha
- agent_id: evidence-review-specialist
  skill_name: grp-integration-delivery-evidence-review
  role: evidence-review
  focus: Claim-level evidence review and citation sufficiency for Integration Delivery
    Group
  required_references:
  - references/evidence-review-core.md
  required_outputs:
  - work.md
  - handoff.json
  contract:
    inputs:
    - objective.md
    - group-context.json
    outputs:
    - work.md
    - handoff.json
    output_schema: specialist-handoff-v2
  depends_on:
  - agent_id: delivery-architect
    required_artifacts:
    - internal/delivery-architect/handoff.json
    validate_with: json-parse
    on_missing: request-rerun
  execution:
    remote_transport: local
    scheduler: local
    hardware: cpu
    requires_gpu: false
  effective_skill_name: integration-delivery-evidence-review-specialist--proj-test-alpha
- agent_id: repro-qa-specialist
  skill_name: grp-integration-delivery-repro-qa
  role: repro-qa
  focus: Reproducibility and quality assurance checks for Integration Delivery Group
  required_references:
  - references/repro-qa-core.md
  required_outputs:
  - work.md
  - handoff.json
  contract:
    inputs:
    - objective.md
    - group-context.json
    outputs:
    - work.md
    - handoff.json
    output_schema: specialist-handoff-v2
  depends_on:
  - agent_id: delivery-architect
    required_artifacts:
    - internal/delivery-architect/handoff.json
    validate_with: json-parse
    on_missing: request-rerun
  execution:
    remote_transport: local
    scheduler: local
    hardware: cpu
    requires_gpu: false
  effective_skill_name: integration-delivery-repro-qa-specialist--proj-test-alpha
- agent_id: web-research-specialist
  skill_name: grp-integration-delivery-web-research
  role: web-research
  focus: Gather web-published references and extract citation-ready evidence.
  required_references:
  - references/web-research-core.md
  required_outputs:
  - work.md
  - handoff.json
  contract:
    inputs:
    - objective.md
    - group-context.json
    outputs:
    - work.md
    - handoff.json
    output_schema: specialist-handoff-v2
  depends_on: []
  execution:
    remote_transport: local
    scheduler: local
    hardware: cpu
    requires_gpu: false
  effective_skill_name: integration-delivery-web-research-specialist--proj-test-alpha
tool_profile: delivery-default
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
schema_version: '3.0'
purpose: Coordinate specialist integration and delivery workflows for cross-team objectives.
success_criteria:
- All required artifacts produced
- Gate profile satisfied
- Exposed handoff consumable
required_artifacts:
  objective_types:
    default:
      specialist_internal:
      - internal/<agent-id>/work.md
      - internal/<agent-id>/handoff.json
      head_exposed:
      - exposed/summary.md
      - exposed/handoff.json
      - exposed/INTEGRATION_NOTES.md
gate_profile:
  profile_id: standard-evidence-v2
  specialist_output_schema: specialist-handoff-v2
  checks:
    web_citations_required: true
    repro_command_required: true
    consistency_required: true
    scope_enforced: true
interaction:
  mode: interactive-separated
  linked_groups: []
execution_defaults:
  web_search_enabled: true
  remote_transport: local
  schedulers:
  - local
  hardware:
  - cpu
```

## 34. `generated/projects/proj-test-alpha/agent-groups/integration-delivery/handoffs.yaml`

- Type: `handoff`
- Purpose: Intra-group handoff protocol
- Locked Sections: `-`
- Validation Check: content-reviewed
- Exposure Policy: source

```yaml
schema_version: "3.0"
group_id: "integration-delivery"
handoffs:
  - from: "delivery-architect"
    to: "head-controller"
    condition: "after task completion"
  - from: "dependency-mapping-specialist"
    to: "head-controller"
    condition: "after dependencies satisfied (delivery-architect)"
  - from: "integration-specialist"
    to: "head-controller"
    condition: "after dependencies satisfied (dependency-mapping-specialist)"
  - from: "evidence-review-specialist"
    to: "head-controller"
    condition: "after dependencies satisfied (delivery-architect)"
  - from: "repro-qa-specialist"
    to: "head-controller"
    condition: "after dependencies satisfied (delivery-architect)"
  - from: "web-research-specialist"
    to: "head-controller"
    condition: "after task completion"
output_contract:
  specialist_internal:
    - "internal/<agent-id>/work.md"
    - "internal/<agent-id>/handoff.json"
  head_exposed:
    - "exposed/summary.md"
    - "exposed/handoff.json"
    - "exposed/INTEGRATION_NOTES.md"
```

## 35. `generated/projects/proj-test-alpha/agent-groups/integration-delivery/internal/delivery-architect/AGENTS.md`

- Type: `agents`
- Purpose: Group operating contract and policy
- Locked Sections: `-`
- Validation Check: content-reviewed
- Exposure Policy: source

```md
# Integration Delivery Group Specialist - delivery-architect

## Role Contract
- `project_id`: `proj-test-alpha`
- `group_id`: `integration-delivery`
- `role`: `domain-core`
- `focus`: Delivery architecture, staged rollout plans, and dependency-aware release strategy
- `skill`: `integration-delivery-delivery-architect--proj-test-alpha`

## Activation
Activate and follow the `$integration-delivery-delivery-architect--proj-test-alpha` skill before proceeding.

## Required Outputs
- rollout_plan.md
- claims_with_citations.md
- work.md
- handoff.json

## Required References
- references/delivery-architecture-core.md

## Hard Gate Checks
- `web_citations_required`: `True`
- `repro_command_required`: `True`
- `consistency_required`: `True`
- `scope_enforced`: `True`

## Execution Boundaries
- Write only under `agent-groups/integration-delivery/internal/delivery-architect/`.
- Do not publish exposed artifacts directly.
- If key evidence is missing, return a blocked status with explicit reasons.
```

## 36. `generated/projects/proj-test-alpha/agent-groups/integration-delivery/internal/dependency-mapping-specialist/AGENTS.md`

- Type: `agents`
- Purpose: Group operating contract and policy
- Locked Sections: `-`
- Validation Check: content-reviewed
- Exposure Policy: source

```md
# Integration Delivery Group Specialist - dependency-mapping-specialist

## Role Contract
- `project_id`: `proj-test-alpha`
- `group_id`: `integration-delivery`
- `role`: `domain-core`
- `focus`: Dependency graph mapping, integration sequencing, and handoff risk detection
- `skill`: `integration-delivery-dependency-mapping-specialist--pro-acbf437d`

## Activation
Activate and follow the `$integration-delivery-dependency-mapping-specialist--pro-acbf437d` skill before proceeding.

## Required Outputs
- dependency_matrix.md
- claims_with_citations.md
- work.md
- handoff.json

## Required References
- references/dependency-mapping-core.md

## Hard Gate Checks
- `web_citations_required`: `True`
- `repro_command_required`: `True`
- `consistency_required`: `True`
- `scope_enforced`: `True`

## Execution Boundaries
- Write only under `agent-groups/integration-delivery/internal/dependency-mapping-specialist/`.
- Do not publish exposed artifacts directly.
- If key evidence is missing, return a blocked status with explicit reasons.
```

## 37. `generated/projects/proj-test-alpha/agent-groups/integration-delivery/internal/evidence-review-specialist/AGENTS.md`

- Type: `agents`
- Purpose: Group operating contract and policy
- Locked Sections: `-`
- Validation Check: content-reviewed
- Exposure Policy: source

```md
# Integration Delivery Group Specialist - evidence-review-specialist

## Role Contract
- `project_id`: `proj-test-alpha`
- `group_id`: `integration-delivery`
- `role`: `evidence-review`
- `focus`: Claim-level evidence review and citation sufficiency for Integration Delivery Group
- `skill`: `integration-delivery-evidence-review-specialist--proj-test-alpha`

## Activation
Activate and follow the `$integration-delivery-evidence-review-specialist--proj-test-alpha` skill before proceeding.

## Required Outputs
- work.md
- handoff.json

## Required References
- references/evidence-review-core.md

## Hard Gate Checks
- `web_citations_required`: `True`
- `repro_command_required`: `True`
- `consistency_required`: `True`
- `scope_enforced`: `True`

## Execution Boundaries
- Write only under `agent-groups/integration-delivery/internal/evidence-review-specialist/`.
- Do not publish exposed artifacts directly.
- If key evidence is missing, return a blocked status with explicit reasons.
```

## 38. `generated/projects/proj-test-alpha/agent-groups/integration-delivery/internal/integration-specialist/AGENTS.md`

- Type: `agents`
- Purpose: Group operating contract and policy
- Locked Sections: `-`
- Validation Check: content-reviewed
- Exposure Policy: source

```md
# Integration Delivery Group Specialist - integration-specialist

## Role Contract
- `project_id`: `proj-test-alpha`
- `group_id`: `integration-delivery`
- `role`: `integration`
- `focus`: Cross-artifact integration and consumability checks for Integration Delivery Group
- `skill`: `integration-delivery-integration-specialist--proj-test-alpha`

## Activation
Activate and follow the `$integration-delivery-integration-specialist--proj-test-alpha` skill before proceeding.

## Required Outputs
- work.md
- handoff.json

## Required References
- references/integration-core.md

## Hard Gate Checks
- `web_citations_required`: `True`
- `repro_command_required`: `True`
- `consistency_required`: `True`
- `scope_enforced`: `True`

## Execution Boundaries
- Write only under `agent-groups/integration-delivery/internal/integration-specialist/`.
- Do not publish exposed artifacts directly.
- If key evidence is missing, return a blocked status with explicit reasons.
```

## 39. `generated/projects/proj-test-alpha/agent-groups/integration-delivery/internal/repro-qa-specialist/AGENTS.md`

- Type: `agents`
- Purpose: Group operating contract and policy
- Locked Sections: `-`
- Validation Check: content-reviewed
- Exposure Policy: source

```md
# Integration Delivery Group Specialist - repro-qa-specialist

## Role Contract
- `project_id`: `proj-test-alpha`
- `group_id`: `integration-delivery`
- `role`: `repro-qa`
- `focus`: Reproducibility and quality assurance checks for Integration Delivery Group
- `skill`: `integration-delivery-repro-qa-specialist--proj-test-alpha`

## Activation
Activate and follow the `$integration-delivery-repro-qa-specialist--proj-test-alpha` skill before proceeding.

## Required Outputs
- work.md
- handoff.json

## Required References
- references/repro-qa-core.md

## Hard Gate Checks
- `web_citations_required`: `True`
- `repro_command_required`: `True`
- `consistency_required`: `True`
- `scope_enforced`: `True`

## Execution Boundaries
- Write only under `agent-groups/integration-delivery/internal/repro-qa-specialist/`.
- Do not publish exposed artifacts directly.
- If key evidence is missing, return a blocked status with explicit reasons.
```

## 40. `generated/projects/proj-test-alpha/agent-groups/integration-delivery/internal/web-research-specialist/AGENTS.md`

- Type: `agents`
- Purpose: Group operating contract and policy
- Locked Sections: `-`
- Validation Check: content-reviewed
- Exposure Policy: source

```md
# Integration Delivery Group Specialist - web-research-specialist

## Role Contract
- `project_id`: `proj-test-alpha`
- `group_id`: `integration-delivery`
- `role`: `web-research`
- `focus`: Gather web-published references and extract citation-ready evidence.
- `skill`: `integration-delivery-web-research-specialist--proj-test-alpha`

## Activation
Activate and follow the `$integration-delivery-web-research-specialist--proj-test-alpha` skill before proceeding.

## Required Outputs
- work.md
- handoff.json

## Required References
- references/web-research-core.md

## Hard Gate Checks
- `web_citations_required`: `True`
- `repro_command_required`: `True`
- `consistency_required`: `True`
- `scope_enforced`: `True`

## Execution Boundaries
- Write only under `agent-groups/integration-delivery/internal/web-research-specialist/`.
- Do not publish exposed artifacts directly.
- If key evidence is missing, return a blocked status with explicit reasons.
```

## 41. `generated/projects/proj-test-alpha/agent-groups/integration-delivery/skills/integration-delivery-delivery-architect--proj-test-alpha/SKILL.md`

- Type: `skill`
- Purpose: Operational skill definition for an agent or router
- Locked Sections: `-`
- Validation Check: content-reviewed
- Exposure Policy: source

```md
---
name: integration-delivery-delivery-architect--proj-test-alpha
version: "3.1.1"
role: specialist
description: domain-core specialist for Integration Delivery Group focused on Delivery architecture, staged rollout plans, and dependency-aware release strategy in project proj-test-alpha.
scope: Narrow specialist execution only; no cross-domain final decisions.
inputs:
  - objective
  - group-context.json
  - dependency artifacts
outputs:
  - internal/delivery-architect/work.md
  - internal/delivery-architect/handoff.json
failure_modes:
  - blocked_needs_evidence
  - blocked_uncited
  - scope_violation
autouse_triggers:
  - specialist dispatch task
  - dependency artifact ready
---

# delivery-architect

## Mission
Coordinate specialist integration and delivery workflows for cross-team objectives.

## Scope
Delivery architecture, staged rollout plans, and dependency-aware release strategy

## When to Invoke
- The objective requires `domain-core` expertise.
- Specialist focus applies: Delivery architecture, staged rollout plans, and dependency-aware release strategy
- Group context: `integration-delivery` in project `proj-test-alpha`.

## Definition of Done
- Produce `rollout_plan.md`.
- Produce `claims_with_citations.md`.
- Produce `work.md`.
- Produce `handoff.json`.
- Pass gate check `web_citations_required`.
- Pass gate check `repro_command_required`.
- Pass gate check `consistency_required`.
- Pass gate check `scope_enforced`.

## Method
1. Parse the objective and isolate the sub-problem tied to this specialist focus.
2. Load required references first; mark unknowns before claiming conclusions.
3. Build claim-level outputs with explicit evidence and assumptions.
4. Write required artifacts and ensure paths are reproducible by peers.

## Artifacts to Produce
- rollout_plan.md
- claims_with_citations.md
- work.md
- handoff.json

## Failure Modes
- Missing citations for key claims -> return `BLOCKED_UNCITED`.
- Missing required evidence -> return `BLOCKED_NEEDS_EVIDENCE`.
- Scope creep into other specialists' responsibilities -> return `BLOCKED_REVIEW`.
- Gate `web_citations_required` violation -> return `BLOCKED_REVIEW`.
- Gate `repro_command_required` violation -> return `BLOCKED_REVIEW`.
- Gate `consistency_required` violation -> return `BLOCKED_REVIEW`.
- Gate `scope_enforced` violation -> return `BLOCKED_REVIEW`.

## References
- references/delivery-architecture-core.md

## Gate Profile
- `web_citations_required`: `True`
- `repro_command_required`: `True`
- `consistency_required`: `True`
- `scope_enforced`: `True`

## Output Contract
- Return `BEGIN_WORK/END_WORK` markdown notes.
- Return `BEGIN_HANDOFF_JSON/END_HANDOFF_JSON` JSON object.
- Include `claims_with_citations`, `execution_status`, `dependencies_satisfied`, and reproducibility details.
```

## 42. `generated/projects/proj-test-alpha/agent-groups/integration-delivery/skills/integration-delivery-dependency-mapping-specialist--pro-acbf437d/SKILL.md`

- Type: `skill`
- Purpose: Operational skill definition for an agent or router
- Locked Sections: `-`
- Validation Check: content-reviewed
- Exposure Policy: source

```md
---
name: integration-delivery-dependency-mapping-specialist--pro-acbf437d
version: "3.1.1"
role: specialist
description: domain-core specialist for Integration Delivery Group focused on Dependency graph mapping, integration sequencing, and handoff risk detection in project proj-test-alpha.
scope: Narrow specialist execution only; no cross-domain final decisions.
inputs:
  - objective
  - group-context.json
  - dependency artifacts
outputs:
  - internal/dependency-mapping-specialist/work.md
  - internal/dependency-mapping-specialist/handoff.json
failure_modes:
  - blocked_needs_evidence
  - blocked_uncited
  - scope_violation
autouse_triggers:
  - specialist dispatch task
  - dependency artifact ready
---

# dependency-mapping-specialist

## Mission
Coordinate specialist integration and delivery workflows for cross-team objectives.

## Scope
Dependency graph mapping, integration sequencing, and handoff risk detection

## When to Invoke
- The objective requires `domain-core` expertise.
- Specialist focus applies: Dependency graph mapping, integration sequencing, and handoff risk detection
- Group context: `integration-delivery` in project `proj-test-alpha`.

## Definition of Done
- Produce `dependency_matrix.md`.
- Produce `claims_with_citations.md`.
- Produce `work.md`.
- Produce `handoff.json`.
- Pass gate check `web_citations_required`.
- Pass gate check `repro_command_required`.
- Pass gate check `consistency_required`.
- Pass gate check `scope_enforced`.

## Method
1. Parse the objective and isolate the sub-problem tied to this specialist focus.
2. Load required references first; mark unknowns before claiming conclusions.
3. Consume dependency artifacts from: delivery-architect.
4. Build claim-level outputs with explicit evidence and assumptions.
5. Write required artifacts and ensure paths are reproducible by peers.

## Artifacts to Produce
- dependency_matrix.md
- claims_with_citations.md
- work.md
- handoff.json

## Failure Modes
- Missing citations for key claims -> return `BLOCKED_UNCITED`.
- Missing required evidence -> return `BLOCKED_NEEDS_EVIDENCE`.
- Scope creep into other specialists' responsibilities -> return `BLOCKED_REVIEW`.
- Gate `web_citations_required` violation -> return `BLOCKED_REVIEW`.
- Gate `repro_command_required` violation -> return `BLOCKED_REVIEW`.
- Gate `consistency_required` violation -> return `BLOCKED_REVIEW`.
- Gate `scope_enforced` violation -> return `BLOCKED_REVIEW`.

## References
- references/dependency-mapping-core.md

## Gate Profile
- `web_citations_required`: `True`
- `repro_command_required`: `True`
- `consistency_required`: `True`
- `scope_enforced`: `True`

## Output Contract
- Return `BEGIN_WORK/END_WORK` markdown notes.
- Return `BEGIN_HANDOFF_JSON/END_HANDOFF_JSON` JSON object.
- Include `claims_with_citations`, `execution_status`, `dependencies_satisfied`, and reproducibility details.
```

## 43. `generated/projects/proj-test-alpha/agent-groups/integration-delivery/skills/integration-delivery-evidence-review-specialist--proj-test-alpha/SKILL.md`

- Type: `skill`
- Purpose: Operational skill definition for an agent or router
- Locked Sections: `-`
- Validation Check: content-reviewed
- Exposure Policy: source

```md
---
name: integration-delivery-evidence-review-specialist--proj-test-alpha
version: "3.1.1"
role: specialist
description: evidence-review specialist for Integration Delivery Group focused on Claim-level evidence review and citation sufficiency for Integration Delivery Group in project proj-test-alpha.
scope: Narrow specialist execution only; no cross-domain final decisions.
inputs:
  - objective
  - group-context.json
  - dependency artifacts
outputs:
  - internal/evidence-review-specialist/work.md
  - internal/evidence-review-specialist/handoff.json
failure_modes:
  - blocked_needs_evidence
  - blocked_uncited
  - scope_violation
autouse_triggers:
  - specialist dispatch task
  - dependency artifact ready
---

# evidence-review-specialist

## Mission
Coordinate specialist integration and delivery workflows for cross-team objectives.

## Scope
Claim-level evidence review and citation sufficiency for Integration Delivery Group

## When to Invoke
- The objective requires `evidence-review` expertise.
- Specialist focus applies: Claim-level evidence review and citation sufficiency for Integration Delivery Group
- Group context: `integration-delivery` in project `proj-test-alpha`.

## Definition of Done
- Produce `work.md`.
- Produce `handoff.json`.
- Pass gate check `web_citations_required`.
- Pass gate check `repro_command_required`.
- Pass gate check `consistency_required`.
- Pass gate check `scope_enforced`.

## Method
1. Parse the objective and isolate the sub-problem tied to this specialist focus.
2. Load required references first; mark unknowns before claiming conclusions.
3. Consume dependency artifacts from: delivery-architect.
4. Build claim-level outputs with explicit evidence and assumptions.
5. Write required artifacts and ensure paths are reproducible by peers.

## Artifacts to Produce
- work.md
- handoff.json

## Failure Modes
- Missing citations for key claims -> return `BLOCKED_UNCITED`.
- Missing required evidence -> return `BLOCKED_NEEDS_EVIDENCE`.
- Scope creep into other specialists' responsibilities -> return `BLOCKED_REVIEW`.
- Gate `web_citations_required` violation -> return `BLOCKED_REVIEW`.
- Gate `repro_command_required` violation -> return `BLOCKED_REVIEW`.
- Gate `consistency_required` violation -> return `BLOCKED_REVIEW`.
- Gate `scope_enforced` violation -> return `BLOCKED_REVIEW`.

## References
- references/evidence-review-core.md

## Gate Profile
- `web_citations_required`: `True`
- `repro_command_required`: `True`
- `consistency_required`: `True`
- `scope_enforced`: `True`

## Output Contract
- Return `BEGIN_WORK/END_WORK` markdown notes.
- Return `BEGIN_HANDOFF_JSON/END_HANDOFF_JSON` JSON object.
- Include `claims_with_citations`, `execution_status`, `dependencies_satisfied`, and reproducibility details.
```

## 44. `generated/projects/proj-test-alpha/agent-groups/integration-delivery/skills/integration-delivery-integration-delivery-head--proj-test-alpha/SKILL.md`

- Type: `skill`
- Purpose: Operational skill definition for an agent or router
- Locked Sections: `-`
- Validation Check: content-reviewed
- Exposure Policy: source

```md
---
name: integration-delivery-integration-delivery-head--proj-test-alpha
version: "3.1.1"
role: head
description: Head orchestrator for Integration Delivery Group in project proj-test-alpha with negotiation and quality-gate control.
scope: Group-level orchestration, gate enforcement, and exposed artifact publication.
inputs:
  - objective
  - project_id
  - group_id
  - dispatch_plan
outputs:
  - exposed/summary.md
  - exposed/handoff.json
  - exposed/INTEGRATION_NOTES.md
failure_modes:
  - blocked_uncited_claims
  - unresolved_cross_domain_decision
  - missing_required_artifact
autouse_triggers:
  - group objective dispatch
  - specialist handoff aggregation
---

# Integration Delivery Group Head Controller

## Mission
Coordinate specialist integration and delivery workflows for cross-team objectives.

## When to Invoke
- Group-level objective requires orchestration across specialists.
- The active group is `integration-delivery` in project `proj-test-alpha`.

## Definition of Done
- All required artifacts produced
- Gate profile satisfied
- Exposed handoff consumable

## Method
1. Build a dependency-aware dispatch plan from specialist roster and handoff constraints.
2. Execute independent tasks in parallel and dependency chains sequentially.
3. Enforce quality gates; reject, retry, or request clarification on blocked outputs.
4. Merge accepted specialist artifacts into exposed group deliverables with traceability.
5. Record integration notes, unresolved assumptions, and escalation requirements.

## Specialists
- delivery-architect: `integration-delivery-delivery-architect--proj-test-alpha`
- dependency-mapping-specialist: `integration-delivery-dependency-mapping-specialist--pro-acbf437d`
- integration-specialist: `integration-delivery-integration-specialist--proj-test-alpha`
- evidence-review-specialist: `integration-delivery-evidence-review-specialist--proj-test-alpha`
- repro-qa-specialist: `integration-delivery-repro-qa-specialist--proj-test-alpha`
- web-research-specialist: `integration-delivery-web-research-specialist--proj-test-alpha`

## Gate Profile
- `web_citations_required`: `True`
- `repro_command_required`: `True`
- `consistency_required`: `True`
- `scope_enforced`: `True`

## Exposed Deliverables
- `exposed/summary.md`
- `exposed/handoff.json`
- `exposed/INTEGRATION_NOTES.md`
```

## 45. `generated/projects/proj-test-alpha/agent-groups/integration-delivery/skills/integration-delivery-integration-specialist--proj-test-alpha/SKILL.md`

- Type: `skill`
- Purpose: Operational skill definition for an agent or router
- Locked Sections: `-`
- Validation Check: content-reviewed
- Exposure Policy: source

```md
---
name: integration-delivery-integration-specialist--proj-test-alpha
version: "3.1.1"
role: specialist
description: integration specialist for Integration Delivery Group focused on Cross-artifact integration and consumability checks for Integration Delivery Group in project proj-test-alpha.
scope: Narrow specialist execution only; no cross-domain final decisions.
inputs:
  - objective
  - group-context.json
  - dependency artifacts
outputs:
  - internal/integration-specialist/work.md
  - internal/integration-specialist/handoff.json
failure_modes:
  - blocked_needs_evidence
  - blocked_uncited
  - scope_violation
autouse_triggers:
  - specialist dispatch task
  - dependency artifact ready
---

# integration-specialist

## Mission
Coordinate specialist integration and delivery workflows for cross-team objectives.

## Scope
Cross-artifact integration and consumability checks for Integration Delivery Group

## When to Invoke
- The objective requires `integration` expertise.
- Specialist focus applies: Cross-artifact integration and consumability checks for Integration Delivery Group
- Group context: `integration-delivery` in project `proj-test-alpha`.

## Definition of Done
- Produce `work.md`.
- Produce `handoff.json`.
- Pass gate check `web_citations_required`.
- Pass gate check `repro_command_required`.
- Pass gate check `consistency_required`.
- Pass gate check `scope_enforced`.

## Method
1. Parse the objective and isolate the sub-problem tied to this specialist focus.
2. Load required references first; mark unknowns before claiming conclusions.
3. Consume dependency artifacts from: dependency-mapping-specialist.
4. Build claim-level outputs with explicit evidence and assumptions.
5. Write required artifacts and ensure paths are reproducible by peers.

## Artifacts to Produce
- work.md
- handoff.json

## Failure Modes
- Missing citations for key claims -> return `BLOCKED_UNCITED`.
- Missing required evidence -> return `BLOCKED_NEEDS_EVIDENCE`.
- Scope creep into other specialists' responsibilities -> return `BLOCKED_REVIEW`.
- Gate `web_citations_required` violation -> return `BLOCKED_REVIEW`.
- Gate `repro_command_required` violation -> return `BLOCKED_REVIEW`.
- Gate `consistency_required` violation -> return `BLOCKED_REVIEW`.
- Gate `scope_enforced` violation -> return `BLOCKED_REVIEW`.

## References
- references/integration-core.md

## Gate Profile
- `web_citations_required`: `True`
- `repro_command_required`: `True`
- `consistency_required`: `True`
- `scope_enforced`: `True`

## Output Contract
- Return `BEGIN_WORK/END_WORK` markdown notes.
- Return `BEGIN_HANDOFF_JSON/END_HANDOFF_JSON` JSON object.
- Include `claims_with_citations`, `execution_status`, `dependencies_satisfied`, and reproducibility details.
```

## 46. `generated/projects/proj-test-alpha/agent-groups/integration-delivery/skills/integration-delivery-repro-qa-specialist--proj-test-alpha/SKILL.md`

- Type: `skill`
- Purpose: Operational skill definition for an agent or router
- Locked Sections: `-`
- Validation Check: content-reviewed
- Exposure Policy: source

```md
---
name: integration-delivery-repro-qa-specialist--proj-test-alpha
version: "3.1.1"
role: specialist
description: repro-qa specialist for Integration Delivery Group focused on Reproducibility and quality assurance checks for Integration Delivery Group in project proj-test-alpha.
scope: Narrow specialist execution only; no cross-domain final decisions.
inputs:
  - objective
  - group-context.json
  - dependency artifacts
outputs:
  - internal/repro-qa-specialist/work.md
  - internal/repro-qa-specialist/handoff.json
failure_modes:
  - blocked_needs_evidence
  - blocked_uncited
  - scope_violation
autouse_triggers:
  - specialist dispatch task
  - dependency artifact ready
---

# repro-qa-specialist

## Mission
Coordinate specialist integration and delivery workflows for cross-team objectives.

## Scope
Reproducibility and quality assurance checks for Integration Delivery Group

## When to Invoke
- The objective requires `repro-qa` expertise.
- Specialist focus applies: Reproducibility and quality assurance checks for Integration Delivery Group
- Group context: `integration-delivery` in project `proj-test-alpha`.

## Definition of Done
- Produce `work.md`.
- Produce `handoff.json`.
- Pass gate check `web_citations_required`.
- Pass gate check `repro_command_required`.
- Pass gate check `consistency_required`.
- Pass gate check `scope_enforced`.

## Method
1. Parse the objective and isolate the sub-problem tied to this specialist focus.
2. Load required references first; mark unknowns before claiming conclusions.
3. Consume dependency artifacts from: delivery-architect.
4. Build claim-level outputs with explicit evidence and assumptions.
5. Write required artifacts and ensure paths are reproducible by peers.

## Artifacts to Produce
- work.md
- handoff.json

## Failure Modes
- Missing citations for key claims -> return `BLOCKED_UNCITED`.
- Missing required evidence -> return `BLOCKED_NEEDS_EVIDENCE`.
- Scope creep into other specialists' responsibilities -> return `BLOCKED_REVIEW`.
- Gate `web_citations_required` violation -> return `BLOCKED_REVIEW`.
- Gate `repro_command_required` violation -> return `BLOCKED_REVIEW`.
- Gate `consistency_required` violation -> return `BLOCKED_REVIEW`.
- Gate `scope_enforced` violation -> return `BLOCKED_REVIEW`.

## References
- references/repro-qa-core.md

## Gate Profile
- `web_citations_required`: `True`
- `repro_command_required`: `True`
- `consistency_required`: `True`
- `scope_enforced`: `True`

## Output Contract
- Return `BEGIN_WORK/END_WORK` markdown notes.
- Return `BEGIN_HANDOFF_JSON/END_HANDOFF_JSON` JSON object.
- Include `claims_with_citations`, `execution_status`, `dependencies_satisfied`, and reproducibility details.
```

## 47. `generated/projects/proj-test-alpha/agent-groups/integration-delivery/skills/integration-delivery-web-research-specialist--proj-test-alpha/SKILL.md`

- Type: `skill`
- Purpose: Operational skill definition for an agent or router
- Locked Sections: `-`
- Validation Check: content-reviewed
- Exposure Policy: source

```md
---
name: integration-delivery-web-research-specialist--proj-test-alpha
version: "3.1.1"
role: specialist
description: web-research specialist for Integration Delivery Group focused on Gather web-published references and extract citation-ready evidence. in project proj-test-alpha.
scope: Narrow specialist execution only; no cross-domain final decisions.
inputs:
  - objective
  - group-context.json
  - dependency artifacts
outputs:
  - internal/web-research-specialist/work.md
  - internal/web-research-specialist/handoff.json
failure_modes:
  - blocked_needs_evidence
  - blocked_uncited
  - scope_violation
autouse_triggers:
  - specialist dispatch task
  - dependency artifact ready
---

# web-research-specialist

## Mission
Coordinate specialist integration and delivery workflows for cross-team objectives.

## Scope
Gather web-published references and extract citation-ready evidence.

## When to Invoke
- The objective requires `web-research` expertise.
- Specialist focus applies: Gather web-published references and extract citation-ready evidence.
- Group context: `integration-delivery` in project `proj-test-alpha`.

## Definition of Done
- Produce `work.md`.
- Produce `handoff.json`.
- Pass gate check `web_citations_required`.
- Pass gate check `repro_command_required`.
- Pass gate check `consistency_required`.
- Pass gate check `scope_enforced`.

## Method
1. Parse the objective and isolate the sub-problem tied to this specialist focus.
2. Load required references first; mark unknowns before claiming conclusions.
3. Build claim-level outputs with explicit evidence and assumptions.
4. Write required artifacts and ensure paths are reproducible by peers.

## Artifacts to Produce
- work.md
- handoff.json

## Failure Modes
- Missing citations for key claims -> return `BLOCKED_UNCITED`.
- Missing required evidence -> return `BLOCKED_NEEDS_EVIDENCE`.
- Scope creep into other specialists' responsibilities -> return `BLOCKED_REVIEW`.
- Gate `web_citations_required` violation -> return `BLOCKED_REVIEW`.
- Gate `repro_command_required` violation -> return `BLOCKED_REVIEW`.
- Gate `consistency_required` violation -> return `BLOCKED_REVIEW`.
- Gate `scope_enforced` violation -> return `BLOCKED_REVIEW`.

## References
- references/web-research-core.md

## Gate Profile
- `web_citations_required`: `True`
- `repro_command_required`: `True`
- `consistency_required`: `True`
- `scope_enforced`: `True`

## Output Contract
- Return `BEGIN_WORK/END_WORK` markdown notes.
- Return `BEGIN_HANDOFF_JSON/END_HANDOFF_JSON` JSON object.
- Include `claims_with_citations`, `execution_status`, `dependencies_satisfied`, and reproducibility details.
```

## 48. `generated/projects/proj-test-alpha/agent-groups/integration-delivery/tools/allowlist.yaml`

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
tool_profile: "delivery-default"
```

## 49. `generated/projects/proj-test-alpha/manifest.yaml`

- Type: `manifest`
- Purpose: Project or group manifest instance
- Locked Sections: `-`
- Validation Check: schema-validated
- Exposure Policy: source

```yaml
schema_version: '3.0'
project_id: proj-test-alpha
selected_groups:
- integration-delivery
install_targets:
  codex_skill_dir: /tmp/agents-inc-home/.codex/skills/local
router_skill_name: research-router
bundle_version: 3.0.0
template_versions:
  integration-delivery: 3.0.0
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
  integration-delivery:
    manifest_path: agent-groups/integration-delivery/group.yaml
    skill_dirs:
    - agent-groups/integration-delivery/skills/integration-delivery-integration-delivery-head--proj-test-alpha
    - agent-groups/integration-delivery/skills/integration-delivery-delivery-architect--proj-test-alpha
    - agent-groups/integration-delivery/skills/integration-delivery-dependency-mapping-specialist--pro-acbf437d
    - agent-groups/integration-delivery/skills/integration-delivery-integration-specialist--proj-test-alpha
    - agent-groups/integration-delivery/skills/integration-delivery-evidence-review-specialist--proj-test-alpha
    - agent-groups/integration-delivery/skills/integration-delivery-repro-qa-specialist--proj-test-alpha
    - agent-groups/integration-delivery/skills/integration-delivery-web-research-specialist--proj-test-alpha
    head_skill_dir: agent-groups/integration-delivery/skills/integration-delivery-integration-delivery-head--proj-test-alpha
    specialist_skill_dirs:
    - agent-groups/integration-delivery/skills/integration-delivery-delivery-architect--proj-test-alpha
    - agent-groups/integration-delivery/skills/integration-delivery-dependency-mapping-specialist--pro-acbf437d
    - agent-groups/integration-delivery/skills/integration-delivery-integration-specialist--proj-test-alpha
    - agent-groups/integration-delivery/skills/integration-delivery-evidence-review-specialist--proj-test-alpha
    - agent-groups/integration-delivery/skills/integration-delivery-repro-qa-specialist--proj-test-alpha
    - agent-groups/integration-delivery/skills/integration-delivery-web-research-specialist--proj-test-alpha
```

## 50. `generated/projects/proj-test-hpc/agent-groups/integration-delivery/AGENTS.md`

- Type: `agents`
- Purpose: Group operating contract and policy
- Locked Sections: `safety_policy, citation_gate, routing_audit, exposure_policy`
- Validation Check: content-reviewed
- Exposure Policy: source

```md
# Integration Delivery Group - proj-test-hpc

## Mission
Coordinate cross-team integration, release readiness, and delivery quality for professional services workflows.

## Group Identity
- `group_id`: `integration-delivery`
- `template_version`: `3.0.0`
- `tool_profile`: `delivery-default`
- `head_agent`: `integration-delivery-head`
- `head_skill`: `integration-delivery-integration-delivery-head--proj-test-hpc`

## Specialist Roster
- `delivery-architect`: Delivery architecture, staged rollout plans, and dependency-aware release strategy (skill: `integration-delivery-delivery-architect--proj-test-hpc`)
- `dependency-mapping-specialist`: Dependency graph mapping, integration sequencing, and handoff risk detection (skill: `integration-delivery-dependency-mapping-specialist--pro-e1e000cd`)
- `integration-specialist`: Cross-artifact integration and consumability checks for Integration Delivery Group (skill: `integration-delivery-integration-specialist--proj-test-hpc`)
- `evidence-review-specialist`: Claim-level evidence review and citation sufficiency for Integration Delivery Group (skill: `integration-delivery-evidence-review-specialist--proj-test-hpc`)
- `repro-qa-specialist`: Reproducibility and quality assurance checks for Integration Delivery Group (skill: `integration-delivery-repro-qa-specialist--proj-test-hpc`)
- `web-research-specialist`: Gather web-published references and extract citation-ready evidence. (skill: `integration-delivery-web-research-specialist--proj-test-hpc`)

## Work Directories
- `generated/projects/proj-test-hpc/work/integration-delivery/delivery-architect`
- `generated/projects/proj-test-hpc/work/integration-delivery/dependency-mapping-specialist`
- `generated/projects/proj-test-hpc/work/integration-delivery/integration-specialist`
- `generated/projects/proj-test-hpc/work/integration-delivery/evidence-review-specialist`
- `generated/projects/proj-test-hpc/work/integration-delivery/repro-qa-specialist`
- `generated/projects/proj-test-hpc/work/integration-delivery/web-research-specialist`

## Artifact Partition
- Internal specialist artifacts: `agent-groups/integration-delivery/internal/<specialist>/...`
- Exposed group artifacts: `agent-groups/integration-delivery/exposed/...`
- Specialist runtime instructions: `agent-groups/integration-delivery/internal/<specialist>/AGENTS.md`
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
- `rollout_plan.md` from `delivery-architect`
- `claims_with_citations.md` from `delivery-architect`
- `work.md` from `delivery-architect`
- `handoff.json` from `delivery-architect`
- `dependency_matrix.md` from `dependency-mapping-specialist`
- `claims_with_citations.md` from `dependency-mapping-specialist`
- `work.md` from `dependency-mapping-specialist`
- `handoff.json` from `dependency-mapping-specialist`
- `work.md` from `integration-specialist`
- `handoff.json` from `integration-specialist`
- `work.md` from `evidence-review-specialist`
- `handoff.json` from `evidence-review-specialist`
- `work.md` from `repro-qa-specialist`
- `handoff.json` from `repro-qa-specialist`
- `work.md` from `web-research-specialist`
- `handoff.json` from `web-research-specialist`

## Quality Gates
- `citation_required`: `True`
- `unresolved_claims_block`: `True`
- `peer_check_required`: `True`
- `consistency_required`: `True`
- `scope_required`: `True`
- `reproducibility_required`: `True`
```

## 51. `generated/projects/proj-test-hpc/agent-groups/integration-delivery/group.yaml`

- Type: `manifest`
- Purpose: Project or group manifest instance
- Locked Sections: `-`
- Validation Check: schema-validated
- Exposure Policy: source

```yaml
group_id: integration-delivery
display_name: Integration Delivery Group
template_version: 3.0.0
domain: integration-and-delivery
head:
  agent_id: integration-delivery-head
  skill_name: grp-integration-delivery-head
  mission: Coordinate cross-team integration, release readiness, and delivery quality
    for professional services workflows.
  publish_contract:
    exposed_required:
    - summary.md
    - handoff.json
    - INTEGRATION_NOTES.md
    visibility: group-only
  effective_skill_name: integration-delivery-integration-delivery-head--proj-test-hpc
specialists:
- agent_id: delivery-architect
  skill_name: grp-integration-delivery-architect
  focus: Delivery architecture, staged rollout plans, and dependency-aware release
    strategy
  required_references:
  - references/delivery-architecture-core.md
  required_outputs:
  - rollout_plan.md
  - claims_with_citations.md
  - work.md
  - handoff.json
  role: domain-core
  contract:
    inputs:
    - objective.md
    - group-context.json
    outputs:
    - work.md
    - handoff.json
    output_schema: specialist-handoff-v2
  depends_on: []
  execution:
    remote_transport: local
    scheduler: local
    hardware: cpu
    requires_gpu: false
  effective_skill_name: integration-delivery-delivery-architect--proj-test-hpc
- agent_id: dependency-mapping-specialist
  skill_name: grp-integration-delivery-dependencies
  focus: Dependency graph mapping, integration sequencing, and handoff risk detection
  required_references:
  - references/dependency-mapping-core.md
  required_outputs:
  - dependency_matrix.md
  - claims_with_citations.md
  - work.md
  - handoff.json
  role: domain-core
  contract:
    inputs:
    - objective.md
    - group-context.json
    outputs:
    - work.md
    - handoff.json
    output_schema: specialist-handoff-v2
  depends_on:
  - agent_id: delivery-architect
    required_artifacts:
    - internal/delivery-architect/handoff.json
    validate_with: json-parse
    on_missing: request-rerun
  execution:
    remote_transport: local
    scheduler: local
    hardware: cpu
    requires_gpu: false
  effective_skill_name: integration-delivery-dependency-mapping-specialist--pro-e1e000cd
- agent_id: integration-specialist
  skill_name: grp-integration-delivery-integration
  role: integration
  focus: Cross-artifact integration and consumability checks for Integration Delivery
    Group
  required_references:
  - references/integration-core.md
  required_outputs:
  - work.md
  - handoff.json
  contract:
    inputs:
    - objective.md
    - group-context.json
    outputs:
    - work.md
    - handoff.json
    output_schema: specialist-handoff-v2
  depends_on:
  - agent_id: dependency-mapping-specialist
    required_artifacts:
    - internal/dependency-mapping-specialist/handoff.json
    validate_with: json-parse
    on_missing: request-rerun
  execution:
    remote_transport: local
    scheduler: local
    hardware: cpu
    requires_gpu: false
  effective_skill_name: integration-delivery-integration-specialist--proj-test-hpc
- agent_id: evidence-review-specialist
  skill_name: grp-integration-delivery-evidence-review
  role: evidence-review
  focus: Claim-level evidence review and citation sufficiency for Integration Delivery
    Group
  required_references:
  - references/evidence-review-core.md
  required_outputs:
  - work.md
  - handoff.json
  contract:
    inputs:
    - objective.md
    - group-context.json
    outputs:
    - work.md
    - handoff.json
    output_schema: specialist-handoff-v2
  depends_on:
  - agent_id: delivery-architect
    required_artifacts:
    - internal/delivery-architect/handoff.json
    validate_with: json-parse
    on_missing: request-rerun
  execution:
    remote_transport: local
    scheduler: local
    hardware: cpu
    requires_gpu: false
  effective_skill_name: integration-delivery-evidence-review-specialist--proj-test-hpc
- agent_id: repro-qa-specialist
  skill_name: grp-integration-delivery-repro-qa
  role: repro-qa
  focus: Reproducibility and quality assurance checks for Integration Delivery Group
  required_references:
  - references/repro-qa-core.md
  required_outputs:
  - work.md
  - handoff.json
  contract:
    inputs:
    - objective.md
    - group-context.json
    outputs:
    - work.md
    - handoff.json
    output_schema: specialist-handoff-v2
  depends_on:
  - agent_id: delivery-architect
    required_artifacts:
    - internal/delivery-architect/handoff.json
    validate_with: json-parse
    on_missing: request-rerun
  execution:
    remote_transport: local
    scheduler: local
    hardware: cpu
    requires_gpu: false
  effective_skill_name: integration-delivery-repro-qa-specialist--proj-test-hpc
- agent_id: web-research-specialist
  skill_name: grp-integration-delivery-web-research
  role: web-research
  focus: Gather web-published references and extract citation-ready evidence.
  required_references:
  - references/web-research-core.md
  required_outputs:
  - work.md
  - handoff.json
  contract:
    inputs:
    - objective.md
    - group-context.json
    outputs:
    - work.md
    - handoff.json
    output_schema: specialist-handoff-v2
  depends_on: []
  execution:
    remote_transport: local
    scheduler: local
    hardware: cpu
    requires_gpu: false
  effective_skill_name: integration-delivery-web-research-specialist--proj-test-hpc
tool_profile: delivery-default
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
schema_version: '3.0'
purpose: Coordinate specialist integration and delivery workflows for cross-team objectives.
success_criteria:
- All required artifacts produced
- Gate profile satisfied
- Exposed handoff consumable
required_artifacts:
  objective_types:
    default:
      specialist_internal:
      - internal/<agent-id>/work.md
      - internal/<agent-id>/handoff.json
      head_exposed:
      - exposed/summary.md
      - exposed/handoff.json
      - exposed/INTEGRATION_NOTES.md
gate_profile:
  profile_id: standard-evidence-v2
  specialist_output_schema: specialist-handoff-v2
  checks:
    web_citations_required: true
    repro_command_required: true
    consistency_required: true
    scope_enforced: true
interaction:
  mode: interactive-separated
  linked_groups: []
execution_defaults:
  web_search_enabled: true
  remote_transport: local
  schedulers:
  - local
  hardware:
  - cpu
```

## 52. `generated/projects/proj-test-hpc/agent-groups/integration-delivery/handoffs.yaml`

- Type: `handoff`
- Purpose: Intra-group handoff protocol
- Locked Sections: `-`
- Validation Check: content-reviewed
- Exposure Policy: source

```yaml
schema_version: "3.0"
group_id: "integration-delivery"
handoffs:
  - from: "delivery-architect"
    to: "head-controller"
    condition: "after task completion"
  - from: "dependency-mapping-specialist"
    to: "head-controller"
    condition: "after dependencies satisfied (delivery-architect)"
  - from: "integration-specialist"
    to: "head-controller"
    condition: "after dependencies satisfied (dependency-mapping-specialist)"
  - from: "evidence-review-specialist"
    to: "head-controller"
    condition: "after dependencies satisfied (delivery-architect)"
  - from: "repro-qa-specialist"
    to: "head-controller"
    condition: "after dependencies satisfied (delivery-architect)"
  - from: "web-research-specialist"
    to: "head-controller"
    condition: "after task completion"
output_contract:
  specialist_internal:
    - "internal/<agent-id>/work.md"
    - "internal/<agent-id>/handoff.json"
  head_exposed:
    - "exposed/summary.md"
    - "exposed/handoff.json"
    - "exposed/INTEGRATION_NOTES.md"
```

## 53. `generated/projects/proj-test-hpc/agent-groups/integration-delivery/internal/delivery-architect/AGENTS.md`

- Type: `agents`
- Purpose: Group operating contract and policy
- Locked Sections: `-`
- Validation Check: content-reviewed
- Exposure Policy: source

```md
# Integration Delivery Group Specialist - delivery-architect

## Role Contract
- `project_id`: `proj-test-hpc`
- `group_id`: `integration-delivery`
- `role`: `domain-core`
- `focus`: Delivery architecture, staged rollout plans, and dependency-aware release strategy
- `skill`: `integration-delivery-delivery-architect--proj-test-hpc`

## Activation
Activate and follow the `$integration-delivery-delivery-architect--proj-test-hpc` skill before proceeding.

## Required Outputs
- rollout_plan.md
- claims_with_citations.md
- work.md
- handoff.json

## Required References
- references/delivery-architecture-core.md

## Hard Gate Checks
- `web_citations_required`: `True`
- `repro_command_required`: `True`
- `consistency_required`: `True`
- `scope_enforced`: `True`

## Execution Boundaries
- Write only under `agent-groups/integration-delivery/internal/delivery-architect/`.
- Do not publish exposed artifacts directly.
- If key evidence is missing, return a blocked status with explicit reasons.
```

## 54. `generated/projects/proj-test-hpc/agent-groups/integration-delivery/internal/dependency-mapping-specialist/AGENTS.md`

- Type: `agents`
- Purpose: Group operating contract and policy
- Locked Sections: `-`
- Validation Check: content-reviewed
- Exposure Policy: source

```md
# Integration Delivery Group Specialist - dependency-mapping-specialist

## Role Contract
- `project_id`: `proj-test-hpc`
- `group_id`: `integration-delivery`
- `role`: `domain-core`
- `focus`: Dependency graph mapping, integration sequencing, and handoff risk detection
- `skill`: `integration-delivery-dependency-mapping-specialist--pro-e1e000cd`

## Activation
Activate and follow the `$integration-delivery-dependency-mapping-specialist--pro-e1e000cd` skill before proceeding.

## Required Outputs
- dependency_matrix.md
- claims_with_citations.md
- work.md
- handoff.json

## Required References
- references/dependency-mapping-core.md

## Hard Gate Checks
- `web_citations_required`: `True`
- `repro_command_required`: `True`
- `consistency_required`: `True`
- `scope_enforced`: `True`

## Execution Boundaries
- Write only under `agent-groups/integration-delivery/internal/dependency-mapping-specialist/`.
- Do not publish exposed artifacts directly.
- If key evidence is missing, return a blocked status with explicit reasons.
```

## 55. `generated/projects/proj-test-hpc/agent-groups/integration-delivery/internal/evidence-review-specialist/AGENTS.md`

- Type: `agents`
- Purpose: Group operating contract and policy
- Locked Sections: `-`
- Validation Check: content-reviewed
- Exposure Policy: source

```md
# Integration Delivery Group Specialist - evidence-review-specialist

## Role Contract
- `project_id`: `proj-test-hpc`
- `group_id`: `integration-delivery`
- `role`: `evidence-review`
- `focus`: Claim-level evidence review and citation sufficiency for Integration Delivery Group
- `skill`: `integration-delivery-evidence-review-specialist--proj-test-hpc`

## Activation
Activate and follow the `$integration-delivery-evidence-review-specialist--proj-test-hpc` skill before proceeding.

## Required Outputs
- work.md
- handoff.json

## Required References
- references/evidence-review-core.md

## Hard Gate Checks
- `web_citations_required`: `True`
- `repro_command_required`: `True`
- `consistency_required`: `True`
- `scope_enforced`: `True`

## Execution Boundaries
- Write only under `agent-groups/integration-delivery/internal/evidence-review-specialist/`.
- Do not publish exposed artifacts directly.
- If key evidence is missing, return a blocked status with explicit reasons.
```

## 56. `generated/projects/proj-test-hpc/agent-groups/integration-delivery/internal/integration-specialist/AGENTS.md`

- Type: `agents`
- Purpose: Group operating contract and policy
- Locked Sections: `-`
- Validation Check: content-reviewed
- Exposure Policy: source

```md
# Integration Delivery Group Specialist - integration-specialist

## Role Contract
- `project_id`: `proj-test-hpc`
- `group_id`: `integration-delivery`
- `role`: `integration`
- `focus`: Cross-artifact integration and consumability checks for Integration Delivery Group
- `skill`: `integration-delivery-integration-specialist--proj-test-hpc`

## Activation
Activate and follow the `$integration-delivery-integration-specialist--proj-test-hpc` skill before proceeding.

## Required Outputs
- work.md
- handoff.json

## Required References
- references/integration-core.md

## Hard Gate Checks
- `web_citations_required`: `True`
- `repro_command_required`: `True`
- `consistency_required`: `True`
- `scope_enforced`: `True`

## Execution Boundaries
- Write only under `agent-groups/integration-delivery/internal/integration-specialist/`.
- Do not publish exposed artifacts directly.
- If key evidence is missing, return a blocked status with explicit reasons.
```

## 57. `generated/projects/proj-test-hpc/agent-groups/integration-delivery/internal/repro-qa-specialist/AGENTS.md`

- Type: `agents`
- Purpose: Group operating contract and policy
- Locked Sections: `-`
- Validation Check: content-reviewed
- Exposure Policy: source

```md
# Integration Delivery Group Specialist - repro-qa-specialist

## Role Contract
- `project_id`: `proj-test-hpc`
- `group_id`: `integration-delivery`
- `role`: `repro-qa`
- `focus`: Reproducibility and quality assurance checks for Integration Delivery Group
- `skill`: `integration-delivery-repro-qa-specialist--proj-test-hpc`

## Activation
Activate and follow the `$integration-delivery-repro-qa-specialist--proj-test-hpc` skill before proceeding.

## Required Outputs
- work.md
- handoff.json

## Required References
- references/repro-qa-core.md

## Hard Gate Checks
- `web_citations_required`: `True`
- `repro_command_required`: `True`
- `consistency_required`: `True`
- `scope_enforced`: `True`

## Execution Boundaries
- Write only under `agent-groups/integration-delivery/internal/repro-qa-specialist/`.
- Do not publish exposed artifacts directly.
- If key evidence is missing, return a blocked status with explicit reasons.
```

## 58. `generated/projects/proj-test-hpc/agent-groups/integration-delivery/internal/web-research-specialist/AGENTS.md`

- Type: `agents`
- Purpose: Group operating contract and policy
- Locked Sections: `-`
- Validation Check: content-reviewed
- Exposure Policy: source

```md
# Integration Delivery Group Specialist - web-research-specialist

## Role Contract
- `project_id`: `proj-test-hpc`
- `group_id`: `integration-delivery`
- `role`: `web-research`
- `focus`: Gather web-published references and extract citation-ready evidence.
- `skill`: `integration-delivery-web-research-specialist--proj-test-hpc`

## Activation
Activate and follow the `$integration-delivery-web-research-specialist--proj-test-hpc` skill before proceeding.

## Required Outputs
- work.md
- handoff.json

## Required References
- references/web-research-core.md

## Hard Gate Checks
- `web_citations_required`: `True`
- `repro_command_required`: `True`
- `consistency_required`: `True`
- `scope_enforced`: `True`

## Execution Boundaries
- Write only under `agent-groups/integration-delivery/internal/web-research-specialist/`.
- Do not publish exposed artifacts directly.
- If key evidence is missing, return a blocked status with explicit reasons.
```

## 59. `generated/projects/proj-test-hpc/agent-groups/integration-delivery/skills/integration-delivery-delivery-architect--proj-test-hpc/SKILL.md`

- Type: `skill`
- Purpose: Operational skill definition for an agent or router
- Locked Sections: `-`
- Validation Check: content-reviewed
- Exposure Policy: source

```md
---
name: integration-delivery-delivery-architect--proj-test-hpc
version: "3.1.1"
role: specialist
description: domain-core specialist for Integration Delivery Group focused on Delivery architecture, staged rollout plans, and dependency-aware release strategy in project proj-test-hpc.
scope: Narrow specialist execution only; no cross-domain final decisions.
inputs:
  - objective
  - group-context.json
  - dependency artifacts
outputs:
  - internal/delivery-architect/work.md
  - internal/delivery-architect/handoff.json
failure_modes:
  - blocked_needs_evidence
  - blocked_uncited
  - scope_violation
autouse_triggers:
  - specialist dispatch task
  - dependency artifact ready
---

# delivery-architect

## Mission
Coordinate specialist integration and delivery workflows for cross-team objectives.

## Scope
Delivery architecture, staged rollout plans, and dependency-aware release strategy

## When to Invoke
- The objective requires `domain-core` expertise.
- Specialist focus applies: Delivery architecture, staged rollout plans, and dependency-aware release strategy
- Group context: `integration-delivery` in project `proj-test-hpc`.

## Definition of Done
- Produce `rollout_plan.md`.
- Produce `claims_with_citations.md`.
- Produce `work.md`.
- Produce `handoff.json`.
- Pass gate check `web_citations_required`.
- Pass gate check `repro_command_required`.
- Pass gate check `consistency_required`.
- Pass gate check `scope_enforced`.

## Method
1. Parse the objective and isolate the sub-problem tied to this specialist focus.
2. Load required references first; mark unknowns before claiming conclusions.
3. Build claim-level outputs with explicit evidence and assumptions.
4. Write required artifacts and ensure paths are reproducible by peers.

## Artifacts to Produce
- rollout_plan.md
- claims_with_citations.md
- work.md
- handoff.json

## Failure Modes
- Missing citations for key claims -> return `BLOCKED_UNCITED`.
- Missing required evidence -> return `BLOCKED_NEEDS_EVIDENCE`.
- Scope creep into other specialists' responsibilities -> return `BLOCKED_REVIEW`.
- Gate `web_citations_required` violation -> return `BLOCKED_REVIEW`.
- Gate `repro_command_required` violation -> return `BLOCKED_REVIEW`.
- Gate `consistency_required` violation -> return `BLOCKED_REVIEW`.
- Gate `scope_enforced` violation -> return `BLOCKED_REVIEW`.

## References
- references/delivery-architecture-core.md

## Gate Profile
- `web_citations_required`: `True`
- `repro_command_required`: `True`
- `consistency_required`: `True`
- `scope_enforced`: `True`

## Output Contract
- Return `BEGIN_WORK/END_WORK` markdown notes.
- Return `BEGIN_HANDOFF_JSON/END_HANDOFF_JSON` JSON object.
- Include `claims_with_citations`, `execution_status`, `dependencies_satisfied`, and reproducibility details.
```

## 60. `generated/projects/proj-test-hpc/agent-groups/integration-delivery/skills/integration-delivery-dependency-mapping-specialist--pro-e1e000cd/SKILL.md`

- Type: `skill`
- Purpose: Operational skill definition for an agent or router
- Locked Sections: `-`
- Validation Check: content-reviewed
- Exposure Policy: source

```md
---
name: integration-delivery-dependency-mapping-specialist--pro-e1e000cd
version: "3.1.1"
role: specialist
description: domain-core specialist for Integration Delivery Group focused on Dependency graph mapping, integration sequencing, and handoff risk detection in project proj-test-hpc.
scope: Narrow specialist execution only; no cross-domain final decisions.
inputs:
  - objective
  - group-context.json
  - dependency artifacts
outputs:
  - internal/dependency-mapping-specialist/work.md
  - internal/dependency-mapping-specialist/handoff.json
failure_modes:
  - blocked_needs_evidence
  - blocked_uncited
  - scope_violation
autouse_triggers:
  - specialist dispatch task
  - dependency artifact ready
---

# dependency-mapping-specialist

## Mission
Coordinate specialist integration and delivery workflows for cross-team objectives.

## Scope
Dependency graph mapping, integration sequencing, and handoff risk detection

## When to Invoke
- The objective requires `domain-core` expertise.
- Specialist focus applies: Dependency graph mapping, integration sequencing, and handoff risk detection
- Group context: `integration-delivery` in project `proj-test-hpc`.

## Definition of Done
- Produce `dependency_matrix.md`.
- Produce `claims_with_citations.md`.
- Produce `work.md`.
- Produce `handoff.json`.
- Pass gate check `web_citations_required`.
- Pass gate check `repro_command_required`.
- Pass gate check `consistency_required`.
- Pass gate check `scope_enforced`.

## Method
1. Parse the objective and isolate the sub-problem tied to this specialist focus.
2. Load required references first; mark unknowns before claiming conclusions.
3. Consume dependency artifacts from: delivery-architect.
4. Build claim-level outputs with explicit evidence and assumptions.
5. Write required artifacts and ensure paths are reproducible by peers.

## Artifacts to Produce
- dependency_matrix.md
- claims_with_citations.md
- work.md
- handoff.json

## Failure Modes
- Missing citations for key claims -> return `BLOCKED_UNCITED`.
- Missing required evidence -> return `BLOCKED_NEEDS_EVIDENCE`.
- Scope creep into other specialists' responsibilities -> return `BLOCKED_REVIEW`.
- Gate `web_citations_required` violation -> return `BLOCKED_REVIEW`.
- Gate `repro_command_required` violation -> return `BLOCKED_REVIEW`.
- Gate `consistency_required` violation -> return `BLOCKED_REVIEW`.
- Gate `scope_enforced` violation -> return `BLOCKED_REVIEW`.

## References
- references/dependency-mapping-core.md

## Gate Profile
- `web_citations_required`: `True`
- `repro_command_required`: `True`
- `consistency_required`: `True`
- `scope_enforced`: `True`

## Output Contract
- Return `BEGIN_WORK/END_WORK` markdown notes.
- Return `BEGIN_HANDOFF_JSON/END_HANDOFF_JSON` JSON object.
- Include `claims_with_citations`, `execution_status`, `dependencies_satisfied`, and reproducibility details.
```

## 61. `generated/projects/proj-test-hpc/agent-groups/integration-delivery/skills/integration-delivery-evidence-review-specialist--proj-test-hpc/SKILL.md`

- Type: `skill`
- Purpose: Operational skill definition for an agent or router
- Locked Sections: `-`
- Validation Check: content-reviewed
- Exposure Policy: source

```md
---
name: integration-delivery-evidence-review-specialist--proj-test-hpc
version: "3.1.1"
role: specialist
description: evidence-review specialist for Integration Delivery Group focused on Claim-level evidence review and citation sufficiency for Integration Delivery Group in project proj-test-hpc.
scope: Narrow specialist execution only; no cross-domain final decisions.
inputs:
  - objective
  - group-context.json
  - dependency artifacts
outputs:
  - internal/evidence-review-specialist/work.md
  - internal/evidence-review-specialist/handoff.json
failure_modes:
  - blocked_needs_evidence
  - blocked_uncited
  - scope_violation
autouse_triggers:
  - specialist dispatch task
  - dependency artifact ready
---

# evidence-review-specialist

## Mission
Coordinate specialist integration and delivery workflows for cross-team objectives.

## Scope
Claim-level evidence review and citation sufficiency for Integration Delivery Group

## When to Invoke
- The objective requires `evidence-review` expertise.
- Specialist focus applies: Claim-level evidence review and citation sufficiency for Integration Delivery Group
- Group context: `integration-delivery` in project `proj-test-hpc`.

## Definition of Done
- Produce `work.md`.
- Produce `handoff.json`.
- Pass gate check `web_citations_required`.
- Pass gate check `repro_command_required`.
- Pass gate check `consistency_required`.
- Pass gate check `scope_enforced`.

## Method
1. Parse the objective and isolate the sub-problem tied to this specialist focus.
2. Load required references first; mark unknowns before claiming conclusions.
3. Consume dependency artifacts from: delivery-architect.
4. Build claim-level outputs with explicit evidence and assumptions.
5. Write required artifacts and ensure paths are reproducible by peers.

## Artifacts to Produce
- work.md
- handoff.json

## Failure Modes
- Missing citations for key claims -> return `BLOCKED_UNCITED`.
- Missing required evidence -> return `BLOCKED_NEEDS_EVIDENCE`.
- Scope creep into other specialists' responsibilities -> return `BLOCKED_REVIEW`.
- Gate `web_citations_required` violation -> return `BLOCKED_REVIEW`.
- Gate `repro_command_required` violation -> return `BLOCKED_REVIEW`.
- Gate `consistency_required` violation -> return `BLOCKED_REVIEW`.
- Gate `scope_enforced` violation -> return `BLOCKED_REVIEW`.

## References
- references/evidence-review-core.md

## Gate Profile
- `web_citations_required`: `True`
- `repro_command_required`: `True`
- `consistency_required`: `True`
- `scope_enforced`: `True`

## Output Contract
- Return `BEGIN_WORK/END_WORK` markdown notes.
- Return `BEGIN_HANDOFF_JSON/END_HANDOFF_JSON` JSON object.
- Include `claims_with_citations`, `execution_status`, `dependencies_satisfied`, and reproducibility details.
```

## 62. `generated/projects/proj-test-hpc/agent-groups/integration-delivery/skills/integration-delivery-integration-delivery-head--proj-test-hpc/SKILL.md`

- Type: `skill`
- Purpose: Operational skill definition for an agent or router
- Locked Sections: `-`
- Validation Check: content-reviewed
- Exposure Policy: source

```md
---
name: integration-delivery-integration-delivery-head--proj-test-hpc
version: "3.1.1"
role: head
description: Head orchestrator for Integration Delivery Group in project proj-test-hpc with negotiation and quality-gate control.
scope: Group-level orchestration, gate enforcement, and exposed artifact publication.
inputs:
  - objective
  - project_id
  - group_id
  - dispatch_plan
outputs:
  - exposed/summary.md
  - exposed/handoff.json
  - exposed/INTEGRATION_NOTES.md
failure_modes:
  - blocked_uncited_claims
  - unresolved_cross_domain_decision
  - missing_required_artifact
autouse_triggers:
  - group objective dispatch
  - specialist handoff aggregation
---

# Integration Delivery Group Head Controller

## Mission
Coordinate specialist integration and delivery workflows for cross-team objectives.

## When to Invoke
- Group-level objective requires orchestration across specialists.
- The active group is `integration-delivery` in project `proj-test-hpc`.

## Definition of Done
- All required artifacts produced
- Gate profile satisfied
- Exposed handoff consumable

## Method
1. Build a dependency-aware dispatch plan from specialist roster and handoff constraints.
2. Execute independent tasks in parallel and dependency chains sequentially.
3. Enforce quality gates; reject, retry, or request clarification on blocked outputs.
4. Merge accepted specialist artifacts into exposed group deliverables with traceability.
5. Record integration notes, unresolved assumptions, and escalation requirements.

## Specialists
- delivery-architect: `integration-delivery-delivery-architect--proj-test-hpc`
- dependency-mapping-specialist: `integration-delivery-dependency-mapping-specialist--pro-e1e000cd`
- integration-specialist: `integration-delivery-integration-specialist--proj-test-hpc`
- evidence-review-specialist: `integration-delivery-evidence-review-specialist--proj-test-hpc`
- repro-qa-specialist: `integration-delivery-repro-qa-specialist--proj-test-hpc`
- web-research-specialist: `integration-delivery-web-research-specialist--proj-test-hpc`

## Gate Profile
- `web_citations_required`: `True`
- `repro_command_required`: `True`
- `consistency_required`: `True`
- `scope_enforced`: `True`

## Exposed Deliverables
- `exposed/summary.md`
- `exposed/handoff.json`
- `exposed/INTEGRATION_NOTES.md`
```

## 63. `generated/projects/proj-test-hpc/agent-groups/integration-delivery/skills/integration-delivery-integration-specialist--proj-test-hpc/SKILL.md`

- Type: `skill`
- Purpose: Operational skill definition for an agent or router
- Locked Sections: `-`
- Validation Check: content-reviewed
- Exposure Policy: source

```md
---
name: integration-delivery-integration-specialist--proj-test-hpc
version: "3.1.1"
role: specialist
description: integration specialist for Integration Delivery Group focused on Cross-artifact integration and consumability checks for Integration Delivery Group in project proj-test-hpc.
scope: Narrow specialist execution only; no cross-domain final decisions.
inputs:
  - objective
  - group-context.json
  - dependency artifacts
outputs:
  - internal/integration-specialist/work.md
  - internal/integration-specialist/handoff.json
failure_modes:
  - blocked_needs_evidence
  - blocked_uncited
  - scope_violation
autouse_triggers:
  - specialist dispatch task
  - dependency artifact ready
---

# integration-specialist

## Mission
Coordinate specialist integration and delivery workflows for cross-team objectives.

## Scope
Cross-artifact integration and consumability checks for Integration Delivery Group

## When to Invoke
- The objective requires `integration` expertise.
- Specialist focus applies: Cross-artifact integration and consumability checks for Integration Delivery Group
- Group context: `integration-delivery` in project `proj-test-hpc`.

## Definition of Done
- Produce `work.md`.
- Produce `handoff.json`.
- Pass gate check `web_citations_required`.
- Pass gate check `repro_command_required`.
- Pass gate check `consistency_required`.
- Pass gate check `scope_enforced`.

## Method
1. Parse the objective and isolate the sub-problem tied to this specialist focus.
2. Load required references first; mark unknowns before claiming conclusions.
3. Consume dependency artifacts from: dependency-mapping-specialist.
4. Build claim-level outputs with explicit evidence and assumptions.
5. Write required artifacts and ensure paths are reproducible by peers.

## Artifacts to Produce
- work.md
- handoff.json

## Failure Modes
- Missing citations for key claims -> return `BLOCKED_UNCITED`.
- Missing required evidence -> return `BLOCKED_NEEDS_EVIDENCE`.
- Scope creep into other specialists' responsibilities -> return `BLOCKED_REVIEW`.
- Gate `web_citations_required` violation -> return `BLOCKED_REVIEW`.
- Gate `repro_command_required` violation -> return `BLOCKED_REVIEW`.
- Gate `consistency_required` violation -> return `BLOCKED_REVIEW`.
- Gate `scope_enforced` violation -> return `BLOCKED_REVIEW`.

## References
- references/integration-core.md

## Gate Profile
- `web_citations_required`: `True`
- `repro_command_required`: `True`
- `consistency_required`: `True`
- `scope_enforced`: `True`

## Output Contract
- Return `BEGIN_WORK/END_WORK` markdown notes.
- Return `BEGIN_HANDOFF_JSON/END_HANDOFF_JSON` JSON object.
- Include `claims_with_citations`, `execution_status`, `dependencies_satisfied`, and reproducibility details.
```

## 64. `generated/projects/proj-test-hpc/agent-groups/integration-delivery/skills/integration-delivery-repro-qa-specialist--proj-test-hpc/SKILL.md`

- Type: `skill`
- Purpose: Operational skill definition for an agent or router
- Locked Sections: `-`
- Validation Check: content-reviewed
- Exposure Policy: source

```md
---
name: integration-delivery-repro-qa-specialist--proj-test-hpc
version: "3.1.1"
role: specialist
description: repro-qa specialist for Integration Delivery Group focused on Reproducibility and quality assurance checks for Integration Delivery Group in project proj-test-hpc.
scope: Narrow specialist execution only; no cross-domain final decisions.
inputs:
  - objective
  - group-context.json
  - dependency artifacts
outputs:
  - internal/repro-qa-specialist/work.md
  - internal/repro-qa-specialist/handoff.json
failure_modes:
  - blocked_needs_evidence
  - blocked_uncited
  - scope_violation
autouse_triggers:
  - specialist dispatch task
  - dependency artifact ready
---

# repro-qa-specialist

## Mission
Coordinate specialist integration and delivery workflows for cross-team objectives.

## Scope
Reproducibility and quality assurance checks for Integration Delivery Group

## When to Invoke
- The objective requires `repro-qa` expertise.
- Specialist focus applies: Reproducibility and quality assurance checks for Integration Delivery Group
- Group context: `integration-delivery` in project `proj-test-hpc`.

## Definition of Done
- Produce `work.md`.
- Produce `handoff.json`.
- Pass gate check `web_citations_required`.
- Pass gate check `repro_command_required`.
- Pass gate check `consistency_required`.
- Pass gate check `scope_enforced`.

## Method
1. Parse the objective and isolate the sub-problem tied to this specialist focus.
2. Load required references first; mark unknowns before claiming conclusions.
3. Consume dependency artifacts from: delivery-architect.
4. Build claim-level outputs with explicit evidence and assumptions.
5. Write required artifacts and ensure paths are reproducible by peers.

## Artifacts to Produce
- work.md
- handoff.json

## Failure Modes
- Missing citations for key claims -> return `BLOCKED_UNCITED`.
- Missing required evidence -> return `BLOCKED_NEEDS_EVIDENCE`.
- Scope creep into other specialists' responsibilities -> return `BLOCKED_REVIEW`.
- Gate `web_citations_required` violation -> return `BLOCKED_REVIEW`.
- Gate `repro_command_required` violation -> return `BLOCKED_REVIEW`.
- Gate `consistency_required` violation -> return `BLOCKED_REVIEW`.
- Gate `scope_enforced` violation -> return `BLOCKED_REVIEW`.

## References
- references/repro-qa-core.md

## Gate Profile
- `web_citations_required`: `True`
- `repro_command_required`: `True`
- `consistency_required`: `True`
- `scope_enforced`: `True`

## Output Contract
- Return `BEGIN_WORK/END_WORK` markdown notes.
- Return `BEGIN_HANDOFF_JSON/END_HANDOFF_JSON` JSON object.
- Include `claims_with_citations`, `execution_status`, `dependencies_satisfied`, and reproducibility details.
```

## 65. `generated/projects/proj-test-hpc/agent-groups/integration-delivery/skills/integration-delivery-web-research-specialist--proj-test-hpc/SKILL.md`

- Type: `skill`
- Purpose: Operational skill definition for an agent or router
- Locked Sections: `-`
- Validation Check: content-reviewed
- Exposure Policy: source

```md
---
name: integration-delivery-web-research-specialist--proj-test-hpc
version: "3.1.1"
role: specialist
description: web-research specialist for Integration Delivery Group focused on Gather web-published references and extract citation-ready evidence. in project proj-test-hpc.
scope: Narrow specialist execution only; no cross-domain final decisions.
inputs:
  - objective
  - group-context.json
  - dependency artifacts
outputs:
  - internal/web-research-specialist/work.md
  - internal/web-research-specialist/handoff.json
failure_modes:
  - blocked_needs_evidence
  - blocked_uncited
  - scope_violation
autouse_triggers:
  - specialist dispatch task
  - dependency artifact ready
---

# web-research-specialist

## Mission
Coordinate specialist integration and delivery workflows for cross-team objectives.

## Scope
Gather web-published references and extract citation-ready evidence.

## When to Invoke
- The objective requires `web-research` expertise.
- Specialist focus applies: Gather web-published references and extract citation-ready evidence.
- Group context: `integration-delivery` in project `proj-test-hpc`.

## Definition of Done
- Produce `work.md`.
- Produce `handoff.json`.
- Pass gate check `web_citations_required`.
- Pass gate check `repro_command_required`.
- Pass gate check `consistency_required`.
- Pass gate check `scope_enforced`.

## Method
1. Parse the objective and isolate the sub-problem tied to this specialist focus.
2. Load required references first; mark unknowns before claiming conclusions.
3. Build claim-level outputs with explicit evidence and assumptions.
4. Write required artifacts and ensure paths are reproducible by peers.

## Artifacts to Produce
- work.md
- handoff.json

## Failure Modes
- Missing citations for key claims -> return `BLOCKED_UNCITED`.
- Missing required evidence -> return `BLOCKED_NEEDS_EVIDENCE`.
- Scope creep into other specialists' responsibilities -> return `BLOCKED_REVIEW`.
- Gate `web_citations_required` violation -> return `BLOCKED_REVIEW`.
- Gate `repro_command_required` violation -> return `BLOCKED_REVIEW`.
- Gate `consistency_required` violation -> return `BLOCKED_REVIEW`.
- Gate `scope_enforced` violation -> return `BLOCKED_REVIEW`.

## References
- references/web-research-core.md

## Gate Profile
- `web_citations_required`: `True`
- `repro_command_required`: `True`
- `consistency_required`: `True`
- `scope_enforced`: `True`

## Output Contract
- Return `BEGIN_WORK/END_WORK` markdown notes.
- Return `BEGIN_HANDOFF_JSON/END_HANDOFF_JSON` JSON object.
- Include `claims_with_citations`, `execution_status`, `dependencies_satisfied`, and reproducibility details.
```

## 66. `generated/projects/proj-test-hpc/agent-groups/integration-delivery/tools/allowlist.yaml`

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
tool_profile: "delivery-default"
```

## 67. `generated/projects/proj-test-hpc/manifest.yaml`

- Type: `manifest`
- Purpose: Project or group manifest instance
- Locked Sections: `-`
- Validation Check: schema-validated
- Exposure Policy: source

```yaml
schema_version: '3.0'
project_id: proj-test-hpc
selected_groups:
- integration-delivery
install_targets:
  codex_skill_dir: /tmp/agents-inc-home/.codex/skills/local
router_skill_name: research-router
bundle_version: 3.0.0
template_versions:
  integration-delivery: 3.0.0
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
  integration-delivery:
    manifest_path: agent-groups/integration-delivery/group.yaml
    skill_dirs:
    - agent-groups/integration-delivery/skills/integration-delivery-integration-delivery-head--proj-test-hpc
    - agent-groups/integration-delivery/skills/integration-delivery-delivery-architect--proj-test-hpc
    - agent-groups/integration-delivery/skills/integration-delivery-dependency-mapping-specialist--pro-e1e000cd
    - agent-groups/integration-delivery/skills/integration-delivery-integration-specialist--proj-test-hpc
    - agent-groups/integration-delivery/skills/integration-delivery-evidence-review-specialist--proj-test-hpc
    - agent-groups/integration-delivery/skills/integration-delivery-repro-qa-specialist--proj-test-hpc
    - agent-groups/integration-delivery/skills/integration-delivery-web-research-specialist--proj-test-hpc
    head_skill_dir: agent-groups/integration-delivery/skills/integration-delivery-integration-delivery-head--proj-test-hpc
    specialist_skill_dirs:
    - agent-groups/integration-delivery/skills/integration-delivery-delivery-architect--proj-test-hpc
    - agent-groups/integration-delivery/skills/integration-delivery-dependency-mapping-specialist--pro-e1e000cd
    - agent-groups/integration-delivery/skills/integration-delivery-integration-specialist--proj-test-hpc
    - agent-groups/integration-delivery/skills/integration-delivery-evidence-review-specialist--proj-test-hpc
    - agent-groups/integration-delivery/skills/integration-delivery-repro-qa-specialist--proj-test-hpc
    - agent-groups/integration-delivery/skills/integration-delivery-web-research-specialist--proj-test-hpc
```

