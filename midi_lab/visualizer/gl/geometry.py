# -*- coding: utf-8 -*-
"""タイムライン → GPU 頂点（スタイル別ビルダーへ委譲）。"""
from __future__ import annotations

import numpy as np

from midi_lab.visualizer.styles_builders import build_scene
from midi_lab.visualizer.styles_builders.context import VERT_DTYPE
from midi_lab.visualizer.timeline import MidiTimeline

__all__ = ["VERT_DTYPE", "build_geometry", "build_scene_meshes"]


def build_scene_meshes(
    timeline: MidiTimeline,
    *,
    t_ql: float,
    window_ql: float,
    style_id: str,
    track_colors: bool,
    sustain_extend: float,
    dt: float = 1.0 / 60.0,
    viewport_w: int = 1280,
    viewport_h: int = 720,
):
    return build_scene(
        timeline,
        style_id=style_id,
        t_ql=t_ql,
        window_ql=window_ql,
        track_colors=track_colors,
        sustain_extend=sustain_extend,
        dt=dt,
        viewport_w=viewport_w,
        viewport_h=viewport_h,
    )


def build_geometry(
    timeline: MidiTimeline,
    *,
    t_ql: float,
    window_ql: float,
    style_id: str,
    track_colors: bool,
    sustain_extend: float,
    dt: float = 1.0 / 60.0,
    viewport_w: int = 1280,
    viewport_h: int = 720,
) -> np.ndarray:
    """後方互換: ノート+ライン+鍵盤を単一配列に結合。"""
    scene = build_scene_meshes(
        timeline,
        t_ql=t_ql,
        window_ql=window_ql,
        style_id=style_id,
        track_colors=track_colors,
        sustain_extend=sustain_extend,
        dt=dt,
        viewport_w=viewport_w,
        viewport_h=viewport_h,
    )
    parts = [scene.notes, scene.glow, scene.lines, scene.keyboard]
    parts = [p for p in parts if p.size]
    if not parts:
        return np.zeros(0, dtype=VERT_DTYPE)
    return np.concatenate(parts)
