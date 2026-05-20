@echo off
setlocal
cd /d "%~dp0.."
if exist "%ProgramFiles%\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" (
  call "%ProgramFiles%\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
)
set PATH=%USERPROFILE%\.cargo\bin;%PATH%
call .venv\Scripts\activate.bat
maturin develop --release --manifest-path rust\midi_viz\Cargo.toml
exit /b %ERRORLEVEL%
