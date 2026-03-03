# agents-inc Overview

This is the full operator manual.
`README.md` is the quick path. This document is the complete path.

## 1. Mental Model

`agents-inc` keeps project orchestration stable across long sessions:
- Group heads coordinate specialist agents.
- Specialists work in scoped internal areas.
- Cross-group communication happens through exposed artifacts.
- Checkpoints and compact snapshots keep resume deterministic.

## 2. Install

## 2.1 Source (editable)

```bash
git clone git@github.com:sacRedeeRhoRn/agents-inc.git
cd agents-inc
python3 -m pip install --upgrade pip
python3 -m pip install -e .
```

## 2.2 Source (non-editable)

```bash
git clone git@github.com:sacRedeeRhoRn/agents-inc.git
cd agents-inc
python3 -m pip install --upgrade pip
python3 -m pip install .
```

## 2.3 Release-pinned wheel install

```bash
export AGI_VER="v4.0.1" && \
WHEEL="agents_inc-4.0.1-py3-none-any.whl" && \
curl -sfL "https://github.com/sacRedeeRhoRn/agents-inc/releases/download/${AGI_VER}/${WHEEL}" -o "/tmp/${WHEEL}" && \
curl -sfL "https://github.com/sacRedeeRhoRn/agents-inc/releases/download/${AGI_VER}/agents_inc-4.0.1.sha256" -o /tmp/agents_inc-4.0.1.sha256 && \
(cd /tmp && grep "  ${WHEEL}$" agents_inc-4.0.1.sha256 > wheel.sha256 && shasum -a 256 -c wheel.sha256) && \
python3 -m pip install --upgrade pip setuptools wheel && \
python3 -m pip install --upgrade "/tmp/${WHEEL}"
```

## 2.4 Verify

```bash
agents-inc --version
agents-inc --help
```

## 3. Bootstrap and First Turn

Primary bootstrap command:

```bash
agents-inc init
```

Behavior summary:
- asks new/resume intent
- resolves project root/index/config context
- generates/rebuilds project bundle files
- writes state/checkpoint/compact metadata
- can launch managed orchestrator chat

Important: if someone tells you to run `entrace init`, use `agents-inc init`.

## 4. Core Lifecycle Commands

Minimal day-to-day flow:

```bash
agents-inc group-list
agents-inc new-group
agents-inc create <project-id>
agents-inc list
agents-inc save <project-id>
agents-inc deactivate <project-id>
agents-inc resume <project-id>
```

## 5. Command Router Reference

Top-level router:

```bash
agents-inc <command> [args]
```

Current router commands:
- `init`
- `group-list`
- `create`
- `save`
- `deactivate`
- `list`
- `resume`
- `dispatch`
- `orchestrator-reply`
- `project-groups`
- `delete`
- `new-group`

## 6. Detailed Command Flags

## 6.1 `agents-inc init`

```text
usage: agents-inc init [--fabric-root] [--project-root] [--projects-root]
                       [--config-path] [--project-id] [--groups]
                       [--task] [--timeline] [--compute {cpu,gpu,cuda}]
                       [--remote-cluster {yes,no}] [--output-target]
                       [--non-interactive] [--target-skill-dir]
                       [--mode {ask,new,resume}] [--resume-project-id]
                       [--resume-checkpoint]
                       [--resume-mode {auto,compact,rehydrate}]
                       [--project-index] [--no-launch] [--overwrite-existing]
                       [--json]
```

Use cases:
- guided bootstrap: `agents-inc init`
- force new flow: `agents-inc init --mode new`
- force resume flow: `agents-inc init --mode resume`
- non-launch prep: `agents-inc init --no-launch`
- machine output for scripts: `agents-inc init --json`

Output behavior:
- default: human-readable setup guidance + next commands
- `--json`: machine-readable payload (automation-friendly)

## 6.2 `agents-inc group-list`

```text
usage: agents-inc group-list [--fabric-root] [--json]
```

## 6.3 `agents-inc new-group`

```text
usage: agents-inc new-group [--fabric-root] [--group-id] [--display-name]
                            [--domain] [--purpose] [--success-criteria]
                            [--extra-roles] [--force] [--use-codex|--no-codex]
                            [--json] [--regenerate-core] [--core-seed-file]
```

Examples:

```bash
agents-inc new-group
agents-inc new-group --group-id customer-success --display-name "Customer Success" --domain professional-services --purpose "Coordinate onboarding delivery" --success-criteria "handoff complete,evidence linked" --no-codex
```

## 6.4 `agents-inc create`

```text
usage: agents-inc create <project-id> [--fabric-root] [--projects-root]
                         [--config-path] [--project-index] [--groups]
                         [--no-launch] [--json] [--force]
```

## 6.5 `agents-inc list`

```text
usage: agents-inc list [--project-index] [--scan-root] [--config-path]
                       [--no-scan] [--include-stale] [--json]
```

Default behavior:
- includes `active` and `inactive`
- excludes `stale` unless `--include-stale`

## 6.6 `agents-inc deactivate`

```text
usage: agents-inc deactivate <project-id> [--project-index] [--scan-root]
                             [--config-path] [--json]
```

## 6.7 `agents-inc save`

```text
usage: agents-inc save <project-id> [--fabric-root] [--project-index]
                       [--scan-root] [--config-path] [--json]
```

## 6.8 `agents-inc resume`

```text
usage: agents-inc resume <project-id> [--fabric-root] [--project-index]
                         [--scan-root] [--config-path] [--no-launch] [--json]
```

## 6.9 `agents-inc dispatch`

```text
usage: agents-inc dispatch --project-id <project-id> --objective <objective>
                           [--group <group-id|auto>] [--json] [...]
```

Purpose:
- deterministic dry-run dispatch planning

## 6.10 `agents-inc orchestrator-reply`

```text
usage: agents-inc orchestrator-reply --project-id <project-id> --message <message>
                                     [--group auto|<group-id>] [--output-dir]
                                     [--project-index] [--scan-root] [--config-path]
                                     [--json] [--max-parallel] [--retry-attempts]
                                     [--retry-backoff-sec] [--agent-timeout-sec]
                                     [--specialist-model] [--head-model]
                                     [--specialist-reasoning-effort]
                                     [--head-reasoning-effort]
                                     [--live-profile bounded|custom]
                                     [--audit] [--loop-mode cooperative]
                                     [--meeting-enabled|--no-meeting]
                                     [--stop-rule unanimous-head-satisfied]
                                     [--max-cycles] [--heartbeat-sec]
                                     [--require-negotiation true|false]
                                     [--abort-file]
                                     [--non-interactive-escalation]
```

Common examples:

```bash
agents-inc orchestrator-reply --project-id <project-id> --message "Draft execution plan"
agents-inc orchestrator-reply --project-id <project-id> --message "[non-group] show active specialist sessions"
agents-inc orchestrator-reply --project-id <project-id> --message "Investigate production risk" --live-profile bounded --require-negotiation true
```

## 6.11 `agents-inc project-groups`

```text
usage: agents-inc project-groups <list|add|remove|create> ...
```

Examples:

```bash
agents-inc project-groups list --project-id <project-id>
agents-inc project-groups add --project-id <project-id> --groups developer,integration-delivery
agents-inc project-groups remove --project-id <project-id> --groups quality-assurance
agents-inc project-groups create --project-id <project-id> --group-id custom-group --display-name "Custom Group" --domain custom
```

## 6.12 `agents-inc delete`

```text
usage: agents-inc delete <project-id> [--project-index] [--scan-root]
                         [--config-path] [--yes]
```

## 7. State, Artifacts, and Resume Contracts

Global state:
- `~/.agents-inc/config.yaml`
- `~/.agents-inc/projects-index.yaml`

Project state:
- `<project-root>/.agents-inc/state/session-state.yaml`
- `<project-root>/.agents-inc/state/latest-checkpoint.yaml`
- `<project-root>/.agents-inc/state/checkpoints/<checkpoint-id>.yaml`
- `<project-root>/.agents-inc/state/latest-compacted.yaml`
- `<project-root>/.agents-inc/state/compacted/<compact-id>.yaml`
- `<project-root>/.agents-inc/state/response-policy.yaml`
- `<project-root>/.agents-inc/state/specialist-sessions.yaml`

Turn outputs:
- `<project-root>/.agents-inc/turns/<turn-id>/request.txt`
- `<project-root>/.agents-inc/turns/<turn-id>/delegation-ledger.json`
- `<project-root>/.agents-inc/turns/<turn-id>/group-evidence-index.json`
- `<project-root>/.agents-inc/turns/<turn-id>/final/full-report.md` (pass path)
- `<project-root>/.agents-inc/turns/<turn-id>/blocked-report.md` (block path)

Latest polling pointers:
- `wait-state.latest.json`
- `cooperation-ledger.latest.ndjson`
- `group-head-sessions.latest.json`
- `specialist-sessions.latest.json`

## 8. Operational Tips

- Prefer `agents-inc init` for guided setup in mixed environments.
- Keep `README.md` for fast path; use this document when you need flags.
- Use `agents-inc save <project-id>` before major experimental branching.
- Use `agents-inc deactivate <project-id>` to deliberately suspend project selection.
- Use `agents-inc resume <project-id>` to restore continuity quickly.

## 9. Internal and External References

- Quickstart: [README.md](./README.md)
- Bootstrap contract: [docs/bootstrap/START_IN_CODEX.md](./docs/bootstrap/START_IN_CODEX.md)
- Internal intake docs: [src/agents_inc/docs/internal/session-intake.md](./src/agents_inc/docs/internal/session-intake.md)
- Internal resume docs: [src/agents_inc/docs/internal/session-resume.md](./src/agents_inc/docs/internal/session-resume.md)
- Repo: [sacRedeeRhoRn/agents-inc](https://github.com/sacRedeeRhoRn/agents-inc)
- Releases: [github.com/sacRedeeRhoRn/agents-inc/releases](https://github.com/sacRedeeRhoRn/agents-inc/releases)
