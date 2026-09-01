# Fixed isolated protection boundary; this route cannot start its legacy target.
$ErrorActionPreference = "Stop"
$repoRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$pythonExe = Join-Path $repoRoot ".venv\Scripts\python.exe"
$bootstrap = Join-Path $repoRoot "scripts\bootstrap\protected_bootstrap_v05.py"

if (-not (Test-Path -LiteralPath $pythonExe -PathType Leaf)) {
    [Console]::Error.WriteLine("Fixed repository Python executable is unavailable; refusing operation.")
    exit 1
}
if (-not (Test-Path -LiteralPath $bootstrap -PathType Leaf)) {
    [Console]::Error.WriteLine("Fixed protected bootstrap is unavailable; refusing operation.")
    exit 1
}

& $pythonExe -I -S -B $bootstrap --target-id queen-eternal-machine
exit $LASTEXITCODE
