# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec: dist/MIDIChordViewer/MIDIChordViewer.exe"""

from PyInstaller.utils.hooks import collect_all

block_cipher = None

datas_m21, binaries_m21, hidden_m21 = collect_all("music21")
datas_mpl, binaries_mpl, hidden_mpl = collect_all("matplotlib")

a = Analysis(
    ["app.py"],
    pathex=[],
    binaries=binaries_m21 + binaries_mpl,
    datas=datas_m21 + datas_mpl,
    hiddenimports=hidden_m21
    + hidden_mpl
    + [
        "matplotlib.backends.backend_qtagg",
        "matplotlib.backends.backend_qt",
        "PyQt6.QtCore",
        "PyQt6.QtGui",
        "PyQt6.QtWidgets",
        "music21.converter",
        "music21.midi",
        "music21.graph",
        "music21.harmony",
        "music21.roman",
        "mido",
        "mido.backends.rtmidi",
        "piano_keyboard",
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
    name="MIDIChordViewer",
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
    name="MIDIChordViewer",
)
