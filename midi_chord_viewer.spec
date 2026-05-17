# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec: dist/MIDIChordViewer/MIDIChordViewer.exe"""

from PyInstaller.utils.hooks import collect_all, collect_dynamic_libs

block_cipher = None

datas_m21, binaries_m21, hidden_m21 = collect_all("music21")
datas_mpl, binaries_mpl, hidden_mpl = collect_all("matplotlib")
binaries_sd = collect_dynamic_libs("sounddevice")
_app_assets = [("image.png", ".")]

a = Analysis(
    ["app.py"],
    pathex=[],
    binaries=binaries_m21 + binaries_mpl + binaries_sd,
    datas=datas_m21 + datas_mpl + _app_assets,
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
        "midi_lab",
        "midi_lab.bootstrap",
        "midi_lab.resources",
        "midi_lab.core",
        "midi_lab.core.harmony",
        "midi_lab.core.chord_rules",
        "midi_lab.core.score",
        "midi_lab.core.playback",
        "midi_lab.core.plotting",
        "midi_lab.ui",
        "midi_lab.ui.theme",
        "midi_lab.ui.main_window",
        "midi_lab.ui.widgets",
        "midi_lab.ui.widgets.piano_keyboard",
        "midi_lab.ui.widgets.timeline_panel",
        "midi_lab.ui.widgets.timeline_delegate",
        "midi_lab.ui.widgets.welcome_page",
        "midi_lab.ui.widgets.sidebar",
        "midi_lab.ui.widgets.loading_overlay",
        "midi_lab.ui.splash",
        "midi_lab.ui.startup",
        "midi_lab.core.settings",
        "midi_lab.core.load_worker",
        "midi_lab.core.launch_args",
        "midi_lab.core.file_association",
        "sounddevice",
        "numpy",
        "midi_lab.diagnostics",
        "midi_lab.ui.design_tokens",
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
    icon="app.ico",
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
