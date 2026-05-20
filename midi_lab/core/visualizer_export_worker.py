# -*- coding: utf-8 -*-
"""ビジュアライザ動画書き出しのバックグラウンドワーカー。"""
from __future__ import annotations

import traceback

from PyQt6.QtCore import QThread, pyqtSignal

from midi_lab.visualizer.engine import VisualizerEngine
from midi_lab.visualizer.export import export_png_sequence, export_video


class VideoExportWorker(QThread):
    progress = pyqtSignal(int, int)
    completed = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(
        self,
        path: str,
        engine: VisualizerEngine,
        fps: int,
        width: int,
        height: int,
        png_sequence: bool,
        parent=None,
    ):
        super().__init__(parent)
        self._path = path
        self._engine = engine
        self._fps = fps
        self._width = width
        self._height = height
        self._png_sequence = bool(png_sequence)

    def run(self) -> None:
        try:
            if self.isInterruptionRequested():
                return

            def on_progress(cur: int, total: int) -> None:
                if not self.isInterruptionRequested():
                    self.progress.emit(cur, total)

            if self._png_sequence:
                out = export_png_sequence(
                    self._engine,
                    self._path,
                    fps=self._fps,
                    width=self._width,
                    height=self._height,
                    transparent=True,
                    progress=on_progress,
                )
            else:
                out = export_video(
                    self._engine,
                    self._path,
                    fps=self._fps,
                    width=self._width,
                    height=self._height,
                    progress=on_progress,
                )
            if not self.isInterruptionRequested():
                self.completed.emit(str(out))
        except Exception:
            self.failed.emit(traceback.format_exc())
