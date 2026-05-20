@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo [.venv が見つかりません] python -m venv .venv を先に実行してください。
  pause
  exit /b 1
)
call .venv\Scripts\activate.bat
if exist scripts\build_rust.bat (
  echo [Rust] midi_viz をビルドしています...
  call scripts\build_rust.bat
  if errorlevel 1 (
    echo [警告] Rust ビジュアライザのビルドに失敗しました。ModernGL フォールバックで続行します。
  )
)
python -m pip install -q pyinstaller
python -c "from PIL import Image; im=Image.open('image.png').convert('RGBA'); icons=[im.resize(s, Image.Resampling.LANCZOS) for s in ((256,256),(128,128),(64,64),(48,48),(32,32),(16,16))]; icons[0].save('app.ico', format='ICO', sizes=[(x.width,x.height) for x in icons], append_images=icons[1:])"
if errorlevel 1 (
  echo image.png から app.ico を作成できませんでした。
  pause
  exit /b 1
)
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
