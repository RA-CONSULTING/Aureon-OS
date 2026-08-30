[CmdletBinding()]
param(
    [string]$PackagePath,
    [string]$ManifestPath,
    [string]$WebsiteRoot = $PSScriptRoot,
    [string]$FtpHost = $env:HOMEPL_FTPS_HOST,
    [string]$FtpUser = $env:HOMEPL_FTPS_USER,
    [string]$RemoteRoot = $(if ($env:HOMEPL_FTPS_REMOTE_ROOT) { $env:HOMEPL_FTPS_REMOTE_ROOT } else { '/public_html' }),
    [string]$ExpectedCertificateThumbprint = $env:HOMEPL_FTPS_CERT_THUMBPRINT,
    [switch]$ReadPasswordFromStandardInput,
    [switch]$VerifyOnly,
    [switch]$Deploy
)

$ErrorActionPreference = 'Stop'

function Get-LatestReleasePath {
    param([string]$Directory, [string]$Filter)
    $candidate = Get-ChildItem -LiteralPath $Directory -Filter $Filter -File |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
    if (-not $candidate) { throw "No release matching '$Filter' was found in $Directory." }
    return $candidate.FullName
}

function Get-SafeRelativePath {
    param([string]$PathValue)
    if ([string]::IsNullOrWhiteSpace($PathValue)) { throw 'A manifest path is empty.' }
    $normalised = $PathValue.Replace('\', '/').TrimStart('/')
    if ($normalised -match '(^|/)\.\.(/|$)' -or [System.IO.Path]::IsPathRooted($normalised)) {
        throw "Unsafe manifest path: $PathValue"
    }
    return $normalised
}

function Get-RemoteUri {
    param([string]$HostName, [string]$Root, [string]$RelativePath)
    $root = '/' + $Root.Trim('/')
    $segments = @($RelativePath.Split('/') | ForEach-Object { [Uri]::EscapeDataString($_) })
    return "ftp://$HostName$root/$($segments -join '/')"
}

function New-FtpRequest {
    param([string]$Uri, [string]$Method, [string]$UserName, [string]$PasswordValue)
    $request = [System.Net.FtpWebRequest]::Create($Uri)
    $request.Method = $Method
    $request.EnableSsl = $true
    $request.UseBinary = $true
    $request.KeepAlive = $false
    $request.Credentials = [System.Net.NetworkCredential]::new($UserName, $PasswordValue)
    return $request
}

function Ensure-RemoteDirectory {
    param([string]$Uri, [string]$UserName, [string]$PasswordValue)
    try {
        $request = New-FtpRequest -Uri $Uri -Method ([System.Net.WebRequestMethods+Ftp]::MakeDirectory) -UserName $UserName -PasswordValue $PasswordValue
        $response = $request.GetResponse()
        $response.Dispose()
    }
    catch [System.Net.WebException] {
        $status = ''
        if ($_.Exception.Response) { $status = $_.Exception.Response.StatusDescription }
        if ($status -notmatch '(?i)(exists|file unavailable|550)') { throw }
    }
}

$releaseDirectory = Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'Aureon-Releases'
if (-not $PackagePath) { $PackagePath = Get-LatestReleasePath -Directory $releaseDirectory -Filter 'aureon-homepl-*.zip' }
if (-not $ManifestPath) {
    $base = [System.IO.Path]::GetFileNameWithoutExtension($PackagePath)
    $ManifestPath = Join-Path (Split-Path -Parent $PackagePath) "$base-manifest.csv"
}

$resolvedWebsiteRoot = (Resolve-Path -LiteralPath $WebsiteRoot).Path
$resolvedPackagePath = (Resolve-Path -LiteralPath $PackagePath).Path
$resolvedManifestPath = (Resolve-Path -LiteralPath $ManifestPath).Path
$manifest = @(Import-Csv -LiteralPath $resolvedManifestPath)
if ($manifest.Count -eq 0) { throw 'The release manifest has no files.' }

$files = foreach ($item in $manifest) {
    $relativePath = Get-SafeRelativePath -PathValue $item.Path
    $localPath = Join-Path $resolvedWebsiteRoot $relativePath.Replace('/', [System.IO.Path]::DirectorySeparatorChar)
    if (-not (Test-Path -LiteralPath $localPath -PathType Leaf)) { throw "Manifest file is missing locally: $relativePath" }
    $actualHash = (Get-FileHash -LiteralPath $localPath -Algorithm SHA256).Hash
    if ($actualHash -ne $item.Sha256) { throw "Manifest hash mismatch: $relativePath" }
    [pscustomobject]@{ RelativePath = $relativePath; LocalPath = $localPath; Bytes = [int64]$item.Bytes }
}

$packageHash = (Get-FileHash -LiteralPath $resolvedPackagePath -Algorithm SHA256).Hash
$verification = [pscustomobject]@{
    State = 'verified-local-release'
    Package = $resolvedPackagePath
    PackageSha256 = $packageHash
    Manifest = $resolvedManifestPath
    FileCount = $files.Count
    RemoteRoot = $RemoteRoot
}

if ($VerifyOnly -or -not $Deploy) {
    $verification
    Write-Host 'No upload was attempted. Use -Deploy only after a current Home.pl backup is confirmed and the temporary FTPS account is approved.'
    return
}

if ([string]::IsNullOrWhiteSpace($FtpHost) -or [string]::IsNullOrWhiteSpace($FtpUser)) {
    throw 'HOMEPL_FTPS_HOST and HOMEPL_FTPS_USER must be supplied at runtime for a deployment.'
}
$passwordValue = if ($ReadPasswordFromStandardInput) {
    [Console]::In.ReadLine()
}
else {
    [Environment]::GetEnvironmentVariable('HOMEPL_FTPS_PASSWORD')
}
if ([string]::IsNullOrWhiteSpace($passwordValue)) {
    throw 'Supply HOMEPL_FTPS_PASSWORD only in the current process environment, or use -ReadPasswordFromStandardInput for a deployment.'
}

[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
if (-not [string]::IsNullOrWhiteSpace($ExpectedCertificateThumbprint)) {
    $script:expectedCertificateThumbprint = ($ExpectedCertificateThumbprint -replace '[^0-9A-Fa-f]', '').ToUpperInvariant()
    [Net.ServicePointManager]::ServerCertificateValidationCallback = {
        param($Sender, $Certificate, $Chain, $SslPolicyErrors)
        if ($SslPolicyErrors -eq [Net.Security.SslPolicyErrors]::None) {
            return $true
        }
        if ($SslPolicyErrors -ne [Net.Security.SslPolicyErrors]::RemoteCertificateNameMismatch) {
            return $false
        }
        $certificate2 = [System.Security.Cryptography.X509Certificates.X509Certificate2]::new($Certificate)
        $observedThumbprint = ($certificate2.Thumbprint -replace '[^0-9A-Fa-f]', '').ToUpperInvariant()
        $now = [datetime]::UtcNow
        return (
            $observedThumbprint -eq $script:expectedCertificateThumbprint -and
            $now -ge $certificate2.NotBefore.ToUniversalTime() -and
            $now -le $certificate2.NotAfter.ToUniversalTime()
        )
    }
}
$directories = @($files | ForEach-Object { Split-Path $_.RelativePath -Parent } | Where-Object { $_ } | Sort-Object -Unique)
foreach ($directory in $directories) {
    Ensure-RemoteDirectory -Uri (Get-RemoteUri -HostName $FtpHost -Root $RemoteRoot -RelativePath $directory) -UserName $FtpUser -PasswordValue $passwordValue
}

$uploaded = 0
foreach ($file in ($files | Sort-Object @{ Expression = { $_.RelativePath -eq 'index.html' } }, RelativePath)) {
    $uri = Get-RemoteUri -HostName $FtpHost -Root $RemoteRoot -RelativePath $file.RelativePath
    $request = New-FtpRequest -Uri $uri -Method ([System.Net.WebRequestMethods+Ftp]::UploadFile) -UserName $FtpUser -PasswordValue $passwordValue
    $request.ContentLength = $file.Bytes
    $input = [System.IO.File]::OpenRead($file.LocalPath)
    $output = $request.GetRequestStream()
    try { $input.CopyTo($output) }
    finally {
        $output.Dispose()
        $input.Dispose()
    }
    $response = $request.GetResponse()
    $response.Dispose()
    $uploaded += 1
}

[pscustomobject]@{
    State = 'uploaded-via-explicit-ftps-deploy'
    UploadedFiles = $uploaded
    PackageSha256 = $packageHash
    RemoteRoot = $RemoteRoot
}
