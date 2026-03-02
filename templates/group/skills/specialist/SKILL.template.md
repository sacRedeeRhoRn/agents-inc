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
