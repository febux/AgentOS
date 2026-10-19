#!/bin/sh
# run.sh — запуск opencode с killpg-таймаутом (фазы 4b/4f). Воркер зовёт ЭТО, не opencode напрямую.
# Usage: run.sh [-m model] [-T type] [-t sec] "spec..."
#   -T <type> — тип задачи (build|plan|explore|title|summary), модель берётся из
#   models.conf рядом со скриптом. Дефолт build. -m перекрывает.
#   (ponytail: свой маппинг, а не agent.<X>.model — opencode CLI run его игнорирует,
#   берёт только глобальный model; -m работает всегда)
#   -t берётся из строки "timeout: <sec>" тикета; нет ключа — нет таймаута.
# timeout(1) кладёт команду в отдельную process group и убивает её целиком (-k = SIGKILL
# спустя 5с после TERM) — дети opencode не осиротеют.
# ponytail: OC_CMD переопределяем для тестов без реального opencode.
set -u
OC_CMD="${OC_CMD:-opencode}"
CONF="$(dirname "$0")/models.conf"
TYPE="build"
MODEL=""
TIMEOUT=""
while getopts "m:T:t:" o; do
  case "$o" in
    m) MODEL="$OPTARG" ;;
    T) TYPE="$OPTARG" ;;
    t) TIMEOUT="$OPTARG" ;;
    *) echo "usage: run.sh [-m model] [-T type] [-t sec] spec" >&2; exit 2 ;;
  esac
done
shift $((OPTIND - 1))
[ $# -ge 1 ] || { echo "usage: run.sh [-m model] [-T type] [-t sec] spec" >&2; exit 2; }

# -m > тип из models.conf > ошибка
if [ -z "$MODEL" ]; then
  MODEL="$(grep -m1 "^${TYPE}=" "$CONF" 2>/dev/null | cut -d= -f2-)"
  [ -n "$MODEL" ] || { echo "ERR_RUN_BAD_TYPE: неизвестный тип '$TYPE' (см. $CONF)" >&2; exit 2; }
fi

if [ -n "$TIMEOUT" ]; then
  timeout -k 5 "$TIMEOUT" "$OC_CMD" run -m "$MODEL" "$1"
  rc=$?
  [ "$rc" -eq 124 ] && echo "ERR_RUN_TIMEOUT: opencode превысил ${TIMEOUT}s (убит по pgid)"
  exit "$rc"
fi
exec "$OC_CMD" run -m "$MODEL" "$1"
