# -*- coding: utf-8 -*-
"""MIDI 再生 — 絶対時刻スケジュール / ソフトウェアはタイムライン一括ミックス。"""
from __future__ import annotations

import sys
import tempfile
import threading
import time
import wave
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal

try:
    import mido
except ImportError:
    mido = None  # type: ignore

try:
    import numpy as np
except ImportError:
    np = None  # type: ignore

try:
    import sounddevice as sd
except ImportError:
    sd = None  # type: ignore

SAMPLE_RATE = 44100


def stop_audio_output() -> None:
    """再生を即座に止める（UI の停止ボタンからも呼ぶ）。"""
    if sd is not None:
        try:
            sd.stop()
        except Exception:
            pass
    if sys.platform == "win32":
        try:
            import winsound

            winsound.PlaySound(None, winsound.SND_PURGE)
        except Exception:
            pass


def _tempo_spq(tempo: int) -> float:
    return 60.0 / float(max(40, min(220, tempo)))


def _midi_to_freq(midi: int) -> float:
    return 440.0 * (2.0 ** ((midi - 69) / 12.0))


def _note_envelope(n_samples: int, sample_rate: int) -> np.ndarray:
    t = np.arange(n_samples, dtype=np.float32) / sample_rate
    seg_len = n_samples / sample_rate
    attack = min(0.015, seg_len * 0.12)
    release = min(0.04, seg_len * 0.18)
    env = np.ones(n_samples, dtype=np.float32)
    na = max(1, int(attack * sample_rate))
    env[:na] = np.linspace(0.0, 1.0, na, dtype=np.float32)
    nr = max(1, int(release * sample_rate))
    if n_samples > nr:
        env[-nr:] = np.linspace(1.0, 0.0, nr, dtype=np.float32)
    return env


def build_playback_marks(
    timeline: list[tuple[float, float, tuple[int, ...]]],
    tempo: int,
) -> list[tuple[int, float, float]]:
    """各行インデックスと開始・終了時刻（秒）。"""
    spq = _tempo_spq(tempo)
    marks: list[tuple[int, float, float]] = []
    for row, (off, ql, pitches) in enumerate(timeline):
        if not pitches:
            continue
        start = off * spq
        end = (off + ql) * spq
        marks.append((row, start, end))
    return marks


def render_timeline_buffer(
    timeline: list[tuple[float, float, tuple[int, ...]]],
    tempo: int,
    sample_rate: int = SAMPLE_RATE,
):
    if np is None or not timeline:
        return None, sample_rate, []

    spq = _tempo_spq(tempo)
    marks = build_playback_marks(timeline, tempo)
    if not marks:
        return None, sample_rate, []

    end_sec = max(end for _, _, end in marks) + 0.15
    n = int(end_sec * sample_rate) + 1
    buf = np.zeros(n, dtype=np.float32)

    for off, ql, pitches in timeline:
        ps = {int(p) for p in pitches}
        if not ps:
            continue
        start = off * spq
        end = (off + ql) * spq
        i0 = int(start * sample_rate)
        i1 = min(n, int(end * sample_rate))
        if i1 <= i0:
            continue
        seg_n = i1 - i0
        env = _note_envelope(seg_n, sample_rate)
        t = np.arange(seg_n, dtype=np.float32) / sample_rate
        seg = np.zeros(seg_n, dtype=np.float32)
        amp = 0.24 / max(len(ps), 1)
        for p in ps:
            seg += amp * np.sin(2.0 * np.pi * _midi_to_freq(p) * t).astype(np.float32) * env
        buf[i0:i1] += seg

    peak = float(np.max(np.abs(buf)))
    if peak > 0.98:
        buf *= 0.98 / peak
    return buf, sample_rate, marks


def _sleep_until(target_time: float, stop_check) -> bool:
    """target_time まで待つ。stop_check() が True なら False を返す（中断）。"""
    while True:
        if stop_check():
            return False
        remaining = target_time - time.perf_counter()
        if remaining <= 0:
            return True
        time.sleep(min(0.02, remaining))


def _play_buffer_winsound_async(buf, sample_rate: int, stop_check) -> bool:
    if sys.platform != "win32" or np is None or buf is None:
        return False
    try:
        import winsound

        pcm = (buf * 32767.0).astype(np.int16)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            path = Path(tmp.name)
        with wave.open(str(path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(pcm.tobytes())
        winsound.PlaySound(str(path), winsound.SND_FILENAME | winsound.SND_ASYNC)
        deadline = time.perf_counter() + len(buf) / sample_rate + 0.05
        while time.perf_counter() < deadline:
            if stop_check():
                winsound.PlaySound(None, winsound.SND_PURGE)
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    pass
                return True
            time.sleep(0.02)
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass
        return True
    except Exception:
        return False


def _open_mido_port():
    if mido is None:
        return None
    try:
        names = mido.get_output_names()
    except Exception:
        return None
    if not names:
        return None
    for pref in (
        "Microsoft GS",
        "Microsoft MIDI",
        "VirtualMIDISynth",
        "loopMIDI",
        "LoopBe",
        "Fluid",
        "Synth",
    ):
        for n in names:
            if any(p.lower() in n.lower() for p in (pref,)):
                try:
                    return mido.open_output(n)
                except Exception:
                    continue
    try:
        return mido.open_output(names[0])
    except Exception:
        return None


def _midi_schedule(
    timeline: list[tuple[float, float, tuple[int, ...]]], tempo: int
) -> list[tuple[float, str, int]]:
    spq = _tempo_spq(tempo)
    events: list[tuple[float, str, int]] = []
    for off, ql, pitches in timeline:
        t_on = off * spq
        t_off = (off + ql) * spq
        for p in pitches:
            pi = int(p)
            events.append((t_on, "on", pi))
            events.append((t_off, "off", pi))
    events.sort(key=lambda e: (e[0], 0 if e[1] == "on" else 1, e[2]))
    return events


class PlaybackThread(QThread):
    """highlight_row: タイムライン行番号（-1 でハイライト解除）。"""

    highlight_row = pyqtSignal(int)
    mode_changed = pyqtSignal(str)
    finished_playback = pyqtSignal()

    def __init__(self, timeline: list[tuple[float, float, tuple[int, ...]]], tempo: int = 120, parent=None):
        super().__init__(parent)
        self.timeline = timeline
        self.tempo = tempo
        self._marks: list[tuple[int, float, float]] = []

    def _stopped(self) -> bool:
        return self.isInterruptionRequested()

    def _run_highlights_synced(self, marks: list[tuple[int, float, float]], t0: float) -> None:
        for row, start, end in marks:
            if not _sleep_until(t0 + start, self._stopped):
                return
            self.highlight_row.emit(row)
            if not _sleep_until(t0 + end, self._stopped):
                self.highlight_row.emit(-1)
                return
            self.highlight_row.emit(-1)

    def _run_software(self, buf, sr) -> str:
        t0 = time.perf_counter()
        hl = threading.Thread(
            target=self._run_highlights_synced, args=(self._marks, t0), daemon=True
        )
        hl.start()

        mode = "silent"
        if sd is not None:
            try:
                sd.play(buf, sr, blocking=False)
                stream = sd.get_stream()
                while stream and stream.active:
                    if self._stopped():
                        stop_audio_output()
                        break
                    time.sleep(0.02)
                if not self._stopped():
                    mode = "software"
            except Exception:
                stop_audio_output()
        if mode == "silent" and not self._stopped():
            if _play_buffer_winsound_async(buf, sr, self._stopped):
                mode = "wave"

        hl.join(timeout=max(1.0, (self._marks[-1][2] if self._marks else 1.0) + 1.0))
        return mode

    def _run_midi(self, port) -> None:
        events = _midi_schedule(self.timeline, self.tempo)
        wall = 0.0
        t0 = time.perf_counter()
        hl = threading.Thread(
            target=self._run_highlights_synced, args=(self._marks, t0), daemon=True
        )
        hl.start()

        for t_ev, kind, pitch in events:
            if self._stopped():
                break
            if t_ev > wall:
                if not _sleep_until(t0 + t_ev, self._stopped):
                    break
            wall = t_ev
            if kind == "on":
                port.send(mido.Message("note_on", note=pitch, velocity=96))
            else:
                port.send(mido.Message("note_off", note=pitch, velocity=0))

        hl.join(timeout=max(1.0, (self._marks[-1][2] if self._marks else 1.0) + 1.0))

    def run(self) -> None:
        self._marks = build_playback_marks(self.timeline, self.tempo)
        port = _open_mido_port()
        try:
            if port is not None:
                self.mode_changed.emit("midi")
                self._run_midi(port)
            else:
                buf, sr, _ = render_timeline_buffer(self.timeline, self.tempo)
                if buf is None:
                    self.mode_changed.emit("silent")
                else:
                    mode = self._run_software(buf, sr)
                    self.mode_changed.emit(mode if mode != "silent" else "silent")
        finally:
            if port:
                try:
                    for p in range(128):
                        port.send(mido.Message("note_off", note=p, velocity=0))
                    port.close()
                except Exception:
                    pass
            stop_audio_output()
            self.highlight_row.emit(-1)
            self.finished_playback.emit()
