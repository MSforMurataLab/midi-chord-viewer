# -*- coding: utf-8 -*-
"""パフォーマンス分析 — ベロシティ・音域・密度の統計と可視化。"""
from __future__ import annotations

from dataclasses import dataclass

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

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


def build_performance_dashboard_figure(
    events: list[NoteEvent],
    report: PerformanceReport,
    figsize: tuple[float, float] = (13.0, 9.5),
) -> Figure:
    fig = plt.figure(figsize=figsize, facecolor=dt.MPL_BG)
    gs = fig.add_gridspec(
        2,
        2,
        hspace=0.52,
        wspace=0.40,
        left=0.08,
        right=0.96,
        top=0.90,
        bottom=0.09,
    )
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

    sc = ax_vel.scatter(
        offsets, vels, c=midis, cmap="cool", s=18, alpha=0.75,
        edgecolors=dt.BORDER_STRONG, linewidths=0.3,
    )
    ax_vel.axhline(report.mean_velocity, color=dt.ACCENT, linestyle="--", linewidth=1.2, alpha=0.9)
    ax_vel.set_title("ベロシティ推移", pad=12)
    ax_vel.set_xlabel("拍（曲頭から）", labelpad=6)
    ax_vel.set_ylabel("ベロシティ (1–127)", labelpad=6)
    ax_vel.set_ylim(0, 128)
    cbar = fig.colorbar(sc, ax=ax_vel, label="音高 (MIDI)", pad=0.06, fraction=0.05)
    cbar.ax.yaxis.label.set_fontfamily(plot_font_family())

    pcs = midis % 12
    names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    counts = np.bincount(pcs, minlength=12)
    colors = [dt.ACCENT if i in {0, 4, 7} else dt.HARMONY for i in range(12)]
    ax_pc.bar(names, counts, color=colors, edgecolor=dt.BORDER_DEFAULT, linewidth=0.5)
    ax_pc.set_title("ピッチクラス分布", pad=12)
    ax_pc.set_ylabel("ノート数", labelpad=6)
    ax_pc.tick_params(axis="x", rotation=45)

    duration = max(t1 - t0, 1.0)
    n_bins = max(int(np.ceil(duration)) + 1, 4)
    density, edges = np.histogram(offsets, bins=n_bins, range=(t0, t1 + 1e-6))
    centers = (edges[:-1] + edges[1:]) / 2
    bar_w = max((edges[1] - edges[0]) * 0.85, 0.1) if len(edges) > 1 else 0.85
    ax_den.bar(centers, density, width=bar_w, color=dt.PLAY, alpha=0.85, edgecolor=dt.BORDER_DEFAULT)
    ax_den.set_title("拍あたりノート密度", pad=12)
    ax_den.set_xlabel("拍（曲頭から）", labelpad=6)
    ax_den.set_ylabel("ノート数", labelpad=6)

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
        pctdistance=0.72,
        textprops={"color": dt.TEXT_PRIMARY, "fontsize": 9, "fontfamily": pie_font},
    )
    ax_reg.legend(
        wedges,
        reg_labels,
        loc="center left",
        bbox_to_anchor=(1.02, 0.5),
        fontsize=9,
        frameon=False,
    )
    for t in autotexts:
        t.set_color(dt.BG_DEEP)
        t.set_fontweight("bold")
    ax_reg.set_title("レジスター分布", pad=12)

    fig.suptitle(
        "パフォーマンス分析",
        color=dt.TEXT_PRIMARY,
        fontsize=13,
        fontweight="bold",
        y=0.97,
        fontfamily=plot_font_family(),
    )
    theme_matplotlib_figure(fig)
    return fig
