from __future__ import annotations

import argparse
import re
import shutil
import subprocess
from pathlib import Path

from agents_inc.cli.init_session import run_resume_flow


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Resume agents-inc project orchestrator session")
    parser.add_argument("project_id", help="project id to resume")
    parser.add_argument("--checkpoint", default="latest", help="checkpoint id or 'latest'")
    parser.add_argument(
        "--resume-mode",
        default="auto",
        choices=["auto", "compact", "rehydrate"],
        help="resume source preference",
    )
    parser.add_argument("--project-index", default=None, help="global project index path")
    parser.add_argument("--task", default=None, help="optional objective override")
    parser.add_argument(
        "--no-launch", action="store_true", help="prepare resume artifacts without opening codex"
    )
    return parser.parse_args()


def _build_resume_prompt(summary: dict) -> str:
    project_id = str(summary.get("project_id", ""))
    session_code = str(summary.get("session_code", ""))
    router_call = str(summary.get("router_call", ""))
    groups = summary.get("selected_groups", [])
    if not isinstance(groups, list):
        groups = []
    groups_text = ", ".join(str(group_id) for group_id in groups)
    return (
        "Resume orchestrator for project "
        f"{project_id}. Session code: {session_code}. "
        f"Active groups: {groups_text}. "
        f"Start from router call: {router_call} "
        "Keep group artifacts isolated by project and only exchange through exposed/ paths."
    )


def _persist_resume_prompt(project_root: str, prompt: str) -> Path:
    state_dir = Path(project_root).expanduser().resolve() / ".agents-inc" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    prompt_path = state_dir / "resume-prompt.md"
    prompt_path.write_text(prompt.strip() + "\n", encoding="utf-8")
    return prompt_path


def _sanitize_prompt(prompt: str, max_len: int = 1200) -> str:
    single = re.sub(r"\s+", " ", prompt).strip()
    if len(single) <= max_len:
        return single
    return single[: max_len - 3].rstrip() + "..."


def _launch_codex(project_root: str, prompt: str) -> int:
    codex_bin = shutil.which("codex")
    if not codex_bin:
        print(
            "warning: 'codex' command not found on PATH. Resume artifacts were generated, but auto-launch was skipped."
        )
        return 0
    cmd = [codex_bin, "-C", project_root, prompt]
    print(f"launching: {' '.join(cmd[:3])} <prompt>")
    proc = subprocess.run(cmd)
    return int(proc.returncode)


def main() -> int:
    args = parse_args()
    try:
        resume_args = argparse.Namespace(
            mode="resume",
            resume_project_id=args.project_id,
            project_id=args.project_id,
            resume_checkpoint=args.checkpoint,
            resume_mode=args.resume_mode,
            project_index=args.project_index,
            task=args.task,
            non_interactive=True,
        )
        summary = run_resume_flow(
            resume_args, requested_project_id=args.project_id, emit_output=True
        )
        if args.no_launch:
            return 0
        project_root = str(summary.get("project_root", ""))
        prompt = _build_resume_prompt(summary)
        prompt_path = _persist_resume_prompt(project_root, prompt)
        prompt = _sanitize_prompt(prompt)
        print(f"resume prompt saved: {prompt_path}")
        return _launch_codex(project_root, prompt)
    except Exception as exc:  # noqa: BLE001
        print(f"error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
