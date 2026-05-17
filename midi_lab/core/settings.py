# -*- coding: utf-8 -*-
"""アプリケーション設定（最近使ったファイル等）。"""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QSettings

_ORG = "MurataLab"
_APP = "MIDIChordLab"
_MAX_RECENT = 8


def _settings() -> QSettings:
    return QSettings(_ORG, _APP)


def recent_files() -> list[str]:
    raw = _settings().value("recent_files", [])
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    for p in raw:
        s = str(p)
        if Path(s).is_file() and s not in out:
            out.append(s)
    return out[:_MAX_RECENT]


def add_recent_file(path: str) -> None:
    p = str(Path(path).resolve())
    items = [x for x in recent_files() if x != p]
    items.insert(0, p)
    _settings().setValue("recent_files", items[:_MAX_RECENT])


def fullscreen_default() -> bool:
    return bool(_settings().value("fullscreen_default", True))


def set_fullscreen_default(on: bool) -> None:
    _settings().setValue("fullscreen_default", on)
