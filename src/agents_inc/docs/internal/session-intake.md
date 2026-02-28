# Session Intake Guide (`agents-inc init`)

## Primary Command
Run in terminal:

```bash
agents-inc init --mode ask
```

Modes:
- `new`: create/activate a project orchestrator workspace
- `resume`: restore an existing workspace context

## New Project Intake Fields
The wizard collects:
1. task
2. timeline
3. compute (`cpu|gpu|cuda`)
4. remote cluster requirement (`yes|no`)
5. output target
6. projects root (default from `~/.agents-inc/config.yaml`)
7. project id
8. groups to activate (recommended list is editable)

## New Project Outputs
In `<project-root>`:
- `kickoff.md`
- `router-call.txt`
- `long-run-command.sh`
- `project-manifest.yaml`

Persistent state:
- `.agents-inc/state/session-state.yaml`
- `.agents-inc/state/latest-checkpoint.yaml`
- `.agents-inc/state/checkpoints/<checkpoint-id>.yaml`
- `.agents-inc/state/latest-compacted.yaml`
- `.agents-inc/state/compacted/<compact-id>.yaml`
- `.agents-inc/state/group-sessions.yaml`

## Session Listing

```bash
agents-inc list
agents-inc list --json
```

List output includes session code and active groups.

## Defaults
- visibility: `group-only`
- cross-group exchange: `exposed/` only
- `new` mode is non-destructive unless overwrite is explicitly selected
