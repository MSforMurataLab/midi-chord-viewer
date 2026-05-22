# -*- coding: utf-8 -*-
"""再生スケジュール → 標準 MIDI ファイル（チャンネル別 program_change 付き）。"""
from __future__ import annotations

import tempfile
from pathlib import Path

import mido

from midi_lab.core.playback_notes import ScheduledNote, schedule_duration_sec

TICKS_PER_BEAT = 480


def _tempo_us(bpm: int) -> int:
    return int(mido.bpm2tempo(max(40, min(220, bpm))))


def schedule_to_midi_file(
    schedule: list[ScheduledNote],
    channel_programs: dict[int, int],
    tempo: int,
    path: str | Path,
) -> Path:
    """Type-1 MIDI — チャンネルごとに program_change を先頭へ。"""
    path = Path(path)
    spq = 60.0 / float(max(40, min(220, tempo)))
    sec_per_tick = spq / TICKS_PER_BEAT

    mid = mido.MidiFile(type=1, ticks_per_beat=TICKS_PER_BEAT)
    tempo_track = mido.MidiTrack()
    tempo_track.append(mido.MetaMessage("set_tempo", tempo=_tempo_us(tempo), time=0))
    mid.tracks.append(tempo_track)

    note_track = mido.MidiTrack()
    last_tick = 0
    for ch in sorted(channel_programs.keys()):
        prog = int(channel_programs[ch]) % 128
        note_track.append(
            mido.Message("program_change", channel=ch, program=prog, time=0)
        )

    events: list[tuple[float, mido.Message]] = []
    for n in schedule:
        ch = int(n.channel) % 16
        events.append(
            (
                n.time_on,
                mido.Message(
                    "note_on", note=n.midi, velocity=n.velocity, channel=ch, time=0
                ),
            )
        )
        events.append(
            (
                n.time_off,
                mido.Message("note_off", note=n.midi, velocity=0, channel=ch, time=0),
            )
        )
    events.sort(key=lambda e: (e[0], 0 if e[1].type == "note_on" else 1, e[1].channel))

    for t_sec, msg in events:
        abs_tick = int(round(t_sec / sec_per_tick))
        delta = max(0, abs_tick - last_tick)
        msg.time = delta
        note_track.append(msg)
        last_tick = abs_tick

    end_sec = schedule_duration_sec(schedule)
    end_tick = int(round(end_sec / sec_per_tick))
    if end_tick > last_tick:
        note_track.append(mido.MetaMessage("end_of_track", time=end_tick - last_tick))

    mid.tracks.append(note_track)
    mid.save(str(path))
    return path


def write_schedule_midi_temp(
    schedule: list[ScheduledNote],
    channel_programs: dict[int, int],
    tempo: int,
) -> Path:
    fd, name = tempfile.mkstemp(suffix=".mid", prefix="midi_lab_play_")
    import os

    os.close(fd)
    return schedule_to_midi_file(schedule, channel_programs, tempo, name)
