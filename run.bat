@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo .venv がありません。README のセットアップを実行してください。
  pause
  exit /b 1
)
".venv\Scripts\python.exe" app.py %*
