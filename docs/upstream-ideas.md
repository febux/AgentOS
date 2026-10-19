# Upstream ideas: rivet-dev/agentos and SapienXai/AgentOS

Analysis from 2026-10-18 (the clones were in scratch, links: github.com/rivet-dev/agentos,
github.com/SapienXai/AgentOS). What was taken into the work — PLAN.md, phase 4.
This file is the full tier list and the parking lot of what we are NOT doing now.

Both repos confirm the core concept: Sapien outright forbids "build a parallel
runtime" in its AGENTS.md; rivet keeps enforcement in the kernel code, not in prompts.

## Taken into phase 4

| What | From | Essence |
|---|---|---|
| Honest verdict {pass\|fail\|skipped, retryable} | Sapien evidence + rivet error.rs | Passed = 0 fail AND 0 skipped; a non-retryable fail → block immediately |
| kill(-pgid) of the opencode tree | rivet kernel.rs | start_new_session + killpg — children don't get orphaned |
| Path-jail (resolve + startswith workspace) | rivet permissions.rs | a symlink pointing outside is not verified |
| Redaction patterns (github_pat_, xox[baprs]-, query-param, KEY=VALUE) | Sapien redaction.ts | regex ported 1-to-1 |
| Write-once chmod 0o444 after Passed | rivet immutable xattr | a retry cannot rewrite an accepted artifact |
| `timeout: <sec>` in the ticket body | Sapien secure-browser-worker | a flag for long-running tasks; no key — no timeout |
| `gate: <sec>` in the ticket body (timeout=deny) | Sapien browser-policy | waiting-human → silence = block; not for every task |
| `--machine` output ERR_<SUBSYS>_* | rivet supervision.rs | a machine-readable report format by grep |

## Parking lot — when it hurts (don't build in advance)

- **Per-task env secrets from SQLite** (rivet host_functions): tokens not in
  ~/.zshrc but in the env of a specific subprocess. Take when workers need API keys.
- **Drop-guard / finally in the worker wrapper** (rivet supervision.rs): a
  guaranteed verdict when the worker crashes ("worker exited without verdict").
  Take with multi-worker dispatch.
- **Cron overlap-policy Skip** (rivet cron.rs): flock on a lockfile before a
  tick. Take if dispatch ever starts ticking on a cron.
- **Docker isolation of opencode** (Sapien Dockerfile.browser-worker): ~10
  lines of `docker run` with a read-only mount of the working directory. Take
  for untrusted tasks.

## From agent37-platform/minions (analyzed 2026-10-19; clone in scratch, ran live)

Minions = TS kanban board over Hermes root sessions + a Python JSONL worker that
imports Hermes internals. On this machine the worker crashed (PATH `python3` →
Hermes bundled venv), so nothing was installed — but the source is a free
spec for the same problem AgentOS solves.

### Take now

- **Verify-core already exists upstream: `hermes_cli/goals.py` → GoalManager.**
  The deepest idea of the batch. A goal carries a **GoalContract** (done-criteria
  + subgoals, visible to BOTH the agent and the LLM judge) and **GoalGates**:
  deterministic shell commands that must pass BEFORE the judge is consulted —
  a failing gate short-circuits judging and its bounded output tail becomes the
  next turn's continuation prompt. I.e. the deterministic check *steers* the LLM
  instead of merely grading it afterwards: `pytest -q` failing output tells the
  agent exactly what to fix, turn after turn, until the gate passes. Plus:
  turn budget, auto-pause on consecutive judge transport failures (a broken API
  key no longer burns the budget), verdicts {done|blocked|continue|wait|skipped},
  and wait-barriers (pid / delegation-batch / wall-clock) that park the loop
  instead of poking the agent into busy-work. For AgentOS: card → hermes goal
  with `gate: <verify command>`; verify.py stays as the human-facing runner, the
  autonomous loop becomes native API instead of our own engine. Read
  `~/.hermes/hermes-agent/hermes_cli/goals.py` (1093+ lines) before writing any
  verify code.
- **Spawn agents with an explicit interpreter path + signature guard.**
  Minions' worker crash root cause: it calls `python3` from PATH, which on this
  host resolves to Hermes' bundled venv interpreter (wrong site-packages) →
  ModuleNotFoundError. Lesson for any AgentOS subprocess spawning: always
  resolve the interpreter explicitly (their `HERMES_PYTHON` env override), never
  trust PATH. Their second cheap insurance: `inspect.signature(AIAgent.__init__).parameters`
  before constructing the host agent — constructor drift from a host-agent
  update degrades gracefully instead of crashing.

### Parking lot — when it hurts

- **Task = persistent root session; board DB stores metadata only.**
  Transcripts live in the agent's own session DB (we already read them via
  `hermes kanban log`); the board keeps only derived state: status
  (in_progress → in_review → done), model/effort override, context tokens
  used/window, timestamps. Meaning: never duplicate messages into the kanban
  DB — that creates a second source of truth and sync bugs. Take if the board
  grows beyond git-files state.
- **Adapter interface as the agent seam** (their `adapters/types.ts`, 104 lines):
  `chat / chatStream / interrupt / getMessages / generateTitle / compressSession /
  setGoal·pause·resume·evaluate / scheduledTasks CRUD + tick`. One interface the
  whole board talks to; backends (Hermes today, OpenCode next) are swappable
  without touching board logic. AgentOS MCP server could expose exactly this
  surface instead of inventing verbs. Take when the OpenCode path stabilizes.
- **Task-agent system prompt** (26 lines, XML-tagged): clarify-first ("ask
  focused questions, not a wall"), recurring work → agent-native cron, NOT
  systemd; large list-processing → sample-first validation, then a CSV
  checkpoint file that later runs append to instead of restarting. Meaning:
  batch jobs become durable (restart = resume from checkpoint), and the model
  is told up front which tool owns repetition. Steal wholesale for AgentOS
  card prompts when autonomous execution lands.

## Rejected (deliberately; don't revisit without new pain)

- **Fencing generations of claims, lease+heartbeat in SQLite** (both repos) —
  upstream `hermes kanban` internals; we already have `reclaim`. Reaching into
  someone else's SQLite = a parallel runtime.
- **Append-only event timeline** (Sapien) — already exists: `hermes kanban log <id>`.
- **Fairness scheduler (HDRR), content-addressed block store** (rivet) — one
  worker, ordinary files in git.
- **Memory/diary layer** (Sapien) — they don't build one themselves; our
  "memory between attempts" = the failure reason in the retry prompt (phase 2).
