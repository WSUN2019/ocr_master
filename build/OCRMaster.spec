# -*- mode: python ; coding: utf-8 -*-
#
# PyInstaller spec for OCR Master
#
# Run from the repo root:
#   pyinstaller build/OCRMaster.spec
#
# Output: dist/OCRMaster/OCRMaster.exe  (folder mode — faster startup than onefile)

import glob
import os
import sys
from pathlib import Path

ROOT = Path(SPECPATH).parent   # repo root

block_cipher = None

# Explicitly bundle python3XX.dll and the VC++ runtime DLLs it depends on.
# PyInstaller sometimes omits vcruntime140.dll, which causes a "specified module
# could not be found" error on machines without Visual C++ Redist installed.
_search_dirs = [sys.exec_prefix, os.path.join(sys.exec_prefix, 'DLLs')]
_dll_patterns = ['python3*.dll', 'vcruntime*.dll', 'msvcp*.dll']
_extra_binaries = []
for _dir in _search_dirs:
    for _pat in _dll_patterns:
        for _dll in glob.glob(os.path.join(_dir, _pat)):
            _extra_binaries.append((_dll, '.'))

a = Analysis(
    [str(ROOT / 'app.py')],
    pathex=[str(ROOT)],
    binaries=_extra_binaries,
    datas=[
        # Ship the docs folder (readme images etc.) — no user data
        (str(ROOT / 'docs'), 'docs'),
        # Ship sample statement images so first-time users can try the app
        (str(ROOT / 'input_files' / 'Examples'), 'input_files/Examples'),
        # Ship the SaiminBank example template
        (str(ROOT / 'templates' / 'saiminbank.json'), 'templates'),
        # License and third-party notices — required for GPL / Apache 2.0 redistribution
        (str(ROOT / 'LICENSE'), '.'),
        (str(ROOT / 'NOTICES.txt'), '.'),
    ],
    hiddenimports=[
        # PyQt6 platform plugin loaded at runtime
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'PyQt6.sip',
        # pytesseract uses subprocess; make sure it's included
        'pytesseract',
        # pdfplumber — imported at module level in batch/extract widgets
        'pdfplumber',
        'pdfminer',
        'pdfminer.high_level',
        'pdfminer.layout',
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
    excludes=['tkinter', 'matplotlib', 'scipy', 'notebook', 'pyarrow'],
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
    upx_exclude=['python3*.dll', 'vcruntime*.dll', 'msvcp*.dll'],
    name='OCRMaster',
)
