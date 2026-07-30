#!/usr/bin/env bash
# DocuWizard launcher for macOS
# Usage:  chmod +x scripts/run-macos.sh && ./scripts/run-macos.sh

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

pick_python() {
  if command -v python3 >/dev/null 2>&1; then
    echo python3
  elif command -v python >/dev/null 2>&1; then
    echo python
  else
    echo "[오류] Python 3이 없습니다. Homebrew로 설치: brew install python" >&2
    exit 1
  fi
}

PY="$(pick_python)"
VENV_PY="$ROOT/.venv/bin/python"

if [[ ! -x "$VENV_PY" ]]; then
  echo "[안내] 가상환경(.venv)을 만들고 패키지를 설치합니다…"
  "$PY" -m venv .venv
  "$VENV_PY" -m pip install --upgrade pip
  "$VENV_PY" -m pip install -e ".[dev]"
fi

# Qt / PySide on macOS may need this for some shell environments
export QT_MAC_WANTS_LAYER="${QT_MAC_WANTS_LAYER:-1}"

echo "DocuWizard 시작…"
exec "$VENV_PY" -m docuwizard
