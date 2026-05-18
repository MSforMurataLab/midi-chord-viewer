# -*- coding: utf-8 -*-
from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class DropZone(QFrame):
    """ドラッグ＆ドロップ案内エリア（クリックでファイルを開く）。"""

    clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("DropZone")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(96)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(4)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon = QLabel("↓")
        icon.setObjectName("DropZoneIcon")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        txt = QLabel("MIDI をここへドラッグ＆ドロップ")
        txt.setObjectName("DropZoneText")
        txt.setAlignment(Qt.AlignmentFlag.AlignCenter)
        txt.setWordWrap(True)
        lay.addWidget(icon)
        lay.addWidget(txt)

    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)


def _feature_chip(title: str, desc: str) -> QFrame:
    chip = QFrame()
    chip.setObjectName("FeatureChip")
    chip.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    lay = QVBoxLayout(chip)
    lay.setContentsMargins(12, 10, 12, 10)
    lay.setSpacing(2)
    t = QLabel(title)
    t.setObjectName("FeatureChipTitle")
    t.setWordWrap(True)
    d = QLabel(desc)
    d.setObjectName("FeatureChipDesc")
    d.setWordWrap(True)
    lay.addWidget(t)
    lay.addWidget(d)
    return chip


class WelcomePage(QWidget):
    """プロジェクト未読込時のランディング（スクロール・中央配置・伸縮対応）。"""

    open_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("WelcomePage")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setObjectName("WelcomeScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        viewport = QWidget()
        viewport.setObjectName("WelcomeViewport")
        outer = QVBoxLayout(viewport)
        outer.setContentsMargins(24, 24, 24, 24)
        outer.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)

        center_row = QHBoxLayout()
        center_row.addStretch(1)

        card = QFrame()
        card.setObjectName("WelcomeCard")
        card.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        card.setMaximumWidth(560)
        card.setMinimumWidth(320)
        v = QVBoxLayout(card)
        v.setSpacing(12)
        v.setContentsMargins(36, 36, 36, 32)

        icon = QLabel("♫")
        icon.setObjectName("WelcomeIcon")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        title = QLabel("MIDI Chord Lab")
        title.setObjectName("WelcomeTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setWordWrap(True)
        sub = QLabel("Professional Harmony Workstation")
        sub.setObjectName("WelcomeSubtitle")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setWordWrap(True)

        self._drop = DropZone()
        self._drop.clicked.connect(self.open_requested.emit)

        chips_host = QWidget()
        chips_host.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        chips = QGridLayout(chips_host)
        chips.setContentsMargins(0, 0, 0, 0)
        chips.setSpacing(10)
        chips.addWidget(_feature_chip("和声解析", "コード名を自動抽出"), 0, 0)
        chips.addWidget(_feature_chip("分析スタジオ", "ピアノロール・パフォーマンス・声部進行"), 0, 1)
        chips.addWidget(_feature_chip("理論アシスト", "コード・メロディ候補"), 1, 0)
        chips.addWidget(_feature_chip("書き出し", "MusicXML / MIDI / HTML レポート"), 1, 1)
        for c in range(2):
            chips.setColumnStretch(c, 1)

        hint = QLabel("対応: .mid · .midi  —  F11 全画面 · Ctrl+O 開く")
        hint.setObjectName("WelcomeBody")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setWordWrap(True)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        btn = QPushButton("MIDI ファイルを開く")
        btn.setObjectName("BtnPrimary")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        btn.clicked.connect(self.open_requested.emit)
        btn_ghost = QPushButton("フォルダから選択")
        btn_ghost.setObjectName("BtnGhost")
        btn_ghost.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_ghost.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        btn_ghost.clicked.connect(self.open_requested.emit)
        btn_row.addWidget(btn)
        btn_row.addWidget(btn_ghost)

        v.addWidget(icon)
        v.addWidget(title)
        v.addWidget(sub)
        v.addWidget(self._drop)
        v.addWidget(chips_host)
        v.addWidget(hint)
        v.addLayout(btn_row)

        center_row.addWidget(card, 0, Qt.AlignmentFlag.AlignTop)
        center_row.addStretch(1)
        outer.addLayout(center_row)
        outer.addStretch(1)

        scroll.setWidget(viewport)
        root.addWidget(scroll)
