# -*- coding: utf-8 -*-
from midi_lab.core.playback_schedule import build_playback_schedule
from midi_lab.core.note_events import NoteEvent


def test_build_playback_schedule_prefers_note_events():
    events = [
        NoteEvent(
            offset=0.0,
            quarter_length=1.0,
            midi=60,
            velocity=80,
            channel=0,
            program=0,
            part_index=0,
        )
    ]
    tl = [(0.0, 1.0, (64, 67, 71))]
    sched, ch, ccs = build_playback_schedule(events, tl, 120)
    assert len(sched) == 1
    assert sched[0].midi == 60
    assert ch.get(0) == 0
    assert ccs == []


def test_build_playback_schedule_harmony_fallback():
    tl = [(0.0, 1.0, (60, 64, 67))]
    sched, ch, ccs = build_playback_schedule([], tl, 120)
    assert len(sched) == 3
    assert ch.get(0) is not None
