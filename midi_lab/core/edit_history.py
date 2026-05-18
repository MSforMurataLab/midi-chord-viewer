# -*- coding: utf-8 -*-
"""タイムライン編集の Undo / Redo（行ラベル + 音価長スナップショット）。"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TimelineSnapshot:
    rows: tuple[tuple[float, str], ...]
    row_ql: tuple[float, ...]


class EditHistory:
    def __init__(self, max_depth: int = 64) -> None:
        self._max = max_depth
        self._undo: list[TimelineSnapshot] = []
        self._redo: list[TimelineSnapshot] = []

    def clear(self) -> None:
        self._undo.clear()
        self._redo.clear()

    def can_undo(self) -> bool:
        return bool(self._undo)

    def can_redo(self) -> bool:
        return bool(self._redo)

    def push(self, rows: list[tuple[float, str]], row_ql: list[float]) -> None:
        snap = TimelineSnapshot(tuple(rows), tuple(row_ql))
        if self._undo and self._undo[-1] == snap:
            return
        self._undo.append(snap)
        if len(self._undo) > self._max:
            self._undo.pop(0)
        self._redo.clear()

    def undo(self, current: TimelineSnapshot) -> TimelineSnapshot | None:
        if not self._undo:
            return None
        self._redo.append(current)
        return self._undo.pop()

    def redo(self, current: TimelineSnapshot) -> TimelineSnapshot | None:
        if not self._redo:
            return None
        self._undo.append(current)
        return self._redo.pop()
