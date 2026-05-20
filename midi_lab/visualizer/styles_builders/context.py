# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass, field

import math
import numpy as np

from midi_lab.visualizer.timeline import MidiTimeline

VERT_DTYPE = np.dtype([("x", "f4"), ("y", "f4"), ("r", "f4"), ("g", "f4"), ("b", "f4"), ("a", "f4")])
LINE_DTYPE = VERT_DTYPE


def ease_out_cubic(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return 1.0 - (1.0 - t) ** 3


def ease_out_quad(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return 1.0 - (1.0 - t) ** 2


@dataclass
class RenderContext:
    timeline: MidiTimeline
    t_ql: float
    window_ql: float
    x0: float
    x1: float
    y_lo: int
    y_hi: int
    kb_ratio: float = 0.14
    track_colors: bool = True
    sustain_extend: float = 0.0
    dt: float = 1.0 / 60.0
    aspect: float = 16.0 / 9.0

    notes: list = field(default_factory=list)
    glow: list = field(default_factory=list)
    lines: list = field(default_factory=list)
    keyboard: list = field(default_factory=list)
    use_glow: bool = False
    use_additive: bool = False
    cyber_grid: bool = False

    def note_end(self, onset: float, end: float) -> float:
        if self.sustain_extend > 0 and onset <= self.t_ql < end + 0.05:
            return max(end, self.t_ql + self.sustain_extend)
        return end

    def is_sounding(self, onset: float, end: float) -> bool:
        return onset <= self.t_ql < self.note_end(onset, end)


def channel_rgba(channel: int, vel: float, track_colors: bool) -> tuple[float, float, float, float]:
    if not track_colors:
        return (0.36, 0.61, 0.96, 0.55 + 0.2 * vel)
    h = (channel * 0.618033988749895) % 1.0
    r = max(0.0, abs(h * 6.0 - 3.0) - 1.0)
    g = max(0.0, 2.0 - abs(h * 6.0 - 2.0))
    b = max(0.0, 2.0 - abs(h * 6.0 - 4.0))
    s = 0.4 + 0.6 * vel
    a = 0.58 + 0.18 * vel
    return (r * s, g * s, b * s, min(0.82, a))


def verts_to_array(items: list) -> np.ndarray:
    if not items:
        return np.zeros(0, dtype=VERT_DTYPE)
    return np.array(items, dtype=VERT_DTYPE)


def add_quad(
    out: list,
    x0: float,
    x1: float,
    y0: float,
    y1: float,
    color: tuple[float, float, float, float],
) -> None:
    r, g, b, a = color
    out.extend(
        [
            (x0, y0, r, g, b, a),
            (x1, y0, r, g, b, a),
            (x1, y1, r, g, b, a),
            (x0, y0, r, g, b, a),
            (x1, y1, r, g, b, a),
            (x0, y1, r, g, b, a),
        ]
    )


def add_pseudo_glow(
    glow_out: list,
    x0: float,
    x1: float,
    y0: float,
    y1: float,
    color: tuple[float, float, float, float],
    *,
    scale: float = 1.5,
    alpha_scale: float = 0.3,
) -> None:
    cx = (x0 + x1) * 0.5
    cy = (y0 + y1) * 0.5
    hw = abs(x1 - x0) * 0.5 * scale
    hh = abs(y1 - y0) * 0.5 * scale
    if hw < 0.0008 and hh < 0.0008:
        hw = hh = 0.012 * scale
    gr, gg, gb, ga = color
    add_quad(glow_out, cx - hw, cx + hw, cy - hh, cy + hh, (gr, gg, gb, ga * alpha_scale))


def add_quad_with_glow(
    out: list,
    glow_out: list,
    x0: float,
    x1: float,
    y0: float,
    y1: float,
    color: tuple[float, float, float, float],
    *,
    glow: bool = True,
) -> None:
    if glow and glow_out is not None:
        add_pseudo_glow(glow_out, x0, x1, y0, y1, color)
    add_quad(out, x0, x1, y0, y1, color)


def add_quad4(
    out: list,
    p0: tuple[float, float],
    p1: tuple[float, float],
    p2: tuple[float, float],
    p3: tuple[float, float],
    color: tuple[float, float, float, float],
) -> None:
    r, g, b, a = color
    x0, y0 = p0
    x1, y1 = p1
    x2, y2 = p2
    x3, y3 = p3
    out.extend(
        [
            (x0, y0, r, g, b, a),
            (x1, y1, r, g, b, a),
            (x2, y2, r, g, b, a),
            (x0, y0, r, g, b, a),
            (x2, y2, r, g, b, a),
            (x3, y3, r, g, b, a),
        ]
    )


def add_quad4_with_glow(
    out: list,
    glow_out: list,
    p0: tuple[float, float],
    p1: tuple[float, float],
    p2: tuple[float, float],
    p3: tuple[float, float],
    color: tuple[float, float, float, float],
) -> None:
    xs = [p0[0], p1[0], p2[0], p3[0]]
    ys = [p0[1], p1[1], p2[1], p3[1]]
    add_pseudo_glow(glow_out, min(xs), max(xs), min(ys), max(ys), color)
    add_quad4(out, p0, p1, p2, p3, color)


def polar_xy(aspect: float, angle: float, radius: float) -> tuple[float, float]:
    """NDC 極座標 — ピクセル上で正円になるよう Y を aspect (width/height) で補正。"""
    return math.cos(angle) * radius, math.sin(angle) * radius * aspect


def midi_to_theta(midi: int, y_lo: int, y_hi: int) -> float:
    span = max(y_hi - y_lo, 1)
    t = (midi - y_lo) / span
    return t * math.tau - math.pi / 2


def midi_to_ndc_y(midi: int, y_lo: int, y_hi: int, *, margin: float = 0.06) -> float:
    from midi_lab.visualizer.styles_builders.layout import midi_to_lane_y

    return midi_to_lane_y(midi, y_lo, y_hi, margin=margin)


def add_radial_segment(
    out: list,
    glow_out: list | None,
    aspect: float,
    theta: float,
    r0: float,
    r1: float,
    half_width: float,
    color: tuple[float, float, float, float],
) -> None:
    i0x, i0y = polar_xy(aspect, theta, r0)
    i1x, i1y = polar_xy(aspect, theta, r1)
    px, py = -math.sin(theta) * half_width, math.cos(theta) * half_width * aspect
    p0 = (i0x - px, i0y - py)
    p1 = (i0x + px, i0y + py)
    p2 = (i1x + px, i1y + py)
    p3 = (i1x - px, i1y - py)
    if glow_out is not None:
        add_quad4_with_glow(out, glow_out, p0, p1, p2, p3, color)
    else:
        add_quad4(out, p0, p1, p2, p3, color)


def add_smooth_gradient_bar(
    out: list,
    glow_out: list | None,
    x0: float,
    x1: float,
    y0: float,
    y1: float,
    color: tuple[float, float, float, float],
    *,
    tip_at_high_y: bool = True,
    layers: int = 18,
) -> None:
    """先端発光・根本透明の多層グラデーション（テクスチャ代替）。"""
    x0, x1 = min(x0, x1), max(x0, x1)
    y0, y1 = min(y0, y1), max(y0, y1)
    if y1 - y0 < 0.001:
        return
    r, g, b, a = color
    if glow_out is not None:
        add_pseudo_glow(glow_out, x0, x1, y0, y1, color, scale=1.35, alpha_scale=0.25)
    for i in range(layers):
        t0 = i / layers
        t1 = (i + 1) / layers
        ya = y0 + (y1 - y0) * t0
        yb = y0 + (y1 - y0) * t1
        t_tip = t1 if tip_at_high_y else 1.0 - t1
        bright = 0.25 + 0.75 * (t_tip**0.65)
        alpha = a * (0.08 + 0.92 * (t_tip**1.4))
        layer = (
            min(1.0, r * bright + 0.18 * t_tip),
            min(1.0, g * bright + 0.18 * t_tip),
            min(1.0, b * bright + 0.22 * t_tip),
            min(0.85, alpha),
        )
        add_quad(out, x0, x1, ya, yb, layer)


def add_soft_disc(
    out: list,
    glow_out: list | None,
    aspect: float,
    cx: float,
    cy: float,
    radius: float,
    color: tuple[float, float, float, float],
    *,
    layers: int = 6,
) -> None:
    """ソフトパーティクル風の円形グロー（楕円補正済み）。"""
    r, g, b, base_a = color
    for i in range(layers, 0, -1):
        t = i / layers
        rad = radius * t
        a = base_a * (1.0 - t) ** 2 * 0.55
        if a < 0.02:
            continue
        layer = (r, g, b, a)
        add_quad(
            out,
            cx - rad,
            cx + rad,
            cy - rad * aspect,
            cy + rad * aspect,
            layer,
        )
    if glow_out is not None:
        add_pseudo_glow(glow_out, cx - radius, cx + radius, cy - radius * aspect, cy + radius * aspect, color)


def add_wavy_playhead_spike(
    out: list,
    glow_out: list,
    play_x: float,
    y: float,
    color: tuple[float, float, float, float],
    *,
    vel: float,
    t_ql: float,
    midi: int,
) -> None:
    """発音時 — プレイヘッド付近のサイン波振動。"""
    amp = 0.008 + 0.022 * vel
    length = 0.07 + 0.04 * vel
    steps = 20
    phase = t_ql * 24.0 + midi * 0.17
    r, g, b, a = color
    x_start = play_x - length * 0.5
    x_end = play_x + length * 0.5
    span = x_end - x_start
    for i in range(steps):
        t0 = i / steps
        t1 = (i + 1) / steps
        xa = x_start + span * t0
        xb = x_start + span * t1
        xm = (xa + xb) * 0.5
        ya = y + amp * math.sin(xm * 38.0 + phase)
        yb = y + amp * math.sin(xb * 38.0 + phase + 0.4)
        bright = 0.7 + 0.3 * vel
        seg = (r * bright, g * bright, b * bright, min(0.9, a + 0.2))
        th = 0.002 + 0.003 * vel
        add_quad(out, xa, xb, min(ya, yb) - th, max(ya, yb) + th, seg)
    add_quad(glow_out, play_x - 0.012, play_x + 0.012, y - 0.018, y + 0.018, (r, g, b, a * 0.45))


def add_gradient_quad(
    out: list,
    x0: float,
    x1: float,
    y0: float,
    y1: float,
    base: tuple[float, float, float, float],
    *,
    shine: float = 0.35,
    glow_out: list | None = None,
) -> None:
    r, g, b, a = base
    top = (min(1.0, r + shine), min(1.0, g + shine), min(1.0, b + shine), min(0.85, a + 0.12))
    bot = (r * 0.65, g * 0.65, b * 0.65, a * 0.75)
    x0, x1, y0, y1 = min(x0, x1), max(x0, x1), min(y0, y1), max(y0, y1)
    if glow_out is not None:
        add_pseudo_glow(glow_out, x0, x1, y0, y1, base)
    out.extend(
        [
            (x0, y0, *bot),
            (x1, y0, *bot),
            (x1, y1, *top),
            (x0, y0, *bot),
            (x1, y1, *top),
            (x0, y1, *top),
        ]
    )


def add_laser_beam(
    out: list,
    glow_out: list,
    x_tail: float,
    x_head: float,
    y: float,
    color: tuple[float, float, float, float],
    *,
    thickness: float = 0.004,
    segments: int = 10,
) -> None:
    x0, x1 = min(x_tail, x_head), max(x_tail, x_head)
    if x1 - x0 < 0.002:
        return
    r, g, b, _ = color
    span = x1 - x0
    for i in range(segments):
        ta = i / segments
        tb = (i + 1) / segments
        xa = x0 + span * ta
        xb = x0 + span * tb
        t_mid = (ta + tb) * 0.5
        alpha = 0.12 + 0.68 * t_mid
        bright = 0.55 + 0.45 * t_mid
        seg = (r * bright, g * bright, b * bright, min(0.8, alpha))
        th = thickness * (0.35 + 0.65 * t_mid)
        add_quad_with_glow(out, glow_out, xa, xb, y - th, y + th, seg, glow=True)


def x_ndc(ql: float, x0: float, x1: float) -> float:
    return (ql - x0) / max(x1 - x0, 0.001) * 2.0 - 1.0


def y_note_ndc(midi: int, y_lo: int, y_hi: int, kb_ratio: float) -> float:
    from midi_lab.visualizer.styles_builders.layout import midi_to_lane_y

    return midi_to_lane_y(midi, y_lo, y_hi)


def make_render_context(
    timeline: MidiTimeline,
    *,
    t_ql: float,
    window_ql: float,
    track_colors: bool,
    sustain_extend: float,
    dt: float = 1.0 / 60.0,
    viewport_w: int = 1280,
    viewport_h: int = 720,
) -> RenderContext:
    from midi_lab.visualizer.timeline import visible_beat_window

    x0, x1 = visible_beat_window(t_ql, window_ql, timeline.duration_ql)
    y_lo, y_hi = timeline.y_range()
    vw = max(1, int(viewport_w))
    vh = max(1, int(viewport_h))
    return RenderContext(
        timeline=timeline,
        t_ql=t_ql,
        window_ql=window_ql,
        x0=x0,
        x1=x1,
        y_lo=y_lo,
        y_hi=y_hi,
        track_colors=track_colors,
        sustain_extend=sustain_extend,
        dt=dt,
        aspect=float(vw) / float(vh),
    )
