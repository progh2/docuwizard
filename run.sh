#!/usr/bin/env bash
# DocuWizard — macOS / Linux
# 사용: ./run.sh   (처음이면: chmod +x run.sh)
set -euo pipefail
cd "$(dirname "$0")"

if command -v python3 >/dev/null 2>&1; then
  PY=python3
elif command -v python >/dev/null 2>&1; then
  PY=python
else
  echo "[오류] Python 3이 없습니다." >&2
  echo "  macOS: brew install python" >&2
  echo "  Linux: sudo apt install python3 python3-venv python3-pip" >&2
  exit 1
fi

VENV_PY=".venv/bin/python"
if [[ ! -x "$VENV_PY" ]]; then
  echo "[안내] 가상환경(.venv)을 만들고 패키지를 설치합니다…"
  "$PY" -m venv .venv
  "$VENV_PY" -m pip install --upgrade pip
  "$VENV_PY" -m pip install -e ".[dev]"
fi

# macOS Qt shell 환경용 (없어도 무방)
export QT_MAC_WANTS_LAYER="${QT_MAC_WANTS_LAYER:-1}"

echo "DocuWizard 시작…"
exec "$VENV_PY" -m docuwizard
