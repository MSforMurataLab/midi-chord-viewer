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


def default_tempo() -> int:
    try:
        v = int(_settings().value("default_tempo", 120))
        return max(40, min(208, v))
    except (TypeError, ValueError):
        return 120


def set_default_tempo(bpm: int) -> None:
    _settings().setValue("default_tempo", max(40, min(208, int(bpm))))


def assist_panel_visible_default() -> bool:
    return bool(_settings().value("assist_panel_visible", True))


def set_assist_panel_visible_default(on: bool) -> None:
    _settings().setValue("assist_panel_visible", on)


def selected_soundfont() -> str:
    """選択中 SoundFont（soundfonts からの相対パス、または絶対パス）。"""
    raw = _settings().value("selected_soundfont", "")
    if raw:
        return str(raw).strip()
    legacy = _settings().value("soundfont_path", "")
    return str(legacy).strip() if legacy else ""


def set_selected_soundfont(key: str) -> None:
    _settings().setValue("selected_soundfont", str(key).strip())


def soundfont_path() -> str:
    """後方互換 — selected_soundfont と同じ。"""
    return selected_soundfont()


def set_soundfont_path(path: str) -> None:
    set_selected_soundfont(path)
