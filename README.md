# agents-inc

Publication-ready multi-agent group fabric for Codex sessions with restart-safe orchestration state.

## Quick Start (Pinned Bootstrap v1.1.0)

Paste this in a brand-new Codex session:

```bash
export AGI_VER="v1.1.0" && \
curl -sfL "https://github.com/sacRedeeRhoRn/agents-inc/releases/download/${AGI_VER}/bootstrap.sh" -o /tmp/agents-inc-bootstrap.sh && \
curl -sfL "https://github.com/sacRedeeRhoRn/agents-inc/releases/download/${AGI_VER}/bootstrap.sh.sha256" -o /tmp/agents-inc-bootstrap.sh.sha256 && \
(cd /tmp && shasum -a 256 -c agents-inc-bootstrap.sh.sha256) && \
bash /tmp/agents-inc-bootstrap.sh --owner sacRedeeRhoRn --repo agents-inc --release "${AGI_VER}"
```

Bootstrap does:
1. Downloads pinned release artifacts.
2. Verifies checksum.
3. Installs `agents-inc`.
4. Starts intake wizard (`agents-inc-init-session`).
5. Intake asks `new` or `resume`.

## First Session: New vs Resume

Run interactively:

```bash
agents-inc-init-session --mode ask
```

Modes:
- `new`: create project bundle and install router/head skills.
- `resume`: restore from checkpoint for existing project.

Non-interactive:

```bash
agents-inc-init-session --mode new --non-interactive ...
agents-inc-init-session --mode resume --resume-project-id <project-id>
```

## Project Lifecycle

### 1) Start or Resume Project
- Default root: `~/codex-projects/<project-id>`
- Local fabric root: `~/codex-projects/<project-id>/agent_group_fabric`

### 2) Use Router Command
Generated file:
- `router-call.txt`

Pattern:

```text
Use $research-router for project <project-id> group <group-id>: <objective>.
```

### 3) Dry-Run Dispatch (Optional)

```bash
agents-inc-dispatch-dry-run \
  --fabric-root ~/codex-projects/<project-id>/agent_group_fabric \
  --project-id <project-id> \
  --group <group-id> \
  --objective "<objective>"
```

### 4) Validate Full Multi-Group Interaction

```bash
agents-inc-long-run-test \
  --fabric-root ~/codex-projects/<project-id>/agent_group_fabric \
  --project-id <project-id> \
  --task "Film thickness dependent polymorphism stability of metastable phase" \
  --groups all \
  --duration-min 75 \
  --strict-isolation hard-fail \
  --run-mode local-sim \
  --seed 20260301
```

### 5) Continue in Later Sessions
- Re-run bootstrap or call `agents-inc-init-session`.
- Choose `resume`.
- Paste regenerated `router-call.txt`.

## Resume After Shutdown / Reboot

Global resume index:
- `~/.agents-inc/projects-index.yaml`

Project state files:
- `<project-root>/.agents-inc/state/session-state.yaml`
- `<project-root>/.agents-inc/state/latest-checkpoint.yaml`
- `<project-root>/.agents-inc/state/checkpoints/<checkpoint-id>.yaml`

Quick resume:

```bash
agents-inc-init-session --mode resume --resume-project-id <project-id>
```

## Recover Specific Checkpoint

```bash
agents-inc-init-session \
  --mode resume \
  --resume-project-id <project-id> \
  --resume-checkpoint <checkpoint-id>
```

`new` mode is non-destructive by default:
- interactive: asks `resume/overwrite/cancel` if project exists
- non-interactive: fails unless `--overwrite-existing`

## List All Sessions

List every resumable project session:

```bash
agents-inc-list-sessions
```

Machine-readable output:

```bash
agents-inc-list-sessions --json
```

Include stale entries:

```bash
agents-inc-list-sessions --include-stale
```

## Artifact Isolation Rules

- Specialist write: only `agent-groups/<group>/internal/<specialist>/...`
- Head write: only `agent-groups/<group>/exposed/...`
- Cross-group read: only `agent-groups/<other-group>/exposed/...`
- Any cross-group internal access: violation (`exit 2` in long-run validator)

## How Groups Interact

Default full graph uses 9 groups:
- material-scientist
- material-engineer
- developer
- designer
- data-curation
- literature-intelligence
- quality-assurance
- publication-packaging
- atomistic-hpc-simulation

Execution model:
- Head controller coordinates specialist subtasks.
- Independent branches run in parallel by phase.
- Dependent branches run sequentially by dependency graph.
- Only exposed artifacts cross group boundaries.

## Core Commands

```bash
agents-inc-new-group --group-id <id> --display-name "<name>" --domain "<domain>"
agents-inc-new-project --project-id <id> --groups g1,g2 --profile <profile>
agents-inc-install-skills --project-id <id> --sync
agents-inc-dispatch-dry-run --project-id <id> --group <group> --objective "<objective>"
agents-inc-list-sessions
agents-inc-sync-overlays --project-id <id> --from-template-version 1.0.0
agents-inc-validate --all
agents-inc-generate-docs --include-generated-projects
agents-inc-long-run-test --project-id <id> --groups all --duration-min 75
```

## Troubleshooting

Long-run exit codes:

| Exit Code | Meaning | Action |
|---|---|---|
| `0` | Pass | Review `final-report.md` / `final-report.json`. |
| `2` | Isolation violation | Inspect `violations.json` and `access-ledger.ndjson`. |
| `3` | Lease contention unresolved | Check `lease-events.ndjson`, tune retries/backoff/conflict-rate. |
| `4` | Interaction coverage insufficient | Inspect `coverage.json` for missing edges. |
| `5` | Quality gate failure threshold exceeded | Inspect blocked gate events and exposed payloads. |

Resume issues:
- If resume cannot find project, verify `~/.agents-inc/projects-index.yaml`.
- If index entry points to deleted path, status is marked `stale`.
- Fallback scan checks `~/codex-projects`.

## Documentation

- Intro: [docs/INTRODUCTION.md](docs/INTRODUCTION.md)
- Session intake: `src/agents_inc/docs/internal/session-intake.md`
- Session resume: `src/agents_inc/docs/internal/session-resume.md`
- Full generated template/skill reference:
  `docs/generated/full-template-skill-reference.md`

## Development

```bash
cd /Users/moon.s.june/Documents/Playground/agent_group_fabric
pip install -e .
agents-inc-validate --all
python3 -m unittest discover -s tests -v
```
