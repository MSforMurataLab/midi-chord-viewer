# -*- coding: utf-8 -*-
from __future__ import annotations

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QLinearGradient, QPainter, QPen
from PyQt6.QtWidgets import QSizePolicy, QWidget

from midi_lab.ui import design_tokens as dt


def _is_black_key(midi: int) -> bool:
    return midi % 12 in (1, 3, 6, 8, 10)


class PianoKeyboard(QWidget):
    MIDI_LOW = 45
    MIDI_HIGH = 96

    def __init__(self, parent=None):
        super().__init__(parent)
        self._active: set[int] = set()
        self.setObjectName("PianoKeyboard")
        self.setMinimumHeight(108)
        self.setMaximumHeight(160)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def set_active_pitches(self, pitches: set[int] | None) -> None:
        self._active = set(pitches or ())
        self.update()

    def clear_active(self) -> None:
        self._active = set()
        self.update()

    def paintEvent(self, _event):
        w, h = float(self.width()), float(self.height())
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 台座
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(dt.PIANO_BG))
        painter.drawRoundedRect(QRectF(0, 0, w, h), 10, 10)

        margin = 10.0
        inner = QRectF(margin, margin, w - 2 * margin, h - 2 * margin - 4)
        painter.setPen(QPen(QColor(dt.BORDER_SUBTLE), 1.0))
        painter.setBrush(QColor(dt.PIANO_WELL))
        painter.drawRoundedRect(inner, 8, 8)

        white_keys = [m for m in range(self.MIDI_LOW, self.MIDI_HIGH + 1) if not _is_black_key(m)]
        if not white_keys:
            painter.end()
            return

        pad = 6.0
        area = QRectF(inner.x() + pad, inner.y() + pad, inner.width() - 2 * pad, inner.height() - 2 * pad)
        key_w = area.width() / len(white_keys)
        white_h = area.height() * 0.88
        top_y = area.bottom() - white_h

        for i, midi in enumerate(white_keys):
            x = area.x() + i * key_w
            rect = QRectF(x + 1.0, top_y, key_w - 2.0, white_h)
            active = midi in self._active
            g = QLinearGradient(QPointF(x, top_y), QPointF(x, area.bottom()))
            if active:
                g.setColorAt(0, QColor(dt.ACTIVE_KEY_LIGHT))
                g.setColorAt(0.45, QColor(dt.ACTIVE_KEY))
                g.setColorAt(1, QColor(dt.ACTIVE_KEY_DEEP))
                painter.setPen(QPen(QColor(dt.ACCENT), 1.5))
            else:
                g.setColorAt(0, QColor(dt.PIANO_WHITE_TOP))
                g.setColorAt(1, QColor(dt.PIANO_WHITE_BOT))
                painter.setPen(QPen(QColor("#a1a1aa"), 0.8))
            painter.setBrush(g)
            painter.drawRoundedRect(rect, 4.0, 4.0)

        black_h = area.height() * 0.58
        for i, midi in enumerate(white_keys):
            if i + 1 >= len(white_keys):
                break
            gap_midi = None
            for cand in range(white_keys[i] + 1, white_keys[i + 1]):
                if _is_black_key(cand):
                    gap_midi = cand
                    break
            if gap_midi is None:
                continue
            bx = area.x() + i * key_w + key_w - (key_w * 0.58) / 2
            bw = key_w * 0.58
            rect = QRectF(bx, top_y, bw, black_h)
            active = gap_midi in self._active
            g = QLinearGradient(QPointF(bx, top_y), QPointF(bx, top_y + black_h))
            if active:
                g.setColorAt(0, QColor(dt.ACTIVE_KEY_LIGHT))
                g.setColorAt(1, QColor(dt.ACTIVE_KEY_DEEP))
                painter.setPen(QPen(QColor(dt.ACCENT), 1.2))
            else:
                g.setColorAt(0, QColor(dt.PIANO_BLACK_TOP))
                g.setColorAt(1, QColor(dt.PIANO_BLACK_BOT))
                painter.setPen(QPen(QColor("#09090b"), 1.0))
            painter.setBrush(g)
            painter.drawRoundedRect(rect, 3.0, 3.0)

        painter.end()
