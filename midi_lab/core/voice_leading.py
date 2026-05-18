# -*- coding: utf-8 -*-
"""連続する和声音価間の声部進行解析。"""
from __future__ import annotations

import itertools
from dataclasses import dataclass

from midi_lab.core.score import HarmonyEvent


@dataclass(frozen=True)
class VoiceMotion:
    from_midi: int
    to_midi: int
    semitones: int


@dataclass(frozen=True)
class VoiceLeadingStep:
    index: int
    from_label: str
    to_label: str
    from_offset: float
    to_offset: float
    motions: tuple[VoiceMotion, ...]
    motion_kind: str
    total_motion: int
    max_leap: int


def _match_voices(prev: list[int], nxt: list[int]) -> list[VoiceMotion]:
    if not prev or not nxt:
        return []
    if len(prev) == 1 and len(nxt) == 1:
        a, b = prev[0], nxt[0]
        return [VoiceMotion(a, b, b - a)]
    best: list[tuple[int, ...]] | None = None
    best_cost = 10**9
    if len(prev) <= len(nxt):
        shorter, longer = prev, nxt
        fixed, var = shorter, longer
    else:
        shorter, longer = nxt, prev
        fixed, var = shorter, longer
    k = len(fixed)
    for perm in itertools.permutations(var, k):
        cost = sum(abs(f - p) for f, p in zip(fixed, perm))
        if cost < best_cost:
            best_cost = cost
            best = perm
    if best is None:
        return []
    motions: list[VoiceMotion] = []
    if len(prev) <= len(nxt):
        for a, b in zip(prev, best):
            motions.append(VoiceMotion(a, b, b - a))
        for extra in nxt[len(prev) :]:
            motions.append(VoiceMotion(extra, extra, 0))
    else:
        for a, b in zip(best, nxt):
            motions.append(VoiceMotion(a, b, b - a))
    return motions


def _classify_motion(motions: list[VoiceMotion]) -> str:
    if len(motions) < 2:
        return "単声" if motions else "—"
    dirs = []
    for m in motions:
        if m.semitones > 0:
            dirs.append(1)
        elif m.semitones < 0:
            dirs.append(-1)
        else:
            dirs.append(0)
    nonzero = [d for d in dirs if d != 0]
    if len(nonzero) < 2:
        return "斜行"
    if all(d == nonzero[0] for d in nonzero):
        return "順行"
    if all(d == -nonzero[0] for d in nonzero):
        return "逆行"
    return "混合"


def analyze_voice_leading(
    events: list[HarmonyEvent],
    label_fn,
) -> list[VoiceLeadingStep]:
    """和声イベント列から声部進行ステップを生成。label_fn(element) -> str。"""
    steps: list[VoiceLeadingStep] = []
    chord_events = [(i, ev) for i, ev in enumerate(events) if len(ev.pitches) >= 2]
    for j in range(1, len(chord_events)):
        i0, ev0 = chord_events[j - 1]
        i1, ev1 = chord_events[j]
        prev = list(ev0.pitches)
        nxt = list(ev1.pitches)
        motions = _match_voices(prev, nxt)
        total = sum(abs(m.semitones) for m in motions)
        max_leap = max((abs(m.semitones) for m in motions), default=0)
        kind = _classify_motion(motions)
        steps.append(
            VoiceLeadingStep(
                index=len(steps) + 1,
                from_label=label_fn(ev0.element),
                to_label=label_fn(ev1.element),
                from_offset=ev0.offset,
                to_offset=ev1.offset,
                motions=tuple(motions),
                motion_kind=kind,
                total_motion=total,
                max_leap=max_leap,
            )
        )
    return steps


def format_motions(motions: tuple[VoiceMotion, ...]) -> str:
    parts = []
    for m in motions:
        sign = "+" if m.semitones >= 0 else ""
        parts.append(f"{m.from_midi}→{m.to_midi}({sign}{m.semitones})")
    return " · ".join(parts) if parts else "—"
