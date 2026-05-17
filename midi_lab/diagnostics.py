# -*- coding: utf-8 -*-
"""起動・終了の診断ログ（%LOCALAPPDATA%/MIDIChordViewer/startup.log）。"""
from __future__ import annotations

import traceback
from pathlib import Path


def log_path() -> Path:
    import os

    base = os.environ.get("LOCALAPPDATA") or str(Path.home())
    return Path(base) / "MIDIChordViewer" / "startup.log"


def log(msg: str) -> None:
    try:
        p = log_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except OSError:
        pass


def log_stack(header: str) -> None:
    log(header + "\n" + "".join(traceback.format_stack()))
