# -*- coding: utf-8 -*-
"""MIDI ビジュアライザ — 複数スタイルのフレーム描画。"""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.collections import LineCollection
from matplotlib.figure import Figure

from midi_lab.core.note_events import NoteEvent
from midi_lab.core.plotting import theme_matplotlib_figure
from midi_lab.ui import design_tokens as dt

DEFAULT_WINDOW_SEC = 8.0
_MIN_MIDI = 21
_MAX_MIDI = 108
_CHROMA = 12


class VisualStyle(StrEnum):
    WATERFALL = "waterfall"
    SPECTRUM = "spectrum"
    PARTICLE = "particle"
    CHROMA_RING = "chroma_ring"
    VELOCITY_RIBBON = "velocity_ribbon"


STYLE_LABELS: dict[VisualStyle, str] = {
    VisualStyle.WATERFALL: "ウォーターフォール（ピアノロール）",
    VisualStyle.SPECTRUM: "スペクトラム（音域バー）",
    VisualStyle.PARTICLE: "パーティクル（発光トレイル）",
    VisualStyle.CHROMA_RING: "クロマリング（十二音環）",
    VisualStyle.VELOCITY_RIBBON: "ベロシティリボン",
}

ALL_STYLES: tuple[VisualStyle, ...] = tuple(VisualStyle)


def ql_to_sec(ql: float, bpm: float) -> float:
    bpm = max(20.0, float(bpm))
    return float(ql) * 60.0 / bpm


def sec_to_ql(sec: float, bpm: float) -> float:
    bpm = max(20.0, float(bpm))
    return float(sec) * bpm / 60.0


def score_duration_ql(events: list[NoteEvent]) -> float:
    if not events:
        return 4.0
    return max(e.offset + max(e.quarter_length, 0.06) for e in events)


def visible_beat_window(
    t_ql: float,
    window_ql: float,
    duration_ql: float,
) -> tuple[float, float]:
    """表示する拍範囲 [x0, x1]。曲頭では [0, window_ql] を確保する。"""
    duration_ql = max(float(duration_ql), 0.01)
    window_ql = max(float(window_ql), 0.25)
    t_ql = max(0.0, min(float(t_ql), duration_ql))
    if t_ql < window_ql * 0.05:
        return 0.0, min(window_ql, duration_ql)
    x0 = max(0.0, t_ql - window_ql)
    x1 = min(max(t_ql + 0.02, x0 + 0.5), duration_ql + 0.02)
    return x0, x1


@dataclass(frozen=True)
class VisualizerData:
    offsets: np.ndarray
    ends: np.ndarray
    midis: np.ndarray
    velocities: np.ndarray
    parts: np.ndarray
    duration_ql: float

    @classmethod
    def from_events(cls, events: list[NoteEvent]) -> VisualizerData:
        if not events:
            z = np.zeros(0, dtype=np.float64)
            return cls(z, z, z, z, z, 4.0)
        offsets = np.fromiter((e.offset for e in events), dtype=np.float64, count=len(events))
        durs = np.fromiter(
            (max(e.quarter_length, 0.06) for e in events), dtype=np.float64, count=len(events)
        )
        midis = np.fromiter((e.midi for e in events), dtype=np.int16, count=len(events))
        vels = np.fromiter((e.velocity for e in events), dtype=np.float32, count=len(events))
        parts = np.fromiter((e.part_index for e in events), dtype=np.int16, count=len(events))
        return cls(offsets, offsets + durs, midis, vels, parts, score_duration_ql(events))

    def y_range(self) -> tuple[float, float]:
        if len(self.midis) == 0:
            return float(_MIN_MIDI), float(_MAX_MIDI)
        y0 = max(_MIN_MIDI, int(self.midis.min()) - 2)
        y1 = min(_MAX_MIDI, int(self.midis.max()) + 2)
        if y1 - y0 < 12:
            mid = (y0 + y1) // 2
            y0, y1 = mid - 8, mid + 8
        return float(y0), float(y1)

    def mask_in_range(self, x0: float, x1: float) -> np.ndarray:
        return (self.ends > x0) & (self.offsets < x1)

    def chroma_energy_at(self, t_ql: float, decay_ql: float = 0.35) -> np.ndarray:
        energy = np.zeros(_CHROMA, dtype=np.float64)
        if len(self.midis) == 0:
            return energy
        for i in range(len(self.midis)):
            if self.offsets[i] <= t_ql < self.ends[i]:
                w = 1.0
            elif t_ql < self.offsets[i]:
                gap = self.offsets[i] - t_ql
                w = max(0.0, 1.0 - gap / decay_ql) if gap < decay_ql else 0.0
            else:
                gap = t_ql - self.ends[i]
                w = max(0.0, 1.0 - gap / decay_ql) if gap < decay_ql else 0.0
            if w <= 0:
                continue
            pc = int(self.midis[i]) % _CHROMA
            energy[pc] += float(self.velocities[i]) * w
        return energy

    def velocity_matrix(
        self, x0: float, x1: float, *, bins: int = _CHROMA
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        span = max(x1 - x0, 0.1)
        n_cols = max(32, int(span * 24))
        edges = np.linspace(x0, x1, n_cols + 1)
        mat = np.zeros((bins, n_cols), dtype=np.float32)
        for i in range(len(self.midis)):
            if self.ends[i] <= x0 or self.offsets[i] >= x1:
                continue
            pc = int(self.midis[i]) % bins
            v = self.velocities[i] / 127.0
            for j in range(n_cols):
                seg_a, seg_b = edges[j], edges[j + 1]
                overlap = min(self.ends[i], seg_b) - max(self.offsets[i], seg_a)
                if overlap > 0:
                    mat[pc, j] = max(mat[pc, j], v)
        return edges, np.arange(bins), mat


def _new_figure(figsize: tuple[float, float], dpi: int, *, for_ui: bool = False) -> Figure:
    fig = plt.figure(figsize=figsize, dpi=dpi)
    if for_ui:
        fig.subplots_adjust(left=0.07, right=0.99, top=0.99, bottom=0.10)
    else:
        fig.set_layout_engine("constrained")
    theme_matplotlib_figure(fig)
    return fig


def _playhead_color() -> str:
    return dt.ACCENT


def _render_waterfall(
    data: VisualizerData,
    t_ql: float,
    window_ql: float,
    fig: Figure,
    *,
    for_ui: bool = False,
) -> None:
    ax = fig.add_subplot(111)
    x0, x1 = visible_beat_window(t_ql, window_ql, data.duration_ql)
    m = data.mask_in_range(x0, x1)
    y0, y1 = data.y_range()
    if m.any():
        off = data.offsets[m]
        end = data.ends[m]
        mid = data.midis[m].astype(np.float64)
        vel = data.velocities[m]
        segs = np.stack(
            [np.column_stack([off, mid]), np.column_stack([end, mid])],
            axis=1,
        )
        lc = LineCollection(
            segs,
            array=vel,
            cmap=plt.cm.plasma,
            linewidths=2.8,
            capstyle="butt",
            alpha=0.9,
        )
        ax.add_collection(lc)
    for bx in np.arange(int(x0), int(x1) + 2):
        ax.axvline(bx, color=dt.MPL_GRID, linewidth=0.5, alpha=0.35, zorder=0)
    ax.axvline(t_ql, color=_playhead_color(), linewidth=2.0, alpha=0.95, zorder=5)
    ax.set_xlim(x0, x1)
    ax.set_ylim(y0 - 0.5, y1 + 0.5)
    ax.set_xlabel("拍（四分音符）")
    ax.set_ylabel("音高 (MIDI)")
    if not for_ui:
        ax.set_title(STYLE_LABELS[VisualStyle.WATERFALL])


def _render_spectrum(
    data: VisualizerData,
    t_ql: float,
    fig: Figure,
    *,
    for_ui: bool = False,
) -> None:
    ax = fig.add_subplot(111)
    y0, y1 = int(data.y_range()[0]), int(data.y_range()[1])
    keys = np.arange(y0, y1 + 1)
    heights = np.zeros(len(keys), dtype=np.float64)
    colors = np.zeros((len(keys), 4))
    cmap = plt.cm.viridis
    for i in range(len(data.midis)):
        if data.offsets[i] <= t_ql < data.ends[i]:
            idx = int(data.midis[i]) - y0
            if 0 <= idx < len(keys):
                v = float(data.velocities[i]) / 127.0
                heights[idx] = max(heights[idx], v)
    for j, h in enumerate(heights):
        colors[j] = cmap(h if h > 0 else 0.05)
    ax.bar(keys, heights, width=0.85, color=colors, edgecolor=dt.BORDER_DEFAULT, linewidth=0.3)
    ax.set_xlim(y0 - 0.5, y1 + 0.5)
    ax.set_ylim(0, 1.05)
    ax.set_xlabel("MIDI ノート番号")
    ax.set_ylabel("ベロシティ（正規化）")
    if not for_ui:
        ax.set_title(STYLE_LABELS[VisualStyle.SPECTRUM])


def _render_particle(
    data: VisualizerData,
    t_ql: float,
    window_ql: float,
    fig: Figure,
    *,
    for_ui: bool = False,
) -> None:
    ax = fig.add_subplot(111)
    x0, x1 = visible_beat_window(t_ql, window_ql, data.duration_ql)
    m = data.mask_in_range(x0, x1)
    y0, y1 = data.y_range()
    if m.any():
        off = data.offsets[m]
        mid = data.midis[m].astype(np.float64)
        vel = data.velocities[m]
        age = np.clip((t_ql - off) / max(window_ql, 0.1), 0, 1)
        sizes = 12 + 48 * (vel / 127.0)
        ax.scatter(
            off,
            mid,
            s=sizes,
            c=vel,
            cmap=plt.cm.cool,
            alpha=0.35 + 0.55 * (1.0 - age),
            edgecolors=dt.ACCENT,
            linewidths=0.4,
            zorder=3,
        )
        segs = []
        seg_c = []
        for i in range(len(off)):
            segs.append([[off[i], mid[i]], [t_ql, mid[i]]])
            seg_c.append(vel[i])
        if segs:
            lc = LineCollection(
                segs,
                array=np.array(seg_c),
                cmap=plt.cm.cool,
                linewidths=1.2,
                alpha=0.45,
            )
            ax.add_collection(lc)
    ax.axvline(t_ql, color=_playhead_color(), linewidth=2.0, alpha=0.95, zorder=5)
    ax.set_xlim(x0, x1)
    ax.set_ylim(y0 - 0.5, y1 + 0.5)
    ax.set_xlabel("拍")
    ax.set_ylabel("音高 (MIDI)")
    if not for_ui:
        ax.set_title(STYLE_LABELS[VisualStyle.PARTICLE])


def _render_chroma_ring(
    data: VisualizerData,
    t_ql: float,
    fig: Figure,
    *,
    for_ui: bool = False,
) -> None:
    ax = fig.add_subplot(111, projection="polar")
    energy = data.chroma_energy_at(t_ql)
    if energy.max() > 0:
        energy = energy / energy.max()
    theta = np.linspace(0, 2 * np.pi, _CHROMA, endpoint=False)
    width = 2 * np.pi / _CHROMA * 0.92
    names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    colors = plt.cm.twilight(energy * 0.85 + 0.1)
    ax.bar(theta, 0.35 + 0.65 * energy, width=width, bottom=0.2, color=colors, alpha=0.92)
    ax.set_theta_zero_location("N")
    ax.set_theta_direction(-1)
    ax.set_xticks(theta)
    ax.set_xticklabels(names, color=dt.MPL_TICK, fontsize=9)
    ax.set_yticklabels([])
    ax.set_ylim(0, 1.2)
    ax.set_facecolor(dt.MPL_PANEL)
    if not for_ui:
        ax.set_title(STYLE_LABELS[VisualStyle.CHROMA_RING], pad=16, color=dt.TEXT_PRIMARY)


def _render_velocity_ribbon(
    data: VisualizerData,
    t_ql: float,
    window_ql: float,
    fig: Figure,
    *,
    for_ui: bool = False,
) -> None:
    ax = fig.add_subplot(111)
    x0, x1 = visible_beat_window(t_ql, window_ql, data.duration_ql)
    edges, chroma_idx, mat = data.velocity_matrix(x0, x1)
    if mat.size == 0:
        ax.text(0.5, 0.5, "ノートなし", ha="center", va="center", transform=ax.transAxes)
    else:
        pc_names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
        ax.imshow(
            mat,
            aspect="auto",
            origin="lower",
            extent=[edges[0], edges[-1], -0.5, len(chroma_idx) - 0.5],
            cmap="magma",
            vmin=0,
            vmax=1,
            interpolation="bilinear",
        )
        if not for_ui:
            fig.colorbar(
                ax.images[0],
                ax=ax,
                label="ベロシティ",
                fraction=0.035,
                pad=0.02,
            )
        ax.set_yticks(range(_CHROMA))
        ax.set_yticklabels(pc_names)
    ax.axvline(t_ql, color=_playhead_color(), linewidth=1.8, alpha=0.95)
    ax.set_xlim(x0, x1)
    ax.set_xlabel("拍")
    ax.set_ylabel("ピッチクラス")
    if not for_ui:
        ax.set_title(STYLE_LABELS[VisualStyle.VELOCITY_RIBBON])


def render_frame(
    style: VisualStyle,
    events: list[NoteEvent],
    *,
    t_sec: float = 0.0,
    bpm: float = 120.0,
    window_sec: float = DEFAULT_WINDOW_SEC,
    figsize: tuple[float, float] = (12.8, 7.2),
    dpi: int = 100,
    data: VisualizerData | None = None,
    for_ui: bool = False,
) -> Figure | None:
    """指定時刻の 1 フレームを描画。events が空なら None。"""
    if not events:
        return None
    vd = data if data is not None else VisualizerData.from_events(events)
    t_ql = min(sec_to_ql(t_sec, bpm), vd.duration_ql)
    window_ql = sec_to_ql(window_sec, bpm)
    fig = _new_figure(figsize, dpi, for_ui=for_ui)
    ui = for_ui
    if style == VisualStyle.WATERFALL:
        _render_waterfall(vd, t_ql, window_ql, fig, for_ui=ui)
    elif style == VisualStyle.SPECTRUM:
        _render_spectrum(vd, t_ql, fig, for_ui=ui)
    elif style == VisualStyle.PARTICLE:
        _render_particle(vd, t_ql, window_ql, fig, for_ui=ui)
    elif style == VisualStyle.CHROMA_RING:
        _render_chroma_ring(vd, t_ql, fig, for_ui=ui)
    elif style == VisualStyle.VELOCITY_RIBBON:
        _render_velocity_ribbon(vd, t_ql, window_ql, fig, for_ui=ui)
    else:
        plt.close(fig)
        return None
    return fig


def build_preview_figure(
    style: VisualStyle,
    events: list[NoteEvent],
    *,
    bpm: float = 120.0,
    t_sec: float = 0.0,
    window_sec: float = DEFAULT_WINDOW_SEC,
    for_ui: bool = True,
) -> Figure | None:
    """UI 用プレビュー（指定秒位置）。"""
    if not events:
        return None
    vd = VisualizerData.from_events(events)
    return render_frame(
        style,
        events,
        t_sec=t_sec,
        bpm=bpm,
        window_sec=window_sec,
        figsize=(10.0, 6.0),
        dpi=96,
        data=vd,
        for_ui=for_ui,
    )
