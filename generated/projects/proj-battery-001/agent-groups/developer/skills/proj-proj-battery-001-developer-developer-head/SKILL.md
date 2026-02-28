---
name: proj-proj-battery-001-developer-developer-head
version: "2.0.0"
role: head
description: Orchestrate Developer Group for project proj-battery-001 with strict gate enforcement and artifact publication contracts.
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
- integration-specialist: `proj-proj-battery-001-developer-integration-specialist`
- evidence-review-specialist: `proj-proj-battery-001-developer-evidence-review-specialist`
- web-research-specialist: `proj-proj-battery-001-developer-web-research-specialist`

## Output Contract
- `exposed/summary.md`
- `exposed/handoff.json`
- `exposed/INTEGRATION_NOTES.md`
