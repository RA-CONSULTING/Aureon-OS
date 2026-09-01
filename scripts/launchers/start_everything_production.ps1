#Requires -Version 5.1
<#
.SYNOPSIS
    Held validation wrapper for the Aureon + Flameborn production launch plan.
.DESCRIPTION
    This wrapper does not arm live trading or start Aureon, Flameborn, runtime,
    host-terminal, or sandbox processes. -WhatIf prints the held launch plan.
    Every non-WhatIf invocation fails closed before any Start-Process call until
    an independently reviewed production-supervisor authority type exists.

    Safety blocks that REMAIN active (not overridden):
    - External attack capabilities: BLOCKED
    - Companies House / HMRC automatic filing: BLOCKED
    - Tax / penalty automatic payments: BLOCKED

    These organism safety blocks are not process-start authority and remain
    relevant if a future reviewed authority path replaces the current HOLD.
#>
param(
    [switch]$SkipFlameborn,
    [switch]$SkipSandbox,
    [switch]$SkipHostTerminal,
    [switch]$WhatIf
)

$ErrorActionPreference = "Stop"
$repo = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..\..")).Path
if (-not (Test-Path -LiteralPath (Join-Path $repo "pyproject.toml") -PathType Leaf)) {
    throw "Resolved launcher repo root is invalid: $repo"
}
$productionLauncher = Join-Path $PSScriptRoot "AUREON_PRODUCTION_LIVE.cmd"
$flamebornLauncher = Join-Path $repo "scripts\start_aureon_with_flameborn.ps1"

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
Write-Banner "  AUREON PRODUCTION VALIDATION WRAPPER - HOLD" "WARN"
Write-Banner "  No runtime process or live trading is armed" "WARN"
Write-Banner "===============================================================" "ALIVE"
Write-Banner ""
Write-Banner "MODE: VALIDATION / PROCESS-START AUTHORITY HOLD" "WARN"
Write-Banner "SAFETY: External attacks / auto-filing / auto-payments = BLOCKED" "WARN"
Write-Banner ""

if ($WhatIf) {
    Write-Banner "WhatIf mode -- showing commands without executing." "WARN"
    Write-Banner ""
    Write-Banner "Terminal 1 would run:"
    Write-Banner "  .\scripts\launchers\AUREON_PRODUCTION_LIVE.cmd -WaitForRefresh -MarketStatusPort 8791"
    Write-Banner ""
    Write-Banner "Terminal 2 would run:"
    $fbFlags = @()
    if (-not $SkipSandbox) { $fbFlags += "-EnableSandbox" }
    if (-not $SkipHostTerminal) { $fbFlags += "-EnableHostTerminal" }
    Write-Banner "  .\scripts\start_aureon_with_flameborn.ps1 -StartRuntime $($fbFlags -join ' ')"
    exit 0
}

# This validation wrapper retains the proposed launch plan below for inspection,
# but it is unreachable while the unconditional authority HOLD remains here.
# The child production launcher enforces the same boundary; an evidence-only
# full-live ACCEPT cannot indirectly authorize either Start-Process call.
throw "Production wrapper process-start authority HOLD: no independent production supervisor authority type is available. WhatIf remains available without starting processes."
