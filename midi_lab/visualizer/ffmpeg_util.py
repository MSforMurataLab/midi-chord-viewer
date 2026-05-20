# -*- coding: utf-8 -*-
"""FFmpeg 実行ファイルの解決（PyInstaller 同梱の imageio-ffmpeg を優先）。"""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path


def resolve_ffmpeg_exe() -> str:
    """動画書き出し用 ffmpeg の絶対パス。見つからなければ RuntimeError。"""
    env = os.environ.get("IMAGEIO_FFMPEG_EXE", "").strip()
    if env and Path(env).is_file():
        return str(Path(env).resolve())

    try:
        import imageio_ffmpeg

        exe = imageio_ffmpeg.get_ffmpeg_exe()
        if exe and Path(exe).is_file():
            return str(Path(exe).resolve())
    except Exception:
        pass

    on_path = shutil.which("ffmpeg")
    if on_path:
        return str(Path(on_path).resolve())

    hint = (
        "動画書き出しには FFmpeg が必要です。"
        " pip install imageio-ffmpeg を実行するか、"
        "FFmpeg を PATH に追加してください。"
    )
    if getattr(sys, "frozen", False):
        hint += "（インストーラ版では imageio-ffmpeg が同梱されます。再インストールをお試しください。）"
    raise RuntimeError(hint)
