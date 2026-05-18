# -*- coding: utf-8 -*-
"""声部進行パネル — 連続和音間の移動を表形式で表示。"""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

VL_COL_IDX = 0
VL_COL_FROM = 1
VL_COL_TO = 2
VL_COL_MOTION = 3
VL_COL_KIND = 4
VL_COL_TOTAL = 5

VL_HEADERS = ["#", "前の和音", "次の和音", "声部移動", "種別", "総半音"]

# 声部移動列の最小幅（「60→64(+4) · …」が読める幅）
VL_MOTION_MIN_WIDTH = 320
VL_LABEL_MAX_WIDTH = 200


class VoiceLeadingPanel(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("PanelCard")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        bar = QFrame()
        bar.setObjectName("PanelTitleBar")
        row = QHBoxLayout(bar)
        row.setContentsMargins(16, 10, 16, 10)
        accent = QLabel("│")
        accent.setObjectName("PanelTitleAccent")
        col = QVBoxLayout()
        t = QLabel("声部進行")
        t.setObjectName("PanelTitle")
        sub = QLabel("連続する和声音価の最小移動マッチングと順行／逆行の分類")
        sub.setObjectName("PanelHint")
        sub.setWordWrap(True)
        col.addWidget(t)
        col.addWidget(sub)
        row.addWidget(accent)
        row.addLayout(col)
        row.addStretch(1)
        root.addWidget(bar)

        self._summary = QLabel("—")
        self._summary.setObjectName("TimelineStats")
        sw = QFrame()
        sw.setObjectName("TimelineStatsBar")
        sl = QHBoxLayout(sw)
        sl.setContentsMargins(16, 8, 16, 8)
        sl.addWidget(self._summary)
        root.addWidget(sw)

        self.table = QTableWidget(0, len(VL_HEADERS))
        self.table.setHorizontalHeaderLabels(VL_HEADERS)
        self.table.setObjectName("TimelineTable")
        hdr = self.table.horizontalHeader()
        hdr.setStretchLastSection(False)
        hdr.setMinimumSectionSize(48)
        hdr.setSectionResizeMode(VL_COL_IDX, QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(VL_COL_FROM, QHeaderView.ResizeMode.Interactive)
        hdr.setSectionResizeMode(VL_COL_TO, QHeaderView.ResizeMode.Interactive)
        hdr.setSectionResizeMode(VL_COL_MOTION, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(VL_COL_KIND, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(VL_COL_TOTAL, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setColumnWidth(VL_COL_IDX, 52)
        self.table.setColumnWidth(VL_COL_FROM, 160)
        self.table.setColumnWidth(VL_COL_TO, 160)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.table.setWordWrap(False)

        self._font = QFont()
        self._font.setPointSize(12)
        self._font_mono = QFont("Consolas")
        self._font_mono.setPointSize(11)

        body = QFrame()
        bw = QVBoxLayout(body)
        bw.setContentsMargins(12, 4, 12, 14)
        bw.addWidget(self.table, stretch=1)
        root.addWidget(body, stretch=1)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self.table.rowCount() > 0:
            self._balance_columns()

    def set_summary(self, text: str) -> None:
        self._summary.setText(text)

    def clear_data(self) -> None:
        self.table.setRowCount(0)
        self.set_summary("—")

    def _balance_columns(self) -> None:
        """声部移動列を広く確保し、和音名列は上限付きで収める。"""
        vw = max(self.table.viewport().width(), 720)
        idx_w = 52
        self.table.setColumnWidth(VL_COL_IDX, idx_w)
        self.table.resizeColumnToContents(VL_COL_KIND)
        self.table.resizeColumnToContents(VL_COL_TOTAL)
        kind_w = min(max(self.table.columnWidth(VL_COL_KIND), 64), 96)
        total_w = min(max(self.table.columnWidth(VL_COL_TOTAL), 56), 80)
        self.table.setColumnWidth(VL_COL_KIND, kind_w)
        self.table.setColumnWidth(VL_COL_TOTAL, total_w)

        label_w = min(
            VL_LABEL_MAX_WIDTH,
            max(120, int((vw - idx_w - kind_w - total_w - VL_MOTION_MIN_WIDTH) * 0.35)),
        )
        self.table.setColumnWidth(VL_COL_FROM, label_w)
        self.table.setColumnWidth(VL_COL_TO, label_w)

        motion_w = max(VL_MOTION_MIN_WIDTH, vw - idx_w - label_w * 2 - kind_w - total_w - 8)
        self.table.setColumnWidth(VL_COL_MOTION, motion_w)

    def populate(self, rows: list[tuple]) -> None:
        """rows: (index, from_label, to_label, motion_text, kind, total)."""
        self.table.setRowCount(0)
        read_only = Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled
        for row in rows:
            r = self.table.rowCount()
            self.table.insertRow(r)
            for col, val, mono in (
                (VL_COL_IDX, str(row[0]), True),
                (VL_COL_FROM, row[1], False),
                (VL_COL_TO, row[2], False),
                (VL_COL_MOTION, row[3], True),
                (VL_COL_KIND, row[4], False),
                (VL_COL_TOTAL, str(row[5]), True),
            ):
                it = QTableWidgetItem(val)
                it.setFlags(read_only)
                it.setFont(self._font_mono if mono else self._font)
                if col in (VL_COL_FROM, VL_COL_TO, VL_COL_MOTION):
                    it.setToolTip(val)
                self.table.setItem(r, col, it)
        self._balance_columns()
