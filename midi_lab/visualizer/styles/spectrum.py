# -*- coding: utf-8 -*-
from __future__ import annotations

from PyQt6.QtCore import QRectF
from PyQt6.QtGui import QColor, QLinearGradient, QPainter

from midi_lab.ui import design_tokens as dt
from midi_lab.visualizer.styles.base import RenderContext, RenderStyle


class SpectrumStyle(RenderStyle):
    id = "spectrum"
    label = "Bar / Spectrum"
    particle_kind = 2

    def paint(self, ctx: RenderContext) -> None:
        r = ctx.rect
        p = ctx.painter
        p.fillRect(r.toRect(), QColor(dt.BG_DEEP))

        y_lo, y_hi = ctx.timeline.y_range()
        n_keys = y_hi - y_lo + 1
        bar_w = r.width() / max(1, n_keys)
        floor_y = r.bottom() - 8

        heights = [0.0] * n_keys
        for n in ctx.timeline.notes:
            if n.onset_ql <= ctx.t_ql < ctx.note_end_with_sustain(n):
                idx = n.midi - y_lo
                if 0 <= idx < n_keys:
                    h = n.velocity / 127.0
                    heights[idx] = max(heights[idx], h)

        for i, h in enumerate(heights):
            if h <= 0.01:
                continue
            x = r.left() + i * bar_w + 1
            bh = (r.height() - 24) * h
            c = QColor.fromHsv(int(220 - 120 * h), 200, int(100 + 155 * h))
            grad = QLinearGradient(x, floor_y, x, floor_y - bh)
            grad.setColorAt(0, c)
            grad.setColorAt(1, QColor(c.red(), c.green(), c.blue(), 40))
            p.fillRect(QRectF(x, floor_y - bh, bar_w - 2, bh), grad)

        ctx.particles.paint(p)
