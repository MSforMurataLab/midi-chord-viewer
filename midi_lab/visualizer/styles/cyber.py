# -*- coding: utf-8 -*-
from __future__ import annotations

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QPainter, QPen

from midi_lab.ui import design_tokens as dt
from midi_lab.visualizer.styles.base import RenderContext, RenderStyle
from midi_lab.visualizer.timeline import visible_beat_window


class CyberLaserStyle(RenderStyle):
    id = "cyber"
    label = "Cyber Laser / String"
    particle_kind = 3

    def paint(self, ctx: RenderContext) -> None:
        r = ctx.rect
        p = ctx.painter
        p.fillRect(r.toRect(), QColor("#0a0c12"))

        hit_x = r.right() - 12
        note_left = r.left() + 8
        x0, x1 = visible_beat_window(ctx.t_ql, ctx.window_ql, ctx.timeline.duration_ql)
        y_lo, y_hi = ctx.timeline.y_range()

        p.setPen(QPen(QColor(dt.ACCENT), 2))
        p.drawLine(int(hit_x), int(r.top()), int(hit_x), int(r.bottom()))

        for n in ctx.timeline.notes:
            end = ctx.note_end_with_sustain(n)
            if end < x0 or n.onset_ql > x1:
                continue
            span = max(1, y_hi - y_lo)
            y = r.top() + (y_hi - n.midi) / span * (r.height() - 16)
            x_start = note_left + (n.onset_ql - x0) / max(0.01, x1 - x0) * (hit_x - note_left - 20)
            c = ctx.channel_color(n.channel, n.velocity)
            glow = QColor(c)
            glow.setAlpha(60)
            p.setPen(QPen(glow, 5))
            p.drawLine(QPointF(x_start, y), QPointF(hit_x, y))
            p.setPen(QPen(c, 2))
            p.drawLine(QPointF(x_start, y), QPointF(hit_x, y))
            if n.onset_ql <= ctx.t_ql < end:
                p.setBrush(c)
                p.drawEllipse(QPointF(hit_x, y), 4, 4)

        ctx.particles.paint(p)
