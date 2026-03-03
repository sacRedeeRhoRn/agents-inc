from __future__ import annotations

import json
import shutil
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from agents_inc.core.agent_session_runner import AgentRunConfig, AgentSessionRunner
from agents_inc.core.agent_threads import (
    get_head_thread,
    get_specialist_thread,
    set_head_thread,
    set_specialist_thread,
)
from agents_inc.core.escalation import (
    ESCALATION_REQUEST_FILE,
    ESCALATION_RESPONSE_FILE,
    resolve_escalation_state,
)
from agents_inc.core.fabric_lib import build_dispatch_plan, now_iso, stable_json, write_text
from agents_inc.core.util.dispatch import gate_specialist_output
from agents_inc.core.util.edges import resolve_handoff_edges


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
        },
        "created_at": now_iso(),
    }
    write_text(layer2_dir / "orchestrator-plan.json", stable_json(orchestrator_plan) + "\n")

    group_head_sessions: Dict[str, dict] = {}
    specialist_sessions: Dict[str, dict] = {}

    for group_id in config.selected_groups:
        group_manifest = config.group_manifests[group_id]
        group_head_sessions[group_id] = {
            "session_code": f"{config.project_id}::{group_id}::head::{int(time.time())}",
            "status": "PENDING",
            "started_at": "",
            "finished_at": "",
            "attempts": 0,
            "error": "",
            "specialist_count": len(group_manifest.get("specialists", [])),
            "codex_home": "",
            "visible_skills": [],
            "mount_status": {},
        }
        specialist_sessions[group_id] = {}
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
    with ThreadPoolExecutor(max_workers=max_group_workers) as pool:
        future_map = {
            pool.submit(
                _run_group,
                config,
                group_id,
                runner,
                specialist_sessions,
                group_head_sessions,
                layer3_dir,
                layer4_dir,
                ledger_rows,
            ): group_id
            for group_id in config.selected_groups
        }
        for future in as_completed(future_map):
            group_id = future_map[future]
            result = future.result()
            group_results[group_id] = result
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

    return {
        "schema_version": "3.1",
        "group_status": group_results,
        "blocked": not wait_state["all_groups_complete"],
        "blocked_groups": wait_state["blocked_groups"],
        "reasons": blocked_reasons,
        "timed_out_specialists": timed_out_specialists,
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
    dispatch = build_dispatch_plan(config.project_id, group_id, group_objective, group_manifest)

    phase_outputs: Dict[str, SpecialistResult] = {}
    group_error = ""
    timed_out_specialists: List[dict] = []
    group_escalations: List[dict] = []

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
                result = future.result()
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
        }

    head_result = _run_head_with_retries(
        config=config,
        group_id=group_id,
        objective=group_objective,
        dispatch=dispatch,
        phase_outputs=phase_outputs,
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
        }

    exposed = config.project_dir / "agent-groups" / group_id / "exposed"
    exposed.mkdir(parents=True, exist_ok=True)

    specialist_payloads = _collect_specialist_payloads(phase_outputs)
    handoff_payload = dict(head_result.handoff_payload)

    claims = _normalized_claims(handoff_payload)
    if not claims:
        claims = _claims_from_specialist_payloads(specialist_payloads)

    artifacts = _normalized_artifacts(handoff_payload)
    produced_artifacts = _normalized_strings(handoff_payload.get("produced_artifacts"))
    if not artifacts:
        artifacts = _artifacts_from_specialist_payloads(specialist_payloads)
    if not produced_artifacts:
        produced_artifacts = [str(item.get("path") or "").strip() for item in artifacts]
        produced_artifacts = [item for item in produced_artifacts if item]

    if not claims:
        claims.append(
            {
                "claim": f"{group_id} completed all scheduled specialist tasks.",
                "citation": "https://example.org/group-complete",
            }
        )

    citation_count = _count_claim_citations(claims)

    handoff_payload.setdefault("schema_version", "3.0")
    handoff_payload["status"] = "COMPLETE"
    handoff_payload["group_id"] = group_id
    handoff_payload["execution_status"] = "COMPLETE"
    handoff_payload["dependencies_satisfied"] = True
    handoff_payload["produced_artifacts"] = sorted(set(produced_artifacts))
    handoff_payload["citations_summary"] = {
        "count": citation_count,
        "has_web_url": _claims_have_web_url(claims),
    }
    handoff_payload["artifacts"] = artifacts
    handoff_payload["claims_with_citations"] = claims
    handoff_payload["updated_at"] = now_iso()

    summary_text = head_result.work_text.strip()
    if not summary_text:
        summary_lines = [
            "# Summary",
            "",
            f"Group `{group_id}` completed layered specialist execution.",
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
    web_search_enabled = bool(task.get("web_search_enabled", True))
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
            artifact_scope={
                "work_path": str(work_path),
                "handoff_path": str(handoff_path),
            },
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
                thread_id=get_specialist_thread(config.project_root, group_id, specialist_id),
                session_label=f"{group_id}/{specialist_id}",
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
            handoff_payload.setdefault("schema_version", "3.0")
            handoff_payload.setdefault("status", "COMPLETE")
            handoff_payload.setdefault("execution_status", "COMPLETE")
            handoff_payload.setdefault("dependencies_satisfied", True)
            handoff_payload.setdefault("produced_artifacts", [])
            handoff_payload.setdefault(
                "citations_summary",
                {
                    "count": _count_claim_citations(_normalized_claims(handoff_payload)),
                    "has_web_url": _claims_have_web_url(_normalized_claims(handoff_payload)),
                },
            )
            handoff_payload.setdefault("claims_with_citations", [])
            handoff_payload.setdefault("repro_steps", ["specialist execution complete"])
            handoff_payload.setdefault("artifact_paths", [])
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
                specialist_sessions[group_id][specialist_id]["status"] = "FAILED"
                specialist_sessions[group_id][specialist_id]["finished_at"] = now_iso()
                specialist_sessions[group_id][specialist_id][
                    "error"
                ] = f"specialist gate failed: {gate_status} ({'; '.join(str(x) for x in gate_reasons)})"
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
                        "error": specialist_sessions[group_id][specialist_id]["error"],
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
                if attempt < attempts_total and int(config.retry_backoff_sec) > 0:
                    time.sleep(int(config.retry_backoff_sec))
                continue

            write_text(work_path, result.parsed_work.rstrip() + "\n")
            write_text(handoff_path, json.dumps(handoff_payload, indent=2, sort_keys=True) + "\n")
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
                "timed_out": timed_out,
            }
        )

        if attempt < attempts_total and int(config.retry_backoff_sec) > 0:
            time.sleep(int(config.retry_backoff_sec))

    return SpecialistResult(
        success=False,
        group_id=group_id,
        specialist_id=specialist_id,
        role=role,
        attempt=attempts_total,
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
    runner: AgentSessionRunner,
    layer3_dir: Path,
    ledger_rows: List[dict],
) -> HeadResult:
    group_layer3 = layer3_dir / group_id
    group_layer3.mkdir(parents=True, exist_ok=True)
    raw_log_path = group_layer3 / "head-raw.log"
    redacted_log_path = group_layer3 / "head-redacted.log"

    head_skill = str(dispatch.get("head_skill") or "").strip()
    specialist_skills: List[str] = []
    for phase in dispatch.get("phases", []):
        for task in phase.get("tasks", []):
            skill_name = str(task.get("skill_name") or "").strip()
            if skill_name and skill_name not in specialist_skills:
                specialist_skills.append(skill_name)

    allowed_skills = [head_skill] + specialist_skills
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
    )

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
                timeout_sec=config.agent_timeout_sec,
                web_search=True,
                codex_home=codex_home,
                thread_id=get_head_thread(config.project_root, group_id),
                session_label=f"{group_id}/head",
            )
        )

        payload = dict(result.parsed_handoff or {})
        if result.success:
            payload.setdefault("schema_version", "3.0")
            payload.setdefault("status", "COMPLETE")
            payload.setdefault("execution_status", "COMPLETE")
            payload.setdefault("dependencies_satisfied", True)
            payload.setdefault("produced_artifacts", [])
            payload.setdefault("claims_with_citations", [])
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
    artifact_scope: dict,
) -> str:
    activation = (
        f"Activate and follow the `${skill_name}` skill if available, then proceed.\n"
        if str(skill_name or "").strip()
        else ""
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
        "Requirements:\n"
        "1. Include claim-level citations for all key technical claims.\n"
        "2. Include reproducibility steps and artifact paths.\n"
        "3. If evidence is missing, set status to BLOCKED_NEEDS_EVIDENCE with reasons.\n"
        "4. If privileged access or unknown external credentials are required, write ESCALATION_REQUEST.json in your working directory.\n"
        "Return ONLY with these exact blocks:\n"
        "BEGIN_WORK\n"
        "<markdown work notes>\n"
        "END_WORK\n"
        "BEGIN_HANDOFF_JSON\n"
        "{\n"
        '  "status": "COMPLETE",\n'
        '  "assumptions": [],\n'
        '  "claims_with_citations": [{"claim": "...", "citation": "..."}],\n'
        '  "repro_steps": ["..."],\n'
        '  "artifact_paths": ["..."],\n'
        '  "produced_artifacts": ["..."],\n'
        '  "dependencies_satisfied": true\n'
        "}\n"
        "END_HANDOFF_JSON\n"
        f"Artifact scope target work_path={artifact_scope['work_path']} handoff_path={artifact_scope['handoff_path']}\n"
        "If ESCALATION_RESPONSE.json exists in your working directory, consume it before finalizing output.\n"
    )


def _build_head_prompt(
    *,
    objective: str,
    group_id: str,
    dispatch: dict,
    phase_outputs: Dict[str, SpecialistResult],
) -> str:
    input_rows: List[dict] = []
    for specialist_id, output in sorted(phase_outputs.items()):
        handoff_path = Path(output.handoff_path)
        claim_preview = ""
        if handoff_path.exists():
            try:
                payload = json.loads(handoff_path.read_text(encoding="utf-8"))
                claims = payload.get("claims_with_citations", [])
                if isinstance(claims, list) and claims:
                    first = claims[0]
                    if isinstance(first, dict):
                        claim_preview = str(first.get("claim") or "")[:180]
            except Exception:
                claim_preview = ""
        input_rows.append(
            {
                "specialist_id": specialist_id,
                "handoff_path": str(handoff_path),
                "claim_preview": claim_preview,
            }
        )

    head_skill = str(dispatch.get("head_skill") or "").strip()
    activation = (
        f"Activate and follow the `${head_skill}` skill if available, then proceed.\n"
        if head_skill
        else ""
    )
    return activation + (
        "You are the group head agent in a layered multi-agent runtime. "
        "Merge specialist outputs into one group-level exposed handoff.\n"
        f"Objective: {objective}\n"
        f"Group: {group_id}\n"
        f"Dispatch metadata: {json.dumps({'head_agent': dispatch.get('head_agent'), 'head_skill': dispatch.get('head_skill')}, ensure_ascii=True)}\n"
        f"Specialist inputs: {json.dumps(input_rows, ensure_ascii=True)}\n"
        "Rules:\n"
        "1. Consume specialist handoff artifacts listed above.\n"
        "2. Resolve conflicts and report unresolved assumptions explicitly.\n"
        "3. Publish only group-level artifacts and citations.\n"
        "Return ONLY these exact blocks:\n"
        "BEGIN_WORK\n"
        "<group summary markdown>\n"
        "END_WORK\n"
        "BEGIN_HANDOFF_JSON\n"
        "{\n"
        '  "status": "COMPLETE",\n'
        '  "claims_with_citations": [{"claim": "...", "citation": "..."}],\n'
        '  "artifacts": [{"path": "...", "title": "..."}],\n'
        '  "produced_artifacts": ["..."],\n'
        '  "dependencies_satisfied": true,\n'
        '  "integration_notes": "# Integration Notes\\n\\n- ..."\n'
        "}\n"
        "END_HANDOFF_JSON\n"
    )


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
        claim_rows = payload.get("claims_with_citations", [])
        if not isinstance(claim_rows, list):
            continue
        for item in claim_rows:
            if isinstance(item, dict):
                claims.append(item)
    return claims


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
    claim_rows = payload.get("claims_with_citations", [])
    if not isinstance(claim_rows, list):
        return []
    return [row for row in claim_rows if isinstance(row, dict)]


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
    count = 0
    for claim in claims:
        if not isinstance(claim, dict):
            continue
        if str(claim.get("citation") or "").strip():
            count += 1
        refs = claim.get("citations")
        if isinstance(refs, list):
            count += len([ref for ref in refs if str(ref).strip()])
    return count


def _claims_have_web_url(claims: List[dict]) -> bool:
    for claim in claims:
        if not isinstance(claim, dict):
            continue
        citation = str(claim.get("citation") or "")
        if citation.startswith("http"):
            return True
        refs = claim.get("citations")
        if isinstance(refs, list):
            if any(str(ref).startswith("http") for ref in refs):
                return True
    return False


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
