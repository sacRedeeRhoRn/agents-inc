# Developer Group - proj-battery-001

## Mission
Deliver robust implementation, debugging, and automation support for research projects.

## Group Identity
- `group_id`: `developer`
- `template_version`: `2.0.0`
- `tool_profile`: `developer-default`
- `head_agent`: `developer-head`
- `head_skill`: `proj-proj-battery-001-developer-developer-head`

## Specialist Roster
- `python-expert`: Python architecture, package reliability, tests, and runtime debugging (skill: `proj-proj-battery-001-developer-python-expert`)
- `shell-expert`: Shell automation, reproducible scripts, CLI hardening (skill: `proj-proj-battery-001-developer-shell-expert`)
- `ssh-remote-ops-expert`: Remote operations, secure SSH workflows, transfer and execution protocols (skill: `proj-proj-battery-001-developer-ssh-remote-ops-expert`)
- `integration-specialist`: Cross-artifact integration and consumability checks for Developer Group (skill: `proj-proj-battery-001-developer-integration-specialist`)
- `evidence-review-specialist`: Claim-level evidence review and citation sufficiency for Developer Group (skill: `proj-proj-battery-001-developer-evidence-review-specialist`)
- `web-research-specialist`: Gather web-published references and extract citation-ready evidence. (skill: `proj-proj-battery-001-developer-web-research-specialist`)

## Work Directories
- `generated/projects/proj-battery-001/work/developer/python-expert`
- `generated/projects/proj-battery-001/work/developer/shell-expert`
- `generated/projects/proj-battery-001/work/developer/ssh-remote-ops-expert`
- `generated/projects/proj-battery-001/work/developer/integration-specialist`
- `generated/projects/proj-battery-001/work/developer/evidence-review-specialist`
- `generated/projects/proj-battery-001/work/developer/web-research-specialist`

## Artifact Partition
- Internal specialist artifacts: `agent-groups/developer/internal/<specialist>/...`
- Exposed group artifacts: `agent-groups/developer/exposed/...`
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
- `implementation_patch.md` from `python-expert`
- `test_plan.md` from `python-expert`
- `claims_with_citations.md` from `python-expert`
- `work.md` from `python-expert`
- `handoff.json` from `python-expert`
- `automation_scripts.md` from `shell-expert`
- `claims_with_citations.md` from `shell-expert`
- `work.md` from `shell-expert`
- `handoff.json` from `shell-expert`
- `remote_ops_plan.md` from `ssh-remote-ops-expert`
- `claims_with_citations.md` from `ssh-remote-ops-expert`
- `work.md` from `ssh-remote-ops-expert`
- `handoff.json` from `ssh-remote-ops-expert`
- `work.md` from `integration-specialist`
- `handoff.json` from `integration-specialist`
- `work.md` from `evidence-review-specialist`
- `handoff.json` from `evidence-review-specialist`
- `work.md` from `web-research-specialist`
- `handoff.json` from `web-research-specialist`

## Quality Gates
- `citation_required`: `True`
- `unresolved_claims_block`: `True`
- `peer_check_required`: `True`
- `consistency_required`: `True`
- `scope_required`: `True`
- `reproducibility_required`: `True`
