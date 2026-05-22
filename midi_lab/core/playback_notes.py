# -*- coding: utf-8 -*-
"""元ノート列のチャンネル別スケジュールとソフトウェア合成。"""
from __future__ import annotations

from dataclasses import dataclass

from midi_lab.core.instruments import is_percussion_channel, program_for_part
from midi_lab.core.note_events import NoteEvent

try:
    import numpy as np
except ImportError:
    np = None  # type: ignore


@dataclass(frozen=True)
class ScheduledNote:
    time_on: float
    time_off: float
    midi: int
    velocity: int
    channel: int
    program: int


def _tempo_spq(tempo: int) -> float:
    return 60.0 / float(max(40, min(220, tempo)))


def build_channel_program_map(
    events: list[NoteEvent],
    part_programs: dict[int, int] | None = None,
) -> dict[int, int]:
    """チャンネル → GM program。"""
    part_programs = part_programs or {}
    ch_prog: dict[int, int] = {}
    for e in events:
        if e.channel in ch_prog:
            continue
        if e.program is not None:
            ch_prog[e.channel] = int(e.program) % 128
        elif e.part_index in part_programs:
            ch_prog[e.channel] = part_programs[e.part_index] % 128
        else:
            from midi_lab.core.instruments import default_program_for_part

            ch_prog[e.channel] = default_program_for_part(e.part_index)
    return ch_prog


def build_note_schedule(events: list[NoteEvent], tempo: int) -> list[ScheduledNote]:
    if not events:
        return []
    spq = _tempo_spq(tempo)
    ch_prog = build_channel_program_map(events)
    out: list[ScheduledNote] = []
    for e in events:
        t_on = float(e.offset) * spq
        t_off = float(e.offset + max(e.quarter_length, 0.04)) * spq
        prog = ch_prog.get(e.channel, 0)
        if e.program is not None:
            prog = int(e.program) % 128
        out.append(
            ScheduledNote(
                time_on=t_on,
                time_off=t_off,
                midi=int(e.midi) % 128,
                velocity=max(1, min(127, int(e.velocity))),
                channel=int(e.channel) % 16,
                program=prog,
            )
        )
    out.sort(key=lambda n: (n.time_on, 0 if n.time_off > n.time_on else 1, n.channel, n.midi))
    return out


def schedule_duration_sec(schedule: list[ScheduledNote]) -> float:
    if not schedule:
        return 0.0
    return max(n.time_off for n in schedule) + 0.15


def _midi_to_freq(midi: int) -> float:
    return 440.0 * (2.0 ** ((midi - 69) / 12.0))


def _note_envelope(n_samples: int, sample_rate: int) -> np.ndarray:
    t = np.arange(n_samples, dtype=np.float32) / sample_rate
    seg_len = n_samples / sample_rate
    attack = min(0.012, seg_len * 0.1)
    release = min(0.05, seg_len * 0.2)
    env = np.ones(n_samples, dtype=np.float32)
    na = max(1, int(attack * sample_rate))
    env[:na] = np.linspace(0.0, 1.0, na, dtype=np.float32)
    nr = max(1, int(release * sample_rate))
    if n_samples > nr:
        env[-nr:] = np.linspace(1.0, 0.0, nr, dtype=np.float32)
    return env


def _synth_wave(program: int, midi: int, t: np.ndarray, sample_rate: int) -> np.ndarray:
    """GM プログラムに応じた簡易波形（チャンネル別音色）。"""
    w = 2.0 * np.pi * _midi_to_freq(midi) * t
    vel_scale = 1.0

    if program >= 112:
        # 打楽器系 — 短いノイズバースト
        rng = np.sin(t * 800.0) * np.sin(t * 1200.0)
        return (rng * np.exp(-t * 25.0)).astype(np.float32) * 0.35

    if 32 <= program <= 39:
        # ベース — 鋸波風（低次倍音）
        s = np.sin(w)
        s += 0.45 * np.sin(2.0 * w)
        s += 0.2 * np.sin(3.0 * w)
        return (s * 0.35).astype(np.float32)

    if 40 <= program <= 51:
        # 弦 — デチューン重ね
        s = np.sin(w) + 0.85 * np.sin(w * 1.003)
        s += 0.85 * np.sin(w * 0.997)
        return (s * 0.22).astype(np.float32)

    if 24 <= program <= 31:
        # ギター — プラック（高次減衰）
        s = np.sin(w) + 0.35 * np.sin(2.0 * w)
        pluck = np.exp(-t * 4.0)
        return (s * pluck * 0.3).astype(np.float32)

    if 56 <= program <= 72:
        # 金管・木管 — やや明るいサイン列
        s = np.sin(w) + 0.25 * np.sin(2.0 * w) + 0.1 * np.sin(3.0 * w)
        return (s * 0.28).astype(np.float32)

    if 73 <= program <= 87:
        # フルート系 — 柔らかいサイン
        return (np.sin(w) * 0.32).astype(np.float32)

    # ピアノ・鍵盤 — 基音 + 弱い倍音
    s = np.sin(w) + 0.35 * np.sin(2.0 * w) + 0.12 * np.sin(4.0 * w)
    return (s * 0.26 * vel_scale).astype(np.float32)


def render_note_schedule_buffer(
    schedule: list[ScheduledNote],
    tempo: int,
    sample_rate: int = 44100,
):
    """チャンネル／プログラム別にミックスしたモノラルバッファ。"""
    if np is None or not schedule:
        return None, sample_rate

    end_sec = schedule_duration_sec(schedule)
    n = int(end_sec * sample_rate) + 1
    buf = np.zeros(n, dtype=np.float32)

    for note in schedule:
        if is_percussion_channel(note.channel):
            prog = 118
        else:
            prog = note.program
        i0 = int(note.time_on * sample_rate)
        i1 = min(n, int(note.time_off * sample_rate))
        if i1 <= i0:
            continue
        seg_n = i1 - i0
        env = _note_envelope(seg_n, sample_rate)
        t = np.arange(seg_n, dtype=np.float32) / sample_rate
        wave = _synth_wave(prog, note.midi, t, sample_rate)
        amp = (note.velocity / 127.0) * 0.55
        buf[i0:i1] += wave * env * amp

    peak = float(np.max(np.abs(buf)))
    if peak > 0.98:
        buf *= 0.98 / peak
    return buf, sample_rate


def midi_events_from_schedule(
    schedule: list[ScheduledNote],
) -> list[tuple[float, str, int, int, int]]:
    """(時刻秒, kind, pitch, velocity, channel) — kind は on/off。"""
    events: list[tuple[float, str, int, int, int]] = []
    for n in schedule:
        ch = int(n.channel) % 16
        events.append((n.time_on, "on", n.midi, n.velocity, ch))
        events.append((n.time_off, "off", n.midi, 0, ch))
    events.sort(key=lambda e: (e[0], 0 if e[1] == "on" else 1, e[4], e[2]))
    return events


def part_programs_from_score(score) -> dict[int, int]:
    """スコアの各パート index → GM program。"""
    out: dict[int, int] = {}
    parts = list(score.parts) if getattr(score, "parts", None) else None
    if not parts:
        return out
    for pi, part in enumerate(parts):
        if part:
            out[pi] = program_for_part(part, pi)
    return out
