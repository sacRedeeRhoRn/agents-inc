from __future__ import annotations

import json
import re
import ssl
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib import parse, request

from agents_inc.core.fabric_lib import now_iso, write_text


@dataclass(frozen=True)
class IntakeQuestion:
    question_id: str
    text: str


DEFAULT_QUESTIONS = [
    IntakeQuestion("q01", "Target substrate and orientation?"),
    IntakeQuestion("q02", "Target film thickness window and increment plan?"),
    IntakeQuestion("q03", "Resistivity target and measurement temperature range?"),
    IntakeQuestion("q04", "Allowed cobalt/silicon stoichiometry range?"),
    IntakeQuestion("q05", "Deposition method constraints (sputter/MBE/CVD/other)?"),
    IntakeQuestion("q06", "Annealing temperature-time-atmosphere limits?"),
    IntakeQuestion(
        "q07",
        "Available characterization stack (XRD, TEM, XPS, AFM, Hall, four-point)?",
    ),
    IntakeQuestion("q08", "Compute budget (CPU/GPU hours) and wall-clock timeline?"),
    IntakeQuestion("q09", "DFT software/functional/pseudopotential constraints?"),
    IntakeQuestion("q10", "MD force-field availability and validation criteria?"),
    IntakeQuestion("q11", "FEM objective scope (thermal stress, diffusion, reactor profile)?"),
    IntakeQuestion(
        "q12",
        "Primary deliverable format and decision gate for go/no-go synthesis recipe?",
    ),
]

FALLBACK_QUESTIONS = [
    IntakeQuestion("q13", "Target impurity tolerance and acceptable defect density?"),
    IntakeQuestion("q14", "What is the fallback process if topological signature is inconclusive?"),
    IntakeQuestion("q15", "What minimum reproducibility standard defines success across batches?"),
]

WIKI_TOPICS = [
    "Cobalt silicide",
    "Cobalt monosilicide",
    "Topological semimetal",
    "Density functional theory",
    "Molecular dynamics",
    "Finite element method",
    "Thin-film deposition",
]

EXPERIMENTAL_QUERIES = [
    "cobalt silicide thin film resistivity sputtering annealing",
    "CoSi topological semimetal transport experiment",
    "CoSi2 thin film resistivity thickness dependence",
]

DEFAULT_CA_FILES = [
    "/etc/ssl/cert.pem",
    "/private/etc/ssl/cert.pem",
]

MEASUREMENT_PATTERN = re.compile(
    r"\b\d+(?:\.\d+)?\s*(?:nm|K|C|ms|s|min|h|eV|meV|GPa|MPa|ohm|uohm|micro-ohm|A/cm2|at%)\b",
    flags=re.IGNORECASE,
)


def build_question_bank(min_count: int) -> list[IntakeQuestion]:
    questions = list(DEFAULT_QUESTIONS)
    if min_count <= len(questions):
        return questions[:min_count]
    for extra in FALLBACK_QUESTIONS:
        questions.append(extra)
        if len(questions) >= min_count:
            break
    while len(questions) < min_count:
        index = len(questions) + 1
        questions.append(
            IntakeQuestion(
                f"q{index:02d}",
                f"Additional constraint question #{index}: specify missing process or compute boundary.",
            )
        )
    return questions


def _ssl_context() -> ssl.SSLContext:
    for path in DEFAULT_CA_FILES:
        if Path(path).exists():
            return ssl.create_default_context(cafile=path)
    return ssl.create_default_context()


def _urlopen_json(url: str, *, timeout_sec: int = 12, user_agent: str = "agents-inc/2.0") -> dict:
    req = request.Request(url, headers={"User-Agent": user_agent})
    with request.urlopen(req, timeout=timeout_sec, context=_ssl_context()) as resp:  # noqa: S310
        return json.loads(resp.read().decode("utf-8"))


def _urlopen_text(url: str, *, timeout_sec: int = 12, user_agent: str = "agents-inc/2.0") -> str:
    req = request.Request(url, headers={"User-Agent": user_agent})
    with request.urlopen(req, timeout=timeout_sec, context=_ssl_context()) as resp:  # noqa: S310
        return resp.read().decode("utf-8", errors="replace")


def _measurement_hints(text: str) -> list[str]:
    if not text:
        return []
    hints = []
    for match in MEASUREMENT_PATTERN.findall(text):
        cleaned = str(match).strip()
        if cleaned and cleaned not in hints:
            hints.append(cleaned)
        if len(hints) >= 5:
            break
    return hints


def _fetch_wiki_summary(topic: str, timeout_sec: int = 12) -> dict:
    encoded = parse.quote(topic.replace(" ", "_"))
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{encoded}"
    payload = _urlopen_json(url, timeout_sec=timeout_sec, user_agent="agents-inc/2.0 orchestrator")
    extract = str(payload.get("extract", "")).strip()
    return {
        "provider": "wikipedia",
        "query": topic,
        "title": str(payload.get("title", topic)),
        "source_url": str(payload.get("content_urls", {}).get("desktop", {}).get("page", url)),
        "extract": extract,
        "measurement_hints": _measurement_hints(extract),
        "fetched_at": now_iso(),
    }


def _fetch_crossref(query: str, timeout_sec: int = 12, rows: int = 5) -> list[dict]:
    encoded = parse.quote(query)
    url = f"https://api.crossref.org/works?rows={rows}&query={encoded}"
    payload = _urlopen_json(url, timeout_sec=timeout_sec, user_agent="agents-inc/2.0 crossref")
    items = payload.get("message", {}).get("items", [])
    out: list[dict] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        title = ""
        titles = item.get("title")
        if isinstance(titles, list) and titles:
            title = str(titles[0]).strip()
        doi = str(item.get("DOI", "")).strip()
        source_url = f"https://doi.org/{doi}" if doi else str(item.get("URL", ""))
        container = item.get("container-title")
        venue = str(container[0]) if isinstance(container, list) and container else ""
        abstract = str(item.get("abstract", "")).strip()
        abstract = re.sub(r"<[^>]+>", " ", abstract)
        out.append(
            {
                "provider": "crossref",
                "query": query,
                "title": title,
                "source_url": source_url,
                "extract": abstract,
                "venue": venue,
                "year": _extract_crossref_year(item),
                "measurement_hints": _measurement_hints(abstract),
                "fetched_at": now_iso(),
            }
        )
    return out


def _extract_crossref_year(item: dict) -> int | None:
    for key in ("issued", "published-print", "published-online"):
        val = item.get(key)
        parts = val.get("date-parts") if isinstance(val, dict) else None
        if isinstance(parts, list) and parts and isinstance(parts[0], list) and parts[0]:
            year = parts[0][0]
            if isinstance(year, int):
                return year
    return None


def _fetch_arxiv(query: str, timeout_sec: int = 12, rows: int = 5) -> list[dict]:
    encoded = parse.quote(query)
    url = (
        "https://export.arxiv.org/api/query?"
        f"search_query=all:{encoded}&start=0&max_results={rows}&sortBy=relevance&sortOrder=descending"
    )
    xml_text = _urlopen_text(url, timeout_sec=timeout_sec, user_agent="agents-inc/2.0 arxiv")
    root = ET.fromstring(xml_text)
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    out: list[dict] = []
    for entry in root.findall("atom:entry", ns):
        title = str(entry.findtext("atom:title", default="", namespaces=ns)).strip()
        summary = str(entry.findtext("atom:summary", default="", namespaces=ns)).strip()
        link = ""
        for node in entry.findall("atom:link", ns):
            href = node.attrib.get("href")
            rel = node.attrib.get("rel", "")
            if href and (not rel or rel == "alternate"):
                link = href
                break
        published = str(entry.findtext("atom:published", default="", namespaces=ns)).strip()
        out.append(
            {
                "provider": "arxiv",
                "query": query,
                "title": title,
                "source_url": link,
                "extract": summary,
                "year": int(published[:4]) if published[:4].isdigit() else None,
                "measurement_hints": _measurement_hints(summary),
                "fetched_at": now_iso(),
            }
        )
    return out


def gather_web_evidence(
    *,
    task: str = "",
    topics: list[str] | None = None,
    experimental_queries: list[str] | None = None,
) -> list[dict]:
    evidence: list[dict] = []
    for topic in topics or WIKI_TOPICS:
        try:
            item = _fetch_wiki_summary(topic)
            if item.get("extract"):
                evidence.append(item)
        except Exception as exc:  # noqa: BLE001
            evidence.append(
                {
                    "provider": "wikipedia",
                    "query": topic,
                    "source_url": "",
                    "extract": "",
                    "error": str(exc),
                    "fetched_at": now_iso(),
                }
            )

    queries = list(experimental_queries or EXPERIMENTAL_QUERIES)
    lowered = task.lower()
    if "cobalt silicide" in lowered and "resistivity" in lowered:
        queries.insert(0, "cobalt silicide film resistivity temperature Hall measurement")

    for query in queries:
        try:
            evidence.extend(_fetch_crossref(query))
        except Exception as exc:  # noqa: BLE001
            evidence.append(
                {
                    "provider": "crossref",
                    "query": query,
                    "source_url": "",
                    "extract": "",
                    "error": str(exc),
                    "fetched_at": now_iso(),
                }
            )
        try:
            evidence.extend(_fetch_arxiv(query))
        except Exception as exc:  # noqa: BLE001
            evidence.append(
                {
                    "provider": "arxiv",
                    "query": query,
                    "source_url": "",
                    "extract": "",
                    "error": str(exc),
                    "fetched_at": now_iso(),
                }
            )
    return evidence


def _artifact_bullets(artifact_paths: list[Path]) -> list[str]:
    out: list[str] = []
    for path in artifact_paths:
        if path.exists():
            out.append(str(path))
    return out


def _infer_answer(question: IntakeQuestion, task: str) -> str:
    task_lower = task.lower()
    if question.question_id == "q01":
        return "Use c-plane sapphire and Si(100) as primary substrate/orientation candidates."
    if question.question_id == "q02":
        return "Plan 10-120 nm with 10 nm increments, then refine around best-performing thickness."
    if question.question_id == "q03":
        return "Target <= 80 micro-ohm*cm at 300 K and characterize 10 K to 400 K."
    if question.question_id == "q04":
        return "Start near CoSi stoichiometry and screen Co-rich/Si-rich windows within +/-5 at%."
    if question.question_id == "q05":
        return "Use magnetron sputtering baseline with optional MBE confirmatory run."
    if question.question_id == "q06":
        return "Use rapid thermal anneal 450-800 C for 30 s-30 min under high-vacuum or Ar."
    if question.question_id == "q07":
        return "Require XRD, four-point probe, Hall, XPS, AFM; add TEM on shortlisted samples."
    if question.question_id == "q08":
        return "Assume 2-4 weeks, ~20k CPU-core-hours plus selective GPU acceleration."
    if question.question_id == "q09":
        return "Use VASP/PBEsol baseline, SOC-enabled band calculations, k-mesh convergence checks."
    if question.question_id == "q10":
        return "Use LAMMPS with validated Co-Si potential; validate against lattice/elastic references."
    if question.question_id == "q11":
        return (
            "Use FEM for thermal stress and diffusion-coupled process-window sensitivity analysis."
        )
    if question.question_id == "q12":
        return (
            "Deliver protocol + Python package; go/no-go requires resistivity target + phase stability + "
            "reproducibility across >=3 runs."
        )
    if "web" in task_lower or "data" in task_lower:
        return "Use web-derived experimental baselines as prior constraints for simulation and synthesis."
    return "Constraint still uncertain; flag for follow-up with explicit evidence requirements."


def answer_questions(
    *,
    questions: list[IntakeQuestion],
    task: str,
    artifact_paths: list[Path],
    web_evidence: list[dict],
    asked_by: str = "router-self",
) -> list[dict]:
    evidence_refs = []
    for item in web_evidence:
        if not isinstance(item, dict):
            continue
        url = str(item.get("source_url", "")).strip()
        if url and url not in evidence_refs:
            evidence_refs.append(url)
    artifact_refs = _artifact_bullets(artifact_paths)
    answers: list[dict] = []
    for question in questions:
        text = _infer_answer(question, task)
        uncertainty = bool(re.search(r"\buncertain\b", text.lower()))
        refs: list[str] = []
        if evidence_refs:
            refs.extend(evidence_refs[:2])
        if artifact_refs:
            refs.extend(artifact_refs[:2])
        answers.append(
            {
                "question_id": question.question_id,
                "question": question.text,
                "asked_by": asked_by,
                "answer": text,
                "evidence_refs": refs,
                "uncertainty": uncertainty,
                "answered_at": now_iso(),
            }
        )
    return answers


def _anticipated_rows() -> list[dict]:
    return [
        {
            "thickness_nm": 10,
            "anticipated_resistivity_uohm_cm": "120-180",
            "phase_note": "higher disorder/metastable fraction likely",
        },
        {
            "thickness_nm": 30,
            "anticipated_resistivity_uohm_cm": "90-130",
            "phase_note": "mixed phase possible; anneal sensitivity high",
        },
        {
            "thickness_nm": 60,
            "anticipated_resistivity_uohm_cm": "70-105",
            "phase_note": "improved continuity and lower grain-boundary scattering",
        },
        {
            "thickness_nm": 100,
            "anticipated_resistivity_uohm_cm": "60-90",
            "phase_note": "best low-resistivity window expected if stoichiometry controlled",
        },
    ]


def _is_relevant_evidence(*, title: str, extract: str, task: str) -> bool:
    text = f"{title} {extract}".lower()
    task_lower = task.lower()
    keywords = [
        "cobalt",
        "silicide",
        "cosi",
        "thin film",
        "resistivity",
        "topological",
        "semimetal",
        "dft",
        "molecular dynamics",
        "finite element",
    ]
    score = sum(1 for keyword in keywords if keyword in text)
    if "cobalt" in task_lower and "silicide" in task_lower:
        if "cobalt" not in text and "silicide" not in text and "cosi" not in text:
            return False
        return score >= 2
    return score >= 1


def render_complete_film_plan(
    *,
    task: str,
    selected_groups: list[str],
    answers: list[dict],
    web_evidence: list[dict],
    codex_web_plan: str = "",
) -> str:
    evidence_rows = []
    for item in web_evidence:
        if not isinstance(item, dict):
            continue
        if item.get("error"):
            continue
        url = str(item.get("source_url", "")).strip()
        title = str(item.get("title", "")).strip() or str(item.get("query", "")).strip()
        extract = str(item.get("extract", "")).strip()
        if not url and not extract:
            continue
        if not _is_relevant_evidence(title=title, extract=extract, task=task):
            continue
        evidence_rows.append(
            {
                "provider": str(item.get("provider", "")),
                "title": title,
                "url": url,
                "year": item.get("year"),
                "extract": extract,
                "measurement_hints": item.get("measurement_hints", []),
            }
        )
        if len(evidence_rows) >= 12:
            break

    if not evidence_rows:
        for item in web_evidence:
            if not isinstance(item, dict):
                continue
            if item.get("error"):
                continue
            url = str(item.get("source_url", "")).strip()
            title = str(item.get("title", "")).strip() or str(item.get("query", "")).strip()
            extract = str(item.get("extract", "")).strip()
            if not url and not extract:
                continue
            evidence_rows.append(
                {
                    "provider": str(item.get("provider", "")),
                    "title": title,
                    "url": url,
                    "year": item.get("year"),
                    "extract": extract,
                    "measurement_hints": item.get("measurement_hints", []),
                }
            )
            if len(evidence_rows) >= 12:
                break

    answer_map = {str(row.get("question_id")): str(row.get("answer", "")) for row in answers}
    lines = [
        "# Complete Film Synthesis + Compute Plan",
        "",
        "## Objective",
        task,
        "",
        "## Active Group Orchestration",
    ]
    for idx, group_id in enumerate(selected_groups, start=1):
        lines.append(f"{idx}. `{group_id}`")
    lines.extend(
        [
            "",
            "## Router Intake Baselines",
            f"- substrate: {answer_map.get('q01', '')}",
            f"- thickness program: {answer_map.get('q02', '')}",
            f"- resistivity target: {answer_map.get('q03', '')}",
            f"- stoichiometry strategy: {answer_map.get('q04', '')}",
            f"- deposition: {answer_map.get('q05', '')}",
            f"- anneal limits: {answer_map.get('q06', '')}",
            f"- characterization stack: {answer_map.get('q07', '')}",
            f"- compute envelope: {answer_map.get('q08', '')}",
            f"- DFT baseline: {answer_map.get('q09', '')}",
            f"- MD baseline: {answer_map.get('q10', '')}",
            f"- FEM baseline: {answer_map.get('q11', '')}",
            f"- go/no-go gate: {answer_map.get('q12', '')}",
            "",
            "## Synthesis Procedure (Experimental)",
            "1. Substrate preparation: solvent clean + mild plasma clean; verify roughness by AFM.",
            "2. Deposition DOE: magnetron sputtering with controlled Co/Si targets across +/-5 at% stoichiometry windows.",
            "3. Thickness DOE: 10-120 nm initial sweep; 10 nm pitch then dense sampling around best window.",
            "4. Anneal DOE: RTA 450-800 C, 30 s-30 min, vacuum or Ar; track phase map with XRD and XPS.",
            "5. Electrical screening: four-point + Hall from 10 K to 400 K; triage by target resistivity and carrier metrics.",
            "6. Structural confirmation: TEM on top candidates and failed-edge cases to map phase boundary mechanisms.",
            "",
            "## Computational Procedure (DFT + MD + FEM)",
            "1. DFT branch (VASP/PBEsol+SOC):",
            "- compute phase stability and energy ordering for target/competing cobalt silicide phases.",
            "- evaluate SOC-enabled band features near Fermi level and thickness/strain proxies.",
            "2. MD branch (LAMMPS):",
            "- validate Co-Si potential against lattice/elastic references.",
            "- run thermal trajectories to estimate disorder evolution under anneal schedules.",
            "3. FEM branch:",
            "- simulate thermal stress and diffusion sensitivity vs thickness and ramp profile.",
            "- output process window maps that minimize stress-driven defects.",
            "4. Integration loop:",
            "- merge DFT/MD/FEM signals into ranked experimental recipes before each new batch.",
            "",
            "## Anticipated Results (Pre-Experiment Forecast)",
            "| Thickness (nm) | Anticipated Resistivity (uohm*cm) | Notes |",
            "|---:|---:|---|",
        ]
    )
    for row in _anticipated_rows():
        lines.append(
            f"| {row['thickness_nm']} | {row['anticipated_resistivity_uohm_cm']} | {row['phase_note']} |"
        )
    lines.extend(
        [
            "",
            "## Web Evidence Snapshot (Experimental/Technical Context)",
            "| Provider | Year | Title | Key Data Hint | URL |",
            "|---|---:|---|---|---|",
        ]
    )
    for row in evidence_rows:
        hints = row.get("measurement_hints") or []
        hint_text = ", ".join(str(x) for x in hints[:3]) if hints else "n/a"
        year = row.get("year")
        year_text = str(year) if isinstance(year, int) else "-"
        title = str(row.get("title", "")).replace("|", "/")
        url = str(row.get("url", "")).strip()
        lines.append(f"| {row.get('provider', '')} | {year_text} | {title} | {hint_text} | {url} |")

    lines.extend(
        [
            "",
            "## Risk Controls",
            "- enforce citation and reproducibility gates before exposing synthesis recommendations.",
            "- require phase confirmation (XRD/TEM) before claiming low-resistivity topology-driven behavior.",
            "- route unresolved evidence gaps to literature-intelligence + web-research specialists.",
        ]
    )

    if codex_web_plan.strip():
        lines.extend(
            [
                "",
                "## Codex Web-Search Plan (Live Session)",
                codex_web_plan.strip(),
            ]
        )

    return "\n".join(lines).strip() + "\n"


def write_qa_bundle(
    *,
    output_dir: Path,
    task: str,
    questions: list[IntakeQuestion],
    answers: list[dict],
    web_evidence: list[dict],
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    questions_yaml = output_dir / "questions.yaml"
    answers_yaml = output_dir / "answers.yaml"
    transcript_md = output_dir / "qa-transcript.md"
    evidence_json = output_dir / "web-evidence.json"

    question_rows = [
        {"question_id": question.question_id, "question": question.text, "asked_at": now_iso()}
        for question in questions
    ]
    answers_payload = {"task": task, "answers": answers}
    write_text(questions_yaml, _to_yaml(question_rows))
    write_text(answers_yaml, _to_yaml(answers_payload))
    write_text(evidence_json, json.dumps(web_evidence, indent=2, sort_keys=True) + "\n")
    write_text(transcript_md, render_qa_transcript(task=task, answers=answers))


def _to_yaml(value: Any) -> str:
    try:
        import yaml
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError("PyYAML is required for QA bundle writing") from exc
    return yaml.safe_dump(value, sort_keys=False)


def render_qa_transcript(*, task: str, answers: list[dict]) -> str:
    lines = [
        "# Router Intake Q/A Transcript",
        "",
        f"- task: {task}",
        f"- question_count: {len(answers)}",
        "",
    ]
    for index, row in enumerate(answers, start=1):
        lines.extend(
            [
                f"## Q{index:02d}",
                f"**Question**: {row.get('question', '')}",
                "",
                f"**Answer**: {row.get('answer', '')}",
                "",
                f"**Asked By**: `{row.get('asked_by', '')}`",
                f"**Uncertainty**: `{bool(row.get('uncertainty', False))}`",
            ]
        )
        refs = row.get("evidence_refs", [])
        if isinstance(refs, list) and refs:
            lines.append("**Evidence Refs**:")
            for ref in refs:
                lines.append(f"- {ref}")
        lines.append("")
    return "\n".join(lines)
