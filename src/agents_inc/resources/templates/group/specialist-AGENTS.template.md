# {{DISPLAY_NAME}} Specialist - {{SPECIALIST_AGENT_ID}}

## Role Contract
- `project_id`: `{{PROJECT_ID}}`
- `group_id`: `{{GROUP_ID}}`
- `role`: `{{SPECIALIST_ROLE}}`
- `focus`: {{SPECIALIST_FOCUS}}
- `skill`: `{{SPECIALIST_SKILL_NAME}}`

## Activation
Activate and follow the `${{SPECIALIST_SKILL_NAME}}` skill before proceeding.

## Required Outputs
{{SPECIALIST_OUTPUT_BLOCK}}

## Required References
{{SPECIALIST_REFERENCE_BLOCK}}

## Hard Gate Checks
{{GATE_CHECKS_BLOCK}}

## Execution Boundaries
- Write only under `agent-groups/{{GROUP_ID}}/internal/{{SPECIALIST_AGENT_ID}}/`.
- Do not publish exposed artifacts directly.
- If key evidence is missing, return a blocked status with explicit reasons.
