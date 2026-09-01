#Requires -Version 5.1
$ErrorActionPreference = "Stop"
$repo = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$python = Join-Path $repo ".venv\Scripts\python.exe"
$bootstrap = Join-Path $repo "scripts\bootstrap\protected_bootstrap_v05.py"

if (-not (Test-Path -LiteralPath $python -PathType Leaf) -or
    -not (Test-Path -LiteralPath $bootstrap -PathType Leaf)) {
    Write-Error "Aureon protected installer boundary is unavailable; refusing installation."
    exit 1
}

Write-Warning "Aureon installation and release are on terminal protection HOLD."
& $python -I -S -B $bootstrap --target-id production-supervisor
exit $LASTEXITCODE
