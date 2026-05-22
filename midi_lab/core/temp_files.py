# -*- coding: utf-8 -*-
"""一時ファイルの確実な削除（レビュー: クラッシュ時の WAV リーク対策）。"""
from __future__ import annotations

import os
import tempfile
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def temp_file_path(suffix: str = "", prefix: str = "midi_lab_"):
    """yield 後に unlink を試みる。再生中など削除できない場合は呼び出し側で再度削除。"""
    fd, name = tempfile.mkstemp(suffix=suffix, prefix=prefix)
    os.close(fd)
    path = Path(name)
    try:
        yield path
    finally:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass
