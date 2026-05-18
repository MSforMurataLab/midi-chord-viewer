# -*- coding: utf-8 -*-
"""分析グラフ（ピアノロール・パフォーマンス等）のバックグラウンド生成。"""
from __future__ import annotations

import traceback
from dataclasses import dataclass

from matplotlib.figure import Figure
from PyQt6.QtCore import QThread, pyqtSignal

from midi_lab.core.functional_harmony import functional_label
from midi_lab.core.harmony import voice_leading_label
from midi_lab.core.note_events import NoteEvent
from midi_lab.core.performance_analytics import (
    analyze_performance,
    build_performance_dashboard_figure,
    report_summary_text,
)
from midi_lab.core.pianoroll_plot import build_pianoroll_figure_from_notes
from midi_lab.core.score import collect_harmony_events
from midi_lab.core.voice_leading import analyze_voice_leading, format_motions


@dataclass(frozen=True)
class AnalysisResult:
    pianoroll_figure: Figure | None
    perf_figure: Figure | None
    voice_steps: tuple
    voice_rows: tuple[tuple, ...]
    voice_summary: str


class AnalysisBuildWorker(QThread):
    progress = pyqtSignal(str)
    completed = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(
        self,
        note_events: list[NoteEvent],
        work_flat: object,
        key_obj: object | None,
        parent=None,
    ):
        super().__init__(parent)
        self._note_events = note_events
        self._work_flat = work_flat
        self._key_obj = key_obj

    def run(self) -> None:
        try:
            events = self._note_events
            if self.isInterruptionRequested():
                return

            self.progress.emit("声部進行を解析しています…")
            harmony = collect_harmony_events(self._work_flat)
            voice_steps = analyze_voice_leading(
                harmony,
                lambda el: voice_leading_label(el, self._key_obj),
            )

            if self.isInterruptionRequested():
                return

            self.progress.emit("パフォーマンス統計を計算しています…")
            report = analyze_performance(events)

            if self.isInterruptionRequested():
                return

            self.progress.emit("ピアノロールを描画中…")
            pr_fig = build_pianoroll_figure_from_notes(events) if events else None

            if self.isInterruptionRequested():
                return

            self.progress.emit("パフォーマンス分析グラフを描画中…")
            perf_fig = (
                build_performance_dashboard_figure(events, report) if events else None
            )

            if self.isInterruptionRequested():
                return
            vl_rows = tuple(
                (
                    s.index,
                    s.from_label,
                    s.to_label,
                    format_motions(s.motions),
                    s.motion_kind,
                    s.total_motion,
                )
                for s in voice_steps
            )
            parallel = sum(1 for s in voice_steps if s.motion_kind == "順行")
            contrary = sum(1 for s in voice_steps if s.motion_kind == "逆行")
            summary = (
                f"和音遷移 {len(voice_steps)} 件 · 順行 {parallel} · 逆行 {contrary} · "
                f"{report_summary_text(report)}"
            )

            self.completed.emit(
                AnalysisResult(
                    pianoroll_figure=pr_fig,
                    perf_figure=perf_fig,
                    voice_steps=tuple(voice_steps),
                    voice_rows=vl_rows,
                    voice_summary=summary,
                )
            )
        except Exception:
            self.failed.emit(traceback.format_exc())
