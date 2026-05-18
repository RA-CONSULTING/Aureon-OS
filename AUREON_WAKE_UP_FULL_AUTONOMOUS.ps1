[CmdletBinding()]
param(
    [switch]$Production,
    [switch]$LiveTrading,
    [switch]$ConfirmLiveTrading,
    [switch]$Restart,
    [switch]$AccountsAutonomous,
    [switch]$AccountsBuild,
    [switch]$FullCognitiveOrderCapability,
    [switch]$KeepAlive,
    [switch]$SkipIgnition,
    [switch]$SkipMarketTelemetry,
    [switch]$SkipMindHub,
    [switch]$SkipSelfQuestioning,
    [switch]$SkipAutonomousSelfRun,
    [switch]$SkipFrontend,
    [switch]$SkipNpmInstall,
    [switch]$WaitForRefresh,
    [switch]$NoStatusWait,
    [switch]$NoOpen,
    [switch]$ValidateOnly,
    [int]$FrontendPort = 8081,
    [int]$MarketStatusPort = 8790,
    [int]$ObserverInterval = 30,
    [int]$MarketInterval = 1,
    [int]$StatusTimeoutSec = 75,
    [int]$SupervisorIntervalSec = 20,
    [int]$SelfRunIntervalSec = 300
)

$ErrorActionPreference = "Stop"

function Write-Aureon {
    param([string]$Message, [string]$Level = "INFO")
    $stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host "[$stamp] [$Level] $Message"
}

function Resolve-RepoRoot {
    $root = Split-Path -Parent $MyInvocation.ScriptName
    if (-not $root) {
        $root = (Get-Location).Path
    }
    return (Resolve-Path $root).Path
}

function Get-PythonPath {
    param([string]$RepoRoot)
    $venvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"
    if (Test-Path -LiteralPath $venvPython) {
        return $venvPython
    }
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if ($cmd) {
        return $cmd.Source
    }
    throw "Python was not found. Install Python or restore .venv before waking Aureon."
}

function Get-NpmPath {
    $cmd = Get-Command npm.cmd -ErrorAction SilentlyContinue
    if ($cmd) {
        return $cmd.Source
    }
    $cmd = Get-Command npm -ErrorAction SilentlyContinue
    if ($cmd) {
        return $cmd.Source
    }
    throw "npm was not found. Install Node.js/npm before starting the frontend."
}

function Get-MatchingProcess {
    param([string]$Pattern)
    Get-CimInstance Win32_Process |
        Where-Object { $_.CommandLine -and $_.CommandLine -like "*$Pattern*" }
}

function Get-ProcessSummaryById {
    param([int]$ProcessId)
    try {
        $proc = Get-CimInstance Win32_Process -Filter "ProcessId=$ProcessId" -ErrorAction Stop
        if ($null -eq $proc) { return $null }
        return [ordered]@{
            pid = [int]$proc.ProcessId
            parent_pid = [int]$proc.ParentProcessId
            name = $proc.Name
            command_line = $proc.CommandLine
        }
    } catch {
        return $null
    }
}

function Test-ProcessAlive {
    param([int]$ProcessId)
    try {
        $proc = Get-Process -Id $ProcessId -ErrorAction Stop
        return ($null -ne $proc)
    } catch {
        return $false
    }
}

function Get-CurrentProcessTreeIds {
    $ids = @([int]$PID)
    try {
        $proc = Get-CimInstance Win32_Process -Filter "ProcessId=$PID" -ErrorAction Stop
        while ($null -ne $proc -and $proc.ParentProcessId) {
            $parentId = [int]$proc.ParentProcessId
            if ($ids -contains $parentId) { break }
            $ids += $parentId
            $proc = Get-CimInstance Win32_Process -Filter "ProcessId=$parentId" -ErrorAction SilentlyContinue
        }
    } catch {
    }
    return $ids
}

function Get-PortOwnerSummary {
    param([int[]]$Ports)
    $rows = @()
    foreach ($port in @($Ports | Select-Object -Unique)) {
        try {
            $listeners = @(Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue)
        } catch {
            $listeners = @()
        }
        if ($listeners.Count -eq 0) {
            $rows += [ordered]@{
                port = $port
                listening = $false
                pid = $null
                name = $null
                parent_pid = $null
                command_line = $null
            }
            continue
        }
        foreach ($owner in @($listeners | Select-Object -ExpandProperty OwningProcess -Unique | Where-Object { $_ })) {
            $summary = Get-ProcessSummaryById -ProcessId ([int]$owner)
            $rows += [ordered]@{
                port = $port
                listening = $true
                pid = [int]$owner
                name = if ($summary) { $summary.name } else { $null }
                parent_pid = if ($summary) { $summary.parent_pid } else { $null }
                command_line = if ($summary) { $summary.command_line } else { $null }
            }
        }
    }
    return $rows
}

function Stop-MatchingProcess {
    param([string]$Pattern, [string]$Name)
    $matches = @(Get-MatchingProcess -Pattern $Pattern)
    foreach ($proc in $matches) {
        try {
            Write-Aureon "Stopping $Name PID $($proc.ProcessId)" "RESTART"
            Stop-Process -Id $proc.ProcessId -Force -ErrorAction Stop
        } catch {
            Write-Aureon "Could not stop $Name PID $($proc.ProcessId): $($_.Exception.Message)" "WARN"
        }
    }

    if ($matches.Count -gt 0) {
        $deadline = (Get-Date).AddSeconds(15)
        do {
            Start-Sleep -Milliseconds 500
            $remaining = @(Get-MatchingProcess -Pattern $Pattern)
        } while ($remaining.Count -gt 0 -and (Get-Date) -lt $deadline)

        if ($remaining.Count -gt 0) {
            $pids = ($remaining | Select-Object -ExpandProperty ProcessId) -join ", "
            Write-Aureon "$Name restart wait still sees PID(s) $pids; continuing with a fresh start check" "WARN"
        }
    }
}

function Stop-ProcessOnPort {
    param([int]$Port, [string]$Name, [switch]$Force)
    if (-not $Restart -and -not $Force) {
        return
    }
    try {
        $listeners = @(Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue)
    } catch {
        return
    }
    $owners = @($listeners | Select-Object -ExpandProperty OwningProcess -Unique | Where-Object { $_ -and $_ -ne $PID })
    foreach ($owner in $owners) {
        try {
            Write-Aureon "Stopping $Name port $Port owner PID $owner" "RESTART"
            Stop-Process -Id $owner -Force -ErrorAction Stop
        } catch {
            Write-Aureon "Could not stop $Name port $Port owner PID $owner`: $($_.Exception.Message)" "WARN"
        }
    }

    if ($owners.Count -gt 0) {
        $deadline = (Get-Date).AddSeconds(15)
        do {
            Start-Sleep -Milliseconds 500
            $remaining = @(Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue)
        } while ($remaining.Count -gt 0 -and (Get-Date) -lt $deadline)
    }
}

function Test-LocalPortListening {
    param([int]$Port)
    try {
        $listeners = @(Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue)
        return ($listeners.Count -gt 0)
    } catch {
        return $false
    }
}

function Find-FreeLocalPort {
    param([int]$StartPort = 8791, [int]$EndPort = 8799)
    for ($port = $StartPort; $port -le $EndPort; $port++) {
        if (-not (Test-LocalPortListening -Port $port)) {
            return $port
        }
    }
    return $StartPort
}

function Find-ExistingMarketStatusPort {
    param([int]$StartPort = 8791, [int]$EndPort = 8799)
    for ($port = $StartPort; $port -le $EndPort; $port++) {
        $probe = Test-AureonEndpoint -Url "http://127.0.0.1:$port/api/flight-test" -TimeoutSec 1
        if ($probe.ok) {
            return $port
        }
    }
    return 0
}

function Test-LiveStreamCacheFresh {
    param(
        [string]$Path,
        [double]$MaxAgeSec = 30.0
    )
    try {
        if ([string]::IsNullOrWhiteSpace($Path)) { return $false }
        $resolved = $Path
        if (-not [System.IO.Path]::IsPathRooted($resolved)) {
            $resolved = Join-Path $RepoRoot $resolved
        }
        if (-not (Test-Path -LiteralPath $resolved)) { return $false }
        $item = Get-Item -LiteralPath $resolved -ErrorAction Stop
        if ($item.Length -le 0) { return $false }
        $age = ((Get-Date) - $item.LastWriteTime).TotalSeconds
        if ($age -gt $MaxAgeSec) { return $false }
        try {
            $payload = Get-Content -LiteralPath $resolved -Raw -ErrorAction Stop | ConvertFrom-Json
            if ($null -eq $payload.ticker_cache) { return $false }
            $tickerCount = @($payload.ticker_cache.PSObject.Properties).Count
            return ($tickerCount -gt 0)
        } catch {
            return $false
        }
    } catch {
        return $false
    }
}

function Start-AureonProcess {
    param(
        [string]$Name,
        [string]$Pattern,
        [string]$FilePath,
        [string]$Arguments,
        [string]$WorkingDirectory,
        [string]$LogDirectory
    )

    if ($Restart) {
        Stop-MatchingProcess -Pattern $Pattern -Name $Name
        Start-Sleep -Milliseconds 500
    }

    $existing = @(Get-MatchingProcess -Pattern $Pattern)
    if ($existing.Count -gt 0) {
        $pids = ($existing | Select-Object -ExpandProperty ProcessId) -join ", "
        Write-Aureon "$Name already running: PID(s) $pids" "OK"
        return @{
            name = $Name
            status = "already_running"
            pids = @($existing | Select-Object -ExpandProperty ProcessId)
            log = $null
        }
    }

    $safeName = ($Name -replace "[^A-Za-z0-9_-]", "_").ToLowerInvariant()
    $stdout = Join-Path $LogDirectory "$safeName.out.log"
    $stderr = Join-Path $LogDirectory "$safeName.err.log"
    Write-Aureon "Starting $Name"
    $proc = Start-Process `
        -FilePath $FilePath `
        -ArgumentList $Arguments `
        -WorkingDirectory $WorkingDirectory `
        -RedirectStandardOutput $stdout `
        -RedirectStandardError $stderr `
        -WindowStyle Hidden `
        -PassThru

    Start-Sleep -Milliseconds 800
    if (-not (Get-Process -Id $proc.Id -ErrorAction SilentlyContinue)) {
        Write-Aureon "$Name process exited quickly after launch. Check $stderr" "WARN"
    }

    return @{
        name = $Name
        status = "started"
        pids = @($proc.Id)
        stdout = $stdout
        stderr = $stderr
        command = "$FilePath $Arguments"
    }
}

function Start-AureonProcessWithoutStopping {
    param(
        [string]$Name,
        [string]$Pattern,
        [string]$FilePath,
        [string]$Arguments,
        [string]$WorkingDirectory,
        [string]$LogDirectory,
        [string]$LogNameSuffix = ""
    )

    $existing = @(Get-MatchingProcess -Pattern $Pattern)
    if ($existing.Count -gt 0) {
        $pids = ($existing | Select-Object -ExpandProperty ProcessId) -join ", "
        Write-Aureon "$Name already running: PID(s) $pids" "OK"
        return @{
            name = $Name
            status = "already_running"
            pids = @($existing | Select-Object -ExpandProperty ProcessId)
            log = $null
        }
    }

    $safeName = ($Name -replace "[^A-Za-z0-9_-]", "_").ToLowerInvariant()
    if (-not [string]::IsNullOrWhiteSpace($LogNameSuffix)) {
        $safeName = "$safeName-$LogNameSuffix"
    }
    $stdout = Join-Path $LogDirectory "$safeName.out.log"
    $stderr = Join-Path $LogDirectory "$safeName.err.log"
    Write-Aureon "Starting $Name without stopping live surfaces"
    $proc = Start-Process `
        -FilePath $FilePath `
        -ArgumentList $Arguments `
        -WorkingDirectory $WorkingDirectory `
        -RedirectStandardOutput $stdout `
        -RedirectStandardError $stderr `
        -WindowStyle Hidden `
        -PassThru

    Start-Sleep -Milliseconds 800
    if (-not (Get-Process -Id $proc.Id -ErrorAction SilentlyContinue)) {
        Write-Aureon "$Name process exited quickly after launch. Check $stderr" "WARN"
    }

    return @{
        name = $Name
        status = "started_no_stop"
        pids = @($proc.Id)
        stdout = $stdout
        stderr = $stderr
        command = "$FilePath $Arguments"
    }
}

function Invoke-NativeLogged {
    param(
        [string]$Name,
        [string]$FilePath,
        [string[]]$Arguments,
        [string]$WorkingDirectory,
        [string]$StdoutPath,
        [string]$StderrPath
    )

    $proc = Start-Process `
        -FilePath $FilePath `
        -ArgumentList $Arguments `
        -WorkingDirectory $WorkingDirectory `
        -RedirectStandardOutput $StdoutPath `
        -RedirectStandardError $StderrPath `
        -WindowStyle Hidden `
        -Wait `
        -PassThru

    if ($proc.ExitCode -ne 0) {
        Write-Aureon "$Name exited with code $($proc.ExitCode). Check $StderrPath" "WARN"
    }
    return [int]$proc.ExitCode
}

function Invoke-Refresh {
    param([string]$Python, [string]$RepoRoot, [string]$LogDirectory)
    $refreshLog = Join-Path $LogDirectory "manifest_refresh.out.log"
    $refreshErr = Join-Path $LogDirectory "manifest_refresh.err.log"
    $modules = @(
        "aureon.autonomous.aureon_saas_system_inventory",
        "aureon.autonomous.aureon_frontend_unification_plan",
        "aureon.autonomous.aureon_frontend_evolution_queue",
        "aureon.autonomous.aureon_autonomous_capability_switchboard",
        "aureon.autonomous.aureon_unified_ui_builder",
        "aureon.autonomous.aureon_trading_intelligence_checklist",
        "aureon.autonomous.aureon_exchange_monitoring_checklist",
        "aureon.autonomous.aureon_exchange_data_capability_matrix",
        "aureon.autonomous.aureon_global_financial_coverage_map",
        "aureon.autonomous.aureon_organism_runtime_observer --refresh-core"
    )

    foreach ($module in $modules) {
        Write-Aureon "Refreshing $module"
        $parts = $module -split " "
        $moduleName = $parts[0]
        $extra = @()
        if ($parts.Count -gt 1) {
            $extra = $parts[1..($parts.Count - 1)]
        }
        $args = @("-m", $moduleName) + $extra
        $exitCode = Invoke-NativeLogged `
            -Name "Refresh $module" `
            -FilePath $Python `
            -Arguments $args `
            -WorkingDirectory $RepoRoot `
            -StdoutPath $refreshLog `
            -StderrPath $refreshErr
        if ($exitCode -ne 0) {
            Write-Aureon "Refresh step failed: $module. Check $refreshErr" "WARN"
        }
    }
}

function Test-AureonEndpoint {
    param([string]$Url, [int]$TimeoutSec = 3)
    try {
        $response = Invoke-WebRequest -Uri $Url -TimeoutSec $TimeoutSec -UseBasicParsing
        return @{
            url = $Url
            ok = $true
            status = [int]$response.StatusCode
            length = [int]$response.Content.Length
            error = ""
        }
    } catch {
        return @{
            url = $Url
            ok = $false
            status = 0
            length = 0
            error = $_.Exception.Message
        }
    }
}

function Get-AureonMindFlightTest {
    param([int]$TimeoutSec = 5)
    try {
        $response = Invoke-WebRequest -Uri "http://127.0.0.1:13002/api/flight-test" -TimeoutSec $TimeoutSec -UseBasicParsing
        return ($response.Content | ConvertFrom-Json)
    } catch {
        return $null
    }
}

function Get-AureonMarketFlightTest {
    param([int]$TimeoutSec = 5)
    try {
        $response = Invoke-WebRequest -Uri $RuntimeFlightUrl -TimeoutSec $TimeoutSec -UseBasicParsing
        return ($response.Content | ConvertFrom-Json)
    } catch {
        return $null
    }
}

function Test-AureonDayAllowed {
    param([string]$DayName, [string]$AllowedDays)
    $raw = if ([string]::IsNullOrWhiteSpace($AllowedDays)) { "Sun" } else { $AllowedDays }
    $value = $raw.Trim().ToLowerInvariant()
    if ($value -in @("*", "all", "daily", "everyday")) {
        return $true
    }
    $current = $DayName.Substring(0, 3).ToLowerInvariant()
    foreach ($part in ($value -split "[,;]")) {
        $item = $part.Trim()
        if ($item.Length -eq 0) { continue }
        if ($item -eq $current -or $item -eq $DayName.ToLowerInvariant()) {
            return $true
        }
        if ($item.Contains("-")) {
            $pieces = $item.Split("-", 2)
            $names = @("mon", "tue", "wed", "thu", "fri", "sat", "sun")
            $start = [Array]::IndexOf($names, $pieces[0].Trim().Substring(0, 3).ToLowerInvariant())
            $end = [Array]::IndexOf($names, $pieces[1].Trim().Substring(0, 3).ToLowerInvariant())
            $now = [Array]::IndexOf($names, $current)
            if ($start -ge 0 -and $end -ge 0 -and $now -ge 0) {
                if ($start -le $end -and $now -ge $start -and $now -le $end) { return $true }
                if ($start -gt $end -and ($now -ge $start -or $now -le $end)) { return $true }
            }
        }
    }
    return $false
}

function Test-AureonMindDowntimeWindow {
    $days = if ($env:AUREON_MIND_DOWNTIME_DAYS) { $env:AUREON_MIND_DOWNTIME_DAYS } else { "Sun" }
    $startRaw = if ($env:AUREON_MIND_DOWNTIME_START_LOCAL) { $env:AUREON_MIND_DOWNTIME_START_LOCAL } else { "03:00" }
    $endRaw = if ($env:AUREON_MIND_DOWNTIME_END_LOCAL) { $env:AUREON_MIND_DOWNTIME_END_LOCAL } else { "03:15" }
    try {
        $start = [TimeSpan]::Parse($startRaw)
        $end = [TimeSpan]::Parse($endRaw)
    } catch {
        $start = [TimeSpan]::Parse("03:00")
        $end = [TimeSpan]::Parse("03:15")
    }

    $now = Get-Date
    $todayAllowed = Test-AureonDayAllowed -DayName $now.DayOfWeek.ToString() -AllowedDays $days
    $todayStart = $now.Date.Add($start)
    $todayEnd = $now.Date.Add($end)
    if ($end -le $start) {
        $todayEnd = $todayEnd.AddDays(1)
    }
    if ($todayAllowed -and $now -ge $todayStart -and $now -lt $todayEnd) {
        return $true
    }

    if ($end -le $start) {
        $yesterday = $now.AddDays(-1)
        $yesterdayAllowed = Test-AureonDayAllowed -DayName $yesterday.DayOfWeek.ToString() -AllowedDays $days
        $previousStart = $now.Date.AddDays(-1).Add($start)
        $previousEnd = $now.Date.Add($end)
        if ($yesterdayAllowed -and $now -ge $previousStart -and $now -lt $previousEnd) {
            return $true
        }
    }
    return $false
}

function Test-AureonMarketDowntimeWindow {
    $days = if ($env:AUREON_MARKET_DOWNTIME_DAYS) { $env:AUREON_MARKET_DOWNTIME_DAYS } elseif ($env:AUREON_MIND_DOWNTIME_DAYS) { $env:AUREON_MIND_DOWNTIME_DAYS } else { "Sun" }
    $startRaw = if ($env:AUREON_MARKET_DOWNTIME_START_LOCAL) { $env:AUREON_MARKET_DOWNTIME_START_LOCAL } elseif ($env:AUREON_MIND_DOWNTIME_START_LOCAL) { $env:AUREON_MIND_DOWNTIME_START_LOCAL } else { "03:00" }
    $endRaw = if ($env:AUREON_MARKET_DOWNTIME_END_LOCAL) { $env:AUREON_MARKET_DOWNTIME_END_LOCAL } elseif ($env:AUREON_MIND_DOWNTIME_END_LOCAL) { $env:AUREON_MIND_DOWNTIME_END_LOCAL } else { "03:15" }
    try {
        $start = [TimeSpan]::Parse($startRaw)
        $end = [TimeSpan]::Parse($endRaw)
    } catch {
        $start = [TimeSpan]::Parse("03:00")
        $end = [TimeSpan]::Parse("03:15")
    }

    $now = Get-Date
    $todayAllowed = Test-AureonDayAllowed -DayName $now.DayOfWeek.ToString() -AllowedDays $days
    $todayStart = $now.Date.Add($start)
    $todayEnd = $now.Date.Add($end)
    if ($end -le $start) {
        $todayEnd = $todayEnd.AddDays(1)
    }
    if ($todayAllowed -and $now -ge $todayStart -and $now -lt $todayEnd) {
        return $true
    }

    if ($end -le $start) {
        $yesterday = $now.AddDays(-1)
        $yesterdayAllowed = Test-AureonDayAllowed -DayName $yesterday.DayOfWeek.ToString() -AllowedDays $days
        $previousStart = $now.Date.AddDays(-1).Add($start)
        $previousEnd = $now.Date.Add($end)
        if ($yesterdayAllowed -and $now -ge $previousStart -and $now -lt $previousEnd) {
            return $true
        }
    }
    return $false
}

function Get-AureonRuntimeState {
    param([int]$TimeoutSec = 5)
    try {
        $response = Invoke-WebRequest -Uri $RuntimeFeedUrl -TimeoutSec $TimeoutSec -UseBasicParsing
        return ($response.Content | ConvertFrom-Json)
    } catch {
        return $null
    }
}

function Test-AureonRuntimeHasOpenPositions {
    param($RuntimeState)
    if ($null -eq $RuntimeState) {
        return $true
    }
    try {
        if ($null -ne $RuntimeState.combined -and $null -ne $RuntimeState.combined.open_positions) {
            return ([int]$RuntimeState.combined.open_positions -gt 0)
        }
        if ($null -ne $RuntimeState.positions -and $RuntimeState.positions.Count -gt 0) {
            return $true
        }
        return $false
    } catch {
        return $true
    }
}

function Get-AureonRuntimeWriterPid {
    param($RuntimeState)
    try {
        if ($null -eq $RuntimeState -or $null -eq $RuntimeState.runtime_writer -or $null -eq $RuntimeState.runtime_writer.pid) {
            return 0
        }
        return [int]$RuntimeState.runtime_writer.pid
    } catch {
        return 0
    }
}

function Test-AureonRuntimeWriterAlive {
    param($RuntimeState)
    $writerPid = Get-AureonRuntimeWriterPid -RuntimeState $RuntimeState
    if ($writerPid -le 0) {
        return $false
    }
    return (Test-ProcessAlive -ProcessId $writerPid)
}

function Test-AureonRuntimeLiveTradingArmed {
    param($RuntimeState)
    if ($null -eq $RuntimeState) {
        return $false
    }
    try {
        $plan = $RuntimeState.exchange_action_plan
        if ($null -eq $plan) {
            return $false
        }
        $globalBlockers = @()
        if ($null -ne $plan.global_blockers) {
            $globalBlockers = @($plan.global_blockers | ForEach-Object { [string]$_ })
        }
        $requiredCleared = @(
            "live_trading_not_enabled",
            "real_orders_disabled",
            "exchange_mutations_disabled",
            "order_intent_publish_disabled"
        )
        foreach ($blocker in $requiredCleared) {
            if ($globalBlockers -contains $blocker) {
                return $false
            }
        }
        return (
            [bool]$plan.order_intent_publish_enabled -and
            [bool]$plan.executor_enabled -and
            (-not [bool]$plan.real_orders_disabled) -and
            (-not [bool]$plan.exchange_mutations_disabled)
        )
    } catch {
        return $false
    }
}

function Complete-AureonMindRebootIntent {
    param([string]$Status = "completed")
    try {
        if ([string]::IsNullOrWhiteSpace($StateRoot)) { return }
        $intentPath = Join-Path $StateRoot "aureon_reboot_intent.json"
        if (-not (Test-Path -LiteralPath $intentPath)) { return }
        $payload = Get-Content -LiteralPath $intentPath -Raw | ConvertFrom-Json
        $payload | Add-Member -NotePropertyName status -NotePropertyValue $Status -Force
        $payload | Add-Member -NotePropertyName completed_at -NotePropertyValue (Get-Date).ToString("o") -Force
        $payload | Add-Member -NotePropertyName completed_by -NotePropertyValue "AUREON_WAKE_UP_FULL_AUTONOMOUS supervisor" -Force
        $payload | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $intentPath -Encoding UTF8
    } catch {
        Write-Aureon "Could not update reboot intent: $($_.Exception.Message)" "WARN"
    }
}

function Request-AureonMindRebootIntent {
    param(
        [string]$Reason = "planned_mind_hub_update",
        [string]$ChangeId = "mind_hub_goal_pursuit_flight_test"
    )
    try {
        if ([string]::IsNullOrWhiteSpace($StateRoot)) { return }
        New-Item -ItemType Directory -Force -Path $StateRoot | Out-Null
        $intentPath = Join-Path $StateRoot "aureon_reboot_intent.json"
        $payload = [ordered]@{
            status = "pending"
            surface = "mind"
            requested_by = "AUREON_WAKE_UP_FULL_AUTONOMOUS supervisor"
            reason = $Reason
            change_id = $ChangeId
            requested_at = (Get-Date).ToString("o")
            policy = "reboot only after internal flight test and configured downtime window approve"
        }
        $payload | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $intentPath -Encoding UTF8
    } catch {
        Write-Aureon "Could not write reboot intent: $($_.Exception.Message)" "WARN"
    }
}

function Complete-AureonMarketRebootIntent {
    param([string]$Status = "completed")
    try {
        if ([string]::IsNullOrWhiteSpace($StateRoot)) { return }
        $intentPath = Join-Path $StateRoot "aureon_market_reboot_intent.json"
        if (-not (Test-Path -LiteralPath $intentPath)) { return }
        $payload = Get-Content -LiteralPath $intentPath -Raw | ConvertFrom-Json
        $payload | Add-Member -NotePropertyName status -NotePropertyValue $Status -Force
        $payload | Add-Member -NotePropertyName completed_at -NotePropertyValue (Get-Date).ToString("o") -Force
        $payload | Add-Member -NotePropertyName completed_by -NotePropertyValue "AUREON_WAKE_UP_FULL_AUTONOMOUS supervisor" -Force
        $payload | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $intentPath -Encoding UTF8
    } catch {
        Write-Aureon "Could not update market reboot intent: $($_.Exception.Message)" "WARN"
    }
}

function Complete-AureonEnvUpdateIntent {
    param([string]$Status = "completed")
    try {
        if ([string]::IsNullOrWhiteSpace($StateRoot)) { return }
        $intentPath = Join-Path $StateRoot "aureon_env_update_intent.json"
        if (-not (Test-Path -LiteralPath $intentPath)) { return }
        $payload = Get-Content -LiteralPath $intentPath -Raw | ConvertFrom-Json
        if ($payload.status -ne "pending") { return }
        $payload | Add-Member -NotePropertyName status -NotePropertyValue $Status -Force
        $payload | Add-Member -NotePropertyName completed_at -NotePropertyValue (Get-Date).ToString("o") -Force
        $payload | Add-Member -NotePropertyName completed_by -NotePropertyValue "AUREON_WAKE_UP_FULL_AUTONOMOUS supervisor" -Force
        $payload | Add-Member -NotePropertyName secret_policy -NotePropertyValue "metadata_only_no_values_returned" -Force
        $payload | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $intentPath -Encoding UTF8
    } catch {
        Write-Aureon "Could not update env credential reload intent: $($_.Exception.Message)" "WARN"
    }
}

function Request-AureonMarketRebootIntent {
    param(
        [string]$Reason = "planned_market_runtime_update",
        [string]$ChangeId = "unified_market_api_governor"
    )
    try {
        if ([string]::IsNullOrWhiteSpace($StateRoot)) { return }
        New-Item -ItemType Directory -Force -Path $StateRoot | Out-Null
        $intentPath = Join-Path $StateRoot "aureon_market_reboot_intent.json"
        $payload = [ordered]@{
            status = "pending"
            surface = "market"
            requested_by = "AUREON_WAKE_UP_FULL_AUTONOMOUS supervisor"
            reason = $Reason
            change_id = $ChangeId
            requested_at = (Get-Date).ToString("o")
            policy = "restart only when runtime is live, configured downtime window is active, and no open positions are reported"
        }
        $payload | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $intentPath -Encoding UTF8
    } catch {
        Write-Aureon "Could not write market reboot intent: $($_.Exception.Message)" "WARN"
    }
}

function Restart-AureonMarketStatusServerOnly {
    if ($SkipMarketTelemetry) { return }
    Stop-MatchingProcess -Pattern "aureon.exchanges.unified_market_status_server" -Name "Unified market status server"
    try {
        $listeners = @(Get-NetTCPConnection -State Listen -LocalPort $MarketStatusPort -ErrorAction SilentlyContinue)
        $owners = @($listeners | Select-Object -ExpandProperty OwningProcess -Unique | Where-Object { $_ })
        if ($owners.Count -gt 0) {
            $ownerList = ($owners -join ", ")
            Write-Aureon "Port $MarketStatusPort is owned by PID(s) $ownerList; not stopping trading runtime during status-only refresh" "WARN"
        }
    } catch {
        Write-Aureon "Could not inspect port $MarketStatusPort before status-only refresh: $($_.Exception.Message)" "WARN"
    }
    Start-AureonProcess `
        -Name "Unified market status server" `
        -Pattern "aureon.exchanges.unified_market_status_server --port $MarketStatusPort" `
        -FilePath $Python `
        -Arguments "-m aureon.exchanges.unified_market_status_server --port $MarketStatusPort" `
        -WorkingDirectory $RepoRoot `
        -LogDirectory $LogRoot | Out-Null
}

function Start-AureonMarketTelemetryWriterOnly {
    param([string]$Reason = "runtime_writer_takeover")
    if ($SkipMarketTelemetry) { return $null }

    $marketArgs = "-m aureon.exchanges.unified_market_trader --interval $MarketInterval"
    if (-not $LiveTrading) { $marketArgs += " --dry-run" }
    Write-Aureon "Market runtime writer takeover requested ($Reason); preserving status server and open-position continuity" "WATCH"
    return Start-AureonProcessWithoutStopping `
        -Name "Unified market telemetry" `
        -Pattern "aureon.exchanges.unified_market_trader" `
        -FilePath $Python `
        -Arguments $marketArgs `
        -WorkingDirectory $RepoRoot `
        -LogDirectory $LogRoot `
        -LogNameSuffix "writer-takeover"
}

function Wait-AureonEndpoint {
    param([string]$Name, [string]$Url, [int]$TimeoutSec = 75)
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    do {
        $result = Test-AureonEndpoint -Url $Url -TimeoutSec 3
        if ($result.ok) {
            Write-Aureon "$Name online: $Url" "ALIVE"
            return $result
        }
        Start-Sleep -Seconds 2
    } while ((Get-Date) -lt $deadline)

    Write-Aureon "$Name not ready: $Url :: $($result.error)" "WARN"
    return $result
}

$RepoRoot = Resolve-RepoRoot
Set-Location $RepoRoot

$ProductionMode = $false
if ($Production) {
    $ProductionMode = $true
    $LiveTrading = $true
    $ConfirmLiveTrading = $true
    $Restart = $true
    $AccountsAutonomous = $true
    $FullCognitiveOrderCapability = $true
    $KeepAlive = $true
    if ($StatusTimeoutSec -lt 120) {
        $StatusTimeoutSec = 120
    }
}

$Python = Get-PythonPath -RepoRoot $RepoRoot
$Npm = Get-NpmPath
$FrontendRoot = Join-Path $RepoRoot "frontend"
$LogRoot = Join-Path $RepoRoot "logs\wake_up"
$StateRoot = Join-Path $RepoRoot "state"
New-Item -ItemType Directory -Force -Path $LogRoot, $StateRoot | Out-Null
$manifestPath = Join-Path $StateRoot "aureon_wake_up_manifest.json"
$publicManifestPath = Join-Path $FrontendRoot "public\aureon_wake_up_manifest.json"
$supervisorLockPath = Join-Path $StateRoot "aureon_supervisor_lock.json"
$script:LastPublicManifestWarningAt = [datetime]::MinValue
$script:PublicManifestWarningCooldownSec = 300

function Get-SupervisorLockPayload {
    param([string]$Status = "active")
    return [ordered]@{
        status = $Status
        pid = [int]$PID
        repo_root = $RepoRoot
        mode = $Mode
        frontend_port = $FrontendPort
        market_status_port = $MarketStatusPort
        runtime_feed_url = $RuntimeFeedUrl
        runtime_flight_test_url = $RuntimeFlightUrl
        runtime_reboot_advice_url = $RuntimeRebootAdviceUrl
        started_at = (Get-Date).ToString("o")
        heartbeat_at = (Get-Date).ToString("o")
        process = (Get-ProcessSummaryById -ProcessId ([int]$PID))
        parent_tree = @((Get-CurrentProcessTreeIds) | ForEach-Object { Get-ProcessSummaryById -ProcessId ([int]$_) })
        policy = "single production supervisor per repo; market runtime restart remains flight-test and downtime gated"
    }
}

function Write-SupervisorLock {
    param([string]$Status = "active")
    try {
        $payload = Get-SupervisorLockPayload -Status $Status
        $payload | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $supervisorLockPath -Encoding UTF8
    } catch {
        Write-Aureon "Supervisor lock update failed: $($_.Exception.Message)" "WARN"
    }
}

function Assert-SingleProductionSupervisor {
    if (-not $ProductionMode -or -not $KeepAlive) { return }

    if (Test-Path -LiteralPath $supervisorLockPath) {
        try {
            $existingLock = Get-Content -LiteralPath $supervisorLockPath -Raw | ConvertFrom-Json
            $existingPid = [int]($existingLock.pid)
            if ($existingPid -and $existingPid -ne $PID -and (Test-ProcessAlive -ProcessId $existingPid)) {
                throw "Aureon production supervisor lock is active at PID $existingPid. Close that supervisor or remove stale lock $supervisorLockPath only after confirming PID $existingPid is gone."
            }
        } catch {
            if ($_.Exception.Message -like "Aureon production supervisor lock is active*") { throw }
            Write-Aureon "Ignoring unreadable stale supervisor lock: $($_.Exception.Message)" "WARN"
        }
    }

    $currentTree = @(Get-CurrentProcessTreeIds)
    $otherSupervisors = @(
        Get-CimInstance Win32_Process |
            Where-Object {
                $_.CommandLine -and
                $_.CommandLine -like "*$RepoRoot*" -and
                ($_.CommandLine -like "*AUREON_WAKE_UP_FULL_AUTONOMOUS.ps1*" -or $_.CommandLine -like "*AUREON_PRODUCTION_LIVE.cmd*") -and
                ($currentTree -notcontains [int]$_.ProcessId)
            } |
            Select-Object ProcessId, ParentProcessId, Name, CommandLine
    )
    if ($otherSupervisors.Count -gt 0) {
        $details = ($otherSupervisors | ForEach-Object { "PID $($_.ProcessId) $($_.Name): $($_.CommandLine)" }) -join "`n"
        throw "Another Aureon production launcher/supervisor is already running. Close the duplicate before relaunching.`n$details"
    }

    Write-SupervisorLock -Status "active"
}

function New-WakeManifestPayload {
    param([array]$Statuses, [array]$StartedProcesses = @(), [bool]$SupervisorMode = $false)
    $payload = [ordered]@{
        generated_at = (Get-Date).ToString("o")
        repo_root = $RepoRoot
        mode = $Mode
        frontend_url = "http://127.0.0.1:$FrontendPort/"
        mind_hub_url = "http://127.0.0.1:13002/"
        runtime_feed_url = $RuntimeFeedUrl
        runtime_flight_test_url = $RuntimeFlightUrl
        runtime_reboot_advice_url = $RuntimeRebootAdviceUrl
        logs = $LogRoot
        supervisor_lock = [ordered]@{
            path = $supervisorLockPath
            pid = [int]$PID
            active = $SupervisorMode
            process = (Get-ProcessSummaryById -ProcessId ([int]$PID))
        }
        port_owners = @(Get-PortOwnerSummary -Ports @($FrontendPort, $MarketStatusPort, 8790, 8791, 13002))
        live_safety_flags = [ordered]@{
            live_trading = $env:AUREON_LIVE_TRADING
            live = $env:LIVE
            dry_run = $env:DRY_RUN
            aureon_dry_run = $env:AUREON_DRY_RUN
            disable_real_orders = $env:AUREON_DISABLE_REAL_ORDERS
            disable_exchange_mutations = $env:AUREON_DISABLE_EXCHANGE_MUTATIONS
            allow_sim_fallback = $env:AUREON_ALLOW_SIM_FALLBACK
            order_authority_mode = $env:AUREON_ORDER_AUTHORITY_MODE
            order_intent_publish = $env:AUREON_ORDER_INTENT_PUBLISH
            unified_order_executor = $env:AUREON_UNIFIED_ORDER_EXECUTOR
        }
        safety = [ordered]@{
            llm_live_capabilities = $env:AUREON_LLM_LIVE_CAPABILITIES
            cognitive_live_mode = $env:AUREON_COGNITIVE_LIVE_MODE
            llm_order_authority = $env:AUREON_LLM_ORDER_AUTHORITY
            cognitive_order_authority = $env:AUREON_COGNITIVE_ORDER_AUTHORITY
            llm_order_intent_authority = $env:AUREON_LLM_ORDER_INTENT_AUTHORITY
            cognitive_order_intent_authority = $env:AUREON_COGNITIVE_ORDER_INTENT_AUTHORITY
            order_authority_mode = $env:AUREON_ORDER_AUTHORITY_MODE
            order_intent_publish = $env:AUREON_ORDER_INTENT_PUBLISH
            order_ticket_requires_executor = $env:AUREON_ORDER_TICKET_REQUIRES_EXECUTOR
            unified_order_executor = $env:AUREON_UNIFIED_ORDER_EXECUTOR
            live_trading = $env:AUREON_LIVE_TRADING
            disable_real_orders = $env:AUREON_DISABLE_REAL_ORDERS
            disable_exchange_mutations = $env:AUREON_DISABLE_EXCHANGE_MUTATIONS
            allow_sim_fallback = $env:AUREON_ALLOW_SIM_FALLBACK
            official_filing_disabled = $env:AUREON_DISABLE_OFFICIAL_FILING
            payments_disabled = $env:AUREON_DISABLE_PAYMENTS
            external_attacks_disabled = $env:AUREON_DISABLE_EXTERNAL_ATTACKS
        }
        api_governor = [ordered]@{
            market_interval_sec = $MarketInterval
            central_beat_refresh_sec = $env:UNIFIED_CENTRAL_BEAT_REFRESH_SEC
            stream_cache_path = $env:WS_PRICE_CACHE_PATH
            stream_cache_write_interval_sec = $env:WS_FEED_WRITE_INTERVAL_S
            stream_price_max_age_sec = $env:UNIFIED_STREAM_PRICE_MAX_AGE_SEC
            stream_cache_max_symbols = $env:UNIFIED_STREAM_CACHE_MAX_SYMBOLS
            fast_money_min_volatility_pct = $env:UNIFIED_FAST_MONEY_MIN_VOLATILITY_PCT
            fast_money_break_even_move_pct = $env:UNIFIED_FAST_MONEY_BREAK_EVEN_MOVE_PCT
            fast_money_volume_usd_target = $env:UNIFIED_FAST_MONEY_VOLUME_USD_TARGET
            fast_money_min_score = $env:UNIFIED_FAST_MONEY_MIN_SCORE
            orderbook_probe_max_per_tick = $env:UNIFIED_ORDERBOOK_PROBE_MAX_PER_TICK
            orderbook_probe_min_interval_sec = $env:UNIFIED_ORDERBOOK_PROBE_MIN_INTERVAL_SEC
            orderbook_probe_stale_ttl_sec = $env:UNIFIED_ORDERBOOK_PROBE_STALE_TTL_SEC
            capital_fast_profit_capture_enabled = $env:CAPITAL_FAST_PROFIT_CAPTURE_ENABLED
            capital_fast_profit_min_gbp = $env:CAPITAL_FAST_PROFIT_MIN_GBP
            capital_fast_profit_min_pct = $env:CAPITAL_FAST_PROFIT_MIN_PCT
            capital_fast_profit_min_hold_sec = $env:CAPITAL_FAST_PROFIT_MIN_HOLD_SECS
            capital_fast_profit_market_status_ttl_sec = $env:CAPITAL_FAST_PROFIT_MARKET_STATUS_TTL_SECS
            kraken_fast_profit_capture_enabled = $env:KRAKEN_FAST_PROFIT_CAPTURE_ENABLED
            kraken_fast_profit_min_usd = $env:KRAKEN_FAST_PROFIT_MIN_USD
            kraken_fast_profit_min_hold_sec = $env:KRAKEN_FAST_PROFIT_MIN_HOLD_SECS
            kraken_spot_fast_profit_capture_enabled = $env:KRAKEN_SPOT_FAST_PROFIT_CAPTURE_ENABLED
            kraken_spot_fast_profit_min_usd = $env:KRAKEN_SPOT_FAST_PROFIT_MIN_USD
            kraken_spot_fast_profit_min_hold_sec = $env:KRAKEN_SPOT_FAST_PROFIT_MIN_HOLD_SEC
            kraken_spot_taker_fee_rate = $env:KRAKEN_SPOT_TAKER_FEE_RATE
            kraken_spot_collateral_reserve_usd = $env:KRAKEN_SPOT_COLLATERAL_RESERVE_USD
            probe_symbol_min_interval_sec = $env:UNIFIED_PROBE_SYMBOL_MIN_INTERVAL_SEC
            probe_symbol_stale_ttl_sec = $env:UNIFIED_PROBE_SYMBOL_STALE_TTL_SEC
            kraken_calls_per_min = $env:UNIFIED_KRAKEN_CALLS_PER_MIN
            capital_calls_per_min = $env:UNIFIED_CAPITAL_CALLS_PER_MIN
            alpaca_calls_per_min = $env:UNIFIED_ALPACA_CALLS_PER_MIN
            binance_calls_per_min = $env:UNIFIED_BINANCE_CALLS_PER_MIN
            rate_backoff_sec = $env:UNIFIED_EXCHANGE_RATE_BACKOFF_SEC
            order_intent_min_interval_sec = $env:UNIFIED_ORDER_INTENT_MIN_INTERVAL_SEC
            order_intent_min_confidence = $env:UNIFIED_ORDER_INTENT_MIN_CONFIDENCE
            order_executor_min_interval_sec = $env:UNIFIED_ORDER_EXECUTOR_MIN_INTERVAL_SEC
            order_executor_symbol_cooldown_sec = $env:UNIFIED_ORDER_EXECUTOR_SYMBOL_COOLDOWN_SEC
            order_executor_quote_usd = $env:UNIFIED_ORDER_EXECUTOR_QUOTE_USD
            order_executor_max_per_tick = $env:UNIFIED_ORDER_EXECUTOR_MAX_PER_TICK
            kraken_spot_quote_usd = $env:UNIFIED_KRAKEN_SPOT_QUOTE_USD
            binance_margin_leverage = $env:UNIFIED_BINANCE_MARGIN_LEVERAGE
        }
        processes = $StartedProcesses
        endpoints = $Statuses
    }
    if ($SupervisorMode) {
        $payload.supervisor = [ordered]@{
            keep_alive = $true
            production_mode = $ProductionMode
            interval_sec = $SupervisorIntervalSec
            last_check = (Get-Date).ToString("o")
        }
    }
    return $payload
}

function Set-AureonAtomicTextFile {
    param([string]$LiteralPath, [string]$Content)
    try {
        $dir = Split-Path -Parent $LiteralPath
        if (-not [string]::IsNullOrWhiteSpace($dir)) {
            New-Item -ItemType Directory -Force -Path $dir | Out-Null
        }
        $name = [System.IO.Path]::GetFileName($LiteralPath)
        $tmpPath = Join-Path $dir ".$name.$PID.tmp"
        $Content | Set-Content -LiteralPath $tmpPath -Encoding UTF8
        Move-Item -LiteralPath $tmpPath -Destination $LiteralPath -Force -ErrorAction Stop
        return @{ ok = $true; error = "" }
    } catch {
        try {
            if ($tmpPath -and (Test-Path -LiteralPath $tmpPath)) {
                Remove-Item -LiteralPath $tmpPath -Force -ErrorAction SilentlyContinue
            }
        } catch {
        }
        return @{ ok = $false; error = $_.Exception.Message }
    }
}

function Write-ThrottledPublicManifestWarning {
    param([string]$Message)
    $now = Get-Date
    if (($now - $script:LastPublicManifestWarningAt).TotalSeconds -ge $script:PublicManifestWarningCooldownSec) {
        Write-Aureon $Message "WARN"
        $script:LastPublicManifestWarningAt = $now
    }
}

function Write-WakeManifest {
    param([object]$Payload)
    try {
        $json = $Payload | ConvertTo-Json -Depth 12
        $stateResult = Set-AureonAtomicTextFile -LiteralPath $manifestPath -Content $json
        if (-not $stateResult.ok) {
            Write-Aureon "Wake-up state manifest write failed: $($stateResult.error)" "WARN"
        }
        $publicResult = Set-AureonAtomicTextFile -LiteralPath $publicManifestPath -Content $json
        if (-not $publicResult.ok) {
            $fallbackPath = Join-Path (Split-Path -Parent $publicManifestPath) "aureon_wake_up_manifest.next.json"
            $fallbackResult = Set-AureonAtomicTextFile -LiteralPath $fallbackPath -Content $json
            $fallbackNote = if ($fallbackResult.ok) { " fallback=$fallbackPath" } else { " fallback_failed=$($fallbackResult.error)" }
            Write-ThrottledPublicManifestWarning -Message "Public wake-up manifest is locked; state manifest remains authoritative.$fallbackNote error=$($publicResult.error)"
        }
    } catch {
        Write-Aureon "Wake-up manifest write failed: $($_.Exception.Message)" "WARN"
    }
}

$LegacyMarketRuntimeOnDefaultPort = $false
$LegacyMarketRuntimePids = @()
if ($MarketStatusPort -eq 8790) {
    $defaultFlightProbe = Test-AureonEndpoint -Url "http://127.0.0.1:8790/api/flight-test" -TimeoutSec 2
    if ((-not $defaultFlightProbe.ok) -and (Test-LocalPortListening -Port 8790)) {
        try {
            $LegacyMarketRuntimePids = @(
                Get-NetTCPConnection -State Listen -LocalPort 8790 -ErrorAction SilentlyContinue |
                    Select-Object -ExpandProperty OwningProcess -Unique |
                    Where-Object { $_ }
            )
        } catch {
            $LegacyMarketRuntimePids = @()
        }
        $LegacyMarketRuntimeOnDefaultPort = $true
        $fallbackPort = Find-ExistingMarketStatusPort -StartPort 8791 -EndPort 8799
        if ($fallbackPort -le 0) {
            $fallbackPort = Find-FreeLocalPort -StartPort 8791 -EndPort 8799
        }
        Write-Aureon "Port 8790 is occupied by an older runtime without flight-test; using read-only status fallback port $fallbackPort" "WARN"
        $MarketStatusPort = $fallbackPort
    }
}
$RuntimeFeedUrl = "http://127.0.0.1:$MarketStatusPort/api/terminal-state"
$RuntimeFlightUrl = "http://127.0.0.1:$MarketStatusPort/api/flight-test"
$RuntimeRebootAdviceUrl = "http://127.0.0.1:$MarketStatusPort/api/reboot-advice"

if ($LiveTrading -and -not $ConfirmLiveTrading) {
    throw "Live trading was requested. Re-run with both -LiveTrading and -ConfirmLiveTrading if you really want exchange mutation gates opened."
}

$env:PYTHONUNBUFFERED = "1"
$env:PYTHONIOENCODING = "utf-8"
$env:AUREON_WAKE_UP_LAUNCHER = "1"
$env:AUREON_FRONTEND_PORT = "$FrontendPort"
$env:AUREON_RUNTIME_FEED_URL = $RuntimeFeedUrl
$env:VITE_AUREON_TERMINAL_STATE_URL = $RuntimeFeedUrl
$env:VITE_LOCAL_TERMINAL_URL = $RuntimeFeedUrl
$env:AUREON_SELF_QUESTIONING_AI = "1"
$env:AUREON_SELF_QUESTIONING_START_DELAY_S = "15"
$env:AUREON_SELF_QUESTION_INTERVAL_S = "300"
$env:AUREON_GOAL_PURSUIT_INTERVAL_SEC = "60"
$env:AUREON_PRIMARY_GOAL = "sustain_live_trading_and_grow_equity_with_positive_risk_adjusted_returns"
$env:AUREON_LLM_LIVE_CAPABILITIES = "1"
$env:AUREON_COGNITIVE_LIVE_MODE = "1"
if (-not $env:AUREON_VOICE_BACKEND) { $env:AUREON_VOICE_BACKEND = "ollama_hybrid" }
if (-not $env:AUREON_LLM_BASE_URL) { $env:AUREON_LLM_BASE_URL = "http://localhost:11434/v1" }
if (-not $env:AUREON_LLM_MODEL) { $env:AUREON_LLM_MODEL = "llama3:latest" }
if (-not $env:AUREON_LLM_KEEP_ALIVE) { $env:AUREON_LLM_KEEP_ALIVE = "30m" }
if (-not $env:AUREON_LLM_ALLOW_HTTP_IN_AUDIT) { $env:AUREON_LLM_ALLOW_HTTP_IN_AUDIT = "1" }
if (-not $env:AUREON_LLM_REQUEST_TIMEOUT_S) { $env:AUREON_LLM_REQUEST_TIMEOUT_S = "180" }
if (-not $env:AUREON_LLM_PROBE_TIMEOUT_S) { $env:AUREON_LLM_PROBE_TIMEOUT_S = "120" }
if (-not $env:AUREON_LLM_HEALTH_TIMEOUT_S) { $env:AUREON_LLM_HEALTH_TIMEOUT_S = "10" }
if (-not $env:AUREON_PHI_CHAT_MAX_TOKENS) { $env:AUREON_PHI_CHAT_MAX_TOKENS = "120" }
if (-not $env:AUREON_PHI_CHAT_TIMEOUT_S) { $env:AUREON_PHI_CHAT_TIMEOUT_S = "180" }
if (-not $env:AUREON_PHI_CHAT_TEMPERATURE) { $env:AUREON_PHI_CHAT_TEMPERATURE = "0.25" }
$env:AUREON_GOAL_CAPABILITY_DIRECTIVE = "goal-capability-v1"
$env:AUREON_LLM_ORDER_AUTHORITY = "0"
$env:AUREON_COGNITIVE_ORDER_AUTHORITY = "0"
$env:AUREON_LLM_ORDER_INTENT_AUTHORITY = "0"
$env:AUREON_COGNITIVE_ORDER_INTENT_AUTHORITY = "0"
$env:AUREON_ORDER_AUTHORITY_MODE = "runtime_only"
$env:AUREON_ORDER_INTENT_PUBLISH = "0"
$env:AUREON_ORDER_TICKET_REQUIRES_EXECUTOR = "1"
$env:AUREON_UNIFIED_ORDER_EXECUTOR = "0"
$env:AUREON_DISABLE_EXTERNAL_ATTACKS = "1"
$env:AUREON_DISABLE_OFFICIAL_FILING = "1"
$env:AUREON_DISABLE_PAYMENTS = "1"
$env:AUREON_ALLOW_SIM_FALLBACK = "0"
if (-not $env:UNIFIED_MARKET_EMBEDDED_DASHBOARD) { $env:UNIFIED_MARKET_EMBEDDED_DASHBOARD = "0" }
if (-not $env:UNIFIED_RUNTIME_WRITER_LOCK_TTL_SEC) { $env:UNIFIED_RUNTIME_WRITER_LOCK_TTL_SEC = "120" }
if (-not $env:UNIFIED_CENTRAL_BEAT_REFRESH_SEC) { $env:UNIFIED_CENTRAL_BEAT_REFRESH_SEC = "2" }
if (-not $env:UNIFIED_READY_STALE_AFTER_SEC) { $env:UNIFIED_READY_STALE_AFTER_SEC = "45" }
if (-not $env:UNIFIED_TICK_RUNNING_STALE_AFTER_SEC) { $env:UNIFIED_TICK_RUNNING_STALE_AFTER_SEC = "600" }
if (-not $env:UNIFIED_PROBE_SYMBOL_MIN_INTERVAL_SEC) { $env:UNIFIED_PROBE_SYMBOL_MIN_INTERVAL_SEC = "5" }
if (-not $env:UNIFIED_PROBE_SYMBOL_STALE_TTL_SEC) { $env:UNIFIED_PROBE_SYMBOL_STALE_TTL_SEC = "30" }
if (-not $env:MARKET_CACHE_DIR) { $env:MARKET_CACHE_DIR = "ws_cache" }
if (-not $env:WS_PRICE_CACHE_PATH) { $env:WS_PRICE_CACHE_PATH = "ws_cache/ws_prices.json" }
if (-not $env:WS_FEED_WRITE_INTERVAL_S) { $env:WS_FEED_WRITE_INTERVAL_S = "1.0" }
if (-not $env:UNIFIED_STREAM_PRICE_MAX_AGE_SEC) { $env:UNIFIED_STREAM_PRICE_MAX_AGE_SEC = "5" }
if (-not $env:UNIFIED_STREAM_CACHE_MAX_SYMBOLS) { $env:UNIFIED_STREAM_CACHE_MAX_SYMBOLS = "96" }
if (-not $env:UNIFIED_FAST_MONEY_MIN_VOLATILITY_PCT) { $env:UNIFIED_FAST_MONEY_MIN_VOLATILITY_PCT = "0.34" }
if (-not $env:UNIFIED_FAST_MONEY_BREAK_EVEN_MOVE_PCT) { $env:UNIFIED_FAST_MONEY_BREAK_EVEN_MOVE_PCT = "0.34" }
if (-not $env:UNIFIED_FAST_MONEY_VOLUME_USD_TARGET) { $env:UNIFIED_FAST_MONEY_VOLUME_USD_TARGET = "25000000" }
if (-not $env:UNIFIED_FAST_MONEY_MIN_SCORE) { $env:UNIFIED_FAST_MONEY_MIN_SCORE = "0.55" }
if (-not $env:UNIFIED_ORDERBOOK_PROBE_MAX_PER_TICK) { $env:UNIFIED_ORDERBOOK_PROBE_MAX_PER_TICK = "4" }
if (-not $env:UNIFIED_ORDERBOOK_PROBE_MIN_INTERVAL_SEC) { $env:UNIFIED_ORDERBOOK_PROBE_MIN_INTERVAL_SEC = "12" }
if (-not $env:UNIFIED_ORDERBOOK_PROBE_STALE_TTL_SEC) { $env:UNIFIED_ORDERBOOK_PROBE_STALE_TTL_SEC = "30" }
if (-not $env:CAPITAL_FAST_PROFIT_CAPTURE_ENABLED) { $env:CAPITAL_FAST_PROFIT_CAPTURE_ENABLED = "1" }
if (-not $env:CAPITAL_FAST_PROFIT_MIN_GBP) { $env:CAPITAL_FAST_PROFIT_MIN_GBP = "0.01" }
if (-not $env:CAPITAL_FAST_PROFIT_MIN_PCT) { $env:CAPITAL_FAST_PROFIT_MIN_PCT = "0.02" }
if (-not $env:CAPITAL_FAST_PROFIT_MIN_HOLD_SECS) { $env:CAPITAL_FAST_PROFIT_MIN_HOLD_SECS = "2" }
if (-not $env:CAPITAL_FAST_PROFIT_MARKET_STATUS_TTL_SECS) { $env:CAPITAL_FAST_PROFIT_MARKET_STATUS_TTL_SECS = "10" }
if (-not $env:KRAKEN_FAST_PROFIT_CAPTURE_ENABLED) { $env:KRAKEN_FAST_PROFIT_CAPTURE_ENABLED = "1" }
if (-not $env:KRAKEN_FAST_PROFIT_MIN_USD) { $env:KRAKEN_FAST_PROFIT_MIN_USD = "0.01" }
if (-not $env:KRAKEN_FAST_PROFIT_MIN_HOLD_SECS) { $env:KRAKEN_FAST_PROFIT_MIN_HOLD_SECS = "1" }
if (-not $env:KRAKEN_FAST_PROFIT_COLLATERAL_WARN_PCT) { $env:KRAKEN_FAST_PROFIT_COLLATERAL_WARN_PCT = "150" }
if (-not $env:KRAKEN_SPOT_FAST_PROFIT_CAPTURE_ENABLED) { $env:KRAKEN_SPOT_FAST_PROFIT_CAPTURE_ENABLED = "1" }
if (-not $env:KRAKEN_SPOT_FAST_PROFIT_MIN_USD) { $env:KRAKEN_SPOT_FAST_PROFIT_MIN_USD = "0.01" }
if (-not $env:KRAKEN_SPOT_FAST_PROFIT_MIN_HOLD_SEC) { $env:KRAKEN_SPOT_FAST_PROFIT_MIN_HOLD_SEC = "1" }
if (-not $env:KRAKEN_SPOT_TAKER_FEE_RATE) { $env:KRAKEN_SPOT_TAKER_FEE_RATE = "0.004" }
if (-not $env:KRAKEN_SPOT_COLLATERAL_RESERVE_USD) { $env:KRAKEN_SPOT_COLLATERAL_RESERVE_USD = "5" }
if (-not $env:UNIFIED_KRAKEN_TICK_MIN_INTERVAL_SEC) { $env:UNIFIED_KRAKEN_TICK_MIN_INTERVAL_SEC = "1" }
if (-not $env:UNIFIED_CAPITAL_TICK_MIN_INTERVAL_SEC) { $env:UNIFIED_CAPITAL_TICK_MIN_INTERVAL_SEC = "2" }
if (-not $env:UNIFIED_ORDER_INTENT_MIN_INTERVAL_SEC) { $env:UNIFIED_ORDER_INTENT_MIN_INTERVAL_SEC = "8" }
if (-not $env:UNIFIED_ORDER_INTENT_MIN_CONFIDENCE) { $env:UNIFIED_ORDER_INTENT_MIN_CONFIDENCE = "0.35" }
if (-not $env:UNIFIED_ORDER_INTENT_MAX_PER_CYCLE) { $env:UNIFIED_ORDER_INTENT_MAX_PER_CYCLE = "4" }
if (-not $env:UNIFIED_ORDER_EXECUTOR_MIN_INTERVAL_SEC) { $env:UNIFIED_ORDER_EXECUTOR_MIN_INTERVAL_SEC = "10" }
if (-not $env:UNIFIED_ORDER_EXECUTOR_SYMBOL_COOLDOWN_SEC) { $env:UNIFIED_ORDER_EXECUTOR_SYMBOL_COOLDOWN_SEC = "60" }
if (-not $env:UNIFIED_ORDER_EXECUTOR_QUOTE_USD) { $env:UNIFIED_ORDER_EXECUTOR_QUOTE_USD = "5" }
if (-not $env:UNIFIED_ORDER_EXECUTOR_MAX_PER_TICK) { $env:UNIFIED_ORDER_EXECUTOR_MAX_PER_TICK = "4" }
if (-not $env:UNIFIED_ORDER_EXECUTOR_MAX_OPEN_POSITIONS) { $env:UNIFIED_ORDER_EXECUTOR_MAX_OPEN_POSITIONS = "12" }
if (-not $env:UNIFIED_KRAKEN_SPOT_QUOTE_USD) { $env:UNIFIED_KRAKEN_SPOT_QUOTE_USD = "65" }
if (-not $env:UNIFIED_BINANCE_MARGIN_LEVERAGE) { $env:UNIFIED_BINANCE_MARGIN_LEVERAGE = "2" }
if (-not $env:UNIFIED_KRAKEN_CALLS_PER_MIN) { $env:UNIFIED_KRAKEN_CALLS_PER_MIN = "60" }
if (-not $env:UNIFIED_CAPITAL_CALLS_PER_MIN) { $env:UNIFIED_CAPITAL_CALLS_PER_MIN = "45" }
if (-not $env:UNIFIED_ALPACA_CALLS_PER_MIN) { $env:UNIFIED_ALPACA_CALLS_PER_MIN = "120" }
if (-not $env:UNIFIED_BINANCE_CALLS_PER_MIN) { $env:UNIFIED_BINANCE_CALLS_PER_MIN = "240" }
if (-not $env:UNIFIED_EXCHANGE_RATE_BACKOFF_SEC) { $env:UNIFIED_EXCHANGE_RATE_BACKOFF_SEC = "30" }

if ($FullCognitiveOrderCapability) {
    $env:AUREON_LLM_ORDER_INTENT_AUTHORITY = "1"
    $env:AUREON_COGNITIVE_ORDER_INTENT_AUTHORITY = "1"
    $env:AUREON_ORDER_AUTHORITY_MODE = "intent_only_runtime_gated"
    $env:AUREON_ORDER_INTENT_PUBLISH = "1"
}

if ($LiveTrading) {
    $env:AUREON_AUDIT_MODE = "0"
    $env:AUREON_LIVE_TRADING = "1"
    $env:AUREON_DISABLE_REAL_ORDERS = "0"
    $env:AUREON_DISABLE_EXCHANGE_MUTATIONS = "0"
    $env:AUREON_DRY_RUN = "0"
    $env:DRY_RUN = "0"
    $env:LIVE = "1"
    $env:CONFIRM_LIVE = "yes"
    if ($FullCognitiveOrderCapability) {
        $env:AUREON_UNIFIED_ORDER_EXECUTOR = "1"
    }
    $Mode = "LIVE_TRADING_OPERATOR_CONFIRMED"
} else {
    $env:AUREON_AUDIT_MODE = "1"
    $env:AUREON_LIVE_TRADING = "0"
    $env:AUREON_DISABLE_REAL_ORDERS = "1"
    $env:AUREON_DISABLE_EXCHANGE_MUTATIONS = "1"
    $env:AUREON_DRY_RUN = "1"
    $env:DRY_RUN = "1"
    $env:LIVE = "0"
    $env:AUREON_UNIFIED_ORDER_EXECUTOR = "0"
    $Mode = "SAFE_FULL_AUTONOMOUS_OBSERVATION"
}
if ($FullCognitiveOrderCapability) {
    $Mode = "$Mode + COGNITIVE_ORDER_INTENT_AUTHORITY"
}
if ($ProductionMode) {
    $Mode = "$Mode + PRODUCTION_SUPERVISOR"
}

Write-Aureon "Aureon wake-up launcher"
Write-Aureon "Repo: $RepoRoot"
Write-Aureon "Mode: $Mode"
Write-Aureon "Python: $Python"
Write-Aureon "Frontend: http://127.0.0.1:$FrontendPort/"
Write-Aureon "Logs: $LogRoot"

if ($ValidateOnly) {
    Write-Aureon "Validation only complete. No processes started." "OK"
    exit 0
}

Assert-SingleProductionSupervisor

if (-not $SkipFrontend -and -not $SkipNpmInstall) {
    $nodeModules = Join-Path $FrontendRoot "node_modules"
    if (-not (Test-Path -LiteralPath $nodeModules)) {
        Write-Aureon "frontend/node_modules missing. Running npm ci."
        $npmOut = Join-Path $LogRoot "npm_ci.out.log"
        $npmErr = Join-Path $LogRoot "npm_ci.err.log"
        $npmExit = Invoke-NativeLogged `
            -Name "npm ci" `
            -FilePath $Npm `
            -Arguments @("ci") `
            -WorkingDirectory $FrontendRoot `
            -StdoutPath $npmOut `
            -StderrPath $npmErr
        if ($npmExit -ne 0) {
            throw "npm ci failed. Fix frontend dependencies before waking Aureon."
        }
    }
}

$started = @()

if (-not $SkipMarketTelemetry -and $env:AUREON_DISABLE_LIVE_STREAM_CACHE -ne "1") {
    $streamOut = ($env:WS_PRICE_CACHE_PATH -replace '"', '')
    $streamInterval = ($env:WS_FEED_WRITE_INTERVAL_S -replace '"', '')
    $streamFreshMaxAgeSec = [Math]::Max(15.0, ([double]$streamInterval * 20.0))
    $streamArgs = "-m aureon.data_feeds.ws_market_data_feeder --binance --kraken --alpaca --capital --history-recording --quiet --out `"$streamOut`" --write-interval-s $streamInterval"
    if (-not (Test-LiveStreamCacheFresh -Path $streamOut -MaxAgeSec $streamFreshMaxAgeSec)) {
        Write-Aureon "Live stream cache missing/stale; restarting stream feeder" "WATCH"
        Stop-MatchingProcess -Pattern "aureon.data_feeds.ws_market_data_feeder" -Name "Live market stream cache"
    }
    $started += Start-AureonProcessWithoutStopping `
        -Name "Live market stream cache" `
        -Pattern "aureon.data_feeds.ws_market_data_feeder" `
        -FilePath $Python `
        -Arguments $streamArgs `
        -WorkingDirectory $RepoRoot `
        -LogDirectory $LogRoot
}

if (-not $SkipIgnition) {
    $ignitionArgs = "scripts/aureon_ignition.py --no-trade --accounts-status"
    if ($LiveTrading) { $ignitionArgs = "scripts/aureon_ignition.py --live --no-trade --accounts-status" }
    if ($AccountsAutonomous) { $ignitionArgs += " --accounts-autonomous" }
    if ($AccountsBuild) { $ignitionArgs += " --accounts-build" }
    $started += Start-AureonProcess `
        -Name "Ignition organism core" `
        -Pattern "scripts/aureon_ignition.py" `
        -FilePath $Python `
        -Arguments $ignitionArgs `
        -WorkingDirectory $RepoRoot `
        -LogDirectory $LogRoot
}

if (-not $SkipMarketTelemetry) {
    $marketLive = Test-AureonEndpoint -Url $RuntimeFeedUrl -TimeoutSec 3
    $marketState = $null
    $marketFlight = $null
    if ($marketLive.ok) {
        $marketFlight = Get-AureonMarketFlightTest -TimeoutSec 3
        if ($null -eq $marketFlight) {
            $marketState = Get-AureonRuntimeState -TimeoutSec 3
        }
    }
    if ($null -ne $marketFlight -and $null -ne $marketFlight.reboot_advice -and $null -ne $marketFlight.checks) {
        $marketHasOpenPositions = [bool]$marketFlight.checks.open_positions
        $marketDowntimeWindow = [bool]$marketFlight.checks.downtime_window
        $marketCanRestart = [bool]$marketFlight.reboot_advice.can_reboot_now
        $marketHoldReason = [string]$marketFlight.reboot_advice.reason
    } else {
        $marketHasOpenPositions = Test-AureonRuntimeHasOpenPositions -RuntimeState $marketState
        $marketDowntimeWindow = Test-AureonMarketDowntimeWindow
        $marketCanRestart = $marketDowntimeWindow -and (-not $marketHasOpenPositions)
        $marketHoldReason = "local_flight_fallback"
    }
    if ($marketLive.ok -and $null -eq $marketState) {
        $marketState = Get-AureonRuntimeState -TimeoutSec 3
    }
    $marketLiveTradingArmed = Test-AureonRuntimeLiveTradingArmed -RuntimeState $marketState
    $operatorLiveUpgrade = [bool]($LiveTrading -and $marketLive.ok -and (-not $marketHasOpenPositions) -and (-not $marketLiveTradingArmed))
    if ($operatorLiveUpgrade) {
        $marketCanRestart = $true
        $marketHoldReason = "operator_confirmed_live_mode_requires_runtime_replacement"
        Write-Aureon "Operator-confirmed live mode requested; replacing non-live market runtime after flat-position check" "WATCH"
    }

    if ($LegacyMarketRuntimeOnDefaultPort) {
        Request-AureonMarketRebootIntent -Reason "legacy_market_runtime_without_flight_test_preserved_until_safe_downtime"
        $started += Start-AureonProcess `
            -Name "Unified market status server" `
            -Pattern "aureon.exchanges.unified_market_status_server --port $MarketStatusPort" `
            -FilePath $Python `
            -Arguments "-m aureon.exchanges.unified_market_status_server --port $MarketStatusPort" `
            -WorkingDirectory $RepoRoot `
            -LogDirectory $LogRoot
        Write-Aureon "Legacy market runtime preserved on 8790; not starting a second trader. Status mirror uses $RuntimeFeedUrl" "OK"
        $started += @{
            name = "Unified market telemetry"
            status = "legacy_runtime_preserved_no_duplicate_trader"
            pids = $LegacyMarketRuntimePids
            reboot_intent = (Join-Path $StateRoot "aureon_market_reboot_intent.json")
            runtime_feed_url = $RuntimeFeedUrl
        }
    } elseif ($Restart -and $marketLive.ok -and (-not $marketCanRestart)) {
        Request-AureonMarketRebootIntent -Reason "launcher_detected_pending_market_runtime_update_deferred_until_safe_downtime"
        if ($null -eq $marketFlight) {
            Write-Aureon "Refreshing read-only market status server so market flight-test endpoints are available; trading loop remains untouched" "INFO"
            Restart-AureonMarketStatusServerOnly
        }
        $runtimeForWriterCheck = $marketState
        if ($null -eq $runtimeForWriterCheck) {
            $runtimeForWriterCheck = Get-AureonRuntimeState -TimeoutSec 3
        }
        $marketWriterPid = Get-AureonRuntimeWriterPid -RuntimeState $runtimeForWriterCheck
        $marketWriterAlive = Test-AureonRuntimeWriterAlive -RuntimeState $runtimeForWriterCheck
        if (-not $marketWriterAlive) {
            $takeoverReason = "dead_or_missing_writer_pid_$marketWriterPid; restart_deferred_reason=$marketHoldReason"
            $started += Start-AureonMarketTelemetryWriterOnly -Reason $takeoverReason
        }
        $marketPids = @()
        try {
            $marketPids += @(
                Get-NetTCPConnection -State Listen -LocalPort $MarketStatusPort -ErrorAction SilentlyContinue |
                    Select-Object -ExpandProperty OwningProcess -Unique
            )
        } catch {
            $marketPids += @()
        }
        $marketPids += @((Get-MatchingProcess -Pattern "aureon.exchanges.unified_market_trader") | Select-Object -ExpandProperty ProcessId)
        $marketPids = @($marketPids | Where-Object { $_ } | Select-Object -Unique)
        Write-Aureon "Market runtime already alive; planned restart deferred until downtime window and flat-position check pass (reason=$marketHoldReason downtime=$marketDowntimeWindow open_positions=$marketHasOpenPositions)" "OK"
        $started += @{
            name = "Unified market telemetry"
            status = "already_running_restart_deferred"
            pids = $marketPids
            reboot_intent = (Join-Path $StateRoot "aureon_market_reboot_intent.json")
        }
    } else {
        Stop-ProcessOnPort -Port $MarketStatusPort -Name "Unified market runtime API"
        $started += Start-AureonProcess `
            -Name "Unified market status server" `
            -Pattern "aureon.exchanges.unified_market_status_server --port $MarketStatusPort" `
            -FilePath $Python `
            -Arguments "-m aureon.exchanges.unified_market_status_server --port $MarketStatusPort" `
            -WorkingDirectory $RepoRoot `
            -LogDirectory $LogRoot

        $marketArgs = "-m aureon.exchanges.unified_market_trader --interval $MarketInterval"
        if (-not $LiveTrading) { $marketArgs += " --dry-run" }
        $started += Start-AureonProcess `
            -Name "Unified market telemetry" `
            -Pattern "aureon.exchanges.unified_market_trader" `
            -FilePath $Python `
            -Arguments $marketArgs `
            -WorkingDirectory $RepoRoot `
            -LogDirectory $LogRoot
    }
}

if (-not $SkipMindHub) {
    $mindLive = Test-AureonEndpoint -Url "http://127.0.0.1:13002/api/thoughts" -TimeoutSec 3
    $mindFlight = $null
    if ($mindLive.ok) {
        $mindFlight = Get-AureonMindFlightTest -TimeoutSec 3
    }
    $localDowntimeWindow = Test-AureonMindDowntimeWindow
    $flightCanReboot = $false
    $flightReason = "flight_unavailable"
    if ($null -ne $mindFlight -and $null -ne $mindFlight.reboot_advice) {
        $flightCanReboot = [bool]$mindFlight.reboot_advice.can_reboot_now
        $flightReason = [string]$mindFlight.reboot_advice.reason
    }

    if ($Restart -and $mindLive.ok -and -not $flightCanReboot -and -not (($null -eq $mindFlight) -and $localDowntimeWindow)) {
        Request-AureonMindRebootIntent -Reason "launcher_detected_pending_mind_hub_update_deferred_until_downtime"
        try {
            $mindPids = @(
                Get-NetTCPConnection -State Listen -LocalPort 13002 -ErrorAction SilentlyContinue |
                    Select-Object -ExpandProperty OwningProcess -Unique
            )
        } catch {
            $mindPids = @()
        }
        Write-Aureon "Mind hub already alive; planned restart deferred until flight-test/downtime approval (reason=$flightReason local_downtime=$localDowntimeWindow)" "OK"
        $started += @{
            name = "Mind thought action hub"
            status = "already_running_restart_deferred"
            pids = $mindPids
            reboot_intent = (Join-Path $StateRoot "aureon_reboot_intent.json")
        }
    } else {
        Stop-ProcessOnPort -Port 13002 -Name "Mind thought action hub"
        $started += Start-AureonProcess `
            -Name "Mind thought action hub" `
            -Pattern "aureon.autonomous.aureon_mind_thought_action_hub" `
            -FilePath $Python `
            -Arguments "-m aureon.autonomous.aureon_mind_thought_action_hub" `
            -WorkingDirectory $RepoRoot `
            -LogDirectory $LogRoot
    }
}

if (-not $SkipSelfQuestioning) {
    $started += Start-AureonProcess `
        -Name "Self-questioning AI loop" `
        -Pattern "aureon.autonomous.aureon_self_questioning_ai --loop" `
        -FilePath $Python `
        -Arguments "-m aureon.autonomous.aureon_self_questioning_ai --loop --interval 300" `
        -WorkingDirectory $RepoRoot `
        -LogDirectory $LogRoot
}

$started += Start-AureonProcess `
    -Name "Organism runtime observer" `
    -Pattern "aureon.autonomous.aureon_organism_runtime_observer --watch" `
    -FilePath $Python `
    -Arguments "-m aureon.autonomous.aureon_organism_runtime_observer --watch --interval $ObserverInterval --refresh-core" `
    -WorkingDirectory $RepoRoot `
    -LogDirectory $LogRoot

if (-not $SkipAutonomousSelfRun) {
    $started += Start-AureonProcess `
        -Name "Autonomous self-run coding loop" `
        -Pattern "aureon.autonomous.aureon_autonomous_self_run_loop --forever" `
        -FilePath $Python `
        -Arguments "-m aureon.autonomous.aureon_autonomous_self_run_loop --forever --interval-seconds $SelfRunIntervalSec --max-stress-attempts 2" `
        -WorkingDirectory $RepoRoot `
        -LogDirectory $LogRoot
}

if (-not $SkipFrontend) {
    Stop-ProcessOnPort -Port $FrontendPort -Name "Unified frontend console"
    $frontendArgs = "/c npm run dev -- --host 0.0.0.0 --port $FrontendPort"
    $started += Start-AureonProcess `
        -Name "Unified frontend console" `
        -Pattern "vite.js*--port $FrontendPort" `
        -FilePath "cmd.exe" `
        -Arguments $frontendArgs `
        -WorkingDirectory $FrontendRoot `
        -LogDirectory $LogRoot
}

if ($WaitForRefresh) {
    Invoke-Refresh -Python $Python -RepoRoot $RepoRoot -LogDirectory $LogRoot
} else {
    $started += Start-AureonProcess `
        -Name "Manifest refresh one-shot" `
        -Pattern "aureon.autonomous.aureon_organism_runtime_observer --refresh-core" `
        -FilePath $Python `
        -Arguments "-m aureon.autonomous.aureon_organism_runtime_observer --refresh-core" `
        -WorkingDirectory $RepoRoot `
        -LogDirectory $LogRoot
}

$endpointStatus = @()
if (-not $NoStatusWait) {
    Write-Aureon "Waiting for alive endpoints..."
    if (-not $SkipFrontend) {
        $endpointStatus += Wait-AureonEndpoint -Name "Unified frontend console" -Url "http://127.0.0.1:$FrontendPort/" -TimeoutSec $StatusTimeoutSec
    }
    if (-not $SkipMarketTelemetry) {
        $endpointStatus += Wait-AureonEndpoint -Name "Runtime trading telemetry" -Url $RuntimeFeedUrl -TimeoutSec $StatusTimeoutSec
    }
    if (-not $SkipMindHub) {
        $endpointStatus += Wait-AureonEndpoint -Name "Mind/thought/action hub" -Url "http://127.0.0.1:13002/api/thoughts" -TimeoutSec $StatusTimeoutSec
    }
}

$manifest = New-WakeManifestPayload -Statuses $endpointStatus -StartedProcesses $started -SupervisorMode $false
Write-WakeManifest -Payload $manifest

Write-Aureon "Wake-up manifest: $manifestPath" "OK"
Write-Aureon "Public wake-up manifest: $publicManifestPath" "OK"
Write-Aureon "Unified console: http://127.0.0.1:$FrontendPort/" "OK"
Write-Aureon "Mind hub: http://127.0.0.1:13002/" "OK"
Write-Aureon "Runtime feed: $RuntimeFeedUrl" "OK"
Write-Aureon "Runtime flight test: $RuntimeFlightUrl" "OK"
Write-Aureon "Runtime reboot advice: $RuntimeRebootAdviceUrl" "OK"
if ($FullCognitiveOrderCapability) {
    Write-Aureon "LLM/cognitive order-intent authority: ON" "OK"
    Write-Aureon "LLM/cognitive direct exchange mutation authority: OFF (runtime-gated)" "OK"
} else {
    Write-Aureon "LLM/cognitive direct order authority: OFF" "OK"
}

if (-not $NoOpen) {
    Start-Process "http://127.0.0.1:$FrontendPort/"
}

function Restart-AureonSurface {
    param([string]$Surface)

    if ($Surface -eq "frontend" -and -not $SkipFrontend) {
        Stop-ProcessOnPort -Port $FrontendPort -Name "Unified frontend console" -Force
        $frontendArgs = "/c npm run dev -- --host 0.0.0.0 --port $FrontendPort"
        Start-AureonProcess `
            -Name "Unified frontend console" `
            -Pattern "vite.js*--port $FrontendPort" `
            -FilePath "cmd.exe" `
            -Arguments $frontendArgs `
            -WorkingDirectory $FrontendRoot `
            -LogDirectory $LogRoot | Out-Null
        return
    }

    if ($Surface -eq "market" -and -not $SkipMarketTelemetry) {
        if ($LegacyMarketRuntimeOnDefaultPort) {
            Write-Aureon "Legacy market runtime still owns 8790; restarting status mirror only on $MarketStatusPort" "WATCH"
            Restart-AureonMarketStatusServerOnly
            return
        }
        Stop-ProcessOnPort -Port $MarketStatusPort -Name "Unified market runtime API" -Force
        Start-AureonProcess `
            -Name "Unified market status server" `
            -Pattern "aureon.exchanges.unified_market_status_server --port $MarketStatusPort" `
            -FilePath $Python `
            -Arguments "-m aureon.exchanges.unified_market_status_server --port $MarketStatusPort" `
            -WorkingDirectory $RepoRoot `
            -LogDirectory $LogRoot | Out-Null

        $marketArgs = "-m aureon.exchanges.unified_market_trader --interval $MarketInterval"
        if (-not $LiveTrading) { $marketArgs += " --dry-run" }
        Start-AureonProcess `
            -Name "Unified market telemetry" `
            -Pattern "aureon.exchanges.unified_market_trader" `
            -FilePath $Python `
            -Arguments $marketArgs `
            -WorkingDirectory $RepoRoot `
            -LogDirectory $LogRoot | Out-Null
        Complete-AureonEnvUpdateIntent
        return
    }

    if ($Surface -eq "mind" -and -not $SkipMindHub) {
        Stop-ProcessOnPort -Port 13002 -Name "Mind thought action hub" -Force
        Start-AureonProcess `
            -Name "Mind thought action hub" `
            -Pattern "aureon.autonomous.aureon_mind_thought_action_hub" `
            -FilePath $Python `
            -Arguments "-m aureon.autonomous.aureon_mind_thought_action_hub" `
            -WorkingDirectory $RepoRoot `
            -LogDirectory $LogRoot | Out-Null
    }
}

function Ensure-BackgroundProcess {
    param(
        [string]$Name,
        [string]$Pattern,
        [string]$Arguments
    )
    $matches = @(Get-MatchingProcess -Pattern $Pattern)
    if ($matches.Count -gt 0) {
        return
    }
    Start-AureonProcess `
        -Name $Name `
        -Pattern $Pattern `
        -FilePath $Python `
        -Arguments $Arguments `
        -WorkingDirectory $RepoRoot `
        -LogDirectory $LogRoot | Out-Null
}

function Write-SupervisorManifest {
    param([array]$Statuses)
    try {
        Write-SupervisorLock -Status "active"
        $supervisedManifest = New-WakeManifestPayload -Statuses $Statuses -StartedProcesses $started -SupervisorMode $true
        Write-WakeManifest -Payload $supervisedManifest
    } catch {
        Write-Aureon "Supervisor manifest update failed: $($_.Exception.Message)" "WARN"
    }
}

if ($KeepAlive) {
    Write-Aureon "Production supervisor attached. Press Ctrl+C to stop supervising; background services keep their own process state." "ALIVE"
    $mindHubFailureCount = 0
    $mindHubConsecutiveFailuresBeforeRestart = 3
    $mindHubRestartCooldownSec = [Math]::Max(180, $SupervisorIntervalSec * 6)
    $mindHubLastRestart = Get-Date
    $mindHubLastHealthy = Get-Date
    $marketIntentLastLog = (Get-Date).AddMinutes(-10)
    $marketIntentLogCooldownSec = [Math]::Max(300, $SupervisorIntervalSec * 10)
    $marketWriterTakeoverLastAttempt = [datetime]::MinValue
    $marketWriterTakeoverCooldownSec = [Math]::Max(180, $SupervisorIntervalSec * 6)
    while ($true) {
        $statuses = @()

        if (-not $SkipMarketTelemetry -and $env:AUREON_DISABLE_LIVE_STREAM_CACHE -ne "1" -and -not [string]::IsNullOrWhiteSpace($streamArgs)) {
            if (-not (Test-LiveStreamCacheFresh -Path $streamOut -MaxAgeSec $streamFreshMaxAgeSec)) {
                Write-Aureon "Live stream cache stale; restarting stream feeder" "WATCH"
                Stop-MatchingProcess -Pattern "aureon.data_feeds.ws_market_data_feeder" -Name "Live market stream cache"
            }
            Ensure-BackgroundProcess `
                -Name "Live market stream cache" `
                -Pattern "aureon.data_feeds.ws_market_data_feeder" `
                -Arguments $streamArgs
        }

        if (-not $SkipFrontend) {
            $frontendStatus = Test-AureonEndpoint -Url "http://127.0.0.1:$FrontendPort/" -TimeoutSec 5
            $statuses += $frontendStatus
            if (-not $frontendStatus.ok) {
                Write-Aureon "Frontend offline; restarting $FrontendPort" "WATCH"
                Restart-AureonSurface -Surface "frontend"
            }
        }

        if (-not $SkipMarketTelemetry) {
            $marketStatus = Test-AureonEndpoint -Url $RuntimeFeedUrl -TimeoutSec 5
            $statuses += $marketStatus
            if (-not $marketStatus.ok) {
                Write-Aureon "Runtime feed offline; restarting market status and telemetry" "WATCH"
                Restart-AureonSurface -Surface "market"
            } else {
                $marketIntentPath = Join-Path $StateRoot "aureon_market_reboot_intent.json"
                if (Test-Path -LiteralPath $marketIntentPath) {
                    try {
                        $marketIntent = Get-Content -LiteralPath $marketIntentPath -Raw | ConvertFrom-Json
                    } catch {
                        $marketIntent = $null
                    }
                    if ($null -ne $marketIntent -and $marketIntent.status -eq "pending") {
                        $runtimeStateForWriter = Get-AureonRuntimeState -TimeoutSec 3
                        $marketWriterPid = Get-AureonRuntimeWriterPid -RuntimeState $runtimeStateForWriter
                        $marketWriterAlive = Test-AureonRuntimeWriterAlive -RuntimeState $runtimeStateForWriter
                        $marketFlight = Get-AureonMarketFlightTest -TimeoutSec 3
                        if ($null -ne $marketFlight -and $null -ne $marketFlight.reboot_advice -and $null -ne $marketFlight.checks) {
                            $marketHasOpenPositions = [bool]$marketFlight.checks.open_positions
                            $marketDowntimeWindow = [bool]$marketFlight.checks.downtime_window
                            $marketCanRestart = [bool]$marketFlight.reboot_advice.can_reboot_now
                            $marketHoldReason = [string]$marketFlight.reboot_advice.reason
                        } else {
                            $runtimeState = $runtimeStateForWriter
                            $marketHasOpenPositions = Test-AureonRuntimeHasOpenPositions -RuntimeState $runtimeState
                            $marketDowntimeWindow = Test-AureonMarketDowntimeWindow
                            $marketCanRestart = $marketDowntimeWindow -and (-not $marketHasOpenPositions)
                            $marketHoldReason = "local_flight_fallback"
                            Write-Aureon "Refreshing read-only market status server so market flight-test endpoints are available; trading loop remains untouched" "INFO"
                            Restart-AureonMarketStatusServerOnly
                        }
                        $marketLiveTradingArmed = Test-AureonRuntimeLiveTradingArmed -RuntimeState $runtimeStateForWriter
                        if ($LiveTrading -and (-not $marketHasOpenPositions) -and (-not $marketLiveTradingArmed)) {
                            $marketCanRestart = $true
                            $marketHoldReason = "operator_confirmed_live_mode_requires_runtime_replacement"
                            Write-Aureon "Operator-confirmed live mode still needs the market runtime replaced; flat-position check approved" "WATCH"
                        }
                        if (-not $marketWriterAlive -and ((Get-Date) - $marketWriterTakeoverLastAttempt).TotalSeconds -ge $marketWriterTakeoverCooldownSec) {
                            $takeoverReason = "supervisor_dead_or_missing_writer_pid_$marketWriterPid; restart_deferred_reason=$marketHoldReason"
                            Start-AureonMarketTelemetryWriterOnly -Reason $takeoverReason | Out-Null
                            $marketWriterTakeoverLastAttempt = Get-Date
                        } elseif ($marketCanRestart) {
                            Write-Aureon "Market runtime requested planned restart; downtime and flat-position check approved" "WATCH"
                            Restart-AureonSurface -Surface "market"
                            Complete-AureonMarketRebootIntent
                            Complete-AureonEnvUpdateIntent
                        } elseif (((Get-Date) - $marketIntentLastLog).TotalSeconds -ge $marketIntentLogCooldownSec) {
                            Write-Aureon "Market runtime planned restart held: reason=$marketHoldReason downtime=$marketDowntimeWindow open_positions=$marketHasOpenPositions; preserving live monitoring/trading continuity" "WARN"
                            $marketIntentLastLog = Get-Date
                        }
                    }
                }
            }
        }

        if (-not $SkipMindHub) {
            $mindStatus = Test-AureonEndpoint -Url "http://127.0.0.1:13002/api/thoughts" -TimeoutSec 5
            $statuses += $mindStatus
            if (-not $mindStatus.ok) {
                $mindHubFailureCount += 1
                $secondsSinceRestart = ((Get-Date) - $mindHubLastRestart).TotalSeconds
                $secondsSinceHealthy = ((Get-Date) - $mindHubLastHealthy).TotalSeconds
                if ($mindHubFailureCount -ge $mindHubConsecutiveFailuresBeforeRestart -and $secondsSinceRestart -ge $mindHubRestartCooldownSec) {
                    $flightTest = Get-AureonMindFlightTest
                    $flightApprovesRestart = $false
                    $flightDecision = "unavailable"
                    if ($null -ne $flightTest -and $null -ne $flightTest.reboot_advice) {
                        $flightApprovesRestart = [bool]$flightTest.reboot_advice.can_reboot_now
                        $flightDecision = [string]$flightTest.reboot_advice.decision
                    }
                    $localDowntimeWindow = Test-AureonMindDowntimeWindow
                    if ($flightApprovesRestart -or (($null -eq $flightTest) -and $localDowntimeWindow)) {
                        Write-Aureon "Mind hub offline after $mindHubFailureCount consecutive checks ($([int]$secondsSinceHealthy)s since healthy); reboot window approved; restarting cognitive hub" "WATCH"
                        Restart-AureonSurface -Surface "mind"
                        if ($null -ne $flightTest -and $null -ne $flightTest.reboot_advice -and [bool]$flightTest.reboot_advice.should_reboot) {
                            Complete-AureonMindRebootIntent
                        }
                        $mindHubLastRestart = Get-Date
                        $mindHubFailureCount = 0
                    } else {
                        Write-Aureon "Mind hub restart deferred: flight=$flightDecision local_downtime=$localDowntimeWindow failures=$mindHubFailureCount; preserving live cognitive/trading continuity" "WARN"
                    }
                } else {
                    Write-Aureon "Mind hub health miss $mindHubFailureCount/$mindHubConsecutiveFailuresBeforeRestart; preserving cognitive process during grace/cooldown" "WARN"
                }
            } else {
                $mindHubFailureCount = 0
                $mindHubLastHealthy = Get-Date
                $flightTest = Get-AureonMindFlightTest -TimeoutSec 3
                if ($null -ne $flightTest -and $null -ne $flightTest.reboot_advice -and [bool]$flightTest.reboot_advice.should_reboot) {
                    if ([bool]$flightTest.reboot_advice.can_reboot_now) {
                        Write-Aureon "Mind hub requested planned reboot and flight-test approved downtime window" "WATCH"
                        Restart-AureonSurface -Surface "mind"
                        Complete-AureonMindRebootIntent
                        $mindHubLastRestart = Get-Date
                    } else {
                        Write-Aureon "Mind hub requested planned reboot but flight-test says hold: $($flightTest.reboot_advice.reason)" "WARN"
                    }
                }
            }
        }

        if (-not $SkipSelfQuestioning) {
            Ensure-BackgroundProcess `
                -Name "Self-questioning AI loop" `
                -Pattern "aureon.autonomous.aureon_self_questioning_ai --loop" `
                -Arguments "-m aureon.autonomous.aureon_self_questioning_ai --loop --interval 300"
        }

        Ensure-BackgroundProcess `
            -Name "Organism runtime observer" `
            -Pattern "aureon.autonomous.aureon_organism_runtime_observer --watch" `
            -Arguments "-m aureon.autonomous.aureon_organism_runtime_observer --watch --interval $ObserverInterval --refresh-core"

        if (-not $SkipAutonomousSelfRun) {
            Ensure-BackgroundProcess `
                -Name "Autonomous self-run coding loop" `
                -Pattern "aureon.autonomous.aureon_autonomous_self_run_loop --forever" `
                -Arguments "-m aureon.autonomous.aureon_autonomous_self_run_loop --forever --interval-seconds $SelfRunIntervalSec --max-stress-attempts 2"
        }

        Write-SupervisorManifest -Statuses $statuses
        $summary = ($statuses | ForEach-Object {
            $name = $_.url -replace "^https?://127\.0\.0\.1:", ""
            "$name=$($_.status)"
        }) -join " "
        Write-Aureon "Supervisor heartbeat: $summary" "ALIVE"
        Start-Sleep -Seconds $SupervisorIntervalSec
    }
}

Write-Aureon "Aureon wake-up command complete. Background processes continue running." "OK"
