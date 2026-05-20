# -*- coding: utf-8 -*-
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from PyQt6.QtCore import QRectF
from PyQt6.QtGui import QColor, QPainter

from midi_lab.visualizer.particles import ParticleSystem
from midi_lab.visualizer.timeline import MidiTimeline


@dataclass
class RenderContext:
    painter: QPainter
    rect: QRectF
    timeline: MidiTimeline
    t_ql: float
    window_ql: float
    bpm: float
    speed: float
    sustain_extend_ql: float
    particles: ParticleSystem
    track_colors: bool
    particle_style: int

    def note_end_with_sustain(self, note) -> float:
        end = note.end_ql
        if self.sustain_extend_ql > 0 and note.end_ql <= self.t_ql + 0.05:
            end = max(end, self.t_ql + self.sustain_extend_ql)
        return end

    def channel_color(self, channel: int, velocity: int) -> QColor:
        from midi_lab.ui import design_tokens as dt

        hues = (210, 280, 160, 30, 340, 50, 190, 120, 0, 300, 80, 250, 20, 200, 140, 60)
        h = hues[channel % len(hues)]
        v = 0.45 + 0.55 * (velocity / 127.0)
        c = QColor.fromHsv(int(h), int(180 * v), int(120 + 135 * v))
        if not self.track_colors:
            c = QColor(dt.ACCENT)
            c.setAlpha(int(80 + 175 * velocity / 127.0))
        return c

    def x_for_midi(self, midi: int, y_lo: int, y_hi: int) -> float:
        span = max(1, y_hi - y_lo)
        return self.rect.left() + (midi - y_lo) / span * self.rect.width()

    def y_for_ql(self, ql: float, x0: float, x1: float, top: float, bottom: float) -> float:
        """t_ql が bottom（判定ライン）に来る座標系。"""
        span = max(0.01, x1 - x0)
        ratio = (ql - x0) / span
        return bottom - ratio * (bottom - top)


class RenderStyle(ABC):
    id: str
    label: str
    particle_kind: int = 0

    @abstractmethod
    def paint(self, ctx: RenderContext) -> None:
        pass

    def spawn_hits(self, ctx: RenderContext, x0: float, x1: float, hit_y: float) -> None:
        prev_notes = set()
        for n in ctx.timeline.notes:
            if x0 <= n.onset_ql <= ctx.t_ql <= n.onset_ql + 0.08:
                key = (n.midi, int(n.onset_ql * 100))
                if key not in prev_notes:
                    prev_notes.add(key)
                    y_lo, y_hi = ctx.timeline.y_range()
                    x = ctx.x_for_midi(n.midi, y_lo, y_hi)
                    ctx.particles.spawn_hit(
                        x, hit_y, n.velocity, ctx.particle_style, ctx.channel_color(n.channel, n.velocity)
                    )
