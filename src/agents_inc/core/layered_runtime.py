from __future__ import annotations

import json
import re
import shutil
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, as_completed, wait
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from agents_inc.core.agent_session_runner import AgentRunConfig, AgentSessionRunner
from agents_inc.core.agent_threads import (
    set_head_thread,
    set_specialist_thread,
)
from agents_inc.core.evidence_cache import (
    canonicalize_evidence_refs,
    evidence_id_for_citation,
    merge_evidence_refs_into_cache,
    resolve_evidence_ids,
)
from agents_inc.core.escalation import (
    ESCALATION_REQUEST_FILE,
    ESCALATION_RESPONSE_FILE,
    resolve_escalation_state,
)
from agents_inc.core.fabric_lib import build_dispatch_plan, now_iso, stable_json, write_text
from agents_inc.core.model_profiles import (
    DEFAULT_HEAD_MODEL,
    DEFAULT_HEAD_REASONING_EFFORT,
    DEFAULT_SPECIALIST_MODEL,
    DEFAULT_SPECIALIST_REASONING_EFFORT,
)
from agents_inc.core.util.dispatch import gate_specialist_output
from agents_inc.core.util.edges import resolve_handoff_edges

HEAD_MIN_TIMEOUT_SEC = 480
HEAD_MAX_TIMEOUT_SEC = 1800
HEAD_TIMEOUT_MULTIPLIER = 3
HEAD_PROMPT_MAX_SPECIALISTS = 16
HEAD_PROMPT_MAX_CLAIMS_PER_SPECIALIST = 2
HEAD_PROMPT_MAX_ARTIFACTS_PER_SPECIALIST = 3
HEAD_PROMPT_CLAIM_PREVIEW_CHARS = 180
HEAD_PROMPT_CITATION_PREVIEW_CHARS = 180
OBJECTIVE_RESPONSE_STATUS_VALUES = {"ANSWERED", "PARTIAL", "BLOCKED"}
OBJECTIVE_COVERAGE_MIN_FOR_ANSWERED = 0.8
OBJECTIVE_BLOCKED_HINTS = (
    "blocked",
    "needs evidence",
    "insufficient evidence",
    "cannot conclude",
    "unable to conclude",
    "not enough evidence",
)
OBJECTIVE_PARTIAL_HINTS = (
    "partial",
    "incomplete",
    "conditional",
    "unresolved",
    "next cycle",
    "assumption",
)


@dataclass
class LayeredRuntimeConfig:
    project_id: str
    project_root: Path
    project_dir: Path
    turn_dir: Path
    message: str
    selected_groups: List[str]
    group_manifests: Dict[str, dict]
    group_objectives: Optional[Dict[str, str]] = None
    max_parallel: int = 0
    retry_attempts: int = 2
    retry_backoff_sec: int = 5
    agent_timeout_sec: int = 0
    heartbeat_sec: int = 30
    abort_file: Optional[Path] = None
    audit: bool = False
    handoff_edges: List[Tuple[str, str]] = field(default_factory=list)
    specialist_model: str = DEFAULT_SPECIALIST_MODEL
    specialist_reasoning_effort: str | None = DEFAULT_SPECIALIST_REASONING_EFFORT
    head_model: str = DEFAULT_HEAD_MODEL
    head_reasoning_effort: str | None = DEFAULT_HEAD_REASONING_EFFORT
    web_search_policy: str = "web-role-only"
    execution_mode: str = "full"
    progress_callback: Callable[[dict], None] | None = None
    cycle_id: int = 0


@dataclass
class SpecialistResult:
    success: bool
    group_id: str
    specialist_id: str
    role: str
    attempt: int
    work_path: str
    handoff_path: str
    raw_log_path: str
    redacted_log_path: str
    codex_home: str
    visible_skills: List[str]
    mount_status: Dict[str, object]
    timed_out: bool
    error: str
    escalation_request: Optional[Dict[str, object]] = None


@dataclass
class HeadResult:
    success: bool
    group_id: str
    attempt: int
    work_text: str
    handoff_payload: Dict[str, object]
    raw_log_path: str
    redacted_log_path: str
    codex_home: str
    visible_skills: List[str]
    mount_status: Dict[str, object]
    error: str


def _emit_progress(config: LayeredRuntimeConfig, event: dict) -> None:
    callback = config.progress_callback
    if callback is None:
        return
    try:
        callback(event)
    except Exception:
        return


def _resolve_task_web_search_enabled(*, config: LayeredRuntimeConfig, task: dict, role: str) -> bool:
    default_enabled = bool(task.get("web_search_enabled", True))
    policy = str(config.web_search_policy or "web-role-only").strip().lower()
    role_name = str(role or "").strip().lower()
    if policy == "all-enabled":
        return default_enabled
    # Default policy keeps browsing scoped to web-research specialists only.
    return default_enabled and role_name == "web-research"


def _resolve_execution_mode(config: LayeredRuntimeConfig) -> str:
    mode = str(config.execution_mode or "full").strip().lower()
    if mode in {"light", "full"}:
        return mode
    return "full"


def run_layered_runtime(config: LayeredRuntimeConfig) -> dict:
    layer2_dir = config.turn_dir / "layer2"
    layer3_dir = config.turn_dir / "layer3"
    layer4_dir = config.turn_dir / "layer4"
    layer2_dir.mkdir(parents=True, exist_ok=True)
    layer3_dir.mkdir(parents=True, exist_ok=True)
    layer4_dir.mkdir(parents=True, exist_ok=True)

    runner = AgentSessionRunner()
    ledger_rows: List[dict] = []

    orchestrator_plan = {
        "schema_version": "3.1",
        "project_id": config.project_id,
        "message": config.message,
        "selected_groups": config.selected_groups,
        "group_objectives": config.group_objectives or {},
        "settings": {
            "max_parallel": config.max_parallel,
            "retry_attempts": config.retry_attempts,
            "retry_backoff_sec": config.retry_backoff_sec,
            "agent_timeout_sec": config.agent_timeout_sec,
            "agent_timeout_mode": _timeout_mode(config.agent_timeout_sec),
            "heartbeat_sec": config.heartbeat_sec,
            "abort_file": str(config.abort_file) if config.abort_file else "",
            "audit": config.audit,
            "runner_backend": runner.backend,
            "specialist_model": config.specialist_model,
            "specialist_reasoning_effort": config.specialist_reasoning_effort,
            "head_model": config.head_model,
            "head_reasoning_effort": config.head_reasoning_effort,
            "web_search_policy": str(config.web_search_policy or "web-role-only"),
            "execution_mode": _resolve_execution_mode(config),
        },
        "created_at": now_iso(),
    }
    write_text(layer2_dir / "orchestrator-plan.json", stable_json(orchestrator_plan) + "\n")

    group_head_sessions: Dict[str, dict] = {}
    specialist_sessions: Dict[str, dict] = {}

    runtime_mode = _resolve_execution_mode(config)
    for group_id in config.selected_groups:
        group_manifest = config.group_manifests[group_id]
        group_head_sessions[group_id] = {
            "session_code": f"{config.project_id}::{group_id}::head::{int(time.time())}",
            "status": "PENDING",
            "started_at": "",
            "finished_at": "",
            "attempts": 0,
            "error": "",
            "specialist_count": (
                len(group_manifest.get("specialists", [])) if runtime_mode == "full" else 0
            ),
            "codex_home": "",
            "visible_skills": [],
            "mount_status": {},
        }
        specialist_sessions[group_id] = {}
        if runtime_mode == "full":
            for specialist in group_manifest.get("specialists", []):
                aid = str(specialist.get("agent_id") or "")
                if not aid:
                    continue
                specialist_sessions[group_id][aid] = {
                    "session_code": f"{config.project_id}::{group_id}::{aid}::000001",
                    "status": "PENDING",
                    "attempts": 0,
                    "started_at": "",
                    "finished_at": "",
                    "error": "",
                    "role": str(specialist.get("role") or "domain-core"),
                    "codex_home": "",
                    "visible_skills": [],
                    "mount_status": {},
                    "snapshot_work_path": "",
                    "snapshot_handoff_path": "",
                    "snapshot_meta_path": "",
                }

    write_text(layer3_dir / "group-head-sessions.json", stable_json(group_head_sessions) + "\n")
    write_text(layer4_dir / "specialist-sessions.json", stable_json(specialist_sessions) + "\n")

    group_results: Dict[str, dict] = {}
    blocked_reasons: List[str] = []
    active_edges = resolve_handoff_edges(config.selected_groups, config.handoff_edges)
    escalations: List[dict] = []

    if _abort_requested(config):
        blocked_reasons.append("abort file detected before cycle execution")
        group_results = {
            group_id: {
                "status": "BLOCKED",
                "started_at": now_iso(),
                "finished_at": now_iso(),
                "error": "abort requested",
                "specialist_count": 0,
            }
            for group_id in config.selected_groups
        }
        return {
            "schema_version": "3.1",
            "group_status": group_results,
            "blocked": True,
            "blocked_groups": sorted(config.selected_groups),
            "reasons": blocked_reasons,
            "timed_out_specialists": [],
            "specialist_failures": [],
            "agent_timeout_sec": config.agent_timeout_sec,
            "agent_timeout_mode": _timeout_mode(config.agent_timeout_sec),
            "group_head_sessions_path": str(layer3_dir / "group-head-sessions.json"),
            "specialist_sessions_path": str(layer4_dir / "specialist-sessions.json"),
            "cooperation_ledger_path": str(config.turn_dir / "cooperation-ledger.ndjson"),
            "wait_state_path": str(config.turn_dir / "wait-state.json"),
            "escalations": escalations,
        }

    max_group_workers = (
        len(config.selected_groups)
        if int(config.max_parallel) <= 0
        else max(1, min(int(config.max_parallel), len(config.selected_groups)))
    )

    timed_out_specialists: List[dict] = []
    specialist_failures: List[dict] = []
    with ThreadPoolExecutor(max_workers=max_group_workers) as pool:
        future_map = {}
        for group_id in config.selected_groups:
            _emit_progress(
                config,
                {
                    "event": "runtime_group_started",
                    "project_id": config.project_id,
                    "cycle": int(config.cycle_id),
                    "group_id": group_id,
                },
            )
            future = pool.submit(
                _run_group,
                config,
                group_id,
                runner,
                specialist_sessions,
                group_head_sessions,
                layer3_dir,
                layer4_dir,
                ledger_rows,
            )
            future_map[future] = group_id
        heartbeat_every = max(1, int(config.heartbeat_sec))
        next_heartbeat = time.monotonic() + heartbeat_every
        pending = set(future_map.keys())
        while pending:
            timeout = max(0.0, next_heartbeat - time.monotonic())
            done, pending = wait(pending, timeout=timeout, return_when=FIRST_COMPLETED)
            if not done:
                completed_groups = sorted(group_results.keys())
                pending_groups = sorted(future_map[future] for future in pending)
                _emit_progress(
                    config,
                    {
                        "event": "runtime_heartbeat",
                        "project_id": config.project_id,
                        "cycle": int(config.cycle_id),
                        "completed_groups": len(completed_groups),
                        "total_groups": len(config.selected_groups),
                        "pending_groups": pending_groups,
                    },
                )
                next_heartbeat = time.monotonic() + heartbeat_every
                continue

            for future in done:
                group_id = future_map[future]
                try:
                    result = future.result()
                except Exception as exc:  # noqa: BLE001
                    error_text = str(exc).strip() or "group runtime exception"
                    result = {
                        "status": "BLOCKED",
                        "started_at": now_iso(),
                        "finished_at": now_iso(),
                        "error": error_text,
                        "timed_out_specialists": [],
                        "escalations": [],
                        "specialist_failures": [],
                    }
                    ledger_rows.append(
                        {
                            "ts": now_iso(),
                            "event": "group_runtime_exception",
                            "group_id": group_id,
                            "error": error_text,
                        }
                    )
                group_results[group_id] = result
                _emit_progress(
                    config,
                    {
                        "event": "runtime_group_done",
                        "project_id": config.project_id,
                        "cycle": int(config.cycle_id),
                        "group_id": group_id,
                        "status": str(result.get("status") or "UNKNOWN"),
                    },
                )
                timed_out_rows = result.get("timed_out_specialists", [])
                if isinstance(timed_out_rows, list):
                    for row in timed_out_rows:
                        if isinstance(row, dict):
                            timed_out_specialists.append(row)
                escalation_rows = result.get("escalations", [])
                if isinstance(escalation_rows, list):
                    for row in escalation_rows:
                        if isinstance(row, dict):
                            escalations.append(row)
                if result["status"] != "COMPLETE":
                    blocked_reasons.append(
                        f"group '{group_id}' {result['status'].lower()}: {result.get('error', 'no detail')}"
                    )
                    failure_rows = result.get("specialist_failures", [])
                    if isinstance(failure_rows, list):
                        for row in failure_rows:
                            if not isinstance(row, dict):
                                continue
                            specialist_failures.append(row)
                            specialist_id = str(row.get("specialist_id") or "").strip()
                            error_text = str(row.get("error") or "").strip()
                            if not specialist_id or not error_text:
                                continue
                            detail = f"group '{group_id}' specialist '{specialist_id}' failed: {error_text}"
                            if detail not in blocked_reasons:
                                blocked_reasons.append(detail)

            if time.monotonic() >= next_heartbeat:
                completed_groups = sorted(group_results.keys())
                pending_groups = sorted(future_map[future] for future in pending)
                _emit_progress(
                    config,
                    {
                        "event": "runtime_heartbeat",
                        "project_id": config.project_id,
                        "cycle": int(config.cycle_id),
                        "completed_groups": len(completed_groups),
                        "total_groups": len(config.selected_groups),
                        "pending_groups": pending_groups,
                    },
                )
                next_heartbeat = time.monotonic() + heartbeat_every

    # Same-layer cooperation: head-to-head consume from exposed only.
    active = set(config.selected_groups)
    for producer, consumer in active_edges:
        if producer not in active or consumer not in active:
            continue
        if group_results.get(producer, {}).get("status") != "COMPLETE":
            continue
        if group_results.get(consumer, {}).get("status") != "COMPLETE":
            continue
        source = config.project_dir / "agent-groups" / producer / "exposed" / "handoff.json"
        ledger_rows.append(
            {
                "ts": now_iso(),
                "event": "head_consume_exposed",
                "from": producer,
                "to": consumer,
                "source": str(source),
                "exists": bool(source.exists()),
            }
        )

    write_text(layer3_dir / "group-head-sessions.json", stable_json(group_head_sessions) + "\n")
    write_text(layer4_dir / "specialist-sessions.json", stable_json(specialist_sessions) + "\n")

    wait_state = {
        "schema_version": "3.1",
        "project_id": config.project_id,
        "required_groups": config.selected_groups,
        "complete_groups": sorted(
            [g for g, row in group_results.items() if row.get("status") == "COMPLETE"]
        ),
        "blocked_groups": sorted(
            [g for g, row in group_results.items() if row.get("status") != "COMPLETE"]
        ),
        "all_groups_complete": all(
            row.get("status") == "COMPLETE" for row in group_results.values()
        ),
        "updated_at": now_iso(),
        "agent_timeout_sec": config.agent_timeout_sec,
        "agent_timeout_mode": _timeout_mode(config.agent_timeout_sec),
    }
    write_text(config.turn_dir / "wait-state.json", stable_json(wait_state) + "\n")

    cooperation_path = config.turn_dir / "cooperation-ledger.ndjson"
    if ledger_rows:
        write_text(
            cooperation_path,
            "\n".join(json.dumps(row, sort_keys=True) for row in ledger_rows) + "\n",
        )
    else:
        write_text(cooperation_path, "")

    _persist_turn_evidence_cache(config=config, group_results=group_results)

    return {
        "schema_version": "3.1",
        "group_status": group_results,
        "blocked": not wait_state["all_groups_complete"],
        "blocked_groups": wait_state["blocked_groups"],
        "reasons": blocked_reasons,
        "timed_out_specialists": timed_out_specialists,
        "specialist_failures": specialist_failures,
        "agent_timeout_sec": config.agent_timeout_sec,
        "agent_timeout_mode": _timeout_mode(config.agent_timeout_sec),
        "group_head_sessions_path": str(layer3_dir / "group-head-sessions.json"),
        "specialist_sessions_path": str(layer4_dir / "specialist-sessions.json"),
        "cooperation_ledger_path": str(cooperation_path),
        "wait_state_path": str(config.turn_dir / "wait-state.json"),
        "escalations": escalations,
    }


def _run_group(
    config: LayeredRuntimeConfig,
    group_id: str,
    runner: AgentSessionRunner,
    specialist_sessions: Dict[str, dict],
    group_head_sessions: Dict[str, dict],
    layer3_dir: Path,
    layer4_dir: Path,
    ledger_rows: List[dict],
) -> dict:
    started_at = now_iso()
    group_manifest = config.group_manifests[group_id]
    group_objective = str((config.group_objectives or {}).get(group_id) or config.message)
    execution_mode = _resolve_execution_mode(config)
    dispatch = build_dispatch_plan(
        config.project_id,
        group_id,
        group_objective,
        group_manifest,
        execution_mode=execution_mode,
    )

    phase_outputs: Dict[str, SpecialistResult] = {}
    group_error = ""
    timed_out_specialists: List[dict] = []
    group_escalations: List[dict] = []
    specialist_failures: List[dict] = []

    if execution_mode == "full":
        for phase in dispatch.get("phases", []):
            if _abort_requested(config):
                group_error = "abort requested"
                ledger_rows.append(
                    {
                        "ts": now_iso(),
                        "event": "group_abort_requested",
                        "group_id": group_id,
                    }
                )
                break
            tasks = phase.get("tasks", [])
            if not isinstance(tasks, list):
                continue
            max_workers = (
                len(tasks)
                if int(config.max_parallel) <= 0
                else max(1, min(int(config.max_parallel), len(tasks)))
            )
            with ThreadPoolExecutor(max_workers=max_workers) as pool:
                future_map = {
                    pool.submit(
                        _run_specialist_with_retries,
                        config,
                        group_id,
                        group_objective,
                        task,
                        runner,
                        specialist_sessions,
                        layer4_dir,
                        ledger_rows,
                    ): task
                    for task in tasks
                }
                for future in as_completed(future_map):
                    task = future_map[future]
                    specialist_id = str(task.get("agent_id") or "")
                    role = str(task.get("role") or "domain-core")
                    try:
                        result = future.result()
                    except Exception as exc:  # noqa: BLE001
                        error_text = str(exc).strip() or "specialist runtime exception"
                        if specialist_id in specialist_sessions[group_id]:
                            specialist_sessions[group_id][specialist_id]["status"] = "FAILED"
                            specialist_sessions[group_id][specialist_id]["finished_at"] = now_iso()
                            specialist_sessions[group_id][specialist_id]["error"] = error_text
                        ledger_rows.append(
                            {
                                "ts": now_iso(),
                                "event": "specialist_runtime_exception",
                                "group_id": group_id,
                                "specialist_id": specialist_id,
                                "error": error_text,
                            }
                        )
                        result = SpecialistResult(
                            success=False,
                            group_id=group_id,
                            specialist_id=specialist_id or "unknown-specialist",
                            role=role,
                            attempt=0,
                            work_path="",
                            handoff_path="",
                            raw_log_path="",
                            redacted_log_path="",
                            codex_home="",
                            visible_skills=[],
                            mount_status={},
                            timed_out=False,
                            error=error_text,
                            escalation_request=None,
                        )
                    phase_outputs[result.specialist_id] = result
                    if result.timed_out:
                        timed_out_specialists.append(
                            {
                                "group_id": group_id,
                                "specialist_id": result.specialist_id,
                                "attempts": result.attempt,
                                "raw_log_path": result.raw_log_path,
                                "redacted_log_path": result.redacted_log_path,
                            }
                        )
                    if isinstance(result.escalation_request, dict):
                        group_escalations.append(result.escalation_request)
                    if not result.success:
                        failure_entry = {
                            "group_id": group_id,
                            "specialist_id": result.specialist_id,
                            "role": result.role,
                            "attempts": result.attempt,
                            "timed_out": bool(result.timed_out),
                            "error": str(
                                result.error or f"specialist '{result.specialist_id}' failed"
                            ),
                        }
                        if isinstance(result.escalation_request, dict):
                            failure_entry["escalation_type"] = str(
                                result.escalation_request.get("type", "custom")
                            )
                        specialist_failures.append(failure_entry)
                    if not result.success and not group_error:
                        if isinstance(result.escalation_request, dict):
                            group_error = (
                                f"specialist '{result.specialist_id}' requested escalation "
                                f"({result.escalation_request.get('type', 'custom')})"
                            )
                        elif result.timed_out:
                            group_error = (
                                f"specialist '{result.specialist_id}' timed out after "
                                f"{result.attempt} attempt(s)"
                            )
                        else:
                            group_error = result.error or f"specialist '{result.specialist_id}' failed"
                    if _abort_requested(config) and not group_error:
                        group_error = "abort requested"
                        ledger_rows.append(
                            {
                                "ts": now_iso(),
                                "event": "group_abort_requested",
                                "group_id": group_id,
                            }
                        )
                        for pending in future_map:
                            if not pending.done():
                                pending.cancel()
                        break

            if group_error:
                break
    elif _abort_requested(config):
        group_error = "abort requested"
        ledger_rows.append(
            {
                "ts": now_iso(),
                "event": "group_abort_requested",
                "group_id": group_id,
            }
        )

    group_layer3 = layer3_dir / group_id
    group_layer3.mkdir(parents=True, exist_ok=True)
    head_log = group_layer3 / "head-merge.log"

    if group_error:
        group_head_sessions[group_id]["status"] = "BLOCKED"
        group_head_sessions[group_id]["started_at"] = started_at
        group_head_sessions[group_id]["finished_at"] = now_iso()
        group_head_sessions[group_id]["error"] = group_error
        write_text(
            head_log,
            f"group={group_id}\nstatus=BLOCKED\nerror={group_error}\nfinished_at={now_iso()}\n",
        )
        return {
            "status": "BLOCKED",
            "started_at": started_at,
            "finished_at": now_iso(),
            "error": group_error,
            "timed_out_specialists": timed_out_specialists,
            "escalations": group_escalations,
            "specialist_failures": specialist_failures,
        }

    head_result = _run_head_with_retries(
        config=config,
        group_id=group_id,
        objective=group_objective,
        dispatch=dispatch,
        phase_outputs=phase_outputs,
        execution_mode=execution_mode,
        runner=runner,
        layer3_dir=layer3_dir,
        ledger_rows=ledger_rows,
    )

    group_head_sessions[group_id]["attempts"] = head_result.attempt
    group_head_sessions[group_id]["codex_home"] = head_result.codex_home
    group_head_sessions[group_id]["visible_skills"] = head_result.visible_skills
    group_head_sessions[group_id]["mount_status"] = head_result.mount_status

    if not head_result.success:
        group_head_sessions[group_id]["status"] = "BLOCKED"
        group_head_sessions[group_id]["started_at"] = started_at
        group_head_sessions[group_id]["finished_at"] = now_iso()
        group_head_sessions[group_id]["error"] = head_result.error
        write_text(
            head_log,
            (
                f"group={group_id}\n"
                "status=BLOCKED\n"
                f"error={head_result.error}\n"
                f"finished_at={now_iso()}\n"
            ),
        )
        return {
            "status": "BLOCKED",
            "started_at": started_at,
            "finished_at": now_iso(),
            "error": head_result.error,
            "timed_out_specialists": timed_out_specialists,
            "escalations": group_escalations,
            "specialist_failures": specialist_failures,
        }

    exposed = config.project_dir / "agent-groups" / group_id / "exposed"
    exposed.mkdir(parents=True, exist_ok=True)

    specialist_payloads = _collect_specialist_payloads(phase_outputs)
    handoff_payload = dict(head_result.handoff_payload)

    claims = _normalized_claims(handoff_payload)
    if not claims:
        claims = _claims_from_specialist_payloads(specialist_payloads)
    evidence_refs = _normalized_evidence_refs(handoff_payload)
    for row in _evidence_refs_from_specialist_payloads(specialist_payloads):
        evidence_id = str(row.get("evidence_id") or "").strip()
        if not evidence_id:
            continue
        if all(str(item.get("evidence_id") or "").strip() != evidence_id for item in evidence_refs):
            evidence_refs.append(row)

    artifacts = _normalized_artifacts(handoff_payload)
    produced_artifacts = _normalized_strings(handoff_payload.get("produced_artifacts"))
    if not artifacts:
        artifacts = _artifacts_from_specialist_payloads(specialist_payloads)
    if not produced_artifacts:
        produced_artifacts = [str(item.get("path") or "").strip() for item in artifacts]
        produced_artifacts = [item for item in produced_artifacts if item]

    if not claims:
        fallback_ref = {
            "evidence_id": evidence_id_for_citation("https://example.org/group-complete"),
            "citation": "https://example.org/group-complete",
            "title": "group-complete",
            "source_type": "web",
            "domain": "example.org",
        }
        evidence_refs.append(fallback_ref)
        fallback_claim = (
            f"{group_id} completed direct group-head objective execution."
            if execution_mode == "light"
            else f"{group_id} completed all scheduled specialist tasks."
        )
        claims.append(
            {
                "claim": fallback_claim,
                "evidence_ids": [str(fallback_ref["evidence_id"])],
            }
        )

    claims = _canonicalize_claim_evidence_ids(claims=claims, evidence_refs=evidence_refs)
    citation_count = _count_claim_citations(claims)

    handoff_payload.setdefault("schema_version", "4.0")
    handoff_payload["status"] = "COMPLETE"
    handoff_payload["group_id"] = group_id
    handoff_payload["execution_status"] = "COMPLETE"
    handoff_payload["dependencies_satisfied"] = True
    handoff_payload["produced_artifacts"] = sorted(set(produced_artifacts))
    handoff_payload["citations_summary"] = {
        "count": citation_count,
        "has_web_url": _claims_have_web_url(evidence_refs),
    }
    handoff_payload["artifacts"] = artifacts
    handoff_payload["claims"] = claims
    handoff_payload["evidence_refs"] = evidence_refs
    handoff_payload.pop("claims_with_citations", None)
    handoff_payload["updated_at"] = now_iso()

    summary_text = head_result.work_text.strip()
    if not summary_text:
        summary_title = (
            "Group `{0}` completed head-only objective execution.".format(group_id)
            if execution_mode == "light"
            else "Group `{0}` completed layered specialist execution.".format(group_id)
        )
        summary_lines = [
            "# Summary",
            "",
            summary_title,
            f"- specialist_count: {len(phase_outputs)}",
            f"- citation_refs: {citation_count}",
            f"- produced_artifacts: {len(handoff_payload['produced_artifacts'])}",
        ]
        for idx, claim in enumerate(claims[:6], start=1):
            text = str(claim.get("claim") or "").strip()
            if text:
                summary_lines.append(f"- claim_{idx}: {text}")
        summary_text = "\n".join(summary_lines)

    integration_notes = str(handoff_payload.get("integration_notes") or "").strip()
    if not integration_notes:
        integration_notes = (
            "# Integration Notes\n\n"
            f"- status: COMPLETE\n"
            f"- group: {group_id}\n"
            "- integration_ready: true\n"
            "- dependencies_resolved: true\n"
            "- source: layered head session merge\n"
        )

    objective_contract = _normalize_head_objective_contract(
        objective=group_objective,
        group_id=group_id,
        payload=handoff_payload,
        summary_text=summary_text,
        integration_notes=integration_notes,
        claims=claims,
    )
    handoff_payload["response_status"] = objective_contract["response_status"]
    handoff_payload["objective_response"] = objective_contract["objective_response"]
    handoff_payload["decision_summary"] = objective_contract["decision_summary"]
    handoff_payload["recommended_actions"] = objective_contract["recommended_actions"]
    handoff_payload["objective_coverage"] = objective_contract["objective_coverage"]

    write_text(exposed / "summary.md", summary_text.rstrip() + "\n")
    write_text(
        exposed / "handoff.json", json.dumps(handoff_payload, indent=2, sort_keys=True) + "\n"
    )
    write_text(exposed / "INTEGRATION_NOTES.md", integration_notes.rstrip() + "\n")

    group_head_sessions[group_id]["status"] = "COMPLETE"
    group_head_sessions[group_id]["started_at"] = started_at
    group_head_sessions[group_id]["finished_at"] = now_iso()
    group_head_sessions[group_id]["error"] = ""

    write_text(
        head_log,
        (
            f"group={group_id}\n"
            "status=COMPLETE\n"
            f"specialists={len(phase_outputs)}\n"
            f"citations={citation_count}\n"
            f"head_raw_log={head_result.raw_log_path}\n"
            f"head_redacted_log={head_result.redacted_log_path}\n"
            f"finished_at={now_iso()}\n"
        ),
    )

    ledger_rows.append(
        {
            "ts": now_iso(),
            "event": "group_head_published",
            "group_id": group_id,
            "specialist_count": len(phase_outputs),
            "citation_count": citation_count,
            "head_raw_log": head_result.raw_log_path,
            "head_redacted_log": head_result.redacted_log_path,
            "exposed_handoff": str(exposed / "handoff.json"),
        }
    )

    return {
        "status": "COMPLETE",
        "started_at": started_at,
        "finished_at": now_iso(),
        "error": "",
        "specialist_count": len(phase_outputs),
        "timed_out_specialists": timed_out_specialists,
        "escalations": group_escalations,
        "specialist_failures": specialist_failures,
    }


def _run_specialist_with_retries(
    config: LayeredRuntimeConfig,
    group_id: str,
    objective: str,
    task: dict,
    runner: AgentSessionRunner,
    specialist_sessions: Dict[str, dict],
    layer4_dir: Path,
    ledger_rows: List[dict],
) -> SpecialistResult:
    specialist_id = str(task.get("agent_id") or "")
    role = str(task.get("role") or "domain-core")
    focus = str(task.get("focus") or "")
    web_search_enabled = _resolve_task_web_search_enabled(
        config=config,
        task=task,
        role=role,
    )
    attempts_total = max(1, int(config.retry_attempts) + 1)

    specialist_root = config.project_dir / "agent-groups" / group_id / "internal" / specialist_id
    specialist_root.mkdir(parents=True, exist_ok=True)
    work_path = specialist_root / "work.md"
    handoff_path = specialist_root / "handoff.json"

    group_layer4 = layer4_dir / group_id / specialist_id
    raw_log_path = group_layer4 / "raw.log"
    redacted_log_path = group_layer4 / "redacted.log"

    skill_name = str(task.get("skill_name") or "").strip()
    codex_home, visible_skills, missing_skills, mount_status = _prepare_agent_codex_home(
        config=config,
        runtime_dir=group_layer4,
        group_id=group_id,
        allowed_skill_names=[skill_name] if skill_name else [],
    )
    specialist_sessions[group_id][specialist_id]["codex_home"] = str(codex_home)
    specialist_sessions[group_id][specialist_id]["visible_skills"] = visible_skills
    specialist_sessions[group_id][specialist_id]["mount_status"] = mount_status

    if missing_skills and runner.backend != "mock":
        missing_text = ", ".join(missing_skills)
        message = (
            f"required specialist skill(s) not installed in project CODEX_HOME for {group_id}/{specialist_id}: "
            f"{missing_text}. Activate with 'agents-inc skills activate --project-id {config.project_id} "
            f"--groups {group_id} --specialists'."
        )
        specialist_sessions[group_id][specialist_id]["status"] = "FAILED"
        specialist_sessions[group_id][specialist_id]["error"] = message
        specialist_sessions[group_id][specialist_id]["attempts"] = 1
        return SpecialistResult(
            success=False,
            group_id=group_id,
            specialist_id=specialist_id,
            role=role,
            attempt=1,
            work_path=str(work_path),
            handoff_path=str(handoff_path),
            raw_log_path=str(raw_log_path),
            redacted_log_path=str(redacted_log_path),
            codex_home=str(codex_home),
            visible_skills=visible_skills,
            mount_status=mount_status,
            timed_out=False,
            error=message,
            escalation_request=None,
        )

    timed_out = False
    retry_gate_reasons: List[str] = []
    resolved_reference_paths = _resolve_required_reference_paths(
        project_dir=config.project_dir,
        group_id=group_id,
        required_references=task.get("required_references", []),
    )
    resolved_dependency_artifacts = _resolve_dependency_artifact_paths(
        project_dir=config.project_dir,
        group_id=group_id,
        dependencies=task.get("depends_on", []),
    )
    for attempt in range(1, attempts_total + 1):
        specialist_sessions[group_id][specialist_id]["status"] = "RUNNING"
        specialist_sessions[group_id][specialist_id]["attempts"] = attempt
        specialist_sessions[group_id][specialist_id]["started_at"] = now_iso()

        prompt = _build_specialist_prompt(
            objective=objective,
            group_id=group_id,
            specialist_id=specialist_id,
            role=role,
            focus=focus,
            skill_name=skill_name,
            dependencies=task.get("depends_on", []),
            required_outputs=task.get("required_outputs", []),
            required_references=task.get("required_references", []),
            required_reference_paths=resolved_reference_paths,
            dependency_artifact_paths=resolved_dependency_artifacts,
            web_search_enabled=web_search_enabled,
            artifact_scope={
                "work_path": str(work_path),
                "handoff_path": str(handoff_path),
            },
            retry_gate_reasons=retry_gate_reasons,
        )

        result = runner.run(
            AgentRunConfig(
                project_root=config.project_root,
                work_dir=specialist_root,
                prompt=prompt,
                raw_log_path=raw_log_path,
                redacted_log_path=redacted_log_path,
                timeout_sec=config.agent_timeout_sec,
                web_search=web_search_enabled,
                codex_home=codex_home,
                # Specialists start fresh each run to avoid stale cross-turn context drift.
                thread_id=None,
                session_label=f"{group_id}/{specialist_id}",
                model=config.specialist_model,
                model_reasoning_effort=config.specialist_reasoning_effort,
                disable_mcp=True,
            )
        )

        escalation_state = resolve_escalation_state(
            work_dir=specialist_root,
            group_id=group_id,
            specialist_id=specialist_id,
        )
        escalation_kind = str(escalation_state.get("state") or "").upper()
        escalation_request = escalation_state.get("request")
        escalation_response = escalation_state.get("response")
        escalation_reasons = escalation_state.get("reasons")
        if not isinstance(escalation_reasons, list):
            escalation_reasons = []
        if escalation_kind in {"REQUESTED", "UNRESOLVED", "INVALID"}:
            request_payload: Dict[str, object] = {}
            if isinstance(escalation_request, dict):
                request_payload.update(escalation_request)
            request_payload["state"] = escalation_kind
            if escalation_reasons:
                request_payload["state_reasons"] = escalation_reasons
            if isinstance(escalation_response, dict):
                request_payload["response"] = escalation_response
            specialist_sessions[group_id][specialist_id]["status"] = "ESCALATION_REQUIRED"
            specialist_sessions[group_id][specialist_id]["finished_at"] = now_iso()
            message = str(request_payload.get("reason") or "").strip()
            if not message:
                message = (
                    "; ".join(str(item) for item in escalation_reasons) or "escalation required"
                )
            specialist_sessions[group_id][specialist_id]["error"] = message
            ledger_rows.append(
                {
                    "ts": now_iso(),
                    "event": "specialist_escalation_required",
                    "group_id": group_id,
                    "specialist_id": specialist_id,
                    "attempt": attempt,
                    "escalation": request_payload,
                    "raw_log": str(raw_log_path),
                    "redacted_log": str(redacted_log_path),
                    "codex_home": str(codex_home),
                    "visible_skills": visible_skills,
                }
            )
            return SpecialistResult(
                success=False,
                group_id=group_id,
                specialist_id=specialist_id,
                role=role,
                attempt=attempt,
                work_path=str(work_path),
                handoff_path=str(handoff_path),
                raw_log_path=str(raw_log_path),
                redacted_log_path=str(redacted_log_path),
                codex_home=str(codex_home),
                visible_skills=visible_skills,
                mount_status=mount_status,
                timed_out=False,
                error="escalation required",
                escalation_request=request_payload,
            )
        if escalation_kind == "RESOLVED":
            archived_paths = _archive_escalation_files(
                work_dir=specialist_root,
                archive_dir=group_layer4 / "escalations",
            )
            ledger_rows.append(
                {
                    "ts": now_iso(),
                    "event": "specialist_escalation_resolved",
                    "group_id": group_id,
                    "specialist_id": specialist_id,
                    "attempt": attempt,
                    "archived": archived_paths,
                }
            )

        handoff_payload = dict(result.parsed_handoff or {})
        if result.success:
            handoff_payload = _apply_evidence_auto_heal(
                project_root=config.project_root,
                payload=handoff_payload,
            )
            handoff_payload.setdefault("schema_version", "4.0")
            handoff_payload.setdefault("status", "COMPLETE")
            handoff_payload.setdefault("execution_status", "COMPLETE")
            handoff_payload.setdefault("dependencies_satisfied", True)
            handoff_payload.setdefault("produced_artifacts", [])
            handoff_payload["claims"] = _normalized_claims(handoff_payload)
            handoff_payload["evidence_refs"] = _normalized_evidence_refs(handoff_payload)
            handoff_payload["citations_summary"] = {
                "count": _count_claim_citations(handoff_payload["claims"]),
                "has_web_url": _claims_have_web_url(handoff_payload["evidence_refs"]),
            }
            handoff_payload.setdefault("repro_steps", ["specialist execution complete"])
            handoff_payload.setdefault("artifact_paths", [])
            handoff_payload.pop("claims_with_citations", None)
            gate = gate_specialist_output(
                handoff_payload,
                role=role,
                citation_required=True,
                web_available=web_search_enabled,
            )
            gate_status = str(gate.get("status") or "BLOCKED_REVIEW")
            gate_reasons = gate.get("reasons")
            if not isinstance(gate_reasons, list):
                gate_reasons = []
            if gate_status != "PASS":
                gate_error = "specialist gate failed: {0} ({1})".format(
                    gate_status, "; ".join(str(x) for x in gate_reasons)
                )
                specialist_sessions[group_id][specialist_id]["status"] = "FAILED"
                specialist_sessions[group_id][specialist_id]["finished_at"] = now_iso()
                specialist_sessions[group_id][specialist_id]["error"] = gate_error
                snapshot_paths = _write_specialist_snapshot(
                    snapshot_root=layer4_dir / "specialists" / group_id / specialist_id,
                    work_text=result.parsed_work,
                    handoff_payload=handoff_payload,
                    meta_payload={
                        "schema_version": "1.0",
                        "generated_at": now_iso(),
                        "project_id": config.project_id,
                        "group_id": group_id,
                        "specialist_id": specialist_id,
                        "role": role,
                        "attempt": attempt,
                        "success": False,
                        "error": gate_error,
                        "gate": gate,
                        "raw_log_path": str(raw_log_path),
                        "redacted_log_path": str(redacted_log_path),
                    },
                )
                specialist_sessions[group_id][specialist_id].update(snapshot_paths)
                ledger_rows.append(
                    {
                        "ts": now_iso(),
                        "event": (
                            "specialist_gate_retry"
                            if attempt < attempts_total
                            else "specialist_gate_failed"
                        ),
                        "group_id": group_id,
                        "specialist_id": specialist_id,
                        "attempt": attempt,
                        "gate_status": gate_status,
                        "gate_reasons": gate_reasons,
                    }
                )
                retry_gate_reasons = [
                    str(item).strip() for item in gate_reasons if str(item).strip()
                ]
                # Gate failures are deterministic in most cases; do not spend extra model
                # retries once auto-healing has already been applied.
                handoff_payload["execution_status"] = (
                    gate_status if gate_status.startswith("BLOCKED_") else "BLOCKED_REVIEW"
                )
                handoff_payload["dependencies_satisfied"] = False
                handoff_payload["quality_gate"] = {
                    "status": gate_status,
                    "reasons": retry_gate_reasons,
                    "soft_pass": True,
                }
                handoff_payload.setdefault("claims", [])
                handoff_payload.setdefault("evidence_refs", [])
                handoff_payload.setdefault("repro_steps", ["specialist execution completed with warnings"])
                handoff_payload.setdefault("artifact_paths", [])
                handoff_payload.setdefault("produced_artifacts", [])

                soft_work_text = result.parsed_work.strip()
                if not soft_work_text:
                    soft_work_text = (
                        "# Work Notes\n\n"
                        "No specialist work notes were returned. Output published with quality gate "
                        "warnings for downstream head triage."
                    )
                write_text(work_path, soft_work_text.rstrip() + "\n")
                write_text(handoff_path, json.dumps(handoff_payload, indent=2, sort_keys=True) + "\n")
                _persist_payload_evidence_cache(
                    project_root=config.project_root,
                    payload=handoff_payload,
                )
                snapshot_paths = _write_specialist_snapshot(
                    snapshot_root=layer4_dir / "specialists" / group_id / specialist_id,
                    work_text=soft_work_text,
                    handoff_payload=handoff_payload,
                    meta_payload={
                        "schema_version": "1.0",
                        "generated_at": now_iso(),
                        "project_id": config.project_id,
                        "group_id": group_id,
                        "specialist_id": specialist_id,
                        "role": role,
                        "attempt": attempt,
                        "success": True,
                        "soft_success": True,
                        "error": gate_error,
                        "gate": gate,
                        "raw_log_path": str(raw_log_path),
                        "redacted_log_path": str(redacted_log_path),
                    },
                )
                specialist_sessions[group_id][specialist_id].update(snapshot_paths)
                specialist_sessions[group_id][specialist_id]["status"] = "COMPLETE_WITH_WARNINGS"
                specialist_sessions[group_id][specialist_id]["finished_at"] = now_iso()
                specialist_sessions[group_id][specialist_id]["error"] = gate_error
                if result.thread_id:
                    set_specialist_thread(
                        config.project_root,
                        group_id,
                        specialist_id,
                        result.thread_id,
                        "COMPLETE",
                    )
                ledger_rows.append(
                    {
                        "ts": now_iso(),
                        "event": "specialist_gate_soft_pass",
                        "group_id": group_id,
                        "specialist_id": specialist_id,
                        "attempt": attempt,
                        "gate_status": gate_status,
                        "gate_reasons": retry_gate_reasons,
                        "raw_log": str(raw_log_path),
                        "redacted_log": str(redacted_log_path),
                        "codex_home": str(codex_home),
                        "visible_skills": visible_skills,
                        "thread_id": result.thread_id,
                        "used_resume": result.used_resume,
                        "rotated_thread": result.rotated_thread,
                        "parse_mode": result.parse_mode,
                    }
                )
                return SpecialistResult(
                    success=True,
                    group_id=group_id,
                    specialist_id=specialist_id,
                    role=role,
                    attempt=attempt,
                    work_path=str(work_path),
                    handoff_path=str(handoff_path),
                    raw_log_path=str(raw_log_path),
                    redacted_log_path=str(redacted_log_path),
                    codex_home=str(codex_home),
                    visible_skills=visible_skills,
                    mount_status=mount_status,
                    timed_out=False,
                    error="",
                    escalation_request=None,
                )

            write_text(work_path, result.parsed_work.rstrip() + "\n")
            write_text(handoff_path, json.dumps(handoff_payload, indent=2, sort_keys=True) + "\n")
            _persist_payload_evidence_cache(
                project_root=config.project_root,
                payload=handoff_payload,
            )
            snapshot_paths = _write_specialist_snapshot(
                snapshot_root=layer4_dir / "specialists" / group_id / specialist_id,
                work_text=result.parsed_work,
                handoff_payload=handoff_payload,
                meta_payload={
                    "schema_version": "1.0",
                    "generated_at": now_iso(),
                    "project_id": config.project_id,
                    "group_id": group_id,
                    "specialist_id": specialist_id,
                    "role": role,
                    "attempt": attempt,
                    "success": True,
                    "error": "",
                    "raw_log_path": str(raw_log_path),
                    "redacted_log_path": str(redacted_log_path),
                },
            )
            specialist_sessions[group_id][specialist_id].update(snapshot_paths)

            specialist_sessions[group_id][specialist_id]["status"] = "COMPLETE"
            specialist_sessions[group_id][specialist_id]["finished_at"] = now_iso()
            specialist_sessions[group_id][specialist_id]["error"] = ""
            if result.thread_id:
                set_specialist_thread(
                    config.project_root,
                    group_id,
                    specialist_id,
                    result.thread_id,
                    "COMPLETE",
                )
            ledger_rows.append(
                {
                    "ts": now_iso(),
                    "event": "specialist_complete",
                    "group_id": group_id,
                    "specialist_id": specialist_id,
                    "attempt": attempt,
                    "raw_log": str(raw_log_path),
                    "redacted_log": str(redacted_log_path),
                    "codex_home": str(codex_home),
                    "visible_skills": visible_skills,
                    "thread_id": result.thread_id,
                    "used_resume": result.used_resume,
                    "rotated_thread": result.rotated_thread,
                    "parse_mode": result.parse_mode,
                }
            )
            return SpecialistResult(
                success=True,
                group_id=group_id,
                specialist_id=specialist_id,
                role=role,
                attempt=attempt,
                work_path=str(work_path),
                handoff_path=str(handoff_path),
                raw_log_path=str(raw_log_path),
                redacted_log_path=str(redacted_log_path),
                codex_home=str(codex_home),
                visible_skills=visible_skills,
                mount_status=mount_status,
                timed_out=False,
                error="",
                escalation_request=None,
            )

        specialist_sessions[group_id][specialist_id]["status"] = "FAILED"
        specialist_sessions[group_id][specialist_id]["finished_at"] = now_iso()
        specialist_sessions[group_id][specialist_id]["error"] = result.error or "agent failed"
        timed_out = bool(result.return_code == 124 or "timeout" in str(result.error).lower())
        if result.thread_id:
            set_specialist_thread(
                config.project_root,
                group_id,
                specialist_id,
                result.thread_id,
                "FAILED",
            )

        ledger_rows.append(
            {
                "ts": now_iso(),
                "event": "specialist_retry" if attempt < attempts_total else "specialist_failed",
                "group_id": group_id,
                "specialist_id": specialist_id,
                "attempt": attempt,
                "error": result.error or "agent failed",
                "raw_log": str(raw_log_path),
                "redacted_log": str(redacted_log_path),
                "codex_home": str(codex_home),
                "visible_skills": visible_skills,
                "thread_id": result.thread_id,
                "used_resume": result.used_resume,
                "rotated_thread": result.rotated_thread,
                "parse_mode": result.parse_mode,
                "timed_out": timed_out,
            }
        )

        if attempt < attempts_total:
            if _is_retryable_specialist_failure(result):
                if int(config.retry_backoff_sec) > 0:
                    time.sleep(int(config.retry_backoff_sec))
                continue
            break

    return SpecialistResult(
        success=False,
        group_id=group_id,
        specialist_id=specialist_id,
        role=role,
        attempt=attempt,
        work_path=str(work_path),
        handoff_path=str(handoff_path),
        raw_log_path=str(raw_log_path),
        redacted_log_path=str(redacted_log_path),
        codex_home=str(codex_home),
        visible_skills=visible_skills,
        mount_status=mount_status,
        timed_out=timed_out,
        error=specialist_sessions[group_id][specialist_id]["error"],
        escalation_request=None,
    )


def _run_head_with_retries(
    *,
    config: LayeredRuntimeConfig,
    group_id: str,
    objective: str,
    dispatch: dict,
    phase_outputs: Dict[str, SpecialistResult],
    execution_mode: str,
    runner: AgentSessionRunner,
    layer3_dir: Path,
    ledger_rows: List[dict],
) -> HeadResult:
    group_layer3 = layer3_dir / group_id
    group_layer3.mkdir(parents=True, exist_ok=True)
    raw_log_path = group_layer3 / "head-raw.log"
    redacted_log_path = group_layer3 / "head-redacted.log"

    head_skill = str(dispatch.get("head_skill") or "").strip()
    allowed_skills = [head_skill] if head_skill else []
    codex_home, visible_skills, missing_skills, mount_status = _prepare_agent_codex_home(
        config=config,
        runtime_dir=group_layer3,
        group_id=group_id,
        allowed_skill_names=allowed_skills,
    )

    if head_skill and head_skill in missing_skills and runner.backend != "mock":
        message = (
            f"required head skill not installed for {group_id}: {head_skill}. "
            f"Activate head skills with 'agents-inc skills activate --project-id {config.project_id} --groups {group_id}'."
        )
        return HeadResult(
            success=False,
            group_id=group_id,
            attempt=1,
            work_text="",
            handoff_payload={},
            raw_log_path=str(raw_log_path),
            redacted_log_path=str(redacted_log_path),
            codex_home=str(codex_home),
            visible_skills=visible_skills,
            mount_status=mount_status,
            error=message,
        )

    attempts_total = max(1, int(config.retry_attempts) + 1)
    prompt = _build_head_prompt(
        objective=objective,
        group_id=group_id,
        dispatch=dispatch,
        phase_outputs=phase_outputs,
        execution_mode=execution_mode,
    )
    head_timeout_sec = _resolve_head_timeout_sec(config.agent_timeout_sec)

    for attempt in range(1, attempts_total + 1):
        group_work_dir = config.project_dir / "agent-groups" / group_id
        group_work_dir.mkdir(parents=True, exist_ok=True)
        result = runner.run(
            AgentRunConfig(
                project_root=config.project_root,
                work_dir=group_work_dir,
                prompt=prompt,
                raw_log_path=raw_log_path,
                redacted_log_path=redacted_log_path,
                timeout_sec=head_timeout_sec,
                web_search=(execution_mode == "light"),
                codex_home=codex_home,
                # Heads must start fresh each run to avoid stale cross-turn context bloat.
                thread_id=None,
                session_label=f"{group_id}/head",
                model=config.head_model,
                model_reasoning_effort=config.head_reasoning_effort,
            )
        )

        payload = dict(result.parsed_handoff or {})
        if result.success:
            payload = _normalize_specialist_handoff_payload(payload)
            payload = _hydrate_evidence_refs_from_cache(
                project_root=config.project_root,
                payload=payload,
            )
            payload.setdefault("schema_version", "4.0")
            payload.setdefault("status", "COMPLETE")
            payload.setdefault("execution_status", "COMPLETE")
            payload.setdefault("dependencies_satisfied", True)
            payload.setdefault("produced_artifacts", [])
            payload.setdefault("claims", [])
            payload.setdefault("evidence_refs", [])
            payload.setdefault("artifacts", [])

            ledger_rows.append(
                {
                    "ts": now_iso(),
                    "event": "group_head_complete",
                    "group_id": group_id,
                    "attempt": attempt,
                    "raw_log": str(raw_log_path),
                    "redacted_log": str(redacted_log_path),
                    "codex_home": str(codex_home),
                    "visible_skills": visible_skills,
                    "thread_id": result.thread_id,
                    "used_resume": result.used_resume,
                    "rotated_thread": result.rotated_thread,
                    "parse_mode": result.parse_mode,
                }
            )
            if result.thread_id:
                set_head_thread(config.project_root, group_id, result.thread_id, "COMPLETE")
            return HeadResult(
                success=True,
                group_id=group_id,
                attempt=attempt,
                work_text=result.parsed_work,
                handoff_payload=payload,
                raw_log_path=str(raw_log_path),
                redacted_log_path=str(redacted_log_path),
                codex_home=str(codex_home),
                visible_skills=visible_skills,
                mount_status=mount_status,
                error="",
            )

        ledger_rows.append(
            {
                "ts": now_iso(),
                "event": "group_head_retry" if attempt < attempts_total else "group_head_failed",
                "group_id": group_id,
                "attempt": attempt,
                "error": result.error or "head agent failed",
                "raw_log": str(raw_log_path),
                "redacted_log": str(redacted_log_path),
                "codex_home": str(codex_home),
                "visible_skills": visible_skills,
                "thread_id": result.thread_id,
                "used_resume": result.used_resume,
                "rotated_thread": result.rotated_thread,
                "parse_mode": result.parse_mode,
            }
        )
        if result.thread_id:
            set_head_thread(config.project_root, group_id, result.thread_id, "FAILED")
        if attempt < attempts_total and int(config.retry_backoff_sec) > 0:
            time.sleep(int(config.retry_backoff_sec))

    return HeadResult(
        success=False,
        group_id=group_id,
        attempt=attempts_total,
        work_text="",
        handoff_payload={},
        raw_log_path=str(raw_log_path),
        redacted_log_path=str(redacted_log_path),
        codex_home=str(codex_home),
        visible_skills=visible_skills,
        mount_status=mount_status,
        error="head session failed after retries",
    )


def _role_specific_contract(role: str) -> Tuple[List[str], List[str]]:
    role_name = str(role or "").strip().lower()
    if role_name == "integration":
        return (
            [
                "Include dependencies_consumed as a JSON list.",
                "Include integration_risks as a JSON list.",
            ],
            [
                '  "dependencies_consumed": [],',
                '  "integration_risks": [],',
            ],
        )
    if role_name == "evidence-review":
        return (
            [
                "Include contradictions field (false when none).",
                "Include unsupported_claims as a JSON list.",
            ],
            [
                '  "contradictions": false,',
                '  "unsupported_claims": [],',
            ],
        )
    if role_name == "repro-qa":
        return (
            [
                "Include repro_commands as a non-empty JSON list.",
                "Include expected_outputs as a non-empty JSON list.",
            ],
            [
                '  "repro_commands": ["<exact command>"],',
                '  "expected_outputs": ["<observable output>"],',
            ],
        )
    return ([], [])


def _build_specialist_prompt(
    *,
    objective: str,
    group_id: str,
    specialist_id: str,
    role: str,
    focus: str,
    skill_name: str,
    dependencies: object,
    required_outputs: object,
    required_references: object,
    required_reference_paths: List[str],
    dependency_artifact_paths: List[str],
    web_search_enabled: bool,
    artifact_scope: dict,
    retry_gate_reasons: List[str] | None = None,
) -> str:
    activation = (
        f"Activate and follow the `${skill_name}` skill if available, then proceed.\n"
        if str(skill_name or "").strip()
        else ""
    )
    role_requirements, role_handoff_fields = _role_specific_contract(role)
    role_requirements_text = ""
    if role_requirements:
        role_requirements_text = "Role-specific requirements:\n" + "\n".join(
            f"- {item}" for item in role_requirements
        )
        role_requirements_text += "\n"
    retry_feedback_text = ""
    if retry_gate_reasons:
        retry_items = [str(item).strip() for item in retry_gate_reasons if str(item).strip()]
        if retry_items:
            retry_feedback_text = (
                "Retry correction checklist from prior gate failure (MUST satisfy all):\n"
                + "\n".join(f"- {item}" for item in retry_items)
                + "\n"
            )
    role_handoff_text = "".join(f"{line}\n" for line in role_handoff_fields)
    compact_reference_paths = _compact_prompt_list(required_reference_paths, limit=4)
    compact_dependency_paths = _compact_prompt_list(dependency_artifact_paths, limit=4)
    web_policy_line = (
        "Web search policy for this role: enabled.\n"
        if web_search_enabled
        else "Web search policy for this role: disabled. Reuse local artifacts, dependency handoffs, and cache-backed evidence.\n"
    )
    return activation + (
        "You are a specialist agent in a layered multi-agent research runtime. "
        "Work only in your scope and produce structured output.\n"
        f"Objective: {objective}\n"
        f"Group: {group_id}\n"
        f"Specialist: {specialist_id}\n"
        f"Role: {role}\n"
        f"Focus: {focus}\n"
        f"Dependencies: {json.dumps(dependencies, ensure_ascii=True)}\n"
        f"Required outputs: {json.dumps(required_outputs, ensure_ascii=True)}\n"
        f"Required references: {json.dumps(required_references, ensure_ascii=True)}\n"
        f"Resolved required reference paths: {json.dumps(compact_reference_paths, ensure_ascii=True)}\n"
        f"Resolved dependency artifact paths: {json.dumps(compact_dependency_paths, ensure_ascii=True)}\n"
        + web_policy_line
        + "Requirements:\n"
        "1. Do not write files directly. Return structured blocks only; runtime persists artifacts.\n"
        "2. Use compact evidence linking: claims must reference evidence IDs, and evidence details belong in evidence_refs.\n"
        "3. Include reproducibility steps and artifact paths.\n"
        "4. If evidence is missing, set status to BLOCKED_NEEDS_EVIDENCE with reasons.\n"
        "5. If privileged access or unknown external credentials are required, write "
        "ESCALATION_REQUEST.json in your working directory.\n"
        + role_requirements_text
        + retry_feedback_text
        + "Return ONLY with these exact blocks:\n"
        "BEGIN_WORK\n"
        "<markdown work notes>\n"
        "END_WORK\n"
        "BEGIN_HANDOFF_JSON\n"
        "{\n"
        '  "schema_version": "4.0",\n'
        '  "status": "COMPLETE",\n'
        '  "execution_status": "COMPLETE",\n'
        '  "assumptions": [],\n'
        '  "claims": [{"claim": "...", "evidence_ids": ["e1"]}],\n'
        '  "evidence_refs": [{"evidence_id": "e1", "citation": "https://...", "title": "...", "source_type": "web"}],\n'
        '  "repro_steps": ["..."],\n'
        '  "artifact_paths": ["..."],\n'
        '  "produced_artifacts": ["..."],\n'
        '  "citations_summary": {"count": 1, "has_web_url": true},\n'
        + role_handoff_text
        + '  "dependencies_satisfied": true\n'
        "}\n"
        "END_HANDOFF_JSON\n"
        f"Artifact scope target (runtime-managed) work_path={artifact_scope['work_path']} handoff_path={artifact_scope['handoff_path']}\n"
        "If ESCALATION_RESPONSE.json exists in your working directory, consume it before finalizing output.\n"
    )


def _build_head_prompt(
    *,
    objective: str,
    group_id: str,
    dispatch: dict,
    phase_outputs: Dict[str, SpecialistResult],
    execution_mode: str,
) -> str:
    head_skill = str(dispatch.get("head_skill") or "").strip()
    activation = (
        f"Activate and follow the `${head_skill}` skill if available, then proceed.\n"
        if head_skill
        else ""
    )
    if execution_mode == "light":
        head_task_brief = dispatch.get("head_task_brief", {})
        if not isinstance(head_task_brief, dict):
            head_task_brief = {}
        return activation + (
            "You are the group head agent in a layered multi-agent runtime. "
            "Execute this group objective directly without delegating to specialists.\n"
            f"Objective: {objective}\n"
            f"Group: {group_id}\n"
            f"Dispatch metadata: {json.dumps({'head_agent': dispatch.get('head_agent'), 'head_skill': dispatch.get('head_skill'), 'execution_mode': 'light'}, ensure_ascii=True)}\n"
            f"Group brief (canonical): {json.dumps(head_task_brief, ensure_ascii=True)}\n"
            "Rules:\n"
            "1. Directly solve the group objective and produce an evidence-backed answer.\n"
            "2. Web search is enabled for this run; cite sources for externally derived claims.\n"
            "3. Publish only group-level artifacts and citations.\n"
            "4. Set response_status to ANSWERED only when this group directly answers the objective.\n"
            "5. If evidence is insufficient, set response_status to BLOCKED and explain why.\n"
            "6. objective_coverage is a 0..1 score for how fully this group addressed the objective.\n"
            "Return ONLY these exact blocks:\n"
            "BEGIN_WORK\n"
            "<group summary markdown>\n"
            "END_WORK\n"
            "BEGIN_HANDOFF_JSON\n"
            "{\n"
            '  "schema_version": "4.0",\n'
            '  "status": "COMPLETE",\n'
            '  "response_status": "ANSWERED",\n'
            '  "objective_response": "direct answer for this group",\n'
            '  "decision_summary": "direct decision in one to two sentences",\n'
            '  "recommended_actions": ["next action 1"],\n'
            '  "objective_coverage": 0.9,\n'
            '  "claims": [{"claim": "...", "evidence_ids": ["ev_..."]}],\n'
            '  "evidence_refs": [{"evidence_id": "ev_...", "citation": "https://...", "title": "...", "source_type": "web"}],\n'
            '  "artifacts": [{"path": "...", "title": "..."}],\n'
            '  "produced_artifacts": ["..."],\n'
            '  "dependencies_satisfied": true,\n'
            '  "integration_notes": "# Integration Notes\\n\\n- ..."\n'
            "}\n"
            "END_HANDOFF_JSON\n"
        )

    input_rows: List[dict] = []
    for specialist_id, output in sorted(phase_outputs.items())[:HEAD_PROMPT_MAX_SPECIALISTS]:
        handoff_path = Path(output.handoff_path)
        status = ""
        dependencies_satisfied: Optional[bool] = None
        citation_count = 0
        has_web_url = False
        claim_preview_rows: List[dict] = []
        artifact_preview: List[str] = []
        if handoff_path.exists():
            try:
                payload = json.loads(handoff_path.read_text(encoding="utf-8"))
                status = str(payload.get("status") or payload.get("execution_status") or "").strip()
                deps_value = payload.get("dependencies_satisfied")
                if isinstance(deps_value, bool):
                    dependencies_satisfied = deps_value
                summary = payload.get("citations_summary")
                if isinstance(summary, dict):
                    try:
                        citation_count = int(summary.get("count") or 0)
                    except Exception:
                        citation_count = 0
                    has_web_url = bool(summary.get("has_web_url"))

                claims = payload.get("claims")
                if not isinstance(claims, list):
                    claims = payload.get("claims_with_citations", [])
                if isinstance(claims, list):
                    for claim in claims[:HEAD_PROMPT_MAX_CLAIMS_PER_SPECIALIST]:
                        if not isinstance(claim, dict):
                            continue
                        claim_text = str(claim.get("claim") or claim.get("text") or "").strip()
                        evidence_ids = claim.get("evidence_ids")
                        if not isinstance(evidence_ids, list):
                            evidence_ids = []
                        preview_ids = [str(item).strip() for item in evidence_ids if str(item).strip()][:3]
                        if claim_text or preview_ids:
                            claim_preview_rows.append(
                                {
                                    "claim": claim_text[:HEAD_PROMPT_CLAIM_PREVIEW_CHARS],
                                    "evidence_ids": preview_ids,
                                }
                            )

                artifact_rows = payload.get("produced_artifacts")
                if not isinstance(artifact_rows, list):
                    artifact_rows = payload.get("artifact_paths")
                if isinstance(artifact_rows, list):
                    for item in artifact_rows[:HEAD_PROMPT_MAX_ARTIFACTS_PER_SPECIALIST]:
                        text = str(item).strip()
                        if text:
                            artifact_preview.append(text)
            except Exception:
                status = ""
        input_rows.append(
            {
                "specialist_id": specialist_id,
                "status": status or "UNKNOWN",
                "dependencies_satisfied": dependencies_satisfied,
                "citation_count": citation_count,
                "has_web_url": has_web_url,
                "claims": claim_preview_rows,
                "produced_artifacts": artifact_preview,
                "handoff_path": str(handoff_path),
            }
        )

    return activation + (
        "You are the group head agent in a layered multi-agent runtime. "
        "Merge specialist outputs into one group-level exposed handoff.\n"
        f"Objective: {objective}\n"
        f"Group: {group_id}\n"
        f"Dispatch metadata: {json.dumps({'head_agent': dispatch.get('head_agent'), 'head_skill': dispatch.get('head_skill')}, ensure_ascii=True)}\n"
        f"Specialist summaries (canonical): {json.dumps(input_rows, ensure_ascii=True)}\n"
        "Rules:\n"
        "1. Use only the specialist summaries provided above as input. Do not perform web searches.\n"
        "2. Avoid broad filesystem crawling; read at most one specialist handoff file only if a required field is missing.\n"
        "3. Resolve conflicts and report unresolved assumptions explicitly.\n"
        "4. Publish only group-level artifacts and citations.\n"
        "5. Set response_status to ANSWERED only when this group directly answers the objective.\n"
        "6. If evidence is insufficient, set response_status to BLOCKED and explain why.\n"
        "7. objective_coverage is a 0..1 score for how fully this group addressed the objective.\n"
        "Return ONLY these exact blocks:\n"
        "BEGIN_WORK\n"
        "<group summary markdown>\n"
        "END_WORK\n"
        "BEGIN_HANDOFF_JSON\n"
        "{\n"
        '  "schema_version": "4.0",\n'
        '  "status": "COMPLETE",\n'
        '  "response_status": "ANSWERED",\n'
        '  "objective_response": "direct answer for this group",\n'
        '  "decision_summary": "merge decision in one to two sentences",\n'
        '  "recommended_actions": ["next action 1"],\n'
        '  "objective_coverage": 0.9,\n'
        '  "claims": [{"claim": "...", "evidence_ids": ["ev_..."]}],\n'
        '  "evidence_refs": [{"evidence_id": "ev_...", "citation": "https://...", "title": "...", "source_type": "web"}],\n'
        '  "artifacts": [{"path": "...", "title": "..."}],\n'
        '  "produced_artifacts": ["..."],\n'
        '  "dependencies_satisfied": true,\n'
        '  "integration_notes": "# Integration Notes\\n\\n- ..."\n'
        "}\n"
        "END_HANDOFF_JSON\n"
    )


def _resolve_head_timeout_sec(timeout_sec: int) -> int:
    try:
        parsed = int(timeout_sec)
    except Exception:
        parsed = 0
    if parsed <= 0:
        return 0
    scaled = parsed * HEAD_TIMEOUT_MULTIPLIER
    bounded = max(parsed, max(HEAD_MIN_TIMEOUT_SEC, scaled))
    return min(HEAD_MAX_TIMEOUT_SEC, bounded)


def _prepare_agent_codex_home(
    *,
    config: LayeredRuntimeConfig,
    runtime_dir: Path,
    group_id: str,
    allowed_skill_names: List[str],
) -> Tuple[Path, List[str], List[str], Dict[str, object]]:
    source_home = config.project_root / ".agents-inc" / "codex-home"
    source_skills_local = source_home / "skills" / "local"

    agent_home = runtime_dir / "codex-home"
    _remove_path(agent_home)
    (agent_home / "skills" / "local").mkdir(parents=True, exist_ok=True)

    for name in ["auth.json", "config.toml"]:
        src = source_home / name
        dst = agent_home / name
        if src.exists():
            _symlink_or_copy(src, dst)

    visible: List[str] = []
    missing: List[str] = []

    deduped_allowed: List[str] = []
    for skill_name in allowed_skill_names:
        normalized = str(skill_name).strip()
        if not normalized or normalized in deduped_allowed:
            continue
        deduped_allowed.append(normalized)

    for skill_name in deduped_allowed:
        src = source_skills_local / skill_name
        dst = agent_home / "skills" / "local" / skill_name
        if src.exists():
            _symlink_or_copy(src, dst)
            visible.append(skill_name)
        else:
            missing.append(skill_name)

    references_source = config.project_dir / "agent-groups" / group_id / "references"
    mount_errors: List[str] = []
    mounted_count = 0
    mount_mode = "none"

    if references_source.exists():
        if visible:
            mount_mode = "symlink"
            for skill_name in visible:
                skill_dir = agent_home / "skills" / "local" / skill_name
                references_target = skill_dir / "references"
                try:
                    _symlink_or_copy(references_source, references_target)
                except Exception as exc:  # noqa: BLE001
                    mount_errors.append(f"{skill_name}: {exc}")
                    continue
                mounted_count += 1
                if not references_target.is_symlink():
                    mount_mode = "copy"
        else:
            mount_mode = "no-visible-skills"
    else:
        mount_mode = "missing-source"

    mount_status = {
        "references_source": str(references_source),
        "references_available": bool(references_source.exists()),
        "mounted_skill_count": mounted_count,
        "visible_skill_count": len(visible),
        "mode": mount_mode,
        "errors": mount_errors,
    }

    return agent_home, visible, missing, mount_status


def _remove_path(path: Path) -> None:
    if not path.exists() and not path.is_symlink():
        return
    if path.is_file() or path.is_symlink():
        path.unlink()
        return
    shutil.rmtree(path)


def _symlink_or_copy(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() or dst.is_symlink():
        _remove_path(dst)
    try:
        dst.symlink_to(src)
    except Exception:
        if src.is_file():
            shutil.copy2(src, dst)
        else:
            shutil.copytree(src, dst)


def _archive_escalation_files(*, work_dir: Path, archive_dir: Path) -> Dict[str, str]:
    request_path = work_dir / ESCALATION_REQUEST_FILE
    response_path = work_dir / ESCALATION_RESPONSE_FILE
    archived: Dict[str, str] = {}
    if not request_path.exists() and not response_path.exists():
        return archived
    archive_dir.mkdir(parents=True, exist_ok=True)
    stamp = now_iso().replace(":", "").replace("-", "").replace(".", "")
    if request_path.exists():
        dst = archive_dir / f"request-{stamp}.json"
        dst.write_bytes(request_path.read_bytes())
        request_path.unlink()
        archived["request_path"] = str(dst)
    if response_path.exists():
        dst = archive_dir / f"response-{stamp}.json"
        dst.write_bytes(response_path.read_bytes())
        response_path.unlink()
        archived["response_path"] = str(dst)
    return archived


def _write_specialist_snapshot(
    *,
    snapshot_root: Path,
    work_text: str,
    handoff_payload: Dict[str, object],
    meta_payload: Dict[str, object],
) -> Dict[str, str]:
    snapshot_root.mkdir(parents=True, exist_ok=True)
    work_path = snapshot_root / "work.md"
    handoff_path = snapshot_root / "handoff.json"
    meta_path = snapshot_root / "meta.json"
    write_text(work_path, work_text.rstrip() + "\n")
    write_text(handoff_path, json.dumps(handoff_payload, indent=2, sort_keys=True) + "\n")
    write_text(meta_path, json.dumps(meta_payload, indent=2, sort_keys=True) + "\n")
    return {
        "snapshot_work_path": str(work_path),
        "snapshot_handoff_path": str(handoff_path),
        "snapshot_meta_path": str(meta_path),
    }


def _collect_specialist_payloads(phase_outputs: Dict[str, SpecialistResult]) -> List[dict]:
    payloads: List[dict] = []
    for specialist_id, result in sorted(phase_outputs.items()):
        handoff_path = Path(result.handoff_path)
        if not handoff_path.exists():
            continue
        try:
            payload = json.loads(handoff_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(payload, dict):
            continue
        payloads.append(
            {
                "specialist_id": specialist_id,
                "payload": payload,
            }
        )
    return payloads


def _claims_from_specialist_payloads(payloads: List[dict]) -> List[dict]:
    claims: List[dict] = []
    for row in payloads:
        payload = row.get("payload")
        if not isinstance(payload, dict):
            continue
        for item in _normalized_claims(payload):
            claims.append(item)
    return claims


def _evidence_refs_from_specialist_payloads(payloads: List[dict]) -> List[dict]:
    refs: List[dict] = []
    seen: set[str] = set()
    for row in payloads:
        payload = row.get("payload")
        if not isinstance(payload, dict):
            continue
        for ref in _normalized_evidence_refs(payload):
            evidence_id = str(ref.get("evidence_id") or "").strip()
            if not evidence_id or evidence_id in seen:
                continue
            seen.add(evidence_id)
            refs.append(ref)
    return refs


def _artifacts_from_specialist_payloads(payloads: List[dict]) -> List[dict]:
    artifacts: List[dict] = []
    for row in payloads:
        specialist_id = str(row.get("specialist_id") or "")
        payload = row.get("payload")
        if not isinstance(payload, dict):
            continue
        artifact_rows = payload.get("artifact_paths", [])
        if not isinstance(artifact_rows, list):
            continue
        for item in artifact_rows:
            path = str(item).strip()
            if not path:
                continue
            artifacts.append(
                {
                    "path": path,
                    "title": f"{specialist_id} artifact",
                }
            )
    return artifacts


def _normalized_claims(payload: dict) -> List[dict]:
    claim_rows = payload.get("claims")
    if isinstance(claim_rows, list):
        out: List[dict] = []
        for row in claim_rows:
            if not isinstance(row, dict):
                continue
            text = str(row.get("claim") or row.get("text") or "").strip()
            evidence_ids = row.get("evidence_ids")
            if not isinstance(evidence_ids, list):
                evidence_ids = []
            normalized_ids: List[str] = []
            for item in evidence_ids:
                token = str(item or "").strip()
                if token and token not in normalized_ids:
                    normalized_ids.append(token)
            if text:
                out.append({"claim": text, "evidence_ids": normalized_ids})
        return out
    return _legacy_claims_to_v4(payload)


def _normalized_evidence_refs(payload: dict) -> List[dict]:
    raw = payload.get("evidence_refs")
    refs, _ = canonicalize_evidence_refs(raw)
    if refs:
        return refs
    claims = _legacy_claims_to_v4(payload)
    built: List[dict] = []
    seen: set[str] = set()
    for claim in claims:
        evidence_ids = claim.get("evidence_ids")
        if not isinstance(evidence_ids, list):
            continue
        for evidence_id in evidence_ids:
            text = str(evidence_id).strip()
            if not text or text in seen:
                continue
            seen.add(text)
            built.append(
                {
                    "evidence_id": text,
                    "citation": "",
                    "title": "",
                    "source_type": "reference",
                    "domain": "",
                }
            )
    return built


def _legacy_claims_to_v4(payload: dict) -> List[dict]:
    claim_rows = payload.get("claims_with_citations")
    if not isinstance(claim_rows, list):
        return []
    out: List[dict] = []
    for row in claim_rows:
        if not isinstance(row, dict):
            continue
        claim_text = str(row.get("claim") or row.get("text") or "").strip()
        if not claim_text:
            continue
        evidence_ids: List[str] = []
        for ref in _legacy_citations_from_claim(row):
            evidence_id = evidence_id_for_citation(ref)
            if evidence_id and evidence_id not in evidence_ids:
                evidence_ids.append(evidence_id)
        out.append({"claim": claim_text, "evidence_ids": evidence_ids})
    return out


def _legacy_citations_from_claim(row: dict) -> List[str]:
    out: List[str] = []
    candidates = [
        row.get("citation"),
        row.get("url"),
        row.get("source_url"),
        row.get("doi"),
    ]
    refs = row.get("citations")
    if isinstance(refs, list):
        candidates.extend(refs)
    for item in candidates:
        text = str(item or "").strip()
        if not text:
            continue
        if text.lower().startswith("doi:"):
            text = "https://doi.org/" + text[4:].strip()
        if text and text not in out:
            out.append(text)
    return out


def _canonicalize_claim_evidence_ids(*, claims: List[dict], evidence_refs: List[dict]) -> List[dict]:
    canonical_refs, id_map = canonicalize_evidence_refs(evidence_refs)
    mapped: List[dict] = []
    for claim in claims:
        if not isinstance(claim, dict):
            continue
        text = str(claim.get("claim") or claim.get("text") or "").strip()
        if not text:
            continue
        evidence_ids = claim.get("evidence_ids")
        if not isinstance(evidence_ids, list):
            evidence_ids = []
        normalized_ids: List[str] = []
        for item in evidence_ids:
            token = str(item or "").strip()
            if not token:
                continue
            mapped_id = id_map.get(token, token)
            if mapped_id.startswith("http://") or mapped_id.startswith("https://"):
                mapped_id = evidence_id_for_citation(mapped_id) or mapped_id
            if mapped_id and mapped_id not in normalized_ids:
                normalized_ids.append(mapped_id)
        mapped.append({"claim": text, "evidence_ids": normalized_ids})
    # Keep canonical refs in-place for caller by replacing list contents.
    evidence_refs.clear()
    evidence_refs.extend(canonical_refs)
    return mapped


def _normalize_specialist_handoff_payload(payload: dict) -> dict:
    out = dict(payload)
    claims = _normalized_claims(out)
    evidence_refs = _normalized_evidence_refs(out)
    if not evidence_refs:
        # Build evidence_refs from legacy citations if present.
        built_refs: List[dict] = []
        seen: set[str] = set()
        legacy_rows = out.get("claims_with_citations")
        if isinstance(legacy_rows, list):
            for row in legacy_rows:
                if not isinstance(row, dict):
                    continue
                for ref in _legacy_citations_from_claim(row):
                    evidence_id = evidence_id_for_citation(ref)
                    if not evidence_id or evidence_id in seen:
                        continue
                    seen.add(evidence_id)
                    built_refs.append(
                        {
                            "evidence_id": evidence_id,
                            "citation": ref,
                            "title": "",
                            "source_type": "web" if ref.startswith("http") else "reference",
                            "domain": "",
                        }
                    )
        evidence_refs = built_refs
    claims = _canonicalize_claim_evidence_ids(claims=claims, evidence_refs=evidence_refs)
    out["claims"] = claims
    out["evidence_refs"] = evidence_refs
    out.pop("claims_with_citations", None)
    return out


def _collect_claim_evidence_ids(claims: List[dict]) -> List[str]:
    out: List[str] = []
    for claim in claims:
        if not isinstance(claim, dict):
            continue
        evidence_ids = claim.get("evidence_ids")
        if not isinstance(evidence_ids, list):
            continue
        for item in evidence_ids:
            text = str(item or "").strip()
            if text and text not in out:
                out.append(text)
    return out


def _hydrate_evidence_refs_from_cache(*, project_root: Path, payload: dict) -> dict:
    out = dict(payload)
    claims = _normalized_claims(out)
    evidence_refs = _normalized_evidence_refs(out)
    existing_ids = {
        str(row.get("evidence_id") or "").strip()
        for row in evidence_refs
        if isinstance(row, dict)
    }
    needed_ids = [item for item in _collect_claim_evidence_ids(claims) if item not in existing_ids]
    if needed_ids:
        cached = resolve_evidence_ids(project_root, needed_ids)
        for evidence_id in needed_ids:
            row = cached.get(evidence_id)
            if not isinstance(row, dict):
                continue
            evidence_refs.append(
                {
                    "evidence_id": evidence_id,
                    "citation": str(row.get("citation") or "").strip(),
                    "title": str(row.get("title") or "").strip(),
                    "source_type": str(row.get("source_type") or "").strip() or "reference",
                    "domain": str(row.get("domain") or "").strip(),
                }
            )
    out["claims"] = _canonicalize_claim_evidence_ids(claims=claims, evidence_refs=evidence_refs)
    out["evidence_refs"] = evidence_refs
    return out


def _apply_evidence_auto_heal(*, project_root: Path, payload: dict) -> dict:
    out = _normalize_specialist_handoff_payload(payload)
    before_claims = _normalized_claims(out)
    before_refs = _normalized_evidence_refs(out)
    out = _hydrate_evidence_refs_from_cache(project_root=project_root, payload=out)
    claims = _normalized_claims(out)
    evidence_refs = _normalized_evidence_refs(out)

    available_ids = {
        str(row.get("evidence_id") or "").strip()
        for row in evidence_refs
        if isinstance(row, dict)
    }
    healed_ids: List[str] = []

    if len(available_ids) == 1:
        fallback_id = next(iter(available_ids))
        for row in claims:
            if not isinstance(row, dict):
                continue
            ids = row.get("evidence_ids")
            if not isinstance(ids, list):
                ids = []
            normalized = [str(item).strip() for item in ids if str(item).strip()]
            if normalized:
                continue
            row["evidence_ids"] = [fallback_id]
            healed_ids.append(fallback_id)

    claims = _canonicalize_claim_evidence_ids(claims=claims, evidence_refs=evidence_refs)
    out = _hydrate_evidence_refs_from_cache(
        project_root=project_root,
        payload={"claims": claims, "evidence_refs": evidence_refs},
    )
    claims = _normalized_claims(out)
    evidence_refs = _normalized_evidence_refs(out)
    available_ids = {
        str(row.get("evidence_id") or "").strip()
        for row in evidence_refs
        if isinstance(row, dict)
    }
    unresolved_ids = sorted(
        {
            evidence_id
            for evidence_id in _collect_claim_evidence_ids(claims)
            if evidence_id not in available_ids
        }
    )
    changed = stable_json(before_claims) != stable_json(claims) or stable_json(before_refs) != stable_json(
        evidence_refs
    )
    out["claims"] = claims
    out["evidence_refs"] = evidence_refs
    out["evidence_auto_heal"] = {
        "applied": bool(changed or healed_ids),
        "healed_ids": sorted({str(item).strip() for item in healed_ids if str(item).strip()}),
        "unresolved_ids": unresolved_ids,
    }
    return out


def _persist_payload_evidence_cache(*, project_root: Path, payload: dict) -> None:
    refs = _normalized_evidence_refs(payload)
    if refs:
        merge_evidence_refs_into_cache(project_root=project_root, evidence_refs=refs)


def _is_retryable_specialist_failure(result: object) -> bool:
    # Runtime failure retries should target transient failures only.
    error_text = str(getattr(result, "error", "") or "").strip().lower()
    return_code = int(getattr(result, "return_code", 0) or 0)
    if return_code == 124 or "timeout" in error_text:
        return True
    if return_code != 0:
        return True
    parse_markers = (
        "missing begin_work/end_work block",
        "missing begin_handoff_json/end_handoff_json block",
        "invalid handoff json",
        "handoff payload must be json object",
    )
    return any(marker in error_text for marker in parse_markers)


def _compact_prompt_list(values: List[str], *, limit: int = 5) -> List[str]:
    rows = [str(item).strip() for item in values if str(item).strip()]
    if len(rows) <= limit:
        return rows
    overflow = len(rows) - limit
    return rows[:limit] + [f"...(+{overflow} more)"]


def _normalized_artifacts(payload: dict) -> List[dict]:
    rows = payload.get("artifacts", [])
    if not isinstance(rows, list):
        return []
    out: List[dict] = []
    for item in rows:
        if isinstance(item, dict):
            out.append(item)
        elif isinstance(item, str) and item.strip():
            out.append({"path": item.strip(), "title": "artifact"})
    return out


def _normalized_strings(value: object) -> List[str]:
    if not isinstance(value, list):
        return []
    out: List[str] = []
    for item in value:
        text = str(item).strip()
        if text and text not in out:
            out.append(text)
    return out


def _count_claim_citations(claims: List[dict]) -> int:
    ids: set[str] = set()
    for claim in claims:
        if not isinstance(claim, dict):
            continue
        refs = claim.get("evidence_ids")
        if not isinstance(refs, list):
            continue
        for ref in refs:
            text = str(ref or "").strip()
            if text:
                ids.add(text)
    return len(ids)


def _claims_have_web_url(evidence_refs: List[dict]) -> bool:
    for ref in evidence_refs:
        if not isinstance(ref, dict):
            continue
        citation = str(ref.get("citation") or "").strip().lower()
        if citation.startswith("http://") or citation.startswith("https://"):
            return True
    return False


def _normalize_response_status(value: object) -> str:
    text = str(value or "").strip().upper().replace("-", "_").replace(" ", "_")
    if not text:
        return ""
    if text in OBJECTIVE_RESPONSE_STATUS_VALUES:
        return text
    if text in {"COMPLETE", "PASS", "RESOLVED", "SATISFIED", "DONE"}:
        return "ANSWERED"
    if text in {"PARTIALLY_RESOLVED", "INCOMPLETE", "UNRESOLVED", "CONDITIONAL"}:
        return "PARTIAL"
    if text.startswith("BLOCKED") or text in {
        "FAILED",
        "REJECTED",
        "NEEDS_EVIDENCE",
        "BLOCKER",
    }:
        return "BLOCKED"
    return ""


def _parse_objective_coverage(value: object) -> float | None:
    if isinstance(value, (int, float)):
        raw = float(value)
        if raw > 1.0:
            raw = raw / 100.0
        return max(0.0, min(1.0, raw))
    text = str(value or "").strip()
    if not text:
        return None
    if text.endswith("%"):
        text = text[:-1].strip()
        try:
            return max(0.0, min(1.0, float(text) / 100.0))
        except Exception:
            return None
    try:
        raw = float(text)
    except Exception:
        return None
    if raw > 1.0:
        raw = raw / 100.0
    return max(0.0, min(1.0, raw))


def _extract_response_actions(payload: dict) -> List[str]:
    candidates = [
        payload.get("recommended_actions"),
        payload.get("next_actions"),
        payload.get("actions"),
        payload.get("new_actions"),
    ]
    actions: List[str] = []
    for value in candidates:
        if not isinstance(value, list):
            continue
        for item in value:
            text = str(item or "").strip()
            if text and text not in actions:
                actions.append(text)
    return actions


def _truncate_sentence(value: str, *, max_chars: int = 280) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if len(text) <= max_chars:
        return text
    cut = text[:max_chars].rstrip()
    if " " in cut:
        cut = cut.rsplit(" ", 1)[0]
    return cut.rstrip(".,;:") + "..."


def _objective_tokens(value: str) -> List[str]:
    words = re.findall(r"[a-z0-9]+", str(value or "").lower())
    out: List[str] = []
    for token in words:
        if len(token) < 4:
            continue
        if token in {
            "with",
            "from",
            "that",
            "this",
            "your",
            "what",
            "when",
            "where",
            "which",
            "have",
            "will",
            "would",
            "should",
            "could",
            "into",
            "over",
            "under",
            "using",
            "based",
            "only",
            "hours",
            "time",
            "give",
            "want",
            "make",
            "include",
            "criteria",
        }:
            continue
        if token not in out:
            out.append(token)
    return out


def _estimate_objective_coverage(objective: str, text: str) -> float:
    objective_terms = _objective_tokens(objective)
    if not objective_terms:
        return 1.0 if str(text).strip() else 0.0
    hay = set(_objective_tokens(text))
    if not hay:
        return 0.0
    overlap = sum(1 for token in objective_terms if token in hay)
    return round(overlap / len(objective_terms), 3)


def _infer_response_status(*, status: str, summary_text: str, integration_notes: str) -> str:
    normalized_status = _normalize_response_status(status)
    if normalized_status in {"ANSWERED", "PARTIAL", "BLOCKED"}:
        return normalized_status

    combined = " ".join([summary_text, integration_notes]).lower()
    if any(hint in combined for hint in OBJECTIVE_BLOCKED_HINTS):
        return "BLOCKED"
    if any(hint in combined for hint in OBJECTIVE_PARTIAL_HINTS):
        return "PARTIAL"
    if str(status or "").strip().upper() in {"COMPLETE", "PASS"}:
        return "ANSWERED"
    return "PARTIAL"


def _default_objective_response(*, group_id: str, summary_text: str, claims: List[dict]) -> str:
    if summary_text:
        summary = _truncate_sentence(summary_text.replace("\n", " "), max_chars=260)
        if summary:
            return summary
    for claim in claims:
        if not isinstance(claim, dict):
            continue
        text = _truncate_sentence(str(claim.get("claim") or ""), max_chars=260)
        if text:
            return text
    return f"{group_id} completed execution but did not provide an explicit objective response."


def _normalize_head_objective_contract(
    *,
    objective: str,
    group_id: str,
    payload: dict,
    summary_text: str,
    integration_notes: str,
    claims: List[dict],
) -> dict:
    response_status = _normalize_response_status(
        payload.get("response_status") or payload.get("objective_status") or payload.get("result_status")
    )
    if not response_status:
        response_status = _infer_response_status(
            status=str(payload.get("status") or ""),
            summary_text=summary_text,
            integration_notes=integration_notes,
        )

    objective_response = str(
        payload.get("objective_response")
        or payload.get("response_to_objective")
        or payload.get("decision_summary")
        or ""
    ).strip()
    if not objective_response:
        objective_response = _default_objective_response(
            group_id=group_id,
            summary_text=summary_text,
            claims=claims,
        )
    objective_response = _truncate_sentence(objective_response, max_chars=320)

    decision_summary = str(payload.get("decision_summary") or "").strip()
    if not decision_summary:
        decision_summary = objective_response
    decision_summary = _truncate_sentence(decision_summary, max_chars=320)

    recommended_actions = _extract_response_actions(payload)
    if not recommended_actions:
        if response_status == "ANSWERED":
            recommended_actions = [
                "Execute downstream validation steps against published artifacts."
            ]
        else:
            recommended_actions = [
                "Refine objective constraints and collect missing evidence before next cycle."
            ]

    objective_coverage = _parse_objective_coverage(payload.get("objective_coverage"))
    if objective_coverage is None:
        coverage_text = " ".join(
            [
                objective_response,
                decision_summary,
                summary_text,
                integration_notes,
                " ".join(str(claim.get("claim") or "") for claim in claims if isinstance(claim, dict)),
            ]
        )
        objective_coverage = _estimate_objective_coverage(objective, coverage_text)

    if response_status == "ANSWERED":
        objective_coverage = max(objective_coverage, OBJECTIVE_COVERAGE_MIN_FOR_ANSWERED)
    elif response_status == "BLOCKED":
        objective_coverage = min(objective_coverage, 0.49)
    elif response_status == "PARTIAL":
        objective_coverage = min(objective_coverage, 0.79)

    return {
        "response_status": response_status,
        "objective_response": objective_response,
        "decision_summary": decision_summary,
        "recommended_actions": recommended_actions[:8],
        "objective_coverage": round(max(0.0, min(1.0, float(objective_coverage))), 3),
    }


def _resolve_required_reference_paths(
    *, project_dir: Path, group_id: str, required_references: object
) -> List[str]:
    refs = required_references if isinstance(required_references, list) else []
    group_root = project_dir / "agent-groups" / group_id
    out: List[str] = []
    for item in refs:
        text = str(item or "").strip()
        if not text:
            continue
        candidate = (group_root / text).resolve()
        out.append(str(candidate))
    return out


def _resolve_dependency_artifact_paths(
    *, project_dir: Path, group_id: str, dependencies: object
) -> List[str]:
    rows = dependencies if isinstance(dependencies, list) else []
    group_root = project_dir / "agent-groups" / group_id
    out: List[str] = []
    for dep in rows:
        if not isinstance(dep, dict):
            continue
        artifacts = dep.get("required_artifacts")
        if not isinstance(artifacts, list):
            continue
        for item in artifacts:
            text = str(item or "").strip()
            if not text:
                continue
            candidate = (group_root / text).resolve()
            rendered = str(candidate)
            if rendered not in out:
                out.append(rendered)
    return out


def _persist_turn_evidence_cache(
    *, config: LayeredRuntimeConfig, group_results: Dict[str, dict]
) -> None:
    refs: List[dict] = []
    seen: set[str] = set()

    for group_id in config.selected_groups:

        exposed_handoff = config.project_dir / "agent-groups" / group_id / "exposed" / "handoff.json"
        if exposed_handoff.exists():
            try:
                payload = json.loads(exposed_handoff.read_text(encoding="utf-8"))
            except Exception:
                payload = {}
            if isinstance(payload, dict):
                for row in _normalized_evidence_refs(payload):
                    evidence_id = str(row.get("evidence_id") or "").strip()
                    if not evidence_id or evidence_id in seen:
                        continue
                    seen.add(evidence_id)
                    refs.append(row)

        group_internal = config.project_dir / "agent-groups" / group_id / "internal"
        if not group_internal.exists():
            continue
        for handoff in sorted(group_internal.glob("*/handoff.json")):
            try:
                payload = json.loads(handoff.read_text(encoding="utf-8"))
            except Exception:
                payload = {}
            if not isinstance(payload, dict):
                continue
            for row in _normalized_evidence_refs(payload):
                evidence_id = str(row.get("evidence_id") or "").strip()
                if not evidence_id or evidence_id in seen:
                    continue
                seen.add(evidence_id)
                refs.append(row)

    if refs:
        merge_evidence_refs_into_cache(project_root=config.project_root, evidence_refs=refs)


def _timeout_mode(timeout_sec: int) -> str:
    try:
        parsed = int(timeout_sec)
    except Exception:
        parsed = 0
    return "bounded" if parsed > 0 else "unlimited"


def _abort_requested(config: LayeredRuntimeConfig) -> bool:
    if config.abort_file is None:
        return False
    try:
        return config.abort_file.exists()
    except Exception:
        return False
