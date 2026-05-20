# -*- coding: utf-8 -*-
"""Cyber Laser — レーザー・サイン波・音域マッピング。"""
from __future__ import annotations

from midi_lab.visualizer.styles_builders.context import (
    RenderContext,
    add_laser_beam,
    add_quad,
    add_wavy_playhead_spike,
    channel_rgba,
    midi_to_ndc_y,
    x_ndc,
)
from midi_lab.visualizer.styles_builders.keyboard import build_key_map, key_geom_for_midi


def _grid(ctx: RenderContext) -> None:
    col_h = (0.08, 0.35, 0.55, 0.28)
    col_v = (0.06, 0.28, 0.48, 0.22)
    for i in range(-10, 11):
        y = i / 10.0
        add_quad(ctx.lines, -1.0, 1.0, y - 0.001, y + 0.001, col_h)
    for i in range(-10, 11):
        x = i / 10.0
        add_quad(ctx.lines, x - 0.001, x + 0.001, -1.0, 1.0, col_v)


def build(ctx: RenderContext) -> None:
    ctx.use_glow = True
    ctx.use_additive = True
    ctx.cyber_grid = True
    _grid(ctx)
    play_x = x_ndc(ctx.t_ql, ctx.x0, ctx.x1)
    add_quad(ctx.lines, play_x - 0.002, play_x + 0.002, -1.0, 1.0, (0.2, 0.85, 1.0, 0.45))

    keys = build_key_map(ctx.y_lo, ctx.y_hi)

    for n in ctx.timeline.notes:
        end = ctx.note_end(n.onset_ql, n.end_ql)
        if end < ctx.x0 or n.onset_ql > ctx.x1:
            continue
        vel = n.velocity / 127.0
        col = channel_rgba(n.channel, vel, ctx.track_colors)

        kg = key_geom_for_midi(keys, n.midi, ctx.y_lo, ctx.y_hi)
        y = midi_to_ndc_y(n.midi, ctx.y_lo, ctx.y_hi, margin=0.1)
        xs = x_ndc(n.onset_ql, ctx.x0, ctx.x1)
        xe = play_x
        th = 0.0025 + 0.004 * vel
        add_laser_beam(ctx.notes, ctx.glow, xs, xe, y, col, thickness=th, segments=14)

        sounding = ctx.is_sounding(n.onset_ql, end)
        if sounding:
            head_col = (min(1.0, col[0] * 1.4), min(1.0, col[1] * 1.4), min(1.0, col[2] * 1.5), 0.75)
            add_quad(ctx.glow, xe - 0.02, xe + 0.02, y - 0.025, y + 0.025, head_col)
            add_quad(ctx.notes, xe - 0.008, xe + 0.008, y - 0.012, y + 0.012, head_col)
            add_wavy_playhead_spike(
                ctx.notes,
                ctx.glow,
                xe,
                y,
                col,
                vel=vel,
                t_ql=ctx.t_ql,
                midi=n.midi,
            )
            add_wavy_playhead_spike(
                ctx.notes,
                ctx.glow,
                kg.x_center,
                y,
                col,
                vel=vel * 0.85,
                t_ql=ctx.t_ql + 0.3,
                midi=n.midi + 1,
            )
