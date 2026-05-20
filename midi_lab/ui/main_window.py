# -*- coding: utf-8 -*-
"""メインウィンドウ — プロフェッショナル 3 ペイン UI。"""
from __future__ import annotations

import traceback
from pathlib import Path

from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QAction, QDragEnterEvent, QDropEvent, QKeySequence
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QSplitter,
    QStackedWidget,
    QStatusBar,
    QTabWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from music21 import chord as m21_chord
from music21 import key as m21_key
from music21 import note as m21_note
from music21 import pitch as m21_pitch
from music21 import stream as m21_stream

from midi_lab.core.analysis_build_worker import AnalysisBuildWorker, AnalysisResult
from midi_lab.core.edit_history import EditHistory, TimelineSnapshot
from midi_lab.core.analysis_report import build_analysis_html
from midi_lab.core.functional_harmony import functional_label
from midi_lab.core.load_worker import LoadedScore, MidiLoadWorker
from midi_lab.core.note_events import NoteEvent
from midi_lab.core.performance_analytics import (
    analyze_performance,
    build_performance_dashboard_figure,
    report_summary_text,
)
from midi_lab.core.pianoroll_plot import build_pianoroll_figure_from_notes
from midi_lab.core.settings import (
    add_recent_file,
    assist_panel_visible_default,
    default_tempo,
    recent_files,
    set_fullscreen_default,
)
from midi_lab.ui.preferences_dialog import PreferencesDialog
from midi_lab.core.voice_leading import analyze_voice_leading, format_motions
from midi_lab.core.harmony import (
    clear_chord_figure_cache,
    detect_key_for_score,
    event_display_label,
    harmony_chord_for_melody_at_row,
    melodic_note_candidates,
    melody_midi_from_previous,
    parse_chord_cell,
    targeted_chord_suggestions,
    voice_leading_label,
)
from midi_lab.core.playback import PlaybackThread, stop_audio_output
from midi_lab.core.score import build_playback_timeline, collect_harmony_events, rebuild_stream_from_table
from midi_lab import __version__
from midi_lab.ui.widgets import (
    LoadingOverlay,
    PianoKeyboard,
    ScoreCanvas,
    SidebarPanel,
    TimelinePanel,
    VoiceLeadingPanel,
    VisualizerPanel,
    WelcomePage,
)
from midi_lab.ui.widgets.visualizer_panel import VIDEO_FILTER
from midi_lab.ui.widgets.timeline_panel import (
    COL_BEAT,
    COL_DURATION,
    COL_LABEL,
    COL_OFFSET,
    COL_PITCHES,
    COL_ROMAN,
)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MIDI Chord Lab")
        self.resize(1480, 900)
        self.setMinimumSize(1100, 680)
        self.setAcceptDrops(True)

        self._original_score = None
        self._work_flat: m21_stream.Stream | None = None
        self._current_path: Path | None = None
        self._detected_key: m21_key.Key | None = None
        self._row_ql: list[float] = []
        self._suppress_table = False
        self._playback: PlaybackThread | None = None
        self._playback_highlighting = False
        self._load_worker: MidiLoadWorker | None = None
        self._analysis_worker: AnalysisBuildWorker | None = None
        self._assist_visible = True
        self._assist_width = 300
        self._body_split: QSplitter | None = None
        self._sidebar_min_width = SidebarPanel.WIDTH
        self._note_events: list[NoteEvent] = []
        self._voice_steps = []
        self._dirty = False
        self._edit_history = EditHistory()
        self._analysis_debounce = QTimer(self)
        self._analysis_debounce.setSingleShot(True)
        self._analysis_debounce.setInterval(400)
        self._analysis_debounce.timeout.connect(self._start_analysis_build)
        self._hist_cell_pushed = False

        self._build_menus()
        self._build_ui()
        self._wire_signals()
        self.statusBar().showMessage("MIDI ファイルを開くか、ウィンドウへドロップしてください")

    def _build_menus(self) -> None:
        open_act = QAction("MIDI を開く…", self)
        open_act.setShortcut(QKeySequence.StandardKey.Open)
        open_act.triggered.connect(self.open_midi)
        self._export_xml_act = QAction("MusicXML を保存…", self)
        self._export_xml_act.setShortcut("Ctrl+Shift+S")
        self._export_xml_act.setEnabled(False)
        self._export_xml_act.triggered.connect(self.export_musicxml)
        self._export_midi_act = QAction("MIDI を書き出し…", self)
        self._export_midi_act.setShortcut("Ctrl+Shift+M")
        self._export_midi_act.setEnabled(False)
        self._export_midi_act.triggered.connect(self.export_midi_file)
        self._export_report_act = QAction("分析レポート (HTML)…", self)
        self._export_report_act.setShortcut("Ctrl+Shift+R")
        self._export_report_act.setEnabled(False)
        self._export_report_act.triggered.connect(self.export_analysis_report)
        self._export_video_act = QAction("ビジュアライザ動画を書き出し…", self)
        self._export_video_act.setShortcut("Ctrl+Shift+V")
        self._export_video_act.setEnabled(False)
        self._export_video_act.triggered.connect(self.export_visualizer_video)
        self._save_act = QAction("MIDI を保存", self)
        self._save_act.setShortcut(QKeySequence.StandardKey.Save)
        self._save_act.setEnabled(False)
        self._save_act.triggered.connect(self.save_current_midi)
        self._undo_act = QAction("元に戻す", self)
        self._undo_act.setShortcut(QKeySequence.StandardKey.Undo)
        self._undo_act.setEnabled(False)
        self._undo_act.triggered.connect(self.undo_edit)
        self._redo_act = QAction("やり直し", self)
        self._redo_act.setShortcut(QKeySequence.StandardKey.Redo)
        self._redo_act.setEnabled(False)
        self._redo_act.triggered.connect(self.redo_edit)
        play_act = QAction("再生", self)
        play_act.setShortcut("Ctrl+Return")
        play_act.triggered.connect(self.play_transport)
        stop_act = QAction("停止", self)
        stop_act.setShortcut("Ctrl+.")
        stop_act.triggered.connect(self.stop_transport)

        self._fullscreen_act = QAction("全画面表示", self)
        self._fullscreen_act.setShortcut("F11")
        self._fullscreen_act.setCheckable(True)
        self._fullscreen_act.setChecked(True)
        self._fullscreen_act.triggered.connect(self._menu_toggle_fullscreen)
        exit_fs_act = QAction("全画面を終了", self)
        exit_fs_act.setShortcut("Escape")
        exit_fs_act.triggered.connect(self._exit_fullscreen)
        self._assist_act = QAction("理論アシストパネル", self)
        self._assist_act.setShortcut("Ctrl+\\")
        self._assist_act.setCheckable(True)
        self._assist_act.setChecked(True)
        self._assist_act.triggered.connect(self._toggle_assist_panel)

        self._register_assoc_act = QAction("MIDI ファイルの関連付けを登録…", self)
        self._register_assoc_act.triggered.connect(self._register_midi_association)
        self._unregister_assoc_act = QAction("MIDI ファイルの関連付けを解除…", self)
        self._unregister_assoc_act.triggered.connect(self._unregister_midi_association)
        prefs_act = QAction("設定…", self)
        prefs_act.triggered.connect(self._show_preferences)
        about_act = QAction("MIDI Chord Lab について", self)
        about_act.triggered.connect(self._show_about)
        quit_act = QAction("終了", self)
        quit_act.setShortcut(QKeySequence.StandardKey.Quit)
        quit_act.triggered.connect(self.close)

        file_menu = self.menuBar().addMenu("ファイル(&F)")
        file_menu.addAction(open_act)
        self._recent_menu = file_menu.addMenu("最近使ったファイル")
        self._recent_menu.aboutToShow.connect(self._populate_recent_menu)
        file_menu.addSeparator()
        file_menu.addAction(self._export_xml_act)
        file_menu.addAction(self._export_midi_act)
        file_menu.addAction(self._export_report_act)
        file_menu.addAction(self._export_video_act)
        file_menu.addAction(self._save_act)
        file_menu.addSeparator()

        edit_menu = self.menuBar().addMenu("編集(&E)")
        edit_menu.addAction(self._undo_act)
        edit_menu.addAction(self._redo_act)

        file_menu.addSeparator()
        file_menu.addAction(self._register_assoc_act)
        file_menu.addAction(self._unregister_assoc_act)
        file_menu.addSeparator()
        file_menu.addAction(quit_act)

        view_menu = self.menuBar().addMenu("表示(&V)")
        view_menu.addAction(self._fullscreen_act)
        view_menu.addAction(exit_fs_act)
        view_menu.addSeparator()
        view_menu.addAction(self._assist_act)

        transport_menu = self.menuBar().addMenu("再生(&P)")
        transport_menu.addAction(play_act)
        transport_menu.addAction(stop_act)

        help_menu = self.menuBar().addMenu("ヘルプ(&H)")
        help_menu.addAction(prefs_act)
        help_menu.addAction(about_act)

    def _build_ui(self) -> None:
        root = QWidget()
        root.setObjectName("AppRoot")
        layout = QVBoxLayout(root)
        layout.setContentsMargins(20, 14, 20, 12)
        layout.setSpacing(14)

        header = QFrame()
        header.setObjectName("AppHeader")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(18, 14, 18, 14)
        hl.setSpacing(14)

        logo = QFrame()
        logo.setObjectName("LogoMark")
        logo.setFixedSize(48, 48)
        logo.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        logo_l = QVBoxLayout(logo)
        logo_l.setContentsMargins(0, 0, 0, 0)
        logo_t = QLabel("MC")
        logo_t.setObjectName("LogoMarkText")
        logo_t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_l.addWidget(logo_t)
        hl.addWidget(logo)

        brand = QVBoxLayout()
        brand.setSpacing(3)
        t = QLabel("MIDI Chord Lab")
        t.setObjectName("HeaderTitle")
        sub = QLabel(f"Studio Graphite  ·  v{__version__}")
        sub.setObjectName("HeaderSubtitle")
        sub.setWordWrap(True)
        brand.addWidget(t)
        brand.addWidget(sub)
        hl.addLayout(brand)
        hl.addStretch(1)
        self._btn_fullscreen = QPushButton("⛶")
        self._btn_fullscreen.setObjectName("HeaderToolButton")
        self._btn_fullscreen.setFixedSize(44, 44)
        self._btn_fullscreen.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._btn_fullscreen.setToolTip("全画面切替 (F11)")
        self._btn_fullscreen.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_fullscreen.clicked.connect(self._toggle_fullscreen)
        hl.addWidget(self._btn_fullscreen, alignment=Qt.AlignmentFlag.AlignVCenter)
        self._header_badge = QLabel("STANDBY")
        self._header_badge.setObjectName("HeaderBadge")
        hl.addWidget(self._header_badge, alignment=Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(header)

        self._body_split = QSplitter(Qt.Orientation.Horizontal)
        self._body_split.setObjectName("BodySplit")
        self._body_split.setChildrenCollapsible(False)
        self._body_split.setHandleWidth(8)

        sidebar = self._build_sidebar()
        self._body_split.addWidget(sidebar)

        self._stack = QStackedWidget()
        self._stack.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._welcome = WelcomePage()
        self._stack.addWidget(self._welcome)
        self._workspace = self._build_workspace()
        self._stack.addWidget(self._workspace)
        self._stack.setCurrentIndex(0)
        self._body_split.addWidget(self._stack)

        self._assist_panel = self._build_assist_panel()
        self._body_split.addWidget(self._assist_panel)
        self._body_split.setStretchFactor(0, 0)
        self._body_split.setStretchFactor(1, 1)
        self._body_split.setStretchFactor(2, 0)
        self._body_split.setSizes([self._sidebar_min_width, 900, 300])
        for i in range(3):
            self._body_split.setCollapsible(i, False)
        self._body_split.splitterMoved.connect(self._enforce_splitter_sizes)

        layout.addWidget(self._body_split, stretch=1)

        piano_bar = QFrame()
        piano_bar.setObjectName("PianoBar")
        piano_bar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        pb = QVBoxLayout(piano_bar)
        pb.setContentsMargins(16, 12, 16, 14)
        pb.setSpacing(8)
        piano_hdr = QHBoxLayout()
        pt = QLabel("仮想鍵盤")
        pt.setObjectName("PianoBarTitle")
        ph = QLabel("選択・再生中の音をアンバーでハイライト")
        ph.setObjectName("PianoBarHint")
        piano_hdr.addWidget(pt)
        piano_hdr.addStretch(1)
        piano_hdr.addWidget(ph)
        pb.addLayout(piano_hdr)
        self.piano = PianoKeyboard()
        pb.addWidget(self.piano)
        layout.addWidget(piano_bar)

        self.setCentralWidget(root)
        self._loading = LoadingOverlay(root)
        self._loading.hide()
        sb = QStatusBar()
        sb.setSizeGripEnabled(True)
        self._status_mode = QLabel("待機中")
        self._status_mode.setObjectName("StatusPill")
        self._status_events = QLabel("— イベント")
        self._status_events.setObjectName("StatusPill")
        sb.addPermanentWidget(self._status_mode)
        sb.addPermanentWidget(self._status_events)
        self.setStatusBar(sb)

    def _enforce_splitter_sizes(self, _pos: int = 0, _index: int = 0) -> None:
        if self._body_split is None:
            return
        sizes = self._body_split.sizes()
        if len(sizes) < 3:
            return
        min_side = self._sidebar_min_width
        min_center = 380
        changed = False
        if sizes[0] != min_side:
            delta = min_side - sizes[0]
            sizes[0] = min_side
            sizes[1] = max(sizes[1] - delta, min_center)
            changed = True
        if sizes[1] < min_center:
            delta = min_center - sizes[1]
            sizes[1] = min_center
            sizes[0] = max(sizes[0] - delta, min_side)
            changed = True
        if changed:
            self._body_split.blockSignals(True)
            self._body_split.setSizes(sizes)
            self._body_split.blockSignals(False)

    def _build_sidebar(self) -> SidebarPanel:
        panel = SidebarPanel()
        self._sidebar_panel = panel
        self._btn_open = panel.btn_open
        self._btn_export_xml = panel.btn_export_xml
        self._btn_export_midi = panel.btn_export_midi
        self._btn_export_report = panel.btn_export_report
        self._btn_play = panel.btn_play
        self._btn_stop = panel.btn_stop
        self._tempo = panel.tempo
        self._key_display = panel.key_display
        return panel

    def _build_workspace(self) -> QWidget:
        wrap = QWidget()
        lay = QVBoxLayout(wrap)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        self._workspace_tabs = QTabWidget()
        self._workspace_tabs.setDocumentMode(True)
        self._timeline_panel = TimelinePanel()
        self.table = self._timeline_panel.table
        self._table_font = self._timeline_panel._font
        self._table_font_mono = self._timeline_panel._font_mono
        self._workspace_tabs.addTab(self._timeline_panel, "和声タイムライン")
        self._pianoroll_canvas = ScoreCanvas()
        self._perf_canvas = ScoreCanvas()
        self._voice_panel = VoiceLeadingPanel()
        self._visualizer_panel = VisualizerPanel()
        self._workspace_tabs.addTab(self._pianoroll_canvas, "ピアノロール")
        self._workspace_tabs.addTab(self._perf_canvas, "パフォーマンス")
        self._workspace_tabs.addTab(self._voice_panel, "声部進行")
        self._workspace_tabs.addTab(self._visualizer_panel, "MIDIビジュアライザ")
        self._workspace_tabs.currentChanged.connect(self._on_workspace_tab_changed)
        lay.addWidget(self._workspace_tabs)
        return wrap

    def _build_assist_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("PanelCard")
        panel.setMinimumWidth(260)
        panel.setMaximumWidth(420)
        panel.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        v = QVBoxLayout(panel)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        bar = QFrame()
        bar.setObjectName("PanelTitleBar")
        row = QHBoxLayout(bar)
        row.setContentsMargins(16, 10, 16, 10)
        accent = QLabel("│")
        accent.setObjectName("PanelTitleAccent")
        col = QVBoxLayout()
        col.setSpacing(2)
        t = QLabel("理論アシスト")
        t.setObjectName("PanelTitle")
        col.addWidget(t)
        row.addWidget(accent)
        row.addLayout(col)
        row.addStretch(1)
        badge = QLabel("理論ヒント")
        badge.setObjectName("AssistBadge")
        row.addWidget(badge, alignment=Qt.AlignmentFlag.AlignVCenter)
        v.addWidget(bar)

        tabs_wrap = QFrame()
        tabs_wrap.setStyleSheet("background: transparent; border: none;")
        tw = QVBoxLayout(tabs_wrap)
        tw.setContentsMargins(12, 8, 12, 8)
        self._tabs = QTabWidget()
        self._chord_list = QListWidget()
        self._melody_list = QListWidget()
        self._tabs.addTab(self._chord_list, "コード")
        self._tabs.addTab(self._melody_list, "メロディ")
        tw.addWidget(self._tabs, stretch=1)
        v.addWidget(tabs_wrap, stretch=1)

        foot_wrap = QFrame()
        foot_wrap.setStyleSheet("background: transparent; border: none;")
        fw = QVBoxLayout(foot_wrap)
        fw.setContentsMargins(12, 0, 12, 14)
        foot = QLabel("ダブルクリックでセルに適用")
        foot.setObjectName("PanelHint")
        foot.setAlignment(Qt.AlignmentFlag.AlignCenter)
        fw.addWidget(foot)
        v.addWidget(foot_wrap)
        return panel

    def _wire_signals(self) -> None:
        self._welcome.open_requested.connect(self.open_midi)
        self._welcome.file_dropped.connect(self.load_file)
        self._timeline_panel.insert_row_requested.connect(self._insert_row_after)
        self._timeline_panel.duplicate_row_requested.connect(self._duplicate_row)
        self._timeline_panel.delete_row_requested.connect(self._delete_row)
        self._btn_open.clicked.connect(self.open_midi)
        self._btn_export_xml.clicked.connect(self.export_musicxml)
        self._btn_export_midi.clicked.connect(self.export_midi_file)
        self._btn_export_report.clicked.connect(self.export_analysis_report)
        self._btn_play.clicked.connect(self.play_transport)
        self._btn_stop.clicked.connect(self.stop_transport)
        self.table.cellChanged.connect(self._on_table_cell_changed)
        self.table.itemSelectionChanged.connect(self._on_table_selection_changed)
        self._chord_list.itemDoubleClicked.connect(self._on_chord_suggestion)
        self._melody_list.itemDoubleClicked.connect(self._on_melody_suggestion)

    def _populate_recent_menu(self) -> None:
        self._recent_menu.clear()
        paths = recent_files()
        if not paths:
            empty = QAction("（履歴なし）", self)
            empty.setEnabled(False)
            self._recent_menu.addAction(empty)
            return
        for path in paths:
            name = Path(path).name
            act = QAction(name, self)
            act.setToolTip(path)
            act.triggered.connect(lambda _=False, p=path: self.load_file(p))
            self._recent_menu.addAction(act)

    def _refresh_layout(self) -> None:
        """全画面切替・リサイズ後にレイアウトを再計算。"""
        self._enforce_splitter_sizes()
        cw = self.centralWidget()
        if cw is not None:
            cw.layout().activate()
            cw.updateGeometry()
        if self._body_split is not None:
            self._body_split.updateGeometry()
        self._stack.updateGeometry()
        self._welcome.updateGeometry()
        if hasattr(self, "_loading") and cw is not None:
            self._loading.setGeometry(cw.rect())

    def _toggle_fullscreen(self) -> None:
        if self.isFullScreen():
            self.showNormal()
            self.showMaximized()
            set_fullscreen_default(False)
        else:
            self.showFullScreen()
            set_fullscreen_default(True)
        self._fullscreen_act.setChecked(self.isFullScreen())
        QTimer.singleShot(0, self._refresh_layout)

    def _menu_toggle_fullscreen(self, checked: bool) -> None:
        if checked and not self.isFullScreen():
            self.showFullScreen()
            set_fullscreen_default(True)
        elif not checked and self.isFullScreen():
            self.showNormal()
            self.showMaximized()
            set_fullscreen_default(False)
        self._fullscreen_act.setChecked(self.isFullScreen())
        QTimer.singleShot(0, self._refresh_layout)

    def _exit_fullscreen(self) -> None:
        if self.isFullScreen():
            self.showNormal()
            self.showMaximized()
            self._fullscreen_act.setChecked(False)
            set_fullscreen_default(False)
            QTimer.singleShot(0, self._refresh_layout)

    def _toggle_assist_panel(self, visible: bool | None = None) -> None:
        if visible is None:
            visible = not self._assist_visible
        self._assist_visible = visible
        self._assist_act.setChecked(visible)
        if self._body_split is None:
            return
        sizes = self._body_split.sizes()
        if len(sizes) < 3:
            return
        if visible:
            w = max(self._assist_width, 260)
            center = max(sizes[1] - w, 400)
            self._body_split.setSizes([sizes[0], center, w])
        else:
            self._assist_width = sizes[2] if sizes[2] > 80 else 300
            self._body_split.setSizes([sizes[0], sizes[1] + sizes[2], 0])

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cw = self.centralWidget()
        if cw is not None and hasattr(self, "_loading"):
            self._loading.setGeometry(cw.rect())

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(50, self._refresh_layout)
        if not assist_panel_visible_default():
            QTimer.singleShot(80, lambda: self._toggle_assist_panel(False))

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_F11:
            self._toggle_fullscreen()
            event.accept()
            return
        if event.key() == Qt.Key.Key_Escape and self.isFullScreen():
            self._exit_fullscreen()
            event.accept()
            return
        if event.key() == Qt.Key.Key_Space and self._work_flat is not None:
            if self.table.state() == QAbstractItemView.State.EditingState:
                super().keyPressEvent(event)
                return
            if self._playback is not None and self._playback.isRunning():
                self.stop_transport()
            else:
                self.play_transport()
            event.accept()
            return
        super().keyPressEvent(event)

    def closeEvent(self, event):
        from midi_lab.diagnostics import log_stack

        log_stack("MainWindow.closeEvent")
        if self._dirty and self._work_flat is not None:
            ans = QMessageBox.question(
                self,
                "終了の確認",
                "保存していない変更があります。終了しますか？",
                QMessageBox.StandardButton.Save
                | QMessageBox.StandardButton.Discard
                | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Save,
            )
            if ans == QMessageBox.StandardButton.Cancel:
                event.ignore()
                return
            if ans == QMessageBox.StandardButton.Save:
                if not self.save_current_midi(silent=True):
                    event.ignore()
                    return
        self.stop_transport()
        self._stop_analysis_build()
        if hasattr(self, "_visualizer_panel"):
            self._visualizer_panel.stop_export()
        if self._load_worker is not None and self._load_worker.isRunning():
            self._load_worker.requestInterruption()
            self._load_worker.wait(3000)
        super().closeEvent(event)

    def _register_midi_association(self) -> None:
        import sys

        if not getattr(sys, "frozen", False):
            QMessageBox.information(
                self,
                "関連付け",
                "ファイル関連付けは配布版の MIDIChordViewer.exe から登録してください。\n\n"
                "開発時は次のように MIDI を直接開けます:\n"
                "  python app.py 曲.mid\n\n"
                "ビルド後: dist\\MIDIChordViewer\\MIDIChordViewer.exe を実行し、\n"
                "ファイル →「MIDI ファイルの関連付けを登録」",
            )
            return

        from midi_lab.core.file_association import register_midi_associations

        ok, msg = register_midi_associations()
        if ok:
            QMessageBox.information(self, "関連付け", msg)
        else:
            QMessageBox.warning(self, "関連付け", msg)

    def _unregister_midi_association(self) -> None:
        from midi_lab.core.file_association import unregister_midi_associations

        ok, msg = unregister_midi_associations()
        if ok:
            QMessageBox.information(self, "関連付け", msg)
        else:
            QMessageBox.warning(self, "関連付け", msg)

    def _show_about(self) -> None:
        QMessageBox.about(
            self,
            "MIDI Chord Lab",
            f"<h3>MIDI Chord Lab</h3>"
            f"<p>バージョン {__version__}</p>"
            "<p>和声解析・コード編集・分析スタジオ・理論候補を一体化した"
            "デスクトップ和声ワークステーションです。</p>"
            "<p><b>ショートカット</b><br>"
            "Ctrl+O 開く · Ctrl+S 保存 · Ctrl+Z / Ctrl+Y 元に戻す／やり直し<br>"
            "Space 再生／停止 · Ctrl+Enter 再生 · Ctrl+. 停止<br>"
            "F11 全画面 · Esc 全画面終了 · Ctrl+\\ 理論アシスト<br>"
            "Ctrl+Shift+S MusicXML · Ctrl+Shift+M MIDI 書き出し · Ctrl+Shift+R レポート</p>",
        )

    def _show_preferences(self) -> None:
        dlg = PreferencesDialog(self)
        if dlg.exec() != dlg.DialogCode.Accepted:
            return
        if self._work_flat is None:
            self._tempo.setValue(dlg.default_tempo_value())
        if dlg.fullscreen_default() and not self.isFullScreen():
            self.showFullScreen()
            self._fullscreen_act.setChecked(True)
        elif not dlg.fullscreen_default() and self.isFullScreen():
            self._exit_fullscreen()
        self._toggle_assist_panel(dlg.assist_visible())

    def _current_snapshot(self) -> TimelineSnapshot:
        return TimelineSnapshot(tuple(self._row_tuples()), tuple(self._row_ql))

    def _push_history(self) -> None:
        if self._work_flat is None:
            return
        self._edit_history.push(list(self._row_tuples()), list(self._row_ql))
        self._update_undo_actions()

    def _update_undo_actions(self) -> None:
        on = self._work_flat is not None
        self._undo_act.setEnabled(on and self._edit_history.can_undo())
        self._redo_act.setEnabled(on and self._edit_history.can_redo())

    def _restore_snapshot(self, snap: TimelineSnapshot) -> None:
        assert self._work_flat is not None
        self._row_ql = list(snap.row_ql)
        rows = list(snap.rows)
        self._work_flat = rebuild_stream_from_table(self._work_flat, rows, self._row_ql)
        self._fill_table_from_work()
        self._schedule_analysis_refresh()

    def undo_edit(self) -> None:
        if not self._edit_history.can_undo():
            return
        snap = self._edit_history.undo(self._current_snapshot())
        if snap is not None:
            self._restore_snapshot(snap)
            self._mark_dirty()

    def redo_edit(self) -> None:
        if not self._edit_history.can_redo():
            return
        snap = self._edit_history.redo(self._current_snapshot())
        if snap is not None:
            self._restore_snapshot(snap)
            self._mark_dirty()

    def _mark_dirty(self) -> None:
        if self._work_flat is None:
            return
        self._dirty = True
        self._update_window_title()
        self._save_act.setEnabled(True)

    def _clear_dirty(self) -> None:
        self._dirty = False
        self._update_window_title()

    def _update_window_title(self) -> None:
        if self._current_path is None:
            self.setWindowTitle("MIDI Chord Lab")
            return
        star = " *" if self._dirty else ""
        self.setWindowTitle(f"MIDI Chord Lab — {self._current_path.name}{star}")

    def _schedule_analysis_refresh(self) -> None:
        if self._work_flat is None:
            return
        self._analysis_debounce.start()

    def save_current_midi(self, *, silent: bool = False) -> bool:
        if self._work_flat is None:
            return False
        if self._current_path is None:
            self.export_midi_file()
            return not self._dirty
        try:
            self._work_flat.write("midi", fp=str(self._current_path))
            self._clear_dirty()
            self.statusBar().showMessage(f"保存しました: {self._current_path.name}", 10000)
            return True
        except Exception:
            if not silent:
                QMessageBox.critical(self, "保存エラー", traceback.format_exc())
            return False

    def _insert_row_after(self, row: int) -> None:
        if self._work_flat is None:
            return
        self._push_history()
        rows = self._row_tuples()
        ql = list(self._row_ql)
        if not rows:
            rows = [(0.0, "C")]
            ql = [1.0]
        else:
            row = max(0, min(row, len(rows) - 1))
            off = rows[row][0] + ql[row]
            rows.insert(row + 1, (off, "C"))
            ql.insert(row + 1, ql[row])
        self._row_ql = ql
        self._work_flat = rebuild_stream_from_table(self._work_flat, rows, self._row_ql)
        self._fill_table_from_work()
        self._mark_dirty()
        self._schedule_analysis_refresh()

    def _duplicate_row(self, row: int) -> None:
        if self._work_flat is None or row < 0 or row >= len(self._row_ql):
            return
        self._push_history()
        rows = self._row_tuples()
        ql = list(self._row_ql)
        off = rows[row][0] + ql[row]
        label = rows[row][1]
        rows.insert(row + 1, (off, label))
        ql.insert(row + 1, ql[row])
        self._row_ql = ql
        self._work_flat = rebuild_stream_from_table(self._work_flat, rows, self._row_ql)
        self._fill_table_from_work()
        self._mark_dirty()
        self._schedule_analysis_refresh()

    def _delete_row(self, row: int) -> None:
        if self._work_flat is None or self.table.rowCount() <= 1:
            return
        if row < 0 or row >= self.table.rowCount():
            return
        self._push_history()
        rows = self._row_tuples()
        ql = list(self._row_ql)
        del rows[row]
        del ql[row]
        self._row_ql = ql
        self._work_flat = rebuild_stream_from_table(self._work_flat, rows, self._row_ql)
        self._fill_table_from_work()
        self._mark_dirty()
        self._schedule_analysis_refresh()

    def _labels(self) -> list[str]:
        out: list[str] = []
        for r in range(self.table.rowCount()):
            it = self.table.item(r, COL_LABEL)
            if it:
                out.append(it.text())
        return out

    def _row_tuples(self) -> list[tuple[float, str]]:
        rows: list[tuple[float, str]] = []
        for r in range(self.table.rowCount()):
            off_it = self.table.item(r, COL_OFFSET)
            txt_it = self.table.item(r, COL_LABEL)
            if off_it is None or txt_it is None:
                continue
            rows.append((float(off_it.text()), txt_it.text()))
        return rows

    @staticmethod
    def _elem_beat(el) -> str:
        if hasattr(el, "beat") and el.beat is not None:
            return f"{float(el.beat):.2f}"
        return "—"

    @staticmethod
    def _elem_pitches(el) -> str:
        if isinstance(el, m21_chord.Chord):
            return " ".join(p.nameWithOctave for p in el.pitches)
        if isinstance(el, m21_note.Note):
            return el.nameWithOctave
        return ""

    def _update_timeline_stats(self) -> None:
        n = self.table.rowCount()
        if n == 0:
            self._timeline_panel.set_stats("イベント: 0")
            self._status_events.setText("— イベント")
            return
        first = self.table.item(0, COL_OFFSET)
        last = self.table.item(n - 1, COL_OFFSET)
        ftxt = first.text() if first else "0"
        ltxt = last.text() if last else ftxt
        self._timeline_panel.set_stats(f"イベント: {n} 件 · 開始 {ftxt} — {ltxt} 拍（四分）")
        self._status_events.setText(f"{n} イベント")

    def _enable_score_controls(self, on: bool) -> None:
        self._export_xml_act.setEnabled(on)
        self._export_midi_act.setEnabled(on)
        self._export_report_act.setEnabled(on)
        self._export_video_act.setEnabled(on)
        self._save_act.setEnabled(on and self._dirty)
        self._btn_export_xml.setEnabled(on)
        self._btn_export_midi.setEnabled(on)
        self._btn_export_report.setEnabled(on)
        self._btn_play.setEnabled(on)
        self._btn_stop.setEnabled(on)
        self._tempo.setEnabled(on)
        self._update_undo_actions()

    def _roman_for_row_element(self, el) -> str:
        return functional_label(el, self._detected_key)

    def _refresh_analysis_views(self) -> None:
        if self._work_flat is None:
            self._clear_analysis_views()
            return
        events = self._note_events
        report = analyze_performance(events)
        if events:
            self._pianoroll_canvas.set_figure(build_pianoroll_figure_from_notes(events))
            self._perf_canvas.set_figure(build_performance_dashboard_figure(events, report))
        else:
            self._pianoroll_canvas.show_placeholder()
            self._perf_canvas.show_placeholder()

        harmony = collect_harmony_events(self._work_flat)
        self._voice_steps = analyze_voice_leading(
            harmony,
            lambda el: voice_leading_label(el, self._detected_key),
        )
        vl_rows = [
            (
                s.index,
                s.from_label,
                s.to_label,
                format_motions(s.motions),
                s.motion_kind,
                s.total_motion,
            )
            for s in self._voice_steps
        ]
        self._voice_panel.populate(vl_rows)
        parallel = sum(1 for s in self._voice_steps if s.motion_kind == "順行")
        contrary = sum(1 for s in self._voice_steps if s.motion_kind == "逆行")
        self._voice_panel.set_summary(
            f"和音遷移 {len(self._voice_steps)} 件 · 順行 {parallel} · 逆行 {contrary} · "
            f"{report_summary_text(report)}"
        )

    def _clear_analysis_views(self) -> None:
        self._voice_steps = []
        if hasattr(self, "_pianoroll_canvas"):
            self._pianoroll_canvas.show_placeholder()
        if hasattr(self, "_perf_canvas"):
            self._perf_canvas.show_placeholder()
        if hasattr(self, "_voice_panel"):
            self._voice_panel.clear_data()
        if hasattr(self, "_visualizer_panel"):
            self._visualizer_panel.clear_data()

    def _refresh_visualizer(self) -> None:
        if not hasattr(self, "_visualizer_panel"):
            return
        if self._note_events:
            self._visualizer_panel.set_score_data(self._note_events, float(self._tempo.value()))
        else:
            self._visualizer_panel.clear_data()

    def _stop_analysis_build(self) -> None:
        if self._analysis_worker is not None and self._analysis_worker.isRunning():
            self._analysis_worker.requestInterruption()
            self._analysis_worker.wait(5000)
        self._analysis_worker = None

    def _start_analysis_build(self) -> None:
        if self._work_flat is None:
            self._loading.hide_loading()
            return
        self._stop_analysis_build()
        self._clear_analysis_views()
        self._loading.show_loading("分析グラフを描画中", "準備しています…")
        self._analysis_worker = AnalysisBuildWorker(
            self._note_events,
            self._work_flat,
            self._detected_key,
            self,
        )
        self._analysis_worker.progress.connect(
            lambda detail: self._loading.show_loading("分析グラフを描画中", detail)
        )
        self._analysis_worker.completed.connect(self._apply_analysis_result)
        self._analysis_worker.failed.connect(self._on_analysis_failed)
        self._analysis_worker.finished.connect(self._on_analysis_worker_finished)
        self._analysis_worker.start()

    def _on_analysis_worker_finished(self) -> None:
        self._analysis_worker = None

    def _on_analysis_failed(self, tb: str) -> None:
        self._loading.hide_loading()
        self._clear_analysis_views()
        QMessageBox.warning(
            self,
            "分析グラフ",
            "分析グラフの生成に失敗しました。タイムラインは利用できます。\n\n" + tb[:1200],
        )

    def _apply_analysis_result(self, result: AnalysisResult) -> None:
        self._loading.hide_loading()
        self._voice_steps = list(result.voice_steps)
        if result.pianoroll_figure is not None:
            self._pianoroll_canvas.set_figure(result.pianoroll_figure)
        else:
            self._pianoroll_canvas.show_placeholder()
        if result.perf_figure is not None:
            self._perf_canvas.set_figure(result.perf_figure)
        else:
            self._perf_canvas.show_placeholder()
        self._voice_panel.populate(list(result.voice_rows))
        self._voice_panel.set_summary(result.voice_summary)
        self._refresh_visualizer()

    def export_visualizer_video(self) -> None:
        if not self._note_events:
            return
        self._refresh_visualizer()
        default = "visualization.mp4"
        if self._current_path is not None:
            default = self._current_path.stem + "_viz.mp4"
        path, _ = QFileDialog.getSaveFileName(
            self,
            "ビジュアライザ動画を保存",
            default,
            VIDEO_FILTER,
        )
        if not path:
            return
        from pathlib import Path as _Path

        p = _Path(path)
        if p.suffix.lower() not in (".mp4", ".mov", ".avi"):
            path = str(p.with_suffix(".mp4"))
        self._workspace_tabs.setCurrentWidget(self._visualizer_panel)
        self._visualizer_panel.start_export(path)

    def export_analysis_report(self) -> None:
        if self._work_flat is None or self._current_path is None:
            return
        default = self._current_path.stem + "_analysis.html"
        path, _ = QFileDialog.getSaveFileName(
            self,
            "分析レポートを保存",
            default,
            "HTML (*.html);;すべて (*.*)",
        )
        if not path:
            return
        try:
            labels = self._labels()
            romans = []
            for r in range(self.table.rowCount()):
                it = self.table.item(r, COL_ROMAN)
                romans.append(it.text() if it else "—")
            report = analyze_performance(self._note_events)
            html = build_analysis_html(
                self._current_path.name,
                self._key_display.text(),
                report,
                self._voice_steps,
                labels,
                romans,
            )
            Path(path).write_text(html, encoding="utf-8")
            self.statusBar().showMessage(f"分析レポート: {path}", 10000)
        except Exception:
            QMessageBox.critical(self, "エラー", traceback.format_exc())

    def dragEnterEvent(self, event: QDragEnterEvent):
        if not event.mimeData().hasUrls():
            event.ignore()
            return
        for u in event.mimeData().urls():
            if Path(u.toLocalFile()).suffix.lower() in {".mid", ".midi"}:
                event.acceptProposedAction()
                return
        event.ignore()

    def dropEvent(self, event: QDropEvent):
        for u in event.mimeData().urls():
            p = Path(u.toLocalFile())
            if p.suffix.lower() in {".mid", ".midi"}:
                self.load_file(str(p))
                event.acceptProposedAction()
                return

    def open_midi(self):
        path, _ = QFileDialog.getOpenFileName(self, "MIDI を開く", "", "MIDI (*.mid *.midi);;すべて (*.*)")
        if path:
            self.load_file(path)

    def export_musicxml(self):
        if self._work_flat is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "MusicXML を保存", str(self._current_path or "") + ".musicxml", "MusicXML (*.musicxml);;すべて (*.*)"
        )
        if path:
            try:
                self._work_flat.write("musicxml", fp=path)
                self.statusBar().showMessage(f"保存: {path}", 10000)
            except Exception:
                QMessageBox.critical(self, "エラー", traceback.format_exc())

    def export_midi_file(self):
        if self._work_flat is None:
            return
        default = (str(self._current_path) if self._current_path else "edited") + ".mid"
        path, _ = QFileDialog.getSaveFileName(self, "MIDI を保存", default, "MIDI (*.mid *.midi);;すべて (*.*)")
        if path:
            try:
                self._work_flat.write("midi", fp=path)
                self._current_path = Path(path)
                self._clear_dirty()
                self._update_window_title()
                self.statusBar().showMessage(f"MIDI 保存: {path}", 10000)
            except Exception:
                QMessageBox.critical(self, "エラー", traceback.format_exc())

    def _fill_table_from_work(self) -> None:
        assert self._work_flat is not None
        self._suppress_table = True
        self.table.blockSignals(True)
        self.table.setRowCount(0)
        self._row_ql.clear()
        read_only = Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled
        editable = read_only | Qt.ItemFlag.ItemIsEditable

        for ev in collect_harmony_events(self._work_flat):
            el = ev.element
            label = event_display_label(el, self._detected_key)
            off = ev.offset
            ql = ev.quarter_length
            pitches = self._elem_pitches(el)
            r = self.table.rowCount()
            self.table.insertRow(r)
            roman = self._roman_for_row_element(el)
            cells = (
                (COL_BEAT, self._elem_beat(el), read_only, self._table_font_mono),
                (COL_OFFSET, f"{off:.2f}", read_only, self._table_font_mono),
                (COL_DURATION, f"{ql:.2f}", editable, self._table_font_mono),
                (COL_LABEL, label, editable, self._table_font),
                (COL_ROMAN, roman, read_only, self._table_font_mono),
                (COL_PITCHES, pitches, read_only, self._table_font_mono),
            )
            for col, val, flags, font in cells:
                it = QTableWidgetItem(val)
                it.setFlags(flags)
                it.setFont(font)
                if col == COL_LABEL:
                    it.setToolTip(f"{label}\n{pitches}" if pitches else label)
                self.table.setItem(r, col, it)
            self._row_ql.append(ql)
        self.table.resizeColumnsToContents()
        self.table.setColumnWidth(COL_BEAT, max(56, self.table.columnWidth(COL_BEAT)))
        self.table.setColumnWidth(COL_OFFSET, max(72, self.table.columnWidth(COL_OFFSET)))
        self.table.setColumnWidth(COL_DURATION, max(64, self.table.columnWidth(COL_DURATION)))
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.scrollToTop()
        self.table.blockSignals(False)
        self._suppress_table = False
        self._update_timeline_stats()

    def _refresh_suggestions(self, r: int) -> None:
        self._chord_list.clear()
        self._melody_list.clear()
        if r < 0 or r >= len(self._row_ql):
            return
        it = self.table.item(r, COL_LABEL)
        if it is None:
            return
        labels = self._labels()
        try:
            el, _ = parse_chord_cell(it.text(), self._row_ql[r])
        except Exception:
            self._chord_list.addItem("（表記を解釈できません）")
            return
        prev = melody_midi_from_previous(labels, self._row_ql, r)
        for s in targeted_chord_suggestions(
            el,
            self._detected_key,
            label=it.text(),
            labels=labels,
            row_ql=self._row_ql,
            row=r,
            melody_midi=prev,
        ):
            self._chord_list.addItem(s)
        harm = harmony_chord_for_melody_at_row(labels, self._row_ql, r, self._detected_key)
        for line in melodic_note_candidates(prev, harm, self._detected_key):
            self._melody_list.addItem(line)

    def _on_table_cell_changed(self, row: int, col: int) -> None:
        if self._suppress_table or self._work_flat is None:
            return
        if col not in (COL_LABEL, COL_DURATION):
            return
        item = self.table.item(row, col)
        if item is None:
            return
        if col == COL_DURATION:
            try:
                ql = float(item.text().replace(",", "."))
                if ql <= 0:
                    raise ValueError("長さは正の数にしてください")
            except Exception as e:
                QMessageBox.warning(self, "長さ", f"解釈できません:\n{item.text()}\n\n{e}")
                return
        else:
            try:
                parse_chord_cell(item.text(), self._row_ql[row])
            except Exception as e:
                QMessageBox.warning(self, "表記エラー", f"解釈できません:\n{item.text()}\n\n{e}")
                return
        if not self._hist_cell_pushed:
            self._push_history()
            self._hist_cell_pushed = True
        if col == COL_DURATION:
            ql = float(item.text().replace(",", "."))
            self._row_ql[row] = ql
        try:
            self._work_flat = rebuild_stream_from_table(self._work_flat, self._row_tuples(), self._row_ql)
            if col == COL_LABEL:
                _, mids = parse_chord_cell(item.text(), self._row_ql[row])
                pit = self.table.item(row, COL_PITCHES)
                if pit is not None:
                    pit.setText(" ".join(m21_pitch.Pitch(m).nameWithOctave for m in mids))
                el_new, _ = parse_chord_cell(item.text(), self._row_ql[row])
                rom = self.table.item(row, COL_ROMAN)
                if rom is not None:
                    rom.setText(self._roman_for_row_element(el_new))
                self.piano.set_active_pitches(set(mids))
                self._refresh_suggestions(row)
            self._update_timeline_stats()
            self._mark_dirty()
            self._schedule_analysis_refresh()
        except Exception:
            QMessageBox.critical(self, "エラー", traceback.format_exc())

    def _on_table_selection_changed(self) -> None:
        self._hist_cell_pushed = False
        if self._playback_highlighting:
            return
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            self.piano.clear_active()
            self._chord_list.clear()
            self._melody_list.clear()
            return
        r = rows[0].row()
        self._refresh_suggestions(r)
        if r < len(self._row_ql):
            it = self.table.item(r, COL_LABEL)
            if it:
                try:
                    _, mids = parse_chord_cell(it.text(), self._row_ql[r])
                    self.piano.set_active_pitches(set(mids))
                except Exception:
                    self.piano.clear_active()

    def _on_chord_suggestion(self, item: QListWidgetItem) -> None:
        row = self.table.currentRow()
        if row < 0 or item is None or item.text().startswith("（"):
            return
        txt = item.text()
        self._apply_cell_text(row, txt)

    def _on_melody_suggestion(self, item: QListWidgetItem) -> None:
        row = self.table.currentRow()
        if row < 0 or item is None:
            return
        raw = item.text().strip()
        if raw.startswith("（") or "候補" in raw[:8]:
            return
        part = raw.split("—")[0].strip()
        try:
            p_only = m21_pitch.Pitch(part)
            new_text = p_only.nameWithOctave
        except Exception:
            return
        try:
            el0, _ = parse_chord_cell(self.table.item(row, COL_LABEL).text(), self._row_ql[row])
        except Exception:
            return
        if not isinstance(el0, m21_note.Note):
            QMessageBox.information(
                self, "メロディ候補",
                "単音行（例: C5）でのみメロディ候補を適用できます。",
            )
            return
        self._apply_cell_text(row, new_text)

    def _apply_cell_text(self, row: int, txt: str) -> None:
        self._push_history()
        self._suppress_table = True
        self.table.blockSignals(True)
        self.table.item(row, COL_LABEL).setText(txt)
        self.table.blockSignals(False)
        self._suppress_table = False
        self._work_flat = rebuild_stream_from_table(self._work_flat, self._row_tuples(), self._row_ql)
        try:
            _, mids = parse_chord_cell(txt, self._row_ql[row])
            pit = self.table.item(row, COL_PITCHES)
            if pit is not None:
                pit.setText(" ".join(m21_pitch.Pitch(m).nameWithOctave for m in mids))
            el_new, _ = parse_chord_cell(txt, self._row_ql[row])
            rom = self.table.item(row, COL_ROMAN)
            if rom is not None:
                rom.setText(self._roman_for_row_element(el_new))
            self.piano.set_active_pitches(set(mids))
        except Exception:
            pass
        self._refresh_suggestions(row)
        self._update_timeline_stats()
        self._mark_dirty()
        self._schedule_analysis_refresh()

    def play_transport(self) -> None:
        if self._work_flat is None:
            return
        self.stop_transport()
        tl = build_playback_timeline(self._work_flat)
        if not tl:
            QMessageBox.information(self, "再生", "再生できる音符がありません。")
            return
        self._playback = PlaybackThread(tl, self._tempo.value(), self)
        self._playback.highlight_row.connect(self._on_playback_highlight_row)
        self._playback.position_changed.connect(self._on_playback_position)
        self._playback.midi_message.connect(self._on_playback_midi_message)
        self._playback.mode_changed.connect(self._on_playback_mode)
        self._playback.finished_playback.connect(self._on_playback_done)
        self._btn_play.setEnabled(False)
        self._btn_stop.setEnabled(True)
        self._playback.start()

    def _on_playback_highlight_row(self, row: int) -> None:
        if row < 0:
            self.piano.clear_active()
            self._playback_highlighting = False
            return
        if row >= self.table.rowCount():
            return
        self._playback_highlighting = True
        self.table.selectRow(row)
        beat_item = self.table.item(row, COL_BEAT)
        if beat_item is not None:
            self.table.scrollToItem(beat_item, QAbstractItemView.ScrollHint.PositionAtCenter)
        if row < len(self._row_ql):
            it = self.table.item(row, COL_LABEL)
            if it:
                try:
                    _, mids = parse_chord_cell(it.text(), self._row_ql[row])
                    self.piano.set_active_pitches(set(mids))
                except Exception:
                    pass

    def _on_workspace_tab_changed(self, index: int) -> None:
        if index < 0:
            return
        if self._workspace_tabs.widget(index) is self._visualizer_panel:
            self._visualizer_panel.on_tab_activated()

    def _on_playback_position(self, t_sec: float) -> None:
        if hasattr(self, "_visualizer_panel"):
            self._visualizer_panel.update_playback_time(t_sec)

    def _on_playback_midi_message(self, status: int, data1: int, data2: int) -> None:
        if hasattr(self, "_visualizer_panel"):
            self._visualizer_panel.forward_playback_midi(status, data1, data2)

    def _on_playback_mode(self, mode: str) -> None:
        msgs = {
            "midi": "再生中 — MIDI デバイス",
            "software": "再生中 — ソフトウェア音源",
            "wave": "再生中 — Windows 波形出力",
            "beep": "再生中 — システムビープ",
            "silent": "再生中 — 音声なし（鍵盤のみ）",
        }
        self.statusBar().showMessage(msgs.get(mode, "再生中…"), 0)

    def _on_playback_done(self) -> None:
        self._playback_highlighting = False
        if hasattr(self, "_visualizer_panel"):
            self._visualizer_panel.on_playback_stopped()
        self.piano.clear_active()
        self._btn_play.setEnabled(self._work_flat is not None)
        self._btn_stop.setEnabled(self._work_flat is not None)
        self._playback = None
        if self._current_path:
            self.statusBar().showMessage(f"{self._current_path.name} — 再生終了", 8000)

    def stop_transport(self) -> None:
        if self._playback is not None:
            self._playback.requestInterruption()
            stop_audio_output()
            self._playback.wait(3000)
        self._playback = None
        self._playback_highlighting = False
        if hasattr(self, "_visualizer_panel"):
            self._visualizer_panel.on_playback_stopped()
        self.piano.clear_active()
        self._btn_play.setEnabled(self._work_flat is not None)
        self._btn_stop.setEnabled(self._work_flat is not None)

    def load_file(self, path: str) -> None:
        if self._load_worker is not None and self._load_worker.isRunning():
            return
        self._stop_analysis_build()
        self.stop_transport()
        name = Path(path).name
        self.statusBar().showMessage(f"読み込み中: {name}…")
        self._loading.show_loading("MIDI を読み込んでいます", name)
        self._load_worker = MidiLoadWorker(path, self)
        self._load_worker.progress.connect(
            lambda detail: self._loading.show_loading("MIDI を読み込んでいます", detail)
        )
        self._load_worker.completed.connect(self._apply_loaded_score)
        self._load_worker.failed.connect(self._on_load_failed)
        self._load_worker.finished.connect(self._on_load_worker_finished)
        self._load_worker.start()

    def _on_load_worker_finished(self) -> None:
        self._load_worker = None

    def _on_load_failed(self, tb: str) -> None:
        self._stop_analysis_build()
        self._loading.hide_loading()
        self._reset_session()
        QMessageBox.critical(self, "読み込みエラー", tb)

    def _apply_loaded_score(self, payload: LoadedScore) -> None:
        try:
            clear_chord_figure_cache()
            self._original_score = payload.score
            self._work_flat = payload.work_flat
            self._current_path = Path(payload.path)
            self._detected_key = payload.key_obj
            self._key_display.setText(payload.key_text)
            self._note_events = list(payload.note_events)
            self._edit_history.clear()
            self._dirty = False
            self._tempo.setValue(payload.bpm)
            add_recent_file(payload.path)
            self._fill_table_from_work()
            self._chord_list.clear()
            self._melody_list.clear()
            self.piano.clear_active()
            self._enable_score_controls(True)
            self._stack.setCurrentIndex(1)
            name = self._current_path.name
            short = name if len(name) <= 24 else name[:21] + "…"
            self._header_badge.setText(short.upper())
            self._header_badge.setObjectName("HeaderBadgeActive")
            self._header_badge.style().unpolish(self._header_badge)
            self._header_badge.style().polish(self._header_badge)
            self._update_window_title()
            self._status_mode.setText("編集中")
            self.statusBar().showMessage(f"{name} を読み込みました", 12000)
            self._refresh_visualizer()
            self._start_analysis_build()
        except Exception:
            self._stop_analysis_build()
            self._loading.hide_loading()
            self._reset_session()
            QMessageBox.critical(self, "表示エラー", traceback.format_exc())

    def _reset_session(self) -> None:
        self._stop_analysis_build()
        self._edit_history.clear()
        self._dirty = False
        self._original_score = None
        self._work_flat = None
        self._current_path = None
        self._detected_key = None
        self._note_events = []
        self._key_display.setText("—")
        self._enable_score_controls(False)
        self._clear_analysis_views()
        self._header_badge.setText("STANDBY")
        self._header_badge.setObjectName("HeaderBadge")
        self._header_badge.style().unpolish(self._header_badge)
        self._header_badge.style().polish(self._header_badge)
        self._status_mode.setText("待機中")
        self._status_events.setText("— イベント")
        self.setWindowTitle("MIDI Chord Lab")
        self.table.setRowCount(0)
        self._row_ql.clear()
        self._chord_list.clear()
        self._melody_list.clear()
        if hasattr(self, "_timeline_panel"):
            self._timeline_panel.set_stats("イベント: —")
        self._stack.setCurrentIndex(0)
