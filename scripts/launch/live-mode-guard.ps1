# Force guarded mode unless the stage 11 gate is clear and AUREON_OPERATOR_ALLOW_LIVE is set.
function Invoke-AureonLiveModeGuard {
    $previous = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    & python -m aureon.launch.live_gate
    $code = $LASTEXITCODE
    $ErrorActionPreference = $previous
    if ($code -ne 0) {
        $env:AUREON_LIVE_TRADING = "0"
        $env:AUREON_AUTONOMY_MODE = "guarded"
        $env:AUREON_DISABLE_REAL_ORDERS = "1"
    }
}
