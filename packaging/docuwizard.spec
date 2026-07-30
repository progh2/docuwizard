# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for DocuWizard (issue #35).

Build (from repo root, with venv activated)::

    pip install -e ".[dev]" pyinstaller
    pyinstaller packaging/docuwizard.spec

Output: dist/DocuWizard/DocuWizard.exe (Windows) or dist/DocuWizard/DocuWizard
"""

from PyInstaller.utils.hooks import collect_all

block_cipher = None

pyside_datas, pyside_binaries, pyside_hidden = collect_all("PySide6")

a = Analysis(
    ["../src/docuwizard/__main__.py"],
    pathex=["../src"],
    binaries=pyside_binaries,
    datas=pyside_datas,
    hiddenimports=[
        *pyside_hidden,
        "pypdf",
        "docx",
        "openpyxl",
        "PIL",
        "pytesseract",
        "platformdirs",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="DocuWizard",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="DocuWizard",
)
