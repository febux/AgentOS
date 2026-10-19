#!/usr/bin/env python3
"""AgentOS kanban MCP server — stdio JSON-RPC 2.0, stdlib-only.

Выставляет `hermes kanban` как MCP-тулы для внешних агентов (Claude Code,
Cursor, Codex, OMP...). Ничего не reimplements — тонкая обёртка над CLI.
Запуск: python3 server.py (клиент сам держит процесс через stdio).

Self-check: python3 server.py --selftest — гоняет handshake + create/list/show
через pexpect-подобный пайп в отдельный процесс (без pexpect: subprocess).
"""
import json
import subprocess
import sys

TOOLS = [
    {
        "name": "kanban_create",
        "description": "Создать тикет на доске AgentOS. Body = спека (что/где/критерий "
                       "готовности). Флаги-строки в body: 'model: <id>', 'timeout: <sec>|default', "
                       "'gate: <sec>|default' — передай их в соотв. параметрах, они добавятся в body.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "короткий заголовок"},
                "body": {"type": "string", "description": "спека задачи"},
                "board": {"type": "string", "description": "слаг доски", "default": "default"},
                "assignee": {"type": "string", "description": "профиль-воркер", "default": "opencode"},
                "workspace": {"type": "string", "description": "dir:<путь> для работы в чужом репо"},
                "model": {"type": "string", "description": "модель исполнителя (строка 'model: <id>' в body)"},
                "timeout": {"type": "string", "description": "сек или 'default' (строка 'timeout: <v>' в body)"},
                "gate": {"type": "string", "description": "сек или 'default' — human-gate (строка в body)"},
            },
            "required": ["title"],
        },
    },
    {
        "name": "kanban_list",
        "description": "Список тикетов доски (опционально по статусу: ready/running/blocked/done/archived).",
        "inputSchema": {"type": "object", "properties": {
            "board": {"type": "string"},
            "status": {"type": "string", "description": "готовый фильтр hermes kanban list --status"},
        }},
    },
    {
        "name": "kanban_show",
        "description": "Полная картина тикета: тело, комментарии, события (в т.ч. вывод verify и ретраи).",
        "inputSchema": {"type": "object", "properties": {"task_id": {"type": "string"}},
                        "required": ["task_id"]},
    },
    {
        "name": "kanban_comment",
        "description": "Комментарий на тикет. 'APPROVED' = подтверждение human-gate.",
        "inputSchema": {"type": "object", "properties": {"task_id": {"type": "string"},
                                                         "text": {"type": "string"}},
                        "required": ["task_id", "text"]},
    },
    {
        "name": "kanban_complete",
        "description": "Закрыть тикет как done (нормально это делает воркер после verify Passed).",
        "inputSchema": {"type": "object", "properties": {"task_id": {"type": "string"}},
                        "required": ["task_id"]},
    },
    {
        "name": "kanban_block",
        "description": "Заблокировать тикет с причиной.",
        "inputSchema": {"type": "object", "properties": {"task_id": {"type": "string"},
                                                         "reason": {"type": "string"}},
                        "required": ["task_id", "reason"]},
    },
    {
        "name": "kanban_stats",
        "description": "Сводка по статусам доски.",
        "inputSchema": {"type": "object", "properties": {"board": {"type": "string"}}},
    },
]


def run_hermes(args):
    p = subprocess.run(["hermes", "kanban"] + [a for a in args if a],
                       capture_output=True, text=True, timeout=300)
    out = (p.stdout + p.stderr).strip()
    return p.returncode, out or f"(пусто, rc={p.returncode})"


def call_tool(name, a):
    if name == "kanban_create":
        body = a.get("body", "")
        for k, prefix in (("model", "model"), ("timeout", "timeout"), ("gate", "gate")):
            if a.get(k):
                body += f"\n{prefix}: {a[k]}"
        args = ["--board", a.get("board", "default"), "create", a["title"],
                "--body", body, "--assignee", a.get("assignee", "opencode")]
        if a.get("workspace"):
            args += ["--workspace", a["workspace"]]
        return run_hermes(args)
    if name == "kanban_list":
        args = ["--board", a.get("board", "default"), "list"]
        if a.get("status"):
            args += ["--status", a["status"]]
        return run_hermes(args)
    if name == "kanban_show":
        return run_hermes(["show", a["task_id"]])
    if name == "kanban_comment":
        return run_hermes(["comment", a["task_id"], a["text"]])
    if name == "kanban_complete":
        return run_hermes(["complete", a["task_id"]])
    if name == "kanban_block":
        return run_hermes(["block", a["task_id"], a.get("reason", "")])
    if name == "kanban_stats":
        return run_hermes(["--board", a.get("board", "default"), "stats"])
    return 1, f"unknown tool: {name}"


def reply(id_, result):
    sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": id_, "result": result}) + "\n")
    sys.stdout.flush()


def serve():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        msg = json.loads(line)
        if "id" not in msg:  # notification — просто принимаем
            continue
        m, id_ = msg.get("method"), msg["id"]
        if m == "initialize":
            reply(id_, {"protocolVersion": msg["params"].get("protocolVersion", "2025-06-18"),
                        "capabilities": {"tools": {}},
                        "serverInfo": {"name": "agentos-kanban", "version": "1.0.0"}})
        elif m == "tools/list":
            reply(id_, {"tools": TOOLS})
        elif m == "tools/call":
            rc, out = call_tool(msg["params"]["name"], msg["params"].get("arguments", {}))
            reply(id_, {"content": [{"type": "text", "text": out}], "isError": rc != 0})
        else:
            reply(id_, {"error": {"code": -32601, "message": f"method not found: {m}"}})


def selftest():
    proc = subprocess.Popen([sys.executable, __file__], stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE, text=True)

    def rpc(method, params=None, id_=1):
        msg = {"jsonrpc": "2.0", "id": id_, "method": method}
        if params is not None:
            msg["params"] = params
        proc.stdin.write(json.dumps(msg) + "\n")
        proc.stdin.flush()
        return json.loads(proc.stdout.readline())

    r = rpc("initialize", {"protocolVersion": "2025-06-18"})
    assert "agentos-kanban" in r["result"]["serverInfo"]["name"], r
    r = rpc("tools/list", id_=2)
    names = {t["name"] for t in r["result"]["tools"]}
    assert names == {"kanban_create", "kanban_list", "kanban_show", "kanban_comment",
                     "kanban_complete", "kanban_block", "kanban_stats"}, names
    r = rpc("tools/call", {"name": "kanban_create",
                           "arguments": {"title": "mcp-selftest", "body": "тестовый тикет от MCP selftest",
                                         "timeout": "default"}}, id_=3)
    assert not r["result"]["isError"], r
    text = r["result"]["content"][0]["text"]
    print(text)
    r = rpc("tools/call", {"name": "kanban_list", "arguments": {}}, id_=4)
    assert "mcp-selftest" in r["result"]["content"][0]["text"], r
    proc.stdin.close()
    print("MCP SELFTEST PASSED")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    else:
        serve()
