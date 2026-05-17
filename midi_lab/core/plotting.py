# -*- coding: utf-8 -*-
from __future__ import annotations

import matplotlib as mpl

from midi_lab.ui import design_tokens as dt


def configure_matplotlib() -> None:
    mpl.rcParams.update(
        {
            "figure.facecolor": dt.MPL_BG,
            "axes.facecolor": dt.MPL_PANEL,
            "axes.edgecolor": dt.MPL_GRID,
            "axes.labelcolor": dt.MPL_LABEL,
            "text.color": dt.TEXT_PRIMARY,
            "xtick.color": dt.MPL_TICK,
            "ytick.color": dt.MPL_TICK,
            "grid.color": dt.MPL_GRID,
            "grid.alpha": 0.45,
            "font.size": 10,
            "font.family": "sans-serif",
        }
    )


def theme_matplotlib_figure(fig) -> None:
    fig.patch.set_facecolor(dt.MPL_BG)
    for ax in fig.get_axes():
        ax.set_facecolor(dt.MPL_PANEL)
        ax.tick_params(colors=dt.MPL_TICK, labelsize=9)
        ax.grid(True, color=dt.MPL_GRID, alpha=0.45, linestyle="-", linewidth=0.5)
        for spine in ax.spines.values():
            spine.set_color(dt.MPL_GRID)
            spine.set_linewidth(0.8)
        ax.xaxis.label.set_color(dt.MPL_LABEL)
        ax.yaxis.label.set_color(dt.MPL_LABEL)
        title = ax.title
        if title.get_text():
            title.set_color(dt.TEXT_PRIMARY)
            title.set_fontweight("bold")
            title.set_fontsize(11)
