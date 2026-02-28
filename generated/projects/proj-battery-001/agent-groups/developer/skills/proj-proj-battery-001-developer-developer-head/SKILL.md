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
