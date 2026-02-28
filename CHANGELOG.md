# Changelog

## v1.2.0

- Added new primary umbrella CLI: `agents-inc`.
  - Subcommands: `init`, `list`, `resume`, `dispatch`, `long-run`, `validate`, `docs`
- Added markdown-driven Codex bootstrap prompt:
  - `docs/bootstrap/START_IN_CODEX.md`
- Added persistent config defaults:
  - `~/.agents-inc/config.yaml` for projects root and release defaults
- Added compacted orchestrator session snapshots:
  - `<project-root>/.agents-inc/state/compacted/<compact-id>.yaml`
  - `<project-root>/.agents-inc/state/latest-compacted.yaml`
  - `<project-root>/.agents-inc/state/group-sessions.yaml`
- Added `agents-inc resume <project-id>` launcher command:
  - resumes via compact snapshot (auto) with checkpoint rehydrate fallback
  - launches Codex in same terminal unless `--no-launch`
- Extended session listing with session metadata:
  - `session_code`, `active_groups`, `group_session_map`
- Updated `init` intake:
  - asks/saves projects root default
  - supports recommended+editable group activation
- Added one-release alias layer (`v1.2.x`) for old `agents-inc-*` command names with deprecation warnings.
- Updated README and internal docs for terminal-vs-codex clarity and restart-safe orchestration workflow.

## v1.1.0

- Added restart-safe orchestrator state subsystem:
  - project checkpoints under `<project-root>/.agents-inc/state/`
  - global resume index under `~/.agents-inc/projects-index.yaml`
- Extended `agents-inc-init-session` with resume-safe controls:
  - `--mode ask|new|resume`
  - `--resume-project-id`
  - `--resume-checkpoint`
  - `--project-index`
  - `--overwrite-existing`
- Added `agents-inc-list-sessions` to enumerate resumable sessions (active/stale) with JSON output option.
- Changed intake default behavior to non-destructive:
  - existing projects are resumed or explicitly overwritten by user choice
  - removed implicit destructive regeneration in normal paths
- Integrated automatic checkpoint writes into:
  - `agents-inc-dispatch-dry-run`
  - `agents-inc-long-run-test` (run-start, cycle, run-end)
- Added internal resume guide:
  - `src/agents_inc/docs/internal/session-resume.md`
- Updated bootstrap messaging and README for end-to-end new/resume workflow.

## v1.0.4

- Added `agents-inc-long-run-test` for full-group long-run interaction and artifact-isolation validation.
- Added deterministic local simulation runtime with lease contention checks, strict path policy, and machine-readable reports.
- Added long-run test coverage for pass/fail paths (isolation, deadlock, quality gate, audit mode).
- Improved new-session onboarding visibility:
  - bootstrap now prints long-run validator availability
  - intake now generates `long-run-command.sh` in project root
  - session intake docs include long-run validation guidance

## v1.0.3

- Fixed README bootstrap command filename/checksum mismatch (`bootstrap.sh` naming is now consistent).
- Fixed bootstrap wheel checksum verification to validate only the selected wheel entry.
- Hardened bootstrap for fresh Python 3.8 environments by upgrading `pip`, `setuptools`, and `wheel` before install.

## v1.0.2

- Aligned package version with release tag for checksum-verified bootstrap installs.
- Updated README pinned bootstrap command to `v1.0.2`.

## v1.0.1

- Added tracked `.gitkeep` markers for `exposed/` and `internal/*/` visibility directories in sample bundles.
- Made CI unit tests self-contained with fallback lease controller when `multi_agent_dirs` is unavailable.

## v1.0.0

- Converted project to installable package (`agents-inc` / `agents_inc`).
- Added interactive session onboarding (`agents-inc-init-session`).
- Added full inlined docs generation (`agents-inc-generate-docs`).
- Added group-scoped visibility policy with audit override.
- Added `atomistic-hpc-simulation` group with VASP/LAMMPS/Metadynamics and remote HPC experts.
- Added release bootstrap script + checksum workflow.
- Added GitHub Actions CI and release pipelines.
