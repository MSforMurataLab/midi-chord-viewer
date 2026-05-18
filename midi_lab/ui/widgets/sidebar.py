# -*- coding: utf-8 -*-
"""左サイドバー — スクロール可能なゆったりレイアウト。"""
from __future__ import annotations

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtWidgets import (
    QFrame,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

SIDEBAR_WIDTH = 292
BTN_H = 54
BTN_H_PRIMARY = 56
SPIN_H = 52
SECTION_GAP = 14
ITEM_GAP = 12


class SidebarButton(QPushButton):
    """sizeHint を明示し、スタイルシートとレイアウトの高さ不一致を防ぐ。"""

    def __init__(self, text: str, object_name: str, height: int = BTN_H, parent=None):
        super().__init__(text, parent)
        self.setObjectName(object_name)
        self._fixed_h = height
        self.setFixedHeight(height)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def sizeHint(self) -> QSize:
        return QSize(max(super().sizeHint().width(), 120), self._fixed_h)

    def minimumSizeHint(self) -> QSize:
        return self.sizeHint()


class SidebarPanel(QFrame):
    """ファイル / 再生 / 解析コントロール（縦スクロール）。"""

    WIDTH = SIDEBAR_WIDTH

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Sidebar")
        self.setFixedWidth(SIDEBAR_WIDTH)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        scroll = QScrollArea()
        scroll.setObjectName("SidebarScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        viewport = QWidget()
        viewport.setObjectName("SidebarViewport")
        v = QVBoxLayout(viewport)
        v.setContentsMargins(12, 16, 12, 20)
        v.setSpacing(ITEM_GAP)

        # ── FILE ──
        v.addWidget(self._section("FILE"))
        self.btn_open = SidebarButton("＋  MIDI を開く", "NavButtonPrimary", BTN_H_PRIMARY)
        self.btn_export_xml = SidebarButton("MusicXML 保存", "NavButton")
        self.btn_export_midi = SidebarButton("MIDI 書き出し", "NavButton")
        self.btn_export_report = SidebarButton("分析レポート (HTML)", "NavButton")
        self.btn_export_xml.setEnabled(False)
        self.btn_export_midi.setEnabled(False)
        self.btn_export_report.setEnabled(False)
        v.addWidget(self.btn_open)
        v.addWidget(self.btn_export_xml)
        v.addWidget(self.btn_export_midi)
        v.addWidget(self.btn_export_report)

        v.addSpacing(SECTION_GAP)
        v.addWidget(self._divider())
        v.addSpacing(SECTION_GAP)

        # ── TRANSPORT ──
        v.addWidget(self._section("TRANSPORT"))
        self.btn_play = SidebarButton("▶  再生", "NavButtonPlay", BTN_H)
        self.btn_stop = SidebarButton("■  停止", "NavButtonStop", BTN_H)
        self.btn_play.setEnabled(False)
        self.btn_stop.setEnabled(False)
        self.tempo = QSpinBox()
        self.tempo.setObjectName("SidebarTempo")
        self.tempo.setRange(40, 208)
        self.tempo.setValue(120)
        self.tempo.setPrefix("BPM  ")
        self.tempo.setEnabled(False)
        self.tempo.setFixedHeight(SPIN_H)
        self.tempo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        v.addWidget(self.btn_play)
        v.addWidget(self.btn_stop)
        v.addWidget(self.tempo)

        v.addSpacing(SECTION_GAP)
        v.addWidget(self._divider())
        v.addSpacing(SECTION_GAP)

        # ── ANALYSIS ──
        v.addWidget(self._section("ANALYSIS"))
        hint = QLabel("DETECTED KEY")
        hint.setObjectName("KeyDisplayHint")
        hint.setFixedHeight(22)
        self.key_display = QLabel("—")
        self.key_display.setObjectName("KeyDisplay")
        self.key_display.setWordWrap(True)
        self.key_display.setMinimumHeight(56)
        self.key_display.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        v.addWidget(hint)
        v.addWidget(self.key_display)
        v.addSpacing(8)

        scroll.setWidget(viewport)
        root.addWidget(scroll)

    @staticmethod
    def _section(text: str) -> QLabel:
        lb = QLabel(text)
        lb.setObjectName("SidebarSection")
        lb.setFixedHeight(28)
        lb.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        return lb

    @staticmethod
    def _divider() -> QFrame:
        d = QFrame()
        d.setObjectName("SidebarDivider")
        d.setFixedHeight(1)
        d.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        return d
