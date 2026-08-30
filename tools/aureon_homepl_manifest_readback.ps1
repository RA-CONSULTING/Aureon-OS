[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$ManifestPath,

    [Parameter(Mandatory = $true)]
    [string]$SourceRoot,

    [Parameter(Mandatory = $true)]
    [string]$PackagePath,

    [Parameter(Mandatory = $true)]
    [string]$OutputPath,

    [string]$BaseUrl = 'https://aureonzorzatechnologies.pl/',

    [switch]$SkipSiteContract
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Net.Http
Add-Type -AssemblyName System.IO.Compression.FileSystem

function Get-Sha256Hex {
    param([byte[]]$Bytes)

    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        return ([System.BitConverter]::ToString($sha.ComputeHash($Bytes))).Replace('-', '')
    }
    finally {
        $sha.Dispose()
    }
}

function Get-PackageEntryProof {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ArchivePath,

        [Parameter(Mandatory = $true)]
        [string]$RelativePath
    )

    $archive = [System.IO.Compression.ZipFile]::OpenRead($ArchivePath)
    try {
        $matchingEntries = @(
            $archive.Entries |
                Where-Object {
                    -not [string]::IsNullOrEmpty($_.Name) -and
                    $_.FullName.Replace('\', '/').Equals(
                        $RelativePath,
                        [System.StringComparison]::OrdinalIgnoreCase
                    )
                }
        )
        if ($matchingEntries.Count -ne 1) {
            throw "Package must contain exactly one root $RelativePath entry; observed $($matchingEntries.Count)."
        }
        $entry = $matchingEntries[0]
        $entryPath = $entry.FullName.Replace('\', '/')
        if (-not $entryPath.Equals($RelativePath, [System.StringComparison]::Ordinal)) {
            throw "Package protected path is not case-exact: $entryPath"
        }

        $stream = $entry.Open()
        $sha = [System.Security.Cryptography.SHA256]::Create()
        try {
            $entryHash = ([System.BitConverter]::ToString($sha.ComputeHash($stream))).Replace('-', '')
        }
        finally {
            $sha.Dispose()
            $stream.Dispose()
        }
        return [pscustomobject]@{
            Path = $entryPath
            Bytes = [int64]$entry.Length
            Sha256 = $entryHash
        }
    }
    finally {
        $archive.Dispose()
    }
}

function Invoke-ReadbackRequest {
    param(
        [Parameter(Mandatory = $true)]
        [System.Net.Http.HttpClient]$Client,

        [Parameter(Mandatory = $true)]
        [Uri]$Uri
    )

    $response = $Client.GetAsync($Uri).GetAwaiter().GetResult()
    try {
        $body = $response.Content.ReadAsByteArrayAsync().GetAwaiter().GetResult()
        $headers = [ordered]@{}
        foreach ($header in $response.Headers) {
            $headers[$header.Key.ToLowerInvariant()] = [string]::Join(', ', @($header.Value))
        }
        foreach ($header in $response.Content.Headers) {
            $headers[$header.Key.ToLowerInvariant()] = [string]::Join(', ', @($header.Value))
        }

        return [pscustomobject]@{
            status = [int]$response.StatusCode
            body = [byte[]]$body
            bytes = [int64]$body.Length
            sha256 = Get-Sha256Hex -Bytes $body
            location = if ($null -eq $response.Headers.Location) {
                $null
            }
            else {
                $response.Headers.Location.OriginalString
            }
            headers = $headers
        }
    }
    finally {
        $response.Dispose()
    }
}

$manifest = @(Import-Csv -LiteralPath $ManifestPath)
if ($manifest.Count -eq 0) {
    throw 'Release manifest is empty.'
}
$manifestByPath = [System.Collections.Generic.Dictionary[string, object]]::new(
    [System.StringComparer]::Ordinal
)
foreach ($entry in $manifest) {
    $entryPath = ([string]$entry.Path).Replace('\', '/')
    if ([string]::IsNullOrWhiteSpace($entryPath)) {
        throw 'Release manifest contains an empty path.'
    }
    if ($manifestByPath.ContainsKey($entryPath)) {
        throw "Release manifest contains a duplicate path: $entryPath"
    }
    $manifestByPath.Add($entryPath, $entry)
}
$packageItem = Get-Item -LiteralPath $PackagePath
$packageHash = (Get-FileHash -LiteralPath $PackagePath -Algorithm SHA256).Hash
$manifestItem = Get-Item -LiteralPath $ManifestPath
$manifestHash = (Get-FileHash -LiteralPath $ManifestPath -Algorithm SHA256).Hash
$protectedPath = '.htaccess'
$protectedManifestEntries = @(
    $manifest |
        Where-Object {
            ([string]$_.Path).Replace('\', '/').Equals(
                $protectedPath,
                [System.StringComparison]::OrdinalIgnoreCase
            )
        }
)
if ($protectedManifestEntries.Count -ne 1) {
    throw "Manifest must contain exactly one root $protectedPath entry; observed $($protectedManifestEntries.Count)."
}
$protectedManifestEntry = $protectedManifestEntries[0]
$protectedManifestPath = ([string]$protectedManifestEntry.Path).Replace('\', '/')
if (-not $protectedManifestPath.Equals($protectedPath, [System.StringComparison]::Ordinal)) {
    throw "Manifest protected path is not case-exact: $protectedManifestPath"
}
$protectedManifestHash = ([string]$protectedManifestEntry.Sha256).ToUpperInvariant()
if ($protectedManifestHash -notmatch '^[A-F0-9]{64}$') {
    throw "Manifest has an invalid SHA-256 for $protectedPath."
}
$protectedManifestBytes = 0L
if (-not [int64]::TryParse(
    ([string]$protectedManifestEntry.Bytes),
    [Globalization.NumberStyles]::None,
    [Globalization.CultureInfo]::InvariantCulture,
    [ref]$protectedManifestBytes
) -or $protectedManifestBytes -lt 0) {
    throw "Manifest has an invalid byte count for $protectedPath."
}
$protectedSourcePath = Join-Path -Path $SourceRoot -ChildPath $protectedPath
$protectedSourceItem = Get-Item -LiteralPath $protectedSourcePath
$protectedSourceHash = (Get-FileHash -LiteralPath $protectedSourcePath -Algorithm SHA256).Hash
if (
    [int64]$protectedSourceItem.Length -ne $protectedManifestBytes -or
    $protectedSourceHash -ne $protectedManifestHash
) {
    throw "$protectedPath source bytes do not match its manifest hash."
}
$protectedPackageProof = Get-PackageEntryProof -ArchivePath $packageItem.FullName -RelativePath $protectedPath
if (
    [int64]$protectedPackageProof.Bytes -ne $protectedManifestBytes -or
    ([string]$protectedPackageProof.Sha256).ToUpperInvariant() -ne $protectedManifestHash
) {
    throw "$protectedPath package bytes do not match its manifest hash."
}
$protectedProof = [ordered]@{
    path = $protectedPath
    source_bytes = [int64]$protectedSourceItem.Length
    source_sha256 = $protectedSourceHash
    manifest_bytes = $protectedManifestBytes
    manifest_sha256 = $protectedManifestHash
    package_entry_bytes = [int64]$protectedPackageProof.Bytes
    package_entry_sha256 = ([string]$protectedPackageProof.Sha256).ToUpperInvariant()
    package_manifest_exact = $true
    expected_public_status = @(403, 404)
}
$cacheToken = [DateTimeOffset]::Now.ToString('yyyyMMddHHmmssfff')

$handler = New-Object System.Net.Http.HttpClientHandler
$handler.AutomaticDecompression = [System.Net.DecompressionMethods]::GZip -bor [System.Net.DecompressionMethods]::Deflate
$handler.AllowAutoRedirect = $false
$client = New-Object System.Net.Http.HttpClient($handler)
$client.Timeout = [TimeSpan]::FromSeconds(30)
$client.DefaultRequestHeaders.UserAgent.ParseAdd('Aureon-Homepl-Manifest-Readback/1.0')
$client.DefaultRequestHeaders.CacheControl = New-Object System.Net.Http.Headers.CacheControlHeaderValue
$client.DefaultRequestHeaders.CacheControl.NoCache = $true
$client.DefaultRequestHeaders.CacheControl.NoStore = $true

$results = New-Object System.Collections.Generic.List[object]
$failures = New-Object System.Collections.Generic.List[object]
$siteContractResults = New-Object System.Collections.Generic.List[object]
$siteContractFailures = New-Object System.Collections.Generic.List[object]

try {
    foreach ($entry in $manifest) {
        $relativePath = ([string]$entry.Path).Replace('\', '/')
        $expectedBytes = 0L
        if (-not [int64]::TryParse(
            ([string]$entry.Bytes),
            [Globalization.NumberStyles]::None,
            [Globalization.CultureInfo]::InvariantCulture,
            [ref]$expectedBytes
        ) -or $expectedBytes -lt 0) {
            throw "Manifest has an invalid byte count for $relativePath."
        }
        $expectedHash = ([string]$entry.Sha256).ToUpperInvariant()
        if ($expectedHash -notmatch '^[A-F0-9]{64}$') {
            throw "Manifest has an invalid SHA-256 for $relativePath."
        }
        $uri = [Uri]::new([Uri]$BaseUrl, $relativePath + '?audit=' + $cacheToken)
        $status = 0
        $remoteBytes = $null
        $observedHash = $null
        $mode = 'failure'
        $reason = $null

        try {
            $response = $client.GetAsync($uri).GetAwaiter().GetResult()
            try {
                $status = [int]$response.StatusCode
                $remoteBytes = $response.Content.ReadAsByteArrayAsync().GetAwaiter().GetResult()
                $observedHash = Get-Sha256Hex -Bytes $remoteBytes
            }
            finally {
                $response.Dispose()
            }

            if ($relativePath.Equals($protectedPath, [System.StringComparison]::Ordinal)) {
                if ($status -in @(403, 404)) {
                    $mode = 'package_exact_http_denied'
                }
                else {
                    $reason = "expected HTTP 403 or 404 non-public response; observed HTTP $status"
                }
            }
            elseif ($status -ne 200) {
                $reason = "HTTP $status"
            }
            elseif ($remoteBytes.Length -ne $expectedBytes) {
                $reason = 'HTTP content byte count mismatch'
            }
            elseif ($observedHash -eq $expectedHash) {
                $mode = 'exact'
            }
            else {
                $reason = 'HTTP content SHA-256 mismatch'
            }
        }
        catch {
            $reason = $_.Exception.Message
        }

        $record = [pscustomobject]@{
            path = $relativePath
            status = $status
            mode = $mode
            expected_bytes = $expectedBytes
            observed_bytes = if ($null -eq $remoteBytes) { 0 } else { $remoteBytes.Length }
            expected_sha256 = $expectedHash
            observed_sha256 = $observedHash
        }
        $results.Add($record)

        if ($mode -eq 'failure') {
            $failures.Add([pscustomobject]@{
                path = $relativePath
                status = $status
                reason = $reason
            })
        }
    }

    if (-not $SkipSiteContract) {
        $routeMatrix = @(
            [pscustomobject]@{ path = '/'; manifest_path = 'index.html' }
            [pscustomobject]@{ path = '/about/'; manifest_path = 'about/index.html' }
            [pscustomobject]@{ path = '/community/'; manifest_path = 'community/index.html' }
            [pscustomobject]@{ path = '/contact/'; manifest_path = 'contact/index.html' }
            [pscustomobject]@{ path = '/diligence/'; manifest_path = 'diligence/index.html' }
            [pscustomobject]@{ path = '/downloads/'; manifest_path = 'downloads/index.html' }
            [pscustomobject]@{
                path = '/downloads/validation-metrics-ledger/'
                manifest_path = 'downloads/validation-metrics-ledger/index.html'
            }
            [pscustomobject]@{ path = '/funding/'; manifest_path = 'funding/index.html' }
            [pscustomobject]@{
                path = '/funding/investor-deck/'
                manifest_path = 'funding/investor-deck/index.html'
            }
            [pscustomobject]@{ path = '/live/'; manifest_path = 'live/index.html' }
            [pscustomobject]@{ path = '/projects/'; manifest_path = 'projects/index.html' }
            [pscustomobject]@{
                path = '/projects/aureon-trading-system/'
                manifest_path = 'projects/aureon-trading-system/index.html'
            }
            [pscustomobject]@{
                path = '/publications/'
                manifest_path = 'publications/index.html'
            }
            [pscustomobject]@{ path = '/research/'; manifest_path = 'research/index.html' }
            [pscustomobject]@{
                path = '/research/journal/'
                manifest_path = 'research/journal/index.html'
            }
            [pscustomobject]@{ path = '/updates/'; manifest_path = 'updates/index.html' }
            [pscustomobject]@{ path = '/vision/'; manifest_path = 'vision/index.html' }
        )
        $rootProbe = $null
        foreach ($route in $routeMatrix) {
            $manifestRoutePath = [string]$route.manifest_path
            if (-not $manifestByPath.ContainsKey($manifestRoutePath)) {
                throw "Site contract route is missing from the manifest: $manifestRoutePath"
            }
            $manifestRouteEntry = $manifestByPath[$manifestRoutePath]
            $routeExpectedBytes = 0L
            if (-not [int64]::TryParse(
                ([string]$manifestRouteEntry.Bytes),
                [Globalization.NumberStyles]::None,
                [Globalization.CultureInfo]::InvariantCulture,
                [ref]$routeExpectedBytes
            ) -or $routeExpectedBytes -lt 0) {
                throw "Manifest has an invalid byte count for $manifestRoutePath."
            }
            $routeExpectedHash = ([string]$manifestRouteEntry.Sha256).ToUpperInvariant()
            $routeRequestPath = if ([string]$route.path -eq '/') {
                '?audit=' + $cacheToken
            }
            else {
                ([string]$route.path).TrimStart('/') + '?audit=' + $cacheToken
            }
            $routeUri = [Uri]::new([Uri]$BaseUrl, $routeRequestPath)
            $routeStatus = 0
            $routeObservedBytes = 0L
            $routeObservedHash = $null
            $routeMode = 'failure'
            $routeReason = $null
            try {
                $routeProbe = Invoke-ReadbackRequest -Client $client -Uri $routeUri
                if ([string]$route.path -eq '/') {
                    $rootProbe = $routeProbe
                }
                $routeStatus = $routeProbe.status
                $routeObservedBytes = $routeProbe.bytes
                $routeObservedHash = $routeProbe.sha256
                if ($routeStatus -ne 200) {
                    $routeReason = "HTTP $routeStatus"
                }
                elseif ($routeObservedBytes -ne $routeExpectedBytes) {
                    $routeReason = 'friendly-route byte count mismatch'
                }
                elseif ($routeObservedHash -ne $routeExpectedHash) {
                    $routeReason = 'friendly-route SHA-256 mismatch'
                }
                else {
                    $routeMode = 'friendly_route_exact'
                }
            }
            catch {
                $routeReason = $_.Exception.Message
            }

            $siteContractResults.Add([pscustomobject]@{
                kind = 'friendly-route'
                path = [string]$route.path
                manifest_path = $manifestRoutePath
                status = $routeStatus
                mode = $routeMode
                expected_bytes = $routeExpectedBytes
                observed_bytes = $routeObservedBytes
                expected_sha256 = $routeExpectedHash
                observed_sha256 = $routeObservedHash
            })
            if ($routeMode -eq 'failure') {
                $siteContractFailures.Add([pscustomobject]@{
                    kind = 'friendly-route'
                    path = [string]$route.path
                    status = $routeStatus
                    reason = $routeReason
                })
            }
        }

        $notFoundManifestPath = '404.html'
        if (-not $manifestByPath.ContainsKey($notFoundManifestPath)) {
            throw 'Site contract requires 404.html in the release manifest.'
        }
        $notFoundManifestEntry = $manifestByPath[$notFoundManifestPath]
        $notFoundExpectedBytes = 0L
        if (-not [int64]::TryParse(
            ([string]$notFoundManifestEntry.Bytes),
            [Globalization.NumberStyles]::None,
            [Globalization.CultureInfo]::InvariantCulture,
            [ref]$notFoundExpectedBytes
        ) -or $notFoundExpectedBytes -lt 0) {
            throw 'Manifest has an invalid byte count for 404.html.'
        }
        $notFoundExpectedHash = ([string]$notFoundManifestEntry.Sha256).ToUpperInvariant()
        $notFoundPath = '/__aureon-release-probe__/missing-' +
            $packageHash.Substring(0, 16).ToLowerInvariant() + '.html'
        $notFoundUri = [Uri]::new(
            [Uri]$BaseUrl,
            $notFoundPath.TrimStart('/') + '?audit=' + $cacheToken
        )
        $notFoundStatus = 0
        $notFoundObservedBytes = 0L
        $notFoundObservedHash = $null
        $notFoundMode = 'failure'
        $notFoundReason = $null
        try {
            $notFoundProbe = Invoke-ReadbackRequest -Client $client -Uri $notFoundUri
            $notFoundStatus = $notFoundProbe.status
            $notFoundObservedBytes = $notFoundProbe.bytes
            $notFoundObservedHash = $notFoundProbe.sha256
            if ($notFoundStatus -ne 404) {
                $notFoundReason = "expected HTTP 404; observed HTTP $notFoundStatus"
            }
            elseif ($notFoundObservedBytes -ne $notFoundExpectedBytes) {
                $notFoundReason = 'custom 404 byte count mismatch'
            }
            elseif ($notFoundObservedHash -ne $notFoundExpectedHash) {
                $notFoundReason = 'custom 404 SHA-256 mismatch'
            }
            else {
                $notFoundMode = 'custom_404_exact'
            }
        }
        catch {
            $notFoundReason = $_.Exception.Message
        }
        $siteContractResults.Add([pscustomobject]@{
            kind = 'custom-404'
            path = $notFoundPath
            manifest_path = $notFoundManifestPath
            status = $notFoundStatus
            mode = $notFoundMode
            expected_bytes = $notFoundExpectedBytes
            observed_bytes = $notFoundObservedBytes
            expected_sha256 = $notFoundExpectedHash
            observed_sha256 = $notFoundObservedHash
        })
        if ($notFoundMode -eq 'failure') {
            $siteContractFailures.Add([pscustomobject]@{
                kind = 'custom-404'
                path = $notFoundPath
                status = $notFoundStatus
                reason = $notFoundReason
            })
        }

        $sensitivePaths = @(
            '/.htaccess'
            '/.env'
            '/.env1'
            '/.git/config'
            '/archive/'
            '/backup/'
            '/public_html/'
            '/styleguide.html'
            '/release.zip'
            '/deployment.log'
            '/tools/aureon_homepl_manifest_readback.ps1'
        )
        foreach ($sensitivePath in $sensitivePaths) {
            $sensitiveUri = [Uri]::new(
                [Uri]$BaseUrl,
                $sensitivePath.TrimStart('/') + '?audit=' + $cacheToken
            )
            $sensitiveStatus = 0
            $sensitiveObservedBytes = 0L
            $sensitiveObservedHash = $null
            $sensitiveMode = 'failure'
            $sensitiveReason = $null
            try {
                $sensitiveProbe = Invoke-ReadbackRequest -Client $client -Uri $sensitiveUri
                $sensitiveStatus = $sensitiveProbe.status
                $sensitiveObservedBytes = $sensitiveProbe.bytes
                $sensitiveObservedHash = $sensitiveProbe.sha256
                if ($sensitiveStatus -notin @(403, 404)) {
                    $sensitiveReason = (
                        "expected HTTP 403 or 404 non-public response; observed HTTP " +
                        $sensitiveStatus
                    )
                }
                elseif (
                    $sensitivePath -eq '/.htaccess' -and
                    $sensitiveObservedHash -eq $protectedManifestHash
                ) {
                    $sensitiveReason = 'denial response exposed the protected package bytes'
                }
                else {
                    $sensitiveMode = 'sensitive_path_denied'
                }
            }
            catch {
                $sensitiveReason = $_.Exception.Message
            }
            $siteContractResults.Add([pscustomobject]@{
                kind = 'sensitive-path'
                path = $sensitivePath
                status = $sensitiveStatus
                mode = $sensitiveMode
                observed_bytes = $sensitiveObservedBytes
                observed_sha256 = $sensitiveObservedHash
            })
            if ($sensitiveMode -eq 'failure') {
                $siteContractFailures.Add([pscustomobject]@{
                    kind = 'sensitive-path'
                    path = $sensitivePath
                    status = $sensitiveStatus
                    reason = $sensitiveReason
                })
            }
        }

        if ($null -eq $rootProbe) {
            throw 'Site contract could not capture the root response.'
        }
        $requiredRootHeaders = [ordered]@{
            'content-security-policy' = @(
                "default-src 'self'"
                "object-src 'none'"
                "frame-ancestors 'none'"
            )
            'strict-transport-security' = @('max-age=31536000')
            'x-content-type-options' = @('nosniff')
            'x-frame-options' = @('DENY')
            'referrer-policy' = @('strict-origin-when-cross-origin')
            'permissions-policy' = @('camera=()', 'geolocation=()', 'microphone=()')
            'cross-origin-opener-policy' = @('same-origin')
            'cross-origin-resource-policy' = @('same-origin')
            'cache-control' = @('no-cache', 'no-store', 'must-revalidate')
            'content-type' = @('text/html')
        }
        foreach ($requiredHeader in $requiredRootHeaders.GetEnumerator()) {
            $headerName = [string]$requiredHeader.Key
            $requiredTokens = @($requiredHeader.Value)
            $actualHeader = if ($rootProbe.headers.Contains($headerName)) {
                [string]$rootProbe.headers[$headerName]
            }
            else {
                ''
            }
            $missingTokens = @(
                $requiredTokens |
                    Where-Object {
                        $actualHeader.IndexOf(
                            [string]$_,
                            [System.StringComparison]::OrdinalIgnoreCase
                        ) -lt 0
                    }
            )
            $headerMode = if ($missingTokens.Count -eq 0) {
                'required_header_present'
            }
            else {
                'failure'
            }
            $siteContractResults.Add([pscustomobject]@{
                kind = 'root-header'
                path = '/'
                header = $headerName
                mode = $headerMode
                required_tokens = $requiredTokens
                actual = $actualHeader
                missing_tokens = $missingTokens
            })
            if ($headerMode -eq 'failure') {
                $siteContractFailures.Add([pscustomobject]@{
                    kind = 'root-header'
                    path = '/'
                    status = $rootProbe.status
                    reason = (
                        "header $headerName is missing required token(s): " +
                        ($missingTokens -join ', ')
                    )
                })
            }
        }

        $cacheProbeMatrix = @(
            [pscustomobject]@{
                path = '/styles.css'
                required_tokens = @('public', 'max-age=31536000', 'immutable')
            }
            [pscustomobject]@{
                path = '/data/publications.json'
                required_tokens = @('public', 'max-age=3600', 'must-revalidate')
            }
        )
        foreach ($cacheProbeDefinition in $cacheProbeMatrix) {
            $cacheUri = [Uri]::new(
                [Uri]$BaseUrl,
                ([string]$cacheProbeDefinition.path).TrimStart('/') +
                    '?audit=' + $cacheToken
            )
            $cacheStatus = 0
            $cacheHeader = ''
            $cacheMode = 'failure'
            $cacheReason = $null
            $cacheMissingTokens = @()
            try {
                $cacheProbe = Invoke-ReadbackRequest -Client $client -Uri $cacheUri
                $cacheStatus = $cacheProbe.status
                $cacheHeader = if ($cacheProbe.headers.Contains('cache-control')) {
                    [string]$cacheProbe.headers['cache-control']
                }
                else {
                    ''
                }
                $cacheMissingTokens = @(
                    @($cacheProbeDefinition.required_tokens) |
                        Where-Object {
                            $cacheHeader.IndexOf(
                                [string]$_,
                                [System.StringComparison]::OrdinalIgnoreCase
                            ) -lt 0
                        }
                )
                if ($cacheStatus -ne 200) {
                    $cacheReason = "HTTP $cacheStatus"
                }
                elseif ($cacheMissingTokens.Count -gt 0) {
                    $cacheReason = (
                        'Cache-Control is missing required token(s): ' +
                        ($cacheMissingTokens -join ', ')
                    )
                }
                else {
                    $cacheMode = 'cache_policy_present'
                }
            }
            catch {
                $cacheReason = $_.Exception.Message
            }
            $siteContractResults.Add([pscustomobject]@{
                kind = 'cache-header'
                path = [string]$cacheProbeDefinition.path
                status = $cacheStatus
                mode = $cacheMode
                required_tokens = @($cacheProbeDefinition.required_tokens)
                actual = $cacheHeader
                missing_tokens = $cacheMissingTokens
            })
            if ($cacheMode -eq 'failure') {
                $siteContractFailures.Add([pscustomobject]@{
                    kind = 'cache-header'
                    path = [string]$cacheProbeDefinition.path
                    status = $cacheStatus
                    reason = $cacheReason
                })
            }
        }

        $baseUri = [Uri]$BaseUrl
        if (
            $baseUri.Scheme -eq 'https' -and
            $baseUri.Host.Equals(
                'aureonzorzatechnologies.pl',
                [System.StringComparison]::OrdinalIgnoreCase
            )
        ) {
            $redirectProbeDefinitions = @(
                [pscustomobject]@{
                    kind = 'http-to-https'
                    uri = (
                        'http://aureonzorzatechnologies.pl/research/' +
                        '?audit=' + $cacheToken + '&probe=http'
                    )
                    expected_location = (
                        'https://aureonzorzatechnologies.pl/research/' +
                        '?audit=' + $cacheToken + '&probe=http'
                    )
                }
                [pscustomobject]@{
                    kind = 'www-to-apex'
                    uri = (
                        'https://www.aureonzorzatechnologies.pl/research/' +
                        '?audit=' + $cacheToken + '&probe=www'
                    )
                    expected_location = (
                        'https://aureonzorzatechnologies.pl/research/' +
                        '?audit=' + $cacheToken + '&probe=www'
                    )
                }
            )
            foreach ($redirectDefinition in $redirectProbeDefinitions) {
                $redirectStatus = 0
                $redirectLocation = $null
                $redirectMode = 'failure'
                $redirectReason = $null
                try {
                    $redirectProbe = Invoke-ReadbackRequest `
                        -Client $client `
                        -Uri ([Uri][string]$redirectDefinition.uri)
                    $redirectStatus = $redirectProbe.status
                    $redirectLocation = $redirectProbe.location
                    if ($redirectStatus -ne 301) {
                        $redirectReason = "expected HTTP 301; observed HTTP $redirectStatus"
                    }
                    elseif (
                        $redirectLocation -ne [string]$redirectDefinition.expected_location
                    ) {
                        $redirectReason = (
                            'redirect Location mismatch: expected ' +
                            [string]$redirectDefinition.expected_location +
                            '; observed ' + [string]$redirectLocation
                        )
                    }
                    else {
                        $redirectMode = 'canonical_redirect_exact'
                    }
                }
                catch {
                    $redirectReason = $_.Exception.Message
                }
                $siteContractResults.Add([pscustomobject]@{
                    kind = 'canonical-redirect'
                    probe = [string]$redirectDefinition.kind
                    uri = [string]$redirectDefinition.uri
                    status = $redirectStatus
                    mode = $redirectMode
                    expected_location = [string]$redirectDefinition.expected_location
                    observed_location = $redirectLocation
                })
                if ($redirectMode -eq 'failure') {
                    $siteContractFailures.Add([pscustomobject]@{
                        kind = 'canonical-redirect'
                        path = [string]$redirectDefinition.kind
                        status = $redirectStatus
                        reason = $redirectReason
                    })
                }
            }
        }
    }
}
finally {
    $client.Dispose()
    $handler.Dispose()
}

$exact = @($results | Where-Object mode -eq 'exact').Count
$protectedNonPublic = @($results | Where-Object mode -eq 'package_exact_http_denied').Count
$successful = $exact + $protectedNonPublic
$manifestFailureArray = @($failures | ForEach-Object { $_ })
$siteContractFailureArray = @($siteContractFailures | ForEach-Object { $_ })
$failureArray = @($manifestFailureArray + $siteContractFailureArray)
$resultArray = @($results | ForEach-Object { $_ })
$siteContractResultArray = @($siteContractResults | ForEach-Object { $_ })
$totalFailures = $failureArray.Count
$report = [ordered]@{
    summary = [ordered]@{
        generated_at = [DateTimeOffset]::Now.ToString('o')
        base_url = $BaseUrl
        package = $packageItem.FullName
        package_bytes = $packageItem.Length
        package_sha256 = $packageHash
        manifest = $manifestItem.FullName
        manifest_sha256 = $manifestHash
        manifest_entries = $manifest.Count
        successful = $successful
        exact = $exact
        protected_non_public = $protectedNonPublic
        manifest_failures = $failures.Count
        site_contract_enabled = -not [bool]$SkipSiteContract
        site_contract_checks = $siteContractResults.Count
        site_contract_failures = $siteContractFailures.Count
        failures = $totalFailures
    }
    protected_file_proof = $protectedProof
    failures = $failureArray
    results = $resultArray
    site_contract = [ordered]@{
        enabled = -not [bool]$SkipSiteContract
        checks = $siteContractResults.Count
        failures = $siteContractFailureArray
        results = $siteContractResultArray
    }
}

$outputDirectory = Split-Path -Parent $OutputPath
if (-not (Test-Path -LiteralPath $outputDirectory)) {
    New-Item -ItemType Directory -Path $outputDirectory -Force | Out-Null
}

$report | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $OutputPath -Encoding UTF8
$report.summary | ConvertTo-Json -Depth 3

if ($totalFailures -gt 0) {
    exit 1
}
