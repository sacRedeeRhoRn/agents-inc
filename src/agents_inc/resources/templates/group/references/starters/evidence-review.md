# {{REFERENCE_TITLE}} - Evidence Review Starter

## Scope
Covers claim validation, contradiction detection, and evidence sufficiency review.

## Core Concepts & Key Checks
- Classify each claim as supported, unsupported, or contradictory.
- Trace each supported claim to explicit citations.
- Separate factual evidence from interpretation.

## Checklist
- `unsupported_claims` list produced.
- `contradictions` field set explicitly (`true`/`false`).
- Review rationale explains block/retry recommendations.

## Citation Guidance
A claim is supported only when at least one citation directly backs the exact assertion.

## Worked Micro-Example
Claim: "System guarantees exactly-once behavior."
Review: unsupported unless protocol-level evidence is cited.
