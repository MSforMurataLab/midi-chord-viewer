@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "DIST_EXE=dist\MIDIChordViewer\MIDIChordViewer.exe"
if not exist "%DIST_EXE%" (
  echo [エラー] %DIST_EXE% がありません。
  echo 先に build.bat で PyInstaller ビルドを実行してください。
  pause
  exit /b 1
)

if not exist "app.ico" (
  echo [エラー] app.ico がありません。build.bat を実行してアイコンを生成してください。
  pause
  exit /b 1
)

set "ISCC="
where iscc >nul 2>&1 && set "ISCC=iscc"
if not defined ISCC if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not defined ISCC if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"

if not defined ISCC (
  echo [エラー] Inno Setup 6 ^(ISCC.exe^) が見つかりません。
  echo.
  echo 1. https://jrsoftware.org/isdl.php から Inno Setup 6 をインストール
  echo 2. インストール時に「Inno Setup Preprocessor」にチェック
  echo 3. このバッチを再実行
  echo.
  pause
  exit /b 1
)

if not exist "dist\installer" mkdir "dist\installer"

echo Inno Setup でインストーラーをビルドしています...
"%ISCC%" "installer\midi_chord_lab.iss"
if errorlevel 1 (
  echo インストーラーのビルドに失敗しました。
  pause
  exit /b 1
)

echo.
echo 完了: dist\installer\ 内の MIDIChordLab_Setup_*.exe を配布できます。
explorer dist\installer
pause
