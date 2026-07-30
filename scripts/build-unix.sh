# Cross-platform build helpers (optional). Windows: packaging/build.ps1
# macOS / Linux onedir bundle via PyInstaller.

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

OS="$(uname -s)"
case "$OS" in
  Darwin) LABEL="macOS" ;;
  Linux) LABEL="Linux" ;;
  *)
    echo "[오류] 이 스크립트는 macOS/Linux용입니다. Windows는 packaging/build.ps1 를 사용하세요." >&2
    exit 1
    ;;
esac

PY="${ROOT}/.venv/bin/python"
if [[ ! -x "$PY" ]]; then
  echo "[안내] 먼저 ./scripts/run-macos.sh 또는 ./scripts/run-linux.sh 로 환경을 준비하세요." >&2
  exit 1
fi

echo "[${LABEL}] PyInstaller로 DocuWizard 빌드…"
"$PY" -m pip install -e ".[dev,packaging]"
"$PY" -m PyInstaller packaging/docuwizard.spec --noconfirm --clean

echo ""
echo "완료: dist/DocuWizard/DocuWizard"
echo "참고: Ollama와 Tesseract는 별도 설치가 필요합니다."
