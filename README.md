# agents-**inc.**

```text
    _    ____ _____ _   _ _____ ____      ___ _   _  ____
   / \  / ___| ____| \ | |_   _/ ___|    |_ _| \ | |/ ___|
  / _ \| |  _|  _| |  \| | | | \___ \     | ||  \| | |
 / ___ \ |_| | |___| |\  | | |  ___) |    | || |\  | |___
/_/   \_\____|_____|_| \_| |_| |____/    |___|_| \_|\____|
```

`agents-inc` is a multi-agent body that learns while it runs.
One orchestrator, many group minds, each cycle sharpening the next through negotiation, evidence, and restart-safe memory.

![Session pulse](./docs/assets/session-lifecycle-v2.svg)

## Install (Ready To Paste)

```bash
git clone git@github.com:sacRedeeRhoRn/agents-inc.git
cd agents-inc
python3 -m pip install --upgrade pip
python3 -m pip install -e .
```

## Bootstrap (One Command)

```bash
agents-inc init
```

What this activates:
- captures your intent and constraints
- resolves project root and session state
- prepares project bundle and managed skills
- writes checkpoint + compact resume state
- opens managed flow (or keeps terminal-only if configured)

## The Self-Enhancing Core

Every run is not just execution.
It is refinement.
Groups produce outputs, heads challenge each other, and the next cycle gets a sharper objective contract.

![Enhancement loop](./docs/assets/self-enhance-loop.svg)

Grounded behavior behind the language:
- group objectives are split and tuned per cycle
- head meeting can demand another cycle when not satisfied
- exposed handoffs become the canonical memory for integration
- checkpoints preserve continuity when sessions pause or break

## Live Group Negotiation

Groups work in parallel, then converge.
The meeting layer turns disagreement into explicit next actions.

![Negotiation map](./docs/assets/group-negotiation-map.svg)

## Checkpointed Recovery

When the flow blocks, state is not lost.
Checkpoint, compact snapshot, resume contract.
You return to momentum, not to zero.

![Recovery map](./docs/assets/resume-recovery-map.svg)

## First Live Flow

1. inspect available groups:

```bash
agents-inc group-list
```

2. create your first custom group:

```bash
agents-inc new-group
```

3. create your project:

```bash
agents-inc create <project-id>
```

4. list current projects:

```bash
agents-inc list
```

5. pause a project intentionally:

```bash
agents-inc deactivate <project-id>
```

6. save a checkpoint before risky work:

```bash
agents-inc save <project-id>
```

7. resume from latest stable state:

```bash
agents-inc resume <project-id>
```

## Full Operator Manual

For complete flags, advanced modes, and detailed command contracts:
- [OVERVIEW.md](./OVERVIEW.md)

Additional references:
- [docs/bootstrap/START_IN_CODEX.md](./docs/bootstrap/START_IN_CODEX.md)
- [src/agents_inc/docs/internal/session-intake.md](./src/agents_inc/docs/internal/session-intake.md)
- [src/agents_inc/docs/internal/session-resume.md](./src/agents_inc/docs/internal/session-resume.md)
- [sacRedeeRhoRn/agents-inc](https://github.com/sacRedeeRhoRn/agents-inc)
