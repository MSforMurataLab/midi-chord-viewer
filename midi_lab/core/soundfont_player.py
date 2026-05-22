# -*- coding: utf-8 -*-
"""再生エンジン — FluidSynth + SoundFont のみ。"""
from __future__ import annotations

import logging
import os
import subprocess
import sys
import tempfile
import time
import wave
from dataclasses import dataclass
from pathlib import Path

from midi_lab.core.note_events import NoteEvent
from midi_lab.core.playback_notes import (
    ScheduledNote,
    build_channel_program_map,
    build_note_schedule,
    schedule_duration_sec,
)
from midi_lab.core.settings import selected_soundfont, set_selected_soundfont
from midi_lab.core.soundfont_midi import write_schedule_midi_temp

log = logging.getLogger(__name__)

SAMPLE_RATE = 44100
_RENDER_CACHE: dict[tuple, tuple] = {}
_RENDER_CACHE_MAX = 4


class PlaybackSetupError(RuntimeError):
    """FluidSynth または SoundFont が未配置。"""


def _install_dir() -> Path:
    """配布版: exe と同じフォルダ（_internal ではない）。"""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def _bundle_assets_root() -> Path:
    """SoundFont / FluidSynth の同梱 assets ルート。"""
    if getattr(sys, "frozen", False):
        side = _install_dir() / "assets"
        if side.is_dir():
            return side
        return Path(sys._MEIPASS) / "assets"  # type: ignore[attr-defined]
    return Path(__file__).resolve().parents[2] / "assets"


def _fluidsynth_bin_dirs() -> list[Path]:
    env = os.environ.get("FLUIDSYNTH_BIN", "").strip()
    dirs: list[Path] = []
    if env:
        dirs.append(Path(env))
    dirs.append(_bundle_assets_root() / "fluidsynth" / "bin")
    if not getattr(sys, "frozen", False):
        dirs.insert(0, Path(__file__).resolve().parents[2] / "assets" / "fluidsynth" / "bin")
    dirs.append(Path(r"C:\tools\fluidsynth\bin"))
    out: list[Path] = []
    for d in dirs:
        if d.is_dir():
            out.append(d)
    return out


def resolve_fluidsynth_exe() -> Path | None:
    for d in _fluidsynth_bin_dirs():
        for name in ("fluidsynth.exe", "fluidsynth"):
            p = d / name
            if p.is_file():
                return p.resolve()
    from shutil import which

    w = which("fluidsynth")
    return Path(w).resolve() if w else None


def _soundfonts_root() -> Path:
    return _bundle_assets_root() / "soundfonts"


@dataclass(frozen=True)
class SoundFontChoice:
    """UI 用 — key は設定保存用（相対パス POSIX または絶対パス）。"""

    key: str
    path: Path
    label: str


def soundfont_label(path: Path, root: Path | None = None) -> str:
    root = root or _soundfonts_root()
    try:
        rel = path.resolve().relative_to(root.resolve())
        if len(rel.parts) >= 2 and Path(rel.parts[-1]).stem.lower() == rel.parts[-2].lower():
            base = rel.parts[-2]
        else:
            base = Path(rel.parts[-1]).stem if rel.parts else path.stem
    except ValueError:
        base = path.stem
    return base.replace("_", " ").replace("-", " ")


def key_to_soundfont_path(key: str) -> Path | None:
    key = key.strip()
    if not key:
        return None
    p = Path(key)
    if p.is_file() and p.suffix.lower() == ".sf2":
        return p.resolve()
    bundled = _soundfonts_root() / key.replace("/", os.sep)
    if bundled.is_file():
        return bundled.resolve()
    return None


def iter_soundfont_files(root: Path | None = None) -> list[Path]:
    """soundfonts 以下のすべての .sf2（大文字小文字無視、再帰）。"""
    root = (root or _soundfonts_root()).resolve()
    if not root.is_dir():
        return []
    found: list[Path] = []
    for p in root.rglob("*"):
        if p.is_file() and p.suffix.lower() == ".sf2":
            found.append(p.resolve())
    found.sort(key=lambda x: path_to_soundfont_key(x, root).casefold())
    return found


def path_to_soundfont_key(path: Path, root: Path | None = None) -> str:
    root = (root or _soundfonts_root()).resolve()
    try:
        rel = path.resolve().relative_to(root)
        return rel.as_posix()
    except ValueError:
        return str(path.resolve())


def _display_labels_for_soundfonts(
    paths: list[Path], root: Path
) -> dict[Path, str]:
    """同名表示の衝突時は相対パスをラベルに使う。"""
    base_labels = {p: soundfont_label(p, root) for p in paths}
    counts: dict[str, int] = {}
    for lbl in base_labels.values():
        counts[lbl] = counts.get(lbl, 0) + 1
    out: dict[Path, str] = {}
    for p, lbl in base_labels.items():
        if counts[lbl] > 1:
            rel = path_to_soundfont_key(p, root).replace("/", " / ")
            out[p] = rel.replace("_", " ").replace("-", " ")
        else:
            out[p] = lbl
    return out


def enumerate_soundfont_choices() -> list[SoundFontChoice]:
    """assets/soundfonts 以下の .sf2 をすべて列挙（表示名の昇順）。"""
    root = _soundfonts_root()
    if not root.is_dir():
        return []
    paths = iter_soundfont_files(root)
    labels = _display_labels_for_soundfonts(paths, root.resolve())
    choices: list[SoundFontChoice] = []
    seen: set[str] = set()
    for resolved in paths:
        key = path_to_soundfont_key(resolved, root)
        if key in seen:
            continue
        seen.add(key)
        choices.append(
            SoundFontChoice(
                key=key,
                path=resolved,
                label=labels[resolved],
            )
        )
    choices.sort(key=lambda c: c.label.casefold())
    return choices


def _preferred_soundfont_choice(choices: list[SoundFontChoice]) -> SoundFontChoice:
    """同梱の GeneralUser-GS を優先（アルファベット順の先頭を避ける）。"""
    for c in choices:
        if "generaluser" in c.key.casefold():
            return c
    return choices[0]


def discover_bundled_soundfonts() -> list[Path]:
    return [c.path for c in enumerate_soundfont_choices()]


def invalidate_render_cache() -> None:
    _RENDER_CACHE.clear()


def resolve_soundfont_path() -> Path | None:
    sel = selected_soundfont()
    if sel:
        p = key_to_soundfont_path(sel)
        if p is not None:
            return p

    env_sf = os.environ.get("MIDI_LAB_SOUNDFONT", "").strip()
    if env_sf:
        p = Path(env_sf)
        if p.is_file() and p.suffix.lower() == ".sf2":
            return p.resolve()

    choices = enumerate_soundfont_choices()
    if choices:
        return _preferred_soundfont_choice(choices).path

    legacy = Path.home() / "SoundFonts" / "default.sf2"
    if legacy.is_file():
        return legacy.resolve()
    return None


def apply_soundfont_selection(key: str) -> Path | None:
    """選択を保存しレンダキャッシュを破棄。有効なら解決パスを返す。"""
    set_selected_soundfont(key)
    invalidate_render_cache()
    return resolve_soundfont_path()


def ensure_playback_ready() -> tuple[Path, Path]:
    """再生に必要なバイナリを検証し、(fluidsynth_exe, sf2) を返す。"""
    exe = resolve_fluidsynth_exe()
    sf2 = resolve_soundfont_path()
    if exe is None:
        raise PlaybackSetupError(
            "FluidSynth が見つかりません。\n"
            "powershell -ExecutionPolicy Bypass -File scripts/setup_soundfont.ps1\n"
            "を実行するか、FLUIDSYNTH_BIN 環境変数で bin フォルダを指定してください。"
        )
    if sf2 is None:
        raise PlaybackSetupError(
            "SoundFont (.sf2) が見つかりません。\n"
            "assets/soundfonts/GeneralUser-GS/GeneralUser-GS.sf2 を配置するか、"
            "設定ダイアログで .sf2 ファイルを指定してください。"
        )
    return exe, sf2


def playback_status_message() -> str:
    try:
        _, sf2 = ensure_playback_ready()
        return f"再生: SoundFont ({sf2.name})"
    except PlaybackSetupError as e:
        return f"再生: 未準備 — {e.args[0].split(chr(10))[0]}"


def _render_via_cli(
    sf2: Path,
    midi_path: Path,
    wav_path: Path,
    duration_sec: float,
    sample_rate: int = SAMPLE_RATE,
    stop_check=None,
    render_proc_holder=None,
) -> bool:
    exe = resolve_fluidsynth_exe()
    if exe is None:
        return False
    cmd = [
        str(exe),
        "-ni",
        "-F",
        str(wav_path),
        "-r",
        str(sample_rate),
        "-g",
        "0.9",
        str(sf2),
        str(midi_path),
    ]
    env = os.environ.copy()
    fs_dir = str(exe.parent)
    env["PATH"] = fs_dir + os.pathsep + env.get("PATH", "")
    flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    try:
        proc = subprocess.Popen(
            cmd,
            cwd=fs_dir,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            creationflags=flags,
        )
        if render_proc_holder is not None:
            render_proc_holder(proc)
        deadline = time.perf_counter() + max(60.0, duration_sec + 30.0)
        while proc.poll() is None:
            if stop_check and stop_check():
                proc.kill()
                return False
            if time.perf_counter() > deadline:
                proc.kill()
                log.warning("fluidsynth timed out")
                return False
            time.sleep(0.05)
        if proc.returncode != 0:
            err = proc.stderr.read().decode("utf-8", errors="replace") if proc.stderr else ""
            log.warning(
                "fluidsynth exit %s: %s",
                proc.returncode,
                err[:800] or "(no stderr)",
            )
            return False
        if not wav_path.is_file() or wav_path.stat().st_size <= 44:
            log.warning("fluidsynth produced empty or missing wav: %s", wav_path)
            return False
        return True
    except Exception as exc:
        log.warning("fluidsynth: %s", exc)
        return False
    finally:
        if render_proc_holder is not None:
            render_proc_holder(None)


def _read_wav_mono(path: Path):
    import numpy as np

    with wave.open(str(path), "rb") as wf:
        ch = wf.getnchannels()
        sr = wf.getframerate()
        sw = wf.getsampwidth()
        n = wf.getnframes()
        raw = wf.readframes(n)
    if sw != 2:
        return None, sr
    data = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    if ch == 2:
        data = data.reshape(-1, 2).mean(axis=1)
    elif ch > 1:
        data = data.reshape(-1, ch).mean(axis=1)
    peak = float(np.max(np.abs(data))) if len(data) else 0.0
    if peak > 0.98:
        data *= 0.98 / peak
    return data, sr


def is_render_cached(
    schedule: list[ScheduledNote],
    channel_programs: dict[int, int],
    tempo: int,
    sample_rate: int = SAMPLE_RATE,
) -> bool:
    if not schedule:
        return False
    return _schedule_cache_key(schedule, channel_programs, tempo, sample_rate) in _RENDER_CACHE


def _schedule_cache_key(
    schedule: list[ScheduledNote],
    channel_programs: dict[int, int],
    tempo: int,
    sample_rate: int,
) -> tuple:
    notes = tuple(
        (round(n.time_on, 4), round(n.time_off, 4), n.midi, n.velocity, n.channel, n.program)
        for n in schedule[:5000]
    )
    progs = tuple(sorted(channel_programs.items()))
    return (notes, progs, tempo, sample_rate, str(resolve_soundfont_path()))


def render_soundfont_buffer(
    schedule: list[ScheduledNote],
    channel_programs: dict[int, int],
    tempo: int,
    sample_rate: int = SAMPLE_RATE,
    stop_check=None,
    render_proc_holder=None,
):
    """スケジュールを SoundFont でレンダリング（モノラル float32）。"""
    ensure_playback_ready()
    if not schedule:
        return None, sample_rate

    if stop_check and stop_check():
        return None, sample_rate

    cache_key = _schedule_cache_key(schedule, channel_programs, tempo, sample_rate)
    cached = _RENDER_CACHE.get(cache_key)
    if cached is not None:
        return cached

    sf2 = resolve_soundfont_path()
    assert sf2 is not None

    duration_sec = schedule_duration_sec(schedule)
    midi_tmp: Path | None = None
    wav_tmp: Path | None = None
    try:
        midi_tmp = write_schedule_midi_temp(schedule, channel_programs, tempo)
        fd, wav_name = tempfile.mkstemp(suffix=".wav", prefix="midi_lab_sf_")
        os.close(fd)
        wav_tmp = Path(wav_name)

        if _render_via_cli(
            sf2,
            midi_tmp,
            wav_tmp,
            duration_sec,
            sample_rate,
            stop_check=stop_check,
            render_proc_holder=render_proc_holder,
        ):
            if stop_check and stop_check():
                return None, sample_rate
            buf, sr = _read_wav_mono(wav_tmp)
            if buf is not None:
                result = (buf, sr)
                if len(_RENDER_CACHE) >= _RENDER_CACHE_MAX:
                    _RENDER_CACHE.pop(next(iter(_RENDER_CACHE)))
                _RENDER_CACHE[cache_key] = result
                return result
        if stop_check and stop_check():
            return None, sample_rate
        log.warning(
            "SoundFont render failed (sf2=%s, notes=%d, duration=%.1fs)",
            sf2.name,
            len(schedule),
            duration_sec,
        )
        return None, sample_rate
    finally:
        for p in (midi_tmp, wav_tmp):
            if p is not None:
                try:
                    p.unlink(missing_ok=True)
                except OSError:
                    pass


def render_soundfont_for_events(
    events: list[NoteEvent],
    tempo: int,
    sample_rate: int = SAMPLE_RATE,
):
    if not events:
        return None, sample_rate
    schedule = build_note_schedule(events, tempo)
    ch_prog = build_channel_program_map(events)
    return render_soundfont_buffer(schedule, ch_prog, tempo, sample_rate)


def harmony_timeline_to_schedule(
    timeline: list[tuple[float, float, tuple[int, ...]]],
    tempo: int,
) -> tuple[list[ScheduledNote], dict[int, int]]:
    """和声タイムライン（コード行）を SoundFont 用スケジュールへ。"""
    from midi_lab.core.instruments import GM_PIANO

    spq = 60.0 / float(max(40, min(220, tempo)))
    out: list[ScheduledNote] = []
    for off, ql, pitches in timeline:
        if not pitches:
            continue
        t_on = float(off) * spq
        t_off = float(off + max(ql, 0.04)) * spq
        for p in pitches:
            out.append(
                ScheduledNote(
                    time_on=t_on,
                    time_off=t_off,
                    midi=int(p) % 128,
                    velocity=96,
                    channel=0,
                    program=GM_PIANO,
                )
            )
    out.sort(key=lambda n: (n.time_on, n.channel, n.midi))
    return out, {0: GM_PIANO}
