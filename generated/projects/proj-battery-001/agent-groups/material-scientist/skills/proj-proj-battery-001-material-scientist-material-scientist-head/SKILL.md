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
