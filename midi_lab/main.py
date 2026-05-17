# -*- coding: utf-8 -*-
"""アプリケーションエントリポイント — スプラッシュ付き遅延起動。"""
from __future__ import annotations

import sys
import traceback

from midi_lab.bootstrap import bootstrap_frozen

bootstrap_frozen()

# matplotlib バックエンドは必ずメインスレッド・QApplication 直後に設定
import matplotlib

matplotlib.use("QtAgg")

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QApplication, QMessageBox

from midi_lab.diagnostics import log, log_stack
from midi_lab.resources import application_icon
from midi_lab.ui.splash import SPLASH_STYLESHEET, SplashWindow
from midi_lab.ui.theme import APP_STYLESHEET, apply_app_font


def _install_excepthook() -> None:
    def _hook(exc_type, exc, tb):
        text = "".join(traceback.format_exception(exc_type, exc, tb))
        log(f"UNHANDLED:\n{text}")
        try:
            QMessageBox.critical(None, "予期しないエラー", text[:4000])
        except Exception:
            pass

    sys.excepthook = _hook


def _cli_message(title: str, message: str, success: bool) -> None:
    """windowed exe でも結果を表示（コンソールなしビルド向け）。"""
    if sys.platform == "win32":
        try:
            import ctypes

            icon = 0x40 if success else 0x10
            ctypes.windll.user32.MessageBoxW(0, message, title, icon)
            return
        except Exception:
            pass
    print(message)


def _show_startup_error(message: str) -> None:
    log(f"STARTUP ERROR:\n{message}")
    QMessageBox.critical(None, "起動エラー", f"アプリケーションの初期化に失敗しました。\n\n{message[:4000]}")


def run() -> int:
    from midi_lab.core.launch_args import (
        initial_midi_path,
        is_register_association_request,
        is_unregister_association_request,
    )

    if is_register_association_request():
        from midi_lab.core.file_association import register_midi_associations

        ok, msg = register_midi_associations()
        _cli_message("MIDI Chord Lab — 関連付け", msg, ok)
        return 0 if ok else 1

    if is_unregister_association_request():
        from midi_lab.core.file_association import unregister_midi_associations

        ok, msg = unregister_midi_associations()
        _cli_message("MIDI Chord Lab — 関連付け解除", msg, ok)
        return 0 if ok else 1

    pending_midi = initial_midi_path()
    _install_excepthook()
    log(f"--- run start pending_midi={pending_midi!r} ---")

    app = QApplication(sys.argv)
    apply_app_font(app)
    app.setApplicationName("MIDI Chord Lab")
    app.setOrganizationName("MurataLab")
    app.setQuitOnLastWindowClosed(False)

    def _on_about_to_quit() -> None:
        log_stack("aboutToQuit")

    app.aboutToQuit.connect(_on_about_to_quit)

    icon = application_icon()
    if icon is not None:
        app.setWindowIcon(icon)

    splash = SplashWindow()
    splash.setStyleSheet(SPLASH_STYLESHEET)
    app._splash = splash  # type: ignore[attr-defined]

    splash.set_status("グラフィックエンジンを初期化しています…")
    splash.set_progress(10)
    splash.show_centered()

    def _finalize_startup(win) -> None:
        """メイン表示が安定してから全画面化・終了条件を有効化。"""
        from midi_lab.core.settings import fullscreen_default

        if fullscreen_default() and win.isVisible():
            win.showFullScreen()
            win.raise_()
            win.activateWindow()
        app.setQuitOnLastWindowClosed(True)
        log("startup finalize: quitOnLastWindowClosed=True")

    def _launch_main() -> None:
        try:
            splash.set_status("音楽理論エンジン (music21) を読み込んでいます…")
            splash.set_progress(30)
            QApplication.processEvents()

            import music21  # noqa: F401

            splash.set_status("MIDI 再生モジュールを準備しています…")
            splash.set_progress(55)
            QApplication.processEvents()

            import mido  # noqa: F401

            splash.set_status("インターフェースを構築しています…")
            splash.set_progress(75)
            QApplication.processEvents()

            from midi_lab.core.plotting import configure_matplotlib

            configure_matplotlib()

            from midi_lab.ui.main_window import MainWindow

            app.setStyleSheet(APP_STYLESHEET)
            win = MainWindow()
            app._mainWindow = win  # type: ignore[attr-defined]
            if icon is not None:
                win.setWindowIcon(icon)

            win.setAttribute(Qt.WidgetAttribute.WA_QuitOnClose, True)

            # まず最大化で確実に表示（即時全画面は OS/Qt によっては不安定）
            win.show()
            win.showMaximized()
            win.raise_()
            win.activateWindow()
            QApplication.processEvents()

            splash.finish_and_handoff()
            log(f"main window shown visible={win.isVisible()}")

            def _done():
                _finalize_startup(win)
                win._refresh_layout()
                if pending_midi:
                    log(f"opening file from argv: {pending_midi}")
                    win.load_file(pending_midi)

            QTimer.singleShot(400, _done)
        except Exception:
            _show_startup_error(traceback.format_exc())
            splash.hide()

    QTimer.singleShot(0, _launch_main)

    code = app.exec()
    log(f"--- run end code={code} ---")
    return code


if __name__ == "__main__":
    raise SystemExit(run())
