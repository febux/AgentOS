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

## Install

Two things must already work on your machine: [Hermes](https://hermes-agent.nousresearch.com/docs)
(the `hermes` command) and [OpenCode](https://opencode.ai) (the `opencode` command).
Then, in order:

1. **Put this folder anywhere**, e.g. `~/Projects/pet/agentos`.

2. **Create the worker profile** — a headless Hermes profile whose only job is
   to run OpenCode on tickets:

   ```bash
   hermes profile create opencode
   ```

   Then open `~/.hermes/profiles/opencode/config.yaml` and make it look like
   this (model/provider = whatever you already use; the key parts are
   `gateway: false` and `platforms: {}` — without them the worker hits a port
   conflict):

   ```yaml
   model:
     default: glm-5.2
     provider: custom
   gateway:
     enabled: false
   platforms: {}
   terminal:
     backend: local
     cwd: /home/san/Projects/pet/agentos/workspace
   ```

3. **Check the verifier runs on your machine**:

   ```bash
   python3 verify.py --selftest
   ```

4. **Turn on auto-dispatch** (ready tickets get picked up every 60 s;
   optional — manual `dispatch` from step 6 also works without it):

   ```bash
   hermes gateway install
   systemctl --user start hermes-gateway
   ```

5. **Create a board for your project** (one board = one project):

   ```bash
   hermes kanban --board myproj boards create
   ```

6. **Write your first ticket** and dispatch it:

   ```bash
   hermes kanban --board myproj create "Add /health to FastAPI" \
     --body "endpoint in src/api/health.py, responds 200 + {status:ok}, test in tests/" \
     --assignee opencode \
     --workspace dir:~/Projects/myproj

   hermes kanban --board myproj dispatch --max 3
   ```

That's it — the worker picks it up, OpenCode writes the code, verify.py checks
it, the ticket completes or gets blocked with a reason.

- Daily cycle in plain words: [docs/guide.md](docs/guide.md)
- Cheat sheet and traps: [docs/ops.md](docs/ops.md)
- Verify gate into another repo: run `install.sh` from that repo's root

## Optional: MCP server (external agents)

Lets Claude Code, Cursor, Codex etc. work with your board — create tickets,
check status, confirm gates. Stdio JSON-RPC, stdlib-only.

Check that it runs:

```bash
python3 mcp/server.py --selftest
```

Then register it in your client (replace the path with yours):

```bash
# Claude Code
claude mcp add agentos-kanban -- python3 ~/Projects/pet/agentos/mcp/server.py
```

```toml
# Codex — ~/.codex/config.toml
[mcp_servers.agentos-kanban]
command = "python3"
args = ["/home/san/Projects/pet/agentos/mcp/server.py"]
```

```json
// Cursor — ~/.cursor/mcp.json
{ "mcpServers": { "agentos-kanban": {
    "command": "python3",
    "args": ["/home/san/Projects/pet/agentos/mcp/server.py"] } } }
```

## Optional: kanban-dispatch skill (natural language inside Hermes)

Gives your main Hermes profile the skill "поставь задачу opencode" / "что на
доске" — it writes the ticket itself instead of you typing the CLI:

```bash
mkdir -p ~/.hermes/skills/productivity
cp -r skills/kanban-dispatch ~/.hermes/skills/productivity/
```

Works on the next session start.

## Status

Phases 1–4 done, plus MCP integrations. The phase-by-phase history and
acceptance runs: [docs/history.md](docs/history.md).
