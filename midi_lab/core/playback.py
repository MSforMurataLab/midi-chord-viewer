# -*- coding: utf-8 -*-
"""MIDI 再生 — SoundFont（FluidSynth）のみ。"""
from __future__ import annotations

import sys
import tempfile
import time
import wave
from pathlib import Path
from typing import TYPE_CHECKING

from PyQt6.QtCore import QThread, pyqtSignal

from midi_lab.core.playback_notes import (
    midi_events_from_schedule,
    schedule_duration_sec,
)
from midi_lab.core.playback_schedule import build_playback_schedule
from midi_lab.core.soundfont_player import (
    PlaybackSetupError,
    is_render_cached,
    render_soundfont_buffer,
)

if TYPE_CHECKING:
    from midi_lab.core.note_events import NoteEvent

try:
    import numpy as np
except ImportError:
    np = None  # type: ignore

try:
    import sounddevice as sd
except ImportError:
    sd = None  # type: ignore

SAMPLE_RATE = 44100
_TICK_SLEEP = 0.02


def stop_audio_output() -> None:
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


def build_playback_marks(
    timeline: list[tuple[float, float, tuple[int, ...]]],
    tempo: int,
) -> list[tuple[int, float, float]]:
    spq = _tempo_spq(tempo)
    marks: list[tuple[int, float, float]] = []
    for row, (off, ql, pitches) in enumerate(timeline):
        if not pitches:
            continue
        start = off * spq
        end = (off + ql) * spq
        marks.append((row, start, end))
    return marks


def _active_harmony_row(marks: list[tuple[int, float, float]], t_sec: float) -> int:
    for row, start, end in marks:
        if start <= t_sec < end:
            return row
    return -1


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
            time.sleep(_TICK_SLEEP)
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass
        return True
    except Exception:
        return False


class PlaybackThread(QThread):
    highlight_row = pyqtSignal(int)
    position_changed = pyqtSignal(float)
    mode_changed = pyqtSignal(str)
    finished_playback = pyqtSignal()
    setup_error = pyqtSignal(str)
    preparing = pyqtSignal(bool)
    midi_message = pyqtSignal(int, int, int)

    def __init__(
        self,
        harmony_timeline: list[tuple[float, float, tuple[int, ...]]],
        tempo: int = 120,
        note_events: list[NoteEvent] | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self.harmony_timeline = harmony_timeline
        self.note_events = list(note_events) if note_events else []
        self.tempo = tempo
        self._marks: list[tuple[int, float, float]] = []
        self._note_schedule: list = []
        self._channel_programs: dict[int, int] = {}
        self._render_proc = None

        self._note_schedule, self._channel_programs = build_playback_schedule(
            self.note_events,
            self.harmony_timeline,
            tempo,
        )

    def _stopped(self) -> bool:
        return self.isInterruptionRequested()

    def request_stop(self) -> None:
        """UI からの停止 — レンダリング subprocess も打ち切る。"""
        self.requestInterruption()
        stop_audio_output()
        proc = self._render_proc
        if proc is not None and proc.poll() is None:
            try:
                proc.kill()
            except Exception:
                pass

    def _playback_duration(self) -> float:
        if self._note_schedule:
            return schedule_duration_sec(self._note_schedule)
        if self._marks:
            return self._marks[-1][2]
        return 0.0

    def _start_audio(self, buf, sr: int) -> str:
        if sd is not None:
            try:
                sd.play(buf, sr, blocking=False)
                return "soundfont"
            except Exception:
                stop_audio_output()
        if _play_buffer_winsound_async(buf, sr, self._stopped):
            return "wave"
        return "silent"

    def _audio_still_playing(self) -> bool:
        if sd is None:
            return False
        try:
            stream = sd.get_stream()
            return bool(stream and stream.active)
        except Exception:
            return False

    def _run_playback_loop(self, duration: float, midi_events: list) -> None:
        """音声・ハイライト・ビジュアライザを単一ループで同期（停止可能）。"""
        t0 = time.perf_counter()
        active_row = -2
        midi_idx = 0
        mode = "silent"

        while not self._stopped():
            t = time.perf_counter() - t0
            if t >= duration:
                self.position_changed.emit(duration)
                break

            self.position_changed.emit(t)

            if self._marks:
                row = _active_harmony_row(self._marks, t)
                if row != active_row:
                    active_row = row
                    self.highlight_row.emit(row)

            while midi_idx < len(midi_events) and midi_events[midi_idx][0] <= t:
                _, kind, pitch, vel, ch = midi_events[midi_idx]
                midi_idx += 1
                if self._stopped():
                    break
                if kind == "on":
                    self.midi_message.emit(0x90 | ch, pitch, vel)
                else:
                    self.midi_message.emit(0x80 | ch, pitch, 0)

            if mode == "soundfont" and not self._audio_still_playing():
                break

            time.sleep(_TICK_SLEEP)

        if active_row >= 0:
            self.highlight_row.emit(-1)
        self.position_changed.emit(-1.0)

    def _run_timeline_only(self, duration: float) -> None:
        midi_events = (
            midi_events_from_schedule(self._note_schedule) if self._note_schedule else []
        )
        self._run_playback_loop(duration, midi_events)

    def run(self) -> None:
        self._marks = build_playback_marks(self.harmony_timeline, self.tempo)
        duration = self._playback_duration()
        mode = "silent"

        try:
            if not self._note_schedule:
                self.mode_changed.emit("silent")
                if self._marks or duration > 0:
                    self._run_timeline_only(duration)
                return

            need_render = not is_render_cached(
                self._note_schedule, self._channel_programs, self.tempo, SAMPLE_RATE
            )
            if need_render:
                self.preparing.emit(True)
            buf, sr = render_soundfont_buffer(
                self._note_schedule,
                self._channel_programs,
                self.tempo,
                SAMPLE_RATE,
                stop_check=self._stopped,
                render_proc_holder=lambda p: setattr(self, "_render_proc", p),
            )
            if need_render:
                self.preparing.emit(False)

            if self._stopped():
                return

            if buf is None:
                self.setup_error.emit("SoundFont レンダリング結果が空です。")
                self._run_timeline_only(duration)
                return

            midi_events = midi_events_from_schedule(self._note_schedule)
            mode = self._start_audio(buf, sr)
            if mode != "silent":
                self.mode_changed.emit(mode)
            self._run_playback_loop(duration, midi_events)

        except PlaybackSetupError as e:
            self.preparing.emit(False)
            self.setup_error.emit(str(e))
            if not self._stopped() and (self._marks or duration > 0):
                self._run_timeline_only(duration)
        finally:
            self.preparing.emit(False)
            stop_audio_output()
            self.highlight_row.emit(-1)
            self.position_changed.emit(-1.0)
            if mode != "silent":
                self.mode_changed.emit("silent")
            self.finished_playback.emit()
