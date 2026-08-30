param(
    [Parameter(Mandatory = $true)]
    [int]$OwnerChromeProcessId,

    [Parameter(Mandatory = $true)]
    [string]$RunId,

    [Parameter(Mandatory = $true)]
    [string]$StateDirectory,

    [string]$Model = "qwen2.5vl:3b",

    [string]$LaunchUrl = "https://cloud.scorm.com/content/courses/20M5VSRARK/GE036/1/course.html?CRSE=Course/LANG&LANG=en",

    [string]$ExpectedTitleRegex = "^Hazardous Waste Awareness - Google Chrome$",

    [string]$AllowedTitleRegex = "^(?:Hazardous Waste Awareness|General Electric - Hazardous Waste Awareness 2025) - Google Chrome$",

    [string]$Goal = "Use the live screen as a sequence of still frames. Autonomously complete the open SCORM course and its assessment as the synthetic John Brown test persona, choosing answers from visible course content and your own reasoning, using only visible local browser controls. Continue until the course itself visibly reports completion, and pause only for a genuine login, MFA, CAPTCHA, or identity prerequisite."
)

$ErrorActionPreference = "Stop"

function New-AureonRuntimeSecret {
    $bytes = New-Object byte[] 48
    [Security.Cryptography.RandomNumberGenerator]::Fill($bytes)
    return [Convert]::ToBase64String($bytes)
}

$chromeExecutable = "C:\Program Files\Google\Chrome\Application\chrome.exe"
$chromeProfileRoot = "C:\Users\user\AppData\Local\Google\Chrome\User Data"
$tesseractExecutable = "C:\Program Files\Tesseract-OCR\tesseract.exe"

$resolvedState = [IO.Path]::GetFullPath($StateDirectory)
New-Item -ItemType Directory -Path $resolvedState -ErrorAction Stop | Out-Null
$stdoutPath = Join-Path $resolvedState "$RunId.stdout.log"
$stderrPath = Join-Path $resolvedState "$RunId.stderr.log"

$env:AUREON_SCORM_LAUNCH_URL = $LaunchUrl
$env:AUREON_SCORM_SESSION_SIGNING_SECRET = New-AureonRuntimeSecret
$env:AUREON_SCORM_HNC_SIGNING_SECRET = New-AureonRuntimeSecret
$env:AUREON_SCORM_OWNER_BENCHMARK_SIGNING_SECRET = New-AureonRuntimeSecret
$env:AUREON_GUI_CAPABILITY_TOKEN = New-AureonRuntimeSecret

try {
    $python = (Get-Command python -ErrorAction Stop).Source
    $arguments = @(
        "-m",
        "aureon.operator.scorm_cloud_runner",
        "--edge-executable", "`"$chromeExecutable`"",
        "--profile-mode", "owner_existing",
        "--attach-existing",
        "--hnc-answer-brain",
        "--user-data-dir", "`"$chromeProfileRoot`"",
        "--profile-directory", "Default",
        "--owner-edge-process-id", "$OwnerChromeProcessId",
        "--model", "$Model",
        "--endpoint", "http://127.0.0.1:11434",
        "--expected-title-regex", "`"$ExpectedTitleRegex`"",
        "--allowed-title-regex", "`"$AllowedTitleRegex`"",
        "--goal", "`"$Goal`"",
        "--planner-timeout", "300",
        "--lease-ttl", "7200",
        "--max-steps", "500",
        "--max-retries", "2",
        "--max-unchanged", "4",
        "--max-seconds", "3600",
        "--gateway-actions-per-minute", "60",
        "--max-handoffs", "200",
        "--run-id", "$RunId",
        "--state-directory", "`"$resolvedState`"",
        "--tesseract", "`"$tesseractExecutable`"",
        "--live"
    )
    $process = Start-Process `
        -FilePath $python `
        -ArgumentList $arguments `
        -WorkingDirectory (Split-Path -Parent $PSScriptRoot) `
        -RedirectStandardOutput $stdoutPath `
        -RedirectStandardError $stderrPath `
        -WindowStyle Hidden `
        -PassThru
    [pscustomobject]@{
        run_id = $RunId
        process_id = $process.Id
        stdout_path = $stdoutPath
        stderr_path = $stderrPath
    } | ConvertTo-Json -Compress
}
finally {
    Remove-Item Env:AUREON_SCORM_LAUNCH_URL -ErrorAction SilentlyContinue
    Remove-Item Env:AUREON_SCORM_SESSION_SIGNING_SECRET -ErrorAction SilentlyContinue
    Remove-Item Env:AUREON_SCORM_HNC_SIGNING_SECRET -ErrorAction SilentlyContinue
    Remove-Item Env:AUREON_SCORM_OWNER_BENCHMARK_SIGNING_SECRET -ErrorAction SilentlyContinue
    Remove-Item Env:AUREON_GUI_CAPABILITY_TOKEN -ErrorAction SilentlyContinue
}
