from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict

from agents_inc.core.eval_harness import score_session
from agents_inc.core.fabric_lib import (
    FabricError,
    load_project_manifest,
    load_yaml,
    resolve_fabric_root,
    slugify,
)
from agents_inc.core.session_state import resolve_state_project_root


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Score specialist quality for a completed turn")
    parser.add_argument("--fabric-root", default=None, help="path to fabric root")
    parser.add_argument("--project-id", required=True)
    parser.add_argument(
        "--turn-id",
        default=None,
        help="turn id under <project-root>/.agents-inc/turns (defaults to latest)",
    )
    parser.add_argument("--turn-dir", default=None, help="explicit turn directory path")
    parser.add_argument(
        "--source",
        choices=["turn-snapshot", "project-live"],
        default="turn-snapshot",
        help="artifact source for scoring (default: turn-snapshot)",
    )
    parser.add_argument("--json", action="store_true", help="emit full score report as JSON")
    return parser.parse_args()


def _group_manifests(project_dir: Path, manifest: dict) -> Dict[str, dict]:
    groups = manifest.get("groups")
    if not isinstance(groups, dict):
        raise FabricError("project manifest missing groups map")
    out: Dict[str, dict] = {}
    for group_id, payload in groups.items():
        if not isinstance(payload, dict):
            continue
        rel = str(payload.get("manifest_path") or "").strip()
        if not rel:
            continue
        group_manifest = load_yaml(project_dir / rel)
        if isinstance(group_manifest, dict):
            out[str(group_id)] = group_manifest
    return out


def _resolve_turn_dir(*, project_root: Path, turn_id: str | None, turn_dir: str | None) -> Path:
    if turn_dir:
        target = Path(turn_dir).expanduser().resolve()
        if not target.exists():
            raise FabricError(f"turn directory not found: {target}")
        return target
    turns_root = project_root / ".agents-inc" / "turns"
    if not turns_root.exists():
        raise FabricError(f"turns directory not found: {turns_root}")
    if turn_id:
        target = turns_root / str(turn_id).strip()
        if not target.exists():
            raise FabricError(f"turn id not found: {target}")
        return target
    candidates = sorted([path for path in turns_root.iterdir() if path.is_dir()])
    if not candidates:
        raise FabricError(f"no turns found under: {turns_root}")
    return candidates[-1]


def main() -> int:
    args = parse_args()
    try:
        project_id = slugify(str(args.project_id))
        fabric_root = resolve_fabric_root(args.fabric_root)
        project_dir, manifest = load_project_manifest(fabric_root, project_id)
        project_root = resolve_state_project_root(fabric_root, project_id)
        turn_dir = _resolve_turn_dir(
            project_root=project_root, turn_id=args.turn_id, turn_dir=args.turn_dir
        )
        report = score_session(
            turn_dir=turn_dir,
            project_dir=project_dir,
            group_manifests=_group_manifests(project_dir, manifest),
            source=str(args.source or "turn-snapshot"),
        )
        if args.json:
            print(json.dumps(report, indent=2, sort_keys=True))
        else:
            print(f"project_id: {project_id}")
            print(f"turn_dir: {turn_dir}")
            print(f"overall_score: {report.get('overall_score', 0)}")
            print(f"source: {report.get('source', 'turn-snapshot')}")
            print(f"report_path: {turn_dir / 'eval-scores.json'}")
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
