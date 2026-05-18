# -*- coding: utf-8 -*-
"""アプリケーション設定ダイアログ。"""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QSpinBox,
    QVBoxLayout,
)

from midi_lab.core.settings import (
    assist_panel_visible_default,
    default_tempo,
    fullscreen_default,
    set_assist_panel_visible_default,
    set_default_tempo,
    set_fullscreen_default,
)


class PreferencesDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("設定")
        self.setMinimumWidth(380)

        root = QVBoxLayout(self)
        intro = QLabel("起動時と編集の既定動作を変更します。")
        intro.setWordWrap(True)
        intro.setObjectName("PanelHint")
        root.addWidget(intro)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._tempo = QSpinBox()
        self._tempo.setRange(40, 208)
        self._tempo.setValue(default_tempo())
        self._tempo.setSuffix(" BPM")
        form.addRow("既定テンポ", self._tempo)

        self._fullscreen = QCheckBox("起動時に全画面表示する")
        self._fullscreen.setChecked(fullscreen_default())
        form.addRow("", self._fullscreen)

        self._assist = QCheckBox("理論アシストパネルを表示する")
        self._assist.setChecked(assist_panel_visible_default())
        form.addRow("", self._assist)

        root.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _accept(self) -> None:
        set_default_tempo(self._tempo.value())
        set_fullscreen_default(self._fullscreen.isChecked())
        set_assist_panel_visible_default(self._assist.isChecked())
        self.accept()

    def fullscreen_default(self) -> bool:
        return self._fullscreen.isChecked()

    def assist_visible(self) -> bool:
        return self._assist.isChecked()

    def default_tempo_value(self) -> int:
        return self._tempo.value()
