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
