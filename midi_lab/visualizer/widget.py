# -*- coding: utf-8 -*-
"""ModernGL + QOpenGLWidget ビジュアライザキャンバス。"""
from __future__ import annotations

import moderngl
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from PyQt6.QtWidgets import QSizePolicy

from midi_lab.visualizer.engine import VisualizerEngine
from midi_lab.visualizer.gl.renderer import GpuRenderer


class VisualizerCanvas(QOpenGLWidget):
    """GPU 描画 — Qt のデフォルト FBO に直接合成。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumHeight(200)
        self.setUpdateBehavior(QOpenGLWidget.UpdateBehavior.NoPartialUpdate)
        self.engine = VisualizerEngine()
        self._renderer: GpuRenderer | None = None
        self._ctx: moderngl.Context | None = None
        self._gl_ready = False
        self._has_data = False
        self._animating = False
        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._on_tick)
        self._idle_timer = QTimer(self)
        self._idle_timer.setInterval(100)
        self._idle_timer.timeout.connect(self._idle_refresh)

    def set_has_data(self, on: bool) -> None:
        self._has_data = on
        if on:
            self._idle_timer.start()
            if self._gl_ready:
                self.update()
        else:
            self._timer.stop()
            self._idle_timer.stop()
            self._animating = False

    def set_animating(self, on: bool) -> None:
        self._animating = on
        if on and self._has_data and self._gl_ready:
            self._timer.start()
        else:
            self._timer.stop()
            if self._gl_ready and self._has_data:
                self.update()

    def _idle_refresh(self) -> None:
        if self._has_data and self._gl_ready and not self._animating:
            self.update()

    def _on_tick(self) -> None:
        if self._has_data and self._gl_ready:
            self.engine.tick(1.0 / 60.0)
            w, h = self.width(), self.height()
            if w > 0 and h > 0:
                self.engine.spawn_hits_pixels(w, h)
            self.update()

    def initializeGL(self) -> None:  # noqa: N802
        try:
            self._ctx = moderngl.create_context()
            w = max(64, self.width())
            h = max(64, self.height())
            self._renderer = GpuRenderer(self._ctx, w, h)
            self._gl_ready = True
            if self._has_data:
                self.update()
        except Exception as exc:
            self._gl_ready = False
            print(f"[VisualizerCanvas] OpenGL init failed: {exc}")

    def resizeGL(self, w: int, h: int) -> None:  # noqa: N802
        if self._renderer and w > 0 and h > 0:
            self._renderer.resize(w, h)
            if self._has_data:
                self.update()

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        if self._has_data and self._gl_ready:
            self.update()

    def paintGL(self) -> None:  # noqa: N802
        if not self._gl_ready or self._renderer is None or self._ctx is None:
            return
        w, h = self.width(), self.height()
        if w < 1 or h < 1:
            return
        if not self._has_data:
            try:
                fbo = self._ctx.detect_framebuffer()
                fbo.viewport = (0, 0, w, h)
                fbo.use()
                self._ctx.clear(0.04, 0.05, 0.07, 1.0)
            except Exception:
                self._ctx.clear(0.04, 0.05, 0.07, 1.0)
            return

        if self._renderer.width != w or self._renderer.height != h:
            self._renderer.resize(w, h)

        if not self._animating:
            self.engine.spawn_hits_pixels(w, h)

        try:
            target = self._ctx.detect_framebuffer()
        except Exception:
            target = self._ctx.screen
        self._renderer.render(self.engine, target)

    def shutdown_gl(self) -> None:
        if self._renderer is not None:
            self._renderer.release()
            self._renderer = None
        self._ctx = None
        self._gl_ready = False
