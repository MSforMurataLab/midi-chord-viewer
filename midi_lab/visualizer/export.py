# -*- coding: utf-8 -*-
"""GPU オフライン書き出し — Rust/wgpu のみ。"""
from __future__ import annotations

from pathlib import Path
from typing import Callable

import numpy as np
from PyQt6.QtGui import QImage

from midi_lab.visualizer.engine import VisualizerEngine
from midi_lab.visualizer.rust_bridge import VisualizerEngine as RustEngine, rust_available
from midi_lab.visualizer.timeline import ql_to_sec

ProgressCallback = Callable[[int, int], None]


def _require_rust() -> None:
    if not rust_available():
        raise RuntimeError(
            "midi_viz が必要です。scripts/run_maturin.ps1 を実行して Rust ビジュアライザをビルドしてください。"
        )


def _timeline_arrays(timeline) -> tuple[list[float], list[float], list[int], list[int], list[int]]:
    notes = timeline.notes
    return (
        [float(n.onset_ql) for n in notes],
        [float(n.duration_ql) for n in notes],
        [int(n.midi) for n in notes],
        [int(n.velocity) for n in notes],
        [int(n.channel) for n in notes],
    )


def _make_rust_engine(py_eng: VisualizerEngine, width: int, height: int) -> RustEngine:
    rust = RustEngine(max(64, width), max(64, height))
    onsets, durations, midis, velocities, channels = _timeline_arrays(py_eng.timeline)
    rust.load_notes(onsets, durations, midis, velocities, channels)
    rust.set_style(py_eng.style_id)
    rust.set_track_colors(py_eng.track_colors)
    rust.set_particle_amount(py_eng.particle_amount)
    return rust


def export_video(
    engine: VisualizerEngine,
    path: str | Path,
    *,
    fps: int = 30,
    width: int = 1280,
    height: int = 720,
    progress: ProgressCallback | None = None,
) -> Path:
    _require_rust()
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    fps = max(12, min(60, int(fps)))
    w, h = max(64, int(width)), max(64, int(height))
    ext = out.suffix.lower()
    if ext not in (".mp4", ".mov", ".avi"):
        raise ValueError(f"未対応: {ext}")

    rust = _make_rust_engine(engine, w, h)
    try:
        n = int(
            rust.export_video_ffmpeg(str(out), fps, w, h)
        )
        if progress:
            progress(n, n)
        return out
    except (RuntimeError, AttributeError):
        pass

    import imageio.v2 as imageio

    try:
        import imageio_ffmpeg  # noqa: F401
    except ImportError as exc:
        raise RuntimeError(
            "動画書き出しには ffmpeg または imageio-ffmpeg が必要です。"
        ) from exc

    dur = ql_to_sec(engine.timeline.duration_ql, engine.bpm)
    n = max(1, int(dur * fps) + 1)
    kw: dict = {"fps": fps, "format": "FFMPEG"}
    kw.update(codec="libx264", quality=8, pixelformat="yuv420p")

    writer = imageio.get_writer(str(out), **kw)
    try:
        for i in range(n):
            t = min(dur, i / fps)
            t_ql = t * engine.bpm / 60.0
            rust.set_transport(t_ql, engine.bpm, engine.window_sec, engine.speed)
            rust.tick(1.0 / fps)
            rgba = rust.render_frame_rgba()
            rgb = np.frombuffer(rgba, dtype=np.uint8).reshape((h, w, 4))[:, :, :3]
            writer.append_data(np.flipud(rgb))
            if progress:
                progress(i + 1, n)
    finally:
        writer.close()
    return out


def export_png_sequence(
    engine: VisualizerEngine,
    directory: str | Path,
    *,
    fps: int = 30,
    width: int = 1280,
    height: int = 720,
    transparent: bool = False,
    progress: ProgressCallback | None = None,
) -> Path:
    _require_rust()
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    fps = max(12, min(60, int(fps)))
    w, h = max(64, int(width)), max(64, int(height))
    dur = ql_to_sec(engine.timeline.duration_ql, engine.bpm)
    n = max(1, int(dur * fps) + 1)

    rust = _make_rust_engine(engine, w, h)
    fmt = QImage.Format.Format_RGBA8888 if transparent else QImage.Format.Format_RGB888

    for i in range(n):
        t = min(dur, i / fps)
        t_ql = t * engine.bpm / 60.0
        rust.set_transport(t_ql, engine.bpm, engine.window_sec, engine.speed)
        rust.tick(1.0 / fps)
        rgba = rust.render_frame_rgba()
        arr = np.frombuffer(rgba, dtype=np.uint8).reshape((h, w, 4))
        if transparent:
            img = QImage(arr.tobytes(), w, h, w * 4, fmt)
        else:
            rgb_bytes = np.ascontiguousarray(arr[:, :, :3]).tobytes()
            img = QImage(rgb_bytes, w, h, w * 3, QImage.Format.Format_RGB888)
        img = img.mirrored(False, True)
        img.save(str(directory / f"frame_{i:05d}.png"))
        if progress:
            progress(i + 1, n)
    return directory
