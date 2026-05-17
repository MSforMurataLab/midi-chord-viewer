# -*- coding: utf-8 -*-
"""バックグラウンドでの起動時モジュール読込（Qt/matplotlib はメインスレッド専用）。"""
from __future__ import annotations

from PyQt6.QtCore import QThread, pyqtSignal


class StartupLoader(QThread):
    """music21 / mido 等の重い import のみワーカーで実行。"""

    stage_changed = pyqtSignal(str)
    progress = pyqtSignal(int)
    ready = pyqtSignal()
    failed = pyqtSignal(str)

    def run(self) -> None:
        try:
            self.stage_changed.emit("音楽理論エンジン (music21) を読み込んでいます…")
            self.progress.emit(25)
            import music21  # noqa: F401

            self.progress.emit(55)
            self.stage_changed.emit("MIDI 再生モジュールを準備しています…")
            import mido  # noqa: F401

            self.progress.emit(85)
            self.stage_changed.emit("最終準備中…")
            self.progress.emit(100)
            self.stage_changed.emit("起動完了")
            self.ready.emit()
        except Exception as e:
            self.failed.emit(str(e))
