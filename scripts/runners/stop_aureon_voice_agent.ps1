param(
    [string]$RepoRoot = ""
)

if ([string]::IsNullOrWhiteSpace($RepoRoot)) {
    $RepoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..\..") -ErrorAction Stop).Path
} else {
    $RepoRoot = (Resolve-Path -LiteralPath $RepoRoot -ErrorAction Stop).Path
}
if (-not (Test-Path -LiteralPath (Join-Path $RepoRoot "pyproject.toml") -PathType Leaf)) {
    throw "Resolved voice runner repo root is invalid: $RepoRoot"
}

$stateDir = Join-Path $RepoRoot "state"
$stopFile = Join-Path $stateDir "aureon_voice_agent.stop"
$lockFile = Join-Path $stateDir "aureon_voice_agent_supervisor.lock"

$null = New-Item -ItemType Directory -Force -Path $stateDir
Set-Content -Path $stopFile -Value "STOP" -Encoding ascii

if (Test-Path $lockFile) {
    Write-Output "Stop requested. Supervisor will exit."
} else {
    Write-Output "Stop file written. No active supervisor lock found."
}
