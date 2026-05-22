# -*- coding: utf-8 -*-
"""MIDI ファイルのバックグラウンド読込。"""
from __future__ import annotations

import traceback
from dataclasses import dataclass
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal

# progress 表示後に UI スレッドへ制御を返す短い待機（ミリ秒）
_PROGRESS_YIELD_MS = 15

from midi_lab.core.harmony import detect_key_for_score
from midi_lab.core.midi_tempo import detect_score_bpm
from midi_lab.core.note_events import NoteEvent, collect_note_events
from midi_lab.core.score import build_flat_work_stream, build_playback_timeline, load_score
from midi_lab.core.settings import default_tempo
from midi_lab.core.soundfont_preload import try_preload_playback_audio


@dataclass
class LoadedScore:
    path: str
    score: object
    work_flat: object
    key_text: str
    key_obj: object | None
    note_events: tuple[NoteEvent, ...]
    bpm: int


class MidiLoadWorker(QThread):
    progress = pyqtSignal(str)
    completed = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, path: str, parent=None):
        super().__init__(parent)
        self._path = path

    def run(self) -> None:
        try:
            self.progress.emit("MIDI を解析しています…")
            score = load_score(self._path)
            self.progress.emit("和声トラックを構築しています…")
            work = build_flat_work_stream(score)
            self.progress.emit("キーを検出しています…")
            ktxt, kobj = detect_key_for_score(score)
            if kobj is None:
                ktxt, kobj = detect_key_for_score(work)
            self.progress.emit("パフォーマンスデータを抽出しています…")
            if self.isInterruptionRequested():
                return
            QThread.msleep(_PROGRESS_YIELD_MS)
            notes = tuple(collect_note_events(score))
            if self.isInterruptionRequested():
                return
            bpm = detect_score_bpm(score, default_tempo())
            if self.isInterruptionRequested():
                return
            self.progress.emit("再生音声を準備しています（SoundFont）…")
            QThread.msleep(_PROGRESS_YIELD_MS)
            harmony_tl = build_playback_timeline(work)
            if not self.isInterruptionRequested():
                try_preload_playback_audio(
                    list(notes),
                    harmony_tl,
                    bpm,
                    stop_check=self.isInterruptionRequested,
                )
            payload = LoadedScore(
                path=self._path,
                score=score,
                work_flat=work,
                key_text=ktxt,
                key_obj=kobj,
                note_events=notes,
                bpm=bpm,
            )
            self.completed.emit(payload)
        except Exception:
            self.failed.emit(traceback.format_exc())
