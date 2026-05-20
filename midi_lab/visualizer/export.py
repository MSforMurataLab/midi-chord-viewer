# -*- coding: utf-8 -*-
"""GPU オフライン書き出し — Rust/wgpu + 同梱 FFmpeg（メインスレッド描画推奨）。"""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Callable

import numpy as np
from PyQt6.QtGui import QImage

from midi_lab.visualizer.engine import VisualizerEngine
from midi_lab.visualizer.ffmpeg_util import resolve_ffmpeg_exe
from midi_lab.visualizer.rust_bridge import VisualizerEngine as RustEngine, rust_available
from midi_lab.visualizer.timeline import ql_to_sec

ProgressCallback = Callable[[int, int], None]


def export_duration_ql(engine: VisualizerEngine) -> float:
    """書き出し尺（拍）— 最終ノート + 表示窓の余白。"""
    base = float(engine.timeline.duration_ql)
    if engine.timeline.notes:
        base = max(base, max(n.end_ql for n in engine.timeline.notes))
    tail = engine.window_ql / max(0.25, engine.speed) * 0.35
    return base + tail


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
    rust.set_transport(0.0, py_eng.bpm, py_eng.window_sec, py_eng.speed)
    return rust


def _spawn_ffmpeg(ffmpeg_exe: str, path: Path, width: int, height: int, fps: int) -> subprocess.Popen:
    return subprocess.Popen(
        [
            ffmpeg_exe,
            "-y",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgba",
            "-s",
            f"{width}x{height}",
            "-r",
            str(fps),
            "-i",
            "pipe:0",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-crf",
            "18",
            str(path),
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


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

    ffmpeg_exe = resolve_ffmpeg_exe()
    dur_ql = export_duration_ql(engine)
    dur_sec = ql_to_sec(dur_ql, engine.bpm)
    n_frames = max(1, int(dur_sec * fps) + 1)

    rust = _make_rust_engine(engine, w, h)
    proc = _spawn_ffmpeg(ffmpeg_exe, out, w, h, fps)
    try:
        for i in range(n_frames):
            t_sec = min(dur_sec, i / fps)
            t_ql = min(dur_ql, t_sec * engine.bpm / 60.0)
            rust.set_transport(t_ql, engine.bpm, engine.window_sec, engine.speed)
            rust.tick(1.0 / fps)
            rgba = rust.render_frame_rgba()
            if proc.stdin is not None:
                proc.stdin.write(rgba)
            if progress:
                progress(i + 1, n_frames)
    finally:
        if proc.stdin is not None:
            proc.stdin.close()
        rc = proc.wait()
        del rust
        if rc != 0:
            raise RuntimeError(f"FFmpeg が終了コード {rc} で失敗しました。\nFFmpeg: {ffmpeg_exe}")
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
    dur_ql = export_duration_ql(engine)
    dur = ql_to_sec(dur_ql, engine.bpm)
    n = max(1, int(dur * fps) + 1)

    rust = _make_rust_engine(engine, w, h)
    fmt = QImage.Format.Format_RGBA8888 if transparent else QImage.Format.Format_RGB888

    for i in range(n):
        t = min(dur, i / fps)
        t_ql = min(dur_ql, t * engine.bpm / 60.0)
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
    del rust
    return directory
