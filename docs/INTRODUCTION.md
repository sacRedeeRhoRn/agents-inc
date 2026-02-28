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
2. Suggest groups and call order.
3. Create long-term root (`~/codex-projects/<project-id>` by default).
4. Build project bundle.
5. Install callable group-head skills and router.
6. Emit kickoff artifacts (`kickoff.md`, `router-call.txt`, `project-manifest.yaml`).

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
