# -*- mode: python ; coding: utf-8 -*-
#
# PyInstaller spec for OCR Master
#
# Run from the repo root:
#   pyinstaller build/OCRMaster.spec
#
# Output: dist/OCRMaster/OCRMaster.exe  (folder mode — faster startup than onefile)

import sys
from pathlib import Path

ROOT = Path(SPECPATH).parent   # repo root

block_cipher = None

a = Analysis(
    [str(ROOT / 'app.py')],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        # Ship the docs folder (readme images etc.) — no user data
        (str(ROOT / 'docs'), 'docs'),
    ],
    hiddenimports=[
        # PyQt6 platform plugin loaded at runtime
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'PyQt6.sip',
        # pytesseract uses subprocess; make sure it's included
        'pytesseract',
        # pandas optional backends
        'pandas',
        'pandas._libs.tslibs.np_datetime',
        'pandas._libs.tslibs.nattype',
        'pandas._libs.tslibs.timedeltas',
        # fitz (PyMuPDF)
        'fitz',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'scipy', 'notebook'],
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
    name='OCRMaster',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,          # no console window
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon='build/icon.ico',  # uncomment and supply icon.ico to add an app icon
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='OCRMaster',
)
