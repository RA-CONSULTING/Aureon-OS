[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][ValidateNotNullOrEmpty()][string]$FtpHost,
    [Parameter(Mandatory = $true)][ValidateNotNullOrEmpty()][string]$FtpUser,
    [Parameter(Mandatory = $true)][ValidateNotNullOrEmpty()][string]$RemoteRoot,
    [Parameter(Mandatory = $true)][ValidateNotNullOrEmpty()][string]$OutputDirectory,
    [Parameter(Mandatory = $true)][ValidateNotNullOrEmpty()][string]$PreflightReceipt,
    [string]$ExpectedCertificateThumbprint = $env:HOMEPL_FTPS_CERT_THUMBPRINT,
    [ValidateRange(1, 256)][int]$MaximumDepth = 64,
    [ValidateRange(1, 1000000)][int]$MaximumFiles = 100000,
    [ValidateRange(1, [long]::MaxValue)][long]$MaximumTotalBytes = 10GB,
    [switch]$ReadPasswordFromStandardInput,
    [switch]$DiagnoseCertificate,
    [switch]$ListOnly
)

$ErrorActionPreference = 'Stop'
$script:downloadedFileCount = 0
$script:downloadedTotalBytes = [long]0

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

function Write-NewUtf8Json {
    param([string]$PathValue, [object]$Value)
    if (Test-Path -LiteralPath $PathValue) {
        throw "Refusing to replace an existing receipt: $PathValue"
    }
    $temporary = "$PathValue.partial-$([guid]::NewGuid().ToString('N'))"
    $utf8NoBom = [System.Text.UTF8Encoding]::new($false)
    try {
        [System.IO.File]::WriteAllText(
            $temporary,
            (($Value | ConvertTo-Json -Depth 8) + [Environment]::NewLine),
            $utf8NoBom
        )
        [System.IO.File]::Move($temporary, $PathValue)
    }
    finally {
        if (Test-Path -LiteralPath $temporary) {
            Remove-Item -LiteralPath $temporary -Force
        }
    }
}

function Get-RemoteUri {
    param([string]$HostName, [string]$RemotePath)
    $segments = @(
        $RemotePath.Trim('/').Split(
            [char[]]@('/'),
            [System.StringSplitOptions]::RemoveEmptyEntries
        ) | ForEach-Object { [Uri]::EscapeDataString($_) }
    )
    $encodedPath = if ($segments.Count -eq 0) { '/' } else { '/' + ($segments -join '/') }
    return "ftp://$HostName$encodedPath"
}

function New-FtpRequest {
    param([string]$Uri, [string]$Method, [string]$UserName, [string]$PasswordValue)
    $request = [System.Net.FtpWebRequest]::Create($Uri)
    $request.Method = $Method
    $request.EnableSsl = $true
    $request.UseBinary = $true
    $request.UsePassive = $true
    $request.KeepAlive = $false
    $request.Timeout = 30000
    $request.ReadWriteTimeout = 60000
    $request.Credentials = [System.Net.NetworkCredential]::new($UserName, $PasswordValue)
    return $request
}

function Get-RemoteNames {
    param([string]$RemotePath, [string]$UserName, [string]$PasswordValue)
    $request = New-FtpRequest `
        -Uri (Get-RemoteUri -HostName $FtpHost -RemotePath $RemotePath) `
        -Method ([System.Net.WebRequestMethods+Ftp]::ListDirectory) `
        -UserName $UserName `
        -PasswordValue $PasswordValue
    $response = $request.GetResponse()
    $reader = [System.IO.StreamReader]::new($response.GetResponseStream())
    try {
        $names = @(
            $reader.ReadToEnd().Split(
                @("`r`n", "`n"),
                [System.StringSplitOptions]::RemoveEmptyEntries
            )
        )
        $relativeDirectory = $RemotePath.Trim('/')
        if (-not [string]::IsNullOrWhiteSpace($relativeDirectory)) {
            $lastDirectoryName = @($relativeDirectory.Split('/'))[-1]
            $expectedPrefixes = @("$relativeDirectory/", "$lastDirectoryName/") |
                Select-Object -Unique
            $names = @(
                $names | ForEach-Object {
                    $entry = $_
                    $matchingPrefix = @(
                        $expectedPrefixes | Where-Object {
                            $entry.StartsWith($_, [System.StringComparison]::Ordinal)
                        } | Select-Object -First 1
                    )
                    if ($matchingPrefix.Count -eq 1) {
                        $entry.Substring($matchingPrefix[0].Length)
                    }
                    else {
                        $entry
                    }
                }
            )
        }
        return $names
    }
    finally {
        $reader.Dispose()
        $response.Dispose()
    }
}

function Get-RemoteFileSize {
    param([string]$RemotePath, [string]$UserName, [string]$PasswordValue)
    try {
        $request = New-FtpRequest `
            -Uri (Get-RemoteUri -HostName $FtpHost -RemotePath $RemotePath) `
            -Method ([System.Net.WebRequestMethods+Ftp]::GetFileSize) `
            -UserName $UserName `
            -PasswordValue $PasswordValue
        $response = $request.GetResponse()
        try {
            if ($response.ContentLength -lt 0) {
                throw "Home.pl returned a negative size for $RemotePath."
            }
            return [int64]$response.ContentLength
        }
        finally {
            $response.Dispose()
        }
    }
    catch [System.Net.WebException] {
        return $null
    }
}

function Get-RemoteFileObservation {
    param(
        [string]$RemotePath,
        [string]$UserName,
        [string]$PasswordValue,
        [int64]$MaximumBytes = 16MB
    )
    $request = New-FtpRequest `
        -Uri (Get-RemoteUri -HostName $FtpHost -RemotePath $RemotePath) `
        -Method ([System.Net.WebRequestMethods+Ftp]::DownloadFile) `
        -UserName $UserName `
        -PasswordValue $PasswordValue
    $response = $request.GetResponse()
    $input = $response.GetResponseStream()
    $memory = [System.IO.MemoryStream]::new()
    $buffer = New-Object byte[] 65536
    try {
        while (($count = $input.Read($buffer, 0, $buffer.Length)) -gt 0) {
            if ($memory.Length + $count -gt $MaximumBytes) {
                throw "Remote root probe exceeds the permitted byte limit."
            }
            $memory.Write($buffer, 0, $count)
        }
        $algorithm = [System.Security.Cryptography.SHA256]::Create()
        try {
            $sha256 = ([BitConverter]::ToString(
                $algorithm.ComputeHash($memory.ToArray())
            )).Replace('-', '')
        }
        finally {
            $algorithm.Dispose()
        }
        return [pscustomobject]@{
            Bytes = [int64]$memory.Length
            Sha256 = $sha256
        }
    }
    finally {
        $memory.Dispose()
        $input.Dispose()
        $response.Dispose()
    }
}

function Assert-SafeRemoteName {
    param([string]$Name)
    if (
        [string]::IsNullOrWhiteSpace($Name) -or
        $Name -in @('.', '..') -or
        $Name.IndexOfAny([System.IO.Path]::GetInvalidFileNameChars()) -ge 0 -or
        $Name.EndsWith(' ', [System.StringComparison]::Ordinal) -or
        $Name.EndsWith('.', [System.StringComparison]::Ordinal) -or
        $Name -match '^(?i:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)'
    ) {
        throw "Home.pl returned a remote name that cannot be represented safely on Windows."
    }
}

function Get-CheckedRemoteNames {
    param([string]$RemotePath, [string]$UserName, [string]$PasswordValue)
    $seen = @{}
    $result = @()
    foreach (
        $name in (
            Get-RemoteNames `
                -RemotePath $RemotePath `
                -UserName $UserName `
                -PasswordValue $PasswordValue
        )
    ) {
        if ($name -in @('.', '..')) {
            continue
        }
        Assert-SafeRemoteName -Name $name
        $key = $name.Normalize([System.Text.NormalizationForm]::FormC).ToUpperInvariant()
        if ($seen.ContainsKey($key)) {
            throw "Home.pl returned case- or Unicode-colliding names in $RemotePath."
        }
        $seen[$key] = $true
        $result += $name
    }
    return $result
}

function Get-AuthenticatedRootObservation {
    param([string]$UserName, [string]$PasswordValue)
    $names = Get-CheckedRemoteNames `
        -RemotePath '/' `
        -UserName $UserName `
        -PasswordValue $PasswordValue
    $missingRequired = @(
        $preflight.required_root_entries | Where-Object {
            -not (@($names) -ccontains [string]$_)
        }
    )
    if ($missingRequired.Count -gt 0) {
        throw 'The authenticated / listing is missing preflight-required root entries.'
    }
    $rootIndex = Get-RemoteFileObservation `
        -RemotePath '/index.html' `
        -UserName $UserName `
        -PasswordValue $PasswordValue
    $sortedNames = [string[]]@($names)
    [Array]::Sort($sortedNames, [System.StringComparer]::Ordinal)
    return [pscustomobject]@{
        ListingEntryCount = @($names).Count
        ListingSha256 = Get-Sha256Text -Value (($sortedNames -join "`n") + "`n")
        RootIndexSha256 = $rootIndex.Sha256
        RootIndexBytes = [int64]$rootIndex.Bytes
    }
}

function Receive-RemoteFile {
    param(
        [string]$RemotePath,
        [string]$LocalPath,
        [int64]$ExpectedBytes,
        [string]$UserName,
        [string]$PasswordValue
    )
    $nextCount = $script:downloadedFileCount + 1
    $nextBytes = $script:downloadedTotalBytes + $ExpectedBytes
    if ($nextCount -gt $MaximumFiles) {
        throw "Backup file-count safety limit reached before downloading $RemotePath."
    }
    if ($nextBytes -gt $MaximumTotalBytes) {
        throw "Backup byte safety limit reached before downloading $RemotePath."
    }
    $request = New-FtpRequest `
        -Uri (Get-RemoteUri -HostName $FtpHost -RemotePath $RemotePath) `
        -Method ([System.Net.WebRequestMethods+Ftp]::DownloadFile) `
        -UserName $UserName `
        -PasswordValue $PasswordValue
    $response = $request.GetResponse()
    $input = $response.GetResponseStream()
    $output = [System.IO.File]::Open(
        $LocalPath,
        [System.IO.FileMode]::CreateNew,
        [System.IO.FileAccess]::Write,
        [System.IO.FileShare]::None
    )
    try {
        $input.CopyTo($output)
    }
    finally {
        $output.Dispose()
        $input.Dispose()
        $response.Dispose()
    }
    $actualBytes = (Get-Item -Force -LiteralPath $LocalPath).Length
    if ($actualBytes -ne $ExpectedBytes) {
        throw "Downloaded byte count did not match Home.pl for $RemotePath."
    }
    $script:downloadedFileCount = $nextCount
    $script:downloadedTotalBytes = $nextBytes
}

function Copy-RemoteTree {
    param(
        [string]$RemotePath,
        [string]$LocalPath,
        [string]$UserName,
        [string]$PasswordValue,
        [int]$Depth
    )
    if ($Depth -gt $MaximumDepth) {
        throw "Backup directory-depth safety limit reached at $RemotePath."
    }
    [System.IO.Directory]::CreateDirectory($LocalPath) | Out-Null
    foreach (
        $name in (
            Get-CheckedRemoteNames `
                -RemotePath $RemotePath `
                -UserName $UserName `
                -PasswordValue $PasswordValue
        )
    ) {
        $childRemotePath = "$($RemotePath.TrimEnd('/'))/$name"
        $childLocalPath = Join-Path $LocalPath $name
        $fileSize = Get-RemoteFileSize `
            -RemotePath $childRemotePath `
            -UserName $UserName `
            -PasswordValue $PasswordValue
        if ($null -ne $fileSize) {
            Receive-RemoteFile `
                -RemotePath $childRemotePath `
                -LocalPath $childLocalPath `
                -ExpectedBytes $fileSize `
                -UserName $UserName `
                -PasswordValue $PasswordValue
        }
        else {
            Copy-RemoteTree `
                -RemotePath $childRemotePath `
                -LocalPath $childLocalPath `
                -UserName $UserName `
                -PasswordValue $PasswordValue `
                -Depth ($Depth + 1)
        }
    }
}

if ($RemoteRoot -ne '/') {
    throw "This audited backup tool requires the verified Home.pl document root to be exactly '/'."
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
    throw 'FtpHost must be one FTP hostname with an optional port, without a scheme or path.'
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
if (
    -not [string]::IsNullOrWhiteSpace($ExpectedCertificateThumbprint) -and
    ($ExpectedCertificateThumbprint -replace '[^0-9A-Fa-f]', '').Length -ne 40
) {
    throw 'HOMEPL_FTPS_CERT_THUMBPRINT must be one 40-character certificate thumbprint.'
}

$scriptPath = [System.IO.Path]::GetFullPath($PSCommandPath)
$scriptSha256 = (Get-FileHash -LiteralPath $scriptPath -Algorithm SHA256).Hash
$repoRoot = [System.IO.Path]::GetFullPath((Split-Path -Parent $PSScriptRoot))
$backupRoot = [System.IO.Path]::GetFullPath(
    (Join-Path $repoRoot 'artifacts\homepl-backups')
)
$receiptsRoot = [System.IO.Path]::GetFullPath(
    (Join-Path $repoRoot 'artifacts\website-operator')
)
$resolvedOutputDirectory = [System.IO.Path]::GetFullPath($OutputDirectory)
$manifestPath = "$resolvedOutputDirectory-manifest.csv"
$rootMappingReceiptPath = "$resolvedOutputDirectory-root-mapping.json"
$transferReceiptPath = "$resolvedOutputDirectory-transfer.json"
$resolvedPreflightReceipt = [System.IO.Path]::GetFullPath($PreflightReceipt)

Assert-OrdinaryPathChain -PathValue $backupRoot -Label 'Home.pl backup root'
Assert-OrdinaryPathChain -PathValue $receiptsRoot -Label 'Website Operator receipts root'
Assert-OrdinaryPathChain `
    -PathValue (Split-Path -Parent $resolvedOutputDirectory) `
    -Label 'Home.pl backup output parent'
Assert-OrdinaryPathChain -PathValue $resolvedPreflightReceipt -Label 'Home.pl backup preflight'
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
if ($ListOnly -and (Test-Path -LiteralPath $rootMappingReceiptPath)) {
    throw 'Refusing to replace an existing authenticated root-mapping receipt.'
}
if (-not $ListOnly -and -not $DiagnoseCertificate -and
    -not (Test-Path -LiteralPath $rootMappingReceiptPath -PathType Leaf)) {
    throw 'A fresh authenticated served-root mapping receipt is required before transfer.'
}

$preflightSha256 = (Get-FileHash -LiteralPath $resolvedPreflightReceipt -Algorithm SHA256).Hash
$preflight = Get-Content -LiteralPath $resolvedPreflightReceipt -Raw | ConvertFrom-Json
$expectedReadOnlyMethods = @('ListDirectory', 'GetFileSize', 'DownloadFile')
if (
    $preflight.schema -ne 'aureon.website-operator.backup-preflight.v1' -or
    $preflight.state -ne 'ready-for-explicit-backup' -or
    $preflight.repo_root -ne $repoRoot -or
    $preflight.backup_script -ne $scriptPath -or
    $preflight.backup_script_sha256 -ne $scriptSha256 -or
    $preflight.backup_root -ne $backupRoot -or
    $preflight.output_directory -ne $resolvedOutputDirectory -or
    $preflight.manifest -ne $manifestPath -or
    $preflight.root_mapping_receipt -ne $rootMappingReceiptPath -or
    $preflight.transfer_receipt -ne $transferReceiptPath -or
    $preflight.remote_root -ne '/' -or
    $preflight.ftp_host_id -ne $ftpHostId -or
    $preflight.ftp_host_sha256 -ne $ftpHostSha256 -or
    $preflight.ftp_account_sha256 -ne $ftpAccountSha256 -or
    $preflight.ftp_binding_sha256 -ne $ftpBindingSha256 -or
    $preflight.backup_script_safe -ne $true -or
    $preflight.backup_root_safe -ne $true -or
    $preflight.output_parent_safe -ne $true -or
    $preflight.output_within_backup_root -ne $true -or
    $preflight.output_directory_exists -ne $false -or
    $preflight.manifest_exists -ne $false -or
    $preflight.root_mapping_receipt_exists -ne $false -or
    $preflight.transfer_receipt_exists -ne $false -or
    $preflight.destructive_action -ne $false -or
    $preflight.execution_attempted -ne $false -or
    $preflight.credentials.values_recorded -ne $false -or
    $preflight.read_only_contract.remote_write_methods_permitted -ne $false -or
    $preflight.read_only_contract.final_output_published_only_after_complete_download -ne $true -or
    $preflight.read_only_contract.manifest_overwrite_permitted -ne $false -or
    @($preflight.read_only_contract.remote_methods).Count -ne $expectedReadOnlyMethods.Count -or
    (Compare-Object @($preflight.read_only_contract.remote_methods) $expectedReadOnlyMethods)
) {
    throw 'The supplied backup preflight is stale, changed, or does not bind this exact read-only run.'
}
$rawLiveReconciliationReceipt = [string]$preflight.live_reconciliation_receipt
if ([string]::IsNullOrWhiteSpace($rawLiveReconciliationReceipt)) {
    throw 'The supplied backup preflight lacks a public root reconciliation binding.'
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
    throw 'The public root reconciliation path is not canonical.'
}
Assert-OrdinaryPathChain `
    -PathValue $resolvedLiveReconciliationReceipt `
    -Label 'Home.pl live reconciliation receipt'
Assert-ProperDescendant `
    -Candidate $resolvedLiveReconciliationReceipt `
    -Root $receiptsRoot `
    -Label 'Home.pl live reconciliation receipt'
$liveReconciliationSha256 = (
    Get-FileHash -LiteralPath $resolvedLiveReconciliationReceipt -Algorithm SHA256
).Hash
if (
    $preflight.live_reconciliation_receipt -ne $resolvedLiveReconciliationReceipt -or
    $preflight.live_reconciliation_receipt_sha256 -ne $liveReconciliationSha256 -or
    $preflight.public_root_sha256 -notmatch '^[A-F0-9]{64}$' -or
    $preflight.public_root_bytes -lt 1 -or
    $preflight.public_root_url -notmatch '^https://'
) {
    throw 'The supplied backup preflight lacks the exact current public root binding.'
}
$liveObserved = [DateTimeOffset]::Parse($preflight.live_reconciliation_observed_at)
$localValidationNow = [DateTimeOffset]::UtcNow
if (
    $liveObserved -gt $localValidationNow.AddMinutes(5) -or
    $liveObserved -lt $localValidationNow.AddMinutes(-15)
) {
    throw 'The preflight-bound public root observation is future-dated or stale.'
}

$rootMapping = $null
$rootMappingSha256 = ''
if (-not $ListOnly -and -not $DiagnoseCertificate) {
    Assert-OrdinaryPathChain `
        -PathValue $rootMappingReceiptPath `
        -Label 'Home.pl authenticated root mapping'
    $rootMappingSha256 = (
        Get-FileHash -LiteralPath $rootMappingReceiptPath -Algorithm SHA256
    ).Hash
    $rootMapping = Get-Content -LiteralPath $rootMappingReceiptPath -Raw | ConvertFrom-Json
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
        $rootMapping.backup_script -ne $scriptPath -or
        $rootMapping.backup_script_sha256 -ne $scriptSha256 -or
        $rootMapping.live_reconciliation_receipt -ne $resolvedLiveReconciliationReceipt -or
        $rootMapping.live_reconciliation_receipt_sha256 -ne $liveReconciliationSha256 -or
        $rootMapping.live_reconciliation_observed_at -ne
            $preflight.live_reconciliation_observed_at -or
        $rootMapping.public_root_url -ne $preflight.public_root_url -or
        $rootMapping.public_root_sha256 -ne $preflight.public_root_sha256 -or
        $rootMapping.public_root_bytes -ne $preflight.public_root_bytes -or
        $rootMapping.remote_root_index_sha256 -ne $preflight.public_root_sha256 -or
        $rootMapping.remote_root_index_bytes -ne $preflight.public_root_bytes -or
        $rootMapping.required_root_entries_observed -ne $true -or
        (Compare-Object @($rootMapping.required_root_entries) @($preflight.required_root_entries)) -or
        @($rootMapping.remote_operations).Count -ne $expectedMappingOperations.Count -or
        (Compare-Object @($rootMapping.remote_operations) $expectedMappingOperations) -or
        $rootMapping.remote_write_methods_used -ne $false -or
        $rootMapping.credentials_recorded -ne $false
    ) {
        throw 'The authenticated root-mapping receipt does not bind this exact host, account, and served root.'
    }
    $rootMappingObserved = [DateTimeOffset]::Parse($rootMapping.observed_at)
    $now = [DateTimeOffset]::UtcNow
    if (
        $rootMappingObserved -gt $now.AddMinutes(5) -or
        $rootMappingObserved -lt $now.AddMinutes(-15) -or
        $rootMappingObserved -lt $liveObserved.AddMinutes(-5)
    ) {
        throw 'The authenticated root-mapping receipt is future-dated, stale, or predates its public observation.'
    }
}

$passwordValue = if ($ReadPasswordFromStandardInput) {
    [Console]::In.ReadLine()
}
else {
    [Environment]::GetEnvironmentVariable('HOMEPL_FTPS_PASSWORD')
}
if ([string]::IsNullOrWhiteSpace($passwordValue)) {
    throw 'Supply HOMEPL_FTPS_PASSWORD only in the current process environment, or use -ReadPasswordFromStandardInput.'
}

[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$callbackInstalled = $false
try {
    if ($DiagnoseCertificate) {
        $script:certificateObservation = $null
        [Net.ServicePointManager]::ServerCertificateValidationCallback = {
            param($Sender, $Certificate, $Chain, $SslPolicyErrors)
            $certificate2 = [System.Security.Cryptography.X509Certificates.X509Certificate2]::new(
                $Certificate
            )
            $script:certificateObservation = [pscustomobject]@{
                Subject = $certificate2.Subject
                Issuer = $certificate2.Issuer
                Thumbprint = $certificate2.Thumbprint
                NotBeforeUtc = $certificate2.NotBefore.ToUniversalTime().ToString('o')
                NotAfterUtc = $certificate2.NotAfter.ToUniversalTime().ToString('o')
                SslPolicyErrors = $SslPolicyErrors.ToString()
            }
            return $false
        }
        $callbackInstalled = $true
        try {
            Get-CheckedRemoteNames `
                -RemotePath $RemoteRoot `
                -UserName $FtpUser `
                -PasswordValue $passwordValue | Out-Null
        }
        catch {
            [pscustomobject]@{
                State = 'certificate-diagnostics-complete-no-transfer'
                Host = $FtpHost
                Observation = $script:certificateObservation
                RemoteWriteMethodsUsed = $false
            } | ConvertTo-Json -Depth 4
            return
        }
        throw 'The certificate diagnostic unexpectedly completed a request.'
    }

    if (-not [string]::IsNullOrWhiteSpace($ExpectedCertificateThumbprint)) {
        $script:expectedCertificateThumbprint = (
            $ExpectedCertificateThumbprint -replace '[^0-9A-Fa-f]', ''
        ).ToUpperInvariant()
        [Net.ServicePointManager]::ServerCertificateValidationCallback = {
            param($Sender, $Certificate, $Chain, $SslPolicyErrors)
            if ($SslPolicyErrors -eq [Net.Security.SslPolicyErrors]::None) {
                return $true
            }
            if ($SslPolicyErrors -ne [Net.Security.SslPolicyErrors]::RemoteCertificateNameMismatch) {
                return $false
            }
            $certificate2 = [System.Security.Cryptography.X509Certificates.X509Certificate2]::new(
                $Certificate
            )
            $observedThumbprint = (
                $certificate2.Thumbprint -replace '[^0-9A-Fa-f]', ''
            ).ToUpperInvariant()
            $now = [datetime]::UtcNow
            return (
                $observedThumbprint -eq $script:expectedCertificateThumbprint -and
                $now -ge $certificate2.NotBefore.ToUniversalTime() -and
                $now -le $certificate2.NotAfter.ToUniversalTime()
            )
        }
        $callbackInstalled = $true
    }

    if ($ListOnly) {
        $rootObservation = Get-AuthenticatedRootObservation `
            -UserName $FtpUser `
            -PasswordValue $passwordValue
        if (
            $rootObservation.RootIndexSha256 -ne $preflight.public_root_sha256 -or
            $rootObservation.RootIndexBytes -ne $preflight.public_root_bytes
        ) {
            throw 'The authenticated /index.html bytes do not map to the current public homepage.'
        }
        if (
            (Get-FileHash -LiteralPath $resolvedPreflightReceipt -Algorithm SHA256).Hash -ne
                $preflightSha256 -or
            (Get-FileHash -LiteralPath $scriptPath -Algorithm SHA256).Hash -ne
                $scriptSha256 -or
            (Get-FileHash -LiteralPath $resolvedLiveReconciliationReceipt -Algorithm SHA256).Hash -ne
                $liveReconciliationSha256
        ) {
            throw 'The script, preflight, or public root evidence changed during root mapping.'
        }
        $rootMappingPayload = [ordered]@{
            schema = 'aureon.homepl-root-mapping.v1'
            state = 'authenticated-served-root-mapped'
            method = 'homepl-ftps'
            source_assertion =
                'Authenticated Home.pl account mapped to current public root bytes'
            source_tool = 'repo-read-only-ftps-script'
            observed_at = [datetime]::UtcNow.ToString('o')
            remote_root = '/'
            ftp_host_id = $ftpHostId
            ftp_host_sha256 = $ftpHostSha256
            ftp_account_sha256 = $ftpAccountSha256
            ftp_binding_sha256 = $ftpBindingSha256
            preflight_receipt = $resolvedPreflightReceipt
            preflight_receipt_sha256 = $preflightSha256
            backup_script = $scriptPath
            backup_script_sha256 = $scriptSha256
            live_reconciliation_receipt = $resolvedLiveReconciliationReceipt
            live_reconciliation_receipt_sha256 = $liveReconciliationSha256
            live_reconciliation_observed_at = $preflight.live_reconciliation_observed_at
            public_root_url = $preflight.public_root_url
            public_root_sha256 = $preflight.public_root_sha256
            public_root_bytes = [int64]$preflight.public_root_bytes
            remote_root_index_sha256 = $rootObservation.RootIndexSha256
            remote_root_index_bytes = [int64]$rootObservation.RootIndexBytes
            listing_entry_count = $rootObservation.ListingEntryCount
            listing_sha256 = $rootObservation.ListingSha256
            required_root_entries = @($preflight.required_root_entries)
            required_root_entries_observed = $true
            remote_operations = @('ListDirectory', 'DownloadFile')
            remote_write_methods_used = $false
            credentials_recorded = $false
        }
        Write-NewUtf8Json `
            -PathValue $rootMappingReceiptPath `
            -Value $rootMappingPayload
        [pscustomobject]@{
            State = 'authenticated-served-root-mapped'
            RemoteRoot = '/'
            FtpHostId = $ftpHostId
            FtpAccountSha256 = $ftpAccountSha256
            EntryCount = $rootObservation.ListingEntryCount
            ListingSha256 = $rootObservation.ListingSha256
            PublicRootSha256 = $preflight.public_root_sha256
            RootMappingReceipt = $rootMappingReceiptPath
            RootMappingReceiptSha256 = (
                Get-FileHash -LiteralPath $rootMappingReceiptPath -Algorithm SHA256
            ).Hash
            RemoteWriteMethodsUsed = $false
            CredentialsRecorded = $false
        } | ConvertTo-Json -Depth 3
        return
    }

    $startedAt = [datetime]::UtcNow.ToString('o')
    $transferStartRoot = Get-AuthenticatedRootObservation `
        -UserName $FtpUser `
        -PasswordValue $passwordValue
    if (
        $transferStartRoot.ListingEntryCount -ne $rootMapping.listing_entry_count -or
        $transferStartRoot.ListingSha256 -ne $rootMapping.listing_sha256 -or
        $transferStartRoot.RootIndexSha256 -ne $rootMapping.remote_root_index_sha256 -or
        $transferStartRoot.RootIndexBytes -ne $rootMapping.remote_root_index_bytes
    ) {
        throw 'The authenticated served root changed after root mapping and before transfer.'
    }
    $stagingDirectory = Join-Path `
        (Split-Path -Parent $resolvedOutputDirectory) `
        ('.' + (Split-Path -Leaf $resolvedOutputDirectory) + '.partial-' + [guid]::NewGuid().ToString('N'))
    $temporaryManifest = "$manifestPath.partial-$([guid]::NewGuid().ToString('N'))"
    $temporaryTransferReceipt = "$transferReceiptPath.partial-$([guid]::NewGuid().ToString('N'))"
    try {
        Copy-RemoteTree `
            -RemotePath $RemoteRoot `
            -LocalPath $stagingDirectory `
            -UserName $FtpUser `
            -PasswordValue $passwordValue `
            -Depth 0
        $files = @(Get-ChildItem -LiteralPath $stagingDirectory -File -Recurse)
        if ($files.Count -eq 0) {
            throw 'The FTPS backup completed with no files; verification and deployment are blocked.'
        }
        if ($files.Count -ne $script:downloadedFileCount) {
            throw 'The local backup file count differs from the authenticated transfer count.'
        }

        $manifest = foreach ($file in $files) {
            [pscustomobject]@{
                Path = $file.FullName.Substring($stagingDirectory.Length).
                    TrimStart([char]'\', [char]'/').
                    Replace('\', '/')
                Bytes = $file.Length
                Sha256 = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash
            }
        }
        $manifest = @($manifest | Sort-Object Path)
        $downloadedRootIndex = @(
            $manifest | Where-Object { $_.Path -ceq 'index.html' }
        )
        if (
            $downloadedRootIndex.Count -ne 1 -or
            $downloadedRootIndex[0].Sha256 -ne $rootMapping.remote_root_index_sha256 -or
            $downloadedRootIndex[0].Bytes -ne $rootMapping.remote_root_index_bytes
        ) {
            throw 'The downloaded /index.html does not match the authenticated public root mapping.'
        }
        $manifest | Export-Csv `
            -LiteralPath $temporaryManifest `
            -NoTypeInformation `
            -Encoding utf8
        $manifestSha256 = (Get-FileHash -LiteralPath $temporaryManifest -Algorithm SHA256).Hash
        $transferEndRoot = Get-AuthenticatedRootObservation `
            -UserName $FtpUser `
            -PasswordValue $passwordValue
        if (
            $transferEndRoot.ListingEntryCount -ne $rootMapping.listing_entry_count -or
            $transferEndRoot.ListingSha256 -ne $rootMapping.listing_sha256 -or
            $transferEndRoot.RootIndexSha256 -ne $rootMapping.remote_root_index_sha256 -or
            $transferEndRoot.RootIndexBytes -ne $rootMapping.remote_root_index_bytes -or
            $transferEndRoot.ListingEntryCount -ne $transferStartRoot.ListingEntryCount -or
            $transferEndRoot.ListingSha256 -ne $transferStartRoot.ListingSha256 -or
            $transferEndRoot.RootIndexSha256 -ne $transferStartRoot.RootIndexSha256 -or
            $transferEndRoot.RootIndexBytes -ne $transferStartRoot.RootIndexBytes
        ) {
            throw 'The authenticated served root changed during the backup transfer.'
        }
        $completedAt = [datetime]::UtcNow.ToString('o')
        $transfer = [ordered]@{
            schema = 'aureon.homepl-backup-transfer.v1'
            state = 'backup-complete'
            method = 'homepl-ftps'
            source_assertion = 'Authenticated Home.pl document-root download'
            source_tool = 'repo-read-only-ftps-script'
            started_at = $startedAt
            completed_at = $completedAt
            remote_root = '/'
            ftp_host_id = $ftpHostId
            ftp_host_sha256 = $ftpHostSha256
            ftp_account_sha256 = $ftpAccountSha256
            ftp_binding_sha256 = $ftpBindingSha256
            backup_directory = $resolvedOutputDirectory
            manifest = $manifestPath
            manifest_sha256 = $manifestSha256
            file_count = $files.Count
            total_bytes = [long]$script:downloadedTotalBytes
            preflight_receipt = $resolvedPreflightReceipt
            preflight_receipt_sha256 = $preflightSha256
            backup_script = $scriptPath
            backup_script_sha256 = $scriptSha256
            root_mapping_receipt = $rootMappingReceiptPath
            root_mapping_receipt_sha256 = $rootMappingSha256
            live_reconciliation_receipt = $resolvedLiveReconciliationReceipt
            live_reconciliation_receipt_sha256 = $liveReconciliationSha256
            public_root_sha256 = $preflight.public_root_sha256
            root_continuity_observed = $true
            transfer_start_root_listing_sha256 = $transferStartRoot.ListingSha256
            transfer_start_root_listing_entry_count = $transferStartRoot.ListingEntryCount
            transfer_start_root_index_sha256 = $transferStartRoot.RootIndexSha256
            transfer_start_root_index_bytes = [int64]$transferStartRoot.RootIndexBytes
            transfer_end_root_listing_sha256 = $transferEndRoot.ListingSha256
            transfer_end_root_listing_entry_count = $transferEndRoot.ListingEntryCount
            transfer_end_root_index_sha256 = $transferEndRoot.RootIndexSha256
            transfer_end_root_index_bytes = [int64]$transferEndRoot.RootIndexBytes
            remote_operations = @('ListDirectory', 'GetFileSize', 'DownloadFile')
            remote_write_methods_used = $false
            credentials_recorded = $false
        }
        $utf8NoBom = [System.Text.UTF8Encoding]::new($false)
        [System.IO.File]::WriteAllText(
            $temporaryTransferReceipt,
            (($transfer | ConvertTo-Json -Depth 5) + [Environment]::NewLine),
            $utf8NoBom
        )

        if (
            (Get-FileHash -LiteralPath $resolvedPreflightReceipt -Algorithm SHA256).Hash -ne
                $preflightSha256 -or
            (Get-FileHash -LiteralPath $scriptPath -Algorithm SHA256).Hash -ne
                $scriptSha256 -or
            (Get-FileHash -LiteralPath $rootMappingReceiptPath -Algorithm SHA256).Hash -ne
                $rootMappingSha256 -or
            (Get-FileHash -LiteralPath $resolvedLiveReconciliationReceipt -Algorithm SHA256).Hash -ne
                $liveReconciliationSha256
        ) {
            throw 'The script, preflight, root mapping, or public evidence changed during transfer.'
        }
        if (
            (Test-Path -LiteralPath $resolvedOutputDirectory) -or
            (Test-Path -LiteralPath $manifestPath) -or
            (Test-Path -LiteralPath $transferReceiptPath)
        ) {
            throw 'A final backup path appeared during transfer; no final output was published.'
        }
        [System.IO.Directory]::Move($stagingDirectory, $resolvedOutputDirectory)
        [System.IO.File]::Move($temporaryManifest, $manifestPath)
        [System.IO.File]::Move($temporaryTransferReceipt, $transferReceiptPath)
    }
    catch {
        if (Test-Path -LiteralPath $stagingDirectory) {
            Write-Warning "Incomplete backup staging was retained at: $stagingDirectory"
        }
        throw
    }

    [pscustomobject]@{
        State = 'backup-complete'
        Method = 'homepl-ftps'
        RemoteRoot = '/'
        FtpHostId = $ftpHostId
        FtpAccountSha256 = $ftpAccountSha256
        BackupDirectory = $resolvedOutputDirectory
        Manifest = $manifestPath
        RootMappingReceipt = $rootMappingReceiptPath
        TransferReceipt = $transferReceiptPath
        FileCount = $script:downloadedFileCount
        TotalBytes = $script:downloadedTotalBytes
        RemoteWriteMethodsUsed = $false
        CredentialsRecorded = $false
    } | ConvertTo-Json -Depth 3
}
finally {
    if ($callbackInstalled) {
        [Net.ServicePointManager]::ServerCertificateValidationCallback = $null
    }
    $passwordValue = $null
}
