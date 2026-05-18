# -*- coding: utf-8 -*-
"""MIDI ファイルのバックグラウンド読込。"""
from __future__ import annotations

import traceback
from dataclasses import dataclass
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal

from midi_lab.core.harmony import detect_key_for_score
from midi_lab.core.note_events import NoteEvent, collect_note_events
from midi_lab.core.score import build_flat_work_stream, load_score


@dataclass
class LoadedScore:
    path: str
    score: object
    work_flat: object
    key_text: str
    key_obj: object | None
    note_events: tuple[NoteEvent, ...]


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
            notes = tuple(collect_note_events(score))
            payload = LoadedScore(
                path=self._path,
                score=score,
                work_flat=work,
                key_text=ktxt,
                key_obj=kobj,
                note_events=notes,
            )
            self.completed.emit(payload)
        except Exception:
            self.failed.emit(traceback.format_exc())
