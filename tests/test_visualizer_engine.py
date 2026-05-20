# -*- coding: utf-8 -*-
from midi_lab.core.note_events import NoteEvent
from midi_lab.visualizer.engine import VisualizerEngine
from midi_lab.visualizer.styles import STYLE_ORDER, STYLES
from midi_lab.visualizer.timeline import visible_beat_window


def _events():
    return [
        NoteEvent(0.0, 1.0, 60, 90, 0),
        NoteEvent(1.0, 1.0, 64, 80, 0),
        NoteEvent(2.0, 2.0, 67, 100, 1),
    ]


def test_visible_window_at_start():
    x0, x1 = visible_beat_window(0.0, 20.0, 100.0)
    assert x0 == 0.0
    assert x1 >= 10.0


def test_engine_load_and_styles():
    eng = VisualizerEngine()
    eng.load_events(_events())
    assert len(eng.timeline.notes) == 3
    for sid in STYLE_ORDER:
        eng.set_style(sid)
        assert eng.style_id == sid
        assert sid in STYLES
