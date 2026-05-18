# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import sys

import matplotlib as mpl
from matplotlib import font_manager as fm

from midi_lab.ui import design_tokens as dt

_PLOT_FONT: str | None = None

# matplotlib の fontManager に登録する Windows 標準フォント（優先順）
_WIN_FONT_FILES: tuple[tuple[str, str], ...] = (
    ("YuGothM.ttc", "Yu Gothic"),
    ("YuGothR.ttc", "Yu Gothic"),
    ("meiryo.ttc", "Meiryo"),
    ("msgothic.ttc", "MS Gothic"),
    ("YuGothL.ttc", "Yu Gothic"),
)

# 既にシステムに登録済みの場合に名前で探す候補
_CJK_FONT_NAMES: tuple[str, ...] = (
    "Yu Gothic",
    "Yu Gothic UI",
    "Meiryo",
    "Meiryo UI",
    "MS Gothic",
    "MS PGothic",
    "BIZ UDGothic",
    "Noto Sans JP",
    "Noto Sans CJK JP",
    "Hiragino Sans",
    "IPAPGothic",
    "TakaoGothic",
    "Malgun Gothic",
)


def _register_font_file(path: str) -> str | None:
    """フォントファイルを matplotlib に登録し、ファミリー名を返す。"""
    if not os.path.isfile(path):
        return None
    try:
        fm.fontManager.addfont(path)
        return fm.FontProperties(fname=path).get_name()
    except Exception:
        return None


def _resolve_cjk_font() -> str | None:
    """日本語表示用フォントを解決（Windows は Fonts フォルダから明示登録）。"""
    if sys.platform == "win32":
        font_dir = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")
        for filename, _hint in _WIN_FONT_FILES:
            family = _register_font_file(os.path.join(font_dir, filename))
            if family:
                return family

    known = {f.name for f in fm.fontManager.ttflist}
    for name in _CJK_FONT_NAMES:
        if name in known:
            return name

    for f in fm.fontManager.ttflist:
        n = f.name
        if any(k in n for k in ("Gothic", "Meiryo", "Noto Sans JP", "Noto Sans CJK")):
            return n
    return None


def plot_font_family() -> str:
    """グラフ用フォント名（キャッシュ）。"""
    global _PLOT_FONT
    if _PLOT_FONT is None:
        _PLOT_FONT = _resolve_cjk_font() or "DejaVu Sans"
    return _PLOT_FONT


def configure_matplotlib() -> None:
    family = plot_font_family()
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
            "font.family": family,
            "axes.unicode_minus": False,
        }
    )


def _apply_font_to_text(text_obj) -> None:
    if text_obj is None:
        return
    try:
        text_obj.set_fontfamily(plot_font_family())
    except Exception:
        pass


def theme_matplotlib_figure(fig) -> None:
    family = plot_font_family()
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
        _apply_font_to_text(ax.xaxis.label)
        _apply_font_to_text(ax.yaxis.label)
        title = ax.title
        if title.get_text():
            title.set_color(dt.TEXT_PRIMARY)
            title.set_fontweight("bold")
            title.set_fontsize(11)
            _apply_font_to_text(title)
        for lbl in ax.get_xticklabels() + ax.get_yticklabels():
            _apply_font_to_text(lbl)
        leg = ax.get_legend()
        if leg is not None:
            for t in leg.get_texts():
                _apply_font_to_text(t)
    sup = getattr(fig, "_suptitle", None)
    if sup is not None:
        _apply_font_to_text(sup)
    for child in fig.texts:
        _apply_font_to_text(child)
