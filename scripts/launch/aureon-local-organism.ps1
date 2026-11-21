# Start the measured non-model local organism from this checkout.
# No exchange mutation is armed. Model-dependent loops remain blocked until
# the pinned Aureon model and its HNC evidence are available.
param(
    [switch]$Status,
    [switch]$Stop,
    [switch]$EnvStatus
)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location -LiteralPath $Root
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $Python)) {
    throw "Missing $Python. Run install.cmd --smoke first."
}

$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
$env:AUREON_LIVE_TRADING = "0"
$env:AUREON_DISABLE_REAL_ORDERS = "1"
$env:AUREON_DISABLE_EXCHANGE_MUTATIONS = "1"
$env:AUREON_ORDER_INTENT_PUBLISH = "0"
$env:AUREON_UNIFIED_ORDER_EXECUTOR = "0"
$env:AUREON_DRY_RUN = "1"
$env:AUREON_PLUG_AND_PLAY = "0"
# The local runtime may use its configured own-model service. The guarded
# install.cmd smoke remains deliberately offline and strips credentials.
$env:AUREON_LLM_OFFLINE = "0"

$Arguments = @("-B", "-m", "aureon.launch.master")
if ($EnvStatus) {
    $Arguments += "--env-status"
} elseif ($Status) {
    $Arguments += "--status"
} elseif ($Stop) {
    $Arguments += "--stop"
} else {
    $env:AUREON_AUTONOMY_MODE = "full"
    $Arguments += @(
        "--only",
        "organ/hnc_core,organ/hnc_live_daemon,organ/organism_circulation,organ/operator_gateway,organ/frontend_vite,organ/unified_market_status,organ/mind_thought_action_hub,organ/bus_bridge"
    )
}
& $Python @Arguments
exit $LASTEXITCODE
