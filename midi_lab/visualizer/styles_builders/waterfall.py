# -*- coding: utf-8 -*-
"""Classic Waterfall — 鍵盤下端・上から落下・全幅マッピング。"""
from __future__ import annotations

from midi_lab.visualizer.styles_builders.context import (
    RenderContext,
    add_quad,
    add_smooth_gradient_bar,
    channel_rgba,
    ease_out_cubic,
)
from midi_lab.visualizer.styles_builders.keyboard import (
    build_key_map,
    draw_keyboard,
    hit_line_ndc,
    key_geom_for_midi,
)
from midi_lab.visualizer.styles_builders.layout import (
    fall_span_ndc,
    lane_top_ndc,
    play_line_ndc,
    y_at_beat,
)


def build(ctx: RenderContext) -> None:
    ctx.use_additive = True
    keys = build_key_map(ctx.y_lo, ctx.y_hi)
    draw_keyboard(ctx, keys)
    play_y = play_line_ndc(ctx)
    top_y = lane_top_ndc(ctx)
    _ = fall_span_ndc(ctx)

    for n in ctx.timeline.notes:
        end = ctx.note_end(n.onset_ql, n.end_ql)
        if end < ctx.x0 or n.onset_ql > ctx.x1:
            continue
        vel = n.velocity / 127.0
        col = channel_rgba(n.channel, vel, ctx.track_colors)
        kg = key_geom_for_midi(keys, n.midi, ctx.y_lo, ctx.y_hi)
        xl, xr = kg.x_left, kg.x_right

        y_on = y_at_beat(ctx, n.onset_ql)
        y_off = y_at_beat(ctx, end)

        if not ctx.is_sounding(n.onset_ql, end):
            fade = ease_out_cubic(min(1.0, max(0.0, (ctx.t_ql - end) / 0.25)))
            col = (col[0], col[1], col[2], col[3] * (1.0 - fade * 0.85))

        y_lo_n = max(min(y_on, y_off), play_y - 0.01)
        y_hi_n = min(max(y_on, y_off), top_y)
        if y_hi_n - y_lo_n < 0.004 or col[3] < 0.04:
            continue

        add_smooth_gradient_bar(
            ctx.notes,
            ctx.glow,
            xl,
            xr,
            y_lo_n,
            y_hi_n,
            col,
            tip_at_high_y=False,
        )

    py = play_y
    add_quad(ctx.lines, -1.0, 1.0, py - 0.005, py + 0.005, (0.45, 0.72, 1.0, 0.65))
