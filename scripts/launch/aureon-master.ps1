# Canonical Aureon launcher for Windows.
# Live mode stays locked unless the stage 11 gate reports clear and
# AUREON_OPERATOR_ALLOW_LIVE is set.
$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $Root
# A refusal sets AUREON_LIVE_TRADING=0 and AUREON_AUTONOMY_MODE=guarded.
. (Join-Path $PSScriptRoot "live-mode-guard.ps1")
Invoke-AureonLiveModeGuard
python -m aureon.launch.master @args
exit $LASTEXITCODE
