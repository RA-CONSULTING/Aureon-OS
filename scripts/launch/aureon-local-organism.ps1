# Start the measured non-model local organism from this checkout.
# No exchange mutation is armed. Model-dependent loops remain blocked until
# the pinned Aureon model and its HNC evidence are available.
param(
    [switch]$Status,
    [switch]$Stop,
    [switch]$EnvStatus,
    [switch]$Monitor,
    [switch]$Watch,
    [switch]$RefreshRegistry,
    [switch]$NoMonitor
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

# Bounded logs. The ThoughtBus rotates its active log on write; the unified
# bus keeps timestamped archives and never deletes one by itself.
$env:AUREON_THOUGHT_BUS_MAX_BYTES = "33554432"
$env:AUREON_THOUGHT_BUS_BACKUPS = "3"
$env:AUREON_UNIFIED_BUS_MAX_BYTES = "33554432"

$MonitorDir = Join-Path $Root "state\monitor"
$MonitorPid = Join-Path $MonitorDir "monitor.pid"
$MonitorOut = Join-Path $MonitorDir "monitor.out.log"
$MonitorErr = Join-Path $MonitorDir "monitor.err.log"
$MonitorScript = Join-Path $Root "scripts\monitor\aureon_health_monitor.py"
$ServiceDir = Join-Path $Root "state\launcher"
$ServicePid = Join-Path $ServiceDir "service.pid"
$ServiceStop = Join-Path $ServiceDir "service.stop"

function Invoke-RotateLogs {
    $rotate = Join-Path $Root "scripts\ops\rotate_logs.py"
    if (Test-Path -LiteralPath $rotate) {
        & $Python -B $rotate
    }
}

function Invoke-EnsureRegistry {
    param([switch]$Force)
    $ensure = Join-Path $Root "scripts\ops\ensure_system_registry.py"
    if (-not (Test-Path -LiteralPath $ensure)) {
        return
    }
    $arguments = @("-B", $ensure)
    if ($Force) {
        $arguments += "--force"
    }
    & $Python @arguments
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "system registry refresh failed with exit code $LASTEXITCODE"
    }
}

function Get-MonitorProcess {
    if (-not (Test-Path -LiteralPath $MonitorPid)) {
        return $null
    }
    $raw = (Get-Content -LiteralPath $MonitorPid -ErrorAction SilentlyContinue | Select-Object -First 1)
    if (-not $raw) {
        return $null
    }
    $monitorProcessId = 0
    if (-not [int]::TryParse($raw.Trim(), [ref]$monitorProcessId)) {
        return $null
    }
    $process = Get-CimInstance Win32_Process -Filter "ProcessId=$monitorProcessId" -ErrorAction SilentlyContinue
    if (-not $process) {
        return $null
    }
    if ($process.CommandLine -notmatch "aureon_health_monitor\.py") {
        return $null
    }
    return $process
}

function Start-MonitorWatch {
    if (Test-Path -LiteralPath $MonitorPid) {
        $existing = Get-MonitorProcess
        if ($existing) {
            Write-Output "health monitor already running as pid $($existing.ProcessId)"
            return
        }
        Remove-Item -LiteralPath $MonitorPid -Force -ErrorAction SilentlyContinue
    }
    if (-not (Test-Path -LiteralPath $MonitorScript)) {
        Write-Warning "health monitor script is missing: $MonitorScript"
        return
    }
    New-Item -ItemType Directory -Force -Path $MonitorDir | Out-Null
    $process = Start-Process -FilePath $Python `
        -ArgumentList @("-B", $MonitorScript, "--watch", "--interval", "60", "--quiet") `
        -WorkingDirectory $Root `
        -WindowStyle Hidden `
        -RedirectStandardOutput $MonitorOut `
        -RedirectStandardError $MonitorErr `
        -PassThru
    Start-Sleep -Milliseconds 600
    $running = Get-Process -Id $process.Id -ErrorAction SilentlyContinue
    if ($running) {
        Write-Output "health monitor started as pid $($process.Id)"
    } else {
        Write-Warning "health monitor exited during startup; see $MonitorErr"
    }
}

function Stop-MonitorWatch {
    $existing = Get-MonitorProcess
    if ($existing) {
        Stop-Process -Id $existing.ProcessId -Force -ErrorAction SilentlyContinue
        Write-Output "health monitor stopped (pid $($existing.ProcessId))"
    }
    Remove-Item -LiteralPath $MonitorPid -Force -ErrorAction SilentlyContinue
}

function Get-StackServiceProcess {
    if (-not (Test-Path -LiteralPath $ServicePid)) {
        return $null
    }
    $raw = (Get-Content -LiteralPath $ServicePid -ErrorAction SilentlyContinue | Select-Object -First 1)
    if (-not $raw) {
        return $null
    }
    $serviceProcessId = 0
    if (-not [int]::TryParse($raw.Trim(), [ref]$serviceProcessId)) {
        return $null
    }
    $process = Get-CimInstance Win32_Process -Filter "ProcessId=$serviceProcessId" -ErrorAction SilentlyContinue
    if (-not $process) {
        return $null
    }
    if ($process.CommandLine -notmatch "aureon-stack-service\.ps1") {
        return $null
    }
    return $process
}

function Stop-StackService {
    New-Item -ItemType Directory -Force -Path $ServiceDir | Out-Null
    New-Item -ItemType File -Force -Path $ServiceStop | Out-Null
    $existing = Get-StackServiceProcess
    if ($existing) {
        Stop-Process -Id $existing.ProcessId -Force -ErrorAction SilentlyContinue
        Write-Output "stack service stopped (pid $($existing.ProcessId))"
    }
    Remove-Item -LiteralPath $ServicePid -Force -ErrorAction SilentlyContinue
}

function Invoke-MonitorOnce {
    if (-not (Test-Path -LiteralPath $MonitorScript)) {
        Write-Warning "health monitor script is missing: $MonitorScript"
        return
    }
    & $Python -B $MonitorScript
}

if ($Monitor -or $Watch) {
    if ($Watch) {
        Start-MonitorWatch
    } else {
        Invoke-MonitorOnce
    }
    exit $LASTEXITCODE
}

if ($Stop) {
    Stop-StackService
    Stop-MonitorWatch
    $Arguments = @("-B", "-m", "aureon.launch.master", "--stop")
    & $Python @Arguments
    $code = $LASTEXITCODE
    Invoke-RotateLogs
    exit $code
}

if ($Status) {
    $service = Get-StackServiceProcess
    if ($service) {
        Write-Output "stack service: running as pid $($service.ProcessId)"
    } else {
        Write-Output "stack service: not running"
    }
    $Arguments = @("-B", "-m", "aureon.launch.master", "--status")
    if ($RefreshRegistry) {
        Invoke-EnsureRegistry -Force
    }
    & $Python @Arguments
    $code = $LASTEXITCODE
    Invoke-MonitorOnce
    exit $code
}

if ($EnvStatus) {
    $Arguments = @("-B", "-m", "aureon.launch.master", "--env-status")
    & $Python @Arguments
    exit $LASTEXITCODE
}

# Normal start: bound the logs, refresh generated inventory when needed, start
# the selected organs once, then leave a health monitor watching them.
Remove-Item -LiteralPath $ServiceStop -Force -ErrorAction SilentlyContinue
Invoke-RotateLogs
Invoke-EnsureRegistry -Force:$RefreshRegistry
$env:AUREON_AUTONOMY_MODE = "full"
$Arguments = @(
    "-B", "-m", "aureon.launch.master",
    "--only",
    "organ/hnc_core,organ/hnc_live_daemon,organ/organism_circulation,organ/operator_gateway,organ/frontend_vite,organ/unified_market_status,organ/mind_thought_action_hub,organ/bus_bridge"
)
& $Python @Arguments
$code = $LASTEXITCODE
if ($code -eq 0 -and -not $NoMonitor) {
    Start-MonitorWatch
    Invoke-MonitorOnce
}
exit $code
