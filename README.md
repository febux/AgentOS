# AgentOS (working name: agentos)

A technical core for autonomous building by AI agents: the Hermes kanban board,
headless workers, OpenCode as the executor, machine-enforced artifact verification.

The idea is taken from two projects verified hands-on in 2026-10:

- **Technical core** — from the agentos.guide guide (OpenCode × Hermes kanban):
  the Hermes orchestrator doesn't write code itself, it runs OpenCode on tickets
  from the board. The scheme works (all `hermes kanban` commands verified
  locally); the marketing around it is garbage.
- **Enforcement instead of prompts** — from github.com/KbWen/agentic-os:
  rules in AGENTS.md are a request; gates in scripts and hooks are a fact.
  A worker can lie "done" — the verification script cannot.

What we do NOT take: the first project's subscription funnel, or the third
project's governance-heavy program (worklog classification, ADR process, a
40-state state machine). We need a core, not a second AGENTS.md about rules
for AGENTS.md.

## What it does

```
you → ticket on the board → hermes kanban dispatch
                            │
                    headless worker (opencode profile)
                            │
                    opencode run "<spec from the ticket>"
                            │
                    artifact in workspace
                            │
              verify.sh / verify.py  ←── MACHINE VERIFICATION
                    │pass              │fail
                complete            block + log to the ticket
```

The orchestrator never writes code. An artifact without evidence doesn't count
as done. Both rules are enforced by scripts, not prompts.

## Composition (minimal)

| File | Role |
|---|---|
| `~/.hermes/profiles/opencode/config.yaml` | headless profile: gateway off, platforms {}, terminal local |
| `~/.hermes/profiles/opencode/AGENT.md` | standing instruction: only via `opencode run`, then verify |
| `verify.py` | artifact verifier: size, structure, secrets, build |
| `hooks/pre-commit` | scan_credentials — secrets never reach history (from agentic-os, simplified) |
| `docs/ops.md` | cheat sheet: board commands, known traps (the 3 traps from the guide — they're real) |

Zero new runtime code: the whole "OS" is Hermes + OpenCode configs, one
verify script and one hook. Everything else is already written by Nous Research
and openai/codex... that is, sst/opencode.

## Status

Phase 1 done (2026-10-18): the full board→worker→opencode→verify→complete cycle
runs without manual intervention; pre-commit blocks a fake AKIA. A nuance found
during implementation: the standing order lives in workspace/AGENTS.md (Hermes
looks for AGENTS.md in cwd, not in the profile home); the model for opencode:
`zai-coding-plan/glm-5.2`. Next — PLAN.md phase 2.

Phase 2 done (2026-10-18): retry loop in workspace/AGENTS.md (one retry with
the verify error text in the prompt, second Failed → block), report.sh
(stats + done/blocked lists). Acceptance: greet.py (py gate) done + Passed;
an unsatisfiable spec (a 5-byte html) → blocked with a sensible reason, not
done with an empty file. Verified: the worker honestly resolves resolvable
contradictions (html without `</html>` is valid HTML5, since closing tags are
optional) and blocks unresolvable ones.

Phase 3 (2026-10-18, driven by actual pain): install.sh (verify gate in any
repo), `model: <id>` in the ticket body → the worker passes it to opencode run
(list: `opencode models`), auto-dispatcher = gateway systemd-service
(`hermes kanban daemon` deprecated). A git gate is deliberately not built:
review and commit are yours; we'll revisit when it hurts.

Phase 4 done (2026-10-18, hardening based on the analysis of rivet-dev/agentos
and SapienXai/AgentOS, full breakdown in docs/upstream-ideas.md): honest verify
verdict {pass|fail|skipped} + retryable (NORETRY → block without retry),
path-jail for artifacts, extended secret scanner (query-param, KEY=VALUE,
github_pat_, the xox- family), write-once chmod 0o444 after Passed, `--machine`
ERR_/OK_ output format; workspace/run.sh — killpg timeout for opencode via the
`timeout:` flag in the ticket; workspace/gate.sh — human gate `gate:` with
timeout=deny and confirmation by an APPROVED comment. Also fixed a report.sh
bug along the way (tail -n +2 was eating single-row lists). Acceptance run:
selftest (new fixtures), timeout process-tree kill, both gate paths, machine
output.

Integrations (2026-10-18): `mcp/server.py` — a stdio MCP server (stdlib-only,
7 tools over `hermes kanban`) for external agents — Claude Code, Cursor,
Codex, OMP; client configs in docs/ops.md. Inside Hermes — the
`kanban-dispatch` skill: "assign a task to opencode" in natural language.
