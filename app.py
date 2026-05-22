# -*- coding: utf-8 -*-
"""
MIDI Chord Lab — 和声解析・編集ワークステーション

開発時: python app.py [曲.mid]
配布版: dist/MIDIChordViewer/MIDIChordViewer.exe [曲.mid]
"""
from __future__ import annotations

from midi_lab.bootstrap import bootstrap_frozen

# レビュー: Win32 DLL 検索は bootstrap_frozen に集約（二重初期化を廃止）
bootstrap_frozen()

from midi_lab.main import run

if __name__ == "__main__":
    raise SystemExit(run())
