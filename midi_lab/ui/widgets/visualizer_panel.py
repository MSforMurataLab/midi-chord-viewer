# -*- coding: utf-8 -*-
"""中央ワークスペース用 MIDI ビジュアライザ（QPainter / Strategy）。"""
from __future__ import annotations

import copy
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from midi_lab.core.note_events import NoteEvent
from midi_lab.visualizer.canvas_factory import backend_name, create_visualizer_canvas
from midi_lab.visualizer.engine import VisualizerEngine
from midi_lab.visualizer.midi_input import MidiInputWorker, list_input_ports
from midi_lab.visualizer.styles import STYLES, STYLE_ORDER
from midi_lab.visualizer.timeline import ql_to_sec
from midi_lab.core.visualizer_export_worker import VideoExportWorker

VIDEO_FILTER = "動画 (*.mp4 *.mov *.avi);;MP4 (*.mp4);;QuickTime (*.mov);;AVI (*.avi)"
PNG_FILTER = "PNG 連番フォルダ"


class VisualizerPanel(QWidget):
    """Transport 同期・スタイル即時切替・MIDI In・動画書き出し。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._events: list[NoteEvent] = []
        self._export_worker: VideoExportWorker | None = None
        self._midi_in: MidiInputWorker | None = None
        self._live_ql = 0.0
        self._playback_active = False
        self._build_ui()
        self.clear_data()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        toolbar = QFrame()
        toolbar.setObjectName("VisualizerToolbar")
        tb = QVBoxLayout(toolbar)
        tb.setContentsMargins(14, 10, 14, 10)
        tb.setSpacing(8)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("スタイル"))
        self._style_combo = QComboBox()
        for sid in STYLE_ORDER:
            self._style_combo.addItem(STYLES[sid].label, sid)
        self._style_combo.currentIndexChanged.connect(self._on_style_changed)
        row1.addWidget(self._style_combo, stretch=2)

        row1.addWidget(QLabel("表示窓"))
        self._window_spin = QSpinBox()
        self._window_spin.setRange(4, 32)
        self._window_spin.setValue(8)
        self._window_spin.setSuffix(" 秒")
        self._window_spin.valueChanged.connect(self._sync_params)
        row1.addWidget(self._window_spin)

        row1.addWidget(QLabel("速度"))
        self._speed_spin = QDoubleSpinBox()
        self._speed_spin.setRange(0.25, 4.0)
        self._speed_spin.setSingleStep(0.1)
        self._speed_spin.setValue(1.0)
        self._speed_spin.valueChanged.connect(self._sync_params)
        row1.addWidget(self._speed_spin)

        row1.addWidget(QLabel("解像度"))
        self._res_combo = QComboBox()
        self._res_combo.addItem("1280×720", (1280, 720))
        self._res_combo.addItem("1920×1080", (1920, 1080))
        row1.addWidget(self._res_combo)

        row1.addWidget(QLabel("FPS"))
        self._fps_spin = QSpinBox()
        self._fps_spin.setRange(12, 60)
        self._fps_spin.setValue(30)
        row1.addWidget(self._fps_spin)
        tb.addLayout(row1)

        row2 = QHBoxLayout()
        self._track_colors = QCheckBox("トラック別色")
        self._track_colors.setChecked(True)
        self._track_colors.toggled.connect(self._sync_params)
        row2.addWidget(self._track_colors)

        row2.addWidget(QLabel("パーティクル"))
        self._particle_slider = QSlider(Qt.Orientation.Horizontal)
        self._particle_slider.setRange(0, 200)
        self._particle_slider.setValue(100)
        self._particle_slider.valueChanged.connect(self._sync_params)
        row2.addWidget(self._particle_slider, stretch=1)

        row2.addWidget(QLabel("MIDI In"))
        self._midi_port = QComboBox()
        self._midi_port.setMinimumWidth(140)
        self._refresh_midi_ports()
        row2.addWidget(self._midi_port)
        self._btn_midi = QPushButton("Live")
        self._btn_midi.setCheckable(True)
        self._btn_midi.toggled.connect(self._toggle_midi_in)
        row2.addWidget(self._btn_midi)
        tb.addLayout(row2)

        row3 = QHBoxLayout()
        self._time_label = QLabel("0:00 / 0:00")
        self._time_label.setObjectName("VisualizerTime")
        row3.addWidget(self._time_label)
        self._scrub = QSlider(Qt.Orientation.Horizontal)
        self._scrub.setRange(0, 1000)
        self._scrub.valueChanged.connect(self._on_scrub)
        row3.addWidget(self._scrub, stretch=1)
        hint = QLabel("Transport 再生と同期")
        hint.setObjectName("PanelHint")
        row3.addWidget(hint)
        self._btn_export = QPushButton("動画を書き出し…")
        self._btn_export.setObjectName("BtnPrimary")
        self._btn_export.clicked.connect(self.export_video_dialog)
        row3.addWidget(self._btn_export)
        self._btn_png = QPushButton("PNG連番…")
        self._btn_png.setObjectName("BtnSecondary")
        self._btn_png.clicked.connect(self.export_png_dialog)
        row3.addWidget(self._btn_png)
        tb.addLayout(row3)

        self._progress = QProgressBar()
        self._progress.setVisible(False)
        tb.addWidget(self._progress)
        root.addWidget(toolbar)

        self._canvas_container = QWidget()
        self._canvas_layout = QVBoxLayout(self._canvas_container)
        self._canvas_layout.setContentsMargins(0, 0, 0, 0)
        self._canvas = create_visualizer_canvas(self._canvas_container)
        self._canvas_layout.addWidget(self._canvas)
        self._py_engine = VisualizerEngine()
        root.addWidget(self._canvas_container, stretch=1)

    def on_tab_activated(self) -> None:
        """MIDIビジュアライザタブが選択されたとき。"""
        if hasattr(self._canvas, "notify_tab_shown"):
            self._canvas.notify_tab_shown()

    def _engine(self) -> VisualizerEngine:
        return self._py_engine

    def _refresh_midi_ports(self) -> None:
        self._midi_port.clear()
        ports = list_input_ports()
        if not ports:
            self._midi_port.addItem("（デバイスなし）", "")
        else:
            for p in ports:
                self._midi_port.addItem(p, p)

    def _sync_params(self) -> None:
        e = self._engine()
        e.window_sec = float(self._window_spin.value())
        e.speed = float(self._speed_spin.value())
        e.track_colors = self._track_colors.isChecked()
        e.particle_amount = self._particle_slider.value() / 100.0
        if hasattr(self._canvas, "set_params"):
            self._canvas.set_params(
                bpm=e.bpm,
                window_sec=e.window_sec,
                speed=e.speed,
                track_colors=e.track_colors,
                particle_amount=e.particle_amount,
            )
        self._canvas.update()

    def _on_style_changed(self) -> None:
        sid = self._style_combo.currentData()
        if sid:
            self._engine().set_style(str(sid))
            if hasattr(self._canvas, "set_style"):
                self._canvas.set_style(str(sid))
            self._canvas.update()

    def set_score_data(self, events: list[NoteEvent], bpm: float) -> None:
        self._events = list(events)
        e = self._py_engine
        e.load_events(self._events)
        e.bpm = max(20.0, float(bpm))
        if hasattr(self._canvas, "load_events"):
            self._canvas.load_events(self._events)
            self._canvas.set_params(
                bpm=e.bpm,
                window_sec=e.window_sec,
                speed=e.speed,
                track_colors=e.track_colors,
                particle_amount=e.particle_amount,
            )
        self._sync_params()
        has = bool(self._events)
        self._canvas.set_has_data(has)
        self._scrub.setEnabled(has)
        for w in (
            self._style_combo,
            self._window_spin,
            self._speed_spin,
            self._res_combo,
            self._fps_spin,
            self._track_colors,
            self._particle_slider,
            self._btn_export,
            self._btn_png,
        ):
            w.setEnabled(bool(self._events))
        if self._events:
            self._scrub.setValue(0)
            e.set_time_sec(0.0)
            self._update_time_label(0.0)
            QTimer.singleShot(0, self._canvas.update)
            QTimer.singleShot(250, self._canvas.update)

    def clear_data(self) -> None:
        self._stop_midi_in()
        self._events = []
        self._engine().clear()
        self._canvas.set_has_data(False)
        self._canvas.set_animating(False)
        self._playback_active = False
        for w in (
            self._style_combo,
            self._window_spin,
            self._speed_spin,
            self._res_combo,
            self._fps_spin,
            self._track_colors,
            self._particle_slider,
            self._scrub,
            self._btn_export,
            self._btn_png,
            self._btn_midi,
        ):
            w.setEnabled(False)
        self._time_label.setText("—")

    def set_playback_active(self, active: bool) -> None:
        self._playback_active = active
        self._scrub.setEnabled(bool(self._events) and not active)
        self._canvas.set_animating(active and bool(self._events))

    def update_playback_time(self, t_sec: float) -> None:
        if not self._events:
            return
        if t_sec < 0:
            self.set_playback_active(False)
            return
        self.set_playback_active(True)
        e = self._engine()
        e.set_time_sec(t_sec)
        if hasattr(self._canvas, "set_time_ql"):
            from midi_lab.visualizer.timeline import sec_to_ql

            self._canvas.set_time_ql(sec_to_ql(t_sec, e.bpm))
        dur = ql_to_sec(e.timeline.duration_ql, e.bpm)
        self._set_scrub_from_sec(min(t_sec, dur))

    def on_playback_stopped(self) -> None:
        self.set_playback_active(False)
        self._canvas.update()

    def forward_playback_midi(self, status: int, data1: int, data2: int) -> None:
        """再生中の note on/off を Rust ビジュアライザへ転送。"""
        if not hasattr(self._canvas, "send_midi_event"):
            return
        import time

        ts = int(time.perf_counter() * 1_000_000)
        self._canvas.send_midi_event(status, data1, data2, ts)

    def _duration_sec(self) -> float:
        e = self._engine()
        return ql_to_sec(e.timeline.duration_ql, e.bpm) if self._events else 0.0

    def _set_scrub_from_sec(self, t_sec: float) -> None:
        dur = self._duration_sec()
        if dur <= 0:
            return
        self._scrub.blockSignals(True)
        self._scrub.setValue(int(max(0.0, min(1.0, t_sec / dur)) * 1000))
        self._scrub.blockSignals(False)
        self._update_time_label(t_sec)

    def _update_time_label(self, t_sec: float) -> None:
        dur = self._duration_sec()

        def fmt(s: float) -> str:
            m = int(s) // 60
            return f"{m}:{int(s) % 60:02d}"

        self._time_label.setText(f"{fmt(t_sec)} / {fmt(dur)}")

    def _on_scrub(self) -> None:
        if not self._events or self._playback_active:
            return
        t = (self._scrub.value() / 1000.0) * self._duration_sec()
        e = self._engine()
        e.set_time_sec(t)
        if hasattr(self._canvas, "set_time_ql"):
            from midi_lab.visualizer.timeline import sec_to_ql

            self._canvas.set_time_ql(sec_to_ql(t, e.bpm))
        self._update_time_label(t)
        self._canvas.update()

    def _toggle_midi_in(self, on: bool) -> None:
        if not on:
            self._stop_midi_in()
            return
        port = self._midi_port.currentData()
        if not port:
            self._btn_midi.setChecked(False)
            QMessageBox.information(self, "MIDI In", "利用可能な MIDI 入力デバイスがありません。")
            return
        self._midi_in = MidiInputWorker(str(port), self)
        self._midi_in.note_on.connect(self._on_live_note_on)
        self._midi_in.sustain.connect(self._on_live_sustain)
        self._midi_in.failed.connect(self._on_midi_in_failed)
        self._midi_in.finished.connect(lambda: self._btn_midi.setChecked(False))
        self._live_ql = self._engine().t_ql
        self._midi_in.start()
        self._canvas.set_has_data(True)
        self._canvas.set_animating(True)

    def _stop_midi_in(self) -> None:
        if self._midi_in is not None and self._midi_in.isRunning():
            self._midi_in.requestInterruption()
            self._midi_in.wait(2000)
        self._midi_in = None
        if self._btn_midi.isChecked():
            self._btn_midi.setChecked(False)

    def _on_live_note_on(self, midi: int, velocity: int, channel: int) -> None:
        e = self._engine()
        e.timeline.append_live_note(midi, velocity, self._live_ql, 0.5, channel)
        self._live_ql += 0.25
        e.set_time_sec(ql_to_sec(self._live_ql, e.bpm))
        self._canvas.update()

    def _on_live_sustain(self, down: bool) -> None:
        self._engine().sustain_pedal = down
        if hasattr(self._canvas, "set_sustain_pedal"):
            self._canvas.set_sustain_pedal(down)

    def _on_midi_in_failed(self, tb: str) -> None:
        self._btn_midi.setChecked(False)
        QMessageBox.warning(self, "MIDI In", tb[:800])

    def _clone_engine_for_export(self) -> VisualizerEngine:
        e = VisualizerEngine()
        e.timeline = copy.deepcopy(self._engine().timeline)
        e.style_id = self._engine().style_id
        e.bpm = self._engine().bpm
        e.window_sec = self._engine().window_sec
        e.speed = self._engine().speed
        e.track_colors = self._engine().track_colors
        e.particle_amount = self._engine().particle_amount
        return e

    def export_video_dialog(self) -> None:
        if not self._events and not self._engine().timeline.notes:
            return
        path, _ = QFileDialog.getSaveFileName(self, "動画を保存", "visualization.mp4", VIDEO_FILTER)
        if not path:
            return
        p = Path(path)
        if p.suffix.lower() not in (".mp4", ".mov", ".avi"):
            path = str(p.with_suffix(".mp4"))
        self._start_export(path, png=False)

    def export_png_dialog(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "PNG 連番の出力先")
        if path:
            self._start_export(path, png=True)

    def _start_export(self, path: str, *, png: bool) -> None:
        if self._export_worker and self._export_worker.isRunning():
            return
        w, h = self._res_combo.currentData() or (1280, 720)
        self._progress.setVisible(True)
        self._btn_export.setEnabled(False)
        self._btn_png.setEnabled(False)
        self._export_worker = VideoExportWorker(
            path,
            self._clone_engine_for_export(),
            self._fps_spin.value(),
            w,
            h,
            png,
            self,
        )
        self._export_worker.progress.connect(
            lambda c, t: (self._progress.setMaximum(t), self._progress.setValue(c))
        )
        self._export_worker.completed.connect(self._on_export_done)
        self._export_worker.failed.connect(self._on_export_failed)
        self._export_worker.finished.connect(self._on_export_finished)
        self._export_worker.start()

    def _on_export_done(self, path: str) -> None:
        QMessageBox.information(self, "書き出し完了", f"保存しました:\n{path}")

    def _on_export_failed(self, tb: str) -> None:
        QMessageBox.critical(self, "書き出しエラー", tb[:2000])

    def _on_export_finished(self) -> None:
        self._export_worker = None
        self._progress.setVisible(False)
        on = bool(self._events)
        self._btn_export.setEnabled(on)
        self._btn_png.setEnabled(on)

    def stop_export(self) -> None:
        if self._export_worker and self._export_worker.isRunning():
            self._export_worker.requestInterruption()
            self._export_worker.wait(8000)
        self._stop_midi_in()
