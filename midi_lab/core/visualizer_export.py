# -*- coding: utf-8 -*-
"""MIDI ビジュアライザ動画の書き出し（MP4 / MOV / AVI）。"""
from __future__ import annotations

import io
from pathlib import Path
from typing import Callable

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np

from midi_lab.core.midi_visualizer import (
    DEFAULT_WINDOW_SEC,
    VisualStyle,
    VisualizerData,
    ql_to_sec,
    render_frame,
)
from midi_lab.core.note_events import NoteEvent

ProgressCallback = Callable[[int, int], None]


def _ensure_ffmpeg() -> None:
    try:
        import imageio_ffmpeg  # noqa: F401

        imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as exc:
        raise RuntimeError(
            "動画書き出しには FFmpeg が必要です。"
            " pip install imageio-ffmpeg を実行するか、"
            "FFmpeg を PATH に追加してください。"
        ) from exc


def _writer_params(path: Path) -> dict:
    ext = path.suffix.lower()
    if ext == ".mp4":
        return {"format": "FFMPEG", "codec": "libx264", "quality": 8, "pixelformat": "yuv420p"}
    if ext == ".mov":
        return {"format": "FFMPEG", "codec": "libx264", "quality": 8, "pixelformat": "yuv420p"}
    if ext == ".avi":
        return {"format": "FFMPEG", "codec": "libx264", "quality": 7, "pixelformat": "yuv420p"}
    raise ValueError(f"未対応の拡張子です: {ext}（.mp4 / .mov / .avi のみ）")


def _figure_to_rgb(fig, dpi: int) -> np.ndarray:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close(fig)
    buf.seek(0)
    import imageio.v3 as iio

    return iio.imread(buf)


def export_visualizer_video(
    path: str | Path,
    events: list[NoteEvent],
    style: VisualStyle,
    *,
    bpm: float = 120.0,
    fps: int = 30,
    width: int = 1280,
    height: int = 720,
    window_sec: float = DEFAULT_WINDOW_SEC,
    progress: ProgressCallback | None = None,
) -> Path:
    """フレーム列をレンダリングし動画ファイルに保存。"""
    if not events:
        raise ValueError("ノートイベントがありません。")
    _ensure_ffmpeg()
    import imageio.v2 as imageio

    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    vd = VisualizerData.from_events(events)
    duration_sec = max(0.25, ql_to_sec(vd.duration_ql, bpm))
    fps = max(12, min(60, int(fps)))
    n_frames = max(1, int(duration_sec * fps) + 1)
    dpi = 100
    figsize = (width / dpi, height / dpi)
    params = _writer_params(out)

    writer = imageio.get_writer(str(out), fps=fps, **params)
    try:
        for i in range(n_frames):
            t_sec = min(duration_sec, i / fps)
            fig = render_frame(
                style,
                events,
                t_sec=t_sec,
                bpm=bpm,
                window_sec=window_sec,
                figsize=figsize,
                dpi=dpi,
                data=vd,
            )
            if fig is None:
                raise RuntimeError("フレームの生成に失敗しました。")
            frame = _figure_to_rgb(fig, dpi)
            if frame.shape[0] != height or frame.shape[1] != width:
                from PIL import Image

                img = Image.fromarray(frame)
                img = img.resize((width, height), Image.Resampling.LANCZOS)
                frame = np.asarray(img)
            if frame.shape[2] == 4:
                frame = frame[:, :, :3]
            writer.append_data(frame)
            if progress is not None:
                progress(i + 1, n_frames)
    finally:
        writer.close()
    return out


VIDEO_FILTER = "動画 (*.mp4 *.mov *.avi);;MP4 (*.mp4);;QuickTime (*.mov);;AVI (*.avi)"
