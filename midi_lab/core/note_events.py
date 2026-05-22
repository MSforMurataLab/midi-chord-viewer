# -*- coding: utf-8 -*-
"""元 MIDI スコアからの生ノートイベント抽出（和声 chordify とは独立）。"""
from __future__ import annotations

from dataclasses import dataclass

from music21 import chord as m21_chord
from music21 import note as m21_note

from midi_lab.core.instruments import (
    default_program_for_part,
    program_for_part,
    program_from_instrument_name,
)

_NOTE_CLASSES = (m21_note.Note, m21_chord.Chord)


@dataclass(frozen=True)
class NoteEvent:
    offset: float
    quarter_length: float
    midi: int
    velocity: int
    part_index: int
    channel: int = 0
    program: int | None = None


def _velocity(el) -> int:
    v = getattr(getattr(el, "volume", None), "velocity", None)
    if v is None:
        return 64
    return max(1, min(127, int(v)))


def _part_midi_channel(part, part_index: int) -> int:
    """MIDI チャンネル 0–15。パートごとに分離（ファイルの channel があれば尊重）。"""
    for obj in (part,):
        ch = getattr(obj, "midiChannel", None)
        if ch is not None:
            return int(ch) % 16
    try:
        inst = part.getInstrument(returnDefault=True)
    except Exception:
        inst = None
    if inst is not None:
        ch = getattr(inst, "midiChannel", None)
        if ch is not None:
            return int(ch) % 16
    # 同一チャンネルに複数パートが載るのを避け、パート index を割り当て
    return part_index % 16


def _append_notes_from_stream(
    stream,
    part_index: int,
    channel: int,
    program: int,
    out: list[NoteEvent],
) -> None:
    """パートを 1 回だけ flatten し、曲頭からの絶対拍でノートを収集。"""
    flat = stream.flatten()
    for el in flat.getElementsByClass(_NOTE_CLASSES):
        off = float(el.offset)
        ql = float(el.quarterLength or 0.25)
        if isinstance(el, m21_note.Note):
            out.append(
                NoteEvent(
                    off,
                    ql,
                    int(el.pitch.midi),
                    _velocity(el),
                    part_index,
                    channel,
                    program,
                )
            )
        elif isinstance(el, m21_chord.Chord):
            vel = _velocity(el)
            for p in el.pitches:
                out.append(
                    NoteEvent(
                        off,
                        ql,
                        int(p.midi),
                        vel,
                        part_index,
                        channel,
                        program,
                    )
                )


def collect_note_events(score) -> list[NoteEvent]:
    """全パートの Note / Chord 内音を時系列で収集（曲頭からの絶対拍）。"""
    events: list[NoteEvent] = []
    parts = list(score.parts) if getattr(score, "parts", None) else None
    if parts:
        for pi, part in enumerate(parts):
            if not part:
                continue
            ch = _part_midi_channel(part, pi)
            prog = program_for_part(part, pi)
            try:
                inst = part.getInstrument(returnDefault=True)
                name = getattr(inst, "instrumentName", None) or getattr(inst, "bestName", None)
                if program_from_instrument_name(str(name) if name else None) == 0:
                    ch = 9
            except Exception:
                pass
            _append_notes_from_stream(part, pi, ch, prog, events)
    elif hasattr(score, "flatten"):
        _append_notes_from_stream(score, 0, 0, default_program_for_part(0), events)
    if len(events) > 1:
        events.sort(key=lambda e: (e.offset, e.midi, e.part_index))
    return events
