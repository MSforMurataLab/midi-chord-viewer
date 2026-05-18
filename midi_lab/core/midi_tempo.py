# -*- coding: utf-8 -*-
"""MIDI スコアからテンポ（BPM）を取得。"""
from __future__ import annotations


def detect_score_bpm(score, default: int = 120) -> int:
    """最初の MetronomeMark を BPM として返す（40–208 にクランプ）。"""
    try:
        from music21 import tempo as m21_tempo

        flat = score.flatten() if hasattr(score, "flatten") else score
        for mm in flat.getElementsByClass(m21_tempo.MetronomeMark):
            num = getattr(mm, "number", None)
            if num is not None:
                return max(40, min(208, int(round(float(num)))))
    except Exception:
        pass
    return default
