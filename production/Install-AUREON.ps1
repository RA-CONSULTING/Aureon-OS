#Requires -Version 5.1
# Existing Aureon installer for Windows. Safe to re-run.
# Installs the toolchain it can, builds the UI, writes .env once, then
# starts the organism through scripts\launch\aureon-master.ps1.
$ErrorActionPreference = "Stop"
$Root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
Set-Location $Root
$UiUrl = "http://127.0.0.1:5173/"

function Refresh-Path {
    $machine = [Environment]::GetEnvironmentVariable("Path", "Machine")
    $user = [Environment]::GetEnvironmentVariable("Path", "User")
    if ($machine -or $user) {
        $env:Path = "$machine;$user"
    }
}

function Ensure-Tool {
    param([string]$Name, [string]$WingetId)
    if (Get-Command $Name -ErrorAction SilentlyContinue) {
        Write-Output "$Name already present"
        return
    }
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        Write-Error "$Name is not on PATH and winget is unavailable."
    }
    Write-Output "installing $Name via winget ($WingetId)"
    & winget install -e --id $WingetId --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
    Refresh-Path
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        Write-Error "$Name is still not on PATH. Open a new terminal and run this installer again."
    }
}

Ensure-Tool python Python.Python.3.12
Ensure-Tool node OpenJS.NodeJS.LTS
Refresh-Path
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    Write-Error "npm is not on PATH."
}

$env:PYTHONPATH = $Root
$env:AUREON_INSTALL_ROOT = $Root
& python -c @"
import os, sys
from pathlib import Path
from aureon.launch.master import _ensure_local_env
ok, detail = _ensure_local_env(Path(os.environ['AUREON_INSTALL_ROOT']))
print(detail)
sys.exit(0 if ok else 1)
"@
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Push-Location (Join-Path $Root "frontend")
if (-not (Test-Path -LiteralPath "node_modules\vite\bin\vite.js")) {
    & npm install --no-audit --no-fund
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} else {
    Write-Output "frontend packages already present"
}
& npm run build
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Pop-Location

if (Get-Command docker -ErrorAction SilentlyContinue) {
    & docker info *> $null
    if ($LASTEXITCODE -eq 0) {
        Write-Output "docker daemon is available; the launcher will pull and build images"
    } else {
        Write-Output "docker daemon is not available; the launcher will use native fallbacks"
    }
} else {
    Write-Output "docker daemon is not available; the launcher will use native fallbacks"
}

$env:SERO_WORKSPACE = $Root
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $Root "scripts\launch\aureon-master.ps1")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Output "Aureon UI: $UiUrl"
$ready = $false
for ($i = 0; $i -lt 45; $i++) {
    try {
        $response = Invoke-WebRequest -Uri $UiUrl -UseBasicParsing -TimeoutSec 5
        if ($response.StatusCode -eq 200) {
            Write-Output "Aureon UI is reachable: $UiUrl (HTTP 200)"
            $ready = $true
            break
        }
    } catch {
        Start-Sleep -Seconds 2
    }
}
if (-not $ready) {
    Write-Error "Aureon UI did not answer at $UiUrl"
}
exit 0
