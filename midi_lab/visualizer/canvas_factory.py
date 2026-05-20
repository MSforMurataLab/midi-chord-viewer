# -*- coding: utf-8 -*-
"""ビジュアライザキャンバス — Rust/wgpu のみ。"""
from __future__ import annotations

from PyQt6.QtWidgets import QWidget

from midi_lab.visualizer.rust_bridge import rust_available


def create_visualizer_canvas(parent: QWidget | None = None):
    if not rust_available():
        raise RuntimeError(
            "midi_viz ネイティブモジュールが見つかりません。"
            " scripts/run_maturin.ps1 または scripts/build_rust.bat を実行してください。"
        )
    from midi_lab.visualizer.widget_rust import RustVisualizerCanvas

    return RustVisualizerCanvas(parent)


def backend_name() -> str:
    if not rust_available():
        raise RuntimeError("midi_viz がビルドされていません。")
    return "rust/wgpu"
