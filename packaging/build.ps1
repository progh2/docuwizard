# Build a onedir DocuWizard bundle with PyInstaller (Windows).
# Usage:  .\packaging\build.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Error "Create a venv first: python -m venv .venv"
}

Write-Host "Installing package + PyInstaller…"
.venv\Scripts\python -m pip install -e ".[dev]" "pyinstaller>=6.0"

Write-Host "Building…"
.venv\Scripts\python -m PyInstaller packaging\docuwizard.spec --noconfirm --clean

Write-Host ""
Write-Host "Done. Run: dist\DocuWizard\DocuWizard.exe"
Write-Host "Note: Ollama and Tesseract must still be installed separately on the machine."
