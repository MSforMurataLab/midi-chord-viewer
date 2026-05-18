# -*- coding: utf-8 -*-
from music21 import stream, tempo

from midi_lab.core.midi_tempo import detect_score_bpm


def test_detect_metronome_mark():
    s = stream.Score()
    s.insert(0, tempo.MetronomeMark(96))
    assert detect_score_bpm(s) == 96
