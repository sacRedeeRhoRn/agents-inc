# Session Intake Guide

Use this guide in a fresh Codex session after bootstrap.

## Step 1: Choose Mode
The wizard asks first:

- `new`: create a new orchestrator project bundle
- `resume`: continue an existing project from checkpoint

CLI equivalent:

```bash
agents-inc-init-session --mode ask
```

## Step 2: Intake Questions (`new` mode)
1. What task do you want to start?
2. What is your target timeline?
3. Do you require CPU-only or CUDA GPU resources?
4. Will remote cluster execution over SSH be required?
5. What output format is needed (report, code, benchmark, slides)?

## Step 3: Generated Artifacts
The wizard creates:

- Long-term project root under `~/codex-projects/<project-id>`
- Project-local fabric bundle
- Group recommendations and invocation order
- Router call text (`router-call.txt`) for immediate execution
- Long-run all-group validation command (`long-run-command.sh`)
- Persistent orchestrator state:
  - `.agents-inc/state/session-state.yaml`
  - `.agents-inc/state/latest-checkpoint.yaml`
  - `.agents-inc/state/checkpoints/<checkpoint-id>.yaml`

## Step 4: Global Resume Index
The wizard updates:

- `~/.agents-inc/projects-index.yaml`

This lets a brand-new session find prior projects after shutdown/restart.

## Default Behavior
- Visibility mode: `group-only`
- Specialist artifacts: internal unless audit mode is enabled
- Existing project in `new` mode is non-destructive by default:
  - interactive: asks `resume/overwrite/cancel`
  - non-interactive: fails unless `--overwrite-existing` or `--mode resume`
- Router invocation:
  `Use $research-router for project <project-id> group <group-id>: <objective>.`
