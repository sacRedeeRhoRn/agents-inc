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
