# -*- coding: utf-8 -*-
"""タイムライン表 — コード列の編集デリゲート（文字の二重描画を防ぐ）。"""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont, QPalette
from PyQt6.QtWidgets import QAbstractItemView, QLineEdit, QStyleOptionViewItem, QStyledItemDelegate


class ChordCellDelegate(QStyledItemDelegate):
    """編集時にセル本文を重ね描画しない不透明エディタを使う。"""

    def __init__(self, font: QFont, parent=None):
        super().__init__(parent)
        self._font = font

    def paint(self, painter, option: QStyleOptionViewItem, index) -> None:
        view = option.widget
        if isinstance(view, QAbstractItemView) and view.indexWidget(index) is not None:
            painter.save()
            painter.fillRect(option.rect, QColor("#12121a"))
            painter.restore()
            return
        super().paint(painter, option, index)

    def createEditor(self, parent, option, index):
        editor = QLineEdit(parent)
        editor.setFont(self._font)
        editor.setFrame(False)
        editor.setAutoFillBackground(True)
        pal = editor.palette()
        pal.setColor(QPalette.ColorRole.Base, QColor("#12121a"))
        pal.setColor(QPalette.ColorRole.Text, QColor("#f4f4f5"))
        pal.setColor(QPalette.ColorRole.Highlight, QColor("#f59e0b"))
        pal.setColor(QPalette.ColorRole.HighlightedText, QColor("#0c0c12"))
        editor.setPalette(pal)
        return editor

    def setEditorData(self, editor, index) -> None:
        text = index.data(Qt.ItemDataRole.DisplayRole) or ""
        editor.setText(str(text))
        editor.selectAll()

    def setModelData(self, editor, model, index) -> None:
        model.setData(index, editor.text(), Qt.ItemDataRole.EditRole)

    def updateEditorGeometry(self, editor, option, index) -> None:
        editor.setGeometry(option.rect.adjusted(4, 8, -4, -8))
