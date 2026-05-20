# -*- coding: utf-8 -*-
from __future__ import annotations

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QLinearGradient, QPainter, QPen

from midi_lab.ui import design_tokens as dt
from midi_lab.visualizer.styles.base import RenderContext, RenderStyle
from midi_lab.visualizer.timeline import visible_beat_window


class WaterfallStyle(RenderStyle):
    id = "waterfall"
    label = "Classic Waterfall"
    particle_kind = 0

    def paint(self, ctx: RenderContext) -> None:
        r = ctx.rect
        p = ctx.painter
        p.fillRect(r.toRect(), QColor(dt.BG_DEEP))

        kb_h = max(36.0, r.height() * 0.14)
        note_top = r.top() + 8
        hit_y = r.bottom() - kb_h
        note_rect = QRectF(r.left(), note_top, r.width(), hit_y - note_top)

        x0, x1 = visible_beat_window(ctx.t_ql, ctx.window_ql, ctx.timeline.duration_ql)
        y_lo, y_hi = ctx.timeline.y_range()

        grad = QLinearGradient(0, note_top, 0, hit_y)
        grad.setColorAt(0, QColor(20, 20, 24, 0))
        grad.setColorAt(1, QColor(dt.ACCENT_SOFT))
        p.fillRect(note_rect.toRect(), grad)

        p.setPen(QPen(QColor(dt.ACCENT), 2))
        p.drawLine(int(r.left()), int(hit_y), int(r.right()), int(hit_y))

        for n in ctx.timeline.notes:
            end = ctx.note_end_with_sustain(n)
            if end < x0 or n.onset_ql > x1:
                continue
            x = ctx.x_for_midi(n.midi, y_lo, y_hi)
            w = max(3.0, r.width() / max(24, y_hi - y_lo + 1) * 0.85)
            y1 = ctx.y_for_ql(n.onset_ql, x0, x1, note_top, hit_y)
            y2 = ctx.y_for_ql(end, x0, x1, note_top, hit_y)
            top_y, bot_y = (min(y1, y2), max(y1, y2))
            if bot_y - top_y < 2:
                bot_y = top_y + 3
            c = ctx.channel_color(n.channel, n.velocity)
            p.fillRect(QRectF(x - w / 2, top_y, w, bot_y - top_y), c)

        self._draw_keyboard(p, r, hit_y, kb_h, y_lo, y_hi, ctx)
        ctx.particles.paint(p)

    def _draw_keyboard(
        self, p: QPainter, r: QRectF, hit_y: float, kb_h: float, y_lo: int, y_hi: int, ctx: RenderContext
    ) -> None:
        p.fillRect(QRectF(r.left(), hit_y, r.width(), kb_h).toRect(), QColor(dt.PIANO_WELL))
        white_h = kb_h * 0.92
        for m in range(y_lo, y_hi + 1):
            if m % 12 in (1, 3, 6, 8, 10):
                continue
            x = ctx.x_for_midi(m, y_lo, y_hi)
            w = max(4.0, r.width() / max(20, y_hi - y_lo) * 0.7)
            active = any(
                n.midi == m and n.onset_ql <= ctx.t_ql < ctx.note_end_with_sustain(n)
                for n in ctx.timeline.notes
            )
            col = QColor(dt.ACTIVE_KEY) if active else QColor(dt.PIANO_WHITE_TOP)
            p.fillRect(QRectF(x - w / 2, hit_y + 2, w, white_h), col)
