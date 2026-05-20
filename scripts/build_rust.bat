@echo off
setlocal
cd /d "%~dp0.."
if exist "%ProgramFiles%\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" (
  call "%ProgramFiles%\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
)
set PATH=%USERPROFILE%\.cargo\bin;%PATH%
where rustc >nul 2>&1 || (
  echo [エラー] Rust が未インストールです: https://rustup.rs/
  exit /b 1
)
where maturin >nul 2>&1 || (
  echo maturin をインストールしています...
  .venv\Scripts\pip.exe install maturin
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_maturin.ps1"
if errorlevel 1 exit /b 1
echo.
echo 完了: midi_viz モジュールが .venv にインストールされました。

