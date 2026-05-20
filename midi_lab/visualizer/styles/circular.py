# -*- coding: utf-8 -*-
from __future__ import annotations

import math

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QPainter, QPen

from midi_lab.ui import design_tokens as dt
from midi_lab.visualizer.styles.base import RenderContext, RenderStyle
from midi_lab.visualizer.timeline import visible_beat_window


class CircularStyle(RenderStyle):
    id = "circular"
    label = "Circular / Radial"
    particle_kind = 1

    def paint(self, ctx: RenderContext) -> None:
        r = ctx.rect
        p = ctx.painter
        p.fillRect(r.toRect(), QColor(dt.BG_DEEP))
        cx, cy = r.center().x(), r.center().y()
        base_r = min(r.width(), r.height()) * 0.12
        max_r = min(r.width(), r.height()) * 0.48

        x0, x1 = visible_beat_window(ctx.t_ql, ctx.window_ql, ctx.timeline.duration_ql)
        span = max(0.01, x1 - x0)

        for pc in range(12):
            ang = math.radians(pc * 30 - 90)
            lx = cx + math.cos(ang) * base_r
            ly = cy + math.sin(ang) * base_r
            names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
            p.setPen(QColor(dt.TEXT_MUTED))
            p.drawText(QPointF(lx - 6, ly + 4), names[pc])

        for n in ctx.timeline.notes:
            end = ctx.note_end_with_sustain(n)
            if end < x0 or n.onset_ql > x1:
                continue
            ang = math.radians((n.midi % 12) * 30 + (n.midi // 12) * 3 - 90)
            t_rel = (n.onset_ql - x0) / span
            rad = base_r + t_rel * (max_r - base_r)
            x = cx + math.cos(ang) * rad
            y = cy + math.sin(ang) * rad
            c = ctx.channel_color(n.channel, n.velocity)
            size = 3 + 8 * (n.velocity / 127.0)
            p.setBrush(c)
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPointF(x, y), size, size)
            if n.onset_ql <= ctx.t_ql < end:
                p.setPen(QPen(c, 1.5))
                ripple = base_r + ((ctx.t_ql - x0) / span) * (max_r - base_r)
                rx = cx + math.cos(ang) * ripple
                ry = cy + math.sin(ang) * ripple
                p.drawEllipse(QPointF(rx, ry), 6, 6)

        p.setPen(QPen(QColor(dt.ACCENT), 2))
        p.setBrush(Qt.BrushStyle.NoBrush)
        play_r = base_r + ((ctx.t_ql - x0) / span) * (max_r - base_r)
        p.drawEllipse(QPointF(cx, cy), play_r, play_r)
        ctx.particles.paint(p)
