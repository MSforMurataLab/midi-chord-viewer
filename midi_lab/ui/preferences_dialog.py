# -*- coding: utf-8 -*-
"""アプリケーション設定ダイアログ。"""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from midi_lab.core.settings import (
    assist_panel_visible_default,
    default_tempo,
    fullscreen_default,
    selected_soundfont,
    set_assist_panel_visible_default,
    set_default_tempo,
    set_fullscreen_default,
)
from midi_lab.core.soundfont_player import (
    apply_soundfont_selection,
    enumerate_soundfont_choices,
    key_to_soundfont_path,
    path_to_soundfont_key,
)


class PreferencesDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("設定")
        self.setMinimumWidth(480)

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

        sf_row = QHBoxLayout()
        self._sf_combo = QComboBox()
        self._populate_soundfont_combo()
        sf_row.addWidget(self._sf_combo, stretch=1)
        btn_browse = QPushButton("参照…")
        btn_browse.clicked.connect(self._browse_sf2)
        sf_row.addWidget(btn_browse)
        form.addRow("SoundFont", sf_row)

        sf_hint = QLabel(
            "サイドバーでも音源を切り替えられます。assets/soundfonts に .sf2 を置くと一覧に表示されます。"
        )
        sf_hint.setWordWrap(True)
        sf_hint.setObjectName("PanelHint")
        form.addRow("", sf_hint)

        root.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._populate_soundfont_combo()

    def _populate_soundfont_combo(self) -> None:
        self._sf_combo.clear()
        saved = selected_soundfont()
        select_idx = 0
        for i, ch in enumerate(enumerate_soundfont_choices()):
            self._sf_combo.addItem(ch.label, ch.key)
            if ch.key == saved or (
                saved and key_to_soundfont_path(saved) == ch.path
            ):
                select_idx = i
        if self._sf_combo.count():
            self._sf_combo.setCurrentIndex(select_idx)

    def _browse_sf2(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "SoundFont を選択",
            str(Path.home()),
            "SoundFont (*.sf2);;すべて (*.*)",
        )
        if not path:
            return
        p = Path(path)
        key = path_to_soundfont_key(p)
        label = p.stem.replace("_", " ")
        idx = self._sf_combo.findData(key)
        if idx < 0:
            self._sf_combo.addItem(f"{label} (外部)", key)
            idx = self._sf_combo.count() - 1
        self._sf_combo.setCurrentIndex(idx)

    def _accept(self) -> None:
        set_default_tempo(self._tempo.value())
        set_fullscreen_default(self._fullscreen.isChecked())
        set_assist_panel_visible_default(self._assist.isChecked())
        key = self._sf_combo.currentData()
        if key:
            apply_soundfont_selection(str(key))
        self.accept()

    def fullscreen_default(self) -> bool:
        return self._fullscreen.isChecked()

    def assist_visible(self) -> bool:
        return self._assist.isChecked()

    def default_tempo_value(self) -> int:
        return self._tempo.value()

    def selected_soundfont_key(self) -> str:
        key = self._sf_combo.currentData()
        return str(key) if key else ""
