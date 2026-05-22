# -*- coding: utf-8 -*-
from pathlib import Path

import mido

from midi_lab.core.midi_controls import (
    CC_CHANNEL_VOLUME,
    CC_EXPRESSION,
    collect_channel_controls,
    collect_note_events_from_midi,
)
from midi_lab.core.soundfont_midi import schedule_to_midi_file
from midi_lab.core.playback_notes import build_note_schedule, build_channel_program_map


def test_collect_channel_controls_from_bond():
    root = Path(__file__).resolve().parents[1]
    mid_path = root / "assets" / "soundfonts" / "GeneralUser-GS" / "demo MIDIs" / "Bond.mid"
    if not mid_path.is_file():
        return
    ccs = collect_channel_controls(mid_path)
    assert any(c.control == CC_CHANNEL_VOLUME for c in ccs)
    assert any(c.control == CC_EXPRESSION for c in ccs)


def test_schedule_midi_includes_volume_cc(tmp_path):
    root = Path(__file__).resolve().parents[1]
    mid_path = root / "assets" / "soundfonts" / "GeneralUser-GS" / "demo MIDIs" / "Bond.mid"
    if not mid_path.is_file():
        return
    events = collect_note_events_from_midi(mid_path)[:20]
    ccs = collect_channel_controls(mid_path)[:50]
    sched = build_note_schedule(events, 120)
    ch = build_channel_program_map(events)
    out = tmp_path / "out.mid"
    schedule_to_midi_file(sched, ch, 120, out, channel_controls=ccs)
    merged = list(mido.merge_tracks(mido.MidiFile(str(out)).tracks))
    vol = [m for m in merged if m.type == "control_change" and m.control == CC_CHANNEL_VOLUME]
    expr = [m for m in merged if m.type == "control_change" and m.control == CC_EXPRESSION]
    assert vol
    assert expr
