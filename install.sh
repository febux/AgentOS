#!/bin/sh
# install.sh — поставить verify-гейт в текущий git-репозиторий (запускать из корня репо).
set -e
SRC="$(cd "$(dirname "$0")" && pwd)"
cp "$SRC/verify.py" ./verify.py
cp "$SRC/hooks/pre-commit" .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
echo "OK: verify.py + pre-commit установлены в $(pwd)"
