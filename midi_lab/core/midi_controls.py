# -*- coding: utf-8 -*-
"""MIDI ファイルからのチャンネル音量（CC#7 / CC#11）と再生用ノート抽出。"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import mido

from midi_lab.core.note_events import NoteEvent

CC_CHANNEL_VOLUME = 7
CC_EXPRESSION = 11
_VOLUME_CONTROLS = frozenset({CC_CHANNEL_VOLUME, CC_EXPRESSION})


@dataclass(frozen=True)
class ChannelControlChange:
    """絶対拍（四分音符）でのコントロールチェンジ。"""

    offset_ql: float
    channel: int
    control: int
    value: int


def _is_midi_path(path: str | Path) -> bool:
    return Path(path).suffix.lower() in (".mid", ".midi")


def collect_channel_controls(path: str | Path) -> list[ChannelControlChange]:
    """CC#7（Volume）と CC#11（Expression）を時系列で収集。"""
    if not _is_midi_path(path):
        return []
    mid = mido.MidiFile(str(path))
    tpb = mid.ticks_per_beat
    out: list[ChannelControlChange] = []
    abs_tick = 0
    for msg in mido.merge_tracks(mid.tracks):
        abs_tick += msg.time
        if msg.type != "control_change" or msg.control not in _VOLUME_CONTROLS:
            continue
        out.append(
            ChannelControlChange(
                offset_ql=abs_tick / float(tpb),
                channel=int(msg.channel) % 16,
                control=int(msg.control),
                value=max(0, min(127, int(msg.value))),
            )
        )
    if len(out) > 1:
        out.sort(key=lambda c: (c.offset_ql, c.channel, c.control))
    return out


def collect_note_events_from_midi(path: str | Path) -> list[NoteEvent]:
    """mido でノートを抽出（元 MIDI のチャンネル・ベロシティを保持）。"""
    mid = mido.MidiFile(str(path))
    tpb = mid.ticks_per_beat
    ch_program: dict[int, int] = {}
    active: dict[tuple[int, int], tuple[float, int]] = {}
    out: list[NoteEvent] = []
    abs_tick = 0

    for msg in mido.merge_tracks(mid.tracks):
        abs_tick += msg.time
        if not hasattr(msg, "channel"):
            continue
        ql = abs_tick / float(tpb)
        ch = int(msg.channel) % 16

        if msg.type == "program_change":
            ch_program[ch] = int(msg.program) % 128
            continue

        if msg.type == "note_on" and msg.velocity > 0:
            active[(ch, msg.note)] = (ql, int(msg.velocity))
            continue

        if msg.type == "note_off" or (msg.type == "note_on" and msg.velocity == 0):
            key = (ch, msg.note)
            start = active.pop(key, None)
            if start is None:
                continue
            t_on, vel = start
            ql_len = max(ql - t_on, 0.04)
            out.append(
                NoteEvent(
                    offset=t_on,
                    quarter_length=ql_len,
                    midi=int(msg.note) % 128,
                    velocity=max(1, min(127, vel)),
                    part_index=ch,
                    channel=ch,
                    program=ch_program.get(ch),
                )
            )

    if len(out) > 1:
        out.sort(key=lambda e: (e.offset, e.midi, e.channel))
    return out


def collect_playback_from_midi(
    path: str | Path,
) -> tuple[list[NoteEvent], list[ChannelControlChange]]:
    """再生用ノート列と音量系 CC をまとめて取得。"""
    return (
        collect_note_events_from_midi(path),
        collect_channel_controls(path),
    )
