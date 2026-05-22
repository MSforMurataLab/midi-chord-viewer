# -*- coding: utf-8 -*-
"""再生用ノートスケジュールの構築（再生・プリロード共通）。"""
from __future__ import annotations

from midi_lab.core.note_events import NoteEvent
from midi_lab.core.playback_notes import (
    ScheduledNote,
    build_channel_program_map,
    build_note_schedule,
)
from midi_lab.core.soundfont_player import harmony_timeline_to_schedule


def build_playback_schedule(
    note_events: list[NoteEvent],
    harmony_timeline: list[tuple[float, float, tuple[int, ...]]],
    tempo: int,
) -> tuple[list[ScheduledNote], dict[int, int]]:
    """PlaybackThread と同じ優先順位でスケジュールを構築。"""
    if note_events:
        return (
            build_note_schedule(note_events, tempo),
            build_channel_program_map(note_events),
        )
    if harmony_timeline:
        return harmony_timeline_to_schedule(harmony_timeline, tempo)
    return [], {}
