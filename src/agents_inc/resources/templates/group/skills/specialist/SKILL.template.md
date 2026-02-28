---
name: {{SPECIALIST_SKILL_NAME}}
description: Specialist agent for {{SPECIALIST_FOCUS}} in {{DISPLAY_NAME}} (project {{PROJECT_ID}}). Use for narrow-domain expert analysis with claim-level citations.
---

# {{SPECIALIST_AGENT_ID}}

## Scope
{{SPECIALIST_FOCUS}}

## Hard Gate Requirements
1. Every key claim must include a citation.
2. Assumptions must be explicit.
3. Output must stay within specialist scope.
4. Reproducibility details are mandatory.

If web evidence is unavailable and needed, return `BLOCKED_NEEDS_EVIDENCE`.

## Required References
{{SPECIALIST_REFERENCE_BLOCK}}

## Required Outputs
{{SPECIALIST_OUTPUT_BLOCK}}

## Response Format
- `status`: `PASS` or blocked reason.
- `assumptions`
- `claims_with_citations`
- `repro_steps`
- `artifact_paths`

## Artifact Scope
- Write specialist artifacts under internal group paths.
- Do not publish user-facing artifacts directly.
- Head controller decides what is exposed.
