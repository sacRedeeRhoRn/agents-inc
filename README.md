# agents-inc

`agents-inc` is a project-scoped multi-agent orchestration fabric for Codex.

It is designed for long work.

You can pause, shut down your machine, return later, and continue from stable project state.

The handoff stays calm:
you set intent,
group heads coordinate specialists,
and only group-level outputs are surfaced by default.

## Quick Start (Markdown-Driven, v1.2.0)

Run this in Terminal:

```bash
export AGI_VER="v1.2.0" && \
codex -C "$HOME" "$(curl -sfL "https://raw.githubusercontent.com/sacRedeeRhoRn/agents-inc/${AGI_VER}/docs/bootstrap/START_IN_CODEX.md")"
```

### What Happens Next

1. Codex opens with the `START_IN_CODEX.md` onboarding prompt.
2. The prompt ensures `agents-inc` is available in your environment.
3. You choose `new` or `resume`.
4. You confirm the default projects root.
5. Your selected project groups are activated and kickoff artifacts are emitted.

## Terminal vs Codex

| Place | Purpose |
| --- | --- |
| Terminal | Manage project/session state through `agents-inc` commands. |
| Codex chat | Run orchestration conversation, router calls, and cross-group planning. |

Terminal keeps the state grounded.

Codex carries the reasoning and orchestration flow.

## First Session: Start New or Resume

This is your first decision at startup.

Pick the path that matches your project momentum.

### Path A: Start New

Run in Terminal:

```bash
agents-inc init --mode new
```

Or use fully interactive mode:

```bash
agents-inc init
```

You will choose:

- projects root (saved in `~/.agents-inc/config.yaml`)
- project id
- task
- timeline
- compute target (`cpu`, `gpu`, or `cuda`)
- remote cluster usage (`yes` or `no`)
- output target
- active groups (recommended list is editable)

### Path B: Resume Existing

Run in Terminal:

```bash
agents-inc list
agents-inc resume <project-id>
```

Use this path when you already have project state and want to continue with continuity.

### Generated Project Artifacts

After activation, your project root includes:

- `kickoff.md`
- `router-call.txt`
- `project-manifest.yaml`

These are your immediate handoff files for session continuity.

## Daily Operating Loop

Use this rhythm for day-to-day work.

1. Activate or resume the project in Terminal.
2. Paste the router call into Codex.
3. Let group heads coordinate specialists.
4. Review exposed outputs and decide next objective.
5. Pause safely at any point and resume later.

This keeps motion steady without mixing project boundaries.

### Canonical Router Call

Use this pattern inside Codex:

```text
Use $research-router for project <project-id> group <group-id>: <objective>.
```

By default, you interact with group-level results.

Specialist internals remain private unless you intentionally use audit behavior.

## Sessions at a Glance

List sessions in Terminal:

```bash
agents-inc list
```

Machine-readable listing:

```bash
agents-inc list --json
```

Fields you should expect:

- `project_id`
- `session_code`
- `active_groups`
- `project_root`
- `last_checkpoint`
- `updated_at`
- `status`

This gives you a quick map of live, paused, and stale project contexts.

## Resume After Restart

Resume from Terminal:

```bash
agents-inc resume <project-id>
```

Optional controls:

```bash
agents-inc resume <project-id> --checkpoint latest --resume-mode auto
```

How resume source is selected:

- `auto`: tries compact snapshot first, then checkpoint rehydrate.
- `compact`: use compacted state only.
- `rehydrate`: rebuild from checkpoint record.

Your existing artifacts stay in place unless you explicitly use overwrite behavior during project creation.

## Recover a Specific Checkpoint

Run in Terminal:

```bash
agents-inc resume <project-id> --checkpoint <checkpoint-id> --resume-mode rehydrate
```

Use this when you want to return to a precise earlier decision frame.

## Working Contract for Group Boundaries

Treat these rules as operational guardrails.

1. Specialists write only to their own internal scope:
   `agent-groups/<group>/internal/<specialist>/...`
2. Group heads publish shared outputs only to:
   `agent-groups/<group>/exposed/...`
3. Cross-group consumption is from another group's `exposed/` path only.
4. Group internals are not a shared exchange channel.
5. Keep each project isolated from every other project, even when group names overlap.

This contract preserves clean collaboration and clear ownership of artifacts.

## Lean Command Reference

Run these in Terminal.

| Command | Use |
| --- | --- |
| `agents-inc init` | Start onboarding for a new or resumed project flow. |
| `agents-inc list` | Show resumable project sessions. |
| `agents-inc resume <project-id>` | Reopen orchestration context for one project. |
| `agents-inc dispatch --project-id <id> --group <group-id> --objective "<objective>"` | Build deterministic dispatch plan for an objective. |
| `agents-inc docs --include-generated-projects` | Generate full inlined reference docs. |

## Legacy Aliases in v1.2.x

Legacy `agents-inc-*` commands remain available in `v1.2.x` with deprecation notices.

Use `agents-inc <subcommand>` as the primary interface moving forward.

## Where State Lives

Global files:

- `~/.agents-inc/config.yaml`
- `~/.agents-inc/projects-index.yaml`

Project-local state:

- `<project-root>/.agents-inc/state/session-state.yaml`
- `<project-root>/.agents-inc/state/latest-checkpoint.yaml`
- `<project-root>/.agents-inc/state/checkpoints/<checkpoint-id>.yaml`
- `<project-root>/.agents-inc/state/latest-compacted.yaml`
- `<project-root>/.agents-inc/state/compacted/<compact-id>.yaml`
- `<project-root>/.agents-inc/state/group-sessions.yaml`

Keep these files intact for reliable resume behavior.

## Troubleshooting

### `agents-inc` command not found

Install or repair the package in your active Python environment.

Then retry:

```bash
agents-inc --help
```

### Project does not appear in `agents-inc list`

Run scan-enabled listing:

```bash
agents-inc list --include-stale
```

If needed, point to your known root:

```bash
agents-inc list --scan-root ~/codex-projects
```

### Stale project index entry

If a project path moved or no longer exists, it may appear as `stale`.

Use `--include-stale` to inspect it and then resume the correct active project id.

### Resume from a known checkpoint id

If `latest` is not the context you want, pin a checkpoint:

```bash
agents-inc resume <project-id> --checkpoint <checkpoint-id> --resume-mode rehydrate
```

## Assumptions and Defaults

- Release tag in this guide: `v1.2.0`.
- `codex` CLI is available on your PATH.
- Default projects root is `~/codex-projects` unless you change it.
- Visibility default is group-only output exposure.
- Audit-style specialist detail is optional and explicit.

## Start Here

If you are beginning now,
run the quick-start command,
choose `new` or `resume`,
and keep your work in one project rhythm at a time.

The system is built to preserve continuity,
so your research flow can stay focused,
clear,
and resumable.
