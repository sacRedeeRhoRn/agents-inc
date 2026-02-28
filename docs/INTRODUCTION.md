# agents-inc Introduction

## Purpose

`agents-inc` provides reusable multi-agent group templates and tooling to bootstrap long-term research projects in Codex sessions.

Key goals:
- Reusable group catalogs and templates.
- Deterministic project bundle generation.
- Global routing through `$research-router`.
- Strict citation and quality gates.
- Group-scoped artifact exposure with audit-only specialist visibility.

## Architecture

- `catalog/`: source-of-truth groups/profiles.
- `templates/`: AGENTS/skills/handoffs/tool-policy templates.
- `schemas/`: validation contracts.
- `generated/projects/<project-id>/`: instantiated projects.
- `src/agents_inc/`: package implementation.

## Multi-Agent Runtime Model

- Head controller is user-facing.
- Specialists collaborate internally.
- Internal artifacts: `agent-groups/<group>/internal/<specialist>/...`
- Exposed artifacts: `agent-groups/<group>/exposed/...`

## Onboarding Flow

Use `agents-inc-init-session` to:
1. Capture task and constraints.
2. Ask `new` or `resume` mode.
3. Suggest groups and call order.
4. Create long-term root (`~/codex-projects/<project-id>` by default).
5. Build project bundle.
6. Install callable group-head skills and router.
7. Emit kickoff artifacts (`kickoff.md`, `router-call.txt`, `project-manifest.yaml`).
8. Persist resume-safe checkpoints and project index.

State persistence paths:
- `<project-root>/.agents-inc/state/session-state.yaml`
- `<project-root>/.agents-inc/state/latest-checkpoint.yaml`
- `<project-root>/.agents-inc/state/checkpoints/<checkpoint-id>.yaml`
- `~/.agents-inc/projects-index.yaml`

## HPC Simulation Group

`atomistic-hpc-simulation` includes specialists for VASP, LAMMPS, Metadynamics, scheduler/remote ops, CUDA performance, post-processing, and developer bridge.

Defaults:
- transport: SSH
- scheduler: PBS-first with Slurm compatibility
- hardware: CPU and CUDA GPU queues
- collaboration mode: interactive-separated

## Publication and Releases

- Semantic tag releases (`vX.Y.Z`)
- Release artifacts include wheel/sdist/bootstrap/checksums
- README bootstrap command is release-pinned and checksum-verified

## Full Reference

Generate exhaustive inlined reference:

```bash
agents-inc-generate-docs \
  --fabric-root /Users/moon.s.june/Documents/Playground/agent_group_fabric \
  --output docs/generated/full-template-skill-reference.md \
  --include-generated-projects
```
