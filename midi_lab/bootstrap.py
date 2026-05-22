"""PyInstaller / 配布実行時のランタイム初期化。"""
from __future__ import annotations

import os
import sys
from pathlib import Path


def bootstrap_frozen() -> None:
    if not getattr(sys, "frozen", False):
        return
    if sys.platform == "win32":
        meipass = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
        qt_bin = meipass / "PyQt6" / "Qt6" / "bin"
        if qt_bin.is_dir():
            os.add_dll_directory(str(qt_bin))
    local = os.environ.get("LOCALAPPDATA")
    app_dir = Path(local) / "MIDIChordViewer" if local else Path.home() / ".midi_chord_viewer"
    mpl_dir = app_dir / "matplotlib"
    mpl_dir.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("MPLCONFIGDIR", str(mpl_dir))
