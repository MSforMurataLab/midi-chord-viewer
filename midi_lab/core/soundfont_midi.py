# -*- coding: utf-8 -*-
"""再生スケジュール → 標準 MIDI ファイル（チャンネル別 program_change 付き）。"""
from __future__ import annotations

import tempfile
from pathlib import Path

import mido

from midi_lab.core.midi_controls import ChannelControlChange
from midi_lab.core.constants import clamp_bpm
from midi_lab.core.playback_notes import ScheduledNote, schedule_duration_sec

TICKS_PER_BEAT = 480

# 同一時刻では CC → note_on → note_off の順（FluidSynth が音量を先に受け取る）
_MSG_SORT_ORDER = {
    "program_change": 0,
    "control_change": 1,
    "note_on": 2,
    "note_off": 3,
}


def _tempo_us(bpm: int) -> int:
    return int(mido.bpm2tempo(clamp_bpm(bpm)))


def _msg_sort_key(item: tuple[float, mido.Message]) -> tuple:
    t_sec, msg = item
    order = _MSG_SORT_ORDER.get(msg.type, 9)
    ch = getattr(msg, "channel", -1)
    note = getattr(msg, "note", 0)
    return (t_sec, order, ch, note)


def schedule_to_midi_file(
    schedule: list[ScheduledNote],
    channel_programs: dict[int, int],
    tempo: int,
    path: str | Path,
    channel_controls: list[ChannelControlChange] | None = None,
) -> Path:
    """Type-1 MIDI — program_change / CC#7・#11 / ノートを時系列で出力。"""
    path = Path(path)
    spq = 60.0 / float(clamp_bpm(tempo))
    sec_per_tick = spq / TICKS_PER_BEAT

    mid = mido.MidiFile(type=1, ticks_per_beat=TICKS_PER_BEAT)
    tempo_track = mido.MidiTrack()
    tempo_track.append(mido.MetaMessage("set_tempo", tempo=_tempo_us(tempo), time=0))
    mid.tracks.append(tempo_track)

    note_track = mido.MidiTrack()
    events: list[tuple[float, mido.Message]] = []

    for ch in sorted(channel_programs.keys()):
        prog = int(channel_programs[ch]) % 128
        events.append(
            (
                0.0,
                mido.Message("program_change", channel=ch, program=prog, time=0),
            )
        )

    for cc in channel_controls or []:
        ch = int(cc.channel) % 16
        events.append(
            (
                float(cc.offset_ql) * spq,
                mido.Message(
                    "control_change",
                    channel=ch,
                    control=int(cc.control),
                    value=int(cc.value),
                    time=0,
                ),
            )
        )

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

    events.sort(key=_msg_sort_key)

    last_tick = 0
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
    channel_controls: list[ChannelControlChange] | None = None,
) -> Path:
    fd, name = tempfile.mkstemp(suffix=".mid", prefix="midi_lab_play_")
    import os

    os.close(fd)
    return schedule_to_midi_file(
        schedule,
        channel_programs,
        tempo,
        name,
        channel_controls=channel_controls,
    )
