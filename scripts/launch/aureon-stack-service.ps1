# Keep one local Aureon stack running and one health monitor watching it.
# Task Scheduler (or a WMI-created process) starts this script, so it is not
# tied to a terminal session. Each cycle calls the single launcher; the
# launcher starts only missing components and never duplicates a live pid.
param(
    [int]$IntervalSeconds = 300
)

$ErrorActionPreference = "Continue"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location -LiteralPath $Root
$StateDir = Join-Path $Root "state\launcher"
$LogDir = Join-Path $StateDir "logs"
$PidFile = Join-Path $StateDir "service.pid"
$StopFlag = Join-Path $StateDir "service.stop"
$CoreOnlyFlag = Join-Path $StateDir "core-only"
$LogFile = Join-Path $LogDir "stack_service.log"
$Launcher = Join-Path $PSScriptRoot "aureon-local-organism.ps1"

New-Item -ItemType Directory -Force -Path $StateDir | Out-Null
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

function Rotate-ServiceLog {
    if (-not (Test-Path -LiteralPath $LogFile)) {
        return
    }
    $size = (Get-Item -LiteralPath $LogFile -ErrorAction SilentlyContinue).Length
    if ($size -lt 8MB) {
        return
    }
    $archive = "$LogFile.1"
    Remove-Item -LiteralPath $archive -Force -ErrorAction SilentlyContinue
    Move-Item -LiteralPath $LogFile -Destination $archive -Force -ErrorAction SilentlyContinue
}

function Test-ExistingService {
    if (-not (Test-Path -LiteralPath $PidFile)) {
        return $false
    }
    $raw = Get-Content -LiteralPath $PidFile -ErrorAction SilentlyContinue | Select-Object -First 1
    $serviceProcessId = 0
    if (-not $raw -or -not [int]::TryParse($raw.Trim(), [ref]$serviceProcessId)) {
        return $false
    }
    $process = Get-CimInstance Win32_Process -Filter "ProcessId=$serviceProcessId" -ErrorAction SilentlyContinue
    if (-not $process) {
        return $false
    }
    return ($process.CommandLine -match "aureon-stack-service\.ps1")
}

if (Test-ExistingService) {
    Add-Content -LiteralPath $LogFile -Value "[$(Get-Date -Format o)] another stack service is already running"
    exit 0
}

Set-Content -LiteralPath $PidFile -Value $PID -Encoding ASCII
Add-Content -LiteralPath $LogFile -Value "[$(Get-Date -Format o)] stack service started (pid $PID, interval ${IntervalSeconds}s)"

try {
    while (-not (Test-Path -LiteralPath $StopFlag)) {
        Rotate-ServiceLog
        Add-Content -LiteralPath $LogFile -Value "[$(Get-Date -Format o)] launcher cycle"
        try {
            $LauncherArgs = @()
            if (Test-Path -LiteralPath $CoreOnlyFlag) {
                $LauncherArgs += "-CoreOnly"
            }
            & $Launcher @LauncherArgs *>> $LogFile
        } catch {
            Add-Content -LiteralPath $LogFile -Value "[$(Get-Date -Format o)] launcher failed: $($_.Exception.Message)"
        }
        Start-Sleep -Seconds ([Math]::Max(30, $IntervalSeconds))
    }
    Add-Content -LiteralPath $LogFile -Value "[$(Get-Date -Format o)] stop flag seen; stack service exiting"
} finally {
    Remove-Item -LiteralPath $PidFile -Force -ErrorAction SilentlyContinue
}
