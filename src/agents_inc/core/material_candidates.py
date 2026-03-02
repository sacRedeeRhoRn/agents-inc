from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Dict, List, Tuple

from agents_inc.core.fabric_lib import load_yaml, write_text

REQUIRED_MATERIAL_GROUPS = [
    "literature-intelligence",
    "data-curation",
    "material-scientist",
    "polymorphism-researcher",
    "developer",
    "quality-assurance",
    "designer",
]

_COMPOSITION_RE = re.compile(r"\b([A-Z][a-z]?(?:[0-9]{0,2})?(?:[A-Z][a-z]?(?:[0-9]{0,2})?)+)\b")
_SPACE_GROUP_RE = re.compile(r"\b(P[0-9_]{2,4}|P2_13|P213|P4_132|P3_121|P3_221)\b", re.IGNORECASE)


def compile_candidates_from_artifacts(
    *, project_dir: Path, selected_groups: List[str], objective: str
) -> dict:
    rows: List[dict] = []
    required_groups = [group for group in REQUIRED_MATERIAL_GROUPS if group in selected_groups]
    per_group = {}

    for group_id in selected_groups:
        handoff_path = project_dir / "agent-groups" / group_id / "exposed" / "handoff.json"
        payload = {}
        if handoff_path.exists():
            loaded = load_yaml(handoff_path)
            if isinstance(loaded, dict):
                payload = loaded
        status = str(payload.get("status") or "").strip().upper()
        claims = payload.get("claims_with_citations")
        if not isinstance(claims, list):
            claims = []
        candidates = _extract_candidates_from_payload(group_id, payload, claims)
        rows.extend(candidates)
        per_group[group_id] = {
            "handoff_path": str(handoff_path),
            "status": status or "UNKNOWN",
            "candidate_count": len(candidates),
        }

    missing_required = [
        group_id
        for group_id in required_groups
        if str(per_group.get(group_id, {}).get("status") or "").upper() != "COMPLETE"
    ]

    deduped: Dict[Tuple[str, str], dict] = {}
    for row in rows:
        comp = str(row.get("composition") or "").strip()
        sg = str(row.get("space_group") or "").strip()
        if not comp or not sg:
            continue
        key = (comp, sg)
        if key in deduped:
            continue
        deduped[key] = row

    compiled = list(deduped.values())
    compiled.sort(key=lambda item: (str(item.get("composition")), str(item.get("space_group"))))

    return {
        "objective": objective,
        "required_groups": required_groups,
        "missing_required_groups": missing_required,
        "group_summary": per_group,
        "candidates": compiled,
        "candidate_count": len(compiled),
    }


def write_compiled_candidates(project_root: Path, compiled: List[dict]) -> dict:
    out_dir = project_root / "outputs" / "material"
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "compiled_candidates.csv"
    md_path = out_dir / "compiled_candidates.md"

    fields = [
        "composition",
        "space_group",
        "metastability_rationale",
        "topological_indicator",
        "predicted_resistivity_trend_uohm_cm_300K",
        "synthesis_window",
        "confidence",
        "citation_url",
        "source_group",
    ]
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in compiled:
            writer.writerow({field: str(row.get(field) or "") for field in fields})

    lines = [
        "# Compiled Material Candidates",
        "",
        "| Composition | Space Group | Resistivity Trend (uohm*cm @300K) | Confidence | Source Group | Citation |",
        "|---|---|---:|---|---|---|",
    ]
    for row in compiled:
        lines.append(
            "| {0} | {1} | {2} | {3} | {4} | {5} |".format(
                row.get("composition", ""),
                row.get("space_group", ""),
                row.get("predicted_resistivity_trend_uohm_cm_300K", ""),
                row.get("confidence", ""),
                row.get("source_group", ""),
                row.get("citation_url", ""),
            )
        )
    write_text(md_path, "\n".join(lines).rstrip() + "\n")

    return {
        "csv_path": str(csv_path),
        "md_path": str(md_path),
    }


def write_ranked_candidates_from_compiled(project_root: Path) -> dict:
    material_dir = project_root / "outputs" / "material"
    in_path = material_dir / "compiled_candidates.csv"
    out_path = material_dir / "compiled_ranked.csv"
    if not in_path.exists():
        return {"ranked_path": str(out_path), "ranked_count": 0}

    with in_path.open("r", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    scored: List[dict] = []
    for row in rows:
        score = _material_score_local(row)
        merged = dict(row)
        merged["material_priority_score"] = f"{score:.3f}"
        scored.append(merged)
    scored.sort(
        key=lambda item: float(str(item.get("material_priority_score") or 0.0)), reverse=True
    )
    if scored:
        with out_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(scored[0].keys()))
            writer.writeheader()
            writer.writerows(scored)
    return {"ranked_path": str(out_path), "ranked_count": len(scored)}


def _extract_candidates_from_payload(
    group_id: str, payload: dict, claims: List[dict]
) -> List[dict]:
    rows: List[dict] = []

    explicit = payload.get("candidates")
    if isinstance(explicit, list):
        for item in explicit:
            if not isinstance(item, dict):
                continue
            row = _normalize_candidate(item, group_id)
            if row:
                rows.append(row)

    for claim in claims:
        if not isinstance(claim, dict):
            continue
        text = str(claim.get("claim") or claim.get("text") or "").strip()
        if not text:
            continue
        citation = str(claim.get("citation") or "").strip()
        for comp, sg in _extract_comp_sg_pairs(text):
            rows.append(
                {
                    "composition": comp,
                    "space_group": sg,
                    "metastability_rationale": text[:220],
                    "topological_indicator": "artifact-derived claim",
                    "predicted_resistivity_trend_uohm_cm_300K": "tbd",
                    "synthesis_window": "tbd",
                    "confidence": "medium",
                    "citation_url": citation,
                    "source_group": group_id,
                }
            )

    return rows


def _normalize_candidate(item: dict, group_id: str) -> dict | None:
    composition = str(item.get("composition") or "").strip()
    space_group = str(item.get("space_group") or "").strip()
    if not composition or not space_group:
        return None
    return {
        "composition": composition,
        "space_group": space_group,
        "metastability_rationale": str(item.get("metastability_rationale") or "artifact-derived"),
        "topological_indicator": str(item.get("topological_indicator") or "artifact-derived"),
        "predicted_resistivity_trend_uohm_cm_300K": str(
            item.get("predicted_resistivity_trend_uohm_cm_300K") or "tbd"
        ),
        "synthesis_window": str(item.get("synthesis_window") or "tbd"),
        "confidence": str(item.get("confidence") or "medium"),
        "citation_url": str(item.get("citation_url") or item.get("citation") or ""),
        "source_group": group_id,
    }


def _extract_comp_sg_pairs(text: str) -> List[Tuple[str, str]]:
    comps = [match.group(1) for match in _COMPOSITION_RE.finditer(text)]
    sgs = [match.group(1).upper() for match in _SPACE_GROUP_RE.finditer(text)]
    pairs: List[Tuple[str, str]] = []
    if not comps or not sgs:
        return pairs
    for comp in comps[:4]:
        for sg in sgs[:2]:
            pair = (comp, sg)
            if pair not in pairs:
                pairs.append(pair)
    return pairs


def _material_score_local(row: dict) -> float:
    comp = str(row.get("composition") or "")
    sg = str(row.get("space_group") or "").lower()
    topo = str(row.get("topological_indicator") or "").lower()
    rho = str(row.get("predicted_resistivity_trend_uohm_cm_300K") or "999-999")

    vals: List[float] = []
    for part in rho.replace(" ", "").split("-"):
        try:
            vals.append(float(part))
        except Exception:
            continue
    rho_mid = sum(vals) / len(vals) if vals else 999.0
    chiral_bonus = 1.20 if ("p213" in sg or "p2_13" in sg or "chiral" in sg) else 1.0
    topo_bonus = (
        1.15 if any(item in topo for item in ["weyl", "multifold", "berry", "semimetal"]) else 1.0
    )
    cosi_bonus = 1.10 if "CoSi" in comp else 1.0
    uncertainty_penalty = 0.92 if "low" in str(row.get("confidence") or "").lower() else 1.0
    return (
        (1000.0 / max(rho_mid, 1.0)) * chiral_bonus * topo_bonus * cosi_bonus * uncertainty_penalty
    )
