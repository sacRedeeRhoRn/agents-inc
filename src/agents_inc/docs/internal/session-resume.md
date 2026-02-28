# Session Resume Guide (`agents-inc resume`)

## Quick Resume

```bash
agents-inc resume <project-id>
```

Default behavior:
- resume mode: `auto`
- source preference: compact snapshot first, then checkpoint rehydrate fallback
- launch: opens Codex in same terminal at project root

## List Available Sessions

```bash
agents-inc list
```

## Resume With Explicit Source
Compacted snapshot only:

```bash
agents-inc resume <project-id> --resume-mode compact
```

Checkpoint rehydrate:

```bash
agents-inc resume <project-id> --resume-mode rehydrate --checkpoint <checkpoint-id>
```

Prepare artifacts without launching Codex:

```bash
agents-inc resume <project-id> --no-launch
```

## Regenerated Artifacts
Resume refreshes:
- `kickoff.md`
- `router-call.txt`
- `long-run-command.sh`

Resume also writes:
- a new checkpoint
- a new compacted snapshot
- specialist session map refresh (`.agents-inc/state/specialist-sessions.yaml`)
- response policy state (`.agents-inc/state/response-policy.yaml`)

## Turn Execution After Resume

Default turn command:

```bash
agents-inc orchestrator-reply --project-id <project-id> --message "<request>"
```

Strict mode behavior:
- message starts with `[non-group]`: concise direct state response
- otherwise: full delegation/negotiation/synthesis with publication-grade detail

## Global Index
`~/.agents-inc/projects-index.yaml` tracks project roots and latest checkpoints.

If an entry points to a missing path, status becomes `stale` and it is skipped unless explicitly included.
