# -*- coding: utf-8 -*-
"""
MIDI Chord Lab — 和声解析・編集ワークステーション

開発時: python app.py [曲.mid]
配布版: dist/MIDIChordViewer/MIDIChordViewer.exe [曲.mid]
関連付け: exe --register-midi-association または ファイルメニューから登録
"""

from midi_lab.main import run

if __name__ == "__main__":
    raise SystemExit(run())
