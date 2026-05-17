@echo off
setlocal
cd /d "%~dp0.."
set "EXE=dist\MIDIChordViewer\MIDIChordViewer.exe"
if not exist "%EXE%" (
  echo [エラー] 先に build.bat でビルドしてください: %EXE%
  pause
  exit /b 1
)
"%EXE%" --register-midi-association
pause
