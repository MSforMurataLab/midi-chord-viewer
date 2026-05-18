# -*- coding: utf-8 -*-
"""機能和声 — ローマ数字・スケール度数ラベル。"""
from __future__ import annotations

from music21 import chord as m21_chord
from music21 import key as m21_key
from music21 import note as m21_note
from music21 import pitch as m21_pitch
from music21 import roman as m21_roman


def functional_label(
    el: m21_chord.Chord | m21_note.Note,
    ky: m21_key.Key | None,
) -> str:
    """キー文脈でのローマ数字またはスケール度数。"""
    if ky is None:
        return "—"
    if isinstance(el, m21_note.Note):
        try:
            sd = ky.getScaleDegreeAndAccidentalFromPitch(el.pitch)
            deg, acc = sd[0], sd[1]
            suffix = acc.name if acc is not None and acc.name != "natural" else ""
            return f"{deg}{suffix}"
        except Exception:
            return el.pitch.name
    if not isinstance(el, m21_chord.Chord):
        return "—"
    try:
        ch = m21_chord.Chord(el.pitches)
        rn = m21_roman.romanNumeralFromChord(ch, ky)
        fig = rn.figure
        if fig:
            return fig
    except Exception:
        pass
    try:
        root = el.root()
        if root is not None:
            return root.name
    except Exception:
        pass
    return "?"


def functional_label_from_pitches(
    pitches: tuple[int, ...],
    ky: m21_key.Key | None,
    ql: float = 1.0,
) -> str:
    if not pitches or ky is None:
        return "—"
    if len(pitches) == 1:
        n = m21_note.Note(m21_pitch.Pitch(pitches[0]))
        n.quarterLength = ql
        return functional_label(n, ky)
    ch = m21_chord.Chord([m21_pitch.Pitch(m) for m in pitches])
    ch.quarterLength = ql
    return functional_label(ch, ky)
