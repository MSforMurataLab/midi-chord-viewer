# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from midi_lab.visualizer.styles_builders.circular import build as build_circular
from midi_lab.visualizer.styles_builders.context import (
    VERT_DTYPE,
    make_render_context,
    verts_to_array,
)
from midi_lab.visualizer.styles_builders.cyber import build as build_cyber
from midi_lab.visualizer.styles_builders.waterfall import build as build_waterfall
from midi_lab.visualizer.timeline import MidiTimeline

_spectrum_animator = None


def _get_spectrum():
    global _spectrum_animator
    if _spectrum_animator is None:
        from midi_lab.visualizer.styles_builders.spectrum import SpectrumAnimator

        _spectrum_animator = SpectrumAnimator()
    return _spectrum_animator


def clear_spectrum_state() -> None:
    global _spectrum_animator
    if _spectrum_animator is not None:
        _spectrum_animator.clear()


@dataclass
class SceneMeshes:
    notes: np.ndarray
    glow: np.ndarray
    lines: np.ndarray
    keyboard: np.ndarray
    use_glow: bool = False
    use_additive: bool = False
    cyber_grid: bool = False


def build_scene(
    timeline: MidiTimeline,
    *,
    style_id: str,
    t_ql: float,
    window_ql: float,
    track_colors: bool,
    sustain_extend: float,
    dt: float = 1.0 / 60.0,
    viewport_w: int = 1280,
    viewport_h: int = 720,
) -> SceneMeshes:
    ctx = make_render_context(
        timeline,
        t_ql=t_ql,
        window_ql=window_ql,
        track_colors=track_colors,
        sustain_extend=sustain_extend,
        dt=dt,
        viewport_w=viewport_w,
        viewport_h=viewport_h,
    )
    if style_id == "waterfall":
        build_waterfall(ctx)
    elif style_id == "circular":
        build_circular(ctx)
    elif style_id == "spectrum":
        _get_spectrum().build(ctx)
    elif style_id == "cyber":
        build_cyber(ctx)
    else:
        build_waterfall(ctx)

    return SceneMeshes(
        notes=verts_to_array(ctx.notes),
        glow=verts_to_array(ctx.glow),
        lines=verts_to_array(ctx.lines),
        keyboard=verts_to_array(ctx.keyboard),
        use_glow=ctx.use_glow,
        use_additive=ctx.use_additive,
        cyber_grid=ctx.cyber_grid,
    )
