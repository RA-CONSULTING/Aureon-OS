param(
    [switch]$Adaptive,
    [string]$CoverageProfile = "LicensedReachable",
    [switch]$ValidateOnly,
    [switch]$DryRun,
    [switch]$RunOnce,
    [switch]$NoIngest,
    [switch]$SkipAccountSync,
    [int]$KrakenAccountSyncMax = 50,
    [int]$KrakenAssetRegistryTickers = 100,
    [int]$CapitalAssetRegistrySnapshots = 100,
    [int]$IntervalSeconds = 1800
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $RepoRoot

$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $Python)) {
    throw "Python venv not found: $Python"
}

$env:PYTHONUNBUFFERED = "1"
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONPATH = "$RepoRoot;$RepoRoot\aureon\core;$RepoRoot\aureon\exchanges;$RepoRoot\aureon\data_feeds;$RepoRoot\aureon\monitors;$RepoRoot\aureon\intelligence;$RepoRoot\aureon\queen;$env:PYTHONPATH"

try {
    [System.Diagnostics.Process]::GetCurrentProcess().PriorityClass = [System.Diagnostics.ProcessPriorityClass]::BelowNormal
} catch {
    # Best effort only. The data ocean must never be more important than execution/risk.
}

function Write-Ocean {
    param([string]$Message, [string]$Level = "INFO")
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host "[$ts] [$Level] $Message"
}

function Invoke-OceanPython {
    param([string[]]$PythonArgs, [switch]$AllowFailure)
    Write-Ocean ("python " + ($PythonArgs -join " "))
    & $Python @PythonArgs
    $code = $LASTEXITCODE
    if ($code -ne 0 -and -not $AllowFailure) {
        throw "Python command failed with exit code $code"
    }
    return $code
}

function Get-IngestProfile {
    switch ($CoverageProfile) {
        "InstitutionalMax" { return "max" }
        default { return "standard" }
    }
}

Write-Ocean "Aureon planetary data ocean"
Write-Ocean "Repo: $RepoRoot"
Write-Ocean "Coverage profile: $CoverageProfile"
Write-Ocean "Mode: budgeted adaptive=$($Adaptive.IsPresent), no ingest=$($NoIngest.IsPresent), dry run=$($DryRun.IsPresent), run once=$($RunOnce.IsPresent), skip account sync=$($SkipAccountSync.IsPresent), kraken tickers=$KrakenAssetRegistryTickers, capital snapshots=$CapitalAssetRegistrySnapshots"
Write-Ocean "Priority: BelowNormal where supported"

function Invoke-StatusRefresh {
    $dataArgs = @("-m", "aureon.autonomous.aureon_data_ocean", "--coverage-profile", $CoverageProfile, "--adaptive")
    if ($DryRun -or $ValidateOnly) { $dataArgs += "--dry-run" }
    $null = Invoke-OceanPython -PythonArgs $dataArgs
    $null = Invoke-OceanPython -PythonArgs @("-m", "aureon.exchanges.kraken_asset_registry", "--max-tickers", [string]$KrakenAssetRegistryTickers) -AllowFailure
    $null = Invoke-OceanPython -PythonArgs @("-m", "aureon.exchanges.capital_asset_registry", "--max-snapshots", [string]$CapitalAssetRegistrySnapshots) -AllowFailure
    $null = Invoke-OceanPython -PythonArgs @("-m", "aureon.autonomous.aureon_exchange_monitoring_checklist") -AllowFailure
    $null = Invoke-OceanPython -PythonArgs @("-m", "aureon.autonomous.aureon_exchange_data_capability_matrix") -AllowFailure
    $null = Invoke-OceanPython -PythonArgs @("-m", "aureon.autonomous.aureon_global_financial_coverage_map")
}

function Invoke-IngestCycle {
    if ($NoIngest -or $ValidateOnly) {
        Write-Ocean "Skipping ingest cycle; status/coverage only."
        return
    }
    $profile = Get-IngestProfile
    $args = @("scripts\python\ingest_global_memory.py", "--profile", $profile)
    $args += @("--account-sync-max-kraken", [string]$KrakenAccountSyncMax, "--account-sync-binance-limit", "200", "--account-sync-alpaca-limit", "200")
    if ($SkipAccountSync) { $args += "--skip-account-sync" }
    if ($DryRun) { $args += "--dry-run" }
    $null = Invoke-OceanPython -PythonArgs $args -AllowFailure
}

Invoke-StatusRefresh
if ($ValidateOnly) {
    Write-Ocean "Validation complete."
    exit 0
}

do {
    Invoke-IngestCycle
    Invoke-StatusRefresh
    if ($RunOnce) { break }
    Write-Ocean "Sleeping $IntervalSeconds seconds before next data ocean cycle."
    Start-Sleep -Seconds $IntervalSeconds
} while ($true)

Write-Ocean "Data ocean cycle complete."
