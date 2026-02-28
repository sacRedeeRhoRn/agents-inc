# agents-inc Introduction

## Purpose

`agents-inc` is a reusable multi-agent group platform for Codex-centered research orchestration.

Core outcomes:
- reusable expert group catalogs/templates
- deterministic per-project bundle generation
- strict quality/evidence gates
- project-scoped internal/exposed artifact model
- restart-safe orchestration state and resume workflow

## Primary Interface

Use the umbrella CLI:

```bash
agents-inc init
agents-inc list
agents-inc resume <project-id>
agents-inc dispatch ...
agents-inc long-run ...
```

Legacy `agents-inc-*` names remain as deprecating aliases in `v1.2.x`.

## Runtime Model

- Heads coordinate group specialists.
- Specialists collaborate internally.
- Cross-group communication is only through `exposed/` outputs.
- Internal specialist artifacts remain private unless audit mode is explicitly enabled.

## Onboarding and Resume

`agents-inc init` (mode `new`):
1. captures task/constraints
2. asks projects root and project id
3. recommends groups and lets user edit activation
4. generates project artifacts and installs skills
5. writes checkpoint + compacted session snapshot

`agents-inc resume <project-id>`:
1. loads compact snapshot (`auto`) or checkpoint (`rehydrate`)
2. regenerates kickoff/router artifacts
3. writes a fresh checkpoint/compact record
4. launches Codex in same terminal by default

## State Contracts

Global:
- `~/.agents-inc/config.yaml`
- `~/.agents-inc/projects-index.yaml`

Project:
- `<project-root>/.agents-inc/state/checkpoints/<checkpoint-id>.yaml`
- `<project-root>/.agents-inc/state/compacted/<compact-id>.yaml`
- `<project-root>/.agents-inc/state/group-sessions.yaml`

## HPC Group

`atomistic-hpc-simulation` includes VASP/LAMMPS/Metadynamics plus scheduler/SSH/CUDA specialists and developer bridge.

## Full Reference Generation

```bash
agents-inc docs \
  --fabric-root /Users/moon.s.june/Documents/Playground/agent_group_fabric \
  --output docs/generated/full-template-skill-reference.md \
  --include-generated-projects
```
