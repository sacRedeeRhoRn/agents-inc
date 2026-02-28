# Long-Run Full-Group Validation

This guide explains how to run the full-group interaction and artifact-isolation validator.

## Purpose

The long-run validator simulates a project-wide orchestration across all expert groups and verifies:

1. Cross-group handoffs complete with full edge coverage.
2. Specialists and heads follow strict artifact isolation.
3. Lease coordination protects specialist write workdirs.
4. Quality-gate failures are not leaked into exposed artifacts.

## Default Scenario

Canonical task:

`Film thickness dependent polymorphism stability of metastable phase`

## Command

```bash
agents-inc-long-run-test \
  --fabric-root /path/to/agent_group_fabric \
  --project-id proj-longrun-001 \
  --task "Film thickness dependent polymorphism stability of metastable phase" \
  --groups all \
  --duration-min 75 \
  --strict-isolation hard-fail \
  --run-mode local-sim \
  --seed 20260301
```

## Outputs

The run writes into:

`generated/projects/<project-id>/long-run/<run-id>/`

Expected artifacts:

- `run-config.yaml`
- `interaction-graph.yaml`
- `dispatch-plans/<group-id>.json`
- `events.ndjson`
- `access-ledger.ndjson`
- `lease-events.ndjson`
- `violations.json`
- `coverage.json`
- `final-report.md`
- `final-report.json`

State checkpoints are also written to the project state store:

- `<project-root>/.agents-inc/state/session-state.yaml`
- `<project-root>/.agents-inc/state/latest-checkpoint.yaml`
- `<project-root>/.agents-inc/state/checkpoints/<checkpoint-id>.yaml`

## Exit Codes

- `0`: pass
- `2`: isolation violation
- `3`: lease contention unresolved
- `4`: interaction coverage insufficient
- `5`: quality gate failure threshold exceeded

## Notes

- `--audit` installs specialist skills in a run-local skill target for audit diagnostics.
- The run is deterministic with fixed `--seed` and fixed config.
- Local simulation mode does not require remote SSH/HPC availability.
