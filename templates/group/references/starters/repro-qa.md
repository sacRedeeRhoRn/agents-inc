# {{REFERENCE_TITLE}} - Repro QA Starter

## Scope
Covers reproducibility command validation and expected-output checks.

## Core Concepts & Key Checks
- Commands must be runnable as provided.
- Preconditions (inputs, environment, paths) must be explicit.
- Expected outputs and pass/fail criteria must be measurable.

## Checklist
- `repro_commands` includes at least one executable command.
- `expected_outputs` specifies concrete success indicators.
- Artifact paths are valid and scoped correctly.

## Citation Guidance
When command behavior depends on tools/frameworks, cite the relevant official docs.

## Worked Micro-Example
Command: `python -m pytest tests/test_smoke.py`
Expected: "N passed" and exit code 0.
