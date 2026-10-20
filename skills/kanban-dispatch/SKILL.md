---
name: kanban-dispatch
description: 'Triggers: «поставь задачу/задачи opencode», "create ticket", board status — AgentOS kanban tickets for workers, never run opencode directly.'
version: 1.0.0
author: Hermes Agent
license: MIT
---

# Kanban dispatch (AgentOS)

## When to Use

Пользователь просит поставить/создать задачу или тикет воркерам (opencode),
проверить доску, подтвердить gate — естественным языком, без команд.

Триггеры (в т.ч. по-русски): «поставь задачу opencode», «поставь задачи
opencode» (мн.ч. = N тикетов на борде, НЕ запускать opencode-процессы
напрямую из terminal), «создай тикет»,
«раздай воркерам», «что на доске», «апрувни тикет», «покажи статус доски».
Выполняй через terminal, отвечай id тикета + одной строкой. Никогда не пиши
код сам — только создаёшь/читаешь тикеты. Никогда не `opencode run` напрямую,
если пользователь просил «поставить задачи».

## Правила

- ВСЕГДА явный `--board <slug>` ПЕРЕД ПОДКОМАНДОЙ — для КАЖДОГО вызова,
  включая `edit`/`set-model`/`show`/`comment` (switch и default-борда не
  персистятся между CLI-вызовами; `edit` без `--board` ищет id в текущей
  доске и падает «unknown id»).
- Тело тикета = спека: что сделать, где (путь), критерий готовности. Пиши её
  сам из фразы пользователя, уточняй только если совсем неясно. Многострочное
  тело пиши в файл и передавай `--body-file <path>` — переживает кавычки и
  строки, похожие на флаги.
- Assignee по умолчанию `opencode`.
- Новая борда под проект: `hermes kanban boards create <slug>` +
  `hermes kanban boards set-default-workdir <slug> <path>` (path — позиционный
  аргумент, не `--path`), затем `--workspace dir:<path>` на тикетах.
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
- правка спеки: `hermes kanban --board <b> edit <id> --body "..."`, затем снова dispatch
- модель ИСПОЛНИТЕЛЯ (opencode run) — ТОЛЬКО строкой `model: <provider/model>`
  в теле тикета. НЕ используй `hermes kanban --model`/`set-model` для этого:
  это model_override hermes-профиля-воркера («мозг», читающий тикет и зовущий
  run.sh), у него провайдер только custom/Z.AI — kimi/ollama там дают exit 78
  terminal provider и blocked-тикет (проверено на lanlink t_da9d6ec0).
- правки/`set-model` на DONE-тиките ничего не перезапускают — для
  доработки/новых требований создавай НОВЫЙ тикет, а не редактируй закрытый

## Модели

- Список доступных: `opencode models` (id вида `provider/model`, разделитель `/`, не `:`).
- Маппинг тип→модель: `~/Projects/pet/agentos/workspace/models.conf`
  (build/plan/explore/title/summary). Флаг `type: <x>` в теле тикета → run.sh `-T <x>`.
- Дефолт — type build. `model: <id>` перекрывает type.
- ponytail: opencode CLI `run` игнорирует `agent.<X>.model` из opencode.jsonc
  (берёт только глобальный `model`) — потому маппинг и живёт в models.conf.

## Репозитории с openspec

Если в целевом репо есть `openspec/`, задача на имплементацию спекы обязана
требовать двойной трекинг готовности: (1) openspec change с proposal.md +
tasks.md (чекбоксы по requirements/scenarios, формат как в
openspec/changes/archive/*), (2) подзадачи-тикететы на борде, ID продублированы
в tasks.md. Воркер сам создаёт и то и другое и закрывает по мере работы — иначе
готовность не отследить.

## Ответ пользователю

id тикета + одна строка («создал, воркер подхватит в течение минуты» /
«done: N, blocked: M, вот причины»). Не пересказывай весь вывод команд.

MCP-вариант для внешних агентов: ~/Projects/pet/agentos/mcp/server.py
(selftest: `python3 .../server.py --selftest`); конфиги клиентов — docs/ops.md.
