# Contributing

## Development Setup

```bash
cd /Users/moon.s.june/Documents/Playground/agent_group_fabric
pip install -e .
```

## Validation

```bash
agents-inc-validate --all
python3 -m unittest discover -s tests -v
```

## Pull Request Requirements

1. Keep catalog/templates/schemas and package resources in sync.
2. Add or update tests for behavior changes.
3. Ensure no hardcoded machine-specific absolute paths remain.
4. Update docs when interfaces change.
