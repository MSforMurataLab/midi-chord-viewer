# -*- coding: utf-8 -*-
"""起動・終了の診断ログ（%LOCALAPPDATA%/<APP_DATA_DIR_NAME>/startup.log）。"""
from __future__ import annotations

import traceback
from pathlib import Path

from midi_lab.branding import APP_DATA_DIR_NAME


def log_path() -> Path:
    import os

    base = os.environ.get("LOCALAPPDATA") or str(Path.home())
    return Path(base) / APP_DATA_DIR_NAME / "startup.log"


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
