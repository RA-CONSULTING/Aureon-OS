param(
    [string]$RepoRoot = "",
    [string]$PythonExe = "",
    [string]$SpeechBackend = "google_first",
    [int]$MicDeviceIndex = 1,
    [int]$GoogleRetries = 3,
    [int]$CaptureRetries = 3,
    [double]$AdjustDuration = 1.5
)

$ErrorActionPreference = "Continue"

if ([string]::IsNullOrWhiteSpace($RepoRoot)) {
    $RepoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..\..") -ErrorAction Stop).Path
} else {
    $RepoRoot = (Resolve-Path -LiteralPath $RepoRoot -ErrorAction Stop).Path
}
if (-not (Test-Path -LiteralPath (Join-Path $RepoRoot "pyproject.toml") -PathType Leaf)) {
    throw "Resolved voice runner repo root is invalid: $RepoRoot"
}
if ([string]::IsNullOrWhiteSpace($PythonExe)) {
    $PythonExe = Join-Path $RepoRoot ".venv\Scripts\python.exe"
}

$stateDir = Join-Path $RepoRoot "state"
$stopFile = Join-Path $stateDir "aureon_voice_agent.stop"
$lockFile = Join-Path $stateDir "aureon_voice_agent_supervisor.lock"
$supervisorLog = Join-Path $stateDir "aureon_voice_agent_supervisor.log"
$agentOut = Join-Path $stateDir "aureon_voice_agent_runtime.out.log"
$agentErr = Join-Path $stateDir "aureon_voice_agent_runtime.err.log"
$agentScript = Join-Path $RepoRoot "aureon\autonomous\aureon_unified_voice_agent.py"

if (-not (Test-Path -LiteralPath $PythonExe -PathType Leaf)) {
    throw "Python venv not found: $PythonExe"
}
if (-not (Test-Path -LiteralPath $agentScript -PathType Leaf)) {
    throw "Voice agent script not found: $agentScript"
}

$null = New-Item -ItemType Directory -Force -Path $stateDir

if (Test-Path $lockFile) {
    exit 0
}

Set-Content -Path $lockFile -Value $PID -Encoding ascii

try {
    while ($true) {
        if (Test-Path $stopFile) {
            Add-Content -Path $supervisorLog -Value "$(Get-Date -Format s) stop file detected"
            break
        }

        $env:AUREON_SPEECH_BACKEND = $SpeechBackend
        $env:AUREON_MIC_DEVICE_INDEX = "$MicDeviceIndex"
        $env:AUREON_GOOGLE_RETRIES = "$GoogleRetries"
        $env:AUREON_CAPTURE_RETRIES = "$CaptureRetries"
        $env:AUREON_ADJUST_DURATION = "$AdjustDuration"
        $env:AUREON_AUTO_APPROVE_LIVE_VOICE = "true"

        Add-Content -Path $supervisorLog -Value "$(Get-Date -Format s) starting voice runtime"

        & $PythonExe $agentScript --mic 1>> $agentOut 2>> $agentErr
        $exitCode = $LASTEXITCODE

        Add-Content -Path $supervisorLog -Value "$(Get-Date -Format s) runtime exited code=$exitCode"
        Start-Sleep -Seconds 3
    }
}
finally {
    if (Test-Path $lockFile) {
        Remove-Item $lockFile -Force
    }
}
