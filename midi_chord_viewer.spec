# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec: dist/MIDIChordViewer/MIDIChordViewer.exe"""

import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_dynamic_libs, copy_metadata

block_cipher = None

_binaries_midi_viz = []
_sp = Path(sys.prefix) / "Lib" / "site-packages"
for _name in ("midi_viz.pyd", "midi_viz.dll"):
    _p = _sp / _name
    if _p.is_file():
        _binaries_midi_viz.append((str(_p), "."))
        break

datas_m21, binaries_m21, hidden_m21 = collect_all("music21")
datas_mpl, binaries_mpl, hidden_mpl = collect_all("matplotlib")
datas_io, binaries_io, hidden_io = collect_all("imageio_ffmpeg")
datas_imageio_meta = copy_metadata("imageio")
binaries_sd = collect_dynamic_libs("sounddevice")
_app_assets = [("image.png", ".")]
_spec_dir = Path(SPECPATH)
_sf_datas: list = []
# FluidSynth は datas のみ（binaries にすると依存 DLL が _internal 直下に展開され Qt と競合する）
_fs_bin = _spec_dir / "assets" / "fluidsynth" / "bin"
if _fs_bin.is_dir():
    for _f in _fs_bin.iterdir():
        if _f.is_file():
            _sf_datas.append((str(_f), "assets/fluidsynth/bin"))
_sf_dir = _spec_dir / "assets" / "soundfonts"
if _sf_dir.is_dir():
    for _f in _sf_dir.rglob("*.sf2"):
        if _f.is_file():
            _rel_parent = _f.parent.relative_to(_sf_dir)
            _dest = (
                str(Path("assets/soundfonts") / _rel_parent)
                if str(_rel_parent) != "."
                else "assets/soundfonts"
            )
            _sf_datas.append((str(_f), _dest))

# ビルド時に依存解析で _internal 直下へコピーされる FluidSynth DLL（Qt と競合）
_FS_DLL_NAMES = {
    "libfluidsynth-3.dll",
    "libglib-2.0-0.dll",
    "libgthread-2.0-0.dll",
    "libgobject-2.0-0.dll",
    "libgomp-1.dll",
    "libgcc_s_sjlj-1.dll",
    "libsndfile-1.dll",
    "libstdc++-6.dll",
    "libintl-8.dll",
    "libwinpthread-1.dll",
    "libinstpatch-2.dll",
    "fluidsynth.exe",
}


def _drop_stray_fluidsynth_binaries(binaries):
    kept = []
    for entry in binaries:
        dest = str(entry[0]).replace("\\", "/")
        src = str(entry[1] if len(entry) > 1 else "").replace("\\", "/")
        name = Path(dest).name.lower()
        if name in _FS_DLL_NAMES:
            if "assets/fluidsynth" in dest.lower():
                kept.append(entry)
            continue
        if "fluidsynth" in src.lower() and name.endswith(".dll"):
            continue
        kept.append(entry)
    return kept


def _drop_mismatched_icu_binaries(binaries):
    """Anaconda ICU 73 は Qt6Core と ABI 不一致（UCNV_*_73）— 同梱しない。"""
    kept = []
    for entry in binaries:
        name = Path(entry[0]).name.lower()
        if not name.startswith("icu") or not name.endswith(".dll"):
            kept.append(entry)
            continue
        src = str(entry[1] if len(entry) > 1 else "").replace("\\", "/").lower()
        if "pyqt6" in src or "qt6" in src:
            kept.append(entry)
            continue
        continue
    return kept


a = Analysis(
    ["app.py"],
    pathex=[],
    binaries=binaries_m21 + binaries_mpl + binaries_io + binaries_sd + _binaries_midi_viz,
    datas=datas_m21 + datas_mpl + datas_io + datas_imageio_meta + _app_assets + _sf_datas,
    hiddenimports=hidden_m21
    + hidden_mpl
    + hidden_io
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
        "midi_lab.core.note_events",
        "midi_lab.core.pianoroll_plot",
        "midi_lab.core.performance_analytics",
        "mpl_toolkits.axes_grid1",
        "midi_lab.core.analysis_build_worker",
        "midi_lab.core.analysis_report",
        "midi_lab.core.functional_harmony",
        "midi_lab.core.voice_leading",
        "midi_lab.core.launch_args",
        "midi_lab.core.file_association",
        "midi_lab.ui.widgets.voice_leading_panel",
        "midi_lab.ui.widgets.visualizer_panel",
        "midi_lab.visualizer",
        "midi_lab.visualizer.engine",
        "midi_lab.visualizer.export",
        "midi_lab.visualizer.ffmpeg_util",
        "midi_lab.core.soundfont_player",
        "midi_lab.core.soundfont_midi",
        "midi_lab.core.soundfont_preload",
        "midi_lab.core.playback_schedule",
        "midi_lab.visualizer.midi_input",
        "midi_lab.visualizer.styles",
        "midi_viz",
        "midi_lab.visualizer.canvas_factory",
        "midi_lab.visualizer.widget_rust",
        "midi_lab.visualizer.rust_bridge",
        "midi_lab.core.visualizer_export_worker",
        "imageio",
        "imageio_ffmpeg",
        "imageio.plugins.ffmpeg",
        "sounddevice",
        "numpy",
        "midi_lab.diagnostics",
        "midi_lab.ui.design_tokens",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[str(_spec_dir / "runtime_hooks" / "pyi_rth_midi_lab_dll.py")],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

a.binaries = _drop_stray_fluidsynth_binaries(a.binaries)
a.binaries = _drop_mismatched_icu_binaries(a.binaries)

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
    upx=False,
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
    upx=False,
    name="MIDIChordViewer",
)
