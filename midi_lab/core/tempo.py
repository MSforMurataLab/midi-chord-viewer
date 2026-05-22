# -*- coding: utf-8 -*-
"""テンポ換算の単一実装（レビュー: playback / playback_notes の重複 _tempo_spq を統合）。"""
from __future__ import annotations

from midi_lab.core.constants import clamp_bpm


def seconds_per_quarter(tempo: int) -> float:
    """1 四分音符あたりの秒数。UI・再生・MIDI 書き出しで同じ BPM クランプを使う。"""
    return 60.0 / float(clamp_bpm(tempo))
