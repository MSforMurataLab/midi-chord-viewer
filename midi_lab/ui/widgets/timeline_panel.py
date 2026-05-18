# -*- coding: utf-8 -*-
"""タイムライン専用パネル — 和声イベントを表形式で大きく表示。"""
from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction, QFont
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMenu,
    QSizePolicy,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

from midi_lab.ui.widgets.timeline_delegate import ChordCellDelegate

COL_BEAT = 0
COL_OFFSET = 1
COL_DURATION = 2
COL_LABEL = 3
COL_ROMAN = 4
COL_PITCHES = 5

HEADERS = ["拍", "開始（拍）", "長さ", "コード／音名", "機能", "構成音"]


class TimelinePanel(QFrame):
    """編集可能な和声タイムライン表。"""

    LABEL_COL = COL_LABEL
    insert_row_requested = pyqtSignal(int)
    delete_row_requested = pyqtSignal(int)
    duplicate_row_requested = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("PanelCard")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        bar = self._title_bar()
        root.addWidget(bar)

        self._stats = QLabel("イベント: —")
        self._stats.setObjectName("TimelineStats")
        stats_wrap = QFrame()
        stats_wrap.setObjectName("TimelineStatsBar")
        sw = QHBoxLayout(stats_wrap)
        sw.setContentsMargins(16, 8, 16, 8)
        sw.addWidget(self._stats)
        sw.addStretch(1)
        root.addWidget(stats_wrap)

        self.table = QTableWidget(0, len(HEADERS))
        self.table.setHorizontalHeaderLabels(HEADERS)
        self.table.setObjectName("TimelineTable")
        hdr = self.table.horizontalHeader()
        hdr.setStretchLastSection(True)
        hdr.setMinimumSectionSize(48)
        hdr.setSectionResizeMode(COL_BEAT, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(COL_OFFSET, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(COL_DURATION, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(COL_LABEL, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(COL_ROMAN, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(COL_PITCHES, QHeaderView.ResizeMode.Stretch)
        hdr.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        vhdr = self.table.verticalHeader()
        vhdr.setVisible(False)
        vhdr.setDefaultSectionSize(44)
        vhdr.setMinimumWidth(0)

        self._font = QFont()
        self._font.setPointSize(13)
        self._font_mono = QFont("Consolas")
        self._font_mono.setPointSize(12)

        self.table.setItemDelegateForColumn(COL_LABEL, ChordCellDelegate(self._font, self.table))
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked)
        self.table.setShowGrid(True)
        self.table.setWordWrap(False)
        self.table.setTextElideMode(Qt.TextElideMode.ElideNone)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_row_menu)

        hint = QLabel(
            "コード／音名・長さをダブルクリックで編集 · 右クリックで行の追加／削除 · 理論候補と鍵盤が連動"
        )
        hint.setObjectName("PanelHint")
        hint.setWordWrap(True)
        hint_wrap = QFrame()
        hw = QVBoxLayout(hint_wrap)
        hw.setContentsMargins(16, 0, 16, 8)
        hw.addWidget(hint)

        body = QFrame()
        body.setStyleSheet("background: transparent; border: none;")
        bw = QVBoxLayout(body)
        bw.setContentsMargins(12, 4, 12, 14)
        bw.setSpacing(6)
        bw.addWidget(hint_wrap)
        bw.addWidget(self.table, stretch=1)
        root.addWidget(body, stretch=1)

    def _title_bar(self) -> QFrame:
        bar = QFrame()
        bar.setObjectName("PanelTitleBar")
        row = QHBoxLayout(bar)
        row.setContentsMargins(16, 10, 16, 10)
        accent = QLabel("│")
        accent.setObjectName("PanelTitleAccent")
        col = QVBoxLayout()
        col.setSpacing(2)
        t = QLabel("和声タイムライン")
        t.setObjectName("PanelTitle")
        sub = QLabel("MIDI から抽出したコード／単音（時系列順）")
        sub.setObjectName("PanelHint")
        sub.setWordWrap(True)
        col.addWidget(t)
        col.addWidget(sub)
        row.addWidget(accent)
        row.addLayout(col)
        row.addStretch(1)
        return bar

    def set_stats(self, text: str) -> None:
        self._stats.setText(text)

    def _show_row_menu(self, pos) -> None:
        index = self.table.indexAt(pos)
        row = index.row() if index.isValid() else self.table.currentRow()
        menu = QMenu(self)
        insert_act = QAction("この下に行を追加", self)
        dup_act = QAction("行を複製", self)
        del_act = QAction("行を削除", self)
        insert_act.triggered.connect(lambda: self.insert_row_requested.emit(max(row, 0)))
        dup_act.triggered.connect(
            lambda: self.duplicate_row_requested.emit(max(row, 0))
        )
        del_act.triggered.connect(lambda: self.delete_row_requested.emit(max(row, 0)))
        menu.addAction(insert_act)
        if row >= 0:
            menu.addAction(dup_act)
            menu.addAction(del_act)
        menu.exec(self.table.viewport().mapToGlobal(pos))
