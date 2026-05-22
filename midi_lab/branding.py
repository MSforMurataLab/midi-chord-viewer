# -*- coding: utf-8 -*-
"""製品名・データディレクトリ名の一元化（レビュー: 命名のブレをドキュメント化）。"""
from __future__ import annotations

from midi_lab import __version__

APP_DISPLAY_NAME = "MIDI Chord Lab"
# QSettings の第2引数 — 既存ユーザーの設定キーを壊さないため変更しない
APP_SETTINGS_NAME = "MIDIChordLab"
APP_SETTINGS_ORG = "MurataLab"
# %LOCALAPPDATA% 以下 — ログ・matplotlib 設定（既存パスを維持）
APP_DATA_DIR_NAME = "MIDIChordViewer"
EXE_BASENAME = "MIDIChordViewer"
APP_VERSION = __version__
