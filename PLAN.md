# PLAN — AgentOS: kanban + OpenCode + enforcement

Goal: the technical core from agentos.guide, strengthened by the enforcement
idea from KbWen/agentic-os.
Principle: shortest path to done. Every phase ends with a working command you
can run and see the result of. Nothing from a later phase gets built early.

## What we take, from where

| From | What | Why |
|---|---|---|
| agentos.guide | kanban dispatcher, headless profile, OpenCode as executor, the "orchestrator verifies, doesn't write" pattern | the only working orchestration scheme from the guide; verified, `hermes kanban` exists and matches the description |
| agentos.guide (traps) | 3 configuration traps: port conflict for workers, `openai-compat` doesn't exist, credential overrides the yaml base_url | the only genuinely valuable part of the guide; goes into docs/ops.md so we don't step on it again |
| KbWen/agentic-os | **enforcement instead of prompts**: a verify script decides done/not-done, not the agent's word | the repo's main lesson: a gate in a script/hook cannot lie |
| KbWen/agentic-os | credential scan in pre-commit (scan_credentials.py, ~7 regex patterns, redacted output) | their only standalone-useful component; rewritten compactly, we don't pull their 50-tool framework |
| buildermethods/agent-os | nothing | its theme (specs/standards) is someone else's; spec discipline already exists in our ticket bodies |

What we deliberately do NOT take from agentic-os: worklog contracts,
feature/hotfix/tiny-fix classification, a state machine, an ADR process, a
hash-chained audit log. That's a tax on every PR with a bus factor of 1.
Our verifier is 1 script. Our "audit chain" is `hermes kanban log <task>`
(already in Hermes).

## Architecture — 3 layers

1. **Orchestration** (done, upstream): `hermes kanban` — a SQLite board,
   atomic claims, `dispatch` spawns workers, `--workspace` isolates.
2. **Execution** (done, upstream): OpenCode as the code provider;
   the worker profile calls `opencode run -m <model> "<spec>"`.
3. **Verification** (our only new code): `verify.py` — machine checks of the
   artifact + a `pre-commit` secret scanner. The "machine said no" party from
   agentic-os, without their bureaucracy.

One core rule: **complete without a Passed verify is forbidden.** Enforced by
verify.py being called from the worker's AGENT.md instruction AND being
available manually; the gate is physical — only the worker closes a ticket,
and the worker can't close a ticket around the script, because its standing
order is singular and greppable (`hermes kanban show <id>` either contains the
verification line or not — visible in the log).

## Phases

### Phase 1 — the core (the core of the core, all in one evening)

1. Profile `~/.hermes/profiles/opencode/config.yaml`:
   ```yaml
   model:
     default: <your working model>       # not omniroute/free — see "models"
     provider: <provider>
   toolsets: [hermes-cli]
   terminal: {backend: local, cwd: ~/PycharmProjects/agentos/workspace}
   gateway: {enabled: false}              # trap #1: the worker is headless
   platforms: {}
   ```
   AGENT.md in the profile: "Never write code yourself. Run
   `opencode run "<ticket body>"` in the workspace, then `python3 verify.py <artifact>`.
   Passed → `hermes kanban complete <id>` quoting the verify output.
   Failed → `hermes kanban block <id>` with the error text."

2. `verify.py` (stdlib-only, ~80 lines): checks by artifact type:
   - any file: exists, > minimal size, not an empty diff;
   - .html: parses, has `</html>`, has `<title>`;
   - .py: `python -m py_compile` passes;
   - all: regex secret scan (AKIA, `-----BEGIN`, ghp_, sk-, xoxb) — FAIL.
   Self-check: `python3 verify.py --selftest` — runs on good/bad fixtures.

3. `hooks/pre-commit`: the scan from verify.py against staged files (a call to
   `python3 verify.py --staged`), redacted output, exit 1 = block.

4. The board: `hermes kanban boards create` + the first ticket "build a
   hello-world landing.html" + `dispatch --max 1`.

Phase 1 acceptance: a ticket goes through the full
board→worker→opencode→verify→complete cycle without manual intervention;
a commit with a fake AKIA key is blocked by the hook.

### Phase 2 — retry loop and reporting

- AGENT.md addition: verify Failed → a repeat `opencode run` with the error
  text in the prompt, at most 2 retries, then block. (This is the guide's
  "failures retry themselves", just explicit.)
- `hermes kanban stats` + a simple `report.sh`: how many done/blocked, how
  many retries — from `hermes kanban log`, no database of our own.
- Check on a real mini-project: 3 tickets (a landing, a CLI utility with a
  py_compile gate, a fix in an existing file).

Acceptance: a deliberately broken ticket (the spec requires a file, OpenCode
doesn't create it) ends blocked with a sensible reason, not "done" with an
empty file.

### Phase 3 — only if phases 1-2 see real use

Candidates as pain appears, NOT in advance:
- a git gate in verify (the artifact is committed, not just sitting in the workspace);
- applying pre-commit to all of your projects (a three-line standalone
  `install.sh` script);
- a second worker profile with a different model for comparison;
- `hermes kanban daemon` instead of manual dispatch.

### Phase 4 — core hardening (from the analysis of rivet-dev/agentos and SapienXai/AgentOS, 2026-10-18)

The full tier list and the parking lot of rejected ideas — docs/upstream-ideas.md.
Below only what we build. The concept is untouched: everything strengthens
verify.py and the worker wrapper.

4a. Honest verify.py verdict (Sapien: evidence/*.json; rivet: error.rs):
- every check returns {status: pass|fail|skipped, reason};
- the final Passed only if 0 fail AND 0 skipped on critical checks
  (closes the hole "no files found → 0 errors → Passed");
- a fail has retryable: true|false; retry loop: fail+retryable → retry,
  fail+!retryable (secrets etc.) → block immediately without spending an attempt.

4b. Killing the opencode process tree (rivet: kernel.rs kill(-pgid)):
- the worker wrapper starts `opencode run` via Popen(start_new_session=True);
- on timeout/cancel — os.killpg(os.getpgid(pid), SIGKILL), children don't get orphaned.

4c. Path-jail (rivet: permissions.rs):
- before checks: Path(f).resolve() must start with the workspace root,
  otherwise fail (an artifact symlinked outside is not verified).

4d. Extended secret scanner (Sapien: redaction.ts, patterns ported 1-to-1):
- github_pat_, the xox[baprs]- family, a secret in a query-param (`[?&](token|key|secret|password)=`),
- a KEY=VALUE assignment outside quotes.

4e. Write-once artifact (rivet: immutable):
- after Passed: os.chmod(artifact, 0o444) — a retry physically cannot rewrite an accepted artifact.

4f. Timeout for long tasks — via a flag in the ticket body, like `model: <id>`:
- `timeout: <sec>` → the worker wraps opencode run in the killpg timeout from 4b;
- `timeout: default` → the default (600s); no key → no timeout. Also covers a
  liveness poll: the process died before verify → retry immediately, don't
  wait for the timeout.

4g. Human gate — via a flag in the ticket body, not for every task:
- `gate: <sec>` (or `gate: default` = 120s) → after Passed verify the worker
  does NOT complete, but puts the ticket into waiting-human (request-review +
  a comment);
- operator confirmation → complete; silence longer than <sec> → block
  (timeout=deny).

4h. `--machine` flag for verify.py and report.sh:
- output as `ERR_<SUBSYS>_<WHAT>: detail` lines — a machine interface by grep
  for another script; without the flag — the human format as now.

Phase 4 acceptance: verify.py --selftest runs the new fixtures (a skipped
check → not Passed; a secret in a query-param → fail !retryable → block
without retry; a symlink outside → fail; a retry cannot rewrite a 0o444
artifact); a ticket with `timeout: 5` and a sleeping task is killed by killpg
and goes to retry; a ticket with `gate: default` doesn't finish without the
operator and gets blocked on timeout.

## Known traps (moved from the guide, confirmed by Hermes logic)

1. The worker inherits gateway/platforms → port conflict → "pid not alive".
   Fix: `gateway.enabled: false`, `platforms: {}` in the worker profile.
2. The provider `openai-compat` doesn't exist. Fix: `provider: openrouter` +
   `api_mode: chat_completions` for any OpenAI-compatible base_url.
3. `base_url` in yaml is ignored if the credential store holds a record for
   the provider without its own base_url — calls go to the real openrouter.ai
   and fail with 400. Fix: base_url must be in the credential record too.

## Models

The guide feeds everything "free" models via OmniRoute. Decision: we do NOT
bring OmniRoute into the core. It's a separate dependency with opaque routing
and guaranteed limits/degradation. The core works with any model set in the
profile (you already have working providers). OmniRoute can be plugged in
later as just another provider — the core doesn't change.

## Open questions (resolve in phase 1, not earlier)

- Which provider/model for the worker profile by default (your working one, Z.AI?).
- Whether a separate workspace root is needed, or inherit the ticket project's
  cwd (`--workspace dir:...` already supports both).
