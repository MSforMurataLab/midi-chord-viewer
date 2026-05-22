# -*- coding: utf-8 -*-
"""SoundFont 再生バッファの事前レンダリング。"""
from __future__ import annotations

import logging

from PyQt6.QtCore import QThread, pyqtSignal

log = logging.getLogger(__name__)

from midi_lab.core.midi_controls import ChannelControlChange
from midi_lab.core.note_events import NoteEvent
from midi_lab.core.playback_schedule import build_playback_schedule
from midi_lab.core.soundfont_player import (
    SAMPLE_RATE,
    PlaybackSetupError,
    ensure_playback_ready,
    render_soundfont_buffer,
)


def try_preload_playback_audio(
    note_events: list[NoteEvent],
    harmony_timeline: list[tuple[float, float, tuple[int, ...]]],
    tempo: int,
    stop_check=None,
    channel_controls: list[ChannelControlChange] | None = None,
) -> bool:
    """FluidSynth でレンダリングしキャッシュを温める。未設定時は False。"""
    try:
        ensure_playback_ready()
    except PlaybackSetupError:
        return False

    schedule, channel_programs, controls = build_playback_schedule(
        note_events, harmony_timeline, tempo, channel_controls
    )
    if not schedule:
        return False

    if stop_check and stop_check():
        return False

    try:
        buf, _sr = render_soundfont_buffer(
            schedule,
            channel_programs,
            tempo,
            SAMPLE_RATE,
            stop_check=stop_check,
            channel_controls=controls,
        )
    except PlaybackSetupError as e:
        log.warning("preload skipped: %s", e)
        return False
    except Exception:
        log.exception("preload render failed")
        return False
    return buf is not None


class SoundfontPreloadWorker(QThread):
    """テンポ変更など、ロード後の再プリロード用。"""

    completed = pyqtSignal(bool)

    def __init__(
        self,
        note_events: list[NoteEvent],
        harmony_timeline: list[tuple[float, float, tuple[int, ...]]],
        tempo: int,
        channel_controls: list[ChannelControlChange] | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self._note_events = list(note_events)
        self._harmony_timeline = list(harmony_timeline)
        self._tempo = tempo
        self._channel_controls = list(channel_controls or [])

    def run(self) -> None:
        try:
            ok = try_preload_playback_audio(
                self._note_events,
                self._harmony_timeline,
                self._tempo,
                stop_check=self.isInterruptionRequested,
                channel_controls=self._channel_controls,
            )
        except Exception:
            log.exception("SoundfontPreloadWorker failed")
            ok = False
        if not self.isInterruptionRequested():
            self.completed.emit(ok)
