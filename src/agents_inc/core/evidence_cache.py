from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Dict, List, Tuple
from urllib.parse import urlparse, urlunparse

from agents_inc.core.session_state import state_dir
from agents_inc.core.util.fs import dump_yaml, load_yaml_map
from agents_inc.core.util.time import now_iso

EVIDENCE_CACHE_SCHEMA_VERSION = "1.0"
DEFAULT_EVIDENCE_CACHE_MAX_ENTRIES = 5000


def evidence_cache_path(project_root: Path) -> Path:
    return state_dir(project_root) / "evidence-cache.yaml"


def load_evidence_cache(
    project_root: Path, *, max_entries: int = DEFAULT_EVIDENCE_CACHE_MAX_ENTRIES
) -> dict:
    path = evidence_cache_path(project_root)
    default = {
        "schema_version": EVIDENCE_CACHE_SCHEMA_VERSION,
        "max_entries": int(max_entries),
        "updated_at": now_iso(),
        "entries": {},
    }
    loaded = load_yaml_map(path, default)
    if not isinstance(loaded, dict):
        loaded = dict(default)
    loaded["schema_version"] = EVIDENCE_CACHE_SCHEMA_VERSION
    try:
        loaded["max_entries"] = max(1, int(loaded.get("max_entries", max_entries)))
    except Exception:
        loaded["max_entries"] = int(max_entries)
    entries = loaded.get("entries")
    if not isinstance(entries, dict):
        loaded["entries"] = {}
    return loaded


def save_evidence_cache(project_root: Path, payload: dict) -> Path:
    path = evidence_cache_path(project_root)
    clean = dict(payload)
    clean["schema_version"] = EVIDENCE_CACHE_SCHEMA_VERSION
    if not isinstance(clean.get("entries"), dict):
        clean["entries"] = {}
    try:
        clean["max_entries"] = max(1, int(clean.get("max_entries", DEFAULT_EVIDENCE_CACHE_MAX_ENTRIES)))
    except Exception:
        clean["max_entries"] = DEFAULT_EVIDENCE_CACHE_MAX_ENTRIES
    clean["updated_at"] = now_iso()
    dump_yaml(path, clean)
    return path


def normalize_citation(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    parsed = urlparse(text)
    if not parsed.scheme or not parsed.netloc:
        return " ".join(text.lower().split())
    normalized = parsed._replace(
        scheme=parsed.scheme.lower(),
        netloc=parsed.netloc.lower(),
        fragment="",
    )
    return urlunparse(normalized)


def evidence_id_for_citation(value: str) -> str:
    normalized = normalize_citation(value)
    if not normalized:
        return ""
    digest = hashlib.sha1(normalized.encode("utf-8", errors="replace")).hexdigest()[:12]
    return f"ev_{digest}"


def canonicalize_evidence_refs(value: object) -> Tuple[List[dict], Dict[str, str]]:
    refs = value if isinstance(value, list) else []
    normalized_refs: List[dict] = []
    id_map: Dict[str, str] = {}
    seen: set[str] = set()
    for row in refs:
        if not isinstance(row, dict):
            continue
        local_id = str(
            row.get("evidence_id") or row.get("id") or row.get("key") or ""
        ).strip()
        citation = str(
            row.get("citation")
            or row.get("url")
            or row.get("source_url")
            or row.get("doi")
            or ""
        ).strip()
        canonical_id = evidence_id_for_citation(citation) or local_id
        if not canonical_id:
            continue
        if local_id:
            id_map[local_id] = canonical_id
        id_map[canonical_id] = canonical_id
        if canonical_id in seen:
            continue
        seen.add(canonical_id)
        normalized_refs.append(
            {
                "evidence_id": canonical_id,
                "citation": citation,
                "title": str(row.get("title") or row.get("name") or "").strip(),
                "source_type": str(row.get("source_type") or "").strip() or _source_type(citation),
                "domain": _domain(citation),
            }
        )
    return normalized_refs, id_map


def merge_evidence_refs_into_cache(
    *,
    project_root: Path,
    evidence_refs: List[dict],
    max_entries: int = DEFAULT_EVIDENCE_CACHE_MAX_ENTRIES,
) -> dict:
    cache = load_evidence_cache(project_root, max_entries=max_entries)
    entries = cache.get("entries")
    if not isinstance(entries, dict):
        entries = {}
    timestamp = now_iso()
    for row in evidence_refs:
        if not isinstance(row, dict):
            continue
        evidence_id = str(row.get("evidence_id") or "").strip()
        if not evidence_id:
            continue
        current = entries.get(evidence_id)
        if not isinstance(current, dict):
            current = {
                "evidence_id": evidence_id,
                "citation": "",
                "title": "",
                "source_type": "",
                "domain": "",
                "first_seen_at": timestamp,
                "last_seen_at": timestamp,
                "hit_count": 0,
            }
        citation = str(row.get("citation") or "").strip()
        title = str(row.get("title") or "").strip()
        source_type = str(row.get("source_type") or "").strip()
        domain = str(row.get("domain") or "").strip()
        if citation:
            current["citation"] = citation
        if title:
            current["title"] = title
        if source_type:
            current["source_type"] = source_type
        if domain:
            current["domain"] = domain
        current["evidence_id"] = evidence_id
        current["last_seen_at"] = timestamp
        if not current.get("first_seen_at"):
            current["first_seen_at"] = timestamp
        try:
            current["hit_count"] = int(current.get("hit_count", 0)) + 1
        except Exception:
            current["hit_count"] = 1
        entries[evidence_id] = current

    max_allowed = int(cache.get("max_entries", max_entries))
    if len(entries) > max_allowed:
        ordered = sorted(
            entries.values(),
            key=lambda row: str((row if isinstance(row, dict) else {}).get("last_seen_at") or ""),
        )
        overflow = max(0, len(entries) - max_allowed)
        prune = ordered[:overflow]
        for item in prune:
            if not isinstance(item, dict):
                continue
            key = str(item.get("evidence_id") or "").strip()
            if key and key in entries:
                entries.pop(key, None)

    cache["entries"] = entries
    cache["updated_at"] = timestamp
    save_evidence_cache(project_root, cache)
    return cache


def resolve_evidence_ids(project_root: Path, evidence_ids: List[str]) -> Dict[str, dict]:
    cache = load_evidence_cache(project_root)
    entries = cache.get("entries")
    if not isinstance(entries, dict):
        return {}
    out: Dict[str, dict] = {}
    for evidence_id in evidence_ids:
        key = str(evidence_id or "").strip()
        if not key:
            continue
        row = entries.get(key)
        if isinstance(row, dict):
            out[key] = dict(row)
    return out


def _domain(citation: str) -> str:
    text = str(citation or "").strip()
    parsed = urlparse(text)
    return parsed.netloc.lower() if parsed.netloc else ""


def _source_type(citation: str) -> str:
    text = str(citation or "").strip().lower()
    if text.startswith("http://") or text.startswith("https://"):
        return "web"
    if text.startswith("local:") or text.startswith("/"):
        return "artifact"
    return "reference"
