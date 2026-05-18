# -*- coding: utf-8 -*-
"""パフォーマンス分析 — ベロシティ・音域・密度の統計と可視化。"""
from __future__ import annotations

from dataclasses import dataclass

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure
from mpl_toolkits.axes_grid1 import make_axes_locatable

from midi_lab.core.note_events import NoteEvent
from midi_lab.core.plotting import plot_font_family, theme_matplotlib_figure
from midi_lab.ui import design_tokens as dt


@dataclass(frozen=True)
class PerformanceReport:
    note_count: int
    part_count: int
    duration_beats: float
    mean_velocity: float
    velocity_std: float
    min_midi: int
    max_midi: int
    register_span: int
    notes_per_beat: float
    peak_density_beat: float
    peak_density_value: int
    low_register_pct: float
    mid_register_pct: float
    high_register_pct: float


def _register_band(midi: int) -> str:
    if midi < 48:
        return "low"
    if midi < 72:
        return "mid"
    return "high"


def analyze_performance(events: list[NoteEvent]) -> PerformanceReport:
    if not events:
        return PerformanceReport(
            0, 0, 0.0, 0.0, 0.0, 0, 0, 0, 0.0, 0.0, 0, 0.0, 0.0, 0.0,
        )
    t0 = min(e.offset for e in events)
    t1 = max(e.offset + e.quarter_length for e in events)
    duration = max(t1 - t0, 0.25)
    vels = [e.velocity for e in events]
    midis = [e.midi for e in events]
    parts = {e.part_index for e in events}
    bands = [_register_band(m) for m in midis]
    n = len(events)
    low = bands.count("low") / n * 100
    mid = bands.count("mid") / n * 100
    high = bands.count("high") / n * 100
    beat_bins: dict[int, int] = {}
    for e in events:
        b = int(e.offset)
        beat_bins[b] = beat_bins.get(b, 0) + 1
    peak_beat = max(beat_bins, key=beat_bins.get) if beat_bins else 0
    peak_val = beat_bins.get(peak_beat, 0)
    return PerformanceReport(
        note_count=n,
        part_count=len(parts),
        duration_beats=duration,
        mean_velocity=float(np.mean(vels)),
        velocity_std=float(np.std(vels)),
        min_midi=min(midis),
        max_midi=max(midis),
        register_span=max(midis) - min(midis),
        notes_per_beat=n / duration,
        peak_density_beat=float(peak_beat),
        peak_density_value=peak_val,
        low_register_pct=low,
        mid_register_pct=mid,
        high_register_pct=high,
    )


def report_summary_text(report: PerformanceReport) -> str:
    if report.note_count == 0:
        return "ノートデータがありません"
    return (
        f"ノート {report.note_count} · パート {report.part_count} · "
        f"長さ {report.duration_beats:.1f} 拍 · "
        f"平均ベロシティ {report.mean_velocity:.0f} (σ={report.velocity_std:.1f}) · "
        f"音域 {report.min_midi}–{report.max_midi} ({report.register_span}半音) · "
        f"密度 {report.notes_per_beat:.2f} 音/拍"
    )


def _style_axis(ax, *, title: str, xlabel: str = "", ylabel: str = "") -> None:
    ax.set_title(title, pad=14, fontsize=11)
    if xlabel:
        ax.set_xlabel(xlabel, labelpad=8, fontsize=9)
    if ylabel:
        ax.set_ylabel(ylabel, labelpad=8, fontsize=9)


def build_performance_dashboard_figure(
    events: list[NoteEvent],
    report: PerformanceReport,
    figsize: tuple[float, float] = (12.0, 10.0),
) -> Figure:
    """2×2 ダッシュボード（constrained_layout + サブプロット内 colorbar）。"""
    fig = plt.figure(figsize=figsize, facecolor=dt.MPL_BG, layout="constrained")
    # hspace を抑えてプロット領域を大きく（ScoreCanvas が実サイズに追従）
    fig.set_constrained_layout_pads(w_pad=0.04, h_pad=0.06, wspace=0.10, hspace=0.22)

    gs = fig.add_gridspec(2, 2, height_ratios=(1.0, 1.0), width_ratios=(1.0, 1.0))
    ax_vel = fig.add_subplot(gs[0, 0])
    ax_pc = fig.add_subplot(gs[0, 1])
    ax_den = fig.add_subplot(gs[1, 0])
    ax_reg = fig.add_subplot(gs[1, 1])
    axes = (ax_vel, ax_pc, ax_den, ax_reg)

    if not events:
        for ax in axes:
            ax.text(
                0.5, 0.5, "データなし",
                transform=ax.transAxes,
                ha="center", va="center",
                color=dt.TEXT_MUTED,
            )
        theme_matplotlib_figure(fig)
        return fig

    offsets = np.array([e.offset for e in events])
    vels = np.array([e.velocity for e in events])
    midis = np.array([e.midi for e in events])
    t0 = float(offsets.min())
    t1 = float(max(e.offset + e.quarter_length for e in events))

    # --- ベロシティ（colorbar はサブプロット右端に内付け） ---
    sc = ax_vel.scatter(
        offsets, vels, c=midis, cmap="cool", s=14, alpha=0.75,
        edgecolors=dt.BORDER_STRONG, linewidths=0.25,
    )
    ax_vel.axhline(
        report.mean_velocity, color=dt.ACCENT, linestyle="--", linewidth=1.2, alpha=0.9,
    )
    ax_vel.set_ylim(0, 128)
    ax_vel.margins(x=0.02, y=0.04)
    _style_axis(ax_vel, title="ベロシティ推移", xlabel="拍（曲頭から）", ylabel="ベロシティ")
    divider = make_axes_locatable(ax_vel)
    cax = divider.append_axes("right", size="4.5%", pad=0.12)
    cbar = fig.colorbar(sc, cax=cax)
    cbar.set_label("音高 (MIDI)", fontsize=8, labelpad=6)
    cbar.ax.tick_params(labelsize=8)
    cbar.ax.yaxis.label.set_fontfamily(plot_font_family())

    # --- ピッチクラス ---
    pcs = midis % 12
    names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    counts = np.bincount(pcs, minlength=12)
    colors = [dt.ACCENT if i in {0, 4, 7} else dt.HARMONY for i in range(12)]
    ax_pc.bar(names, counts, color=colors, edgecolor=dt.BORDER_DEFAULT, linewidth=0.5)
    _style_axis(ax_pc, title="ピッチクラス分布", ylabel="ノート数")
    ax_pc.tick_params(axis="x", rotation=45, labelsize=8, pad=2)
    ax_pc.margins(x=0.02)

    # --- 密度 ---
    duration = max(t1 - t0, 1.0)
    n_bins = max(int(np.ceil(duration)) + 1, 4)
    density, edges = np.histogram(offsets, bins=n_bins, range=(t0, t1 + 1e-6))
    centers = (edges[:-1] + edges[1:]) / 2
    bar_w = max((edges[1] - edges[0]) * 0.85, 0.1) if len(edges) > 1 else 0.85
    ax_den.bar(
        centers, density, width=bar_w, color=dt.PLAY, alpha=0.85, edgecolor=dt.BORDER_DEFAULT,
    )
    _style_axis(
        ax_den,
        title="拍あたりノート密度",
        xlabel="拍（曲頭から）",
        ylabel="ノート数",
    )
    ax_den.margins(x=0.02, y=0.06)

    # --- レジスター（凡例は円グラフ下・axes 内） ---
    reg_labels = ["低音 (<C3)", "中音 (C3–B4)", "高音 (≥C5)"]
    reg_vals = [report.low_register_pct, report.mid_register_pct, report.high_register_pct]
    reg_colors = ["#6366f1", dt.ACCENT, "#f59e0b"]
    pie_font = plot_font_family()
    wedges, _, autotexts = ax_reg.pie(
        reg_vals,
        labels=None,
        colors=reg_colors,
        autopct="%1.0f%%",
        startangle=90,
        pctdistance=0.68,
        radius=0.82,
        textprops={"color": dt.TEXT_PRIMARY, "fontsize": 9, "fontfamily": pie_font},
    )
    for t in autotexts:
        t.set_color(dt.BG_DEEP)
        t.set_fontweight("bold")
    ax_reg.set_title("レジスター分布", pad=14, fontsize=11)
    ax_reg.legend(
        wedges,
        reg_labels,
        loc="lower center",
        bbox_to_anchor=(0.5, 0.02),
        ncol=3,
        fontsize=8,
        frameon=False,
        borderaxespad=0.0,
    )
    ax_reg.set_aspect("equal", adjustable="box")

    fig.suptitle(
        "パフォーマンス分析",
        color=dt.TEXT_PRIMARY,
        fontsize=13,
        fontweight="bold",
        fontfamily=plot_font_family(),
    )
    if hasattr(fig, "get_layout_engine") and fig.get_layout_engine() is not None:
        try:
            fig.get_layout_engine().set(rect=(0.0, 0.0, 1.0, 0.97))
        except Exception:
            pass

    theme_matplotlib_figure(fig)
    return fig
