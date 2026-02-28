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
