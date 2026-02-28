# Material Scientist Group - proj-battery-001

## Mission
Route and quality-gate specialist outputs for theoretical and computational materials science.

## Group Identity
- `group_id`: `material-scientist`
- `template_version`: `2.0.0`
- `tool_profile`: `science-default`
- `head_agent`: `material-scientist-head`
- `head_skill`: `proj-proj-battery-001-material-scientist-material-scientist-head`

## Specialist Roster
- `thermodynamics-specialist`: Phase stability, CALPHAD logic, free-energy reasoning (skill: `proj-proj-battery-001-material-scientist-thermodynamics-6ace8773`)
- `electronic-structure-specialist`: DFT setup, band structure interpretation, density-of-states analysis (skill: `proj-proj-battery-001-material-scientist-electronic-str-d41bc6b7`)
- `atomistic-simulation-specialist`: Atomistic simulation strategy, interatomic potential reasoning, trajectory interpretation (skill: `proj-proj-battery-001-material-scientist-atomistic-simu-a6a50b3f`)
- `integration-specialist`: Cross-artifact integration and consumability checks for Material Scientist Group (skill: `proj-proj-battery-001-material-scientist-integration-specialist`)
- `evidence-review-specialist`: Claim-level evidence review and citation sufficiency for Material Scientist Group (skill: `proj-proj-battery-001-material-scientist-evidence-revie-a7b4e65d`)
- `repro-qa-specialist`: Reproducibility and quality assurance checks for Material Scientist Group (skill: `proj-proj-battery-001-material-scientist-repro-qa-specialist`)

## Work Directories
- `generated/projects/proj-battery-001/work/material-scientist/thermodynamics-specialist`
- `generated/projects/proj-battery-001/work/material-scientist/electronic-structure-specialist`
- `generated/projects/proj-battery-001/work/material-scientist/atomistic-simulation-specialist`
- `generated/projects/proj-battery-001/work/material-scientist/integration-specialist`
- `generated/projects/proj-battery-001/work/material-scientist/evidence-review-specialist`
- `generated/projects/proj-battery-001/work/material-scientist/repro-qa-specialist`

## Artifact Partition
- Internal specialist artifacts: `agent-groups/material-scientist/internal/<specialist>/...`
- Exposed group artifacts: `agent-groups/material-scientist/exposed/...`
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
- `assumptions.md` from `thermodynamics-specialist`
- `claims_with_citations.md` from `thermodynamics-specialist`
- `phase_stability_notes.md` from `thermodynamics-specialist`
- `work.md` from `thermodynamics-specialist`
- `handoff.json` from `thermodynamics-specialist`
- `assumptions.md` from `electronic-structure-specialist`
- `claims_with_citations.md` from `electronic-structure-specialist`
- `electronic_summary.md` from `electronic-structure-specialist`
- `work.md` from `electronic-structure-specialist`
- `handoff.json` from `electronic-structure-specialist`
- `assumptions.md` from `atomistic-simulation-specialist`
- `claims_with_citations.md` from `atomistic-simulation-specialist`
- `simulation_plan.md` from `atomistic-simulation-specialist`
- `work.md` from `atomistic-simulation-specialist`
- `handoff.json` from `atomistic-simulation-specialist`
- `work.md` from `integration-specialist`
- `handoff.json` from `integration-specialist`
- `work.md` from `evidence-review-specialist`
- `handoff.json` from `evidence-review-specialist`
- `work.md` from `repro-qa-specialist`
- `handoff.json` from `repro-qa-specialist`

## Quality Gates
- `citation_required`: `True`
- `unresolved_claims_block`: `True`
- `peer_check_required`: `True`
- `consistency_required`: `True`
- `scope_required`: `True`
- `reproducibility_required`: `True`
