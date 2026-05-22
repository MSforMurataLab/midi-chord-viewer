# -*- coding: utf-8 -*-
"""チャンネル別再生スケジュールのテスト。"""
from __future__ import annotations

from midi_lab.core.note_events import NoteEvent
from midi_lab.core.playback_notes import (
    build_channel_program_map,
    build_note_schedule,
    midi_events_from_schedule,
    schedule_duration_sec,
)


def test_note_schedule_preserves_channels():
    events = [
        NoteEvent(0.0, 1.0, 60, 100, 0, channel=0, program=0),
        NoteEvent(0.0, 1.0, 36, 90, 1, channel=1, program=32),
        NoteEvent(2.0, 0.5, 64, 80, 2, channel=2, program=48),
    ]
    sched = build_note_schedule(events, tempo=120)
    assert len(sched) == 3
    chs = {n.channel for n in sched}
    assert chs == {0, 1, 2}
    assert sched[0].program == 0
    assert sched[1].program == 32


def test_channel_program_map_distinct():
    events = [
        NoteEvent(0.0, 1.0, 60, 100, 0, channel=0, program=0),
        NoteEvent(0.0, 1.0, 36, 90, 1, channel=1, program=33),
    ]
    m = build_channel_program_map(events)
    assert m[0] == 0
    assert m[1] == 33


def test_midi_events_include_channel():
    events = [NoteEvent(0.0, 0.5, 60, 100, 0, channel=3, program=40)]
    sched = build_note_schedule(events, tempo=120)
    midi_ev = midi_events_from_schedule(sched)
    on = [e for e in midi_ev if e[1] == "on"]
    assert on[0][4] == 3


def test_schedule_duration():
    events = [
        NoteEvent(0.0, 2.0, 60, 100, 0),
        NoteEvent(4.0, 1.0, 64, 80, 0),
    ]
    sched = build_note_schedule(events, tempo=120)
    # 4ql + 1ql = 5ql at 120bpm = 2.5 sec + tail
    assert schedule_duration_sec(sched) > 2.0
