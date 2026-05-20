# -*- coding: utf-8 -*-
"""リアルタイム・スペクトラム — 下から上へ跳ね上がり・ピークホールド。"""
from __future__ import annotations

from dataclasses import dataclass

from midi_lab.visualizer.styles_builders.context import (
    RenderContext,
    add_quad,
    add_smooth_gradient_bar,
    channel_rgba,
    ease_out_cubic,
)
from midi_lab.visualizer.styles_builders.keyboard import build_key_map, draw_keyboard, key_geom_for_midi
from midi_lab.visualizer.styles_builders.layout import fall_span_ndc, play_line_ndc


@dataclass
class _BarAnim:
    height: float = 0.0
    velocity: float = 0.0
    peak: float = 0.0
    peak_fall: float = 0.0


class SpectrumAnimator:
    def __init__(self) -> None:
        self._bars: dict[int, _BarAnim] = {}

    def clear(self) -> None:
        self._bars.clear()

    def tick(self, ctx: RenderContext) -> None:
        active: dict[int, float] = {}
        for n in ctx.timeline.notes:
            if ctx.is_sounding(n.onset_ql, n.end_ql):
                v = n.velocity / 127.0
                active[n.midi] = max(active.get(n.midi, 0.0), v)

        dt = ctx.dt
        for midi in range(ctx.y_lo, ctx.y_hi + 1):
            bar = self._bars.setdefault(midi, _BarAnim())
            target = active.get(midi, 0.0)
            bar.velocity = max(bar.velocity * 0.88, target)

            if bar.height < target:
                bar.height += (target - bar.height) * min(1.0, 14.0 * dt)
            else:
                gap = bar.height - target
                step = ease_out_cubic(min(1.0, 5.5 * dt)) * gap
                bar.height = max(target, bar.height - step)

            if bar.height > bar.peak:
                bar.peak = bar.height
                bar.peak_fall = 0.0
            elif bar.peak > bar.height:
                bar.peak_fall += dt
                fall_amt = ease_out_cubic(min(1.0, 2.2 * dt)) * 0.14
                bar.peak = max(bar.height, bar.peak - fall_amt)

            if target <= 0 and bar.height < 0.008:
                bar.height = 0.0
            if bar.peak < 0.01:
                bar.peak = 0.0

    def build(self, ctx: RenderContext) -> None:
        ctx.use_additive = True
        self.tick(ctx)
        keys = build_key_map(ctx.y_lo, ctx.y_hi)
        draw_keyboard(ctx, keys)

        floor_y = play_line_ndc(ctx)
        max_h = fall_span_ndc(ctx)

        for midi in range(ctx.y_lo, ctx.y_hi + 1):
            bar = self._bars.get(midi)
            if bar is None or (bar.height < 0.02 and bar.peak < 0.02):
                continue
            kg = key_geom_for_midi(keys, midi, ctx.y_lo, ctx.y_hi)
            h = bar.height * max_h
            vel = bar.velocity
            col = channel_rgba(0, vel, ctx.track_colors)

            y_bot = floor_y
            y_top = floor_y + h
            add_smooth_gradient_bar(
                ctx.notes,
                ctx.glow,
                kg.x_left,
                kg.x_right,
                y_bot,
                y_top,
                col,
                tip_at_high_y=True,
            )

            if bar.peak > bar.height + 0.02:
                pk_y = floor_y + bar.peak * max_h
                dot_h = max(0.008, max_h * 0.018)
                cx = (kg.x_left + kg.x_right) * 0.5
                hw = (kg.x_right - kg.x_left) * 0.22
                peak_col = (col[0], col[1], col[2], min(0.9, col[3] + 0.15))
                add_quad(
                    ctx.notes,
                    cx - hw,
                    cx + hw,
                    pk_y - dot_h,
                    pk_y + dot_h * 0.3,
                    peak_col,
                )
