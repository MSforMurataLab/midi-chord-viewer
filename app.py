# -*- coding: utf-8 -*-
"""
MIDI を開くと和音名一覧とピアノロール（時系列の楽譜表示）を表示します。

開発時: python app.py
配布版: dist/MIDIChordViewer/MIDIChordViewer.exe をダブルクリック
"""

from __future__ import annotations

import copy
import os
import re
import sys
import traceback
from pathlib import Path


def _bootstrap_frozen() -> None:
    """PyInstaller 等の単一 exe / フォルダ配布時に matplotlib 等の書き込み先を確保する。"""
    if not getattr(sys, "frozen", False):
        return
    local = os.environ.get("LOCALAPPDATA")
    if local:
        app_dir = Path(local) / "MIDIChordViewer"
    else:
        app_dir = Path.home() / ".midi_chord_viewer"
    mpl_dir = app_dir / "matplotlib"
    mpl_dir.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("MPLCONFIGDIR", str(mpl_dir))


_bootstrap_frozen()

import matplotlib

matplotlib.use("QtAgg")

import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from PyQt6.QtCore import QThread, Qt, pyqtSignal
from PyQt6.QtGui import QAction, QDragEnterEvent, QDropEvent, QFont, QKeySequence
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
    QSplitter,
    QSpinBox,
    QStatusBar,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from music21 import chord as m21_chord
from music21 import converter
from music21 import harmony
from music21 import key as m21_key
from music21 import meter
from music21 import note as m21_note
from music21 import pitch as m21_pitch
from music21 import roman
from music21 import stream as m21_stream
from music21.roman import romanNumeralFromChord

from piano_keyboard import PianoKeyboard

try:
    import mido
except ImportError:
    mido = None  # type: ignore

APP_STYLESHEET = """
/* --- ベース: ダーク・スタジオ風 --- */
QMainWindow {
    background-color: #0c0c12;
}
QWidget#CentralRoot {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #0e0e16, stop:0.4 #12121c, stop:1 #0a0a10);
}

/* トップクローム */
QFrame#TopChrome {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #141428, stop:0.5 #1a1a32, stop:1 #141428);
    border: none;
    border-bottom: 1px solid #2a2a44;
    min-height: 56px;
}
QLabel#AppTitle {
    color: #f0f2f8;
    font-size: 22px;
    font-weight: 700;
    letter-spacing: 0.5px;
}
QLabel#AppSubtitle {
    color: #7d8aa0;
    font-size: 12px;
    margin-top: 2px;
}
QLabel#AccentBadge {
    background-color: rgba(0, 212, 170, 0.15);
    color: #00d4aa;
    border: 1px solid rgba(0, 212, 170, 0.45);
    border-radius: 6px;
    padding: 4px 10px;
    font-size: 11px;
    font-weight: 600;
}

QToolBar#ChromeToolBar {
    background-color: transparent;
    border: none;
    spacing: 6px;
    padding: 10px 16px 12px 16px;
    icon-size: 18px;
}
QToolBar#ChromeToolBar QToolButton {
    background-color: #252538;
    color: #e4e8f0;
    border: 1px solid #3a3a55;
    border-radius: 8px;
    padding: 8px 14px;
    margin: 0 2px;
    font-weight: 600;
}
QToolBar#ChromeToolBar QToolButton:hover {
    background-color: #2e2e48;
    border-color: #00d4aa;
}
QToolBar#ChromeToolBar QToolButton:pressed {
    background-color: #1e1e30;
}
QToolBar#ChromeToolBar QToolButton:disabled {
    color: #5a5a70;
    border-color: #2a2a3a;
    background-color: #1a1a28;
}

QMenuBar {
    background-color: #12121a;
    color: #c8d0e0;
    border-bottom: 1px solid #252538;
    padding: 4px 8px;
}
QMenuBar::item {
    padding: 6px 12px;
    border-radius: 6px;
}
QMenuBar::item:selected {
    background-color: #252538;
}
QMenu {
    background-color: #1e1e2c;
    color: #e4e8f0;
    border: 1px solid #3a3a55;
    border-radius: 8px;
    padding: 6px;
}
QMenu::item:selected {
    background-color: #2a3a5c;
}

/* カードパネル */
QFrame#CardPanel {
    background-color: rgba(26, 26, 40, 0.92);
    border: 1px solid #32324a;
    border-radius: 14px;
}
QFrame#CardHeader {
    background: transparent;
    border: none;
    border-bottom: 1px solid #2a2a40;
    padding: 0 0 10px 0;
    margin-bottom: 4px;
}
QLabel#CardTitle {
    color: #e8ecf4;
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 0.3px;
}
QLabel#CardHint {
    color: #6b7a90;
    font-size: 11px;
}

QTableWidget {
    gridline-color: #2a2a3c;
    background-color: #14141f;
    alternate-background-color: #181824;
    color: #d8dce6;
    border: 1px solid #2e2e42;
    border-radius: 10px;
    selection-background-color: rgba(0, 212, 170, 0.22);
    selection-color: #ffffff;
    outline: none;
}
QTableWidget::item {
    padding: 6px 8px;
}
QHeaderView::section {
    background-color: #1e1e2e;
    color: #9aa8bc;
    padding: 10px 12px;
    border: none;
    border-bottom: 2px solid #00d4aa;
    font-weight: 700;
    font-size: 11px;
    text-transform: uppercase;
}
QScrollBar:vertical {
    background: #14141f;
    width: 10px;
    border-radius: 5px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: #3a3a55;
    border-radius: 5px;
    min-height: 28px;
}
QScrollBar::handle:vertical:hover {
    background: #00a080;
}
QScrollBar:horizontal {
    background: #14141f;
    height: 10px;
    border-radius: 5px;
}
QScrollBar::handle:horizontal {
    background: #3a3a55;
    border-radius: 5px;
}

QSplitter::handle {
    background: #1e1e2c;
    width: 5px;
}
QSplitter::handle:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #00d4aa, stop:0.5 #00a8cc, stop:1 #00d4aa);
}

QListWidget {
    background-color: #14141f;
    color: #d8dce6;
    border: 1px solid #2e2e42;
    border-radius: 10px;
    padding: 6px;
    outline: none;
}
QListWidget::item {
    padding: 8px 10px;
    border-radius: 6px;
}
QListWidget::item:selected {
    background-color: rgba(0, 212, 170, 0.25);
    color: #ffffff;
}
QListWidget::item:hover {
    background-color: #252538;
}

QLabel#KeyLabel {
    color: #00d4aa;
    font-weight: 700;
    font-size: 13px;
}

QStatusBar {
    background-color: #12121a;
    color: #8b96a8;
    border-top: 1px solid #252538;
    padding: 4px 12px;
}

/* ドロップゾーン */
QFrame#DropHint {
    border: 2px dashed #4a4a68;
    border-radius: 16px;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #1a1a2e, stop:1 #12121c);
    padding: 32px;
}
QLabel#DropTitle {
    color: #f0f2f8;
    font-size: 18px;
    font-weight: 700;
}
QLabel#DropBody {
    color: #8b96a8;
    font-size: 13px;
    line-height: 1.55;
}
QLabel#DropIcon {
    color: #00d4aa;
    font-size: 42px;
}

/* matplotlib 埋め込みツールバー */
QToolBar#PlotToolBar {
    background-color: #14141f;
    border: none;
    border-top: 1px solid #2e2e42;
    border-bottom: 1px solid #2e2e42;
    padding: 4px;
    spacing: 2px;
}
QToolBar#PlotToolBar QToolButton {
    background: transparent;
    border: 1px solid transparent;
    border-radius: 6px;
    padding: 4px;
}
QToolBar#PlotToolBar QToolButton:hover {
    background-color: #252538;
    border-color: #3a3a55;
}

QPushButton#BtnPrimary {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #00e8b8, stop:1 #00a080);
    color: #0a0a12;
    border: none;
    border-radius: 10px;
    padding: 10px 20px;
    font-weight: 700;
    min-width: 100px;
}
QPushButton#BtnPrimary:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #33ffdd, stop:1 #00c090);
}
QPushButton#BtnPrimary:pressed {
    background: #009070;
}

QPushButton#BtnSecondary {
    background-color: #252538;
    color: #e4e8f0;
    border: 1px solid #3a3a55;
    border-radius: 10px;
    padding: 10px 18px;
    font-weight: 600;
}
QPushButton#BtnSecondary:hover {
    border-color: #00d4aa;
    background-color: #2e2e48;
}
QPushButton#BtnSecondary:disabled {
    color: #5a5a70;
    border-color: #2a2a3a;
}

QPushButton#BtnGhost {
    background: transparent;
    color: #8b96a8;
    border: 1px solid #2e2e42;
    border-radius: 10px;
    padding: 10px 16px;
}
QPushButton#BtnGhost:hover {
    color: #e4e8f0;
    border-color: #5a5a70;
}

QMessageBox {
    background-color: #1e1e2c;
}
QMessageBox QLabel {
    color: #e4e8f0;
}
QMessageBox QPushButton {
    background-color: #252538;
    color: #e4e8f0;
    border: 1px solid #3a3a55;
    border-radius: 8px;
    padding: 8px 20px;
    min-width: 72px;
}
QMessageBox QPushButton:hover {
    border-color: #00d4aa;
}
"""


def load_score(path: str):
    return converter.parse(path)


def detect_key_for_score(score) -> tuple[str, m21_key.Key | None]:
    try:
        k = score.analyze("key")
        lab = f"{k.tonic.name} {k.mode}"
        coef = getattr(k, "correlationCoefficient", None)
        if coef is not None:
            lab += f"  ·  r={float(coef):.2f}"
        return lab, k
    except Exception:
        return "不明", None


def parse_chord_cell(text: str, ql: float) -> tuple[m21_chord.Chord | m21_note.Note, tuple[int, ...]]:
    t = text.strip()
    if "（単音）" in t or re.match(r"^[A-G][#b]?\d+\s*（単音）", t):
        note_part = re.sub(r"\s*（単音）\s*$", "", t).strip()
        n = m21_note.Note(note_part, quarterLength=ql)
        return n, (n.pitch.midi,)
    t2 = re.sub(r"\s*（単音）\s*$", "", t).strip()
    try:
        ch = harmony.chordFromFigure(t2)
        ch.quarterLength = ql
        return ch, tuple(p.midi for p in ch.pitches)
    except Exception:
        pass
    try:
        ch = m21_chord.Chord(t2)
        ch.quarterLength = ql
        return ch, tuple(p.midi for p in ch.pitches)
    except Exception:
        n = m21_note.Note(t2, quarterLength=ql)
        return n, (n.pitch.midi,)


def targeted_chord_suggestions(
    el: m21_chord.Chord | m21_note.Note,
    ky: m21_key.Key | None,
) -> list[str]:
    if ky is None:
        return ["キーが検出できません（候補は参考程度）"]
    cand: list[str] = []
    seen: set[str] = set()

    def add(name: str | None) -> None:
        if not name or name in seen:
            return
        seen.add(name)
        cand.append(name)

    labels = [
        "I",
        "I7",
        "ii",
        "ii7",
        "iii",
        "iii7",
        "IV",
        "IVmaj7",
        "V",
        "V7",
        "vi",
        "vi7",
        "viiø7",
        "bIII",
        "bVI",
        "bVII",
        "iv",
        "iiø7",
        "Ger+6",
        "It+6",
        "Fr+6",
    ]
    for lab in labels:
        try:
            rn = roman.RomanNumeral(lab, ky)
            if rn.chord:
                add(rn.chord.pitchedCommonName)
        except Exception:
            continue

    if isinstance(el, m21_chord.Chord):
        cur = el.pitchedCommonName
        cand = [x for x in cand if x != cur]
        try:
            rn0 = romanNumeralFromChord(el, ky)
            fig = str(rn0.figure)
            if "7" in fig or fig in ("V", "v"):
                try:
                    tr = roman.RomanNumeral("bII7", ky)
                    if tr.chord:
                        add(tr.chord.pitchedCommonName)
                except Exception:
                    pass
        except Exception:
            pass
    else:
        for lab in ("I", "IV", "V", "vi"):
            try:
                rn = roman.RomanNumeral(lab, ky)
                if rn.chord:
                    add(rn.chord.pitchedCommonName)
            except Exception:
                pass

    return cand[:18] if cand else ["（候補を生成できません）"]


def _scale_pitch_classes(ky: m21_key.Key) -> set[int]:
    sc = ky.getScale()
    return {p.pitchClass for p in sc.pitches}


def melody_midi_from_previous_row(
    table: QTableWidget,
    row_ql: list[float],
    r: int,
) -> int | None:
    """一つ前のイベントのメロディ相当 MIDI（単音＝その音、和音＝最高音）。"""
    if r <= 0:
        return None
    try:
        it = table.item(r - 1, 2)
        if it is None:
            return None
        el, mids = parse_chord_cell(it.text(), row_ql[r - 1])
        if isinstance(el, m21_note.Note):
            return el.pitch.midi
        if isinstance(el, m21_chord.Chord):
            return max(mids)
    except Exception:
        return None
    return None


def harmony_chord_for_melody_at_row(
    table: QTableWidget,
    row_ql: list[float],
    r: int,
    ky: m21_key.Key | None,
) -> m21_chord.Chord | None:
    """現在位置の和声：行が和音ならそれ／単音なら直前に現れる最後の和音／なければ I。"""
    if r < 0 or r >= len(row_ql):
        return None
    try:
        el, _ = parse_chord_cell(table.item(r, 2).text(), row_ql[r])
        if isinstance(el, m21_chord.Chord):
            return el
        for j in range(r - 1, -1, -1):
            el2, _ = parse_chord_cell(table.item(j, 2).text(), row_ql[j])
            if isinstance(el2, m21_chord.Chord):
                return el2
    except Exception:
        pass
    if ky is not None:
        try:
            rn = roman.RomanNumeral("I", ky)
            if rn.chord:
                return rn.chord
        except Exception:
            pass
    return None


def melodic_note_candidates(
    prev_midi: int | None,
    harmony: m21_chord.Chord | None,
    ky: m21_key.Key | None,
) -> list[str]:
    """直前のメロディと現在の和音・旋法から、取りうるメロディ音の候補（表示用文字列）。"""
    if ky is None:
        return ["キー未検出のため、旋法に基づく候補を絞り込めません。"]
    if harmony is None:
        return ["この位置の和音を特定できません（表のコード行を確認してください）。"]
    pcs_chord = {p.pitchClass for p in harmony.pitches}
    pcs_scale = _scale_pitch_classes(ky)
    center = prev_midi if prev_midi is not None else 64

    scored: list[tuple[int, str]] = []

    def add(mid: int, reason: str) -> None:
        if 36 <= mid <= 108:
            scored.append((mid, reason))

    # 和音構成音（直前に近いオクターブを優先）
    for p in harmony.pitches:
        base = p.midi
        for mid in (base - 24, base - 12, base, base + 12, base + 24):
            if prev_midi is None:
                if 55 <= mid <= 79:
                    add(mid, "和音構成音（中央付近）")
            else:
                if abs(mid - prev_midi) <= 12:
                    add(mid, "和音構成音（ボイシング近接）")

    if prev_midi is not None:
        for delta in range(-8, 9):
            if delta == 0:
                continue
            mid = prev_midi + delta
            pc = mid % 12
            if pc in pcs_chord:
                add(mid, f"先行音から{delta:+d}半音（和音内）")
            elif pc in pcs_scale:
                add(mid, f"先行音から{delta:+d}半音（旋法内）")
            elif abs(delta) <= 2:
                add(mid, f"先行音から{delta:+d}半音（経過・非和声）")

    if not scored and prev_midi is None:
        for p in harmony.pitches[:4]:
            mid = p.midi
            while mid < 60:
                mid += 12
            while mid > 84:
                mid -= 12
            add(mid, "和音構成音（先頭イベント用）")

    best: dict[int, str] = {}
    for mid, reason in scored:
        if mid not in best:
            best[mid] = reason

    def sort_key(m: int) -> tuple[int, int]:
        d = abs(m - center) if prev_midi is None else abs(m - prev_midi)
        return (d, m)

    lines: list[str] = []
    for mid in sorted(best.keys(), key=sort_key)[:26]:
        nm = m21_pitch.Pitch(mid).nameWithOctave
        lines.append(f"{nm}  —  {best[mid]}")
    return lines if lines else ["（候補を生成できません）"]


def build_flat_work_stream(score) -> m21_stream.Stream:
    ch = score.chordify()
    flat = m21_stream.Stream()
    try:
        ts = score.flatten().getTimeSignatures(searchContext=True)
        if ts:
            flat.insert(0.0, ts[0])
        else:
            flat.insert(0.0, meter.TimeSignature("4/4"))
    except Exception:
        flat.insert(0.0, meter.TimeSignature("4/4"))
    for el in ch.flatten().notesAndRests:
        if isinstance(el, (m21_chord.Chord, m21_note.Note)):
            ne = copy.deepcopy(el)
            flat.insert(float(el.offset), ne)
    return flat


def build_playback_timeline(work: m21_stream.Stream) -> list[tuple[float, float, tuple[int, ...]]]:
    out: list[tuple[float, float, tuple[int, ...]]] = []
    for el in work.flatten().notesAndRests:
        if isinstance(el, m21_chord.Chord):
            ps = tuple(sorted(p.midi for p in el.pitches))
        elif isinstance(el, m21_note.Note):
            ps = (el.pitch.midi,)
        else:
            continue
        out.append((float(el.offset), float(el.quarterLength), ps))
    out.sort(key=lambda x: x[0])
    return out


class PlaybackThread(QThread):
    highlight = pyqtSignal(object)
    finished_playback = pyqtSignal()

    def __init__(self, timeline: list[tuple[float, float, tuple[int, ...]]], tempo: int = 120, parent=None):
        super().__init__(parent)
        self.timeline = timeline
        self.tempo = tempo

    def run(self) -> None:
        import time

        spq = 60.0 / float(max(40, min(220, self.tempo)))
        port = None
        if mido:
            try:
                names = mido.get_output_names()
                chosen = None
                for pref in ("Microsoft GS", "VirtualMIDISynth", "LoopBe", "Fluid"):
                    for n in names:
                        if pref in n:
                            chosen = n
                            break
                    if chosen:
                        break
                if chosen is None and names:
                    chosen = names[0]
                if chosen:
                    port = mido.open_output(chosen)
            except Exception:
                port = None
        wall = 0.0
        try:
            for off, ql, pitches in self.timeline:
                if self.isInterruptionRequested():
                    break
                target = off * spq
                if target > wall:
                    time.sleep(target - wall)
                wall = target
                ps = {int(p) for p in pitches}
                self.highlight.emit(ps)
                if port:
                    for p in ps:
                        port.send(mido.Message("note_on", note=p, velocity=88))
                dur = max(0.02, ql * spq)
                time.sleep(dur)
                if port:
                    for p in ps:
                        port.send(mido.Message("note_off", note=p, velocity=0))
                self.highlight.emit(set())
                wall = target + dur
        finally:
            if port:
                try:
                    for p in range(128):
                        port.send(mido.Message("note_off", note=p, velocity=0))
                    port.close()
                except Exception:
                    pass
            self.highlight.emit(set())
            self.finished_playback.emit()


def _theme_matplotlib_figure(fig) -> None:
    """UI と一体感のあるダークテーマをピアノロールに適用。"""
    bg = "#0e0e16"
    panel = "#14141f"
    grid_c = "#2a2a3c"
    tick = "#9aa8bc"
    label = "#c4ccd8"
    fig.patch.set_facecolor(bg)
    for ax in fig.get_axes():
        ax.set_facecolor(panel)
        ax.tick_params(colors=tick, labelsize=9)
        ax.grid(True, color=grid_c, alpha=0.55, linestyle="-", linewidth=0.6)
        for s in ax.spines.values():
            s.set_color(grid_c)
        ax.xaxis.label.set_color(label)
        ax.yaxis.label.set_color(label)
        t = ax.title
        if t.get_text():
            t.set_color("#e8ecf4")


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
        hint = QFrame()
        hint.setObjectName("DropHint")
        v = QVBoxLayout(hint)
        v.setSpacing(16)
        icon = QLabel("♪")
        icon.setObjectName("DropIcon")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title = QLabel("MIDI をここにドロップ")
        title.setObjectName("DropTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        body = QLabel(
            "<b>対応:</b> .mid / .midi<br><br>"
            "上部の <b>開く</b> からも読み込めます。<br>"
            "解析結果は左のリスト、右はピアノロール（音程 × 時間）です。<br><br>"
            "五線譜で確認する場合は <b>MusicXML を保存</b> して MuseScore 等へ。"
        )
        body.setObjectName("DropBody")
        body.setAlignment(Qt.AlignmentFlag.AlignCenter)
        body.setWordWrap(True)
        body.setTextFormat(Qt.TextFormat.RichText)
        v.addStretch(1)
        v.addWidget(icon)
        v.addWidget(title)
        v.addWidget(body)
        v.addStretch(2)
        self._layout.addWidget(hint)

    def set_plot(self, plot_obj):
        self._clear_widgets()
        self._figure = plot_obj.figure
        _theme_matplotlib_figure(self._figure)
        try:
            self._figure.tight_layout()
        except Exception:
            pass
        self._canvas = FigureCanvasQTAgg(self._figure)
        self._canvas.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        self._toolbar = NavigationToolbar(self._canvas, self)
        self._toolbar.setObjectName("PlotToolBar")
        self._layout.addWidget(self._toolbar)
        self._layout.addWidget(self._canvas, stretch=1)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MIDI Chord Lab")
        self.resize(1360, 820)
        self.setMinimumSize(980, 580)
        self.setAcceptDrops(True)

        self._original_score = None
        self._work_flat: m21_stream.Stream | None = None
        self._current_path: Path | None = None
        self._detected_key: m21_key.Key | None = None
        self._row_ql: list[float] = []
        self._suppress_table = False
        self._playback: PlaybackThread | None = None

        style = self.style()
        open_act = QAction(style.standardIcon(style.StandardPixmap.SP_DialogOpenButton), "MIDI を開く…", self)
        open_act.setShortcut(QKeySequence.StandardKey.Open)
        open_act.setStatusTip("MIDI ファイルを選択して開きます")
        open_act.triggered.connect(self.open_midi)

        self.export_act = QAction(
            style.standardIcon(style.StandardPixmap.SP_DialogSaveButton),
            "MusicXML を保存…",
            self,
        )
        self.export_act.setShortcut("Ctrl+Shift+S")
        self.export_act.setStatusTip("編集中のスコアを MusicXML で保存")
        self.export_act.setEnabled(False)
        self.export_act.triggered.connect(self.export_musicxml)

        self.export_midi_act = QAction("MIDI を書き出し…", self)
        self.export_midi_act.setShortcut("Ctrl+Shift+M")
        self.export_midi_act.setEnabled(False)
        self.export_midi_act.triggered.connect(self.export_midi_file)

        quit_act = QAction("終了", self)
        quit_act.setShortcut(QKeySequence.StandardKey.Quit)
        quit_act.triggered.connect(self.close)

        menubar = self.menuBar()
        file_menu = menubar.addMenu("ファイル(&F)")
        file_menu.addAction(open_act)
        file_menu.addAction(self.export_act)
        file_menu.addAction(self.export_midi_act)
        file_menu.addSeparator()
        file_menu.addAction(quit_act)

        chrome = QFrame()
        chrome.setObjectName("TopChrome")
        crow = QHBoxLayout(chrome)
        crow.setContentsMargins(22, 14, 22, 14)
        crow.setSpacing(18)

        brand = QWidget()
        bl = QVBoxLayout(brand)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(2)
        app_title = QLabel("MIDI Chord Lab")
        app_title.setObjectName("AppTitle")
        app_sub = QLabel("コード解析 · ピアノロール · ドラッグ＆ドロップ対応")
        app_sub.setObjectName("AppSubtitle")
        bl.addWidget(app_title)
        bl.addWidget(app_sub)
        crow.addWidget(brand)

        self._status_badge = QLabel(" STUDIO ")
        self._status_badge.setObjectName("AccentBadge")
        crow.addWidget(self._status_badge)
        crow.addStretch(1)

        open_btn = QPushButton(style.standardIcon(style.StandardPixmap.SP_DialogOpenButton), "  開く  ")
        open_btn.setObjectName("BtnPrimary")
        open_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        open_btn.setStatusTip("MIDI を選択")
        open_btn.clicked.connect(self.open_midi)

        self._export_btn = QPushButton(
            style.standardIcon(style.StandardPixmap.SP_DialogSaveButton),
            "  MusicXML  ",
        )
        self._export_btn.setObjectName("BtnSecondary")
        self._export_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._export_btn.setEnabled(False)
        self._export_btn.clicked.connect(self.export_musicxml)

        self._export_midi_btn = QPushButton("  MIDI 書き出し  ")
        self._export_midi_btn.setObjectName("BtnSecondary")
        self._export_midi_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._export_midi_btn.setEnabled(False)
        self._export_midi_btn.clicked.connect(self.export_midi_file)

        self._play_btn = QPushButton("  ▶ 再生  ")
        self._play_btn.setObjectName("BtnPrimary")
        self._play_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._play_btn.setEnabled(False)
        self._play_btn.clicked.connect(self.play_transport)

        self._stop_btn = QPushButton("  ■ 停止  ")
        self._stop_btn.setObjectName("BtnGhost")
        self._stop_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._stop_btn.setEnabled(False)
        self._stop_btn.clicked.connect(self.stop_transport)

        self._tempo_spin = QSpinBox()
        self._tempo_spin.setRange(40, 208)
        self._tempo_spin.setValue(120)
        self._tempo_spin.setPrefix("BPM ")
        self._tempo_spin.setEnabled(False)

        quit_btn = QPushButton("終了")
        quit_btn.setObjectName("BtnGhost")
        quit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        quit_btn.clicked.connect(self.close)

        crow.addWidget(open_btn, alignment=Qt.AlignmentFlag.AlignVCenter)
        crow.addWidget(self._export_btn, alignment=Qt.AlignmentFlag.AlignVCenter)
        crow.addWidget(self._export_midi_btn, alignment=Qt.AlignmentFlag.AlignVCenter)
        crow.addWidget(self._play_btn, alignment=Qt.AlignmentFlag.AlignVCenter)
        crow.addWidget(self._stop_btn, alignment=Qt.AlignmentFlag.AlignVCenter)
        crow.addWidget(self._tempo_spin, alignment=Qt.AlignmentFlag.AlignVCenter)
        crow.addWidget(quit_btn, alignment=Qt.AlignmentFlag.AlignVCenter)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(5)
        splitter.setChildrenCollapsible(False)

        left_card = QFrame()
        left_card.setObjectName("CardPanel")
        left_lay = QVBoxLayout(left_card)
        left_lay.setContentsMargins(18, 16, 18, 16)
        left_lay.setSpacing(12)
        left_head = QFrame()
        left_head.setObjectName("CardHeader")
        lh = QVBoxLayout(left_head)
        lh.setContentsMargins(0, 0, 0, 0)
        lh.setSpacing(4)
        lt = QLabel("イベント一覧")
        lt.setObjectName("CardTitle")
        lh_hint = QLabel(
            "和音は chordify による推定。3列目を編集して Enter で反映（ピアノロール更新）。"
        )
        lh_hint.setObjectName("CardHint")
        lh_hint.setWordWrap(True)
        lh.addWidget(lt)
        lh.addWidget(lh_hint)
        left_lay.addWidget(left_head)

        self._key_label = QLabel("検出キー: —")
        self._key_label.setObjectName("KeyLabel")
        self._key_label.setWordWrap(True)
        left_lay.addWidget(self._key_label)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["小節", "オフセット", "コード／音名（編集可）"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(True)
        self.table.setSelectionBehavior(self.table.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(self.table.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked)
        self.table.setSortingEnabled(False)
        self.table.verticalHeader().setDefaultSectionSize(30)
        self.table.setColumnWidth(0, 68)
        self.table.setColumnWidth(1, 100)
        left_lay.addWidget(self.table, stretch=1)

        sug_title = QLabel("推奨コード（キーに基づく候補 · ダブルクリックで適用）")
        sug_title.setObjectName("CardTitle")
        left_lay.addWidget(sug_title)
        self.suggestions = QListWidget()
        self.suggestions.setMaximumHeight(130)
        self.suggestions.setMinimumHeight(80)
        left_lay.addWidget(self.suggestions)

        mel_title = QLabel(
            "メロディ候補（1つ前の音＋現在の和音・旋法から理論的に取りうる音）"
        )
        mel_title.setObjectName("CardTitle")
        mel_title.setWordWrap(True)
        left_lay.addWidget(mel_title)
        self.melody_suggestions = QListWidget()
        self.melody_suggestions.setMaximumHeight(150)
        self.melody_suggestions.setMinimumHeight(88)
        left_lay.addWidget(self.melody_suggestions)

        right_card = QFrame()
        right_card.setObjectName("CardPanel")
        right_lay = QVBoxLayout(right_card)
        right_lay.setContentsMargins(18, 16, 18, 16)
        right_lay.setSpacing(12)
        right_head = QFrame()
        right_head.setObjectName("CardHeader")
        rh = QVBoxLayout(right_head)
        rh.setContentsMargins(0, 0, 0, 0)
        rh.setSpacing(4)
        rt = QLabel("ピアノロール")
        rt.setObjectName("CardTitle")
        rh_hint = QLabel(
            "下のツールバーでズーム・パン。編集後は自動で再描画。鍵盤は行選択・再生で発光します。"
        )
        rh_hint.setObjectName("CardHint")
        rh_hint.setWordWrap(True)
        rh.addWidget(rt)
        rh.addWidget(rh_hint)
        right_lay.addWidget(right_head)

        self.score_canvas = ScoreCanvas()
        self.score_canvas.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        right_lay.addWidget(self.score_canvas, stretch=1)

        splitter.addWidget(left_card)
        splitter.addWidget(right_card)
        splitter.setSizes([400, 960])

        central = QWidget()
        central.setObjectName("CentralRoot")
        root = QVBoxLayout(central)
        root.setContentsMargins(16, 12, 16, 14)
        root.setSpacing(14)
        root.addWidget(chrome)
        root.addWidget(splitter, stretch=1)

        kb_row = QHBoxLayout()
        kb_lbl = QLabel("鍵盤（選択・再生中の音が赤く発光）")
        kb_lbl.setObjectName("CardHint")
        kb_row.addWidget(kb_lbl)
        kb_row.addStretch(1)
        root.addLayout(kb_row)
        self.piano = PianoKeyboard()
        root.addWidget(self.piano)

        self.table.cellChanged.connect(self._on_table_cell_changed)
        self.table.itemSelectionChanged.connect(self._on_table_selection_changed)
        self.suggestions.itemDoubleClicked.connect(self._on_suggestion_activated)
        self.melody_suggestions.itemDoubleClicked.connect(self._on_melody_suggestion_activated)

        self.setCentralWidget(central)
        sb = QStatusBar()
        sb.setSizeGripEnabled(True)
        self.setStatusBar(sb)
        self.statusBar().showMessage("Ready — MIDI を開くか、このウィンドウへドロップしてください")

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            for u in event.mimeData().urls():
                p = Path(u.toLocalFile())
                if p.suffix.lower() in {".mid", ".midi"}:
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
        path, _ = QFileDialog.getOpenFileName(
            self,
            "MIDI を開く",
            "",
            "MIDI (*.mid *.midi);;すべて (*.*)",
        )
        if path:
            self.load_file(path)

    def export_musicxml(self):
        if self._work_flat is None:
            QMessageBox.information(self, "MusicXML", "先に MIDI を読み込んでください。")
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            "MusicXML を保存",
            str(self._current_path or "") + ".musicxml",
            "MusicXML (*.musicxml);;XML (*.xml);;すべて (*.*)",
        )
        if not path:
            return
        try:
            self._work_flat.write("musicxml", fp=path)
            self.statusBar().showMessage(f"保存しました: {path}", 10000)
        except Exception:
            QMessageBox.critical(self, "エラー", traceback.format_exc())

    def export_midi_file(self):
        if self._work_flat is None:
            QMessageBox.information(self, "MIDI", "先に MIDI を読み込んでください。")
            return
        default = (str(self._current_path) if self._current_path else "edited") + ".mid"
        path, _ = QFileDialog.getSaveFileName(
            self,
            "編集済み MIDI を保存",
            default,
            "MIDI (*.mid *.midi);;すべて (*.*)",
        )
        if not path:
            return
        try:
            self._work_flat.write("midi", fp=path)
            self.statusBar().showMessage(f"MIDI を保存しました: {path}", 10000)
        except Exception:
            QMessageBox.critical(self, "エラー", traceback.format_exc())

    def _enable_score_controls(self, on: bool) -> None:
        self.export_act.setEnabled(on)
        self.export_midi_act.setEnabled(on)
        self._export_btn.setEnabled(on)
        self._export_midi_btn.setEnabled(on)
        self._play_btn.setEnabled(on)
        self._stop_btn.setEnabled(on)
        self._tempo_spin.setEnabled(on)

    def _fill_table_from_work(self) -> None:
        assert self._work_flat is not None
        self._suppress_table = True
        self.table.blockSignals(True)
        self.table.setRowCount(0)
        self._row_ql.clear()
        for el in self._work_flat.flatten().notesAndRests:
            if isinstance(el, m21_chord.Chord):
                label = el.pitchedCommonName or str(el)
            elif isinstance(el, m21_note.Note):
                label = f"{el.nameWithOctave}（単音）"
            else:
                continue
            r = self.table.rowCount()
            self.table.insertRow(r)
            m = getattr(el, "measureNumber", None)
            it0 = QTableWidgetItem("" if m is None else str(m))
            it0.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            it1 = QTableWidgetItem(f"{float(el.offset):.3f}")
            it1.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            it2 = QTableWidgetItem(label)
            it2.setFlags(
                Qt.ItemFlag.ItemIsSelectable
                | Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsEditable
            )
            self.table.setItem(r, 0, it0)
            self.table.setItem(r, 1, it1)
            self.table.setItem(r, 2, it2)
            self._row_ql.append(float(el.quarterLength))
        self.table.blockSignals(False)
        self._suppress_table = False

    def _rebuild_stream_from_table(self) -> None:
        new_flat = m21_stream.Stream()
        ts_set = False
        if self._work_flat is not None:
            for ts in self._work_flat.flatten().getElementsByClass(meter.TimeSignature):
                new_flat.insert(0.0, copy.deepcopy(ts))
                ts_set = True
                break
        if not ts_set:
            new_flat.insert(0.0, meter.TimeSignature("4/4"))
        for r in range(self.table.rowCount()):
            off = float(self.table.item(r, 1).text())
            ql = self._row_ql[r]
            txt = self.table.item(r, 2).text()
            el, _ = parse_chord_cell(txt, ql)
            new_flat.insert(off, el)
        self._work_flat = new_flat

    def _refresh_piano_roll_plot(self) -> None:
        if self._work_flat is None:
            return
        plt.close("all")
        plot_obj = self._work_flat.plot("pianoroll", doneAction=None, figureSize=(14, 8))
        self.score_canvas.set_plot(plot_obj)

    def _on_table_cell_changed(self, row: int, col: int) -> None:
        if self._suppress_table or col != 2 or self._work_flat is None:
            return
        item = self.table.item(row, col)
        if item is None:
            return
        txt = item.text()
        ql = self._row_ql[row]
        try:
            el, mids = parse_chord_cell(txt, ql)
        except Exception as e:
            QMessageBox.warning(self, "表記エラー", f"解釈できません:\n{txt}\n\n{e}")
            return
        try:
            self._rebuild_stream_from_table()
            self._refresh_piano_roll_plot()
            self.piano.set_active_pitches(set(mids))
            self._refresh_suggestions_for_row(row)
        except Exception:
            QMessageBox.critical(self, "エラー", traceback.format_exc())

    def _on_table_selection_changed(self) -> None:
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            self.piano.clear_active()
            self.suggestions.clear()
            self.melody_suggestions.clear()
            return
        r = rows[0].row()
        self._refresh_suggestions_for_row(r)
        if r >= len(self._row_ql):
            return
        it = self.table.item(r, 2)
        if it is None:
            return
        try:
            _, mids = parse_chord_cell(it.text(), self._row_ql[r])
            self.piano.set_active_pitches(set(mids))
        except Exception:
            self.piano.clear_active()

    def _refresh_suggestions_for_row(self, r: int) -> None:
        self.suggestions.clear()
        self.melody_suggestions.clear()
        if r < 0 or r >= len(self._row_ql):
            return
        it = self.table.item(r, 2)
        if it is None:
            return
        try:
            el, _ = parse_chord_cell(it.text(), self._row_ql[r])
        except Exception:
            self.suggestions.addItem("（この行のコード表記を解釈できません）")
            return
        for s in targeted_chord_suggestions(el, self._detected_key):
            self.suggestions.addItem(s)

        prev_m = melody_midi_from_previous_row(self.table, self._row_ql, r)
        harm = harmony_chord_for_melody_at_row(self.table, self._row_ql, r, self._detected_key)
        for line in melodic_note_candidates(prev_m, harm, self._detected_key):
            self.melody_suggestions.addItem(line)

    def _on_suggestion_activated(self, item: QListWidgetItem) -> None:
        row = self.table.currentRow()
        if row < 0 or item is None:
            return
        txt = item.text()
        if txt.startswith("（"):
            return
        self._suppress_table = True
        self.table.blockSignals(True)
        self.table.item(row, 2).setText(txt)
        self.table.blockSignals(False)
        self._suppress_table = False
        self._rebuild_stream_from_table()
        self._refresh_piano_roll_plot()
        try:
            _, mids = parse_chord_cell(txt, self._row_ql[row])
            self.piano.set_active_pitches(set(mids))
        except Exception:
            pass
        self._refresh_suggestions_for_row(row)

    def _on_melody_suggestion_activated(self, item: QListWidgetItem) -> None:
        row = self.table.currentRow()
        if row < 0 or item is None:
            return
        raw = item.text().strip()
        if raw.startswith("（") or "候補を生成" in raw or "キー未検出" in raw or "特定できません" in raw:
            return
        part = raw.split("—")[0].strip()
        try:
            p_only = m21_pitch.Pitch(part)
            new_text = f"{p_only.nameWithOctave}（単音）"
        except Exception:
            return
        try:
            el0, _ = parse_chord_cell(self.table.item(row, 2).text(), self._row_ql[row])
        except Exception:
            return
        if not isinstance(el0, m21_note.Note):
            QMessageBox.information(
                self,
                "メロディ候補",
                "メロディ候補の適用は「単音」の行だけです。\n"
                "コード行のままでは上書きできません。3列目を単音表記（例: C5（単音））にしてから再度お試しください。",
            )
            return
        self._suppress_table = True
        self.table.blockSignals(True)
        self.table.item(row, 2).setText(new_text)
        self.table.blockSignals(False)
        self._suppress_table = False
        self._rebuild_stream_from_table()
        self._refresh_piano_roll_plot()
        try:
            _, mids = parse_chord_cell(new_text, self._row_ql[row])
            self.piano.set_active_pitches(set(mids))
        except Exception:
            pass
        self._refresh_suggestions_for_row(row)
        self.statusBar().showMessage(f"メロディを {new_text} に変更しました", 6000)

    def play_transport(self) -> None:
        if self._work_flat is None:
            return
        self.stop_transport()
        tl = build_playback_timeline(self._work_flat)
        if not tl:
            QMessageBox.information(self, "再生", "再生できる音符がありません。")
            return
        self._playback = PlaybackThread(tl, self._tempo_spin.value(), self)
        self._playback.highlight.connect(self.piano.set_active_pitches)
        self._playback.finished_playback.connect(self._on_playback_finished)
        self._play_btn.setEnabled(False)
        self._playback.start()

    def _on_playback_finished(self) -> None:
        self.piano.clear_active()
        self._play_btn.setEnabled(True)
        self._playback = None

    def stop_transport(self) -> None:
        if self._playback is not None:
            self._playback.requestInterruption()
            self._playback.wait(8000)
        self._playback = None
        self.piano.clear_active()
        self._play_btn.setEnabled(self._work_flat is not None)

    def load_file(self, path: str):
        self.statusBar().showMessage("読み込み中…")
        QApplication.processEvents()
        self.stop_transport()
        try:
            plt.close("all")
            score = load_score(path)
            self._original_score = score
            self._work_flat = build_flat_work_stream(score)
            self._current_path = Path(path)

            ktxt, kobj = detect_key_for_score(score)
            if kobj is None:
                ktxt, kobj = detect_key_for_score(self._work_flat)
            self._key_label.setText(f"検出キー: {ktxt}")
            self._detected_key = kobj

            self._fill_table_from_work()
            self._refresh_piano_roll_plot()
            self.suggestions.clear()
            self.melody_suggestions.clear()
            self.piano.clear_active()

            self._enable_score_controls(True)
            name = self._current_path.name
            short = name if len(name) <= 30 else name[:27] + "…"
            self._status_badge.setText(f" {short} ")
            self.setWindowTitle(f"MIDI Chord Lab — {name}")
            n = self.table.rowCount()
            self.statusBar().showMessage(
                f"{name} · {n} イベント · chordify 和声トラックを編集できます（MIDI 書き出しはこのトラック）",
                12000,
            )
        except Exception:
            self._original_score = None
            self._work_flat = None
            self._current_path = None
            self._detected_key = None
            self._key_label.setText("検出キー: —")
            self._enable_score_controls(False)
            self._status_badge.setText(" STUDIO ")
            self.setWindowTitle("MIDI Chord Lab")
            self.table.setRowCount(0)
            self._row_ql.clear()
            self.suggestions.clear()
            self.melody_suggestions.clear()
            self.score_canvas.show_placeholder()
            QMessageBox.critical(self, "読み込みエラー", traceback.format_exc())
            self.statusBar().showMessage("読み込みに失敗しました")


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    if sys.platform == "win32":
        ui = QFont("Yu Gothic UI", 10)
    elif sys.platform == "darwin":
        ui = QFont(".AppleSystemUIFont", 11)
    else:
        ui = QFont("Noto Sans CJK JP", 10)
    app.setFont(ui)
    app.setStyleSheet(APP_STYLESHEET)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
