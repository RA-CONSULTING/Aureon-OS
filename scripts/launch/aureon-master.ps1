# Canonical Aureon launcher for Windows. Live trading is not armed here.
$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $Root
python -m aureon.launch.master @args
exit $LASTEXITCODE
