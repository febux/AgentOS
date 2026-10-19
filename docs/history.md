# History — phases and acceptance runs

Moved out of README.md on 2026-10-19. The plan behind these phases: PLAN.md.

## Phase 1 done (2026-10-18)

The full board→worker→opencode→verify→complete cycle runs without manual
intervention; pre-commit blocks a fake AKIA. A nuance found during
implementation: the standing order lives in workspace/AGENTS.md (Hermes looks
for AGENTS.md in cwd, not in the profile home); the model for opencode:
`zai-coding-plan/glm-5.2`. Next — PLAN.md phase 2.

## Phase 2 done (2026-10-18)

Retry loop in workspace/AGENTS.md (one retry with the verify error text in the
prompt, second Failed → block), report.sh (stats + done/blocked lists).
Acceptance: greet.py (py gate) done + Passed; an unsatisfiable spec (a 5-byte
html) → blocked with a sensible reason, not done with an empty file. Verified:
the worker honestly resolves resolvable contradictions (html without `</html>`
is valid HTML5, since closing tags are optional) and blocks unresolvable ones.

## Phase 3 (2026-10-18, driven by actual pain)

install.sh (verify gate in any repo), `model: <id>` in the ticket body → the
worker passes it to opencode run (list: `opencode models`), auto-dispatcher =
gateway systemd-service (`hermes kanban daemon` deprecated). A git gate is
deliberately not built: review and commit are yours; we'll revisit when it
hurts.

## Phase 4 done (2026-10-18, hardening)

Based on the analysis of rivet-dev/agentos and SapienXai/AgentOS, full
breakdown in docs/upstream-ideas.md. What landed: honest verify verdict
{pass|fail|skipped} + retryable (NORETRY → block without retry), path-jail for
artifacts, extended secret scanner (query-param, KEY=VALUE, github_pat_, the
xox- family), write-once chmod 0o444 after Passed, `--machine` ERR_/OK_ output
format; workspace/run.sh — killpg timeout for opencode via the `timeout:` flag
in the ticket; workspace/gate.sh — human gate `gate:` with timeout=deny and
confirmation by an APPROVED comment. Also fixed a report.sh bug along the way
(tail -n +2 was eating single-row lists). Acceptance run: selftest (new
fixtures), timeout process-tree kill, both gate paths, machine output.

## Integrations (2026-10-18)

`mcp/server.py` — a stdio MCP server (stdlib-only, 7 tools over
`hermes kanban`) for external agents — Claude Code, Cursor, Codex, OMP; client
configs in docs/ops.md. Inside Hermes — the `kanban-dispatch` skill: "assign a
task to opencode" in natural language.
