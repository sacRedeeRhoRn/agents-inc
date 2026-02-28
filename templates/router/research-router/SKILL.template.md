---
name: research-router
version: 2.1.0
role: router
description: Global router for expert multi-agent group bundles. Dispatch objectives
  to group heads with strict gate and artifact contracts.
scope: Project and group dispatch routing only.
inputs:
- project_id
- group_id
- objective
outputs:
- dispatch_plan.json
- artifact_index.md
failure_modes:
- unknown_project
- unknown_group
- blocked_gate
autouse_triggers:
- router objective command
---

# Research Router

## Usage
Use this skill as:

`Use $research-router for project <project-id> group <group-id>: <objective>.`

Mode contract:
- If request starts with `[non-group]`, return concise direct state answer without delegation.
- Otherwise, run full group delegation + negotiation + synthesis and return publication-grade detail.

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
- Never return short final answers for group-routed requests.
- Always include delegation and negotiation artifact references in group-routed responses.

## Quick Command
```bash
python {{FABRIC_ROOT}}/scripts/dispatch_dry_run.py --project-id <project-id> --group <group-id> --objective "<objective>"
```
