# -*- coding: utf-8 -*-
"""Circular / Radial — 正円・全音域マッピング・ソフトグロー。"""
from __future__ import annotations

import math

from midi_lab.visualizer.styles_builders.context import (
    RenderContext,
    add_quad4,
    add_radial_segment,
    add_soft_disc,
    channel_rgba,
    midi_to_theta,
    polar_xy,
)


def _draw_concentric_rings(ctx: RenderContext, r_hub: float, r_max: float) -> None:
    rings = 8
    asp = ctx.aspect
    for i in range(1, rings + 1):
        r = r_hub + (r_max - r_hub) * (i / rings)
        alpha = 0.06 + 0.05 * (i / rings)
        col = (0.22, 0.38, 0.58, alpha)
        segs = 80
        for j in range(segs):
            a0 = (j / segs) * math.tau
            a1 = ((j + 1) / segs) * math.tau
            p0 = polar_xy(asp, a0, r)
            p1 = polar_xy(asp, a1, r)
            p2 = polar_xy(asp, a1, r + 0.003)
            p3 = polar_xy(asp, a0, r + 0.003)
            add_quad4(ctx.lines, p0, p1, p2, p3, col)


def build(ctx: RenderContext) -> None:
    ctx.use_glow = True
    ctx.use_additive = True
    asp = ctx.aspect
    r_hub = 0.08
    r_max = 0.92
    span_t = max(ctx.window_ql, 0.001)

    _draw_concentric_rings(ctx, r_hub, r_max)

    for n in ctx.timeline.notes:
        end = ctx.note_end(n.onset_ql, n.end_ql)
        if end < ctx.x0 or n.onset_ql > ctx.x1:
            continue
        vel = n.velocity / 127.0
        col = channel_rgba(n.channel, vel, ctx.track_colors)

        theta = midi_to_theta(n.midi, ctx.y_lo, ctx.y_hi)
        age_on = max(0.0, ctx.t_ql - n.onset_ql)
        age_end = max(0.0, ctx.t_ql - end)
        r_in = r_hub + (age_on / span_t) * (r_max - r_hub)
        r_out = r_hub + (age_end / span_t) * (r_max - r_hub)
        if ctx.is_sounding(n.onset_ql, end):
            r_out = max(r_out, r_in + 0.05 + 0.04 * vel)
        elif r_out <= r_in:
            r_out = r_in + 0.018

        half_w = 0.01 + 0.012 * vel
        add_radial_segment(ctx.notes, ctx.glow, asp, theta, r_in, r_out, half_w, col)

        cx, cy = polar_xy(asp, theta, (r_in + r_out) * 0.5)
        disc_r = half_w * 1.8 + 0.01 * vel
        add_soft_disc(ctx.notes, ctx.glow, asp, cx, cy, disc_r, col, layers=5)

        if ctx.is_sounding(n.onset_ql, end):
            ox, oy = polar_xy(asp, theta, r_out + 0.02)
            burst = (col[0], col[1], col[2], min(0.9, col[3] + 0.2))
            add_soft_disc(ctx.notes, ctx.glow, asp, ox, oy, disc_r * 1.4, burst, layers=4)

    for i in range(ctx.y_lo, ctx.y_hi + 1, max(1, (ctx.y_hi - ctx.y_lo) // 24 or 1)):
        ang = midi_to_theta(i, ctx.y_lo, ctx.y_hi)
        add_quad4(
            ctx.lines,
            polar_xy(asp, ang, r_hub),
            polar_xy(asp, ang + 0.006, r_hub),
            polar_xy(asp, ang + 0.006, r_max),
            polar_xy(asp, ang, r_max),
            (0.14, 0.22, 0.34, 0.22),
        )

    for i in range(64):
        a0 = (i / 64.0) * math.tau
        a1 = ((i + 1) / 64.0) * math.tau
        add_quad4(
            ctx.lines,
            polar_xy(asp, a0, r_hub),
            polar_xy(asp, a1, r_hub),
            polar_xy(asp, a1, r_hub + 0.01),
            polar_xy(asp, a0, r_hub + 0.01),
            (0.38, 0.62, 1.0, 0.4),
        )
