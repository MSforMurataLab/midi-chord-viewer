# -*- coding: utf-8 -*-
"""MIDI スコアからテンポ（BPM）を取得。"""
from __future__ import annotations

from midi_lab.core.constants import clamp_bpm, DEFAULT_BPM


def detect_score_bpm(score, default: int = DEFAULT_BPM) -> int:
    """最初の MetronomeMark を BPM として返す（constants.clamp_bpm で統一）。"""
    try:
        from music21 import tempo as m21_tempo

        flat = score.flatten() if hasattr(score, "flatten") else score
        for mm in flat.getElementsByClass(m21_tempo.MetronomeMark):
            num = getattr(mm, "number", None)
            if num is not None:
                return clamp_bpm(float(num))
    except Exception:
        pass
    return clamp_bpm(default)
