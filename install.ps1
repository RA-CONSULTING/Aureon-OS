#Requires -Version 5.1
# Guarded local boot for Windows. Live trading stays off.
# .env stays unread. Supported go-live remains HOLD.
# Python 3.11+ and Node.js 20+ must already be on PATH.
$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $false
$Root = (Resolve-Path -LiteralPath $PSScriptRoot).Path
Set-Location -LiteralPath $Root

function Fail {
    param([string]$Message)
    [Console]::Error.WriteLine($Message)
    exit 1
}

function Test-Python311 {
    param(
        [string]$Exe,
        [string[]]$PrefixArgs
    )
    & $Exe @PrefixArgs -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)"
    return $LASTEXITCODE -eq 0
}

$PyExe = $null
$PyPrefix = @()
if (Get-Command py -ErrorAction SilentlyContinue) {
    if (Test-Python311 -Exe "py" -PrefixArgs @("-3")) {
        $PyExe = "py"
        $PyPrefix = @("-3")
    }
}
if (-not $PyExe -and (Get-Command python -ErrorAction SilentlyContinue)) {
    if (Test-Python311 -Exe "python" -PrefixArgs @()) {
        $PyExe = "python"
        $PyPrefix = @()
    }
}
if (-not $PyExe) {
    Fail "Python 3.11 or newer is required. Install it from https://www.python.org/downloads/windows/ and reopen the terminal. This script does not install Windows packages, leaves .env unread, and keeps live trading off. Supported go-live remains HOLD."
}

$VenvPy = Join-Path $Root ".venv\Scripts\python.exe"
$Plug = Join-Path $Root "scripts\plug_and_play.py"

if ($args.Count -gt 0 -and $args[0] -eq "--stop") {
    if (-not (Test-Path -LiteralPath $VenvPy)) {
        Fail "No .venv yet. Nothing to stop."
    }
    & $VenvPy $Plug --stop
    exit $LASTEXITCODE
}

if (-not (Get-Command node -ErrorAction SilentlyContinue) -or -not (Get-Command npm -ErrorAction SilentlyContinue)) {
    Fail "Node.js and npm are required for the dashboard (Node 20 or newer). This script does not install them."
}
$nodeRaw = (& node -p "process.versions.node")
if ($LASTEXITCODE -ne 0 -or -not $nodeRaw) {
    Fail "Node.js 20 or newer is required for the dashboard."
}
$nodeRaw = $nodeRaw.ToString().Trim()
$nodeMajor = 0
$parsedNode = [int]::TryParse($nodeRaw.Split(".")[0], [ref]$nodeMajor)
if (-not $parsedNode -or $nodeMajor -lt 20) {
    Fail "Node.js $nodeRaw is too old; 20 or newer is required."
}

if (-not (Test-Path -LiteralPath $VenvPy)) {
    & $PyExe @PyPrefix -m venv (Join-Path $Root ".venv")
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $VenvPy)) {
        Fail "Could not create .venv. Install Python 3.11 or newer and run this script again."
    }
}

& $VenvPy -m pip install -U pip
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $VenvPy -m pip install -r (Join-Path $Root "requirements-plug.lock")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$ViteJs = Join-Path $Root "frontend\node_modules\vite\bin\vite.js"
if (-not (Test-Path -LiteralPath $ViteJs)) {
    & npm ci --ignore-scripts --prefix frontend
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
if (-not (Test-Path -LiteralPath $ViteJs)) {
    Fail "dashboard binary missing: $ViteJs"
}

$EnvFile = Join-Path $Root ".env"
if (Test-Path -LiteralPath $EnvFile) {
    Write-Output ".env is present and is not read. Live trading stays off."
}
Write-Output "release boundary: HOLD. Guarded smoke only. Live trading stays off. Supported go-live remains HOLD."
& $VenvPy $Plug @args
exit $LASTEXITCODE
