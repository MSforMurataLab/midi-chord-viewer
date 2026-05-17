# -*- coding: utf-8 -*-
"""モーダル風ローディングオーバーレイ（MIDI 解析等）。"""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QLabel, QProgressBar, QVBoxLayout, QWidget


class LoadingOverlay(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("LoadingOverlay")
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.hide()

        self._title = QLabel("読み込み中")
        self._title.setObjectName("LoadingTitle")
        self._title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._detail = QLabel("")
        self._detail.setObjectName("LoadingDetail")
        self._detail.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._detail.setWordWrap(True)

        self._bar = QProgressBar()
        self._bar.setRange(0, 0)  # 不定インジケータ
        self._bar.setFixedHeight(6)
        self._bar.setTextVisible(False)

        card = QFrame()
        card.setObjectName("LoadingCard")
        cv = QVBoxLayout(card)
        cv.setContentsMargins(32, 28, 32, 28)
        cv.setSpacing(12)
        cv.addWidget(self._title)
        cv.addWidget(self._detail)
        cv.addWidget(self._bar)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addStretch(1)
        lay.addWidget(card, alignment=Qt.AlignmentFlag.AlignCenter)
        lay.addStretch(1)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.parentWidget() is not None:
            self.setGeometry(self.parentWidget().rect())

    def show_loading(self, title: str, detail: str = "") -> None:
        self._title.setText(title)
        self._detail.setText(detail)
        if self.parentWidget() is not None:
            self.setGeometry(self.parentWidget().rect())
        self.raise_()
        self.show()

    def hide_loading(self) -> None:
        self.hide()
