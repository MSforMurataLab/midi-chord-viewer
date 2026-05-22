# PyInstaller: pyi_rth_pyqt6 の後に PATH を並べ替え（_internal 単独先頭を避ける）
import os
import sys


def _pyi_rthook() -> None:
    if not getattr(sys, "frozen", False) or not sys.platform.startswith("win"):
        return

    meipass = getattr(sys, "_MEIPASS", "")
    if not meipass:
        return

    qt_bin = os.path.join(meipass, "PyQt6", "Qt6", "bin")
    if not os.path.isdir(qt_bin):
        return

    blocked = {os.path.normcase(meipass), os.path.normcase(qt_bin)}
    rest = [
        p
        for p in os.environ.get("PATH", "").split(os.pathsep)
        if p and os.path.normcase(p) not in blocked
    ]
    os.environ["PATH"] = os.pathsep.join([qt_bin, meipass, *rest])


_pyi_rthook()
del _pyi_rthook
