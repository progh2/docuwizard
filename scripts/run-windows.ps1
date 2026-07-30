# DocuWizard launcher for Windows (PowerShell)
# Usage:  .\scripts\run-windows.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$venvPython = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Host "[안내] 가상환경(.venv)을 만들고 패키지를 설치합니다…"
    if (Get-Command py -ErrorAction SilentlyContinue) {
        py -3 -m venv .venv
    } elseif (Get-Command python -ErrorAction SilentlyContinue) {
        python -m venv .venv
    } else {
        throw "Python 3이 PATH에 없습니다. https://www.python.org/downloads/ 에서 설치하세요."
    }
    & $venvPython -m pip install --upgrade pip
    & $venvPython -m pip install -e ".[dev]"
}

Write-Host "DocuWizard 시작…"
& $venvPython -m docuwizard
exit $LASTEXITCODE
