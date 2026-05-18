# -*- coding: utf-8 -*-
"""読みやすいカスタム・ピアノロール（matplotlib）。"""
from __future__ import annotations

from typing import TYPE_CHECKING

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle

from midi_lab.core.note_events import NoteEvent
from midi_lab.core.plotting import theme_matplotlib_figure
from midi_lab.ui import design_tokens as dt

if TYPE_CHECKING:
    from music21 import stream as m21_stream


def _midi_to_name(midi: int) -> str:
    names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    return f"{names[midi % 12]}{midi // 12 - 1}"


def build_pianoroll_figure(work: m21_stream.Stream, figsize: tuple[float, float] = (14.0, 7.0)) -> Figure:
    """和声ストリームからダークテーマのピアノロール Figure を生成。"""
    from music21 import chord as m21_chord
    from music21 import note as m21_note

    events: list[tuple[float, float, int, bool]] = []
    for el in work.flatten().notesAndRests:
        if isinstance(el, m21_chord.Chord):
            for p in el.pitches:
                events.append((float(el.offset), float(el.quarterLength), int(p.midi), True))
        elif isinstance(el, m21_note.Note):
            events.append((float(el.offset), float(el.quarterLength), int(el.pitch.midi), False))

    fig, ax = plt.subplots(figsize=figsize, facecolor=dt.MPL_BG)
    ax.set_facecolor(dt.MPL_PANEL)

    if not events:
        ax.text(
            0.5,
            0.5,
            "表示できる音符がありません",
            transform=ax.transAxes,
            ha="center",
            va="center",
            color=dt.TEXT_MUTED,
            fontsize=12,
        )
        theme_matplotlib_figure(fig)
        return fig

    min_off = min(e[0] for e in events)
    max_end = max(e[0] + e[1] for e in events)
    min_midi = min(e[2] for e in events)
    max_midi = max(e[2] for e in events)
    pad_p = 3
    y0, y1 = min_midi - pad_p, max_midi + pad_p

    # 拍区切り（1拍ごと）
    beat = 1.0
    x_start = max(0.0, min_off - 0.5)
    x_end = max_end + 0.5
    beat_x = np.arange(int(x_start), int(x_end) + 2, beat)
    for bx in beat_x:
        ax.axvline(bx, color=dt.MPL_GRID, linewidth=0.6, alpha=0.35, zorder=0)

    for off, dur, midi, is_chord in events:
        color = dt.HARMONY if is_chord else dt.ACCENT
        edge = "#e4e4e7" if is_chord else "#fde68a"
        rect = Rectangle(
            (off, midi - 0.42),
            max(dur, 0.08),
            0.84,
            facecolor=color,
            edgecolor=edge,
            linewidth=0.6,
            alpha=0.92,
            zorder=2 if is_chord else 3,
        )
        ax.add_patch(rect)

    ax.set_xlim(x_start, x_end)
    ax.set_ylim(y0 - 0.5, y1 + 0.5)
    ax.set_xlabel("拍（曲頭から / 四分音符）", color=dt.MPL_LABEL, fontsize=10, labelpad=8)
    ax.set_ylabel("音高", color=dt.MPL_LABEL, fontsize=10, labelpad=8)

    # Y 軸: 音名（適度な間引き）
    span = y1 - y0
    step = 1 if span <= 14 else (2 if span <= 24 else 3)
    ticks = list(range(int(y0), int(y1) + 1, step))
    ax.set_yticks(ticks)
    ax.set_yticklabels([_midi_to_name(t) for t in ticks], fontsize=9)

    ax.set_title("ピアノロール", color=dt.TEXT_PRIMARY, fontsize=12, fontweight="bold", pad=12)
    theme_matplotlib_figure(fig)
    fig.tight_layout(pad=1.4)
    return fig


def build_pianoroll_figure_from_notes(
    events: list[NoteEvent],
    figsize: tuple[float, float] = (14.0, 7.0),
) -> Figure:
    """生ノート列からベロシティで彩度を変えたピアノロール。"""
    fig, ax = plt.subplots(figsize=figsize, facecolor=dt.MPL_BG)
    ax.set_facecolor(dt.MPL_PANEL)

    if not events:
        ax.text(
            0.5, 0.5, "表示できる音符がありません",
            transform=ax.transAxes, ha="center", va="center",
            color=dt.TEXT_MUTED, fontsize=12,
        )
        theme_matplotlib_figure(fig)
        return fig

    min_off = min(e.offset for e in events)
    max_end = max(e.offset + e.quarter_length for e in events)
    min_midi = min(e.midi for e in events)
    max_midi = max(e.midi for e in events)
    pad_p = 3
    y0, y1 = min_midi - pad_p, max_midi + pad_p
    vels = [e.velocity for e in events]
    vmin, vmax = min(vels), max(vels)
    vspan = max(vmax - vmin, 1)

    beat_x = np.arange(int(max(0, min_off - 0.5)), int(max_end + 2) + 1, 1.0)
    for bx in beat_x:
        ax.axvline(bx, color=dt.MPL_GRID, linewidth=0.6, alpha=0.35, zorder=0)

    for e in events:
        alpha = 0.45 + 0.5 * (e.velocity - vmin) / vspan
        hue = 0.55 + 0.12 * ((e.midi - min_midi) / max(y1 - y0, 1))
        color = plt.cm.cool(hue)
        rect = Rectangle(
            (e.offset, e.midi - 0.42),
            max(e.quarter_length, 0.06),
            0.84,
            facecolor=color,
            edgecolor=dt.BORDER_STRONG,
            linewidth=0.4,
            alpha=alpha,
            zorder=2,
        )
        ax.add_patch(rect)

    ax.set_xlim(max(0.0, min_off - 0.5), max_end + 0.5)
    ax.set_ylim(y0 - 0.5, y1 + 0.5)
    ax.set_xlabel("拍（曲頭から / 四分音符）", color=dt.MPL_LABEL, fontsize=10, labelpad=8)
    ax.set_ylabel("音高", color=dt.MPL_LABEL, fontsize=10, labelpad=8)
    span = y1 - y0
    step = 1 if span <= 14 else (2 if span <= 24 else 3)
    ticks = list(range(int(y0), int(y1) + 1, step))
    ax.set_yticks(ticks)
    ax.set_yticklabels([_midi_to_name(t) for t in ticks], fontsize=9)
    ax.set_title(
        "ピアノロール（全パート · ベロシティ連動）",
        color=dt.TEXT_PRIMARY, fontsize=12, fontweight="bold", pad=12,
    )
    theme_matplotlib_figure(fig)
    fig.tight_layout(pad=1.4)
    return fig
