# -*- coding: utf-8 -*-
"""起動スプラッシュ。"""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from midi_lab import __version__
from midi_lab.ui.theme import SPLASH_STYLESHEET


class SplashWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("SplashRoot")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)
        self.setAttribute(Qt.WidgetAttribute.WA_QuitOnClose, False)
        self.setStyleSheet(SPLASH_STYLESHEET)
        self.setFixedSize(500, 340)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(28, 28, 28, 28)
        outer.setAlignment(Qt.AlignmentFlag.AlignCenter)

        card = QFrame()
        card.setObjectName("SplashCard")
        card.setFixedSize(444, 284)
        v = QVBoxLayout(card)
        v.setContentsMargins(40, 36, 40, 32)
        v.setSpacing(8)

        logo_row = QHBoxLayout()
        logo_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo = QFrame()
        logo.setObjectName("SplashLogo")
        ll = QVBoxLayout(logo)
        ll.setContentsMargins(0, 0, 0, 0)
        lt = QLabel("MC")
        lt.setObjectName("SplashLogoText")
        lt.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ll.addWidget(lt)
        logo_row.addWidget(logo)
        v.addLayout(logo_row)

        title = QLabel("MIDI Chord Lab")
        title.setObjectName("SplashTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub = QLabel("STUDIO GRAPHITE")
        sub.setObjectName("SplashSubtitle")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._status = QLabel("起動しています…")
        self._status.setObjectName("SplashStatus")
        self._status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status.setWordWrap(True)

        self._bar = QProgressBar()
        self._bar.setRange(0, 100)
        self._bar.setValue(0)
        self._bar.setTextVisible(False)

        ver = QLabel(f"VERSION {__version__}")
        ver.setObjectName("SplashVersion")
        ver.setAlignment(Qt.AlignmentFlag.AlignCenter)

        v.addWidget(title)
        v.addWidget(sub)
        v.addSpacing(20)
        v.addWidget(self._status)
        v.addWidget(self._bar)
        v.addStretch(1)
        v.addWidget(ver)
        outer.addWidget(card, alignment=Qt.AlignmentFlag.AlignCenter)

    def set_status(self, text: str) -> None:
        self._status.setText(text)
        QApplication.processEvents()

    def set_progress(self, value: int) -> None:
        self._bar.setValue(max(0, min(100, value)))
        QApplication.processEvents()

    def show_centered(self) -> None:
        screen = QApplication.primaryScreen()
        if screen is not None:
            geo = screen.availableGeometry()
            self.move(
                geo.x() + (geo.width() - self.width()) // 2,
                geo.y() + (geo.height() - self.height()) // 2,
            )
        self.show()
        self.raise_()
        QApplication.processEvents()

    def finish_and_handoff(self) -> None:
        self.hide()
