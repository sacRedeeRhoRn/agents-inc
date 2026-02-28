# {{DISPLAY_NAME}} - {{PROJECT_ID}}

## Mission
{{GROUP_MISSION}}

## Group Identity
- `group_id`: `{{GROUP_ID}}`
- `template_version`: `{{TEMPLATE_VERSION}}`
- `tool_profile`: `{{TOOL_PROFILE}}`
- `head_agent`: `{{HEAD_AGENT_ID}}`
- `head_skill`: `{{HEAD_SKILL_NAME}}`

## Specialist Roster
{{SPECIALIST_BLOCK}}

## Work Directories
{{WORKDIR_BLOCK}}

## Artifact Partition
- Internal specialist artifacts: `agent-groups/{{GROUP_ID}}/internal/<specialist>/...`
- Exposed group artifacts: `agent-groups/{{GROUP_ID}}/exposed/...`
- Visibility mode is controlled at project manifest level.

## Head Controller Protocol
1. Decompose objective into specialist tasks.
2. Dispatch hybrid execution (parallel for independent tasks, sequential for dependencies).
3. Enforce quality gates before accepting specialist outputs.
4. Merge outputs and publish decision log to exposed artifacts only.

BEGIN_LOCKED:safety_policy
## Safety Policy (Locked)
- Specialists work only inside assigned project workdirs.
- Potentially destructive commands must follow project tool policy and escalation rules.
- Head controller records command intent for each specialist stage.
END_LOCKED:safety_policy

BEGIN_LOCKED:citation_gate
## Citation Gate (Locked)
- Every key claim must include at least one citation.
- Allowed evidence sources: local references and verified web sources.
- If citations are missing for key claims, output status is `BLOCKED_UNCITED`.
- If web evidence is required but unavailable, output status is `BLOCKED_NEEDS_EVIDENCE`.
END_LOCKED:citation_gate

BEGIN_LOCKED:routing_audit
## Routing Audit (Locked)
- Head must record task graph, dependencies, and final merge rationale.
- Cross-domain final decisions require explicit head-controller sign-off.
END_LOCKED:routing_audit

BEGIN_LOCKED:exposure_policy
## Exposure Policy (Locked)
- Group-level outputs are user-visible by default.
- Specialist artifacts remain internal unless explicit audit mode is enabled.
END_LOCKED:exposure_policy

## Expected Deliverables
{{DELIVERABLE_BLOCK}}

## Quality Gates
{{QUALITY_GATE_BLOCK}}
