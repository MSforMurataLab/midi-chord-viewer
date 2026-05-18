# -*- coding: utf-8 -*-
"""連続する和声音価間の声部進行解析。"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from midi_lab.core.score import HarmonyEvent

# itertools.permutations は和音が 7 音以上だと階乗爆発するため、
# 小さい和音はビットマスク DP、大きい和音は貪欲法で最小移動量割当を行う。
_MAX_DP_ROWS = 8


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


def _assign_rows_dp(cost: np.ndarray) -> list[tuple[int, int]]:
    """cost: (n_rows, n_cols), n_rows <= n_cols。各行を異なる列に割当。"""
    p, n = cost.shape
    if p == 0:
        return []
    if p == 1:
        c = int(np.argmin(cost[0]))
        return [(0, c)]

    inf = int(cost.max()) + 10_000
    dp: dict[int, int] = {0: 0}
    choice: list[dict[int, int]] = []

    for i in range(p):
        ndp: dict[int, int] = {}
        nchoice: dict[int, int] = {}
        for mask, val in dp.items():
            for j in range(n):
                if mask & (1 << j):
                    continue
                nm = mask | (1 << j)
                nc = val + int(cost[i, j])
                if nm not in ndp or nc < ndp[nm]:
                    ndp[nm] = nc
                    nchoice[nm] = j
        choice.append(nchoice)
        dp = ndp

    full = (1 << p) - 1
    # 上の DP は p 行を p 列に割当（n>=p のとき full mask は (1<<p)-1 ではない）
    # 正しくは p 行割当完了 mask は p ビットが立つ組合せのみ
    target_mask = None
    best = inf
    for mask, val in dp.items():
        if bin(mask).count("1") == p and val < best:
            best = val
            target_mask = mask

    if target_mask is None:
        # フォールバック（通常到達しない）
        return _assign_rows_greedy(cost)

    pairs: list[tuple[int, int]] = []
    mask = target_mask
    for i in range(p - 1, -1, -1):
        j = choice[i][mask]
        pairs.append((i, j))
        mask &= ~(1 << j)
    pairs.reverse()
    return pairs


def _assign_rows_greedy(cost: np.ndarray) -> list[tuple[int, int]]:
    """最小コストの貪欲割当（高速・ほぼ最適）。"""
    p, n = cost.shape
    used_r: set[int] = set()
    used_c: set[int] = set()
    pairs: list[tuple[int, int]] = []
    flat = [(int(cost[r, c]), r, c) for r in range(p) for c in range(n)]
    flat.sort(key=lambda x: x[0])
    for _, r, c in flat:
        if r in used_r or c in used_c:
            continue
        used_r.add(r)
        used_c.add(c)
        pairs.append((r, c))
        if len(pairs) >= p:
            break
    return pairs


def _assign_rows(cost: np.ndarray) -> list[tuple[int, int]]:
    p, _ = cost.shape
    if p <= _MAX_DP_ROWS:
        return _assign_rows_dp(cost)
    return _assign_rows_greedy(cost)


def _match_voices(prev: list[int], nxt: list[int]) -> list[VoiceMotion]:
    if not prev or not nxt:
        return []
    if len(prev) == 1 and len(nxt) == 1:
        a, b = prev[0], nxt[0]
        return [VoiceMotion(a, b, b - a)]

    prev_a = np.asarray(prev, dtype=np.int32)
    nxt_a = np.asarray(nxt, dtype=np.int32)

    if len(prev) <= len(nxt):
        cost = np.abs(prev_a[:, None] - nxt_a[None, :])
        pairs = _assign_rows(cost)
        matched_cols = {c for _, c in pairs}
        motions = [
            VoiceMotion(int(prev_a[r]), int(nxt_a[c]), int(nxt_a[c] - prev_a[r]))
            for r, c in pairs
        ]
        for c in range(len(nxt)):
            if c not in matched_cols:
                b = int(nxt_a[c])
                motions.append(VoiceMotion(b, b, 0))
        return motions

    cost = np.abs(nxt_a[:, None] - prev_a[None, :])
    pairs = _assign_rows(cost)
    return [
        VoiceMotion(int(prev_a[c]), int(nxt_a[r]), int(nxt_a[r] - prev_a[c]))
        for r, c in pairs
    ]


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
    chord_events: list[tuple[HarmonyEvent, str]] = []
    for ev in events:
        if len(ev.pitches) >= 2:
            chord_events.append((ev, label_fn(ev.element)))

    steps: list[VoiceLeadingStep] = []
    for j in range(1, len(chord_events)):
        ev0, label0 = chord_events[j - 1]
        ev1, label1 = chord_events[j]
        prev = list(ev0.pitches)
        nxt = list(ev1.pitches)
        motions = _match_voices(prev, nxt)
        total = sum(abs(m.semitones) for m in motions)
        max_leap = max((abs(m.semitones) for m in motions), default=0)
        kind = _classify_motion(motions)
        steps.append(
            VoiceLeadingStep(
                index=len(steps) + 1,
                from_label=label0,
                to_label=label1,
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
