# -*- coding: utf-8 -*-
"""GM プログラムとパート名からの音色割り当て。"""
from __future__ import annotations

# General MIDI プログラム番号（抜粋）
GM_PIANO = 0
GM_BRIGHT_PIANO = 1
GM_ELECTRIC_PIANO = 4
GM_HARPSICHORD = 6
GM_CELESTA = 8
GM_VIBRAPHONE = 11
GM_MARIMBA = 12
GM_ORGAN = 16
GM_GUITAR_NYLON = 24
GM_GUITAR_STEEL = 25
GM_GUITAR_JAZZ = 26
GM_GUITAR_CLEAN = 27
GM_BASS_ACOUSTIC = 32
GM_BASS_FRETLESS = 35
GM_BASS_PICK = 33
GM_VIOLIN = 40
GM_VIOLA = 41
GM_CELLO = 42
GM_STRINGS = 48
GM_STRINGS_SLOW = 52
GM_BRASS = 61
GM_TRUMPET = 56
GM_FLUTE = 73
GM_LEAD = 80
GM_PAD = 88

# パート index が増えるときの既定（トラックごとに別音色）
DEFAULT_PROGRAMS_BY_PART_INDEX = (
    GM_PIANO,
    GM_BASS_PICK,
    GM_STRINGS,
    GM_VIOLIN,
    GM_TRUMPET,
    GM_GUITAR_CLEAN,
    GM_CELLO,
    GM_FLUTE,
    GM_ELECTRIC_PIANO,
    GM_VIBRAPHONE,
    GM_BRASS,
    GM_MARIMBA,
    GM_PAD,
    GM_HARPSICHORD,
    GM_GUITAR_JAZZ,
    GM_ORGAN,
    GM_LEAD,
)

_NAME_KEYWORDS: list[tuple[tuple[str, ...], int]] = [
    (("drum", "kit", "percussion", "perc"), 0),  # ch10 で処理
    (("bass", "bs"), GM_BASS_PICK),
    (("cello", "vc"), GM_CELLO),
    (("viola", "va"), GM_VIOLA),
    (("violin", "vn", "fiddle"), GM_VIOLIN),
    (("string", "str"), GM_STRINGS),
    (("trumpet", "trombone", "horn", "brass"), GM_TRUMPET),
    (("flute", "piccolo", "oboe", "clarinet", "sax"), GM_FLUTE),
    (("guitar", "gtr"), GM_GUITAR_CLEAN),
    (("piano", "pf", "key"), GM_PIANO),
    (("organ", "org"), GM_ORGAN),
    (("synth", "lead"), GM_LEAD),
    (("pad"), GM_PAD),
    (("marimba", "vibe", "mallet"), GM_VIBRAPHONE),
]


def program_from_instrument_name(name: str | None) -> int | None:
    if not name:
        return None
    low = name.lower()
    for keys, prog in _NAME_KEYWORDS:
        if any(k in low for k in keys):
            return prog
    return None


def default_program_for_part(part_index: int) -> int:
    return DEFAULT_PROGRAMS_BY_PART_INDEX[part_index % len(DEFAULT_PROGRAMS_BY_PART_INDEX)]


def program_for_part(part, part_index: int) -> int:
    """music21 Part から GM プログラム番号を推定。"""
    inst = None
    try:
        inst = part.getInstrument(returnDefault=True)
    except Exception:
        inst = None
    if inst is not None:
        mp = getattr(inst, "midiProgram", None)
        if mp is not None:
            return int(mp) % 128
        name = getattr(inst, "instrumentName", None) or getattr(inst, "bestName", None)
        guessed = program_from_instrument_name(str(name) if name else None)
        if guessed is not None:
            return guessed
    return default_program_for_part(part_index)


def is_percussion_channel(channel: int) -> bool:
    return channel == 9


def program_display_name(program: int) -> str:
    names = {
        0: "Piano",
        32: "Bass",
        40: "Violin",
        48: "Strings",
        56: "Trumpet",
        73: "Flute",
    }
    return names.get(program, f"GM {program}")
