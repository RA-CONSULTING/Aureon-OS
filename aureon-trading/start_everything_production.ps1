#Requires -Version 5.1
<#
.SYNOPSIS
    One-command full Aureon + Flameborn production launch.
.DESCRIPTION
    Starts the entire Aureon organism in production mode AND the Flameborn
    frontend with runtime, host terminal, and sandbox enabled.

    WARNING: This opens live trading gates. Only run when you intend to
    trade with real money on configured exchanges.

    Safety blocks that REMAIN active (not overridden):
    - External attack capabilities: BLOCKED
    - Companies House / HMRC automatic filing: BLOCKED
    - Tax / penalty automatic payments: BLOCKED

    These blocks protect you from legal/financial autopilot errors.
    They are hardcoded organism safety limits, not runtime bugs.
#>
param(
    [switch]$SkipFlameborn,
    [switch]$SkipSandbox,
    [switch]$SkipHostTerminal,
    [switch]$WhatIf
)

$ErrorActionPreference = "Stop"
$repo = Resolve-Path (Split-Path -Parent $MyInvocation.MyCommand.Definition)

function Write-Banner {
    param([string]$Text, [string]$Level = "INFO")
    $stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $color = switch ($Level) {
        "WARN"  { "Yellow" }
        "ERROR" { "Red" }
        "ALIVE" { "Green" }
        default { "Cyan" }
    }
    Write-Host "[$stamp] [$Level] $Text" -ForegroundColor $color
}

Write-Banner "===============================================================" "ALIVE"
Write-Banner "  AUREON FULL PRODUCTION LAUNCHER" "ALIVE"
Write-Banner "  Organism + Flameborn + Runtime + Sandbox" "ALIVE"
Write-Banner "===============================================================" "ALIVE"
Write-Banner ""
Write-Banner "MODE: PRODUCTION (live trading armed)" "WARN"
Write-Banner "SAFETY: External attacks / auto-filing / auto-payments = BLOCKED" "WARN"
Write-Banner ""

if ($WhatIf) {
    Write-Banner "WhatIf mode -- showing commands without executing." "WARN"
    Write-Banner ""
    Write-Banner "Terminal 1 would run:"
    Write-Banner "  .\AUREON_PRODUCTION_LIVE.cmd -WaitForRefresh -MarketStatusPort 8791"
    Write-Banner ""
    Write-Banner "Terminal 2 would run:"
    $fbFlags = @()
    if (-not $SkipSandbox) { $fbFlags += "-EnableSandbox" }
    if (-not $SkipHostTerminal) { $fbFlags += "-EnableHostTerminal" }
    Write-Banner "  .\scripts\start_aureon_with_flameborn.ps1 -StartRuntime $($fbFlags -join ' ')"
    exit 0
}

# -- Terminal 1: Aureon Organism (Production) --
$orgCmd = "cd `"$repo`"; .\AUREON_PRODUCTION_LIVE.cmd -WaitForRefresh -MarketStatusPort 8791"
Write-Banner "Launching Terminal 1: Aureon Organism (Production) ..."
Start-Process powershell -ArgumentList "-NoExit","-Command",$orgCmd

# -- Wait for organism core to bind --
Write-Banner "Waiting 15s for organism ignition ..."
Start-Sleep -Seconds 15

# -- Terminal 2: Flameborn Frontend --
$fbFlags = @("-StartRuntime")
if (-not $SkipHostTerminal) { $fbFlags += "-EnableHostTerminal" }
if (-not $SkipSandbox) { $fbFlags += "-EnableSandbox" }
$fbCmd = "cd `"$repo`"; .\scripts\start_aureon_with_flameborn.ps1 $($fbFlags -join ' ')"
Write-Banner "Launching Terminal 2: Flameborn Frontend ..."
Start-Process powershell -ArgumentList "-NoExit","-Command",$fbCmd

Write-Banner ""
Write-Banner "===============================================================" "ALIVE"
Write-Banner "  BOTH TERMINALS LAUNCHED" "ALIVE"
Write-Banner "===============================================================" "ALIVE"
Write-Banner ""
Write-Banner "Unified console:     http://127.0.0.1:8081/"
Write-Banner "Flameborn chat:      http://127.0.0.1:4173/"
Write-Banner "Market feed:         http://127.0.0.1:8791/api/terminal-state"
Write-Banner "Market flight-test:  http://127.0.0.1:8791/api/flight-test"
Write-Banner "Mind hub:            http://127.0.0.1:13002/"
Write-Banner "Vault UI:            http://127.0.0.1:5566/"
Write-Banner ""
Write-Banner "Close each terminal window to stop that surface." "WARN"
Write-Banner ""
