$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $root

& "$root\scripts\run_maturin.ps1"
if ($LASTEXITCODE -ne 0) {
    Write-Warning "Rust build failed; continuing with ModernGL fallback only."
}

& "$root\.venv\Scripts\pip.exe" install -q pyinstaller
& "$root\.venv\Scripts\python.exe" -c @"
from PIL import Image
im = Image.open('image.png').convert('RGBA')
icons = [im.resize(s, Image.Resampling.LANCZOS) for s in ((256,256),(128,128),(64,64),(48,48),(32,32),(16,16))]
icons[0].save('app.ico', format='ICO', sizes=[(x.width,x.height) for x in icons], append_images=icons[1:])
"@

& "$root\.venv\Scripts\pyinstaller.exe" --noconfirm midi_chord_viewer.spec
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$iscc = $null
if (Get-Command iscc -ErrorAction SilentlyContinue) { $iscc = "iscc" }
elseif (Test-Path "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe") { $iscc = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe" }
elseif (Test-Path "$env:ProgramFiles\Inno Setup 6\ISCC.exe") { $iscc = "$env:ProgramFiles\Inno Setup 6\ISCC.exe" }

if ($iscc) {
    New-Item -ItemType Directory -Force -Path dist\installer | Out-Null
    & $iscc "installer\midi_chord_lab.iss"
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    Write-Host "Installer: dist\installer\MIDIChordLab_Setup_2.14.0.exe"
} else {
    Write-Warning "Inno Setup not found; skipped installer. dist\MIDIChordViewer\MIDIChordViewer.exe is ready."
}

Write-Host "Done: dist\MIDIChordViewer\MIDIChordViewer.exe"
