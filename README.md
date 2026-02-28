# agents-inc

Publication-ready multi-agent orchestration fabric for Codex sessions, with resume-safe checkpoints and strict project-level artifact isolation.

## Terminal vs Codex
- `Terminal`: run shell commands.
- `Codex session`: chat with Codex in an interactive session.

## Quick Start (Markdown-Driven, v1.2.0)
Run this in `Terminal`:

```bash
export AGI_VER="v1.2.0" && \
codex -C "$HOME" "$(curl -sfL "https://raw.githubusercontent.com/sacRedeeRhoRn/agents-inc/${AGI_VER}/docs/bootstrap/START_IN_CODEX.md")"
```

What this does:
1. Starts a new Codex session with the onboarding prompt.
2. Guides install/check of `agents-inc`.
3. Asks `new` vs `resume`.
4. Asks/sets projects root default.
5. Activates groups for the selected project.

## Primary Commands (Terminal)

```bash
agents-inc init
agents-inc list
agents-inc resume <project-id>
agents-inc dispatch --project-id <id> --group <group-id> --objective "<objective>"
agents-inc long-run --project-id <id> --groups all --duration-min 75
agents-inc validate --all
agents-inc docs --include-generated-projects
```

## Start a New Project
Run in `Terminal`:

```bash
agents-inc init --mode new
```

The wizard asks:
- projects root (saved to `~/.agents-inc/config.yaml`)
- project id
- task and constraints
- recommended groups (editable)

Generated in project root:
- `kickoff.md`
- `router-call.txt`
- `long-run-command.sh`
- `project-manifest.yaml`

## List All Sessions
Run in `Terminal`:

```bash
agents-inc list
```

JSON output:

```bash
agents-inc list --json
```

Includes:
- `project_id`
- `session_code`
- `active_groups`
- `project_root`
- `last_checkpoint`
- `updated_at`
- `status`

## Resume After Shutdown/Reboot
Run in `Terminal`:

```bash
agents-inc resume <project-id>
```

Optional resume controls:

```bash
agents-inc resume <project-id> --checkpoint latest --resume-mode auto
```

Behavior:
- Restores context from compact snapshot first (`auto`), then falls back to checkpoint rehydrate.
- Regenerates `kickoff.md` and `router-call.txt`.
- Launches a fresh Codex session in the same terminal at project root (unless `--no-launch`).

## Restore Specific Checkpoint
Run in `Terminal`:

```bash
agents-inc resume <project-id> --checkpoint <checkpoint-id> --resume-mode rehydrate
```

## Where State Is Stored
Global:
- `~/.agents-inc/config.yaml`
- `~/.agents-inc/projects-index.yaml`

Per project:
- `<project-root>/.agents-inc/state/session-state.yaml`
- `<project-root>/.agents-inc/state/latest-checkpoint.yaml`
- `<project-root>/.agents-inc/state/checkpoints/<checkpoint-id>.yaml`
- `<project-root>/.agents-inc/state/latest-compacted.yaml`
- `<project-root>/.agents-inc/state/compacted/<compact-id>.yaml`
- `<project-root>/.agents-inc/state/group-sessions.yaml`

## Group Interaction and Isolation
- Specialists write only to `agent-groups/<group>/internal/<specialist>/...`.
- Group heads publish only to `agent-groups/<group>/exposed/...`.
- Cross-group reads are allowed only from another group’s `exposed/`.
- Cross-group internal reads/writes are violations.

## Validate Full 9-Group Interaction
Run in `Terminal`:

```bash
agents-inc long-run \
  --fabric-root ~/codex-projects/<project-id>/agent_group_fabric \
  --project-id <project-id> \
  --task "Film thickness dependent polymorphism stability of metastable phase" \
  --groups all \
  --duration-min 75 \
  --strict-isolation hard-fail \
  --run-mode local-sim \
  --seed 20260301
```

Exit codes:
- `0` pass
- `2` isolation violation
- `3` unresolved lease contention
- `4` insufficient interaction coverage
- `5` quality-gate exposure failure

## Legacy Alias Commands (`v1.2.x` only)
Old `agents-inc-*` command names still work with deprecation warnings for one release line. Migrate to `agents-inc <subcommand>`.

## Development
Run in `Terminal`:

```bash
cd /Users/moon.s.june/Documents/Playground/agent_group_fabric
pip install -e .
agents-inc validate --all
python3 -m unittest discover -s tests -v
```
