"""PyInstaller / 配布実行時のランタイム初期化。"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from midi_lab.branding import APP_DATA_DIR_NAME


def _frozen_win_prepare_dll_search() -> None:
    """配布版: 同梱 Qt を最優先（レビュー: app.py と重複していた DLL 初期化を一本化）。"""
    if not getattr(sys, "frozen", False) or not sys.platform.startswith("win"):
        return

    meipass = getattr(sys, "_MEIPASS", "")
    if not meipass:
        return

    qt_bin = os.path.join(meipass, "PyQt6", "Qt6", "bin")
    if not os.path.isdir(qt_bin):
        return

    try:
        os.add_dll_directory(qt_bin)
        os.add_dll_directory(meipass)
    except (AttributeError, OSError):
        pass

    blocked = {os.path.normcase(meipass), os.path.normcase(qt_bin)}
    rest = [
        p
        for p in os.environ.get("PATH", "").split(os.pathsep)
        if p and os.path.normcase(p) not in blocked
    ]
    os.environ["PATH"] = os.pathsep.join([qt_bin, meipass, *rest])


def bootstrap_frozen() -> None:
    if not getattr(sys, "frozen", False):
        return
    _frozen_win_prepare_dll_search()
    if sys.platform == "win32":
        meipass = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
        qt_bin = meipass / "PyQt6" / "Qt6" / "bin"
        if qt_bin.is_dir():
            os.add_dll_directory(str(qt_bin))
    local = os.environ.get("LOCALAPPDATA")
    app_dir = Path(local) / APP_DATA_DIR_NAME if local else Path.home() / ".midi_chord_viewer"
    mpl_dir = app_dir / "matplotlib"
    mpl_dir.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("MPLCONFIGDIR", str(mpl_dir))
