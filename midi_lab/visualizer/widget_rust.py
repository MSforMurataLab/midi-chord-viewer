# -*- coding: utf-8 -*-
"""PyQt6 + Rust/wgpu ビジュアライザキャンバス（オフスクリーン描画 → QImage 表示）。"""
from __future__ import annotations

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QImage, QPainter
from PyQt6.QtWidgets import QLabel, QSizePolicy, QVBoxLayout, QWidget

from midi_lab.core.note_events import NoteEvent
from midi_lab.diagnostics import log
from midi_lab.visualizer.rust_bridge import VisualizerEngine, rust_available


class RustVisualizerCanvas(QWidget):
    """wgpu オフスクリーン描画。HWND / ModernGL は使用しない。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)
        self.setAutoFillBackground(False)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumHeight(200)
        self._engine = None
        self._init_failed = False
        self._init_scheduled = False
        self._error_message = ""
        self._error_label = QLabel(self)
        self._error_label.setObjectName("PanelHint")
        self._error_label.setWordWrap(True)
        self._error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._error_label.hide()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.addWidget(self._error_label)
        self._frame: QImage | None = None
        self._has_data = False
        self._animating = False
        self._bpm = 120.0
        self._window_sec = 8.0
        self._speed = 1.0
        self._style_id = "waterfall"
        self._track_colors = True
        self._particle_amount = 1.0
        self._t_ql = 0.0
        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._on_tick)
        self._idle_timer = QTimer(self)
        self._idle_timer.setInterval(100)
        self._idle_timer.timeout.connect(self._update)

    @staticmethod
    def is_available() -> bool:
        return rust_available()

    def notify_tab_shown(self) -> None:
        self._schedule_engine_init()

    def set_has_data(self, on: bool) -> None:
        self._has_data = on
        if on:
            self._idle_timer.start()
            self._schedule_engine_init()
            self._update()
        else:
            self._timer.stop()
            self._idle_timer.stop()
            self._animating = False

    def set_animating(self, on: bool) -> None:
        self._animating = on
        if on and self._has_data:
            self._timer.start()
        else:
            self._timer.stop()
            if self._has_data:
                self._update()

    def load_events(self, events: list[NoteEvent]) -> None:
        self._schedule_engine_init()
        if self._engine is None:
            return
        onsets = [float(e.offset) for e in events]
        durations = [float(e.quarter_length) for e in events]
        midis = [int(e.midi) for e in events]
        velocities = [int(e.velocity) for e in events]
        channels = [int(e.channel) for e in events]
        self._engine.load_notes(onsets, durations, midis, velocities, channels)
        self._t_ql = 0.0
        self._sync_transport()
        self._update()

    def clear_data(self) -> None:
        self._has_data = False
        self._frame = None
        self._timer.stop()
        self._idle_timer.stop()

    def set_style(self, style_id: str) -> None:
        self._style_id = style_id
        if self._engine:
            self._engine.set_style(style_id)

    def set_params(
        self,
        *,
        bpm: float,
        window_sec: float,
        speed: float,
        track_colors: bool,
        particle_amount: float,
    ) -> None:
        self._bpm = bpm
        self._window_sec = window_sec
        self._speed = speed
        self._track_colors = track_colors
        self._particle_amount = particle_amount
        if self._engine:
            self._engine.set_track_colors(track_colors)
            self._engine.set_particle_amount(particle_amount)
        self._sync_transport()

    def set_time_ql(self, t_ql: float) -> None:
        self._t_ql = max(0.0, float(t_ql))
        self._sync_transport()

    def set_sustain_pedal(self, down: bool) -> None:
        if self._engine:
            self._engine.set_sustain_pedal(down)

    def send_midi_event(self, status: int, data1: int, data2: int, timestamp_us: int = 0) -> None:
        if self._engine:
            self._engine.send_midi_event(status, data1, data2, timestamp_us)

    def set_audio_latency_ms(self, ms: float) -> None:
        if self._engine:
            self._engine.set_audio_latency_ms(ms)

    def _sync_transport(self) -> None:
        if self._engine:
            self._engine.set_transport(self._t_ql, self._bpm, self._window_sec, self._speed)

    def _can_init_engine(self) -> bool:
        if self._init_failed or self._engine is not None:
            return False
        return self.width() >= 64 and self.height() >= 64

    def _schedule_engine_init(self) -> None:
        if self._engine is not None or self._init_failed or self._init_scheduled:
            return
        self._init_scheduled = True
        QTimer.singleShot(0, self._deferred_ensure_engine)

    def _deferred_ensure_engine(self) -> None:
        self._init_scheduled = False
        self._ensure_engine()

    def _ensure_engine(self) -> None:
        if not self._can_init_engine():
            return
        w, h = max(64, self.width()), max(64, self.height())
        try:
            self._engine = VisualizerEngine(w, h)
        except Exception as exc:
            self._init_failed = True
            self._error_message = str(exc)
            self._error_label.setText(
                "GPU ビジュアライザを初期化できませんでした。\n"
                f"{self._error_message}\n\n"
                "グラフィックスドライバの更新、または Windows の「グラフィックス設定」で\n"
                "このアプリを高性能 GPU に割り当ててください。"
            )
            self._error_label.show()
            log(f"[RustVisualizer] init failed: {exc}")
            self.update()
            return
        self._engine.set_style(self._style_id)
        self._engine.set_track_colors(self._track_colors)
        self._engine.set_particle_amount(self._particle_amount)
        self._sync_transport()

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        self._schedule_engine_init()
        if self._has_data:
            self._update()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        if self.width() >= 64 and self.height() >= 64:
            self._schedule_engine_init()
        if self._engine and self.width() >= 64 and self.height() >= 64:
            self._engine.resize(self.width(), self.height())
            self._update()

    def paintEvent(self, event) -> None:  # noqa: N802
        if self._init_failed:
            painter = QPainter(self)
            painter.fillRect(self.rect(), Qt.GlobalColor.black)
            painter.end()
            return
        if self._engine and self._has_data:
            try:
                rgba = self._engine.render_frame_rgba()
                w, h = self.width(), self.height()
                if rgba and w > 0 and h > 0 and len(rgba) >= w * h * 4:
                    self._frame = QImage(
                        rgba, w, h, w * 4, QImage.Format.Format_RGBA8888
                    ).copy()
            except Exception as exc:
                self._init_failed = True
                self._error_message = str(exc)
                self._error_label.setText(f"描画エラー: {self._error_message}")
                self._error_label.show()
                log(f"[RustVisualizer] render failed: {exc}")
                return
        if self._frame is not None and not self._frame.isNull():
            painter = QPainter(self)
            painter.drawImage(0, 0, self._frame)
            painter.end()
        else:
            painter = QPainter(self)
            painter.fillRect(self.rect(), Qt.GlobalColor.black)
            painter.end()

    def _on_tick(self) -> None:
        if self._engine and self._has_data:
            try:
                self._engine.tick(1.0 / 60.0)
            except RuntimeError:
                pass
            self._update()

    def _update(self) -> None:
        if not self._init_failed:
            self.update()

    def shutdown(self) -> None:
        self._engine = None
        self._frame = None
