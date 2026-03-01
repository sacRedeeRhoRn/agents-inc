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
export AGI_VER="v2.2.2" && \
WHEEL="agents_inc-2.2.2-py3-none-any.whl" && \
curl -sfL "https://github.com/sacRedeeRhoRn/agents-inc/releases/download/${AGI_VER}/${WHEEL}" -o "/tmp/${WHEEL}" && \
curl -sfL "https://github.com/sacRedeeRhoRn/agents-inc/releases/download/${AGI_VER}/agents_inc-2.2.2.sha256" -o /tmp/agents_inc-2.2.2.sha256 && \
(cd /tmp && grep "  ${WHEEL}$" agents_inc-2.2.2.sha256 > wheel.sha256 && shasum -a 256 -c wheel.sha256) && \
python3 -m pip install --upgrade pip setuptools wheel && \
python3 -m pip install --upgrade "/tmp/${WHEEL}"
```

### Verify Install

```bash
agents-inc --version
agents-inc --help
```

Expected version for this guide: `2.2.2`.

## 3. Start Your Codex Orchestrator Session

Run this in Terminal to open a new Codex session with the onboarding markdown prompt:

```bash
export AGI_VER="v2.2.2" && \
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

## 4.3 Dispatch or reply

```bash
agents-inc dispatch --project-id <project-id> --group <group-id> --objective "<objective>"
agents-inc orchestrator-reply --project-id <project-id> --message "<message>"
```

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
- `<project-root>/.agents-inc/turns/<turn-id>/final-exposed-answer.md`
- `<project-root>/.agents-inc/turns/<turn-id>/final-answer-quality.json`

## 5. Example Task Run (Metastable Chiral Silicide Discovery)

Objective theme:
- find a new metastable phase candidate in a silicide system within chiral space groups
- build computational plan (DFT + MD + FEM)
- generate developer-side Python scripts/package to operationalize the workflow

### 5.1 Security note for project credentials

> Warning
> Never place real API keys in prompts, markdown, commits, or logs.
>
> Use environment variables only.

```bash
export MATERIALS_PROJECT_API_KEY="<your-key-here>"
```

### 5.2 Start a new project

```bash
agents-inc init --mode new
```

Choose or confirm groups including at least:
- `material-scientist`
- `literature-intelligence`
- `data-curation`
- `developer`
- `quality-assurance`

Optional for downstream packaging/presentation:
- `designer`
- `publication-packaging`

### 5.3 Activate specialists for core technical groups

```bash
agents-inc skills activate --project-id <project-id> --groups developer,material-scientist --specialists
```

### 5.4 Run a publication-grade orchestrator turn

```bash
agents-inc orchestrator-reply --project-id <project-id> --message "Plan an end-to-end discovery campaign for a metastable chiral silicide phase. Include hypothesis generation, DFT ranking, MD stability screening, FEM process-window analysis, and a decision-gated experimental synthesis plan with expected resistivity outcomes and evidence-backed risks."
```

### 5.5 Push concrete objectives into developer and materials groups

```bash
agents-inc dispatch --project-id <project-id> --group developer --objective "Create a Python package and runnable scripts for the silicide discovery pipeline: structure candidate ingestion, DFT job templating, MD batch submission plan, FEM parameter sweeps, and reproducible report assembly with CLI entrypoints."

agents-inc dispatch --project-id <project-id> --group material-scientist --objective "Search and rank chiral-space-group metastable silicide candidates, define stability criteria and uncertainty bounds, and output prioritized synthesis targets with computationally anticipated transport behavior."
```

### 5.6 Run a concise state query with strict non-group mode

```bash
agents-inc orchestrator-reply --project-id <project-id> --message "[non-group] List specialist session IDs currently active for this project."
```

### 5.7 Confirm session and resume readiness

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
