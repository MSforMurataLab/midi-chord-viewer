# -*- coding: utf-8 -*-
"""Rust wgpu ビジュアライザ — オプショナルネイティブ拡張。"""
from __future__ import annotations

_RUST_AVAILABLE = False
_midi_viz = None

try:
    import midi_viz as _midi_viz

    _RUST_AVAILABLE = bool(_midi_viz.is_available())
except ImportError:
    _midi_viz = None


def rust_available() -> bool:
    return _RUST_AVAILABLE


def VisualizerEngine(width: int, height: int):
    if not _RUST_AVAILABLE or _midi_viz is None:
        raise RuntimeError("midi_viz native module not built. Run scripts/build_rust.bat")
    return _midi_viz.VisualizerEngine(width, height)
