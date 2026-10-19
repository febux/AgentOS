#!/bin/sh
# gate.sh — human-gate с timeout=deny (фаза 4g). Воркер зовет ПОСЛЕ Passed verify
# вместо complete. Оператор подтверждает: hermes kanban comment <id> APPROVED
# Одобрение = комментарий с APPROVE от чужого автора И с таймстампом не раньше
# старта gate (иначе старый APPROVED из прошлого цикла апрувит мгновенно).
# Exit 0 → можно complete; 1 → тишина дольше таймаута = block.
# Usage: gate.sh <task_id> [timeout_sec]   (default 120)
# ponytail: у kanban-комментариев минутное разрешение времени — APPROVED,
# написанный в ту же минуту ДО старта gate, посчитается валидным. Потолок
# редкий (повторный gate в ту же минуту); лечится секундными таймстампами в upstream.
set -u
ID="$1"; TMO="${2:-120}"
PROFILE="${HERMES_PROFILE:-opencode}"
START="$(date '+%Y-%m-%d %H:%M')"
hermes kanban comment "$ID" "GATE: жду подтверждения оператора (комментарий-подтверждение, см. ops), timeout ${TMO}s = deny" >/dev/null
i=0
while [ "$i" -le "$TMO" ]; do
  ok=$(hermes kanban show "$ID" 2>/dev/null | awk -v s="$START" -v me="$PROFILE" '
    /APPROVE/ && match($0, /\[[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9] [0-9][0-9]:[0-9][0-9]\]/) {
      ts = substr($0, RSTART + 1, RLENGTH - 2)
      rest = substr($0, RSTART + RLENGTH)
      if (ts >= s && rest !~ ("] " me ":") && rest !~ /GATE: жду/) { print; exit }
    }')
  if [ -n "$ok" ]; then
    echo "OK_GATE_APPROVED: $ID"
    exit 0
  fi
  [ "$i" -ge "$TMO" ] && break
  sleep 5; i=$((i + 5))
done
echo "ERR_GATE_TIMEOUT: $ID не подтверждён за ${TMO}s — timeout=deny"
exit 1
