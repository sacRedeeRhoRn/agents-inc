# agents-inc Session Validation Report

Date: 2026-03-01 (Asia/Seoul)
Repository: https://github.com/sacRedeeRhoRn/agents-inc
Validated release: https://github.com/sacRedeeRhoRn/agents-inc/releases/tag/v1.0.3

## Scope
End-to-end validation of new-session onboarding and multi-group orchestration with multiple invocation paths:
- local package commands
- non-interactive and interactive intake wizard
- visibility mode installs (`group-only` vs `--audit`)
- dispatch dry-run metadata for HPC group
- pinned README bootstrap command from live GitHub release

## Case Results
1. `case01-local-sanity.log`: PASS
2. `case02-init-noninteractive.log`: PASS
3. `case03-init-interactive.log`: PASS
4. `case04-visibility-install.log`: PASS
5. `case05-dispatch-hpc.log`: PASS
6. `case06-bootstrap-isolated.log`: FAIL (README checksum filename mismatch)
7. `case06b-bootstrap-diagnostic.log`: FAIL (bootstrap verified checksum file entries for wheel+sdist while only wheel downloaded)
8. `case07-patched-bootstrap-e2e.log`: FAIL (fresh Python 3.8 env had old pip; install failure)
9. `case07-patched-bootstrap-e2e-rerun.log`: PASS (after bootstrap pip upgrade hardening)
10. `case08-readme-live-v1.0.3.log`: PASS (exact README command against live release)

## Defects Found and Fixes
1. README checksum filename mismatch
- Symptom: `shasum` failed because checksum file referenced `bootstrap.sh` but README downloaded `agents-inc-bootstrap.sh`.
- Fix: standardized README command to download as `/tmp/bootstrap.sh` and `/tmp/bootstrap.sh.sha256`.
- File: `README.md`.

2. Bootstrap wheel checksum verification logic
- Symptom: script ran `shasum -c` on a checksum file containing both wheel and sdist entries, but only wheel was downloaded; verification failed.
- Fix: extract wheel-specific checksum line and verify only that line (`wheel-only.sha256`).
- File: `scripts/release/bootstrap.sh`.

3. Fresh Python 3.8 bootstrap dependency failure
- Symptom: old default pip in clean venv could not build/install dependencies.
- Fix: bootstrap now upgrades `pip`, `setuptools`, and `wheel` before installing `agents-inc` wheel.
- File: `scripts/release/bootstrap.sh`.

## Release and CI Status
- `main` CI: PASS (run `22523905350`)
- Release workflow for `v1.0.3`: PASS (run `22523913764`)
- Published assets for `v1.0.3`:
  - `agents_inc-1.0.3-py3-none-any.whl`
  - `agents_inc-1.0.3.tar.gz`
  - `agents_inc-1.0.3.sha256`
  - `bootstrap.sh`
  - `bootstrap.sh.sha256`

## Code Changes Applied During Refinement
- `b941feb` Fix bootstrap verification and harden fresh-session install
- Version updated to `1.0.3` in package metadata and docs.

## Log Inventory
- `TEST_MATRIX.md`
- `case01-local-sanity.log`
- `case02-init-noninteractive.log`
- `case03-init-interactive.log`
- `case04-visibility-install.log`
- `case05-dispatch-hpc.log`
- `case06-bootstrap-isolated.log`
- `case06b-bootstrap-diagnostic.log`
- `case07-patched-bootstrap-e2e.log`
- `case07-patched-bootstrap-e2e-rerun.log`
- `case08-readme-live-v1.0.3.log`

All logs are under:
`/Users/moon.s.june/Documents/Playground/agent_group_fabric/docs/generated/test-logs/2026-03-01-session-e2e`
