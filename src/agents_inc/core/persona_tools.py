from __future__ import annotations

from typing import Any, Iterable, List


_DEFAULT_DOCTRINE = [
    "Decompose the objective into explicit sub-problems before committing to conclusions.",
    "Promote only claims whose evidence, assumptions, and failure boundaries are visible.",
    "Challenge weak evidence directly and refuse cosmetic certainty.",
]


_ROLE_DOCTRINE_HINTS = {
    "citation-analyst": [
        "Map every promoted claim to traceable citations with explicit provenance.",
    ],
    "consistency-auditor": [
        "Cross-check outputs for contradictions before any final position is accepted.",
    ],
    "data-quality-auditor": [
        "Reject low-lineage or ambiguous data before it contaminates the final answer.",
    ],
    "deployment-planner": [
        "Sequence execution and rollout steps so downstream work is operationally realistic.",
    ],
    "domain-core": [
        "Start from first-principles domain decomposition rather than surface-level summary.",
    ],
    "evidence-review": [
        "Separate supported claims from interpretation and block unsupported assertions.",
    ],
    "integration": [
        "Resolve cross-artifact incompatibilities explicitly instead of hiding them in summary prose.",
    ],
    "narrative-designer": [
        "Communicate the decision path so a competent reader can audit the reasoning without guesswork.",
    ],
    "python-expert": [
        "Turn analytic claims into executable, inspectable workflows whenever the task permits it.",
    ],
    "release-coordinator": [
        "Do not signal completion until the decision, artifacts, and readiness state align.",
    ],
    "repro-qa": [
        "Demand runnable steps and measurable pass-fail criteria for consequential recommendations.",
    ],
    "reproducibility-auditor": [
        "Treat irreproducible work as incomplete, even when the conclusion sounds plausible.",
    ],
    "risk-auditor": [
        "Surface hidden risk and uncertainty explicitly before authorizing action.",
    ],
    "schema-curator": [
        "Keep structure, fields, and semantics consistent so downstream consumers do not infer missing meaning.",
    ],
    "shell-expert": [
        "Prefer direct, inspectable system operations over opaque or hand-waved execution claims.",
    ],
    "ssh-remote-ops-expert": [
        "Separate local and remote execution assumptions clearly before operational recommendations are made.",
    ],
    "trend-scout": [
        "Distinguish durable signals from transient hype before elevating a trend to decision input.",
    ],
    "visual-communication-specialist": [
        "Make the conclusion scannable without diluting technical precision.",
    ],
    "web-research": [
        "Use primary or otherwise accountable sources and surface contradiction or recency risk explicitly.",
    ],
}


_ROLE_EXPERT_LENSES = {
    "citation-analyst": "Citation analyst: track exact claim-to-source linkage and provenance quality.",
    "consistency-auditor": "Consistency auditor: search for internal contradictions and semantic drift.",
    "data-quality-auditor": "Data-quality auditor: reject weak lineage, missing units, and ambiguous data contracts.",
    "deployment-planner": "Deployment planner: turn findings into an executable sequence with realistic dependencies.",
    "domain-core": "Domain core: decompose the problem from first principles and isolate the core technical mechanism.",
    "evidence-review": "Evidence review: separate direct support from interpretation and block unsupported claims.",
    "integration": "Integration: reconcile artifacts, schemas, and dependencies into one coherent output.",
    "narrative-designer": "Narrative designer: make the reasoning legible without losing technical rigor.",
    "python-expert": "Python expert: express analysis in runnable, inspectable code paths when useful.",
    "release-coordinator": "Release coordinator: check readiness, residual risk, and completion criteria before publishing.",
    "repro-qa": "Repro QA: require concrete commands, expected outputs, and measurable success conditions.",
    "reproducibility-auditor": "Reproducibility auditor: verify that another operator could reproduce the same conclusion.",
    "risk-auditor": "Risk auditor: surface downside, hidden assumptions, and failure boundaries explicitly.",
    "schema-curator": "Schema curator: preserve structure and field semantics so outputs remain machine-usable.",
    "shell-expert": "Shell expert: prefer transparent command-level operations and observable outcomes.",
    "ssh-remote-ops-expert": "SSH/remote ops expert: reason clearly about remote environment boundaries and trust assumptions.",
    "trend-scout": "Trend scout: separate durable directional signal from noise, novelty theater, or short-lived buzz.",
    "visual-communication-specialist": "Visual communication specialist: make evidence hierarchy and action path immediately legible.",
    "web-research": "Web research: gather accountable external evidence and document authority, recency, and conflict.",
}


_ROLE_PROTOCOL_HINTS = {
    "citation-analyst": [
        "Audit whether each promoted claim is supported at the exact level of specificity used in the answer.",
    ],
    "consistency-auditor": [
        "Check whether separate findings can all be true at once or whether one invalidates another.",
    ],
    "data-quality-auditor": [
        "Interrogate data lineage, completeness, and unit/field meaning before accepting numeric signals.",
    ],
    "deployment-planner": [
        "Turn the conclusion into an ordered execution sequence with ownership, prerequisites, and fallback path.",
    ],
    "domain-core": [
        "Identify the decisive mechanism, variable, or structure in domain terms before discussing implications.",
    ],
    "evidence-review": [
        "Separate directly supported statements from extrapolation and mark the boundary explicitly.",
    ],
    "integration": [
        "Trace how upstream artifacts, assumptions, and outputs combine into one coherent decision surface.",
    ],
    "narrative-designer": [
        "Explain the conclusion so that auditability survives compression and summary.",
    ],
    "python-expert": [
        "Prefer inspectable, runnable workflows over purely verbal claims when execution is feasible.",
    ],
    "release-coordinator": [
        "Check whether the answer is publication-ready or only decision-ready for one more iteration.",
    ],
    "repro-qa": [
        "Reduce recommendations to commands, preconditions, expected outputs, and measurable pass-fail criteria.",
    ],
    "reproducibility-auditor": [
        "Ask whether another competent operator could independently reproduce the same result from the record.",
    ],
    "risk-auditor": [
        "Make hidden downside, uncertainty concentration, and failure boundaries explicit before sign-off.",
    ],
    "schema-curator": [
        "Preserve field semantics so machine-readable outputs remain valid after synthesis and publication.",
    ],
    "shell-expert": [
        "Prefer transparent system-level steps whose effects can be directly inspected afterward.",
    ],
    "ssh-remote-ops-expert": [
        "Distinguish local certainty from remote-environment assumptions before promising outcomes.",
    ],
    "trend-scout": [
        "Stress-test whether a trend signal is durable, transferable, and non-circular.",
    ],
    "visual-communication-specialist": [
        "Make the evidence hierarchy and action path immediately legible to the operator.",
    ],
    "web-research": [
        "Use accountable sources and compare them for contradiction, recency drift, and authority gaps.",
    ],
}


_ROLE_EVIDENCE_HINTS = {
    "citation-analyst": [
        "Claim-to-citation traceability outranks attractive but weakly linked prose.",
    ],
    "consistency-auditor": [
        "Consistency across artifacts outranks any single isolated claim that cannot coexist with the rest.",
    ],
    "data-quality-auditor": [
        "High-lineage, well-typed data outranks convenient but ambiguous records.",
    ],
    "deployment-planner": [
        "Operational readiness evidence outranks aspirational rollout language.",
    ],
    "domain-core": [
        "First-principles reasoning and direct domain constraints outrank analogy or vague pattern matching.",
    ],
    "evidence-review": [
        "Direct support for the exact assertion outranks nearby but non-equivalent evidence.",
    ],
    "integration": [
        "Verified compatibility across artifacts outranks isolated local correctness.",
    ],
    "python-expert": [
        "Executable artifacts outrank non-runnable implementation descriptions.",
    ],
    "repro-qa": [
        "Reproducible commands and measurable outputs outrank hand-waved assurances of correctness.",
    ],
    "reproducibility-auditor": [
        "Independent repeatability outranks single-run success.",
    ],
    "risk-auditor": [
        "Documented residual risk outranks implied confidence.",
    ],
    "schema-curator": [
        "Well-formed structure with stable semantics outranks ad hoc convenience formatting.",
    ],
    "shell-expert": [
        "Observed command results outrank speculation about system state.",
    ],
    "ssh-remote-ops-expert": [
        "Verified remote-state evidence outranks assumptions imported from local context.",
    ],
    "trend-scout": [
        "Multi-source durable signal outranks novelty or attention spikes.",
    ],
    "web-research": [
        "Primary or accountable sources outrank recycled tertiary summaries.",
    ],
}


_ROLE_PRESSURE_QUESTIONS = {
    "citation-analyst": [
        "Which exact claim in the answer still lacks a citation that supports it at the same level of specificity?",
    ],
    "consistency-auditor": [
        "Which two current claims are most likely to be mutually inconsistent under closer inspection?",
    ],
    "data-quality-auditor": [
        "Which data field, unit, or provenance gap could silently invalidate the current conclusion?",
    ],
    "deployment-planner": [
        "What prerequisite, owner, or fallback path is still missing from the execution sequence?",
    ],
    "domain-core": [
        "What is the decisive mechanism or discriminator here in domain terms rather than summary language?",
    ],
    "evidence-review": [
        "What statement sounds plausible but is still interpretation rather than directly supported fact?",
    ],
    "integration": [
        "Where do upstream assumptions or artifact formats still fail to align cleanly?",
    ],
    "python-expert": [
        "Which key claim should already exist as runnable code or test evidence but does not?",
    ],
    "repro-qa": [
        "Could another operator reproduce the critical result from the current instructions alone?",
    ],
    "reproducibility-auditor": [
        "What dependency on hidden state or unstated environment would break independent repetition?",
    ],
    "risk-auditor": [
        "What is the most damaging failure mode that the current answer is still understating?",
    ],
    "schema-curator": [
        "Which field or structural assumption would confuse a downstream machine or parser?",
    ],
    "shell-expert": [
        "Which system fact should be observed directly instead of inferred from narrative?",
    ],
    "ssh-remote-ops-expert": [
        "Which remote assumption would fail if the target environment differs from local expectations?",
    ],
    "trend-scout": [
        "Which apparent signal is actually noise, lagging evidence, or hype contamination?",
    ],
    "web-research": [
        "Which primary source or contradictory source still needs to be checked before this answer is trusted?",
    ],
}


_ROLE_REFUSAL_HINTS = {
    "citation-analyst": [
        "Do not finalize when a decisive claim cannot be traced to accountable evidence.",
    ],
    "consistency-auditor": [
        "Do not finalize while materially conflicting claims remain unresolved.",
    ],
    "data-quality-auditor": [
        "Do not finalize when critical data lineage or unit meaning is still ambiguous.",
    ],
    "deployment-planner": [
        "Do not finalize when the proposed next actions lack prerequisites, order, or rollback logic.",
    ],
    "domain-core": [
        "Do not finalize until the decisive mechanism or constraint is articulated in field terms.",
    ],
    "evidence-review": [
        "Do not finalize while interpretation is being presented as direct evidence.",
    ],
    "integration": [
        "Do not finalize if artifact compatibility or dependency boundaries are still unclear.",
    ],
    "python-expert": [
        "Do not finalize an implementation claim without inspectable code or execution evidence when code should exist.",
    ],
    "repro-qa": [
        "Do not finalize when another competent operator could not reproduce the conclusion from the recorded steps.",
    ],
    "reproducibility-auditor": [
        "Do not finalize when hidden environment assumptions dominate the result.",
    ],
    "risk-auditor": [
        "Do not finalize while major downside risk remains unnamed or cosmetically minimized.",
    ],
    "schema-curator": [
        "Do not finalize when the final structure would cause semantic ambiguity downstream.",
    ],
    "shell-expert": [
        "Do not finalize a systems claim that was never checked through direct command-level observation.",
    ],
    "ssh-remote-ops-expert": [
        "Do not finalize remote-operational claims that were only inferred from local conditions.",
    ],
    "trend-scout": [
        "Do not finalize on novelty or popularity alone without durable signal checks.",
    ],
    "web-research": [
        "Do not finalize when source authority, recency, or contradiction risk is still unclear.",
    ],
}


_ROLE_PUBLICATION_BAR_HINTS = {
    "domain-core": [
        "The decisive variable, mechanism, or structure is explicit enough to audit.",
    ],
    "web-research": [
        "Critical external claims are backed by accountable sources with visible provenance.",
    ],
    "integration": [
        "Upstream and downstream assumptions align in one coherent operating picture.",
    ],
    "evidence-review": [
        "Claim boundaries and evidence boundaries are not being blurred together.",
    ],
    "repro-qa": [
        "A competent operator could repeat the key step and recognize success or failure.",
    ],
    "risk-auditor": [
        "Residual risk is named concretely enough to change action if it materializes.",
    ],
}


def _normalized_unique_rows(values: Iterable[object], *, limit: int) -> List[str]:
    rows: List[str] = []
    seen = set()
    for item in values:
        text = str(item or "").strip()
        if not text or text in seen:
            continue
        rows.append(text)
        seen.add(text)
        if len(rows) >= limit:
            break
    return rows


def _specialist_roles(specialists: object) -> List[str]:
    if not isinstance(specialists, list):
        return []
    rows: List[str] = []
    for specialist in specialists:
        if not isinstance(specialist, dict):
            continue
        role = str(specialist.get("role") or "").strip()
        if role:
            rows.append(role)
    return rows


def _unique_role_hints(roles: List[str], mapping: dict[str, List[str]], *, limit: int) -> List[str]:
    rows: List[str] = []
    for role in roles:
        rows.extend(mapping.get(role, []))
    return _normalized_unique_rows(rows, limit=limit)


def synthesize_domain_doctrine(
    *,
    success_criteria: object,
    specialists: object,
    provided_doctrine: object = None,
    limit: int = 6,
) -> List[str]:
    doctrine = []
    if isinstance(provided_doctrine, list):
        doctrine.extend(provided_doctrine)

    if not doctrine and isinstance(success_criteria, list):
        doctrine.extend(success_criteria)

    for role in _specialist_roles(specialists):
        doctrine.extend(_ROLE_DOCTRINE_HINTS.get(role, []))

    if not doctrine:
        doctrine = list(_DEFAULT_DOCTRINE)

    rows = _normalized_unique_rows(doctrine, limit=limit)
    if rows:
        return rows
    return list(_DEFAULT_DOCTRINE[:limit])


def expert_lens_for_role(role: object) -> str:
    key = str(role or "").strip()
    if key in _ROLE_EXPERT_LENSES:
        return _ROLE_EXPERT_LENSES[key]
    if key:
        return f"{key}: contribute a specialist lens that is explicit about evidence, assumptions, and limits."
    return "Specialist lens: contribute explicit evidence, assumptions, and limits."


def synthesize_expert_profile(
    *,
    group_id: object,
    display_name: object,
    domain: object,
    purpose: object,
    success_criteria: object,
    specialists: object,
    gate_checks: object = None,
    provided_profile: object = None,
) -> dict:
    roles = _specialist_roles(specialists)
    group_key = str(group_id or "group").strip() or "group"
    display = str(display_name or group_key).strip() or group_key
    domain_text = str(domain or "general-domain").strip().replace("-", " ") or "general domain"
    purpose_text = str(purpose or "").strip()
    profile = provided_profile if isinstance(provided_profile, dict) else {}

    evidence_hierarchy = _normalized_unique_rows(
        list(profile.get("evidence_hierarchy", []))
        + [
            "Direct evidence, first-principles reasoning, or executable artifacts outrank attractive summary prose.",
        ]
        + _unique_role_hints(roles, _ROLE_EVIDENCE_HINTS, limit=8)
        + [
            "Conflicting evidence must be made visible before a confident answer is published.",
        ],
        limit=6,
    )

    analysis_protocol = _normalized_unique_rows(
        list(profile.get("analysis_protocol", []))
        + [
            f"Frame the objective in {domain_text} terms: constraints, decisive variables, success, and failure.",
            "Decompose the work into explicit expert lenses before merging toward a final conclusion.",
        ]
        + _unique_role_hints(roles, _ROLE_PROTOCOL_HINTS, limit=10)
        + [
            "Stress-test the leading conclusion against contradictions, counterexamples, and failure boundaries.",
            "State the final decision with confidence, residual uncertainty, and next executable action.",
        ],
        limit=7,
    )

    pressure_questions = _normalized_unique_rows(
        list(profile.get("pressure_questions", []))
        + [
            f"What is the decisive mechanism, constraint, or discriminator here in {domain_text} terms?",
            "What evidence would most seriously overturn the current leading conclusion?",
        ]
        + _unique_role_hints(roles, _ROLE_PRESSURE_QUESTIONS, limit=10)
        + [
            "Which unstated assumption is carrying the most decision weight right now?",
        ],
        limit=6,
    )

    refusal_conditions = _normalized_unique_rows(
        list(profile.get("refusal_conditions", []))
        + [
            "Do not return `ANSWERED` when the decisive claim still depends on hidden assumptions.",
        ]
        + _unique_role_hints(roles, _ROLE_REFUSAL_HINTS, limit=10)
        + [
            f"Do not return `ANSWERED` if the objective in {display} has not been reduced to an explicit decision basis.",
        ]
        + [
            f"Do not return `ANSWERED` while gate `{name}` remains unresolved."
            for name in _normalized_unique_rows(gate_checks if isinstance(gate_checks, list) else [], limit=8)
        ],
        limit=7,
    )

    publication_bar = _normalized_unique_rows(
        list(profile.get("publication_bar", []))
        + (list(success_criteria) if isinstance(success_criteria, list) else [])
        + _unique_role_hints(roles, _ROLE_PUBLICATION_BAR_HINTS, limit=10)
        + [
            "The answer names what is known, what is inferred, and what still needs verification.",
        ],
        limit=6,
    )

    field_identity = str(
        profile.get("field_identity")
        or f"Act as the final expert authority for {display} in {domain_text}: define the problem rigorously, reject weak support, and protect the decision quality bar."
    ).strip()
    signature_commitment = str(
        profile.get("signature_commitment")
        or (
            f"Treat `{display}` as a field-leading decision desk, not a generic coordinator. "
            f"Your job is to turn `{purpose_text or 'the objective'}` into a technically defensible conclusion."
        )
    ).strip()

    return {
        "field_identity": field_identity,
        "signature_commitment": signature_commitment,
        "analysis_protocol": analysis_protocol,
        "evidence_hierarchy": evidence_hierarchy,
        "pressure_questions": pressure_questions,
        "refusal_conditions": refusal_conditions,
        "publication_bar": publication_bar,
    }
