#Requires -Version 5.1
$ErrorActionPreference = "Stop"
$repo = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
Set-Location -LiteralPath $repo
$env:AUREON_LIVE_TRADING = "0"
$env:AUREON_SIMULATED_BOOT = "0"
if (-not $env:AUREON_UI_PORT) { $env:AUREON_UI_PORT = "8080" }
$env:PYTHONPATH = $repo
$ui = "http://127.0.0.1:$($env:AUREON_UI_PORT)/"

$python = $null
$venvPython = Join-Path $repo ".venv\Scripts\python.exe"
if (Test-Path -LiteralPath $venvPython) {
    $python = $venvPython
} else {
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if (-not $cmd) { $cmd = Get-Command python3 -ErrorAction SilentlyContinue }
    if (-not $cmd) {
        Write-Error "Python 3 is required."
        exit 1
    }
    & $cmd.Source -m venv (Join-Path $repo ".venv")
    $python = $venvPython
}

& $python -m pip install --disable-pip-version-check -q "aiohttp>=3.9" "websocket-client>=1.6" "requests>=2.32" "python-dotenv>=1.0" "rich>=13.7"
$envFile = Join-Path $repo ".env"
$example = Join-Path $repo ".env.example"
if (-not (Test-Path -LiteralPath $envFile)) {
    Copy-Item -LiteralPath $example -Destination $envFile
    Add-Content -LiteralPath $envFile -Value "`nAUREON_LIVE_TRADING=0`nAUREON_SIMULATED_BOOT=0"
    Write-Output "wrote .env from .env.example with live trading left off"
} else {
    Write-Output ".env already present; installer left it unchanged"
}

Write-Output "Aureon UI: $ui"
& $python -m aureon.autonomous.aureon_master_launcher --preflight
exit $LASTEXITCODE
