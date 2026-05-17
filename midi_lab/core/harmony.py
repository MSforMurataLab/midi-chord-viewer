# -*- coding: utf-8 -*-
"""和声解析・コード／メロディ候補生成。"""
from __future__ import annotations

import re

from music21 import chord as m21_chord
from music21 import harmony
from music21 import key as m21_key
from music21 import note as m21_note
from music21 import pitch as m21_pitch
from music21 import roman
from music21.roman import romanNumeralFromChord


def event_display_label(el: m21_chord.Chord | m21_note.Note, ky: m21_key.Key | None = None) -> str:
    """タイムライン表示用 — コードは chordSymbol 形式（例: Cmaj7, Am）。"""
    if isinstance(el, m21_note.Note):
        return el.nameWithOctave
    if isinstance(el, m21_chord.Chord):
        try:
            cs = harmony.chordSymbolFromChord(el)
            fig = getattr(cs, "figure", None)
            if fig:
                return str(fig)
        except Exception:
            pass
        if ky is not None:
            try:
                rn = romanNumeralFromChord(el, ky)
                fig = getattr(rn, "figure", None)
                if fig:
                    return str(fig)
            except Exception:
                pass
        name = el.pitchedCommonName or el.commonName
        if name:
            return str(name)
    return str(el)


def detect_key_for_score(score) -> tuple[str, m21_key.Key | None]:
    try:
        k = score.analyze("key")
        lab = f"{k.tonic.name} {k.mode}"
        coef = getattr(k, "correlationCoefficient", None)
        if coef is not None:
            lab += f"  ·  r={float(coef):.2f}"
        return lab, k
    except Exception:
        return "不明", None


def parse_chord_cell(text: str, ql: float) -> tuple[m21_chord.Chord | m21_note.Note, tuple[int, ...]]:
    t = text.strip()
    if re.match(r"^[A-G][#b]?\d+$", t):
        n = m21_note.Note(t, quarterLength=ql)
        return n, (n.pitch.midi,)
    if "（単音）" in t or re.match(r"^[A-G][#b]?\d+\s*（単音）", t):
        note_part = re.sub(r"\s*（単音）\s*$", "", t).strip()
        n = m21_note.Note(note_part, quarterLength=ql)
        return n, (n.pitch.midi,)
    t2 = re.sub(r"\s*（単音）\s*$", "", t).strip()
    try:
        cs = harmony.ChordSymbol(t2)
        ch = m21_chord.Chord(cs.pitches)
        ch.quarterLength = ql
        return ch, tuple(p.midi for p in ch.pitches)
    except Exception:
        pass
    try:
        ch = m21_chord.Chord(t2)
        ch.quarterLength = ql
        return ch, tuple(p.midi for p in ch.pitches)
    except Exception:
        n = m21_note.Note(t2, quarterLength=ql)
        return n, (n.pitch.midi,)


def targeted_chord_suggestions(el: m21_chord.Chord | m21_note.Note, ky: m21_key.Key | None) -> list[str]:
    if ky is None:
        return ["キーが検出できません（候補は参考程度）"]
    cand: list[str] = []
    seen: set[str] = set()

    def add(name: str | None) -> None:
        if not name or name in seen:
            return
        seen.add(name)
        cand.append(name)

    for lab in (
        "I", "I7", "ii", "ii7", "iii", "iii7", "IV", "IVmaj7", "V", "V7",
        "vi", "vi7", "viiø7", "bIII", "bVI", "bVII", "iv", "iiø7", "Ger+6", "It+6", "Fr+6",
    ):
        try:
            rn = roman.RomanNumeral(lab, ky)
            if rn.chord:
                add(rn.chord.pitchedCommonName)
        except Exception:
            continue

    if isinstance(el, m21_chord.Chord):
        cur = el.pitchedCommonName
        cand = [x for x in cand if x != cur]
        try:
            rn0 = romanNumeralFromChord(el, ky)
            if "7" in str(rn0.figure) or str(rn0.figure) in ("V", "v"):
                try:
                    tr = roman.RomanNumeral("bII7", ky)
                    if tr.chord:
                        add(tr.chord.pitchedCommonName)
                except Exception:
                    pass
        except Exception:
            pass
    else:
        for lab in ("I", "IV", "V", "vi"):
            try:
                rn = roman.RomanNumeral(lab, ky)
                if rn.chord:
                    add(rn.chord.pitchedCommonName)
            except Exception:
                pass

    return cand[:18] if cand else ["（候補を生成できません）"]


def _scale_pitch_classes(ky: m21_key.Key) -> set[int]:
    return {p.pitchClass for p in ky.getScale().pitches}


def melody_midi_from_previous(labels: list[str], row_ql: list[float], r: int) -> int | None:
    if r <= 0:
        return None
    try:
        el, mids = parse_chord_cell(labels[r - 1], row_ql[r - 1])
        if isinstance(el, m21_note.Note):
            return el.pitch.midi
        if isinstance(el, m21_chord.Chord):
            return max(mids)
    except Exception:
        return None
    return None


def harmony_chord_for_melody_at_row(
    labels: list[str], row_ql: list[float], r: int, ky: m21_key.Key | None
) -> m21_chord.Chord | None:
    if r < 0 or r >= len(row_ql):
        return None
    try:
        el, _ = parse_chord_cell(labels[r], row_ql[r])
        if isinstance(el, m21_chord.Chord):
            return el
        for j in range(r - 1, -1, -1):
            el2, _ = parse_chord_cell(labels[j], row_ql[j])
            if isinstance(el2, m21_chord.Chord):
                return el2
    except Exception:
        pass
    if ky is not None:
        try:
            rn = roman.RomanNumeral("I", ky)
            if rn.chord:
                return rn.chord
        except Exception:
            pass
    return None


def melodic_note_candidates(
    prev_midi: int | None,
    harmony_ch: m21_chord.Chord | None,
    ky: m21_key.Key | None,
) -> list[str]:
    if ky is None:
        return ["キー未検出のため、旋法に基づく候補を絞り込めません。"]
    if harmony_ch is None:
        return ["この位置の和音を特定できません。"]
    pcs_chord = {p.pitchClass for p in harmony_ch.pitches}
    pcs_scale = _scale_pitch_classes(ky)
    center = prev_midi if prev_midi is not None else 64
    scored: list[tuple[int, str]] = []

    def add(mid: int, reason: str) -> None:
        if 36 <= mid <= 108:
            scored.append((mid, reason))

    for p in harmony_ch.pitches:
        base = p.midi
        for mid in (base - 24, base - 12, base, base + 12, base + 24):
            if prev_midi is None:
                if 55 <= mid <= 79:
                    add(mid, "和音構成音（中央付近）")
            elif abs(mid - prev_midi) <= 12:
                add(mid, "和音構成音（ボイシング近接）")

    if prev_midi is not None:
        for delta in range(-8, 9):
            if delta == 0:
                continue
            mid = prev_midi + delta
            pc = mid % 12
            if pc in pcs_chord:
                add(mid, f"先行音から{delta:+d}半音（和音内）")
            elif pc in pcs_scale:
                add(mid, f"先行音から{delta:+d}半音（旋法内）")
            elif abs(delta) <= 2:
                add(mid, f"先行音から{delta:+d}半音（経過）")

    if not scored and prev_midi is None:
        for p in harmony_ch.pitches[:4]:
            mid = p.midi
            while mid < 60:
                mid += 12
            while mid > 84:
                mid -= 12
            add(mid, "和音構成音（先頭）")

    best: dict[int, str] = {}
    for mid, reason in scored:
        if mid not in best:
            best[mid] = reason

    def sort_key(m: int) -> tuple[int, int]:
        d = abs(m - center) if prev_midi is None else abs(m - prev_midi)
        return (d, m)

    lines = [f"{m21_pitch.Pitch(mid).nameWithOctave}  —  {best[mid]}" for mid in sorted(best, key=sort_key)[:26]]
    return lines if lines else ["（候補を生成できません）"]
