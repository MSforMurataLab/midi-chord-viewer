# -*- coding: utf-8 -*-
"""ピアノ鍵盤ウィジェット（MIDI 番号で発光表示）。"""

from __future__ import annotations

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QLinearGradient, QPainter, QPen
from PyQt6.QtWidgets import QSizePolicy, QWidget


def _is_black_key(midi: int) -> bool:
    return midi % 12 in (1, 3, 6, 8, 10)


class PianoKeyboard(QWidget):
    """MIDI_LOW〜MIDI_HIGH の鍵を描画。active に含まれる鍵を赤く強調。"""

    MIDI_LOW = 45   # A2
    MIDI_HIGH = 96  # C7

    def __init__(self, parent=None):
        super().__init__(parent)
        self._active: set[int] = set()
        self.setMinimumHeight(96)
        self.setMaximumHeight(140)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def set_active_pitches(self, pitches: set[int] | None) -> None:
        self._active = set(pitches or ())
        self.update()

    def clear_active(self) -> None:
        self._active = set()
        self.update()

    def sizeHint(self):
        from PyQt6.QtCore import QSize

        return QSize(800, 112)

    def paintEvent(self, _event):
        w, h = float(self.width()), float(self.height())
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        lo, hi = self.MIDI_LOW, self.MIDI_HIGH
        white_keys = [m for m in range(lo, hi + 1) if not _is_black_key(m)]
        n_white = len(white_keys)
        if n_white == 0:
            return

        key_w = w / n_white
        white_h = h * 0.92
        top_y = h - white_h

        # 白鍵
        for i, midi in enumerate(white_keys):
            x = i * key_w
            rect = QRectF(x + 0.5, top_y, key_w - 1.0, white_h)
            active = midi in self._active
            g = QLinearGradient(QPointF(x, top_y), QPointF(x, h))
            if active:
                g.setColorAt(0, QColor("#ff6b6b"))
                g.setColorAt(0.55, QColor("#e02020"))
                g.setColorAt(1, QColor("#8b1010"))
            else:
                g.setColorAt(0, QColor("#f5f5f8"))
                g.setColorAt(0.7, QColor("#d8dae4"))
                g.setColorAt(1, QColor("#b8bac8"))
            painter.setPen(QPen(QColor("#2a2a38"), 1.0))
            painter.setBrush(g)
            painter.drawRoundedRect(rect, 2.0, 2.0)

        # 黒鍵（白鍵の上に重ねる）
        black_h = h * 0.58
        black_top = top_y
        for i, midi in enumerate(white_keys):
            if i + 1 >= len(white_keys):
                break
            # 右隣の白鍵との間に黒鍵があるか（C-D間は D♭ 等）
            gap_midi = None
            for cand in range(white_keys[i] + 1, white_keys[i + 1]):
                if _is_black_key(cand):
                    gap_midi = cand
                    break
            if gap_midi is None:
                continue
            x_left = i * key_w
            bw = key_w * 0.62
            bx = x_left + key_w - bw / 2
            rect = QRectF(bx, black_top, bw, black_h)
            active = gap_midi in self._active
            g = QLinearGradient(QPointF(bx, black_top), QPointF(bx, black_top + black_h))
            if active:
                g.setColorAt(0, QColor("#ff5555"))
                g.setColorAt(0.5, QColor("#cc1515"))
                g.setColorAt(1, QColor("#660808"))
            else:
                g.setColorAt(0, QColor("#2a2a36"))
                g.setColorAt(0.5, QColor("#12121a"))
                g.setColorAt(1, QColor("#08080c"))
            painter.setPen(QPen(QColor("#0a0a10"), 1.0))
            painter.setBrush(g)
            painter.drawRoundedRect(rect, 2.0, 2.0)

        painter.end()
