# -*- coding: utf-8 -*-
"""和声解析・コード／メロディ候補生成。"""
from __future__ import annotations

import copy
import re

from music21 import chord as m21_chord
from music21 import harmony
from music21 import key as m21_key
from music21 import note as m21_note
from music21 import pitch as m21_pitch
from midi_lab.core.chord_rules import (
    chord_spec_from_element,
    key_from_music21,
    rule_based_chord_suggestions,
)

_UNIDENTIFIED_RE = re.compile(r"cannot be identified", re.I)

# chord_figure_from_chord の結果キャッシュ（声部進行・表の重複和音向け）
_CHORD_FIGURE_CACHE: dict[tuple[int, ...], str] = {}
_CHORD_FIGURE_CACHE_MAX = 8192

# (ルートからの半音集合, サフィックス, 優先度) — music21 失敗時のテンプレート照合
_CHORD_TEMPLATES: list[tuple[frozenset[int], str, int]] = [
    (frozenset({7}), "5", 8),
    (frozenset({4, 7}), "", 24),
    (frozenset({3, 7}), "m", 24),
    (frozenset({3, 6}), "dim", 20),
    (frozenset({4, 8}), "+", 18),
    (frozenset({2, 7}), "sus2", 19),
    (frozenset({5, 7}), "sus4", 19),
    (frozenset({4, 7, 11}), "maj7", 26),
    (frozenset({4, 7, 10}), "7", 26),
    (frozenset({3, 7, 10}), "m7", 26),
    (frozenset({3, 7, 11}), "mM7", 22),
    (frozenset({3, 6, 10}), "m7b5", 25),
    (frozenset({3, 6, 9}), "dim7", 22),
    (frozenset({4, 7, 10, 2}), "9", 23),
    (frozenset({3, 7, 10, 2}), "m9", 22),
    (frozenset({4, 7, 11, 2}), "maj9", 21),
    (frozenset({4, 7, 10, 5}), "11", 20),
    (frozenset({4, 7, 10, 2, 9}), "13", 19),
    (frozenset({3, 7, 10, 5}), "m11", 18),
    (frozenset({4, 7, 10, 5, 2}), "13", 18),
    (frozenset({4, 11}), "maj7", 23),
    (frozenset({4, 10}), "7", 23),
    (frozenset({3, 10}), "m7", 23),
    (frozenset({3, 11}), "mM7", 21),
    (frozenset({2, 4}), "sus2", 14),
]


def _is_bad_figure(fig: str | None) -> bool:
    if not fig or not str(fig).strip():
        return True
    return bool(_UNIDENTIFIED_RE.search(str(fig)))


def _chord_has_third(ch: m21_chord.Chord) -> bool:
    pcs = {p.pitchClass for p in ch.pitches}
    for a in pcs:
        for b in pcs:
            if a == b:
                continue
            if (b - a) % 12 in (3, 4):
                return True
    return False


def _accept_music21_figure(ch: m21_chord.Chord, fig: str) -> bool:
    if _is_bad_figure(fig):
        return False
    # 3度を含むのに power / 5 だけの記号は誤判定になりやすい
    if _chord_has_third(ch) and re.search(r"(^|[^a-z])5|power", fig, re.I):
        return False
    return True


def _normalize_figure(fig: str) -> str:
    s = str(fig).strip()
    s = s.replace("power", "5")
    s = s.replace("Maj", "maj").replace("Ma7", "maj7")
    return s


def _intervals_from_root(pcs: set[int], root_pc: int) -> frozenset[int]:
    return frozenset((pc - root_pc) % 12 for pc in pcs if pc != root_pc)


def _pitch_name_at_interval(root: m21_pitch.Pitch, semitones: int) -> str:
    p = m21_pitch.Pitch(root.midi + semitones)
    return p.name


def _format_additions(root: m21_pitch.Pitch, extra: set[int]) -> str:
    if not extra:
        return ""
    names: list[str] = []
    for iv in sorted(extra):
        try:
            names.append(_pitch_name_at_interval(root, iv))
        except Exception:
            continue
    if not names:
        return ""
    return "add" + ",".join(names)


def _infer_figure_by_templates(ch: m21_chord.Chord) -> str | None:
    pcs = {p.pitchClass for p in ch.pitches}
    if len(pcs) < 2:
        return None

    bass = ch.bass()
    bass_pc = bass.pitchClass
    best_fig: str | None = None
    best_score = -10_000

    for root_pitch in ch.pitches:
        root_pc = root_pitch.pitchClass
        intervals = _intervals_from_root(pcs, root_pc)
        if not intervals and len(pcs) == 1:
            continue

        for tmpl, suffix, priority in _CHORD_TEMPLATES:
            if not tmpl.issubset(intervals):
                continue
            extra = set(intervals) - set(tmpl)
            score = priority - len(extra) * 4
            if root_pc == bass_pc:
                score += 5
            elif bass_pc in pcs:
                score += 1
            if len(extra) == 0:
                score += 4
            elif len(extra) <= 2:
                score += 1

            fig = root_pitch.name + suffix
            if bass_pc != root_pc:
                fig += "/" + bass.name
            add_part = _format_additions(root_pitch, extra)
            if add_part:
                fig += add_part

            if score > best_score:
                best_score = score
                best_fig = fig

    return best_fig


def _infer_figure_bass_add(ch: m21_chord.Chord) -> str:
    """テンプレート不一致時 — 低音をルートに add 表記で構成音を列挙。"""
    bass = ch.bass()
    root_pc = bass.pitchClass
    extras: set[int] = set()
    for p in ch.pitches:
        if p.pitchClass == root_pc and p.midi == bass.midi:
            continue
        iv = (p.pitchClass - root_pc) % 12
        if iv:
            extras.add(iv)
    fig = bass.name
    add_part = _format_additions(bass, extras)
    if add_part:
        return fig + add_part
    if len({p.pitchClass for p in ch.pitches}) == 1:
        return bass.nameWithOctave
    names = sorted({p.name for p in ch.pitches if p.pitchClass != root_pc})
    if names:
        return fig + "add" + ",".join(names)
    return fig


def _music21_figure(ch: m21_chord.Chord) -> str | None:
    try:
        fig = harmony.chordSymbolFigureFromChord(ch)
        if _accept_music21_figure(ch, str(fig)):
            return _normalize_figure(fig)
    except Exception:
        pass
    return None


def _music21_figure_with_root_guesses(ch: m21_chord.Chord) -> str | None:
    pitches = list(ch.pitches)
    try_first = [ch.bass(), *sorted(pitches, key=lambda p: p.midi)]
    seen: set[int] = set()
    for root_pitch in try_first:
        if root_pitch.midi in seen:
            continue
        seen.add(root_pitch.midi)
        trial = m21_chord.Chord([copy.deepcopy(p) for p in pitches])
        try:
            trial.root(root_pitch)
            fig = _music21_figure(trial)
            if fig:
                return fig
        except Exception:
            continue
    return None


def clear_chord_figure_cache() -> None:
    _CHORD_FIGURE_CACHE.clear()


def _store_chord_figure(cache_key: tuple[int, ...], figure: str) -> str:
    if len(_CHORD_FIGURE_CACHE) < _CHORD_FIGURE_CACHE_MAX:
        _CHORD_FIGURE_CACHE[cache_key] = figure
    return figure


def chord_figure_from_chord(ch: m21_chord.Chord, ky: m21_key.Key | None = None) -> str:
    """構成音からコード記号を推定（music21 + テンプレート + add 表記）。"""
    cache_key = tuple(sorted(p.midi for p in ch.pitches))
    cached = _CHORD_FIGURE_CACHE.get(cache_key)
    if cached is not None:
        return cached

    fig = _music21_figure(ch)
    if fig:
        return _store_chord_figure(cache_key, fig)

    fig = _infer_figure_by_templates(ch)
    if fig:
        return _store_chord_figure(cache_key, _normalize_figure(fig))

    fig = _music21_figure_with_root_guesses(ch)
    if fig:
        return _store_chord_figure(cache_key, fig)

    # キー文脈でルート推定を再試行
    if ky is not None:
        try:
            trial = copy.deepcopy(ch)
            sc = ky.getScale()
            scale_pcs = {p.pitchClass for p in sc.pitches}
            chord_pcs = {p.pitchClass for p in ch.pitches}
            for pc in chord_pcs:
                if pc in scale_pcs:
                    rp = next(p for p in ch.pitches if p.pitchClass == pc)
                    trial.root(rp)
                    fig = _music21_figure(trial) or _music21_figure_with_root_guesses(trial)
                    if fig:
                        return _store_chord_figure(cache_key, fig)
        except Exception:
            pass

    return _store_chord_figure(cache_key, _normalize_figure(_infer_figure_bass_add(ch)))


def voice_leading_label(el: m21_chord.Chord | m21_note.Note, ky: m21_key.Key | None = None) -> str:
    """声部進行表向けの軽量ラベル（重い chord 推定を避ける）。"""
    if isinstance(el, m21_note.Note):
        return el.nameWithOctave
    if isinstance(el, m21_chord.Chord):
        ps = sorted(el.pitches, key=lambda p: p.midi)
        if len(ps) <= 1:
            return ps[0].nameWithOctave if ps else "?"
        cache_key = tuple(p.midi for p in ps)
        cached = _CHORD_FIGURE_CACHE.get(cache_key)
        if cached is not None:
            return cached
        # 構成音表記（即時）— 必要ならキャッシュ済みコード記号に差し替え可能
        return "–".join(p.nameWithOctave for p in ps)
    return str(el)


def event_display_label(el: m21_chord.Chord | m21_note.Note, ky: m21_key.Key | None = None) -> str:
    """タイムライン表示用 — コードは chordSymbol 形式（例: Cmaj7, Am）。"""
    if isinstance(el, m21_note.Note):
        return el.nameWithOctave
    if isinstance(el, m21_chord.Chord):
        return chord_figure_from_chord(el, ky)
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


def targeted_chord_suggestions(
    el: m21_chord.Chord | m21_note.Note,
    ky: m21_key.Key | None,
    *,
    label: str = "",
    labels: list[str] | None = None,
    row_ql: list[float] | None = None,
    row: int = 0,
    melody_midi: int | None = None,
) -> list[str]:
    key = key_from_music21(ky)
    if key is None:
        return ["キーが検出できません（候補は参考程度）"]

    figure = label.strip() if label else ""
    if not figure and isinstance(el, m21_chord.Chord):
        figure = chord_figure_from_chord(el, ky)

    target = chord_spec_from_element(el, figure)

    next_chord = None
    if labels and row_ql is not None and 0 <= row < len(labels) - 1:
        try:
            nxt_label = labels[row + 1]
            nxt_el, _ = parse_chord_cell(nxt_label, row_ql[row + 1])
            nxt_fig = nxt_label if isinstance(nxt_el, m21_note.Note) else (
                chord_figure_from_chord(nxt_el, ky) if isinstance(nxt_el, m21_chord.Chord) else nxt_label
            )
            next_chord = chord_spec_from_element(nxt_el, nxt_fig)
        except Exception:
            next_chord = None

    return rule_based_chord_suggestions(
        key,
        target,
        next_chord=next_chord,
        melody_midi=melody_midi,
        current_figure=figure,
    )


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
