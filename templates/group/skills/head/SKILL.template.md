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
