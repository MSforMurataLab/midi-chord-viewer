# -*- coding: utf-8 -*-
"""Qt OpenGL 3.3 Core プロファイル設定。"""
from __future__ import annotations

from PyQt6.QtGui import QSurfaceFormat


def configure_opengl_surface() -> None:
    fmt = QSurfaceFormat()
    fmt.setVersion(3, 3)
    fmt.setProfile(QSurfaceFormat.OpenGLContextProfile.CoreProfile)
    fmt.setDepthBufferSize(24)
    fmt.setStencilBufferSize(8)
    fmt.setSamples(4)
    QSurfaceFormat.setDefaultFormat(fmt)
