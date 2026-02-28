# Session Resume Guide

Use this guide when restarting a Codex session and continuing an existing orchestrator project.

## Quick Resume

```bash
agents-inc-init-session --mode resume --resume-project-id <project-id>
```

By default this restores the latest checkpoint.

## Resume Specific Checkpoint

```bash
agents-inc-init-session \
  --mode resume \
  --resume-project-id <project-id> \
  --resume-checkpoint <checkpoint-id>
```

## Interactive Decision Flow
1. Wizard asks `Start mode (new/resume)`.
2. Choose `resume`.
3. Provide project id when prompted (or pass by CLI).
4. Wizard loads checkpoint context and regenerates:
   - `kickoff.md`
   - `router-call.txt`
   - `long-run-command.sh`
5. Wizard writes a new resume checkpoint.

## Checkpoint Semantics
- `session-state.yaml`: rolling state metadata + checkpoint counter.
- `latest-checkpoint.yaml`: pointer to latest checkpoint.
- `checkpoints/<id>.yaml`: immutable checkpoint snapshot.

Checkpoint payload includes:
- project/task/constraints
- selected groups and primary group
- router call
- latest artifacts
- pending actions
- optional quality/isolation summaries

## Global Project Index
`~/.agents-inc/projects-index.yaml` tracks:
- project root path
- fabric root path
- latest checkpoint id/path
- status (`active` or `stale`)

If an indexed path no longer exists, it is marked `stale` and skipped.

## Data Safety Defaults
- Resume is non-destructive.
- `new` mode does not overwrite existing project bundles unless explicitly allowed:
  - `--overwrite-existing` or interactive `overwrite` choice.

## Restart Workflow (Power Off / Reboot Safe)
1. Start a new Codex session.
2. Run bootstrap command from README.
3. Choose `resume` in intake.
4. Paste regenerated `router-call.txt` into session.
5. Run `long-run-command.sh` when you need full-group isolation validation again.
