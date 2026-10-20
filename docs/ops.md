# How to use AgentOS (the everyday cycle)

## The board trap (learned 2026-10-18)

`hermes kanban boards switch` does NOT persist between CLI calls — every call
starts on the default board. Always write `--board <slug>` explicitly in every
command. report.sh also takes the board as an argument.

## Auto-dispatcher (instead of manual dispatch)

`hermes kanban daemon` is DEPRECATED: the dispatcher is built into the gateway.

    hermes gateway install   # once: a systemd user-service
    systemctl --user start hermes-gateway

Ready tickets get picked up automatically every 60s (config: `kanban:`
in config.yaml). Manual `dispatch` still works as a force measure.
Logs: `journalctl --user -u hermes-gateway -f`.

## Choosing a model per task

Add a `model: <id>` line to the ticket body — the worker will pass it to
`opencode run -m` instead of the default. Current list: `opencode models`.

This is the ONLY way to pick the executor model. `hermes kanban --model` /
`set-model` override the model of the worker **profile** (the Hermes brain
that reads the ticket and calls run.sh), not opencode; the worker profile
only has the custom/Z.AI provider, so ollama/kimi ids there fail with
exit 78 (terminal provider error) and block the ticket.

## Timeout for long tasks (phase 4f)

A `timeout: <sec>` line in the ticket body (or `timeout: default` = 600s) —
the worker will start opencode via `run.sh -t <sec>`: when the time expires
the whole process group is killed (SIGTERM, then SIGKILL), the ticket goes to
retry. No line — no timeout.

## Human gate (phase 4g)

A `gate: <sec>` line in the ticket body (or `gate: default` = 120s) — after
Passed verify the ticket is NOT completed but waits for your confirmation:
silence longer than <N>s = block (timeout=deny). Confirm:
`hermes kanban comment <id> APPROVED`. The worker sees the comment by itself
and completes.

## Machine format of verify/report (phase 4h)

`verify.py --machine ...` and `report.sh --machine [board]` — output as
`ERR_VERIFY_*` / `ERR_REPORT_*` / `OK_*` lines for grepping by another script.
The NORETRY prefix = do not retry, block immediately (secrets, path-jail).

## MCP server for external agents (Claude Code, Cursor, Codex, OMP)

`mcp/server.py` — stdio JSON-RPC, stdlib-only, a thin wrapper over `hermes kanban`.
7 tools: kanban_create / list / show / comment / complete / block / stats.
The model/timeout/gate flags are passed as parameters and land in the body as
lines by themselves. Check: `python3 mcp/server.py --selftest`.

Connecting to clients (substitute your own path):

    # Claude Code
    claude mcp add agentos-kanban -- python3 /home/san/Projects/pet/agentos/mcp/server.py

    # Codex (~/.codex/config.toml)
    [mcp_servers.agentos-kanban]
    command = "python3"
    args = ["/home/san/Projects/pet/agentos/mcp/server.py"]

    # Cursor (~/.cursor/mcp.json)
    { "mcpServers": { "agentos-kanban": {
        "command": "python3",
        "args": ["/home/san/Projects/pet/agentos/mcp/server.py"] } } }

    # any stdio MCP client: command=python3, args=[<path>/mcp/server.py]

## Installing the verify gate into another project

From the root of the target git repo: `/path/to/agentos/install.sh`
(copies verify.py + the pre-commit hook).

## One-time (after phase 1)

The worker profile and board are already set up. Every new project — one command:

```bash
hermes kanban --board <project> boards create
```

The pre-commit hook goes into the project where you want secret scanning:
`cp hooks/pre-commit <repo>/.git/hooks/pre-commit`

## Daily cycle — 3 commands

1. **Pile up tickets** (specs instead of prompts):
   ```bash
   hermes kanban --board myproj create "Add /health to FastAPI" \
     --body "endpoint in src/api/health.py, 200 + {status:ok}, test in tests/" \
     --assignee opencode \
     --workspace dir:~/PycharmProjects/myproj
   ```
   The ticket body = the spec: what, where, the done criterion. The more
   precise the body, the fewer retries.

2. **Start the line and walk away**:
   ```bash
   hermes kanban --board myproj dispatch --max 3
   ```
   Each ticket gets picked up by a worker → OpenCode writes → verify.py checks
   → complete or block with a reason.

3. **Come back and look**:
   ```bash
   hermes kanban --board myproj list          # what's done / blocked
   hermes kanban --board myproj show <id>     # log: what was done, what verify said
   ```

## Working through results

- **done** — open the artifact, review as usual (the machine checked
  existence/structure/secrets, not quality — the final review is yours),
  commit. The hook catches secrets by itself.
- **blocked** — the reason is in the log (verify failed: ...). Read it, fix
  the ticket body (`hermes kanban edit <id>`), reopen and dispatch again.
- **hopelessly stuck** — `hermes kanban reclaim <id>` takes the ticket back.

## What NOT to do

- Don't write code in the worker by hand — the profile is headless for a
  reason; its job: call OpenCode and verify. Do it yourself — lose the whole point.
- Don't create a board "for the future". Board = a living project.
- Don't raise --max above what you're ready to review in an evening.

## Where this fits into your current workflow

You have agents write code, you review. Right now you ARE the dispatcher:
handing out prompts one by one. AgentOS only removes the transport: specs live
on the board, distribution is automatic, "done" is machine-checked. The review
stays yours — the last gate is always a human, deliberately (agentic-os does
the same).
