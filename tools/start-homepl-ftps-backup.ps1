[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$BackupScript,
    [Parameter(Mandatory = $true)][string]$FtpHost,
    [Parameter(Mandatory = $true)][string]$FtpUser,
    [Parameter(Mandatory = $true)][string]$RemoteRoot,
    [Parameter(Mandatory = $true)][string]$OutputDirectory,
    [Parameter(Mandatory = $true)][string]$PreflightReceipt,
    [Parameter(Mandatory = $true)][string]$StandardOutputPath,
    [Parameter(Mandatory = $true)][string]$StandardErrorPath
)

$ErrorActionPreference = 'Stop'

function ConvertTo-SingleQuotedPowerShellLiteral {
    param([string]$Value)
    return "'" + $Value.Replace("'", "''") + "'"
}

function Get-Sha256Text {
    param([string]$Value)
    $algorithm = [System.Security.Cryptography.SHA256]::Create()
    try {
        $bytes = [System.Text.Encoding]::UTF8.GetBytes($Value)
        return ([BitConverter]::ToString($algorithm.ComputeHash($bytes))).Replace('-', '')
    }
    finally {
        $algorithm.Dispose()
    }
}

function Get-Sha256Stream {
    param([System.IO.Stream]$Stream)
    $algorithm = [System.Security.Cryptography.SHA256]::Create()
    try {
        $Stream.Position = 0
        $hash = ([BitConverter]::ToString($algorithm.ComputeHash($Stream))).Replace('-', '')
        $Stream.Position = 0
        return $hash
    }
    finally {
        $algorithm.Dispose()
    }
}

function Read-JsonStream {
    param([System.IO.Stream]$Stream)
    $Stream.Position = 0
    $reader = [System.IO.StreamReader]::new(
        $Stream,
        [System.Text.UTF8Encoding]::new($true),
        $true,
        4096,
        $true
    )
    try {
        return ($reader.ReadToEnd() | ConvertFrom-Json)
    }
    finally {
        $reader.Dispose()
        $Stream.Position = 0
    }
}

function Assert-OrdinaryPathChain {
    param([string]$PathValue, [string]$Label)
    $item = Get-Item -Force -LiteralPath $PathValue
    while ($null -ne $item) {
        if (($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) {
            throw "$Label may not traverse a link or reparse point."
        }
        $item = $item.Parent
    }
}

function Assert-ProperDescendant {
    param([string]$Candidate, [string]$Root, [string]$Label)
    $separator = [System.IO.Path]::DirectorySeparatorChar
    $prefix = $Root.TrimEnd($separator, [System.IO.Path]::AltDirectorySeparatorChar) + $separator
    if (-not $Candidate.StartsWith($prefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "$Label must stay below $Root."
    }
}

if ($RemoteRoot -ne '/') {
    throw "The audited Home.pl backup launcher requires RemoteRoot to be exactly '/'."
}
$repoRoot = [System.IO.Path]::GetFullPath((Split-Path -Parent $PSScriptRoot))
$expectedBackupScript = (
    Resolve-Path -LiteralPath (Join-Path $repoRoot 'website\backup-homepl-ftps.ps1')
).Path
$resolvedBackupScript = (Resolve-Path -LiteralPath $BackupScript).Path
if ($resolvedBackupScript -ne $expectedBackupScript) {
    throw 'BackupScript must resolve to the exact repository Home.pl backup script.'
}
$receiptsRoot = [System.IO.Path]::GetFullPath(
    (Join-Path $repoRoot 'artifacts\website-operator')
)
$backupRoot = [System.IO.Path]::GetFullPath(
    (Join-Path $repoRoot 'artifacts\homepl-backups')
)
$resolvedPreflightReceipt = [System.IO.Path]::GetFullPath($PreflightReceipt)
$resolvedOutputDirectory = [System.IO.Path]::GetFullPath($OutputDirectory)
$manifestPath = "$resolvedOutputDirectory-manifest.csv"
$rootMappingReceipt = "$resolvedOutputDirectory-root-mapping.json"
$transferReceiptPath = "$resolvedOutputDirectory-transfer.json"
Assert-OrdinaryPathChain -PathValue $expectedBackupScript -Label 'Home.pl backup script'
$scriptReadLock = [System.IO.File]::Open(
    $expectedBackupScript,
    [System.IO.FileMode]::Open,
    [System.IO.FileAccess]::Read,
    [System.IO.FileShare]::Read
)
$expectedBackupScriptSha256 = Get-Sha256Stream -Stream $scriptReadLock
$preflightReadLock = $null
$rootMappingReadLock = $null
$liveReconciliationReadLock = $null
try {
Assert-OrdinaryPathChain -PathValue $receiptsRoot -Label 'Website Operator receipts root'
Assert-OrdinaryPathChain -PathValue $backupRoot -Label 'Home.pl backup root'
Assert-OrdinaryPathChain `
    -PathValue (Split-Path -Parent $resolvedOutputDirectory) `
    -Label 'Home.pl backup output parent'
Assert-OrdinaryPathChain `
    -PathValue $resolvedPreflightReceipt `
    -Label 'Home.pl backup preflight'
Assert-ProperDescendant `
    -Candidate $resolvedPreflightReceipt `
    -Root $receiptsRoot `
    -Label 'Home.pl backup preflight'
Assert-ProperDescendant `
    -Candidate $resolvedOutputDirectory `
    -Root $backupRoot `
    -Label 'Home.pl backup output'
if (
    (Test-Path -LiteralPath $resolvedOutputDirectory) -or
    (Test-Path -LiteralPath $manifestPath) -or
    (Test-Path -LiteralPath $transferReceiptPath)
) {
    throw 'The preflight-bound backup output, manifest, and transfer receipt must all be absent.'
}

$parsedHost = $null
if (
    -not [Uri]::TryCreate("ftp://$FtpHost/", [UriKind]::Absolute, [ref]$parsedHost) -or
    $parsedHost.Scheme -ne 'ftp' -or
    [string]::IsNullOrWhiteSpace($parsedHost.Host) -or
    -not [string]::IsNullOrEmpty($parsedHost.UserInfo) -or
    $parsedHost.AbsolutePath -ne '/' -or
    -not [string]::IsNullOrEmpty($parsedHost.Query) -or
    -not [string]::IsNullOrEmpty($parsedHost.Fragment)
) {
    throw 'FtpHost must be one FTP hostname with an optional port.'
}
$ftpHostId = "$($parsedHost.IdnHost.ToLowerInvariant()):$($parsedHost.Port)"
$normalisedAccount = $FtpUser.Normalize([System.Text.NormalizationForm]::FormC)
if (
    [string]::IsNullOrWhiteSpace($normalisedAccount) -or
    $normalisedAccount -ne $FtpUser.Trim() -or
    $normalisedAccount.Length -gt 256 -or
    $normalisedAccount -match '\p{C}'
) {
    throw 'FtpUser must be one trimmed account identifier without control characters.'
}
$ftpHostSha256 = Get-Sha256Text -Value $ftpHostId
$ftpAccountSha256 = Get-Sha256Text -Value $normalisedAccount
$ftpBindingSha256 = Get-Sha256Text -Value "$ftpHostId`0$normalisedAccount"

$preflightReadLock = [System.IO.File]::Open(
    $resolvedPreflightReceipt,
    [System.IO.FileMode]::Open,
    [System.IO.FileAccess]::Read,
    [System.IO.FileShare]::Read
)
$preflightSha256 = Get-Sha256Stream -Stream $preflightReadLock
$preflight = Read-JsonStream -Stream $preflightReadLock
$expectedSiteRoot = [System.IO.Path]::GetFullPath((Join-Path $repoRoot 'website'))
$expectedCredentialNames = @(
    'HOMEPL_FTPS_HOST',
    'HOMEPL_FTPS_USER',
    'HOMEPL_FTPS_PASSWORD'
)
$expectedReadOnlyMethods = @('ListDirectory', 'GetFileSize', 'DownloadFile')
if (
    $preflight.schema -ne 'aureon.website-operator.backup-preflight.v1' -or
    $preflight.state -ne 'ready-for-explicit-backup' -or
    $preflight.repo_root -ne $repoRoot -or
    $preflight.site_root -ne $expectedSiteRoot -or
    $preflight.backup_script -ne $expectedBackupScript -or
    $preflight.backup_script_sha256 -ne $expectedBackupScriptSha256 -or
    $preflight.backup_script_safe -ne $true -or
    $preflight.backup_root -ne $backupRoot -or
    $preflight.backup_root_safe -ne $true -or
    $preflight.output_directory -ne $resolvedOutputDirectory -or
    $preflight.output_directory_exists -ne $false -or
    $preflight.output_parent_exists -ne $true -or
    $preflight.output_parent_safe -ne $true -or
    $preflight.output_within_backup_root -ne $true -or
    $preflight.manifest -ne $manifestPath -or
    $preflight.manifest_exists -ne $false -or
    $preflight.root_mapping_receipt -ne $rootMappingReceipt -or
    $preflight.root_mapping_receipt_exists -ne $false -or
    $preflight.transfer_receipt -ne $transferReceiptPath -or
    $preflight.transfer_receipt_exists -ne $false -or
    $preflight.remote_root -ne '/' -or
    $preflight.ftp_host_id -ne $ftpHostId -or
    $preflight.ftp_host_sha256 -ne $ftpHostSha256 -or
    $preflight.ftp_account_sha256 -ne $ftpAccountSha256 -or
    $preflight.ftp_binding_sha256 -ne $ftpBindingSha256 -or
    $preflight.public_root_sha256 -notmatch '^[A-F0-9]{64}$' -or
    $preflight.public_root_bytes -lt 1 -or
    $preflight.public_root_url -notmatch '^https://' -or
    $preflight.destructive_action -ne $false -or
    $preflight.execution_attempted -ne $false -or
    @($preflight.credentials.PSObject.Properties.Name).Count -ne 2 -or
    @($preflight.credentials.required_runtime_names).Count -ne
        $expectedCredentialNames.Count -or
    (Compare-Object @($preflight.credentials.required_runtime_names) $expectedCredentialNames) -or
    $preflight.credentials.values_recorded -ne $false -or
    $preflight.read_only_contract.remote_write_methods_permitted -ne $false -or
    $preflight.read_only_contract.final_output_published_only_after_complete_download -ne $true -or
    $preflight.read_only_contract.manifest_overwrite_permitted -ne $false -or
    @($preflight.read_only_contract.remote_methods).Count -ne $expectedReadOnlyMethods.Count -or
    (Compare-Object @($preflight.read_only_contract.remote_methods) $expectedReadOnlyMethods)
) {
    throw 'The preflight does not bind the exact repository script, host, account, and output.'
}
$rawLiveReconciliationReceipt = [string]$preflight.live_reconciliation_receipt
if ([string]::IsNullOrWhiteSpace($rawLiveReconciliationReceipt)) {
    throw 'The preflight lacks a current public root reconciliation receipt.'
}
$resolvedLiveReconciliationReceipt = [System.IO.Path]::GetFullPath(
    $rawLiveReconciliationReceipt
)
if (
    -not [string]::Equals(
        $rawLiveReconciliationReceipt,
        $resolvedLiveReconciliationReceipt,
        [System.StringComparison]::OrdinalIgnoreCase
    )
) {
    throw 'The public root reconciliation receipt path is not canonical.'
}
Assert-OrdinaryPathChain `
    -PathValue $resolvedLiveReconciliationReceipt `
    -Label 'Home.pl live reconciliation receipt'
Assert-ProperDescendant `
    -Candidate $resolvedLiveReconciliationReceipt `
    -Root $receiptsRoot `
    -Label 'Home.pl live reconciliation receipt'
$liveReconciliationReadLock = [System.IO.File]::Open(
    $resolvedLiveReconciliationReceipt,
    [System.IO.FileMode]::Open,
    [System.IO.FileAccess]::Read,
    [System.IO.FileShare]::Read
)
$liveReconciliationSha256 = Get-Sha256Stream -Stream $liveReconciliationReadLock
if (
    $preflight.live_reconciliation_receipt -ne $resolvedLiveReconciliationReceipt -or
    $preflight.live_reconciliation_receipt_sha256 -ne $liveReconciliationSha256
) {
    throw 'The public root reconciliation receipt changed after preflight.'
}
$liveObserved = [DateTimeOffset]::Parse($preflight.live_reconciliation_observed_at)
$localValidationNow = [DateTimeOffset]::UtcNow
if (
    $liveObserved -gt $localValidationNow.AddMinutes(5) -or
    $liveObserved -lt $localValidationNow.AddMinutes(-15)
) {
    throw 'The preflight-bound public root observation is future-dated or stale.'
}
if (-not (Test-Path -LiteralPath $rootMappingReceipt -PathType Leaf)) {
    throw 'A preflight-bound authenticated served-root mapping is required before secret handoff.'
}
Assert-OrdinaryPathChain `
    -PathValue $rootMappingReceipt `
    -Label 'Home.pl authenticated root mapping'
$rootMappingReadLock = [System.IO.File]::Open(
    $rootMappingReceipt,
    [System.IO.FileMode]::Open,
    [System.IO.FileAccess]::Read,
    [System.IO.FileShare]::Read
)
$rootMappingSha256 = Get-Sha256Stream -Stream $rootMappingReadLock
$rootMapping = Read-JsonStream -Stream $rootMappingReadLock
$expectedMappingOperations = @('ListDirectory', 'DownloadFile')
if (
    $rootMapping.schema -ne 'aureon.homepl-root-mapping.v1' -or
    $rootMapping.state -ne 'authenticated-served-root-mapped' -or
    $rootMapping.method -ne 'homepl-ftps' -or
    $rootMapping.source_assertion -ne
        'Authenticated Home.pl account mapped to current public root bytes' -or
    $rootMapping.source_tool -ne 'repo-read-only-ftps-script' -or
    $rootMapping.remote_root -ne '/' -or
    $rootMapping.ftp_host_id -ne $ftpHostId -or
    $rootMapping.ftp_host_sha256 -ne $ftpHostSha256 -or
    $rootMapping.ftp_account_sha256 -ne $ftpAccountSha256 -or
    $rootMapping.ftp_binding_sha256 -ne $ftpBindingSha256 -or
    $rootMapping.preflight_receipt -ne $resolvedPreflightReceipt -or
    $rootMapping.preflight_receipt_sha256 -ne $preflightSha256 -or
    $rootMapping.backup_script -ne $expectedBackupScript -or
    $rootMapping.backup_script_sha256 -ne $expectedBackupScriptSha256 -or
    $rootMapping.live_reconciliation_receipt -ne $resolvedLiveReconciliationReceipt -or
    $rootMapping.live_reconciliation_receipt_sha256 -ne $liveReconciliationSha256 -or
    $rootMapping.live_reconciliation_observed_at -ne
        $preflight.live_reconciliation_observed_at -or
    $rootMapping.public_root_url -ne $preflight.public_root_url -or
    $rootMapping.public_root_sha256 -ne $preflight.public_root_sha256 -or
    $rootMapping.public_root_bytes -ne $preflight.public_root_bytes -or
    $rootMapping.public_root_sha256 -ne $rootMapping.remote_root_index_sha256 -or
    $rootMapping.public_root_bytes -ne $rootMapping.remote_root_index_bytes -or
    $rootMapping.listing_entry_count -lt @($preflight.required_root_entries).Count -or
    $rootMapping.listing_sha256 -notmatch '^[A-F0-9]{64}$' -or
    $rootMapping.required_root_entries_observed -ne $true -or
    (Compare-Object @($rootMapping.required_root_entries) @($preflight.required_root_entries)) -or
    @($rootMapping.remote_operations).Count -ne $expectedMappingOperations.Count -or
    (Compare-Object @($rootMapping.remote_operations) $expectedMappingOperations) -or
    $rootMapping.remote_write_methods_used -ne $false -or
    $rootMapping.credentials_recorded -ne $false
) {
    throw 'The root mapping does not bind the exact repository script, host, account, and public bytes.'
}
$rootMappingObserved = [DateTimeOffset]::Parse($rootMapping.observed_at)
if (
    $rootMappingObserved -gt $localValidationNow.AddMinutes(5) -or
    $rootMappingObserved -lt $localValidationNow.AddMinutes(-15) -or
    $rootMappingObserved -lt $liveObserved.AddMinutes(-5)
) {
    throw 'The authenticated root mapping is future-dated, stale, or predates its public observation.'
}

$resolvedStandardOutput = [System.IO.Path]::GetFullPath($StandardOutputPath)
$resolvedStandardError = [System.IO.Path]::GetFullPath($StandardErrorPath)
if (
    (Test-Path -LiteralPath $resolvedStandardOutput) -or
    (Test-Path -LiteralPath $resolvedStandardError)
) {
    throw 'Refusing to replace an existing backup process log.'
}
foreach ($parent in @(
    (Split-Path -Parent $resolvedStandardOutput),
    (Split-Path -Parent $resolvedStandardError)
)) {
    if (-not (Test-Path -LiteralPath $parent -PathType Container)) {
        throw "Backup process log parent does not exist: $parent"
    }
    if (
        ((Get-Item -Force -LiteralPath $parent).Attributes -band
            [System.IO.FileAttributes]::ReparsePoint) -ne 0
    ) {
        throw "Backup process logs may not traverse a link or reparse point: $parent"
    }
}

if (
    (Get-Sha256Stream -Stream $scriptReadLock) -ne $expectedBackupScriptSha256 -or
    (Get-Sha256Stream -Stream $preflightReadLock) -ne $preflightSha256 -or
    (Get-Sha256Stream -Stream $rootMappingReadLock) -ne $rootMappingSha256 -or
    (Get-Sha256Stream -Stream $liveReconciliationReadLock) -ne
        $liveReconciliationSha256
) {
    throw 'A locked backup input changed before secret handoff.'
}

$passwordValue = [Console]::In.ReadLine()
if ([string]::IsNullOrWhiteSpace($passwordValue)) {
    throw 'Supply the temporary FTPS password on standard input.'
}

$command = @(
    '&',
    (ConvertTo-SingleQuotedPowerShellLiteral $resolvedBackupScript),
    '-FtpHost',
    (ConvertTo-SingleQuotedPowerShellLiteral $FtpHost),
    '-FtpUser',
    (ConvertTo-SingleQuotedPowerShellLiteral $FtpUser),
    '-RemoteRoot',
    "'/'",
    '-OutputDirectory',
    (ConvertTo-SingleQuotedPowerShellLiteral $resolvedOutputDirectory),
    '-PreflightReceipt',
    (ConvertTo-SingleQuotedPowerShellLiteral $resolvedPreflightReceipt)
) -join ' '
$encodedCommand = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($command))
$processInfo = [System.Diagnostics.ProcessStartInfo]::new()
$processInfo.FileName = 'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'
$processInfo.Arguments = "-NoProfile -ExecutionPolicy Bypass -EncodedCommand $encodedCommand"
$processInfo.UseShellExecute = $false
$processInfo.CreateNoWindow = $true
$processInfo.WindowStyle = [System.Diagnostics.ProcessWindowStyle]::Hidden
$processInfo.RedirectStandardOutput = $true
$processInfo.RedirectStandardError = $true
$processInfo.EnvironmentVariables['HOMEPL_FTPS_PASSWORD'] = $passwordValue

$process = [System.Diagnostics.Process]::new()
$process.StartInfo = $processInfo
try {
    if (-not $process.Start()) {
        throw 'The Home.pl backup process did not start.'
    }
    $standardOutputTask = $process.StandardOutput.ReadToEndAsync()
    $standardErrorTask = $process.StandardError.ReadToEndAsync()
    $process.WaitForExit()
    $standardOutput = $standardOutputTask.GetAwaiter().GetResult()
    $standardError = $standardErrorTask.GetAwaiter().GetResult()
    $utf8NoBom = [System.Text.UTF8Encoding]::new($false)
    [System.IO.File]::WriteAllText($resolvedStandardOutput, $standardOutput, $utf8NoBom)
    [System.IO.File]::WriteAllText($resolvedStandardError, $standardError, $utf8NoBom)
    $result = [pscustomobject]@{
        State = if ($process.ExitCode -eq 0) {
            'backup-process-completed'
        }
        else {
            'backup-process-failed'
        }
        ProcessId = $process.Id
        ExitCode = $process.ExitCode
        OutputDirectory = $resolvedOutputDirectory
        PreflightReceipt = $resolvedPreflightReceipt
        TransferReceipt = "$resolvedOutputDirectory-transfer.json"
        StandardOutput = $resolvedStandardOutput
        StandardError = $resolvedStandardError
        RemoteRoot = '/'
        CredentialsRecorded = $false
    }
    $result | ConvertTo-Json -Depth 3
    if ($process.ExitCode -ne 0) {
        throw "Home.pl backup process failed; inspect the unique standard-error log."
    }
}
finally {
    $passwordValue = $null
    $process.Dispose()
}
}
finally {
    if ($null -ne $liveReconciliationReadLock) {
        $liveReconciliationReadLock.Dispose()
    }
    if ($null -ne $rootMappingReadLock) {
        $rootMappingReadLock.Dispose()
    }
    if ($null -ne $preflightReadLock) {
        $preflightReadLock.Dispose()
    }
    $scriptReadLock.Dispose()
}
