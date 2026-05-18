# -*- coding: utf-8 -*-
"""元 MIDI スコアからの生ノートイベント抽出（和声 chordify とは独立）。"""
from __future__ import annotations

from dataclasses import dataclass

from music21 import chord as m21_chord
from music21 import note as m21_note

_NOTE_CLASSES = (m21_note.Note, m21_chord.Chord)


@dataclass(frozen=True)
class NoteEvent:
    offset: float
    quarter_length: float
    midi: int
    velocity: int
    part_index: int


def _velocity(el) -> int:
    v = getattr(getattr(el, "volume", None), "velocity", None)
    if v is None:
        return 64
    return max(1, min(127, int(v)))


def _append_notes_from_stream(
    stream,
    part_index: int,
    out: list[NoteEvent],
) -> None:
    """パートを 1 回だけ flatten し、曲頭からの絶対拍でノートを収集。"""
    flat = stream.flatten()
    for el in flat.getElementsByClass(_NOTE_CLASSES):
        off = float(el.offset)
        ql = float(el.quarterLength or 0.25)
        if isinstance(el, m21_note.Note):
            out.append(NoteEvent(off, ql, int(el.pitch.midi), _velocity(el), part_index))
        elif isinstance(el, m21_chord.Chord):
            vel = _velocity(el)
            for p in el.pitches:
                out.append(NoteEvent(off, ql, int(p.midi), vel, part_index))


def collect_note_events(score) -> list[NoteEvent]:
    """全パートの Note / Chord 内音を時系列で収集（曲頭からの絶対拍）。"""
    events: list[NoteEvent] = []
    parts = list(score.parts) if getattr(score, "parts", None) else None
    if parts:
        for pi, part in enumerate(parts):
            if not part:
                continue
            _append_notes_from_stream(part, pi, events)
    elif hasattr(score, "flatten"):
        _append_notes_from_stream(score, 0, events)
    if len(events) > 1:
        events.sort(key=lambda e: (e.offset, e.midi, e.part_index))
    return events
