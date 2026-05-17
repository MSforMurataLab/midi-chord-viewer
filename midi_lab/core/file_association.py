# -*- coding: utf-8 -*-
"""Windows: .mid / .midi を MIDI Chord Lab で開く関連付け（HKCU）。"""
from __future__ import annotations

import sys
from pathlib import Path

PROG_ID = "MIDIChordLab.midi"
APP_NAME = "MIDIChordLab"
DESCRIPTION = "MIDI ファイル (MIDI Chord Lab)"


def _exe_path() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve()
    return Path(sys.argv[0]).resolve()


def _set_hkcu(key: str, value: str, value_name: str = "") -> None:
    import winreg

    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key) as k:
        winreg.SetValueEx(k, value_name, 0, winreg.REG_SZ, value)


def _delete_hkcu_tree(key: str) -> None:
    import winreg

    try:
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, key)
    except FileNotFoundError:
        pass
    except OSError:
        # 子キーがある場合は深い順で削除
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key) as parent:
                while True:
                    try:
                        child = winreg.EnumKey(parent, 0)
                        _delete_hkcu_tree(f"{key}\\{child}")
                    except OSError:
                        break
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, key)
        except OSError:
            pass


def register_midi_associations(exe: Path | None = None) -> tuple[bool, str]:
    """現在ユーザー向けに .mid / .midi の関連付けを登録。"""
    if sys.platform != "win32":
        return False, "ファイル関連付けは Windows でのみ利用できます。"

    exe = (exe or _exe_path()).resolve()
    if not exe.is_file():
        return False, f"実行ファイルが見つかりません: {exe}"

    exe_str = str(exe)
    command = f'"{exe_str}" "%1"'
    icon = f'"{exe_str}",0'
    app_key = f"Software\\Classes\\Applications\\{exe.name}"

    try:
        _set_hkcu(f"{app_key}\\shell\\open\\command", command)
        _set_hkcu(f"Software\\Classes\\{PROG_ID}", DESCRIPTION)
        _set_hkcu(f"Software\\Classes\\{PROG_ID}\\DefaultIcon", icon)
        _set_hkcu(f"Software\\Classes\\{PROG_ID}\\shell\\open\\command", command)

        for ext in (".mid", ".midi"):
            _set_hkcu(f"Software\\Classes\\{ext}", PROG_ID)

        # 「プログラムから開く」一覧用
        for ext in ("mid", "midi"):
            _set_hkcu(
                f"Software\\Classes\\{ext}\\OpenWithList\\{exe.name}",
                exe.name,
            )

        return (
            True,
            "登録しました。\n"
            f"実行ファイル: {exe_str}\n\n"
            "エクスプローラーで .mid / .midi を右クリック →「プログラムから開く」→ "
            "MIDI Chord Lab を選ぶと、このアプリで開けます。\n"
            "（常にこのアプリで開くには「常に」を選択）",
        )
    except OSError as e:
        return False, f"レジストリへの書き込みに失敗しました:\n{e}"


def unregister_midi_associations() -> tuple[bool, str]:
    if sys.platform != "win32":
        return False, "Windows でのみ利用できます。"

    try:
        for ext in (".mid", ".midi"):
            try:
                import winreg

                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, f"Software\\Classes\\{ext}") as k:
                    val, _ = winreg.QueryValueEx(k, "")
                if val == PROG_ID:
                    winreg.DeleteKey(winreg.HKEY_CURRENT_USER, f"Software\\Classes\\{ext}")
            except OSError:
                pass

        _delete_hkcu_tree(f"Software\\Classes\\{PROG_ID}")
        return True, "関連付けを解除しました（.mid / .midi）。"
    except OSError as e:
        return False, f"解除に失敗しました:\n{e}"
