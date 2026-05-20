$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$vcvars = "${env:ProgramFiles}\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat"
if (Test-Path $vcvars) {
    cmd /c "`"$vcvars`" && set" | ForEach-Object {
        if ($_ -match '^([^=]+)=(.*)$') {
            [System.Environment]::SetEnvironmentVariable($matches[1], $matches[2])
        }
    }
}
$env:PATH = "$env:USERPROFILE\.cargo\bin;$env:PATH"
$pyLibs = "$env:LOCALAPPDATA\Programs\Python\Python313\libs"
$pyInc = "$env:LOCALAPPDATA\Programs\Python\Python313\include"
if (Test-Path "$pyLibs\python313.lib") {
    $env:LIB = "$pyLibs;$env:LIB"
    $env:INCLUDE = "$pyInc;$env:INCLUDE"
}
$env:PYO3_PYTHON = "$root\.venv\Scripts\python.exe"
Set-Location $root
& "$root\.venv\Scripts\Activate.ps1"
& "$root\.venv\Scripts\pip.exe" install -q maturin
& "$root\.venv\Scripts\maturin.exe" develop --release --manifest-path rust\midi_viz\Cargo.toml
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& "$root\.venv\Scripts\python.exe" -c "import midi_viz; print('midi_viz OK', midi_viz.is_available())"
