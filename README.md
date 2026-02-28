# agents-inc

`agents-inc` is a project-scoped multi-agent orchestration fabric for Codex.

It is built for long work with continuity: you can pause, shut down, return, and keep moving from stable session state.

You set intent. Group heads coordinate specialists. Exposed artifacts stay clear and calm.

## Quick Start (Markdown-Driven, v2.1.0)

Run this in Terminal:

```bash
export AGI_VER="v2.1.0" && \
export AGI_BOOTSTRAP_URL="https://raw.githubusercontent.com/sacRedeeRhoRn/agents-inc/${AGI_VER}/docs/bootstrap/START_IN_CODEX.md" && \
AGI_BOOTSTRAP_MD="$(mktemp /tmp/agents-inc-start.XXXXXX)" && \
curl -fsSL "$AGI_BOOTSTRAP_URL" -o "$AGI_BOOTSTRAP_MD" && \
test -s "$AGI_BOOTSTRAP_MD" && \
codex -C "$HOME" "$(cat "$AGI_BOOTSTRAP_MD")"
```

### What Happens Next

1. Codex opens with the onboarding prompt.
2. The prompt confirms `agents-inc` availability.
3. You choose `new` or `resume`.
4. You confirm your default projects root.
5. You activate project groups and receive kickoff artifacts.

## Terminal vs Codex

| Place | Purpose |
| --- | --- |
| Terminal | Manage project/session state and catalog commands. |
| Codex chat | Run orchestration conversation and router-driven coordination. |

Terminal anchors state.

Codex carries orchestration reasoning.

## First Session: Start New or Resume

### Path A: Start New

```bash
agents-inc init --mode new
```

Or interactive:

```bash
agents-inc init
```

You will choose:

- projects root (saved in `~/.agents-inc/config.yaml`)
- project id
- task and constraints
- active groups (recommended, editable)

### Path B: Resume Existing

```bash
agents-inc list
agents-inc resume <project-id>
```

Resume preserves project context and continues from compact/checkpoint state.

### Generated Project Artifacts

- `kickoff.md`
- `router-call.txt`
- `project-manifest.yaml`

## Daily Operating Loop

1. Activate or resume from Terminal.
2. Paste the router call into Codex.
3. Let group heads coordinate specialist execution.
4. Review exposed outputs.
5. Continue with next objective or pause safely.

### Canonical Router Call

```text
Use $research-router for project <project-id> group <group-id>: <objective>.
```

By default, interaction is group-level.

Specialist artifacts remain internal unless you explicitly enable audit-level inspection.

## Request Mode Contract

`agents-inc` enforces strict request mode parsing per turn:

- Message starts with `[non-group]`: concise direct response, no group delegation.
- Any other message: group-routed orchestration with publication-grade detailed synthesis.

Run per-turn orchestration from Terminal:

```bash
agents-inc orchestrator-reply --project-id <project-id> --message "<your request>"
```

For direct state lookups:

```bash
agents-inc orchestrator-reply --project-id <project-id> --message "[non-group] Bring session id of web-search specialist of polymorphism researcher dangled to current project."
```

## Evidence Campaign (Live Orchestrator Session)

Run a full evidence-first orchestrator session with transcript capture, 12+ intake Q/A, multi-group checks, and a final report:

```bash
agents-inc orchestrate \
  --fabric-root /Users/moon.s.june/Documents/Playground/agent_group_fabric \
  --project-id proj-cosi-polymorphism \
  --task "want to synthesize low resistivity topological semimetal cobalt silicide film and design procedure with computational methods like DFT, MD, FEM" \
  --create-group polymorphism-researcher \
  --group-selection recommended \
  --questions-min 12 \
  --self-qa router-self \
  --live-codex \
  --codex-web-search \
  --report-root /Users/moon.s.june/agents-inc-local-runs \
  --until-pass
```

The run writes:

- `run-config.yaml`
- `session.raw.log`
- `session.redacted.log`
- `qa/questions.yaml`
- `qa/answers.yaml`
- `qa/qa-transcript.md`
- `plan/complete-film-synthesis-plan.md`
- `events.ndjson`
- `access-ledger.ndjson`
- `group-matrix.json`
- `refinement-history.md`
- `REPORT.md`
- `REPORT.json`

`plan/complete-film-synthesis-plan.md` includes:
- synthesis DOE
- DFT/MD/FEM workflow
- anticipated resistivity-vs-thickness table
- web evidence snapshot with source URLs

If live Codex web execution times out, orchestration falls back automatically to the built-in web evidence planner and still completes.

Regenerate report from a prior run directory:

```bash
agents-inc orchestrate-report --run-dir <run-dir>
```

## Catalog Groups (Reusable, Not Project-Bound)

List all catalog groups:

```bash
agents-inc groups list
```

Machine-readable:

```bash
agents-inc groups list --json
```

Show a specific group:

```bash
agents-inc groups show <group-id>
```

Create a new group with codex-session-friendly wizard:

```bash
agents-inc groups new --interactive
```

Template/archetype info:

```bash
agents-inc groups templates
```

## Sessions at a Glance

```bash
agents-inc list
```

```bash
agents-inc list --json
```

Fields include:

- `project_id`
- `session_code`
- `active_groups`
- `project_root`
- `last_checkpoint`
- `updated_at`
- `status`

## Resume After Restart

```bash
agents-inc resume <project-id>
```

Optional:

```bash
agents-inc resume <project-id> --checkpoint latest --resume-mode auto
```

Resume behavior:

- `auto`: compact snapshot first, then checkpoint rehydrate.
- `compact`: compact source only.
- `rehydrate`: checkpoint source only.

## Recover a Specific Checkpoint

```bash
agents-inc resume <project-id> --checkpoint <checkpoint-id> --resume-mode rehydrate
```

## Migration to v2 (Hard Cutover)

`v2.1.0` uses strict schema contracts.

If existing artifacts are from earlier schema versions, migrate before normal operations:

```bash
agents-inc migrate-v2 --fabric-root <path> --project-index <path> --dry-run
agents-inc migrate-v2 --fabric-root <path> --project-index <path> --apply
```

Optional backup target:

```bash
agents-inc migrate-v2 --apply --backup-dir <path>
```

## Working Contract for Artifact Boundaries

1. Specialists write only to:
   `agent-groups/<group>/internal/<specialist>/...`
2. Heads publish shared results only to:
   `agent-groups/<group>/exposed/...`
3. Cross-group reads are from `exposed/` only.
4. Cross-group internal reads/writes are not allowed.
5. Keep each project isolated, even when group names overlap.

## Lean Command Reference

Run these in Terminal:

| Command | Use |
| --- | --- |
| `agents-inc --version` | Show runtime package version. |
| `agents-inc init` | Start new/resume intake flow. |
| `agents-inc list` | List resumable project sessions. |
| `agents-inc resume <project-id>` | Resume orchestration context for one project. |
| `agents-inc groups list` | List reusable catalog groups. |
| `agents-inc groups show <group-id>` | Show one catalog group contract. |
| `agents-inc groups new --interactive` | Create a reusable catalog group with user-confirmed specialists. |
| `agents-inc orchestrator-reply --project-id <id> --message "<request>"` | Execute one orchestrator turn with strict mode split (`group-detailed` by default, `[non-group]` for concise direct queries). |
| `agents-inc orchestrate ...` | Run live orchestrator campaign with web-enabled intake, complete film-plan artifact, and report bundle. |
| `agents-inc orchestrate-report --run-dir <run-dir>` | Regenerate report from existing run artifacts. |
| `agents-inc dispatch --project-id <id> --group <group-id> --objective "<objective>"` | Build deterministic dispatch plan. |
| `agents-inc docs --include-generated-projects` | Generate full inlined reference docs. |
| `agents-inc migrate-v2 --dry-run|--apply` | Upgrade older artifacts to strict v2 schema. |

## Legacy Aliases in v2.1.x

Legacy `agents-inc-*` aliases still run with deprecation warnings during the compatibility window.

Canonical interface is `agents-inc <subcommand>`.

## Where State Lives

Global:

- `~/.agents-inc/config.yaml`
- `~/.agents-inc/projects-index.yaml`

Project-local:

- `<project-root>/.agents-inc/state/session-state.yaml`
- `<project-root>/.agents-inc/state/latest-checkpoint.yaml`
- `<project-root>/.agents-inc/state/checkpoints/<checkpoint-id>.yaml`
- `<project-root>/.agents-inc/state/latest-compacted.yaml`
- `<project-root>/.agents-inc/state/compacted/<compact-id>.yaml`
- `<project-root>/.agents-inc/state/group-sessions.yaml`
- `<project-root>/.agents-inc/state/specialist-sessions.yaml`
- `<project-root>/.agents-inc/state/response-policy.yaml`
- `<project-root>/.agents-inc/state/resume-prompt.md`

## Troubleshooting

### `agents-inc` command not found

Install in the active Python environment, then retry:

```bash
agents-inc --help
```

### Project missing from session list

```bash
agents-inc list --include-stale
agents-inc list --scan-root ~/codex-projects
```

### Stale index entry

Use `--include-stale` to inspect stale entries, then resume the active project id.

### Resume from a known checkpoint

```bash
agents-inc resume <project-id> --checkpoint <checkpoint-id> --resume-mode rehydrate
```

### Schema-version errors after upgrade

Run migration:

```bash
agents-inc migrate-v2 --dry-run
agents-inc migrate-v2 --apply
```

## Assumptions and Defaults

- Release tag in this guide: `v2.1.0`.
- `codex` CLI is available on PATH.
- Default projects root: `~/codex-projects` unless changed.
- Default visibility: group-only exposed artifacts.
- Locking mode default for dispatch: `auto`.

## Start Here

Run the quick-start command, choose `new` or `resume`, and keep one project rhythm at a time.

The platform is designed to preserve continuity while keeping group boundaries clean.
