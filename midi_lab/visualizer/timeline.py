# -*- coding: utf-8 -*-
"""ビジュアライザ共通タイムライン。"""
from __future__ import annotations

from dataclasses import dataclass, field

from midi_lab.core.note_events import NoteEvent

PIANO_LO = 21
PIANO_HI = 108


@dataclass(frozen=True)
class MidiNote:
    onset_ql: float
    duration_ql: float
    midi: int
    velocity: int
    channel: int = 0

    @property
    def end_ql(self) -> float:
        return self.onset_ql + max(self.duration_ql, 0.04)


@dataclass
class MidiTimeline:
    notes: list[MidiNote] = field(default_factory=list)
    duration_ql: float = 4.0

    @classmethod
    def from_note_events(cls, events: list[NoteEvent]) -> MidiTimeline:
        notes = [
            MidiNote(
                onset_ql=float(e.offset),
                duration_ql=max(float(e.quarter_length), 0.04),
                midi=int(e.midi),
                velocity=int(e.velocity),
                channel=int(e.channel),
            )
            for e in events
        ]
        dur = max((n.end_ql for n in notes), default=4.0)
        return cls(notes=notes, duration_ql=dur)

    def append_live_note(self, midi: int, velocity: int, onset_ql: float, duration_ql: float, channel: int = 0) -> None:
        self.notes.append(
            MidiNote(onset_ql, max(duration_ql, 0.04), midi, velocity, channel)
        )
        self.duration_ql = max(self.duration_ql, onset_ql + duration_ql)

    def y_range(self) -> tuple[int, int]:
        """描画用 MIDI 範囲 — 88鍵内で曲の実音域を画面全体にマッピング。"""
        if not self.notes:
            return PIANO_LO, PIANO_HI

        lo = min(n.midi for n in self.notes)
        hi = max(n.midi for n in self.notes)
        lo = max(PIANO_LO, lo - 2)
        hi = min(PIANO_HI, hi + 2)

        min_span = 24
        if hi - lo < min_span:
            mid = (lo + hi) // 2
            pad = (min_span - (hi - lo) + 1) // 2
            lo = max(PIANO_LO, mid - pad)
            hi = min(PIANO_HI, mid + pad)
        return lo, hi


def visible_beat_window(t_ql: float, window_ql: float, duration_ql: float) -> tuple[float, float]:
    duration_ql = max(float(duration_ql), 0.01)
    window_ql = max(float(window_ql), 0.25)
    t_ql = max(0.0, min(float(t_ql), duration_ql))
    if t_ql < window_ql * 0.05:
        return 0.0, min(window_ql, duration_ql)
    x0 = max(0.0, t_ql - window_ql)
    x1 = min(max(t_ql + 0.02, x0 + 0.5), duration_ql + 0.02)
    return x0, x1


def ql_to_sec(ql: float, bpm: float) -> float:
    return float(ql) * 60.0 / max(20.0, float(bpm))


def sec_to_ql(sec: float, bpm: float) -> float:
    return float(sec) * max(20.0, float(bpm)) / 60.0
