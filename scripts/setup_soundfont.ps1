# FluidSynth (Windows x64) と GM SoundFont を assets に配置
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$binDir = Join-Path $root "assets\fluidsynth\bin"
$sfDir = Join-Path $root "assets\soundfonts"
New-Item -ItemType Directory -Force -Path $binDir, $sfDir | Out-Null

# FluidSynth 2.3.4 win10 x64（GitHub Releases）
$fsZip = Join-Path $env:TEMP "fluidsynth-win.zip"
$fsUrl = "https://github.com/fluidsynth/fluidsynth/releases/download/v2.3.4/fluidsynth-2.3.4-win10-x64.zip"
Write-Host "Downloading FluidSynth..."
Invoke-WebRequest -Uri $fsUrl -OutFile $fsZip -UseBasicParsing
Expand-Archive -Path $fsZip -DestinationPath (Join-Path $env:TEMP "fs_extract") -Force
$extracted = Get-ChildItem (Join-Path $env:TEMP "fs_extract") -Recurse -Filter "fluidsynth.exe" | Select-Object -First 1
if (-not $extracted) { throw "fluidsynth.exe not found in archive" }
$srcDir = $extracted.Directory.FullName
Copy-Item -Path (Join-Path $srcDir "*") -Destination $binDir -Recurse -Force
Write-Host "FluidSynth -> $binDir"

$guDir = Join-Path $sfDir "GeneralUser-GS"
$sfPath = Join-Path $guDir "GeneralUser-GS.sf2"
if (Test-Path $sfPath) {
    Write-Host "SoundFont -> $sfPath"
} else {
    Write-Warning "Place GeneralUser-GS.sf2 in assets\soundfonts\GeneralUser-GS\"
}
Write-Host "Done. Rebuild the app or run from venv."
