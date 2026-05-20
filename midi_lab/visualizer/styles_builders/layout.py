# -*- coding: utf-8 -*-
"""
NDC レイアウト — Qt OpenGL 座標系に合わせる。

- X: -1（左）〜 +1（右）= ウィジェット全幅
- Y: -1（下）〜 +1（上）= 鍵盤は下端、ノートは上から落下
"""
from __future__ import annotations

from midi_lab.visualizer.styles_builders.context import RenderContext


def kb_bottom_ndc(kb_ratio: float = 0.14) -> float:
    return -1.0


def kb_top_ndc(kb_ratio: float = 0.14) -> float:
    return -1.0 + kb_ratio * 2.0


def play_line_ndc(ctx: RenderContext) -> float:
    """判定ライン — 鍵盤の上端。"""
    return kb_top_ndc(ctx.kb_ratio)


def lane_top_ndc(ctx: RenderContext) -> float:
    """ノート落下レーンの上端。"""
    return 1.0 - 0.05


def fall_span_ndc(ctx: RenderContext) -> float:
    return lane_top_ndc(ctx) - play_line_ndc(ctx)


def y_at_beat(ctx: RenderContext, beat: float) -> float:
    """拍位置 → NDC Y。過去の拍ほど下（プレイラインを通過済み）。"""
    play = play_line_ndc(ctx)
    span = max(fall_span_ndc(ctx), 0.2)
    return play - (ctx.t_ql - beat) / max(ctx.window_ql, 0.001) * span


def ndc_to_pixel_y(ndc_y: float, height: int) -> float:
    """NDC Y → ピクセル Y（Qt: 上が 0）。"""
    return (1.0 - (ndc_y + 1.0) / 2.0) * height


def ndc_to_pixel_x(ndc_x: float, width: int) -> float:
    return (ndc_x + 1.0) * 0.5 * width


def midi_to_lane_y(midi: int, y_lo: int, y_hi: int, *, margin: float = 0.08) -> float:
    """Cyber 等 — 低音は下（鍵盤付近）、高音は上。"""
    span = max(y_hi - y_lo, 1)
    t = (midi - y_lo) / span
    bot = kb_top_ndc(0.14) + margin
    top = lane_top_ndc_from_ratio(0.14) - margin
    return bot + t * (top - bot)


def play_line_ndc_from_ratio(kb_ratio: float) -> float:
    return kb_top_ndc(kb_ratio)


def lane_top_ndc_from_ratio(kb_ratio: float) -> float:
    return 1.0 - 0.05
