@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo [.venv が見つかりません] python -m venv .venv を先に実行してください。
  pause
  exit /b 1
)
call .venv\Scripts\activate.bat
python -m pip install -q pyinstaller
pyinstaller --noconfirm midi_chord_viewer.spec
if errorlevel 1 (
  echo ビルドに失敗しました。
  pause
  exit /b 1
)
echo.
echo 完了: dist\MIDIChordViewer\MIDIChordViewer.exe をダブルクリックで起動できます。
explorer dist\MIDIChordViewer
pause
