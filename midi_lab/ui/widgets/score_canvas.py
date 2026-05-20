# -*- coding: utf-8 -*-
from __future__ import annotations

import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtWidgets import QFrame, QLabel, QSizePolicy, QVBoxLayout, QWidget


class ScoreCanvas(QWidget):
    """matplotlib Figure を Qt 領域いっぱいに表示するキャンバス。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)
        self._figure = None
        self._canvas = None
        self._toolbar = None
        self.show_placeholder()

    def _clear_widgets(self) -> None:
        while self._layout.count():
            item = self._layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        self._toolbar = None
        self._canvas = None
        if self._figure is not None:
            plt.close(self._figure)
            self._figure = None

    def _sync_figure_size(self) -> None:
        """ウィジェットサイズに Figure を合わせ、グラフを中央の小さな塊にしない。"""
        if self._figure is None or self._canvas is None:
            return
        dpi = self._figure.get_dpi()
        w_px = max(self._canvas.width(), 480)
        h_px = max(self._canvas.height(), 360)
        self._figure.set_size_inches(w_px / dpi, h_px / dpi, forward=True)
        self._canvas.draw_idle()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._sync_figure_size()

    def show_placeholder(
        self,
        *,
        title: str = "ピアノロール",
        body: str = "MIDI を読み込むと、音程と時間の関係がここに表示されます",
        icon_text: str = "▤",
    ) -> None:
        self.show_custom_placeholder(title, body, icon_text)

    def show_custom_placeholder(self, title: str, body: str, icon_text: str = "▤") -> None:
        self._clear_widgets()
        wrap = QFrame()
        wrap.setObjectName("PlotPlaceholder")
        v = QVBoxLayout(wrap)
        v.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.setSpacing(10)
        icon = QLabel(icon_text)
        icon.setObjectName("PlotPlaceholderIcon")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        t = QLabel(title)
        t.setObjectName("PlotPlaceholderTitle")
        t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        b = QLabel(body)
        b.setObjectName("PlotPlaceholderBody")
        b.setAlignment(Qt.AlignmentFlag.AlignCenter)
        b.setWordWrap(True)
        v.addWidget(icon)
        v.addWidget(t)
        v.addWidget(b)
        self._layout.addWidget(wrap)

    def set_figure(self, figure, *, show_toolbar: bool = True) -> None:
        """matplotlib Figure を表示（カスタム・ピアノロール / パフォーマンス用）。"""
        self._clear_widgets()
        self._figure = figure
        self._canvas = FigureCanvasQTAgg(self._figure)
        self._canvas.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        if show_toolbar:
            self._toolbar = NavigationToolbar(self._canvas, self)
            self._toolbar.setObjectName("PlotToolBar")
            self._layout.addWidget(self._toolbar)
        self._layout.addWidget(self._canvas, stretch=1)
        QTimer.singleShot(0, self._sync_figure_size)
