# -*- coding: utf-8 -*-
"""読みやすいカスタム・ピアノロール（matplotlib）。"""
from __future__ import annotations

from typing import TYPE_CHECKING

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.collections import LineCollection
from matplotlib.figure import Figure

from midi_lab.core.note_events import NoteEvent
from midi_lab.core.plotting import theme_matplotlib_figure
from midi_lab.ui import design_tokens as dt

if TYPE_CHECKING:
    from music21 import stream as m21_stream

# 1 ノート = 1 Rectangle は大曲で数十秒かかるため LineCollection で描画
_MAX_PIANOROLL_NOTES = 80_000


def _midi_to_name(midi: int) -> str:
    names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    return f"{names[midi % 12]}{midi // 12 - 1}"


def _draw_beat_grid(ax, x_start: float, x_end: float) -> None:
    beat_x = np.arange(int(x_start), int(x_end) + 2, 1.0)
    for bx in beat_x:
        ax.axvline(bx, color=dt.MPL_GRID, linewidth=0.6, alpha=0.35, zorder=0)


def _apply_y_axis(ax, y0: float, y1: float) -> None:
    span = y1 - y0
    step = 1 if span <= 14 else (2 if span <= 24 else 3)
    ticks = list(range(int(y0), int(y1) + 1, step))
    ax.set_yticks(ticks)
    ax.set_yticklabels([_midi_to_name(t) for t in ticks], fontsize=9)


def _note_events_to_arrays(events: list[NoteEvent]) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, bool]:
    """(offsets, ends, midis, velocities, was_downsampled)"""
    n = len(events)
    downsampled = False
    if n > _MAX_PIANOROLL_NOTES:
        stride = (n + _MAX_PIANOROLL_NOTES - 1) // _MAX_PIANOROLL_NOTES
        events = events[::stride]
        downsampled = True
    offsets = np.fromiter((e.offset for e in events), dtype=np.float64, count=len(events))
    durs = np.fromiter(
        (max(e.quarter_length, 0.06) for e in events), dtype=np.float64, count=len(events)
    )
    midis = np.fromiter((e.midi for e in events), dtype=np.float64, count=len(events))
    vels = np.fromiter((e.velocity for e in events), dtype=np.float32, count=len(events))
    return offsets, offsets + durs, midis, vels, downsampled


def _add_note_segments(
    ax,
    offsets: np.ndarray,
    ends: np.ndarray,
    midis: np.ndarray,
    *,
    color_values: np.ndarray | None = None,
    linewidth: float = 2.6,
    cmap=plt.cm.cool,
) -> None:
    segments = np.stack(
        [np.column_stack([offsets, midis]), np.column_stack([ends, midis])],
        axis=1,
    )
    if color_values is not None:
        lc = LineCollection(
            segments,
            array=color_values,
            cmap=cmap,
            linewidths=linewidth,
            capstyle="butt",
            alpha=0.88,
            zorder=2,
        )
    else:
        lc = LineCollection(
            segments,
            colors=dt.ACCENT,
            linewidths=linewidth,
            capstyle="butt",
            alpha=0.9,
            zorder=2,
        )
    ax.add_collection(lc)


def build_pianoroll_figure(work: m21_stream.Stream, figsize: tuple[float, float] = (14.0, 7.0)) -> Figure:
    """和声ストリームからダークテーマのピアノロール Figure を生成。"""
    from music21 import chord as m21_chord
    from music21 import note as m21_note

    events: list[tuple[float, float, int, bool]] = []
    flat = work.flatten()
    for el in flat.notesAndRests:
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
    x_start = max(0.0, min_off - 0.5)
    x_end = max_end + 0.5
    _draw_beat_grid(ax, x_start, x_end)

    if len(events) > _MAX_PIANOROLL_NOTES:
        stride = (len(events) + _MAX_PIANOROLL_NOTES - 1) // _MAX_PIANOROLL_NOTES
        events = events[::stride]

    offsets = np.array([e[0] for e in events], dtype=np.float64)
    ends = np.array([e[0] + max(e[1], 0.08) for e in events], dtype=np.float64)
    midis = np.array([e[2] for e in events], dtype=np.float64)
    is_chord = np.array([e[3] for e in events], dtype=bool)
    if is_chord.any():
        mask = is_chord
        _add_note_segments(ax, offsets[mask], ends[mask], midis[mask])
        ax.collections[-1].set_color(dt.HARMONY)
    if (~is_chord).any():
        mask = ~is_chord
        _add_note_segments(ax, offsets[mask], ends[mask], midis[mask])
        ax.collections[-1].set_color(dt.ACCENT)

    ax.set_xlim(x_start, x_end)
    ax.set_ylim(y0 - 0.5, y1 + 0.5)
    ax.set_xlabel("拍（曲頭から / 四分音符）", color=dt.MPL_LABEL, fontsize=10, labelpad=8)
    ax.set_ylabel("音高", color=dt.MPL_LABEL, fontsize=10, labelpad=8)
    _apply_y_axis(ax, y0, y1)
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

    offsets, ends, midis, vels, downsampled = _note_events_to_arrays(events)
    min_off = float(offsets.min())
    max_end = float(ends.max())
    min_midi = int(midis.min())
    max_midi = int(midis.max())
    pad_p = 3
    y0, y1 = min_midi - pad_p, max_midi + pad_p
    x_start = max(0.0, min_off - 0.5)
    x_end = max_end + 0.5
    _draw_beat_grid(ax, x_start, x_end)

    vmin = float(vels.min())
    vmax = float(vels.max())
    vspan = max(vmax - vmin, 1.0)
    color_values = 0.45 + 0.55 * (vels - vmin) / vspan
    _add_note_segments(
        ax, offsets, ends, midis, color_values=color_values, cmap=plt.cm.cool
    )

    ax.set_xlim(x_start, x_end)
    ax.set_ylim(y0 - 0.5, y1 + 0.5)
    ax.set_xlabel("拍（曲頭から / 四分音符）", color=dt.MPL_LABEL, fontsize=10, labelpad=8)
    ax.set_ylabel("音高", color=dt.MPL_LABEL, fontsize=10, labelpad=8)
    _apply_y_axis(ax, y0, y1)
    title = "ピアノロール（全パート · ベロシティ連動）"
    if downsampled:
        title += f" — 表示用に間引き（最大 {_MAX_PIANOROLL_NOTES:,} 音）"
    ax.set_title(title, color=dt.TEXT_PRIMARY, fontsize=12, fontweight="bold", pad=12)
    theme_matplotlib_figure(fig)
    fig.tight_layout(pad=1.4)
    return fig
