# -*- coding: utf-8 -*-
"""MIDI 読み込み・編集用ストリーム構築。"""
from __future__ import annotations

import copy
from dataclasses import dataclass

from music21 import chord as m21_chord
from music21 import converter
from music21 import meter
from music21 import note as m21_note
from music21 import stream as m21_stream

from midi_lab.core.harmony import parse_chord_cell


@dataclass(frozen=True)
class HarmonyEvent:
    offset: float
    quarter_length: float
    pitches: tuple[int, ...]
    element: m21_chord.Chord | m21_note.Note


def load_score(path: str):
    return converter.parse(path)


def build_flat_work_stream(score) -> m21_stream.Stream:
    ch = score.chordify()
    flat = m21_stream.Stream()
    try:
        ts = score.flatten().getTimeSignatures(searchContext=True)
        if ts:
            flat.insert(0.0, ts[0])
        else:
            flat.insert(0.0, meter.TimeSignature("4/4"))
    except Exception:
        flat.insert(0.0, meter.TimeSignature("4/4"))
    for el in ch.flatten().notesAndRests:
        if isinstance(el, (m21_chord.Chord, m21_note.Note)):
            flat.insert(float(el.offset), copy.deepcopy(el))
    return flat


def collect_harmony_events(work: m21_stream.Stream) -> list[HarmonyEvent]:
    """タイムライン表・再生で同じ順序になるイベント一覧。"""
    events: list[HarmonyEvent] = []
    for el in work.flatten().notesAndRests:
        if isinstance(el, m21_chord.Chord):
            ps = tuple(sorted(p.midi for p in el.pitches))
        elif isinstance(el, m21_note.Note):
            ps = (el.pitch.midi,)
        else:
            continue
        events.append(
            HarmonyEvent(
                offset=float(el.offset),
                quarter_length=float(el.quarterLength),
                pitches=ps,
                element=el,
            )
        )
    events.sort(key=lambda e: (e.offset, e.pitches))
    return events


def rebuild_stream_from_table(
    work_flat: m21_stream.Stream | None,
    rows: list[tuple[float, str]],
    row_ql: list[float],
) -> m21_stream.Stream:
    new_flat = m21_stream.Stream()
    ts_set = False
    if work_flat is not None:
        for ts in work_flat.flatten().getElementsByClass(meter.TimeSignature):
            new_flat.insert(0.0, copy.deepcopy(ts))
            ts_set = True
            break
    if not ts_set:
        new_flat.insert(0.0, meter.TimeSignature("4/4"))
    for (off, txt), ql in zip(rows, row_ql):
        el, _ = parse_chord_cell(txt, ql)
        new_flat.insert(off, el)
    return new_flat


def build_playback_timeline(work: m21_stream.Stream) -> list[tuple[float, float, tuple[int, ...]]]:
    return [(e.offset, e.quarter_length, e.pitches) for e in collect_harmony_events(work)]
