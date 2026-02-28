# Session Intake Guide

Use this guide in a fresh Codex session after bootstrap.

## Intake Questions
1. What task do you want to start?
2. What is your target timeline?
3. Do you require CPU-only or CUDA GPU resources?
4. Will remote cluster execution over SSH be required?
5. What output format is needed (report, code, benchmark, slides)?

## Outcome
The onboarding wizard should create:
- A long-term project root under `~/codex-projects/<project-id>`
- A project-local fabric bundle
- Group recommendations and invocation order
- Router call text for immediate execution
- Long-run all-group validation command (`long-run-command.sh`)

## Default Behavior
- Visibility mode: group-only
- Specialist artifacts: internal unless audit mode is enabled
- Router invocation:
  `Use $research-router for project <project-id> group <group-id>: <objective>.`
- Long-run validator:
  `agents-inc-long-run-test --project-id <project-id> --groups all --duration-min 75`
