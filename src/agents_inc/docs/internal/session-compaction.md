# Session Compaction Model

Compaction stores a concise orchestrator state snapshot that is fast to resume.

## Files
Per project:
- `.agents-inc/state/latest-compacted.yaml`
- `.agents-inc/state/compacted/<compact-id>.yaml`
- `.agents-inc/state/group-sessions.yaml`

## Compact Payload
Each compact snapshot includes:
- project/task/constraints
- selected groups
- router call
- pending actions
- latest artifact paths
- quality/isolation summaries (when available)
- `session_code` (same as `compact_id`)
- `group_session_map`

## Group Session Codes
`group-sessions.yaml` assigns stable per-project codes:
- format: `<project-id>::<group-id>::<counter>`

These are project-scoped and prevent cross-project leakage when two projects activate the same group IDs.

## Resume Priority
`agents-inc resume` with `--resume-mode auto`:
1. load latest compact snapshot
2. fallback to checkpoint rehydrate if compact is missing
