from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtGui import QIcon


def app_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path.cwd()))
    return Path(__file__).resolve().parent.parent


def icon_path() -> Path | None:
    p = app_root() / "image.png"
    return p if p.is_file() else None


def application_icon() -> QIcon | None:
    p = icon_path()
    return QIcon(str(p)) if p else None
