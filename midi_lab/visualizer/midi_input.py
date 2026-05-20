# -*- coding: utf-8 -*-
"""リアルタイム MIDI 入力（mido）。"""
from __future__ import annotations

import traceback

from PyQt6.QtCore import QThread, pyqtSignal

try:
    import mido
except ImportError:
    mido = None  # type: ignore


def list_input_ports() -> list[str]:
    if mido is None:
        return []
    try:
        return list(mido.get_input_names())
    except Exception:
        return []


class MidiInputWorker(QThread):
    note_on = pyqtSignal(int, int, int)  # midi, velocity, channel
    note_off = pyqtSignal(int, int)
    sustain = pyqtSignal(bool)
    failed = pyqtSignal(str)

    def __init__(self, port_name: str, parent=None):
        super().__init__(parent)
        self._port_name = port_name
        self._port = None

    def run(self) -> None:
        if mido is None:
            self.failed.emit("mido が利用できません。")
            return
        try:
            self._port = mido.open_input(self._port_name)
            while not self.isInterruptionRequested():
                for msg in self._port.iter_pending():
                    if self.isInterruptionRequested():
                        break
                    if msg.type == "note_on":
                        vel = getattr(msg, "velocity", 0)
                        if vel > 0:
                            self.note_on.emit(msg.note, vel, getattr(msg, "channel", 0))
                        else:
                            self.note_off.emit(msg.note, getattr(msg, "channel", 0))
                    elif msg.type == "note_off":
                        self.note_off.emit(msg.note, getattr(msg, "channel", 0))
                    elif msg.type == "control_change" and msg.control == 64:
                        self.sustain.emit(msg.value >= 64)
                self.msleep(5)
        except Exception:
            self.failed.emit(traceback.format_exc())
        finally:
            if self._port is not None:
                try:
                    self._port.close()
                except Exception:
                    pass
                self._port = None
