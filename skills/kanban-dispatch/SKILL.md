---
name: kanban-dispatch
description: "Use when user asks to put tasks on the AgentOS kanban board."
version: 1.0.0
author: Hermes Agent
license: MIT
---

# Kanban dispatch (AgentOS)

## When to Use

Пользователь просит поставить/создать задачу или тикет воркерам (opencode),
проверить доску, подтвердить gate — естественным языком, без команд.

Триггеры (в т.ч. по-русски): «поставь задачу opencode», «создай тикет»,
«раздай воркерам», «что на доске», «апрувни тикет», «покажи статус доски».
Выполняй через terminal, отвечай id тикета + одной строкой. Никогда не пиши
код сам — только создаёшь/читаешь тикеты.

## Правила

- ВСЕГДА явный `--board <slug>` (default-доска называется `default`, switch
  не персистится между CLI-вызовами).
- Тело тикета = спека: что сделать, где (путь), критерий готовности. Пиши её
  сам из фразы пользователя, уточняй только если совсем неясно.
- Assignee по умолчанию `opencode`.
- Флаги — строками В ТЕЛЕ тикета: `type: build|plan|explore|title|summary`
  (модель из agentos/workspace/models.conf; дефолт build — добавляй, когда ясно,
  что задача не кодовая: план/исследование), `model: <id>` (перекрывает type),
  `timeout: <sec>|default`, `gate: <sec>|default`.
  Пользователь сказал «долгая задача» → добавь timeout, «опасная/деплой» → gate.

## Команды

- создать: `hermes kanban --board <b> create "<title>" --body "<spec>" --assignee opencode [--workspace dir:<path>]`
- статус: `hermes kanban --board <b> list [--status done|blocked|ready|...]`;
  сводка: `~/Projects/pet/agentos/report.sh <b>`
- детали/лог verify: `hermes kanban show <id>`
- подтвердить gate: `hermes kanban comment <id> APPROVED`
- разбудить вручную: `hermes kanban --board <b> dispatch --max N`
  (gateway обычно подхватывает ready сам каждые 60с)
- зависло: `hermes kanban reclaim <id>`
- правка спеки: `hermes kanban edit <id>`, затем снова dispatch

## Модели

- Список доступных: `opencode models` (id вида `provider/model`, разделитель `/`, не `:`).
- Маппинг тип→модель: `~/Projects/pet/agentos/workspace/models.conf`
  (build/plan/explore/title/summary). Флаг `type: <x>` в теле тикета → run.sh `-T <x>`.
- Дефолт — type build. `model: <id>` перекрывает type.
- ponytail: opencode CLI `run` игнорирует `agent.<X>.model` из opencode.jsonc
  (берёт только глобальный `model`) — потому маппинг и живёт в models.conf.

## Ответ пользователю

id тикета + одна строка («создал, воркер подхватит в течение минуты» /
«done: N, blocked: M, вот причины»). Не пересказывай весь вывод команд.

MCP-вариант для внешних агентов: ~/Projects/pet/agentos/mcp/server.py
(selftest: `python3 .../server.py --selftest`); конфиги клиентов — docs/ops.md.
