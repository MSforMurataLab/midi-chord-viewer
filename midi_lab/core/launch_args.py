# -*- coding: utf-8 -*-
"""起動引数の解析（ファイルを開いて起動・関連付け登録）。"""
from __future__ import annotations

import sys
from pathlib import Path

MIDI_SUFFIXES = {".mid", ".midi"}

REGISTER_FLAG = "--register-midi-association"
UNREGISTER_FLAG = "--unregister-midi-association"


def is_register_association_request(argv: list[str] | None = None) -> bool:
    return REGISTER_FLAG in (argv if argv is not None else sys.argv)


def is_unregister_association_request(argv: list[str] | None = None) -> bool:
    return UNREGISTER_FLAG in (argv if argv is not None else sys.argv)


def midi_paths_from_argv(argv: list[str] | None = None) -> list[Path]:
    """コマンドラインから .mid / .midi ファイルパスを抽出。"""
    args = argv if argv is not None else sys.argv[1:]
    paths: list[Path] = []
    for arg in args:
        if not arg or arg.startswith("-"):
            continue
        raw = arg.strip().strip('"')
        if not raw:
            continue
        p = Path(raw)
        try:
            p = p.expanduser().resolve()
        except OSError:
            p = Path(raw)
        if p.suffix.lower() in MIDI_SUFFIXES and p.is_file():
            paths.append(p)
    return paths


def initial_midi_path(argv: list[str] | None = None) -> str | None:
    paths = midi_paths_from_argv(argv)
    return str(paths[0]) if paths else None
