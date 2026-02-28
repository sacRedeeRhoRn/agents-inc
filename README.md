# agents-inc

Publication-ready multi-agent group fabric for Codex sessions.

## Quick Start (Pinned Release Bootstrap)

Paste this in a brand-new Codex session:

```bash
export AGI_VER="v1.0.4" && \
curl -sfL "https://github.com/sacRedeeRhoRn/agents-inc/releases/download/${AGI_VER}/bootstrap.sh" -o /tmp/bootstrap.sh && \
curl -sfL "https://github.com/sacRedeeRhoRn/agents-inc/releases/download/${AGI_VER}/bootstrap.sh.sha256" -o /tmp/bootstrap.sh.sha256 && \
(cd /tmp && shasum -a 256 -c bootstrap.sh.sha256) && \
bash /tmp/bootstrap.sh --owner sacRedeeRhoRn --repo agents-inc --release "${AGI_VER}"
```

What it does:
1. Downloads pinned release artifacts.
2. Verifies checksums.
3. Installs `agents-inc`.
4. Starts interactive intake (`agents-inc-init-session`).
5. Generates `long-run-command.sh` in project root for full-group isolation validation.

## Core Commands

```bash
agents-inc-new-group --group-id <id> --display-name "<name>" --domain "<domain>"
agents-inc-new-project --project-id <id> --groups g1,g2 --profile <profile>
agents-inc-install-skills --project-id <id> --sync
agents-inc-dispatch-dry-run --project-id <id> --group <group> --objective "<objective>"
agents-inc-sync-overlays --project-id <id> --from-template-version 1.0.0
agents-inc-validate --all
agents-inc-generate-docs --include-generated-projects
agents-inc-long-run-test --project-id <id> --groups all --duration-min 75
```

## Long-Run Full-Group Validation

Run one command to simulate cross-group orchestration and enforce strict artifact isolation:

```bash
agents-inc-long-run-test \
  --fabric-root /Users/moon.s.june/Documents/Playground/agent_group_fabric \
  --project-id proj-polymorph-longrun-001 \
  --task "Film thickness dependent polymorphism stability of metastable phase" \
  --groups all \
  --duration-min 75 \
  --strict-isolation hard-fail \
  --run-mode local-sim \
  --seed 20260301
```

Isolation semantics:
- No cross-group access to `agent-groups/<other-group>/internal/...`
- Cross-group exchange is only through `agent-groups/<group>/exposed/...`
- Specialists write only to their own `internal/<specialist>/...`
- Heads write only to their own `exposed/...`

Troubleshooting:

| Exit Code | Meaning | Typical Action |
|---|---|---|
| `0` | Pass | Review `final-report.md` and `coverage.json`. |
| `2` | Isolation violation | Inspect `violations.json` and `access-ledger.ndjson` for offending actor/path. |
| `3` | Lease contention unresolved | Check `lease-events.ndjson`, increase `--max-retries`, reduce `--conflict-rate`. |
| `4` | Interaction coverage insufficient | Inspect `coverage.json` for missing handoff edges. |
| `5` | Quality gate failure threshold exceeded | Review exposed artifacts and blocked gate events in `events.ndjson`. |

## Router Call Pattern

```text
Use $research-router for project <project-id> group <group-id>: <objective>.
```

## Project Visibility Policy

- Default: `group-only`
- Specialist artifacts: internal by default
- Specialist exposure: audit-only override

## Documentation

- Concise guide: [docs/INTRODUCTION.md](docs/INTRODUCTION.md)
- Full generated reference:
  `docs/generated/full-template-skill-reference.md`

## Development

```bash
cd /Users/moon.s.june/Documents/Playground/agent_group_fabric
pip install -e .
agents-inc-validate --all
python3 -m unittest discover -s tests -v
```
