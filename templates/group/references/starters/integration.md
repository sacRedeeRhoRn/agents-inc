# {{REFERENCE_TITLE}} - Integration Starter

## Scope
Covers cross-specialist artifact integration and dependency risk assessment.

## Core Concepts & Key Checks
- Identify all consumed upstream artifacts.
- Verify schema compatibility and path consistency.
- Record integration risks and mitigation actions.

## Checklist
- `dependencies_consumed` list is complete.
- `integration_risks` list is present (empty allowed).
- Final handoff references only validated upstream artifacts.

## Citation Guidance
Cite internal handoff artifacts directly by path and include any external dependency docs.

## Worked Micro-Example
Consumed: `agent-groups/<group>/internal/<agent>/handoff.json`
Risk: "Schema mismatch with downstream consumer".
