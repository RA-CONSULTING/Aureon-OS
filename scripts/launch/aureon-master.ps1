# Canonical Aureon launcher for Windows. Trading follows exchange keys in .env.
$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $Root
python -m aureon.launch.master @args
exit $LASTEXITCODE
