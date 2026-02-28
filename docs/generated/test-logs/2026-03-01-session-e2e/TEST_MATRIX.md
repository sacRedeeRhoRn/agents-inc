# agents-inc Session E2E Test Matrix

Date: 2026-03-01 (Asia/Seoul)
Workspace: /Users/moon.s.june/Documents/Playground/agent_group_fabric

## Cases
1. Local package sanity (`pip install -e .`, CLI `--help`, validate, unit tests)
2. `agents-inc-init-session` non-interactive flow (materials reproduction)
3. `agents-inc-init-session` interactive flow (piped answers)
4. Skill install visibility check (default head-only vs `--audit` specialist exposure)
5. Dispatch dry-run metadata check (`transport/scheduler/hardware/session_mode/lock_plan`)
6. README pinned bootstrap command in clean virtualenv (simulated new session)
7. Bootstrap wizard auto-start with piped input and artifact generation

## Success Criteria
- All cases complete without error, or issues are patched and retested until pass.
- Logs captured per case in this folder.
