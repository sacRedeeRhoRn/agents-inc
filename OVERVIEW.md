# agents-inc Overview

## 1. Introduction

`agents-inc` turns one Codex workspace into a project-stable orchestration system.

You work through group heads. Specialists execute in narrow scopes. Shared outputs flow through exposed artifacts only. That separation keeps your project calm under long timelines, concurrent objectives, and repeated restarts.

If you close your laptop today and return next week, the project state is still there: checkpoints, compact snapshots, group sessions, activation state, and router context.

## 2. Installation (Terminal-Managed)

### Preflight

```bash
python3 --version
codex --version
git --version
```

### Recommended Install (Release-Pinned + Checksum)

```bash
export AGI_VER="v4.0.0" && \
WHEEL="agents_inc-4.0.0-py3-none-any.whl" && \
curl -sfL "https://github.com/sacRedeeRhoRn/agents-inc/releases/download/${AGI_VER}/${WHEEL}" -o "/tmp/${WHEEL}" && \
curl -sfL "https://github.com/sacRedeeRhoRn/agents-inc/releases/download/${AGI_VER}/agents_inc-4.0.0.sha256" -o /tmp/agents_inc-4.0.0.sha256 && \
(cd /tmp && grep "  ${WHEEL}$" agents_inc-4.0.0.sha256 > wheel.sha256 && shasum -a 256 -c wheel.sha256) && \
python3 -m pip install --upgrade pip setuptools wheel && \
python3 -m pip install --upgrade "/tmp/${WHEEL}"
```

### Verify Install

```bash
agents-inc --version
agents-inc --help
```

Expected version for this guide: `4.0.0`.

## 3. Start Your Codex Orchestrator Session

Run this in Terminal to open a new Codex session with the onboarding markdown prompt:

```bash
export AGI_VER="v4.0.0" && \
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

### What you should see in the first 10 seconds

1. The first question appears immediately:
   `Start new project or resume existing project?`
2. No pre-check command output appears before that question.

### If it looks idle

```bash
# inside the Codex session
/status
```

If needed, relaunch with:

```bash
CODEX_HOME="$AGI_BOOTSTRAP_HOME" codex --no-alt-screen -C "$HOME" "$(cat "$AGI_BOOTSTRAP_MD")"
```

## 4. Project Lifecycle

## 4.1 Create or resume

```bash
agents-inc init
agents-inc list
agents-inc resume <project-id>
```

## 4.2 Activate specialist skills only when needed

By default, only head skills for active groups are installed.

```bash
agents-inc skills activate --project-id <project-id> --groups <group-id> --specialists
```

Deactivate when you want a tighter active surface:

```bash
agents-inc skills deactivate --project-id <project-id> --groups <group-id>
```

## 4.2.1 Expand or shrink project groups

```bash
agents-inc project-groups list --project-id <project-id>
agents-inc project-groups add --project-id <project-id> --groups <group-id>
agents-inc project-groups create --project-id <project-id> --group-id <new-id> --display-name "<name>" --domain "<domain>"
agents-inc project-groups remove --project-id <project-id> --groups <group-id>
```

## 4.3 Dispatch or reply

```bash
agents-inc dispatch --project-id <project-id> --group <group-id> --objective "<objective>"
agents-inc orchestrator-reply --project-id <project-id> --message "<message>" --live-profile bounded --require-negotiation true
agents-inc cleanup-projects --all-indexed --yes
```

Timeout semantics:
- omit `--agent-timeout-sec` for unlimited per-agent runtime
- pass `--agent-timeout-sec 0` for unlimited explicitly
- pass `--agent-timeout-sec <seconds>` only when you want bounded sessions
- use `--abort-file <path>` or Ctrl+C for manual stop

## 4.4 State and artifacts

Core outputs:
- `<project-root>/kickoff.md`
- `<project-root>/router-call.txt`
- `<project-root>/project-manifest.yaml`

Persistent state:
- `<project-root>/.agents-inc/state/session-state.yaml`
- `<project-root>/.agents-inc/state/latest-checkpoint.yaml`
- `<project-root>/.agents-inc/state/checkpoints/<checkpoint-id>.yaml`
- `<project-root>/.agents-inc/state/latest-compacted.yaml`
- `<project-root>/.agents-inc/state/compacted/<compact-id>.yaml`
- `<project-root>/.agents-inc/state/response-policy.yaml`
- `<project-root>/.agents-inc/state/specialist-sessions.yaml`
- `<project-root>/.agents-inc/state/codex-home.yaml`
- `<project-root>/.agents-inc/state/skill-activation.yaml`

Turn artifacts:
- `<project-root>/.agents-inc/turns/<turn-id>/request.txt`
- `<project-root>/.agents-inc/turns/<turn-id>/delegation-ledger.json`
- `<project-root>/.agents-inc/turns/<turn-id>/negotiation-sequence.md`
- `<project-root>/.agents-inc/turns/<turn-id>/group-evidence-index.json`
- `<project-root>/.agents-inc/turns/<turn-id>/cycles/cycle-0001/...` (runtime artifacts per cycle)
- `<project-root>/.agents-inc/turns/<turn-id>/wait-state.latest.json` (latest cycle pointer)
- `<project-root>/.agents-inc/turns/<turn-id>/cooperation-ledger.latest.ndjson` (latest cycle pointer)
- `<project-root>/.agents-inc/turns/<turn-id>/group-head-sessions.latest.json` (latest cycle pointer)
- `<project-root>/.agents-inc/turns/<turn-id>/specialist-sessions.latest.json` (latest cycle pointer)
- `<project-root>/.agents-inc/turns/<turn-id>/final/full-report.md` (pass only)
- `<project-root>/.agents-inc/turns/<turn-id>/final/full-report.json` (pass only)
- `<project-root>/.agents-inc/turns/<turn-id>/final/key-points.txt` (printed in terminal)
- `<project-root>/.agents-inc/turns/<turn-id>/final-exposed-answer.md` (compat pass path)
- `<project-root>/.agents-inc/turns/<turn-id>/final-answer-quality.json`
- `<project-root>/.agents-inc/turns/<turn-id>/blocked-report.md` (block path)
- `<project-root>/.agents-inc/turns/<turn-id>/blocked-reasons.json` (block path)

## 5. Example Task Run (Domain-Agnostic Service Delivery)

Objective theme:
- plan and deliver a cross-functional professional services objective
- combine implementation, evidence collection, QA, data support, integration, and stakeholder communication
- produce a publication-grade final response with explicit evidence and risks

### 5.1 Start a new project

```bash
agents-inc init --mode new
```

Choose or confirm groups including at least:
- `developer`
- `quality-assurance`
- `literature-intelligence`
- `data-curation`
- `integration-delivery`
- `design-communication`

### 5.2 Activate specialists for selected groups

```bash
agents-inc skills activate --project-id <project-id> --groups developer,integration-delivery --specialists
```

### 5.3 Run a publication-grade orchestrator turn

```bash
agents-inc orchestrator-reply --project-id <project-id> --message "Plan an end-to-end service delivery workflow for a high-priority client objective. Include evidence collection, implementation sequencing, QA checkpoints, integration gates, stakeholder communication outputs, and explicit risk controls." --live-profile bounded --require-negotiation true
```

### 5.4 Push concrete objectives into developer and integration groups

```bash
agents-inc dispatch --project-id <project-id> --group developer --objective "Implement automation and reproducible tooling for the objective workflow, with clear commands, artifact outputs, and operational safeguards."

agents-inc dispatch --project-id <project-id> --group integration-delivery --objective "Integrate cross-group outputs into a staged delivery plan with dependency checks, release gates, and rollback strategy."
```

### 5.5 Run a concise state query with strict non-group mode

```bash
agents-inc orchestrator-reply --project-id <project-id> --message "[non-group] List specialist session IDs currently active for this project."
```

### 5.6 Confirm session and resume readiness

```bash
agents-inc list
agents-inc resume <project-id>
```

## 6. Resume After Shutdown

After restart:

```bash
agents-inc list
agents-inc resume <project-id>
```

Default resume mode is `auto`:
- tries compact snapshot first
- falls back to checkpoint rehydrate if compact is unavailable

Resume with explicit checkpoint:

```bash
agents-inc resume <project-id> --checkpoint <checkpoint-id> --resume-mode rehydrate
```

## 7. Artifact Boundary Contract

Operational contract:
1. Specialist writes only to own internal path:
   `agent-groups/<group>/internal/<specialist>/...`
2. Group head publishes only to exposed path:
   `agent-groups/<group>/exposed/...`
3. Cross-group consumption uses exposed paths only.
4. Cross-group access to other groups' internal paths is not allowed.
5. Same group IDs across different projects remain isolated by project-specific roots and project-scoped `CODEX_HOME`.

## 8. References

Internal:
- [README.md](./README.md)
- [docs/bootstrap/START_IN_CODEX.md](./docs/bootstrap/START_IN_CODEX.md)
- [src/agents_inc/docs/internal/session-intake.md](./src/agents_inc/docs/internal/session-intake.md)
- [src/agents_inc/docs/internal/session-resume.md](./src/agents_inc/docs/internal/session-resume.md)
- [src/agents_inc/docs/internal/session-compaction.md](./src/agents_inc/docs/internal/session-compaction.md)

GitHub:
- [Repository](https://github.com/sacRedeeRhoRn/agents-inc)
- [Releases](https://github.com/sacRedeeRhoRn/agents-inc/releases)
- [Latest tags](https://github.com/sacRedeeRhoRn/agents-inc/tags)
