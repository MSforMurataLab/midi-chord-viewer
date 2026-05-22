$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $root

# Keep Anaconda off PATH so PyInstaller does not bundle ICU 73 (breaks Qt6Core)
if ($env:PATH) {
    $clean = @()
    foreach ($p in $env:PATH -split ';') {
        if ($p -and $p -notmatch 'anaconda|conda|miniconda') { $clean += $p }
    }
    $env:PATH = $clean -join ';'
}

if ($env:CONDA_PREFIX -and $env:VIRTUAL_ENV) {
    Remove-Item Env:CONDA_PREFIX -ErrorAction SilentlyContinue
}
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

& "$root\.venv\Scripts\pyinstaller.exe" --noconfirm --clean midi_chord_viewer.spec
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

# FluidSynth DLL を _internal 外へ（PyInstaller が PATH に _internal を載せるため Qt と競合しうる）
# NOTE: 変数名に $ を連続させない（Git Bash 経由だと $dist が展開される）
$distDir = Join-Path $root "dist\MIDIChordViewer"
$assetsInternal = Join-Path $distDir "_internal\assets"
$assetsSide = Join-Path $distDir "assets"
if (Test-Path $assetsInternal) {
    if (Test-Path $assetsSide) {
        Remove-Item -Recurse -Force $assetsSide
    }
    Move-Item -Force $assetsInternal $assetsSide
    Write-Host "Moved assets -> $assetsSide (outside _internal)"
}

# Qt6*.dll を PyQt6 直下にも置く（QtCore.pyd の DLL 探索を安定化）
$qtBin = Join-Path $distDir "_internal\PyQt6\Qt6\bin"
$qtPkg = Join-Path $distDir "_internal\PyQt6"
if ((Test-Path $qtBin) -and (Test-Path $qtPkg)) {
    Get-ChildItem -Path $qtBin -Filter "Qt6*.dll" | ForEach-Object {
        Copy-Item -Force $_.FullName (Join-Path $qtPkg $_.Name)
    }
    Write-Host "Copied Qt6 DLLs beside QtCore.pyd"
}

# Qt6Core 用 ICU（Windows 標準名 UCNV_*）を Qt6/bin に配置
$sys32 = Join-Path $env:SystemRoot "System32"
foreach ($icuName in @("icuuc.dll", "icuin.dll")) {
    $src = Join-Path $sys32 $icuName
    if ((Test-Path $src) -and (Test-Path $qtBin)) {
        Copy-Item -Force $src (Join-Path $qtBin $icuName)
        Write-Host "Copied $icuName -> Qt6/bin"
    }
}
# _internal 直下に残った誤った ICU を削除
$internal = Join-Path $distDir "_internal"
Get-ChildItem -Path $internal -Filter "icu*.dll" -ErrorAction SilentlyContinue | ForEach-Object {
    Remove-Item -Force $_.FullName
    Write-Host "Removed stray $($_.Name) from _internal"
}

$iscc = $null
if (Get-Command iscc -ErrorAction SilentlyContinue) { $iscc = "iscc" }
elseif (Test-Path "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe") { $iscc = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe" }
elseif (Test-Path "$env:ProgramFiles\Inno Setup 6\ISCC.exe") { $iscc = "$env:ProgramFiles\Inno Setup 6\ISCC.exe" }

if ($iscc) {
    New-Item -ItemType Directory -Force -Path dist\installer | Out-Null
    & $iscc "installer\midi_chord_lab.iss"
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    Write-Host "Installer: dist\installer\MIDIChordLab_Setup_2.14.9.exe"
} else {
    Write-Warning "Inno Setup not found; skipped installer. dist\MIDIChordViewer\MIDIChordViewer.exe is ready."
}

Write-Host "Done: dist\MIDIChordViewer\MIDIChordViewer.exe"
