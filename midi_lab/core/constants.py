# -*- coding: utf-8 -*-
"""アプリ全体で共有する定数（レビュー: BPM クランプ範囲の不一致を解消）。"""
from __future__ import annotations

BPM_MIN = 40
BPM_MAX = 208
DEFAULT_BPM = 120


def clamp_bpm(bpm: int | float) -> int:
    """UI・再生・MIDI 書き出しで同じテンポ範囲を使う。"""
    return max(BPM_MIN, min(BPM_MAX, int(round(float(bpm)))))
