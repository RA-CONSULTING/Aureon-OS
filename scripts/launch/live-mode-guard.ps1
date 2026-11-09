# Force guarded mode unless the stage 11 gate is clear and AUREON_OPERATOR_ALLOW_LIVE
# is set, or a valid operator test session is active. A session does not set go_live_clear.
function Invoke-AureonLiveModeGuard {
    $previous = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $output = & python -m aureon.launch.live_gate 2>&1 | Out-String
    $code = $LASTEXITCODE
    $ErrorActionPreference = $previous
    Write-Output $output
    if ($code -ne 0) {
        $env:AUREON_LIVE_TRADING = "0"
        $env:AUREON_AUTONOMY_MODE = "guarded"
        $env:AUREON_DISABLE_REAL_ORDERS = "1"
        Remove-Item Env:AUREON_OPERATOR_TEST_SESSION_STAMP -ErrorAction SilentlyContinue
        return
    }
    if ($output -match "operator_test_session=[A-Za-z0-9._-]*, go_live_clear=false") {
        $env:AUREON_OPERATOR_TEST_SESSION_STAMP = $Matches[0]
    }
}
