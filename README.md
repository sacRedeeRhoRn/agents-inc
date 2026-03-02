# agents-inc

`agents-inc` is a project-scoped multi-agent orchestration fabric for Codex.

You define the objective. Group heads coordinate specialists. The session keeps continuity, so you can stop, reboot, and resume without losing project rhythm.

## Quick Start (Codex Orchestrator, v3.1.2)

Run this in Terminal:

```bash
export AGI_VER="v3.1.2" && \
export AGI_BOOTSTRAP_URL="https://raw.githubusercontent.com/sacRedeeRhoRn/agents-inc/${AGI_VER}/docs/bootstrap/START_IN_CODEX.md" && \
export AGI_BOOTSTRAP_HOME="$HOME/.agents-inc/bootstrap-codex-home" && \
mkdir -p "$AGI_BOOTSTRAP_HOME/skills/local" && \
[ -f "$HOME/.codex/auth.json" ] && ln -snf "$HOME/.codex/auth.json" "$AGI_BOOTSTRAP_HOME/auth.json" || true && \
[ -f "$HOME/.codex/config.toml" ] && ln -snf "$HOME/.codex/config.toml" "$AGI_BOOTSTRAP_HOME/config.toml" || true && \
AGI_BOOTSTRAP_MD="$(mktemp /tmp/agents-inc-start.XXXXXX)" && \
curl -fsSL "$AGI_BOOTSTRAP_URL" -o "$AGI_BOOTSTRAP_MD" && \
test -s "$AGI_BOOTSTRAP_MD" && \
CODEX_HOME="$AGI_BOOTSTRAP_HOME" codex -C "$HOME" "$(cat "$AGI_BOOTSTRAP_MD")"
```

The first prompt should immediately ask:

`Start new project or resume existing project?`

## Install In Terminal

Use a release-pinned, checksum-verified install:

```bash
export AGI_VER="v3.1.2" && \
WHEEL="agents_inc-3.1.2-py3-none-any.whl" && \
curl -sfL "https://github.com/sacRedeeRhoRn/agents-inc/releases/download/${AGI_VER}/${WHEEL}" -o "/tmp/${WHEEL}" && \
curl -sfL "https://github.com/sacRedeeRhoRn/agents-inc/releases/download/${AGI_VER}/agents_inc-3.1.2.sha256" -o /tmp/agents_inc-3.1.2.sha256 && \
(cd /tmp && grep "  ${WHEEL}$" agents_inc-3.1.2.sha256 > wheel.sha256 && shasum -a 256 -c wheel.sha256) && \
python3 -m pip install --upgrade pip setuptools wheel && \
python3 -m pip install --upgrade "/tmp/${WHEEL}"
```

## Terminal vs Codex

| Place | Purpose |
| --- | --- |
| Terminal | Install, init/resume, session listing, skill activation, dispatch commands. |
| Codex session | Orchestration conversation and group-routed reasoning. |

Terminal anchors state. Codex drives orchestration.

## Session Commands

```bash
agents-inc init
agents-inc list
agents-inc resume <project-id>
agents-inc project-groups list --project-id <project-id>
agents-inc project-groups add --project-id <project-id> --groups <group-id>
agents-inc project-groups remove --project-id <project-id> --groups <group-id>
agents-inc deactivate <project-id>
agents-inc delete <project-id> --yes
agents-inc cleanup-projects --all-indexed --yes
agents-inc orchestrator-reply --project-id <project-id> --message "<objective>" --live-profile bounded --require-negotiation true
```

`agents-inc list` now shows only:
- `project_id`
- `status`
- `root`

## Project-Scoped Skills

Default behavior:
- active group heads are installed
- specialists stay off until explicitly enabled

Enable specialists only for selected groups:

```bash
agents-inc skills activate --project-id <project-id> --groups <group-id> --specialists
```

Clean old globally-managed skills safely (managed entries only):

```bash
agents-inc skills cleanup-global --dry-run
agents-inc skills cleanup-global --apply
```

## Full Guide

See [OVERVIEW.md](./OVERVIEW.md) for the full operator journey, including:
- installation and bootstrap details
- project lifecycle and artifact map
- complete metastable chiral silicide example run
- resume and checkpoint workflow

## Orchestrator Contract

Group-routed turns are strict and artifact-grounded:
- all active project groups must publish valid `exposed/handoff.json` contributions
- orchestration runs iterative cooperative cycles (delegate -> group meeting -> refine -> re-delegate)
- group mode requires the meeting loop and non-zero cycle budget
- per-agent timeout is unlimited by default (`--agent-timeout-sec` omitted or `0`)
- use `--agent-timeout-sec <seconds>` only when you explicitly want bounded agent sessions
- final answer is emitted only on pass
- otherwise, the turn returns `blocked-report.md` and `blocked-reasons.json`
- successful turns save:
  - `final/full-report.md`
  - `final/full-report.json`
  - `final/key-points.txt` (also printed in terminal)
  - turn-root latest pointers for polling:
    - `wait-state.latest.json`
    - `cooperation-ledger.latest.ndjson`
    - `group-head-sessions.latest.json`
    - `specialist-sessions.latest.json`

## References

- Bootstrap prompt: [docs/bootstrap/START_IN_CODEX.md](./docs/bootstrap/START_IN_CODEX.md)
- Deep operator guide: [OVERVIEW.md](./OVERVIEW.md)
- Session intake internals: [src/agents_inc/docs/internal/session-intake.md](./src/agents_inc/docs/internal/session-intake.md)
- Session resume internals: [src/agents_inc/docs/internal/session-resume.md](./src/agents_inc/docs/internal/session-resume.md)
- Session compaction internals: [src/agents_inc/docs/internal/session-compaction.md](./src/agents_inc/docs/internal/session-compaction.md)
- GitHub repository: [sacRedeeRhoRn/agents-inc](https://github.com/sacRedeeRhoRn/agents-inc)
- Releases: [github.com/sacRedeeRhoRn/agents-inc/releases](https://github.com/sacRedeeRhoRn/agents-inc/releases)
