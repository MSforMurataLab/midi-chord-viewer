# -*- coding: utf-8 -*-
from pathlib import Path

from midi_lab.core.note_events import NoteEvent
from midi_lab.core.playback_notes import build_channel_program_map, build_note_schedule
from midi_lab.core.soundfont_midi import schedule_to_midi_file
from midi_lab.core.soundfont_player import (
    apply_soundfont_selection,
    enumerate_soundfont_choices,
    ensure_playback_ready,
    iter_soundfont_files,
    key_to_soundfont_path,
    resolve_fluidsynth_exe,
    resolve_soundfont_path,
)
from midi_lab.core.settings import set_selected_soundfont


def test_midi_file_has_program_changes(tmp_path):
    events = [
        NoteEvent(0.0, 0.5, 60, 100, 0, channel=0, program=0),
        NoteEvent(0.0, 0.5, 36, 90, 1, channel=1, program=32),
    ]
    sched = build_note_schedule(events, 120)
    ch = build_channel_program_map(events)
    mid_path = tmp_path / "t.mid"
    schedule_to_midi_file(sched, ch, 120, mid_path)
    import mido

    mid = mido.MidiFile(str(mid_path))
    merged = list(mido.merge_tracks(mid.tracks))
    pcs = [m for m in merged if m.type == "program_change"]
    assert len(pcs) >= 2


def test_enumerate_lists_every_sf2_under_soundfonts():
    root = Path(__file__).resolve().parents[1]
    sf_root = root / "assets" / "soundfonts"
    if not sf_root.is_dir():
        return
    on_disk = {p.resolve() for p in iter_soundfont_files(sf_root)}
    in_combo = {c.path for c in enumerate_soundfont_choices()}
    assert on_disk == in_combo
    assert on_disk, "expected at least one .sf2 under assets/soundfonts"


def test_selected_soundfont_switch():
    root = Path(__file__).resolve().parents[1]
    ac = root / "assets" / "soundfonts" / "Animal_Crossing_Wild_World.sf2"
    gu = root / "assets" / "soundfonts" / "GeneralUser-GS" / "GeneralUser-GS.sf2"
    if not ac.is_file() or not gu.is_file():
        return
    apply_soundfont_selection("Animal_Crossing_Wild_World.sf2")
    assert resolve_soundfont_path() == ac.resolve()
    apply_soundfont_selection("GeneralUser-GS/GeneralUser-GS.sf2")
    assert resolve_soundfont_path() == gu.resolve()
    set_selected_soundfont("")


def test_soundfont_assets_optional():
    root = Path(__file__).resolve().parents[1]
    if not resolve_fluidsynth_exe():
        return
    if not enumerate_soundfont_choices():
        return
    ensure_playback_ready()
