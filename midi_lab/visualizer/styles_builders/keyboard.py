# -*- coding: utf-8 -*-
"""ピアノ鍵盤レイアウト — 画面下端・全幅マッピング。"""
from __future__ import annotations

from dataclasses import dataclass

from midi_lab.visualizer.styles_builders.context import RenderContext, add_quad
from midi_lab.visualizer.styles_builders.layout import (
    kb_bottom_ndc,
    kb_top_ndc,
    ndc_to_pixel_x,
    ndc_to_pixel_y,
    play_line_ndc,
)

_BLACK = {1, 3, 6, 8, 10}


@dataclass(frozen=True)
class KeyGeom:
    midi: int
    x_left: float
    x_right: float
    x_center: float
    is_black: bool


def build_key_map(y_lo: int, y_hi: int) -> dict[int, KeyGeom]:
    whites = [m for m in range(y_lo, y_hi + 1) if m % 12 not in _BLACK]
    if not whites:
        whites = list(range(y_lo, y_hi + 1))
    n = len(whites)
    mapping: dict[int, KeyGeom] = {}
    for i, w in enumerate(whites):
        xl = -1.0 + (i / n) * 2.0
        xr = -1.0 + ((i + 1) / n) * 2.0
        xc = (xl + xr) * 0.5
        mapping[w] = KeyGeom(w, xl, xr, xc, False)
    for m in range(y_lo, y_hi + 1):
        if m % 12 not in _BLACK:
            continue
        below = max((w for w in whites if w < m), default=whites[0])
        above = min((w for w in whites if w > m), default=whites[-1])
        wl = mapping[below]
        wr = mapping[above]
        xc = (wl.x_center + wr.x_center) * 0.5
        half = min(0.018, (wr.x_left - wl.x_right) * 0.22)
        mapping[m] = KeyGeom(m, xc - half, xc + half, xc, True)
    return mapping


def key_geom_for_midi(keys: dict[int, KeyGeom], midi: int, y_lo: int, y_hi: int) -> KeyGeom:
    if midi in keys:
        return keys[midi]
    span = max(y_hi - y_lo, 1)
    t = (midi - y_lo) / span
    xc = -1.0 + t * 2.0
    hw = 0.012
    return KeyGeom(midi, xc - hw, xc + hw, xc, midi % 12 in _BLACK)


def draw_keyboard(ctx: RenderContext, keys: dict[int, KeyGeom]) -> None:
    y_bot = kb_bottom_ndc(ctx.kb_ratio)
    y_top = kb_top_ndc(ctx.kb_ratio)
    white_h = y_top - y_bot
    for m in range(ctx.y_lo, ctx.y_hi + 1):
        if m % 12 in _BLACK:
            continue
        kg = keys[m]
        active = any(
            ctx.is_sounding(n.onset_ql, n.end_ql) and n.midi == m for n in ctx.timeline.notes
        )
        col = (0.36, 0.61, 0.96, 0.95) if active else (0.91, 0.91, 0.94, 1.0)
        add_quad(ctx.keyboard, kg.x_left, kg.x_right, y_bot, y_top, col)
    for m in range(ctx.y_lo, ctx.y_hi + 1):
        if m % 12 not in _BLACK:
            continue
        kg = keys[m]
        active = any(
            ctx.is_sounding(n.onset_ql, n.end_ql) and n.midi == m for n in ctx.timeline.notes
        )
        col = (0.55, 0.75, 1.0, 0.95) if active else (0.22, 0.22, 0.26, 1.0)
        bh = white_h * 0.62
        add_quad(ctx.keyboard, kg.x_left, kg.x_right, y_top - bh, y_top, col)


def hit_line_ndc(ctx: RenderContext) -> float:
    return play_line_ndc(ctx)


def key_center_pixels(
    midi: int,
    y_lo: int,
    y_hi: int,
    width: int,
    height: int,
    kb_ratio: float = 0.14,
) -> tuple[float, float]:
    keys = build_key_map(y_lo, y_hi)
    kg = key_geom_for_midi(keys, midi, y_lo, y_hi)
    px = ndc_to_pixel_x(kg.x_center, width)
    py = ndc_to_pixel_y(play_line_ndc_from_ctx_kr(kb_ratio), height)
    return px, py


def play_line_ndc_from_ctx_kr(kb_ratio: float) -> float:
    return kb_top_ndc(kb_ratio)


def circular_center_pixels(width: int, height: int) -> tuple[float, float]:
    return width * 0.5, height * 0.5
