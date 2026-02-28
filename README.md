# agents-inc

Publication-ready multi-agent group fabric for Codex sessions.

## Quick Start (Pinned Release Bootstrap)

Paste this in a brand-new Codex session:

```bash
export AGI_VER="v1.0.0" && \
curl -sfL "https://github.com/sacRedeeRhoRn/agents-inc/releases/download/${AGI_VER}/bootstrap.sh" -o /tmp/agents-inc-bootstrap.sh && \
curl -sfL "https://github.com/sacRedeeRhoRn/agents-inc/releases/download/${AGI_VER}/bootstrap.sh.sha256" -o /tmp/agents-inc-bootstrap.sh.sha256 && \
(cd /tmp && shasum -a 256 -c agents-inc-bootstrap.sh.sha256) && \
bash /tmp/agents-inc-bootstrap.sh --owner sacRedeeRhoRn --repo agents-inc --release "${AGI_VER}"
```

What it does:
1. Downloads pinned release artifacts.
2. Verifies checksums.
3. Installs `agents-inc`.
4. Starts interactive intake (`agents-inc-init-session`).

## Core Commands

```bash
agents-inc-new-group --group-id <id> --display-name "<name>" --domain "<domain>"
agents-inc-new-project --project-id <id> --groups g1,g2 --profile <profile>
agents-inc-install-skills --project-id <id> --sync
agents-inc-dispatch-dry-run --project-id <id> --group <group> --objective "<objective>"
agents-inc-sync-overlays --project-id <id> --from-template-version 1.0.0
agents-inc-validate --all
agents-inc-generate-docs --include-generated-projects
```

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
