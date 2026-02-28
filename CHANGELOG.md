# Changelog

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
