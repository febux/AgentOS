#!/bin/sh
# run.sh — запуск opencode с killpg-таймаутом (фазы 4b/4f). Воркер зовёт ЭТО, не opencode напрямую.
# Usage: run.sh [-m model] [-t sec] "spec..."
#   -t берётся из строки "timeout: <sec>" тикета; нет ключа — нет таймаута.
# timeout(1) кладёт команду в отдельную process group и убивает её целиком (-k = SIGKILL
# спустя 5с после TERM) — дети opencode не осиротеют.
# ponytail: OC_CMD переопределяем для тестов без реального opencode.
set -u
OC_CMD="${OC_CMD:-opencode}"
MODEL="zai-coding-plan/glm-5.2"
TIMEOUT=""
while getopts "m:t:" o; do
  case "$o" in
    m) MODEL="$OPTARG" ;;
    t) TIMEOUT="$OPTARG" ;;
    *) echo "usage: run.sh [-m model] [-t sec] spec" >&2; exit 2 ;;
  esac
done
shift $((OPTIND - 1))
[ $# -ge 1 ] || { echo "usage: run.sh [-m model] [-t sec] spec" >&2; exit 2; }

if [ -n "$TIMEOUT" ]; then
  timeout -k 5 "$TIMEOUT" "$OC_CMD" run -m "$MODEL" "$1"
  rc=$?
  [ "$rc" -eq 124 ] && echo "ERR_RUN_TIMEOUT: opencode превысил ${TIMEOUT}s (убит по pgid)"
  exit "$rc"
fi
exec "$OC_CMD" run -m "$MODEL" "$1"
