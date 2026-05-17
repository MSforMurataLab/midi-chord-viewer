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

SPLASH_STYLESHEET = """
QWidget#SplashRoot {
    background-color: #050508;
}
QFrame#SplashCard {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #18181f, stop:1 #0a0a10);
    border: 1px solid #f59e0b;
    border-radius: 22px;
}
QFrame#SplashLogo {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #fbbf24, stop:1 #d97706);
    border-radius: 16px;
    min-width: 56px;
    max-width: 56px;
    min-height: 56px;
    max-height: 56px;
}
QLabel#SplashLogoText {
    color: #1c1917;
    font-size: 20px;
    font-weight: 800;
    background: transparent;
}
QLabel#SplashTitle {
    color: #fafafa;
    font-size: 26px;
    font-weight: 800;
    letter-spacing: -0.3px;
    background: transparent;
}
QLabel#SplashSubtitle {
    color: #a78bfa;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 1px;
    background: transparent;
}
QLabel#SplashStatus {
    color: #71717a;
    font-size: 12px;
    background: transparent;
}
QLabel#SplashVersion {
    color: #52525b;
    font-size: 10px;
    font-weight: 600;
    background: transparent;
}
QProgressBar {
    background-color: #0c0c12;
    border: 1px solid #32324a;
    border-radius: 5px;
    min-height: 6px;
    max-height: 6px;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #d97706, stop:1 #fbbf24);
    border-radius: 4px;
}
"""


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
        sub = QLabel("MIDNIGHT STUDIO")
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
