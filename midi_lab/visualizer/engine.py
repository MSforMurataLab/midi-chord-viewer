# -*- coding: utf-8 -*-
"""ビジュアライザ状態 — GPU 描画は GpuRenderer が担当。"""
from __future__ import annotations

import math

from midi_lab.core.note_events import NoteEvent
from midi_lab.visualizer.gl.particles import GPUParticleSystem
from midi_lab.visualizer.styles import STYLES
from midi_lab.visualizer.styles_builders.keyboard import key_center_pixels
from midi_lab.visualizer.timeline import MidiTimeline, sec_to_ql, visible_beat_window


class VisualizerEngine:
    def __init__(self) -> None:
        self.timeline = MidiTimeline()
        self.t_ql: float = 0.0
        self.window_sec: float = 8.0
        self.bpm: float = 120.0
        self.speed: float = 1.0
        self.style_id: str = "waterfall"
        self.track_colors: bool = True
        self.particle_amount: float = 1.0
        self.sustain_pedal: bool = False
        self.sustain_extend_ql: float = 0.0
        self.particles = GPUParticleSystem()
        self._spawned: set[tuple[int, int]] = set()

    @property
    def window_ql(self) -> float:
        return sec_to_ql(self.window_sec / max(0.25, self.speed), self.bpm)

    def load_events(self, events: list[NoteEvent]) -> None:
        self.timeline = MidiTimeline.from_note_events(events)
        self.t_ql = 0.0
        self._spawned.clear()
        self.particles.clear()
        self._clear_spectrum()

    def clear(self) -> None:
        self.timeline = MidiTimeline()
        self.t_ql = 0.0
        self._spawned.clear()
        self.particles.clear()
        self._clear_spectrum()

    def _clear_spectrum(self) -> None:
        from midi_lab.visualizer.styles_builders import clear_spectrum_state

        clear_spectrum_state()

    def set_time_sec(self, t_sec: float, bpm: float | None = None) -> None:
        if bpm is not None:
            self.bpm = max(20.0, float(bpm))
        self.t_ql = max(0.0, min(sec_to_ql(t_sec, self.bpm), self.timeline.duration_ql))

    def set_style(self, style_id: str) -> None:
        if style_id in STYLES and style_id != self.style_id:
            self.style_id = style_id
            self.particles.clear()
            self._spawned.clear()
            self._clear_spectrum()

    def tick(self, dt: float) -> None:
        self.particles.amount_scale = self.particle_amount
        self.particles.update(dt)
        if self.sustain_pedal:
            self.sustain_extend_ql = min(2.5, self.sustain_extend_ql + dt * 1.2)
        else:
            self.sustain_extend_ql = max(0.0, self.sustain_extend_ql - dt * 1.5)

    def _channel_rgb(self, channel: int, velocity: int) -> tuple[float, float, float]:
        vel = velocity / 127.0
        if not self.track_colors:
            return (0.36 * vel, 0.61 * vel, 0.96 * vel)
        h = (channel * 0.618033988749895) % 1.0
        r = max(0.0, abs(h * 6.0 - 3.0) - 1.0)
        g = max(0.0, 2.0 - abs(h * 6.0 - 2.0))
        b = max(0.0, 2.0 - abs(h * 6.0 - 4.0))
        s = 0.4 + 0.6 * vel
        return (r * s, g * s, b * s)

    def spawn_hits_pixels(self, width: int, height: int) -> None:
        """ノートオンを鍵盤（または円心）座標からパーティクル生成。"""
        style = STYLES.get(self.style_id)
        if style is None:
            return
        t = self.t_ql
        y_lo, y_hi = self.timeline.y_range()
        kb = 0.14

        for n in self.timeline.notes:
            if abs(n.onset_ql - t) > 0.06:
                continue
            key = (n.midi, int(n.onset_ql * 200))
            if key in self._spawned:
                continue
            self._spawned.add(key)
            r, g, b = self._channel_rgb(n.channel, n.velocity)

            if self.style_id == "circular":
                from midi_lab.visualizer.styles_builders.context import midi_to_theta, polar_xy

                y_lo, y_hi = self.timeline.y_range()
                asp = float(width) / float(max(height, 1))
                theta = midi_to_theta(n.midi, y_lo, y_hi)
                ndc_x, ndc_y = polar_xy(asp, theta, 0.1)
                px = (ndc_x + 1.0) * 0.5 * width
                py = (1.0 - (ndc_y + 1.0) / 2.0) * height
            elif self.style_id == "cyber":
                x0, x1 = visible_beat_window(t, self.window_ql, self.timeline.duration_ql)
                px = (n.onset_ql - x0) / max(x1 - x0, 0.001) * width
                span = max(1, y_hi - y_lo)
                py = (y_hi - n.midi) / span * height * 0.88
            else:
                px, py = key_center_pixels(n.midi, y_lo, y_hi, width, height, kb)

            self.particles.spawn_hit(
                px,
                py,
                n.velocity,
                r=r,
                g=g,
                b=b,
                style_kind=style.particle_kind,
            )
