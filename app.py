# -*- coding: utf-8 -*-
"""
MIDI Chord Lab — 和声解析・編集ワークステーション

開発時: python app.py [曲.mid]
配布版: dist/MIDIChordViewer/MIDIChordViewer.exe [曲.mid]
"""
from __future__ import annotations

import os
import sys


def _frozen_win_prepare_dll_search() -> None:
    """配布版: 同梱 Qt を最優先（PATH 上の別 Qt / glib より先に読み込む）。"""
    if not getattr(sys, "frozen", False) or not sys.platform.startswith("win"):
        return

    import ctypes

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


_frozen_win_prepare_dll_search()

from midi_lab.main import run

if __name__ == "__main__":
    raise SystemExit(run())
