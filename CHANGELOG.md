# Changelog

## v2.2.2

- Synced publication tag to include post-`v2.2.1` fixes already on `main`.
- Updated pinned quick-start/install/bootstrap references from `v2.2.1` to `v2.2.2` in:
  - `README.md`
  - `OVERVIEW.md`
  - `docs/bootstrap/START_IN_CODEX.md`
- Simplified `agents-inc list` output to only show:
  - `project_id`
  - `status`
  - `root`
- Added project-level commands:
  - `agents-inc deactivate <project-id>`
  - `agents-inc delete <project-id> --yes`
- Fixed CLI project resolution for commands run outside project roots:
  - `agents-inc orchestrator-reply` now resolves project `fabric_root` via project index/scan fallback when `--fabric-root` is omitted.
  - `agents-inc dispatch` now resolves project `fabric_root` the same way when `--fabric-root` is omitted.
- Added regression tests for project-resolution behavior:
  - `tests/test_cli_project_resolution.py`
- Added regression tests for deactivate/delete controls:
  - `tests/test_project_control.py`
- Bumped package version to `2.2.2`.

## v2.2.1

- Reconstructed top-level documentation into a two-layer operator experience:
  - `README.md` is now a minimal entrypoint with essential lifecycle commands.
  - new `OVERVIEW.md` provides full step-by-step orchestration guidance and example task run.
- Updated all primary quick-start and bootstrap references to `v2.2.1`.
- Hardened bootstrap install guidance in `docs/bootstrap/START_IN_CODEX.md`:
  - release-pinned checksum-verified install path first,
  - source-install fallback for cases where release assets are not yet available.
- Added explicit sensitive-data guidance for materials workflows:
  - docs now use `MATERIALS_PROJECT_API_KEY` placeholder and prohibit hardcoded key usage.
- Bumped package version to `2.2.1`.

## v2.2.0

- Hardened bootstrap startup behavior:
  - `docs/bootstrap/START_IN_CODEX.md` now enforces an immediate first-turn question:
    - `Start new project or resume existing project?`
  - onboarding checks/install guidance remain, but must run only after the first answer.
- Added strict project-scoped skill management (no global managed-skill default install):
  - new command family:
    - `agents-inc skills list --project-id <id> [--json]`
    - `agents-inc skills activate --project-id <id> --groups g1,g2 [--specialists] [--sync]`
    - `agents-inc skills deactivate --project-id <id> --groups g1,g2 [--sync]`
    - `agents-inc skills cleanup-global [--dry-run|--apply]`
- Added project `CODEX_HOME` subsystem:
  - `<project-root>/.agents-inc/codex-home`
  - `<project-root>/.agents-inc/state/codex-home.yaml`
  - `<project-root>/.agents-inc/state/skill-activation.yaml`
  - links/copies global auth/config into project-scoped codex-home.
- Updated `init` and `resume` integration:
  - default skill target is project-scoped codex-home skills dir
  - initial activation installs head skills only
  - specialist skills require explicit activation
  - resume launch now sets `CODEX_HOME=<project-root>/.agents-inc/codex-home`.
- Added tests for v2.2.0 hardening:
  - bootstrap first-question contract and README quick-start version checks
  - project-scoped skill isolation, selective specialist activation, deactivation behavior
  - managed-global cleanup safety checks.
- Bumped package version to `2.2.0`.

## v2.1.0

- Added strict turn-mode orchestration command:
  - `agents-inc orchestrator-reply --project-id <id> --message "<request>"`
  - strict mode parser:
    - `[non-group]` prefix at message start -> concise direct response.
    - all other requests -> group-routed publication-grade detailed synthesis.
- Added project-local response policy state:
  - `.agents-inc/state/response-policy.yaml`
- Added specialist session identity map:
  - `.agents-inc/state/specialist-sessions.yaml`
  - session code format: `<project-id>::<group-id>::<specialist-id>::<counter>`
- Added per-turn orchestration artifacts under:
  - `.agents-inc/turns/<turn-id>/...`
  - includes delegation ledger, negotiation sequence, evidence index, final exposed answer, and quality gate report.
- Added publication-grade answer quality gate for group mode with required sections/evidence thresholds.
- Orchestrator campaign now validates delegation/negotiation/final-quality artifacts and no longer silently passes shallow fallbacks unless explicitly allowed via `--allow-live-fallback`.
- Extended dispatch metadata with web-search policy:
  - `group_web_search_default`
  - `tasks[].web_search_enabled`
- Group manifest contract now requires:
  - `execution_defaults.web_search_enabled`
  - optional specialist override: `specialists[].execution.web_search_enabled`
- Updated all built-in catalog group manifests to default `web_search_enabled: true`.
- Updated README/bootstrap/router template guidance for strict mode semantics and `orchestrator-reply`.
- Bumped package version to `2.1.0`.

## v2.0.0

- Hard-cutover schema upgrade to strict v2 contracts.
  - Group manifests now require `schema_version: "2.0"` with purpose/success criteria, gate profile, publish contract, and dependency artifact semantics.
  - Project manifests now require `schema_version: "2.0"`.
  - Session/checkpoint/compaction/index loaders now reject non-v2 payloads and direct users to migration.
- Added migration command:
  - `agents-inc migrate-v2 --dry-run|--apply`
  - supports backup output for changed files.
- Added runtime version reporting:
  - `agents-inc --version` and `agents-inc -V`.
- Added catalog-level group UX:
  - `agents-inc groups list|show|new|templates`
  - codex-session-friendly interactive group wizard (`groups new --interactive`) with user-confirmed specialist roster.
- Added strict skill frontmatter contract v2:
  - required keys: `name`, `version`, `role`, `description`, `scope`, `inputs`, `outputs`, `failure_modes`, `autouse_triggers`
  - validation now rejects missing/unknown keys.
- Added skill harness checks:
  - role-specific contract checks for head/specialist/router skill content.
- Redesigned catalog groups to v2 and enforced minimum specialist contract coverage.
- Added standardized artifact scaffolding in generated groups:
  - specialists: `internal/<agent>/work.md`, `internal/<agent>/handoff.json`
  - head: `exposed/summary.md`, `exposed/handoff.json`, `exposed/INTEGRATION_NOTES.md`
- Extended dispatch contract:
  - includes `gate_profile`, `specialist_output_schema`, dependency checks, and lock metadata.
  - new locking mode: `--locking-mode required|auto|off`.
- Validation hardening:
  - explicit `multi_agent_dirs` dependency warning,
  - `.swp` template file detection.
- Resume launch hardening:
  - persists `.agents-inc/state/resume-prompt.md`
  - sanitizes launch prompt payload.
- Tooling/CI hardening:
  - added `black` and `ruff` configuration and dev dependencies.
- Bootstrap and README updated to v2.0.0 and catalog-group workflow.

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
