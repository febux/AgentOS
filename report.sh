#!/bin/sh
# report.sh — сводка по доске: статусы + ретраи. Без своей БД, всё из kanban.
# Usage: report.sh [--machine] [board]   (default board: agentos)
# --machine (фаза 4h): greppable-вывод ERR_/OK_ для передачи другому скрипту.
MACHINE=0
BOARD="agentos"
for a in "$@"; do
  case "$a" in
    --machine) MACHINE=1 ;;
    *) BOARD="$a" ;;
  esac
done

if [ "$MACHINE" = 1 ]; then
  hermes kanban --board "$BOARD" list --status blocked 2>/dev/null \
    | while read -r _ id rest; do
        [ -n "$id" ] && echo "ERR_REPORT_BLOCKED: $id $rest"
      done
  hermes kanban --board "$BOARD" stats >/dev/null 2>&1 \
    && echo "OK_REPORT_DONE: $BOARD" \
    || echo "ERR_REPORT_STATS: board $BOARD недоступна"
  exit 0
fi

echo "== ${BOARD} =="
hermes kanban --board "$BOARD" stats
echo
echo "== done tasks =="
hermes kanban --board "$BOARD" list --status done 2>/dev/null 
echo
echo "== blocked tasks =="
hermes kanban --board "$BOARD" list --status blocked 2>/dev/null 
