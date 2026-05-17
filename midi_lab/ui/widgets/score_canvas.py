# -*- coding: utf-8 -*-
from __future__ import annotations

import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QLabel, QSizePolicy, QVBoxLayout, QWidget

class ScoreCanvas(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)
        self._figure = None
        self._canvas = None
        self._toolbar = None
        self.show_placeholder()

    def _clear_widgets(self):
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

    def show_placeholder(self):
        self._clear_widgets()
        wrap = QFrame()
        wrap.setObjectName("PlotPlaceholder")
        v = QVBoxLayout(wrap)
        v.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.setSpacing(10)
        icon = QLabel("▤")
        icon.setObjectName("PlotPlaceholderIcon")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        t = QLabel("ピアノロール")
        t.setObjectName("PlotPlaceholderTitle")
        t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        b = QLabel("MIDI を読み込むと、音程と時間の関係がここに表示されます")
        b.setObjectName("PlotPlaceholderBody")
        b.setAlignment(Qt.AlignmentFlag.AlignCenter)
        b.setWordWrap(True)
        v.addWidget(icon)
        v.addWidget(t)
        v.addWidget(b)
        self._layout.addWidget(wrap)

    def set_figure(self, figure):
        """matplotlib Figure を表示（カスタム・ピアノロール用）。"""
        self._clear_widgets()
        self._figure = figure
        self._canvas = FigureCanvasQTAgg(self._figure)
        self._canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._toolbar = NavigationToolbar(self._canvas, self)
        self._toolbar.setObjectName("PlotToolBar")
        self._layout.addWidget(self._toolbar)
        self._layout.addWidget(self._canvas, stretch=1)
