# Quality Assurance Group - proj-battery-001

## Mission
Audit technical outputs for reproducibility, consistency, and decision-risk control.

## Group Identity
- `group_id`: `quality-assurance`
- `template_version`: `2.0.0`
- `tool_profile`: `qa-default`
- `head_agent`: `quality-assurance-head`
- `head_skill`: `proj-proj-battery-001-quality-assurance-quality-assurance-head`

## Specialist Roster
- `reproducibility-auditor`: Reproducibility checks, parameter traceability, and artifact completeness (skill: `proj-proj-battery-001-quality-assurance-reproducibility-auditor`)
- `consistency-auditor`: Cross-document consistency checks and contradiction detection (skill: `proj-proj-battery-001-quality-assurance-consistency-auditor`)
- `risk-auditor`: Risk classification, severity tagging, and mitigation recommendation framing (skill: `proj-proj-battery-001-quality-assurance-risk-auditor`)
- `integration-specialist`: Cross-artifact integration and consumability checks for Quality Assurance Group (skill: `proj-proj-battery-001-quality-assurance-integration-specialist`)
- `evidence-review-specialist`: Claim-level evidence review and citation sufficiency for Quality Assurance Group (skill: `proj-proj-battery-001-quality-assurance-evidence-review-b028fe4b`)
- `web-research-specialist`: Gather web-published references and extract citation-ready evidence. (skill: `proj-proj-battery-001-quality-assurance-web-research-specialist`)

## Work Directories
- `generated/projects/proj-battery-001/work/quality-assurance/reproducibility-auditor`
- `generated/projects/proj-battery-001/work/quality-assurance/consistency-auditor`
- `generated/projects/proj-battery-001/work/quality-assurance/risk-auditor`
- `generated/projects/proj-battery-001/work/quality-assurance/integration-specialist`
- `generated/projects/proj-battery-001/work/quality-assurance/evidence-review-specialist`
- `generated/projects/proj-battery-001/work/quality-assurance/web-research-specialist`

## Artifact Partition
- Internal specialist artifacts: `agent-groups/quality-assurance/internal/<specialist>/...`
- Exposed group artifacts: `agent-groups/quality-assurance/exposed/...`
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
- `repro_audit.md` from `reproducibility-auditor`
- `claims_with_citations.md` from `reproducibility-auditor`
- `work.md` from `reproducibility-auditor`
- `handoff.json` from `reproducibility-auditor`
- `consistency_audit.md` from `consistency-auditor`
- `claims_with_citations.md` from `consistency-auditor`
- `work.md` from `consistency-auditor`
- `handoff.json` from `consistency-auditor`
- `risk_register.md` from `risk-auditor`
- `claims_with_citations.md` from `risk-auditor`
- `work.md` from `risk-auditor`
- `handoff.json` from `risk-auditor`
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
