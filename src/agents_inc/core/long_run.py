from __future__ import annotations

import hashlib
import importlib.util
import json
import random
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from agents_inc.core.fabric_lib import (
    FabricError,
    build_dispatch_plan,
    dump_yaml,
    gate_specialist_output,
    load_project_manifest,
    load_yaml,
    now_iso,
    slugify,
    stable_json,
    write_text,
)
from agents_inc.core.session_compaction import compact_session
from agents_inc.core.session_state import (
    default_project_index_path,
    resolve_state_project_root,
    write_checkpoint,
)

CANONICAL_TASK = "Film thickness dependent polymorphism stability of metastable phase"
FULL_GROUPS: List[str] = [
    "material-scientist",
    "material-engineer",
    "developer",
    "designer",
    "data-curation",
    "literature-intelligence",
    "quality-assurance",
    "publication-packaging",
    "atomistic-hpc-simulation",
]
HANDOFF_EDGES: List[Tuple[str, str]] = [
    ("literature-intelligence", "data-curation"),
    ("literature-intelligence", "material-scientist"),
    ("literature-intelligence", "material-engineer"),
    ("data-curation", "material-scientist"),
    ("data-curation", "developer"),
    ("material-scientist", "atomistic-hpc-simulation"),
    ("atomistic-hpc-simulation", "material-scientist"),
    ("atomistic-hpc-simulation", "developer"),
    ("developer", "atomistic-hpc-simulation"),
    ("material-scientist", "material-engineer"),
    ("material-engineer", "quality-assurance"),
    ("material-scientist", "quality-assurance"),
    ("atomistic-hpc-simulation", "quality-assurance"),
    ("developer", "quality-assurance"),
    ("material-scientist", "designer"),
    ("material-engineer", "designer"),
    ("quality-assurance", "designer"),
    ("designer", "publication-packaging"),
    ("quality-assurance", "publication-packaging"),
    ("publication-packaging", "quality-assurance"),
]

EXIT_OK = 0
EXIT_ISOLATION_VIOLATION = 2
EXIT_LEASE_UNRESOLVED = 3
EXIT_COVERAGE_INSUFFICIENT = 4
EXIT_QUALITY_GATE = 5


@dataclass
class Actor:
    role: str  # specialist | head
    group_id: str
    agent_id: str


@dataclass
class LongRunConfig:
    fabric_root: Path
    project_id: str
    task: str
    groups: List[str]
    duration_min: int
    strict_isolation: str
    run_mode: str
    seed: int
    output_dir: Optional[Path]
    project_index_path: Optional[Path]
    audit: bool
    conflict_rate: float
    max_retries: int
    retry_backoff_ms: int
    ttl: int
    inject_isolation_violation: bool
    inject_lease_deadlock: bool
    inject_gate_expose_failure: bool


class _AbortRun(RuntimeError):
    pass


class _FallbackLease:
    def __init__(self, token: str, path: str, agent_id: str, expires_at: int) -> None:
        self.token = token
        self.path = path
        self.agent_id = agent_id
        self.expires_at = expires_at


class _FallbackDirectoryController:
    def __init__(self, root: str) -> None:
        self.root = Path(root)
        self._agents: set[str] = set()
        self._dirs: dict[str, bool] = {}
        self._leases: dict[str, _FallbackLease] = {}

    def init(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)

    def register_agent(self, agent_id: str, label: Optional[str] = None, meta: Optional[dict] = None) -> None:
        _ = label
        _ = meta
        self._agents.add(agent_id)

    def add_directory(self, path: str, shared: bool = False, allowed_agents: Optional[List[str]] = None) -> str:
        _ = allowed_agents
        self._dirs[path] = bool(shared)
        return path

    def acquire(self, agent_id: str, path: str, ttl_seconds: int = 300) -> _FallbackLease:
        if agent_id not in self._agents:
            raise RuntimeError(f"unknown agent: {agent_id}")
        if path not in self._dirs:
            raise RuntimeError(f"unknown directory: {path}")

        now_epoch = int(time.time())
        current = self._leases.get(path)
        if current and current.expires_at > now_epoch and current.agent_id != agent_id and not self._dirs[path]:
            raise RuntimeError("lease conflict")

        token = hashlib.sha1(f"{agent_id}:{path}:{now_epoch}".encode("utf-8")).hexdigest()[:20]
        lease = _FallbackLease(token=token, path=path, agent_id=agent_id, expires_at=now_epoch + ttl_seconds)
        self._leases[path] = lease
        return lease

    def heartbeat(self, token: str, ttl_seconds: int = 300) -> _FallbackLease:
        for lease in self._leases.values():
            if lease.token == token:
                lease.expires_at = int(time.time()) + ttl_seconds
                return lease
        raise RuntimeError("lease token not found")

    def release(self, agent_id: str, path: str, token: Optional[str] = None) -> int:
        current = self._leases.get(path)
        if not current:
            return 0
        if current.agent_id != agent_id:
            return 0
        if token is not None and current.token != token:
            return 0
        self._leases.pop(path, None)
        return 1


class LeaseBackend:
    def __init__(self, root: Path, lease_events: List[dict]) -> None:
        self.root = root
        self.lease_events = lease_events
        self._controller = self._load_controller(root)
        self.backend_name = "multi_agent_dirs" if self._controller.__class__.__name__ != "_FallbackDirectoryController" else "fallback"

    @staticmethod
    def _load_controller(root: Path):
        try:
            from controller import DirectoryController  # type: ignore

            ctl = DirectoryController(str(root))
            ctl.init()
            return ctl
        except Exception:
            pass

        candidate = root.parent / "multi_agent_dirs" / "controller.py"
        if candidate.exists():
            spec = importlib.util.spec_from_file_location("agents_inc_madir_controller", candidate)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                sys.modules[spec.name] = module
                spec.loader.exec_module(module)
                ctl = module.DirectoryController(str(root))
                ctl.init()
                return ctl

        fallback = _FallbackDirectoryController(str(root))
        fallback.init()
        return fallback

    def register_agent(self, agent_id: str) -> None:
        self._controller.register_agent(agent_id)

    def register_directory(self, path: str, allowed_agents: Optional[List[str]] = None) -> None:
        _ = allowed_agents
        self._controller.add_directory(path, shared=False)

    def acquire(self, agent_id: str, path: str, ttl: int) -> Any:
        lease = self._controller.acquire(agent_id, path, ttl_seconds=ttl)
        self.lease_events.append(
            {
                "event": "acquire",
                "agent_id": agent_id,
                "path": path,
                "token": getattr(lease, "token", ""),
                "backend": self.backend_name,
            }
        )
        return lease

    def heartbeat(self, token: str, ttl: int) -> Any:
        lease = self._controller.heartbeat(token, ttl_seconds=ttl)
        self.lease_events.append(
            {
                "event": "heartbeat",
                "token": token,
                "backend": self.backend_name,
            }
        )
        return lease

    def release(self, agent_id: str, path: str, token: Optional[str] = None) -> int:
        count = self._controller.release(agent_id, path, token=token)
        self.lease_events.append(
            {
                "event": "release",
                "agent_id": agent_id,
                "path": path,
                "token": token or "",
                "released": int(count),
                "backend": self.backend_name,
            }
        )
        return count


class LongRunRunner:
    def __init__(self, config: LongRunConfig) -> None:
        self.config = config
        self.events: List[dict] = []
        self.access_ledger: List[dict] = []
        self.lease_events: List[dict] = []
        self.violations: List[dict] = []
        self.covered_edges: set[Tuple[str, str]] = set()
        self.group_stats: Dict[str, dict] = {}
        self.gate_stats: Dict[str, int] = {"PASS": 0, "BLOCKED_UNCITED": 0, "BLOCKED_NEEDS_EVIDENCE": 0, "BLOCKED_REVIEW": 0}
        self.file_last_writer: Dict[str, str] = {}
        self.failed_code = EXIT_OK
        self.failed_reason = ""
        self._event_seq = 0
        self._rng = random.Random(config.seed)
        self._injected_isolation = False
        self._injected_deadlock = False
        self._injected_gate_failure = False
        self._injected_gate_payload = False
        self.actor_by_group: Dict[str, Dict[str, Actor]] = {}
        self.group_head_id: Dict[str, str] = {}

    def run(self) -> Tuple[int, dict]:
        self._validate_config()
        project_dir, manifest = self._ensure_project_bundle()
        project_id = str(manifest.get("project_id", slugify(self.config.project_id)))
        state_project_root = resolve_state_project_root(self.config.fabric_root, project_id)
        project_index_path = (
            self.config.project_index_path
            if self.config.project_index_path is not None
            else default_project_index_path(None)
        )
        self._prepare_output_dir(project_dir)
        dispatch_by_group, group_manifest_by_group = self._build_dispatch_plans(project_dir, manifest)
        self._init_group_stats(dispatch_by_group)

        workdirs = self._collect_workdirs(dispatch_by_group)
        lease_backend = LeaseBackend(self.config.fabric_root, self.lease_events)
        self._register_leases(lease_backend, workdirs)

        active_edges = [edge for edge in HANDOFF_EDGES if edge[0] in self.config.groups and edge[1] in self.config.groups]
        interaction_graph = {
            "task": self.config.task,
            "groups": self.config.groups,
            "edges": [{"from": a, "to": b} for a, b in active_edges],
            "coverage_target_percent": 100,
        }
        dump_yaml(self.output_dir / "interaction-graph.yaml", interaction_graph)

        cycles = max(1, self.config.duration_min // 5)
        self._record_event("run_start", {"cycles": cycles, "seed": self.config.seed})
        self._checkpoint_progress(
            project_id=project_id,
            state_project_root=state_project_root,
            project_index_path=project_index_path,
            stage="run-start",
            manifest=manifest,
        )

        try:
            for cycle in range(1, cycles + 1):
                if self.failed_code != EXIT_OK:
                    break
                self._record_event("cycle_start", {"cycle": cycle})

                for group_id in self.config.groups:
                    if self.failed_code != EXIT_OK:
                        break

                    group_manifest = group_manifest_by_group[group_id]
                    dispatch = dispatch_by_group[group_id]
                    head_actor = self.actor_by_group[group_id]["head"]

                    for phase in dispatch["phases"]:
                        if self.failed_code != EXIT_OK:
                            break
                        phase_id = int(phase["phase_id"])

                        before = self._snapshot_group_artifacts(project_dir)
                        phase_results: List[dict] = []

                        for task in phase["tasks"]:
                            if self.failed_code != EXIT_OK:
                                break
                            specialist_actor = self.actor_by_group[group_id][task["agent_id"]]
                            lease_agent_id = self._lease_agent_id(specialist_actor)
                            workdir = task["workdir"]

                            conflict_now = self._rng.random() < self.config.conflict_rate
                            deadlock_now = False
                            if self.config.inject_lease_deadlock and not self._injected_deadlock:
                                deadlock_now = True
                                conflict_now = True
                                self._injected_deadlock = True

                            lease_token = self._acquire_with_retry(
                                lease_backend=lease_backend,
                                lease_agent_id=lease_agent_id,
                                workdir=workdir,
                                conflict_now=conflict_now,
                                deadlock_now=deadlock_now,
                            )
                            if self.failed_code != EXIT_OK:
                                break

                            if lease_token:
                                lease_backend.heartbeat(lease_token, ttl=self.config.ttl)

                            synthetic = self._build_synthetic_output(
                                group_id=group_id,
                                specialist_id=specialist_actor.agent_id,
                                cycle=cycle,
                                phase_id=phase_id,
                            )
                            gate = gate_specialist_output(
                                synthetic,
                                citation_required=bool(group_manifest.get("quality_gates", {}).get("citation_required", True)),
                                web_available=not bool(synthetic.get("needs_web_evidence", False)),
                            )
                            gate_status = str(gate.get("status", "BLOCKED_REVIEW"))
                            self.gate_stats[gate_status] = self.gate_stats.get(gate_status, 0) + 1

                            artifact_path = (
                                project_dir
                                / "agent-groups"
                                / group_id
                                / "internal"
                                / specialist_actor.agent_id
                                / f"cycle-{cycle:03d}-phase-{phase_id:02d}.json"
                            )
                            self._safe_write(
                                actor=specialist_actor,
                                target=artifact_path,
                                content=stable_json(
                                    {
                                        "cycle": cycle,
                                        "phase": phase_id,
                                        "task": self.config.task,
                                        "group_id": group_id,
                                        "specialist_id": specialist_actor.agent_id,
                                        "gate": gate,
                                        "output": synthetic,
                                    }
                                )
                                + "\n",
                            )

                            phase_results.append(
                                {
                                    "specialist": specialist_actor.agent_id,
                                    "gate": gate,
                                    "internal_artifact": str(artifact_path.relative_to(project_dir)),
                                }
                            )
                            self.group_stats[group_id]["specialist_tasks"] += 1

                            if lease_token:
                                lease_backend.release(lease_agent_id, workdir, token=lease_token)

                        if self.failed_code != EXIT_OK:
                            break

                        blocked_results = [r for r in phase_results if r["gate"].get("status") != "PASS"]
                        exposed_payload = {
                            "cycle": cycle,
                            "phase": phase_id,
                            "group_id": group_id,
                            "task": self.config.task,
                            "accepted_results": [r for r in phase_results if r["gate"].get("status") == "PASS"],
                            "blocked_results": [],
                        }

                        if blocked_results:
                            if self.config.inject_gate_expose_failure and not self._injected_gate_failure:
                                self._injected_gate_failure = True
                                exposed_payload["blocked_results"] = blocked_results
                                self._fail(
                                    EXIT_QUALITY_GATE,
                                    "Blocked specialist output was published to exposed artifact",
                                    {
                                        "group_id": group_id,
                                        "cycle": cycle,
                                        "phase": phase_id,
                                        "blocked_count": len(blocked_results),
                                    },
                                )
                            else:
                                self._record_event(
                                    "blocked_results_filtered",
                                    {
                                        "group_id": group_id,
                                        "cycle": cycle,
                                        "phase": phase_id,
                                        "blocked_count": len(blocked_results),
                                    },
                                )

                        exposed_path = (
                            project_dir
                            / "agent-groups"
                            / group_id
                            / "exposed"
                            / f"cycle-{cycle:03d}-phase-{phase_id:02d}-summary.json"
                        )
                        self._safe_write(
                            actor=head_actor,
                            target=exposed_path,
                            content=stable_json(exposed_payload) + "\n",
                        )
                        latest_path = project_dir / "agent-groups" / group_id / "exposed" / "latest-summary.json"
                        self._safe_write(
                            actor=head_actor,
                            target=latest_path,
                            content=stable_json(exposed_payload) + "\n",
                        )
                        self.group_stats[group_id]["head_publications"] += 1

                        after = self._snapshot_group_artifacts(project_dir)
                        self._verify_ownership(before=before, after=after, cycle=cycle, phase_id=phase_id)
                        if self.failed_code != EXIT_OK:
                            break

                if self.failed_code != EXIT_OK:
                    break

                for producer, consumer in active_edges:
                    if self.failed_code != EXIT_OK:
                        break
                    consumer_head = self.actor_by_group[consumer]["head"]
                    source_path = project_dir / "agent-groups" / producer / "exposed" / "latest-summary.json"
                    self._safe_read(actor=consumer_head, target=source_path)
                    self.covered_edges.add((producer, consumer))
                    self._record_event(
                        "edge_consumed",
                        {
                            "cycle": cycle,
                            "from": producer,
                            "to": consumer,
                            "source": str(source_path.relative_to(project_dir)),
                        },
                    )

                if self.config.inject_isolation_violation and not self._injected_isolation and self.failed_code == EXIT_OK:
                    self._injected_isolation = True
                    producer, consumer = active_edges[0]
                    consumer_head = self.actor_by_group[consumer]["head"]
                    producer_specs = sorted(
                        [
                            spec_id
                            for spec_id, actor in self.actor_by_group[producer].items()
                            if actor.role == "specialist"
                        ]
                    )
                    bad_target = (
                        project_dir
                        / "agent-groups"
                        / producer
                        / "internal"
                        / producer_specs[0]
                        / "cycle-001-phase-01.json"
                    )
                    self._safe_read(actor=consumer_head, target=bad_target)

                self._record_event("cycle_end", {"cycle": cycle})
                self._checkpoint_progress(
                    project_id=project_id,
                    state_project_root=state_project_root,
                    project_index_path=project_index_path,
                    stage=f"cycle-{cycle:03d}",
                    manifest=manifest,
                )

        except _AbortRun:
            pass

        coverage = self._build_coverage(active_edges)
        dump_yaml(self.output_dir / "coverage.yaml", coverage)
        write_text(self.output_dir / "coverage.json", stable_json(coverage) + "\n")

        if self.failed_code == EXIT_OK and coverage["coverage_percent"] < 100.0:
            self._fail(
                EXIT_COVERAGE_INSUFFICIENT,
                "Interaction edge coverage below 100%",
                {"coverage_percent": coverage["coverage_percent"]},
            )

        self._record_event("run_end", {"exit_code": self.failed_code, "reason": self.failed_reason})

        self._write_artifacts(interaction_graph=interaction_graph)
        report = self._final_report(coverage=coverage, interaction_graph=interaction_graph, lease_backend=lease_backend)
        write_text(self.output_dir / "final-report.json", stable_json(report) + "\n")
        write_text(self.output_dir / "final-report.md", self._render_report_md(report) + "\n")
        self._checkpoint_progress(
            project_id=project_id,
            state_project_root=state_project_root,
            project_index_path=project_index_path,
            stage="run-end",
            manifest=manifest,
            coverage=coverage,
            report=report,
        )

        return self.failed_code, report

    def _validate_config(self) -> None:
        if self.config.run_mode != "local-sim":
            raise FabricError("only --run-mode local-sim is supported")
        if self.config.strict_isolation != "hard-fail":
            raise FabricError("only --strict-isolation hard-fail is supported")
        if self.config.duration_min < 1:
            raise FabricError("--duration-min must be >= 1")
        if self.config.max_retries < 1:
            raise FabricError("--max-retries must be >= 1")
        if not (0.0 <= self.config.conflict_rate <= 1.0):
            raise FabricError("--conflict-rate must be between 0 and 1")

    def _ensure_project_bundle(self) -> Tuple[Path, dict]:
        project_id = slugify(self.config.project_id)
        project_dir = self.config.fabric_root / "generated" / "projects" / project_id
        needs_generate = True
        manifest = None

        if project_dir.exists() and (project_dir / "manifest.yaml").exists():
            loaded_dir, loaded_manifest = load_project_manifest(self.config.fabric_root, project_id)
            selected = loaded_manifest.get("selected_groups", [])
            if isinstance(selected, list) and sorted(selected) == sorted(self.config.groups):
                needs_generate = False
                manifest = loaded_manifest
                project_dir = loaded_dir

        if needs_generate:
            cmd = [
                sys.executable,
                "-m",
                "agents_inc.cli.new_project",
                "--fabric-root",
                str(self.config.fabric_root),
                "--project-id",
                project_id,
                "--groups",
                ",".join(self.config.groups),
                "--visibility-mode",
                "group-only",
                "--audit-override",
                "--force",
            ]
            proc = subprocess.run(cmd, capture_output=True, text=True)
            if proc.returncode != 0:
                raise FabricError(
                    "failed to generate project bundle:\nstdout:\n{0}\nstderr:\n{1}".format(
                        proc.stdout.strip(), proc.stderr.strip()
                    )
                )
            project_dir, manifest = load_project_manifest(self.config.fabric_root, project_id)

        if not isinstance(manifest, dict):
            raise FabricError("project manifest could not be loaded")

        if self.config.audit:
            skills_target = self._audit_skill_target(project_dir)
            cmd = [
                sys.executable,
                "-m",
                "agents_inc.cli.install_skills",
                "--fabric-root",
                str(self.config.fabric_root),
                "--project-id",
                project_id,
                "--target",
                str(skills_target),
                "--sync",
                "--audit",
            ]
            proc = subprocess.run(cmd, capture_output=True, text=True)
            if proc.returncode != 0:
                raise FabricError(
                    "failed to install audit skills:\nstdout:\n{0}\nstderr:\n{1}".format(
                        proc.stdout.strip(), proc.stderr.strip()
                    )
                )

        return project_dir, manifest

    def _prepare_output_dir(self, project_dir: Path) -> None:
        if self.config.output_dir is not None:
            out = self.config.output_dir
        else:
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            out = project_dir / "long-run" / f"run-{stamp}-seed-{self.config.seed}"
        out.mkdir(parents=True, exist_ok=True)
        self.output_dir = out

        run_config = {
            "project_id": slugify(self.config.project_id),
            "task": self.config.task,
            "groups": self.config.groups,
            "duration_min": self.config.duration_min,
            "strict_isolation": self.config.strict_isolation,
            "run_mode": self.config.run_mode,
            "seed": self.config.seed,
            "audit_mode": self.config.audit,
            "conflict_rate": self.config.conflict_rate,
            "max_retries": self.config.max_retries,
            "retry_backoff_ms": self.config.retry_backoff_ms,
            "ttl": self.config.ttl,
            "injections": {
                "isolation_violation": self.config.inject_isolation_violation,
                "lease_deadlock": self.config.inject_lease_deadlock,
                "gate_expose_failure": self.config.inject_gate_expose_failure,
            },
            "created_at": now_iso(),
        }
        dump_yaml(self.output_dir / "run-config.yaml", run_config)

    def _build_dispatch_plans(self, project_dir: Path, manifest: dict) -> Tuple[Dict[str, dict], Dict[str, dict]]:
        groups_map = manifest.get("groups", {})
        if not isinstance(groups_map, dict):
            raise FabricError("project manifest missing groups map")

        dispatch_by_group: Dict[str, dict] = {}
        group_manifest_by_group: Dict[str, dict] = {}
        plan_dir = self.output_dir / "dispatch-plans"
        plan_dir.mkdir(parents=True, exist_ok=True)

        for group_id in self.config.groups:
            group_entry = groups_map.get(group_id)
            if not isinstance(group_entry, dict):
                raise FabricError(f"group '{group_id}' missing from project manifest")
            group_manifest_path = project_dir / str(group_entry.get("manifest_path", ""))
            group_manifest = load_yaml(group_manifest_path)
            if not isinstance(group_manifest, dict):
                raise FabricError(f"invalid group manifest: {group_manifest_path}")

            dispatch = build_dispatch_plan(
                manifest["project_id"],
                group_id,
                self.config.task,
                group_manifest,
            )

            dispatch_by_group[group_id] = dispatch
            group_manifest_by_group[group_id] = group_manifest

            self.group_head_id[group_id] = str(group_manifest.get("head", {}).get("agent_id", "head-controller"))
            actors = {"head": Actor(role="head", group_id=group_id, agent_id=self.group_head_id[group_id])}
            for specialist in group_manifest.get("specialists", []):
                if isinstance(specialist, dict) and specialist.get("agent_id"):
                    actors[str(specialist["agent_id"])] = Actor(
                        role="specialist",
                        group_id=group_id,
                        agent_id=str(specialist["agent_id"]),
                    )
            self.actor_by_group[group_id] = actors

            write_text(plan_dir / f"{group_id}.json", stable_json(dispatch) + "\n")

        return dispatch_by_group, group_manifest_by_group

    def _init_group_stats(self, dispatch_by_group: Dict[str, dict]) -> None:
        for group_id in dispatch_by_group:
            self.group_stats[group_id] = {
                "specialist_tasks": 0,
                "head_publications": 0,
                "phases": len(dispatch_by_group[group_id].get("phases", [])),
            }

    def _collect_workdirs(self, dispatch_by_group: Dict[str, dict]) -> List[Tuple[Actor, str]]:
        rows: List[Tuple[Actor, str]] = []
        for group_id, dispatch in dispatch_by_group.items():
            for phase in dispatch.get("phases", []):
                for task in phase.get("tasks", []):
                    actor = self.actor_by_group[group_id][task["agent_id"]]
                    rows.append((actor, str(task["workdir"])))
        return rows

    def _register_leases(self, lease_backend: LeaseBackend, workdirs: Sequence[Tuple[Actor, str]]) -> None:
        seen_agents = set()
        seen_dirs = set()
        lease_backend.register_agent("lease-blocker")

        for actor, workdir in workdirs:
            lease_agent = self._lease_agent_id(actor)
            if lease_agent not in seen_agents:
                lease_backend.register_agent(lease_agent)
                seen_agents.add(lease_agent)
            if workdir not in seen_dirs:
                lease_backend.register_directory(workdir)
                (self.config.fabric_root / workdir).mkdir(parents=True, exist_ok=True)
                seen_dirs.add(workdir)

    def _lease_agent_id(self, actor: Actor) -> str:
        return f"{actor.group_id}--{actor.agent_id}"

    def _acquire_with_retry(
        self,
        lease_backend: LeaseBackend,
        lease_agent_id: str,
        workdir: str,
        conflict_now: bool,
        deadlock_now: bool,
    ) -> Optional[str]:
        blocker_token: Optional[str] = None
        if conflict_now:
            try:
                blocker = lease_backend.acquire("lease-blocker", workdir, ttl=self.config.ttl)
                blocker_token = str(getattr(blocker, "token", ""))
                self._record_event(
                    "lease_conflict_injected",
                    {"workdir": workdir, "deadlock": bool(deadlock_now)},
                )
            except Exception as exc:  # noqa: BLE001
                self._record_event("lease_conflict_injection_failed", {"workdir": workdir, "error": str(exc)})

        for attempt in range(1, self.config.max_retries + 1):
            try:
                lease = lease_backend.acquire(lease_agent_id, workdir, ttl=self.config.ttl)
                token = str(getattr(lease, "token", ""))
                self._record_event(
                    "lease_acquired",
                    {"workdir": workdir, "attempt": attempt, "agent": lease_agent_id},
                )
                return token
            except Exception as exc:  # noqa: BLE001
                self._record_event(
                    "lease_conflict",
                    {
                        "workdir": workdir,
                        "attempt": attempt,
                        "agent": lease_agent_id,
                        "error": str(exc),
                    },
                )
                if blocker_token and not deadlock_now and attempt == 1:
                    lease_backend.release("lease-blocker", workdir, token=blocker_token)
                    blocker_token = None
                if attempt == self.config.max_retries:
                    if blocker_token:
                        lease_backend.release("lease-blocker", workdir, token=blocker_token)
                    self._fail(
                        EXIT_LEASE_UNRESOLVED,
                        "Lease contention unresolved",
                        {"workdir": workdir, "agent": lease_agent_id, "attempts": self.config.max_retries},
                    )
                    return None
                if self.config.retry_backoff_ms > 0:
                    time.sleep(float(self.config.retry_backoff_ms) / 1000.0)

        return None

    def _build_synthetic_output(self, group_id: str, specialist_id: str, cycle: int, phase_id: int) -> dict:
        claims = [
            {
                "claim": f"{group_id}/{specialist_id} synthesized claim for cycle {cycle} phase {phase_id}",
                "citation": f"local:references/{specialist_id}-core.md",
            }
        ]
        output = {
            "assumptions": [
                "Synthetic simulation run",
                "Deterministic local mode",
            ],
            "claims_with_citations": claims,
            "repro_steps": [
                f"Acquire lease for {group_id}/{specialist_id}",
                "Write internal artifact",
                "Return gated output",
            ],
            "artifact_paths": [
                f"agent-groups/{group_id}/internal/{specialist_id}/cycle-{cycle:03d}-phase-{phase_id:02d}.json"
            ],
            "confidence": "medium",
            "unresolved_assumptions": [],
        }

        if self.config.inject_gate_expose_failure and not self._injected_gate_payload:
            self._injected_gate_payload = True
            output["claims_with_citations"] = [{"claim": "intentionally uncited claim"}]

        return output

    def _artifact_rel(self, project_dir: Path, target: Path) -> str:
        return target.relative_to(project_dir).as_posix()

    def _actor_tag(self, actor: Actor) -> str:
        return f"{actor.role}:{actor.group_id}:{actor.agent_id}"

    def _check_access(self, actor: Actor, target: Path, op: str, project_dir: Path) -> Tuple[bool, str]:
        try:
            rel = target.relative_to(project_dir)
        except Exception:
            return False, "target outside project root"

        parts = rel.parts
        if len(parts) < 3 or parts[0] != "agent-groups":
            return False, "target outside group artifact scope"

        target_group = str(parts[1])
        section = str(parts[2])

        if section not in {"internal", "exposed"}:
            return False, "target section is not internal/exposed"

        if actor.role == "specialist":
            if op == "write":
                if target_group == actor.group_id and section == "internal" and len(parts) >= 4 and parts[3] == actor.agent_id:
                    return True, "ok"
                return False, "specialist write must stay in own internal subtree"

            if op == "read":
                if target_group == actor.group_id and section == "internal" and len(parts) >= 4 and parts[3] == actor.agent_id:
                    return True, "ok"
                if target_group == actor.group_id and section == "exposed":
                    return True, "ok"
                if target_group != actor.group_id and section == "exposed":
                    return True, "ok"
                return False, "specialist cross-group internal read denied"

        if actor.role == "head":
            if op == "write":
                if target_group == actor.group_id and section == "exposed":
                    return True, "ok"
                return False, "head write must stay in own exposed subtree"

            if op == "read":
                if target_group == actor.group_id:
                    return True, "ok"
                if target_group != actor.group_id and section == "exposed":
                    return True, "ok"
                return False, "head cross-group internal read denied"

        return False, "unknown actor role"

    def _safe_read(self, actor: Actor, target: Path) -> str:
        project_dir = self.config.fabric_root / "generated" / "projects" / slugify(self.config.project_id)
        allowed, reason = self._check_access(actor, target, "read", project_dir)
        self._record_access(actor=actor, op="read", target=target, allowed=allowed, reason=reason, project_dir=project_dir)
        if not allowed:
            self._fail(
                EXIT_ISOLATION_VIOLATION,
                "Isolation policy violation on read",
                {
                    "actor": self._actor_tag(actor),
                    "target": self._artifact_rel(project_dir, target),
                    "reason": reason,
                },
            )
            raise _AbortRun()

        if not target.exists():
            return ""
        return target.read_text(encoding="utf-8")

    def _safe_write(self, actor: Actor, target: Path, content: str) -> None:
        project_dir = self.config.fabric_root / "generated" / "projects" / slugify(self.config.project_id)
        allowed, reason = self._check_access(actor, target, "write", project_dir)
        self._record_access(actor=actor, op="write", target=target, allowed=allowed, reason=reason, project_dir=project_dir)
        if not allowed:
            self._fail(
                EXIT_ISOLATION_VIOLATION,
                "Isolation policy violation on write",
                {
                    "actor": self._actor_tag(actor),
                    "target": self._artifact_rel(project_dir, target),
                    "reason": reason,
                },
            )
            raise _AbortRun()

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        rel = self._artifact_rel(project_dir, target)
        self.file_last_writer[rel] = self._actor_tag(actor)
        self._record_event(
            "artifact_write",
            {
                "actor": self._actor_tag(actor),
                "target": rel,
            },
        )

    def _record_access(self, actor: Actor, op: str, target: Path, allowed: bool, reason: str, project_dir: Path) -> None:
        self.access_ledger.append(
            {
                "seq": len(self.access_ledger) + 1,
                "actor": self._actor_tag(actor),
                "op": op,
                "target": self._artifact_rel(project_dir, target),
                "allowed": bool(allowed),
                "reason": reason,
            }
        )

    def _record_event(self, event: str, payload: dict) -> None:
        self._event_seq += 1
        row = {"seq": self._event_seq, "event": event}
        row.update(payload)
        self.events.append(row)

    def _fail(self, code: int, reason: str, detail: dict) -> None:
        if self.failed_code != EXIT_OK:
            return
        self.failed_code = code
        self.failed_reason = reason
        violation = {"code": code, "reason": reason, "detail": detail}
        self.violations.append(violation)
        self._record_event("failure", violation)

    def _snapshot_group_artifacts(self, project_dir: Path) -> Dict[str, str]:
        artifact_root = project_dir / "agent-groups"
        hashes: Dict[str, str] = {}
        if not artifact_root.exists():
            return hashes

        for path in sorted(artifact_root.rglob("*")):
            if not path.is_file():
                continue
            rel = path.relative_to(project_dir).as_posix()
            if "/internal/" not in rel and "/exposed/" not in rel:
                continue
            hashes[rel] = _sha256_path(path)
        return hashes

    def _expected_owner(self, rel_path: str) -> Optional[str]:
        parts = Path(rel_path).parts
        if len(parts) < 4:
            return None
        if parts[0] != "agent-groups":
            return None
        group_id = str(parts[1])
        section = str(parts[2])
        if section == "internal" and len(parts) >= 4:
            specialist = str(parts[3])
            return f"specialist:{group_id}:{specialist}"
        if section == "exposed":
            head_id = self.group_head_id.get(group_id, "head-controller")
            return f"head:{group_id}:{head_id}"
        return None

    def _verify_ownership(self, before: Dict[str, str], after: Dict[str, str], cycle: int, phase_id: int) -> None:
        changed = set(before.keys()).union(set(after.keys()))
        changed = {p for p in changed if before.get(p) != after.get(p)}
        for rel in sorted(changed):
            expected_owner = self._expected_owner(rel)
            if expected_owner is None:
                continue
            actual_owner = self.file_last_writer.get(rel)
            if actual_owner != expected_owner:
                self._fail(
                    EXIT_ISOLATION_VIOLATION,
                    "Owner attribution mismatch",
                    {
                        "cycle": cycle,
                        "phase": phase_id,
                        "path": rel,
                        "expected_owner": expected_owner,
                        "actual_owner": actual_owner or "<unknown>",
                    },
                )
                raise _AbortRun()

    def _build_coverage(self, active_edges: List[Tuple[str, str]]) -> dict:
        total = len(active_edges)
        covered = len(self.covered_edges)
        percent = 100.0 if total == 0 else round((covered / total) * 100.0, 3)
        return {
            "total_edges": total,
            "covered_edges": covered,
            "coverage_percent": percent,
            "defined_edges": [{"from": a, "to": b} for a, b in active_edges],
            "covered_edge_list": [{"from": a, "to": b} for a, b in sorted(self.covered_edges)],
        }

    def _write_ndjson(self, path: Path, rows: Iterable[dict]) -> None:
        lines = [json.dumps(row, sort_keys=True) for row in rows]
        write_text(path, "\n".join(lines) + ("\n" if lines else ""))

    def _write_artifacts(self, interaction_graph: dict) -> None:
        write_text(self.output_dir / "interaction-graph.json", stable_json(interaction_graph) + "\n")
        self._write_ndjson(self.output_dir / "events.ndjson", self.events)
        self._write_ndjson(self.output_dir / "access-ledger.ndjson", self.access_ledger)
        self._write_ndjson(self.output_dir / "lease-events.ndjson", self.lease_events)
        write_text(self.output_dir / "violations.json", stable_json({"violations": self.violations}) + "\n")

    def _audit_skill_target(self, project_dir: Path) -> Path:
        return project_dir / "long-run" / "audit-skills"

    def _final_report(self, coverage: dict, interaction_graph: dict, lease_backend: LeaseBackend) -> dict:
        project_dir = self.config.fabric_root / "generated" / "projects" / slugify(self.config.project_id)
        audit_skill_target = self._audit_skill_target(project_dir)
        installed_skill_count = 0
        installed_specialist_skill_count = 0
        if audit_skill_target.exists():
            for skill_dir in audit_skill_target.iterdir():
                marker = skill_dir / ".fabric-managed.json"
                if marker.exists():
                    installed_skill_count += 1
                    try:
                        meta = json.loads(marker.read_text(encoding="utf-8"))
                        if meta.get("role") == "specialist":
                            installed_specialist_skill_count += 1
                    except Exception:
                        pass

        report = {
            "project_id": slugify(self.config.project_id),
            "task": self.config.task,
            "run_mode": self.config.run_mode,
            "strict_isolation": self.config.strict_isolation,
            "seed": self.config.seed,
            "duration_min": self.config.duration_min,
            "audit_mode": self.config.audit,
            "lease_backend": lease_backend.backend_name,
            "groups": self.config.groups,
            "group_completion_matrix": self.group_stats,
            "interaction": {
                "edges_defined": len(interaction_graph["edges"]),
                "edges_covered": len(self.covered_edges),
                "coverage_percent": coverage["coverage_percent"],
            },
            "isolation": {
                "violation_count": len([v for v in self.violations if v.get("code") == EXIT_ISOLATION_VIOLATION]),
                "hard_fail": True,
            },
            "lease": {
                "events": len(self.lease_events),
                "conflicts": len([e for e in self.events if e.get("event") == "lease_conflict"]),
                "retry_attempts": len([e for e in self.events if e.get("event") == "lease_conflict"]),
            },
            "quality_gates": {
                "stats": self.gate_stats,
                "blocked_total": int(sum(v for k, v in self.gate_stats.items() if k != "PASS")),
            },
            "top_failed_invariants": self.violations[:5],
            "exit_code": self.failed_code,
            "exit_reason": self.failed_reason,
            "output_dir": str(self.output_dir),
            "installed_skill_count": installed_skill_count,
            "installed_specialist_skill_count": installed_specialist_skill_count,
            "reproduction_command": self._repro_command(),
            "created_at": now_iso(),
        }
        return report

    def _repro_command(self) -> str:
        parts = [
            "agents-inc long-run",
            f"--fabric-root {self.config.fabric_root}",
            f"--project-id {slugify(self.config.project_id)}",
            f"--task \"{self.config.task}\"",
            f"--groups {','.join(self.config.groups)}",
            f"--duration-min {self.config.duration_min}",
            f"--strict-isolation {self.config.strict_isolation}",
            f"--run-mode {self.config.run_mode}",
            f"--seed {self.config.seed}",
            f"--conflict-rate {self.config.conflict_rate}",
        ]
        if self.config.audit:
            parts.append("--audit")
        return " ".join(parts)

    def _render_report_md(self, report: dict) -> str:
        lines = [
            "# Long-Run Validation Report",
            "",
            f"- Project: `{report['project_id']}`",
            f"- Task: {report['task']}",
            f"- Exit: `{report['exit_code']}` ({report['exit_reason'] or 'pass'})",
            f"- Seed: `{report['seed']}`",
            f"- Duration (sim): `{report['duration_min']} min`",
            f"- Run mode: `{report['run_mode']}`",
            f"- Strict isolation: `{report['strict_isolation']}`",
            f"- Lease backend: `{report['lease_backend']}`",
            f"- Audit mode: `{report['audit_mode']}`",
            "",
            "## Group Completion Matrix",
            "| Group | Specialist Tasks | Head Publications | Phases |",
            "|---|---:|---:|---:|",
        ]
        for group_id in sorted(report["group_completion_matrix"].keys()):
            stat = report["group_completion_matrix"][group_id]
            lines.append(
                f"| `{group_id}` | {stat['specialist_tasks']} | {stat['head_publications']} | {stat['phases']} |"
            )

        lines.extend(
            [
                "",
                "## Interaction Coverage",
                f"- Coverage: `{report['interaction']['coverage_percent']}%`",
                f"- Edges covered: `{report['interaction']['edges_covered']}/{report['interaction']['edges_defined']}`",
                "",
                "## Isolation",
                f"- Violations: `{report['isolation']['violation_count']}`",
                "",
                "## Lease Stats",
                f"- Events: `{report['lease']['events']}`",
                f"- Conflicts: `{report['lease']['conflicts']}`",
                f"- Retry attempts: `{report['lease']['retry_attempts']}`",
                "",
                "## Quality Gates",
                f"- PASS: `{report['quality_gates']['stats'].get('PASS', 0)}`",
                f"- BLOCKED_UNCITED: `{report['quality_gates']['stats'].get('BLOCKED_UNCITED', 0)}`",
                f"- BLOCKED_NEEDS_EVIDENCE: `{report['quality_gates']['stats'].get('BLOCKED_NEEDS_EVIDENCE', 0)}`",
                f"- BLOCKED_REVIEW: `{report['quality_gates']['stats'].get('BLOCKED_REVIEW', 0)}`",
                "",
                "## Reproduction",
                "```bash",
                report["reproduction_command"],
                "```",
            ]
        )

        if report["top_failed_invariants"]:
            lines.extend(["", "## Top Failed Invariants"])
            for item in report["top_failed_invariants"]:
                lines.append(f"- `{item.get('reason', 'unknown')}`: `{stable_json(item.get('detail', {}))}`")

        return "\n".join(lines)

    def _checkpoint_progress(
        self,
        *,
        project_id: str,
        state_project_root: Path,
        project_index_path: Path,
        stage: str,
        manifest: dict,
        coverage: Optional[dict] = None,
        report: Optional[dict] = None,
    ) -> None:
        try:
            selected_groups = manifest.get("selected_groups", self.config.groups)
            if not isinstance(selected_groups, list):
                selected_groups = self.config.groups
            selected_groups = [str(group_id) for group_id in selected_groups]

            primary_group = selected_groups[0] if selected_groups else ""
            router_call = ""
            if primary_group:
                router_call = (
                    f"Use $research-router for project {project_id} group {primary_group}: {self.config.task}."
                )

            latest_artifacts = {
                "kickoff": str(state_project_root / "kickoff.md"),
                "router_call": str(state_project_root / "router-call.txt"),
                "project_manifest": str(state_project_root / "project-manifest.yaml"),
                "long_run_output_dir": str(self.output_dir),
                "final_report_json": str(self.output_dir / "final-report.json"),
                "final_report_md": str(self.output_dir / "final-report.md"),
            }

            quality_summary = {
                "stage": stage,
                "stats": self.gate_stats,
                "blocked_total": int(sum(v for k, v in self.gate_stats.items() if k != "PASS")),
            }
            isolation_summary = {
                "stage": stage,
                "violation_count": len([v for v in self.violations if v.get("code") == EXIT_ISOLATION_VIOLATION]),
                "hard_fail": True,
            }
            if coverage is not None:
                isolation_summary["coverage_percent"] = float(coverage.get("coverage_percent", 0.0))

            pending_actions = [
                "Inspect long-run final report for coverage, quality, and isolation outcomes.",
                "If failures exist, rerun with injections disabled and compare checkpoint timelines.",
            ]
            if report is not None and int(report.get("exit_code", 0)) == 0:
                pending_actions = [
                    "Proceed with router-guided group execution using exposed group summaries.",
                    "Run targeted dispatch dry-runs for next specialist-heavy objectives.",
                ]

            payload = {
                "schema_version": "1.0",
                "project_id": project_id,
                "project_root": str(state_project_root),
                "fabric_root": str(self.config.fabric_root),
                "task": self.config.task,
                "constraints": {
                    "run_mode": self.config.run_mode,
                    "duration_min": self.config.duration_min,
                    "strict_isolation": self.config.strict_isolation,
                    "seed": self.config.seed,
                    "stage": stage,
                },
                "selected_groups": selected_groups,
                "primary_group": primary_group,
                "group_order_recommendation": selected_groups,
                "router_call": router_call,
                "latest_artifacts": latest_artifacts,
                "quality_summary": quality_summary,
                "isolation_summary": isolation_summary,
                "pending_actions": pending_actions,
            }
            if report is not None:
                payload["long_run_summary"] = {
                    "exit_code": report.get("exit_code"),
                    "exit_reason": report.get("exit_reason"),
                    "coverage_percent": report.get("interaction", {}).get("coverage_percent"),
                    "isolation_violations": report.get("isolation", {}).get("violation_count"),
                }

            checkpoint_meta = write_checkpoint(
                project_root=state_project_root,
                project_index_path=project_index_path,
                payload=payload,
            )
            compact_session(
                project_root=state_project_root,
                payload={
                    **payload,
                    "latest_checkpoint_id": str(checkpoint_meta["checkpoint_id"]),
                    "latest_checkpoint_path": str(checkpoint_meta["checkpoint_path"]),
                },
                selected_groups=selected_groups,
            )
        except Exception as exc:  # noqa: BLE001
            self._record_event(
                "checkpoint_write_failed",
                {
                    "stage": stage,
                    "error": str(exc),
                },
            )


def _sha256_path(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def evaluate_access(
    actor_role: str,
    actor_group: str,
    actor_agent: str,
    op: str,
    target_rel: str,
) -> Tuple[bool, str]:
    actor = Actor(role=actor_role, group_id=actor_group, agent_id=actor_agent)
    target = Path("/tmp/project") / target_rel
    dummy_runner = LongRunRunner(
        LongRunConfig(
            fabric_root=Path("/tmp"),
            project_id="dummy",
            task=CANONICAL_TASK,
            groups=[actor_group],
            duration_min=1,
            strict_isolation="hard-fail",
            run_mode="local-sim",
            seed=1,
            output_dir=None,
            project_index_path=None,
            audit=False,
            conflict_rate=0.0,
            max_retries=1,
            retry_backoff_ms=0,
            ttl=60,
            inject_isolation_violation=False,
            inject_lease_deadlock=False,
            inject_gate_expose_failure=False,
        )
    )
    return dummy_runner._check_access(actor, target, op, Path("/tmp/project"))


def detect_owner_mismatches(
    changed_paths: Sequence[str],
    expected_owner_by_path: Dict[str, str],
    actual_owner_by_path: Dict[str, str],
) -> List[dict]:
    mismatches: List[dict] = []
    for path in sorted(changed_paths):
        expected = expected_owner_by_path.get(path)
        actual = actual_owner_by_path.get(path)
        if expected is None:
            continue
        if expected != actual:
            mismatches.append(
                {
                    "path": path,
                    "expected_owner": expected,
                    "actual_owner": actual,
                }
            )
    return mismatches


def run_long_validation(config: LongRunConfig) -> Tuple[int, dict]:
    runner = LongRunRunner(config)
    return runner.run()
