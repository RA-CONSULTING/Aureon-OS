#Requires -Version 5.1
param(
    [int]$WebPort = 4173,
    [int]$RuntimePort = 7331,
    [int]$AureonPort = 5566,
    [switch]$StartRuntime,
    [switch]$EnableHostTerminal,
    [switch]$EnableSandbox
)

$ErrorActionPreference = "Stop"
$repo = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$python = Join-Path $repo ".venv\Scripts\python.exe"
$bootstrap = Join-Path $repo "scripts\bootstrap\protected_bootstrap_v05.py"

if (-not (Test-Path -LiteralPath $python -PathType Leaf) -or
    -not (Test-Path -LiteralPath $bootstrap -PathType Leaf)) {
    Write-Error "Protected Flameborn bootstrap unavailable; refusing startup."
    exit 1
}

Write-Warning "Aureon + Flameborn startup is on terminal protection HOLD."
& $python -I -S -B $bootstrap --target-id flameborn-runtime
exit $LASTEXITCODE
