[CmdletBinding()]
param(
    [string]$WebsiteRoot,
    [string]$OutputDirectory = (Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'Aureon-Releases'),
    [ValidatePattern('^V[0-9]+$')]
    [string]$Release = 'V28',
    [switch]$VerifyOnly
)

$ErrorActionPreference = 'Stop'

if ([string]::IsNullOrWhiteSpace($WebsiteRoot)) {
    $WebsiteRoot = Join-Path $PSScriptRoot '..\website'
}

$releaseFiles = @(
    'index.html',
    'about/index.html',
    'community/index.html',
    'contact/index.html',
    'diligence/index.html',
    'downloads/index.html',
    'downloads/validation-metrics-ledger/index.html',
    'funding/index.html',
    'funding/funding-status.js',
    'funding/investor-deck/index.html',
    'live/index.html',
    'live/live.js',
    'projects/index.html',
    'publications/index.html',
    'research/index.html',
    'research/journal/index.html',
    'updates/index.html',
    'vision/index.html',
    'robots.txt',
    'sitemap.xml',
    'script.js',
    'styles.css',
    'tokens.css',
    'assets/css/aureon-zorza-backgrounds.css',
    'data/blades.json',
    'data/funding-status.json'
)

$supplementalEntryFiles = @(
    '.htaccess',
    '404.html',
    'accessibility.html',
    'privacy.html',
    'site.webmanifest'
)

$forbiddenReleasePaths = @(
    'HOMEPL_PACKAGE_MANIFEST.txt',
    'HOMEPL_UPLOAD_README.md',
    'OWNER_CONTROL.md',
    'CHANGES.md',
    'styleguide.html',
    'backup-homepl-ftps.ps1',
    'build-homepl-package.ps1',
    'publish-homepl-ftps.ps1',
    'refresh-operator-evidence.ps1'
)

$forbiddenReleaseDirectoryNames = @(
    'archive',
    'deployment',
    'internal',
    'source'
)

$forbiddenReleaseFileNames = @(
    'styleguide.html'
)

$siteOrigin = [System.Uri]'https://aureonzorzatechnologies.pl/'
$siteRootPrefixes = @(
    'about/',
    'assets/',
    'community/',
    'contact/',
    'data/',
    'diligence/',
    'downloads/',
    'funding/',
    'live/',
    'projects/',
    'publications/',
    'research/',
    'updates/',
    'vision/'
)

$resolvedWebsiteRoot = (Resolve-Path -LiteralPath $WebsiteRoot).Path
$resolvedOutputDirectory = [System.IO.Path]::GetFullPath($OutputDirectory)
$releaseSlug = $Release.ToLowerInvariant()

$websiteBoundary = $resolvedWebsiteRoot.TrimEnd(
    [System.IO.Path]::DirectorySeparatorChar,
    [System.IO.Path]::AltDirectorySeparatorChar
) + [System.IO.Path]::DirectorySeparatorChar

$releaseEntryFiles = @($releaseFiles + $supplementalEntryFiles)
if ($releaseEntryFiles.Count -ne (@($releaseEntryFiles | Sort-Object -Unique)).Count) {
    throw 'Release entry file list contains duplicate paths.'
}

$includedPaths = New-Object 'System.Collections.Generic.HashSet[string]' ([System.StringComparer]::OrdinalIgnoreCase)
$pendingPaths = New-Object 'System.Collections.Generic.Queue[string]'
$referenceKeys = New-Object 'System.Collections.Generic.HashSet[string]' ([System.StringComparer]::Ordinal)
$referenceRecords = New-Object 'System.Collections.Generic.List[object]'
$scannedHashes = @{}
$fragmentIdCache = @{}

function Test-ExactPathCase {
    param([Parameter(Mandatory = $true)][string]$AbsolutePath)

    if (-not (Test-Path -LiteralPath $AbsolutePath)) {
        return $false
    }
    if ($AbsolutePath.Equals($resolvedWebsiteRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
        return $true
    }
    if (-not $AbsolutePath.StartsWith($websiteBoundary, [System.StringComparison]::OrdinalIgnoreCase)) {
        return $false
    }

    $current = $resolvedWebsiteRoot
    $relative = $AbsolutePath.Substring($websiteBoundary.Length)
    foreach ($segment in @($relative -split '[\\/]')) {
        $exact = Get-ChildItem -LiteralPath $current -Force |
            Where-Object { $_.Name -ceq $segment } |
            Select-Object -First 1
        if ($null -eq $exact) {
            return $false
        }
        $current = $exact.FullName
    }
    return $true
}

function Test-PathContainsReparsePoint {
    param([Parameter(Mandatory = $true)][string]$AbsolutePath)

    $current = $resolvedWebsiteRoot
    if ((Get-Item -LiteralPath $current -Force).Attributes -band [System.IO.FileAttributes]::ReparsePoint) {
        return $true
    }

    $relative = $AbsolutePath.Substring($websiteBoundary.Length)
    foreach ($segment in @($relative -split '[\\/]')) {
        $current = Join-Path $current $segment
        if ((Get-Item -LiteralPath $current -Force).Attributes -band [System.IO.FileAttributes]::ReparsePoint) {
            return $true
        }
    }
    return $false
}

function ConvertTo-SafeReleasePath {
    param(
        [Parameter(Mandatory = $true)][string]$RelativePath,
        [Parameter(Mandatory = $true)][string]$Context
    )

    $normalisedRelativePath = $RelativePath.Replace('\', '/').TrimStart('/')
    if (
        [string]::IsNullOrWhiteSpace($normalisedRelativePath) -or
        [System.IO.Path]::IsPathRooted($normalisedRelativePath) -or
        $normalisedRelativePath -match '(^|/)\.\.(/|$)' -or
        $normalisedRelativePath -match '(^|/)\.(/|$)'
    ) {
        throw "Unsafe release path ($Context): $RelativePath"
    }

    $localPath = [System.IO.Path]::GetFullPath(
        (Join-Path $resolvedWebsiteRoot $normalisedRelativePath.Replace('/', [System.IO.Path]::DirectorySeparatorChar))
    )
    if (-not $localPath.StartsWith($websiteBoundary, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Release path escapes the website root ($Context): $RelativePath"
    }
    if (-not (Test-Path -LiteralPath $localPath -PathType Leaf)) {
        throw "Release file is missing ($Context): $normalisedRelativePath"
    }
    if (-not (Test-ExactPathCase -AbsolutePath $localPath)) {
        throw "Release path case differs from disk ($Context): $normalisedRelativePath"
    }
    if (Test-PathContainsReparsePoint -AbsolutePath $localPath) {
        throw "Release dependency traverses a reparse point ($Context): $normalisedRelativePath"
    }

    $blockedExtensions = @(
        '.bak',
        '.bat',
        '.cmd',
        '.env',
        '.ini',
        '.key',
        '.log',
        '.md',
        '.pem',
        '.pfx',
        '.ps1',
        '.psd1',
        '.psm1',
        '.sh',
        '.sql',
        '.zip'
    )
    $extension = [System.IO.Path]::GetExtension($normalisedRelativePath).ToLowerInvariant()
    if ($blockedExtensions -contains $extension -or [System.IO.Path]::GetFileName($normalisedRelativePath) -match '^\.env(?:\.|$)') {
        throw "Blocked public release dependency ($Context): $normalisedRelativePath"
    }

    return $normalisedRelativePath
}

function Test-ForbiddenReleasePath {
    param([Parameter(Mandatory = $true)][string]$RelativePath)

    if (
        $forbiddenReleasePaths -contains $RelativePath -or
        $forbiddenReleaseFileNames -contains [System.IO.Path]::GetFileName($RelativePath)
    ) {
        return $true
    }
    foreach ($segment in @($RelativePath -split '/')) {
        if ($forbiddenReleaseDirectoryNames -contains $segment) {
            return $true
        }
    }
    return $false
}

function Add-ReferenceRecord {
    param(
        [Parameter(Mandatory = $true)][string]$Source,
        [Parameter(Mandatory = $true)][string]$Reference,
        [Parameter(Mandatory = $true)][ValidateSet('local-included', 'remote', 'non-file')][string]$Disposition,
        [string]$Target = '',
        [string]$Fragment = '',
        [ValidateSet('', 'not-applicable', 'verified')][string]$FragmentState = ''
    )

    $separator = [char]31
    $key = "$Source$separator$Reference$separator$Disposition$separator$Target$separator$Fragment$separator$FragmentState"
    if ($referenceKeys.Add($key)) {
        $referenceRecords.Add([pscustomobject][ordered]@{
            Source = $Source
            Reference = $Reference
            Disposition = $Disposition
            Target = $Target
            Fragment = $Fragment
            FragmentState = $FragmentState
        })
    }
}

function Add-IncludedFile {
    param(
        [Parameter(Mandatory = $true)][string]$RelativePath,
        [Parameter(Mandatory = $true)][string]$Context
    )

    $safePath = ConvertTo-SafeReleasePath -RelativePath $RelativePath -Context $Context
    if (Test-ForbiddenReleasePath -RelativePath $safePath) {
        throw "Source-control or deployment-only file cannot enter the public release ($Context): $safePath"
    }
    if ($includedPaths.Add($safePath)) {
        $pendingPaths.Enqueue($safePath)
    }
    return $safePath
}

function Test-SiteRootReference {
    param([Parameter(Mandatory = $true)][AllowEmptyString()][string]$Reference)

    if ($Reference -eq '/') {
        return $true
    }
    foreach ($prefix in $siteRootPrefixes) {
        if ($Reference.StartsWith($prefix, [System.StringComparison]::OrdinalIgnoreCase)) {
            return $true
        }
    }
    return $false
}

function Assert-ReferenceFragment {
    param(
        [Parameter(Mandatory = $true)][string]$Source,
        [Parameter(Mandatory = $true)][string]$Reference,
        [Parameter(Mandatory = $true)][string]$TargetPath,
        [AllowEmptyString()][string]$Fragment
    )

    if ([string]::IsNullOrWhiteSpace($Fragment)) {
        return 'not-applicable'
    }

    try {
        $decodedFragment = [System.Uri]::UnescapeDataString($Fragment)
    }
    catch {
        throw "Invalid fragment encoding in $Source reference '$Reference': $($_.Exception.Message)"
    }

    $targetExtension = [System.IO.Path]::GetExtension($TargetPath).ToLowerInvariant()
    if ($targetExtension -notin @('.html', '.svg', '.xml')) {
        throw "Local fragment cannot be verified for this file type: $Source -> $Reference"
    }

    if (-not $fragmentIdCache.ContainsKey($TargetPath)) {
        $ids = New-Object 'System.Collections.Generic.HashSet[string]' ([System.StringComparer]::Ordinal)
        $targetText = Get-Content -LiteralPath $TargetPath -Raw
        $attributePattern = '(?is)(?<![\w:-])(?:id|name)\s*=\s*(?:"([^"]*)"|''([^'']*)''|([^\s"''=<>`]+))'
        foreach ($match in [regex]::Matches($targetText, $attributePattern)) {
            foreach ($groupNumber in 1..3) {
                if ($match.Groups[$groupNumber].Success) {
                    [void]$ids.Add([System.Net.WebUtility]::HtmlDecode($match.Groups[$groupNumber].Value))
                    break
                }
            }
        }
        $fragmentIdCache[$TargetPath] = $ids
    }

    if (-not $fragmentIdCache[$TargetPath].Contains($decodedFragment)) {
        throw "Local fragment is missing: $Source -> $Reference (target id '$decodedFragment')"
    }
    return 'verified'
}

function Resolve-ReleaseReference {
    param(
        [Parameter(Mandatory = $true)][string]$Source,
        [Parameter(Mandatory = $true)][AllowEmptyString()][string]$Reference,
        [switch]$FromSiteRoot
    )

    $value = [System.Net.WebUtility]::HtmlDecode($Reference).Trim()
    if ([string]::IsNullOrWhiteSpace($value)) {
        return
    }

    if ($value -match '^(?:mailto:|tel:|javascript:|data:|blob:)' ) {
        Add-ReferenceRecord -Source $Source -Reference $Reference -Disposition 'non-file' -Target (($value -split ':', 2)[0].ToLowerInvariant())
        return
    }

    if ($value.StartsWith('//')) {
        $value = "https:$value"
    }

    $absoluteUri = $null
    if ([System.Uri]::TryCreate($value, [System.UriKind]::Absolute, [ref]$absoluteUri)) {
        if ($absoluteUri.Scheme -notin @('http', 'https')) {
            Add-ReferenceRecord -Source $Source -Reference $Reference -Disposition 'non-file' -Target $absoluteUri.Scheme
            return
        }

        $localHosts = @($siteOrigin.Host, "www.$($siteOrigin.Host)")
        if ($localHosts -notcontains $absoluteUri.Host) {
            Add-ReferenceRecord -Source $Source -Reference $Reference -Disposition 'remote' -Target $absoluteUri.AbsoluteUri
            return
        }
        $value = "$($absoluteUri.AbsolutePath)$($absoluteUri.Query)$($absoluteUri.Fragment)"
        $FromSiteRoot = $true
    }

    $fragment = ''
    $fragmentIndex = $value.IndexOf('#')
    if ($fragmentIndex -ge 0) {
        $fragment = $value.Substring($fragmentIndex + 1)
        $value = $value.Substring(0, $fragmentIndex)
    }
    $queryIndex = $value.IndexOf('?')
    if ($queryIndex -ge 0) {
        $value = $value.Substring(0, $queryIndex)
    }

    if ([string]::IsNullOrWhiteSpace($value)) {
        $targetPath = Add-IncludedFile -RelativePath $Source -Context "self-reference from $Source"
        $targetLocalPath = Join-Path $resolvedWebsiteRoot $targetPath.Replace('/', [System.IO.Path]::DirectorySeparatorChar)
        $fragmentState = Assert-ReferenceFragment -Source $Source -Reference $Reference -TargetPath $targetLocalPath -Fragment $fragment
        Add-ReferenceRecord -Source $Source -Reference $Reference -Disposition 'local-included' -Target $targetPath -Fragment $fragment -FragmentState $fragmentState
        return
    }

    try {
        $decodedPath = [System.Uri]::UnescapeDataString($value)
    }
    catch {
        throw "Invalid URL encoding in $Source reference '$Reference': $($_.Exception.Message)"
    }

    $useSiteRoot = $FromSiteRoot -or $decodedPath.StartsWith('/')
    if ($useSiteRoot) {
        $candidatePath = Join-Path $resolvedWebsiteRoot $decodedPath.TrimStart('/').Replace('/', [System.IO.Path]::DirectorySeparatorChar)
    }
    else {
        $sourcePath = Join-Path $resolvedWebsiteRoot $Source.Replace('/', [System.IO.Path]::DirectorySeparatorChar)
        $candidatePath = Join-Path (Split-Path -Parent $sourcePath) $decodedPath.Replace('/', [System.IO.Path]::DirectorySeparatorChar)
    }

    $candidatePath = [System.IO.Path]::GetFullPath($candidatePath)
    if (
        -not $candidatePath.Equals($resolvedWebsiteRoot, [System.StringComparison]::OrdinalIgnoreCase) -and
        -not $candidatePath.StartsWith($websiteBoundary, [System.StringComparison]::OrdinalIgnoreCase)
    ) {
        throw "Local reference escapes the website root: $Source -> $Reference"
    }

    if (
        $decodedPath.EndsWith('/') -or
        $candidatePath.Equals($resolvedWebsiteRoot, [System.StringComparison]::OrdinalIgnoreCase) -or
        (Test-Path -LiteralPath $candidatePath -PathType Container)
    ) {
        $candidatePath = Join-Path $candidatePath 'index.html'
    }
    elseif (
        -not (Test-Path -LiteralPath $candidatePath) -and
        [string]::IsNullOrEmpty([System.IO.Path]::GetExtension($candidatePath)) -and
        (Test-Path -LiteralPath (Join-Path $candidatePath 'index.html') -PathType Leaf)
    ) {
        $candidatePath = Join-Path $candidatePath 'index.html'
    }

    if (-not (Test-Path -LiteralPath $candidatePath -PathType Leaf)) {
        $missingPath = if ($candidatePath.StartsWith($websiteBoundary, [System.StringComparison]::OrdinalIgnoreCase)) {
            $candidatePath.Substring($websiteBoundary.Length).Replace('\', '/')
        }
        else {
            $candidatePath
        }
        throw "Local dependency is missing: $Source -> $Reference (resolved to $missingPath)"
    }
    if (-not (Test-ExactPathCase -AbsolutePath $candidatePath)) {
        throw "Local dependency path case differs from disk: $Source -> $Reference"
    }

    $targetRelativePath = $candidatePath.Substring($websiteBoundary.Length).Replace('\', '/')
    $targetPath = Add-IncludedFile -RelativePath $targetRelativePath -Context "reference from $Source"
    $fragmentState = Assert-ReferenceFragment -Source $Source -Reference $Reference -TargetPath $candidatePath -Fragment $fragment
    Add-ReferenceRecord -Source $Source -Reference $Reference -Disposition 'local-included' -Target $targetPath -Fragment $fragment -FragmentState $fragmentState
}

function Get-AttributeValue {
    param(
        [Parameter(Mandatory = $true)][string]$Tag,
        [Parameter(Mandatory = $true)][string]$Name
    )

    $attributePattern = '(?is)(?<![\w:-]){0}\s*=\s*(?:"([^"]*)"|''([^'']*)''|([^\s"''=<>`]+))' -f [regex]::Escape($Name)
    $attributeMatch = [regex]::Match($Tag, $attributePattern)
    if (-not $attributeMatch.Success) {
        return $null
    }
    foreach ($groupNumber in 1..3) {
        if ($attributeMatch.Groups[$groupNumber].Success) {
            return $attributeMatch.Groups[$groupNumber].Value
        }
    }
    return $null
}

function Add-CssReferences {
    param(
        [Parameter(Mandatory = $true)][string]$Source,
        [Parameter(Mandatory = $true)][string]$Text
    )

    foreach ($match in [regex]::Matches($Text, '(?is)url\(\s*(?:"([^"]+)"|''([^'']+)''|([^)"'']+))\s*\)')) {
        $reference = if ($match.Groups[1].Success) {
            $match.Groups[1].Value
        }
        elseif ($match.Groups[2].Success) {
            $match.Groups[2].Value
        }
        else {
            $match.Groups[3].Value.Trim()
        }
        Resolve-ReleaseReference -Source $Source -Reference $reference
    }

    foreach ($match in [regex]::Matches($Text, '(?is)@import\s+(?:url\(\s*)?(?:"([^"]+)"|''([^'']+)'')')) {
        $reference = if ($match.Groups[1].Success) { $match.Groups[1].Value } else { $match.Groups[2].Value }
        Resolve-ReleaseReference -Source $Source -Reference $reference
    }
}

foreach ($entryFile in $releaseEntryFiles) {
    Add-IncludedFile -RelativePath $entryFile -Context 'release entry point' | Out-Null
}

while ($pendingPaths.Count -gt 0) {
    $source = $pendingPaths.Dequeue()
    $sourcePath = Join-Path $resolvedWebsiteRoot $source.Replace('/', [System.IO.Path]::DirectorySeparatorChar)
    $scanHashBefore = (Get-FileHash -LiteralPath $sourcePath -Algorithm SHA256).Hash
    $extension = [System.IO.Path]::GetExtension($source).ToLowerInvariant()
    $text = if ($extension -in @('.css', '.html', '.js', '.json', '.svg', '.txt', '.webmanifest', '.xml')) {
        Get-Content -LiteralPath $sourcePath -Raw
    }
    else {
        $null
    }

    switch ($extension) {
        '.html' {
            foreach ($tagMatch in [regex]::Matches($text, '(?is)<(?:a|img|script|source|video|audio|link|iframe|form|object|embed|input|track|use|image)\b[^>]*>')) {
                $tag = $tagMatch.Value
                foreach ($attributeName in @('href', 'xlink:href', 'src', 'poster', 'action', 'data')) {
                    $reference = Get-AttributeValue -Tag $tag -Name $attributeName
                    if ($null -ne $reference) {
                        Resolve-ReleaseReference -Source $source -Reference $reference
                    }
                }

                $srcset = Get-AttributeValue -Tag $tag -Name 'srcset'
                if ($null -ne $srcset) {
                    foreach ($candidate in @($srcset -split ',')) {
                        $candidateUrl = (@($candidate.Trim() -split '\s+'))[0]
                        if (-not [string]::IsNullOrWhiteSpace($candidateUrl)) {
                            Resolve-ReleaseReference -Source $source -Reference $candidateUrl
                        }
                    }
                }
            }

            foreach ($metaMatch in [regex]::Matches($text, '(?is)<meta\b[^>]*>')) {
                $tag = $metaMatch.Value
                $metaName = Get-AttributeValue -Tag $tag -Name 'property'
                if ($null -eq $metaName) {
                    $metaName = Get-AttributeValue -Tag $tag -Name 'name'
                }
                $content = Get-AttributeValue -Tag $tag -Name 'content'
                if ($metaName -in @('og:image', 'og:image:secure_url', 'twitter:image') -and $null -ne $content) {
                    Resolve-ReleaseReference -Source $source -Reference $content
                }

                $httpEquiv = Get-AttributeValue -Tag $tag -Name 'http-equiv'
                if ($httpEquiv -ieq 'refresh' -and $content -match '(?is)\burl\s*=\s*(.+?)\s*$') {
                    Resolve-ReleaseReference -Source $source -Reference $matches[1].Trim('"', "'", ' ')
                }
            }

            Add-CssReferences -Source $source -Text $text
        }
        '.css' {
            Add-CssReferences -Source $source -Text $text
        }
        '.js' {
            foreach ($match in [regex]::Matches(
                $text,
                '(?is)(?:"|'')((?:https?:)?//[^"'']+|(?:\.\.?/|/|assets/|data/)[^"'']+)(?:"|'')'
            )) {
                $reference = $match.Groups[1].Value
                Resolve-ReleaseReference -Source $source -Reference $reference -FromSiteRoot:(Test-SiteRootReference -Reference $reference)
            }

            foreach ($match in [regex]::Matches($text, '(?is)\b(?:siteUrl|localLink|loadJson)\(\s*(?:"([^"]+)"|''([^'']+)'')')) {
                $reference = if ($match.Groups[1].Success) { $match.Groups[1].Value } else { $match.Groups[2].Value }
                Resolve-ReleaseReference -Source $source -Reference $reference -FromSiteRoot
            }

            foreach ($match in [regex]::Matches(
                $text,
                '(?is)\b(?:fetch|import|Worker|SharedWorker|serviceWorker\.register)\(\s*(?:"([^"]+)"|''([^'']+)'')'
            )) {
                $reference = if ($match.Groups[1].Success) { $match.Groups[1].Value } else { $match.Groups[2].Value }
                Resolve-ReleaseReference -Source $source -Reference $reference -FromSiteRoot:(Test-SiteRootReference -Reference $reference)
            }
        }
        { $_ -in @('.json', '.webmanifest') } {
            try {
                $text | ConvertFrom-Json | Out-Null
            }
            catch {
                throw "Invalid public JSON dependency $source`: $($_.Exception.Message)"
            }

            foreach ($match in [regex]::Matches($text, '"((?:\\.|[^"\\])*)"')) {
                $value = [regex]::Unescape($match.Groups[1].Value.Replace('\/', '/'))
                if (
                    $value -match '^(?:https?:)?//' -or
                    $value -match '^(?:mailto:|tel:)' -or
                    $value -match '^\.\.?/' -or
                    $value.StartsWith('/') -or
                    (Test-SiteRootReference -Reference $value)
                ) {
                    Resolve-ReleaseReference -Source $source -Reference $value -FromSiteRoot:(Test-SiteRootReference -Reference $value)
                }
            }
        }
        '.svg' {
            foreach ($tagMatch in [regex]::Matches($text, '(?is)<(?:a|image|link|script|use)\b[^>]*>')) {
                $tag = $tagMatch.Value
                foreach ($attributeName in @('href', 'xlink:href', 'src')) {
                    $reference = Get-AttributeValue -Tag $tag -Name $attributeName
                    if ($null -ne $reference) {
                        Resolve-ReleaseReference -Source $source -Reference $reference
                    }
                }
            }
            Add-CssReferences -Source $source -Text $text
        }
        '.xml' {
            foreach ($match in [regex]::Matches($text, '(?is)<loc>\s*([^<]+?)\s*</loc>')) {
                Resolve-ReleaseReference -Source $source -Reference $match.Groups[1].Value
            }
        }
        '.txt' {
            foreach ($match in [regex]::Matches($text, '(?im)^\s*Sitemap:\s*(\S+)\s*$')) {
                Resolve-ReleaseReference -Source $source -Reference $match.Groups[1].Value
            }
        }
    }

    $scanHashAfter = (Get-FileHash -LiteralPath $sourcePath -Algorithm SHA256).Hash
    if ($scanHashAfter -ne $scanHashBefore) {
        throw "Source changed while its dependency references were being scanned: $source"
    }
    $scannedHashes[$source] = $scanHashAfter
}

$releaseFiles = @($includedPaths | Sort-Object)

$manifest = foreach ($relativePath in $releaseFiles) {
    $normalisedRelativePath = $relativePath.Replace('\', '/')
    if (
        [System.IO.Path]::IsPathRooted($relativePath) -or
        $normalisedRelativePath -match '(^|/)\.\.(/|$)' -or
        $normalisedRelativePath -match '(^|/)\.(/|$)'
    ) {
        throw "Unsafe release path: $relativePath"
    }

    $localPath = [System.IO.Path]::GetFullPath(
        (Join-Path $resolvedWebsiteRoot $relativePath.Replace('/', [System.IO.Path]::DirectorySeparatorChar))
    )
    if (-not $localPath.StartsWith($websiteBoundary, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Release path escapes the website root: $relativePath"
    }
    if (-not (Test-Path -LiteralPath $localPath -PathType Leaf)) {
        throw "Release file is missing: $relativePath"
    }

    $file = Get-Item -LiteralPath $localPath
    $currentHash = (Get-FileHash -LiteralPath $localPath -Algorithm SHA256).Hash
    if (-not $scannedHashes.ContainsKey($normalisedRelativePath) -or $scannedHashes[$normalisedRelativePath] -ne $currentHash) {
        throw "Source changed after dependency closure was calculated: $normalisedRelativePath"
    }
    [pscustomobject]@{
        Path = $normalisedRelativePath
        Bytes = [int64]$file.Length
        Sha256 = $currentHash
        LocalPath = $localPath
    }
}

$manifest = @($manifest | Sort-Object Path)
$manifestTotalBytes = [int64](($manifest | Measure-Object -Property Bytes -Sum).Sum)
$localReferenceCount = @($referenceRecords | Where-Object { $_.Disposition -eq 'local-included' }).Count
$remoteReferenceRecords = @($referenceRecords | Where-Object { $_.Disposition -eq 'remote' })
$nonFileReferenceCount = @($referenceRecords | Where-Object { $_.Disposition -eq 'non-file' }).Count
$fragmentReferenceRecords = @(
    $referenceRecords |
        Where-Object {
            $_.Disposition -eq 'local-included' -and
            -not [string]::IsNullOrWhiteSpace($_.Fragment)
        }
)
$verifiedFragmentReferenceCount = @($fragmentReferenceRecords | Where-Object { $_.FragmentState -eq 'verified' }).Count
$remoteOrigins = @(
    $remoteReferenceRecords |
        ForEach-Object {
            $remoteUri = $null
            if ([System.Uri]::TryCreate($_.Target, [System.UriKind]::Absolute, [ref]$remoteUri)) {
                $remoteUri.GetLeftPart([System.UriPartial]::Authority)
            }
        } |
        Where-Object { -not [string]::IsNullOrWhiteSpace($_) } |
        Sort-Object -Unique
)
$closureByExtension = @(
    $manifest |
        Group-Object {
            $itemExtension = [System.IO.Path]::GetExtension($_.Path).ToLowerInvariant()
            if ([string]::IsNullOrWhiteSpace($itemExtension)) { '[no extension]' } else { $itemExtension }
        } |
        Sort-Object Name |
        ForEach-Object {
            [pscustomobject]@{
                Extension = $_.Name
                FileCount = $_.Count
            }
        }
)
$closureSummary = [ordered]@{
    state = 'verified-complete'
    entry_file_count = $releaseEntryFiles.Count
    discovered_file_count = $manifest.Count - $releaseEntryFiles.Count
    local_reference_count = $localReferenceCount
    included_local_reference_count = $localReferenceCount
    missing_local_reference_count = 0
    fragment_reference_count = $fragmentReferenceRecords.Count
    verified_fragment_reference_count = $verifiedFragmentReferenceCount
    missing_fragment_reference_count = 0
    remote_reference_count = $remoteReferenceRecords.Count
    non_file_reference_count = $nonFileReferenceCount
    remote_origins = $remoteOrigins
    files_by_extension = $closureByExtension
}

if ($VerifyOnly) {
    [pscustomobject]@{
        State = 'release-plan-verified'
        Release = $Release
        SourceRoot = $resolvedWebsiteRoot
        FileCount = $manifest.Count
        TotalBytes = $manifestTotalBytes
        PackageRoot = '/'
        RemoteRoot = 'action-time-confirmation-required'
        EntryFiles = @($releaseEntryFiles | Sort-Object)
        Closure = $closureSummary
        Files = @($manifest | Select-Object Path, Bytes, Sha256)
    } | ConvertTo-Json -Depth 6
    return
}

New-Item -ItemType Directory -Path $resolvedOutputDirectory -Force | Out-Null

$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$releaseName = "aureon-homepl-$releaseSlug-$stamp"
$stagingDirectory = Join-Path $resolvedOutputDirectory "$releaseName-staging"
$packagePath = Join-Path $resolvedOutputDirectory "$releaseName.zip"
$manifestPath = Join-Path $resolvedOutputDirectory "$releaseName-manifest.csv"
$dependencyManifestPath = Join-Path $resolvedOutputDirectory "$releaseName-dependencies.csv"
$receiptPath = Join-Path $resolvedOutputDirectory "$releaseName-receipt.json"

foreach ($target in @($stagingDirectory, $packagePath, $manifestPath, $dependencyManifestPath, $receiptPath)) {
    if (Test-Path -LiteralPath $target) {
        throw "Refusing to overwrite existing release target: $target"
    }
}

New-Item -ItemType Directory -Path $stagingDirectory | Out-Null

foreach ($entry in $manifest) {
    $stagedPath = Join-Path $stagingDirectory $entry.Path.Replace('/', [System.IO.Path]::DirectorySeparatorChar)
    $stagedParent = Split-Path -Parent $stagedPath
    if (-not (Test-Path -LiteralPath $stagedParent)) {
        New-Item -ItemType Directory -Path $stagedParent -Force | Out-Null
    }
    Copy-Item -LiteralPath $entry.LocalPath -Destination $stagedPath
}

$publicManifest = @($manifest | Select-Object Path, Bytes, Sha256)
$publicManifest | Export-Csv -LiteralPath $manifestPath -NoTypeInformation -Encoding utf8
@($referenceRecords | Sort-Object Source, Disposition, Reference, Target) |
    Export-Csv -LiteralPath $dependencyManifestPath -NoTypeInformation -Encoding utf8

$stagingVerificationJson = & $PSCommandPath -WebsiteRoot $stagingDirectory -OutputDirectory $resolvedOutputDirectory -Release $Release -VerifyOnly | Out-String
$stagingVerification = $stagingVerificationJson | ConvertFrom-Json
if ($stagingVerification.State -ne 'release-plan-verified') {
    throw "Staging dependency closure verification failed: $($stagingVerification.State)"
}
if ([int]$stagingVerification.Closure.missing_local_reference_count -ne 0) {
    throw 'Staging contains a missing local dependency.'
}
if ([int]$stagingVerification.Closure.missing_fragment_reference_count -ne 0) {
    throw 'Staging contains a missing local fragment.'
}

$stagedByPath = @{}
foreach ($entry in @($stagingVerification.Files)) {
    $stagedByPath[$entry.Path] = $entry
}
if ($stagedByPath.Count -ne $publicManifest.Count) {
    throw "Staging closure mismatch: expected $($publicManifest.Count) files, found $($stagedByPath.Count)."
}
foreach ($entry in $publicManifest) {
    if (-not $stagedByPath.ContainsKey($entry.Path)) {
        throw "Staging closure is missing manifest path: $($entry.Path)"
    }
    $stagedEntry = $stagedByPath[$entry.Path]
    if ([int64]$stagedEntry.Bytes -ne [int64]$entry.Bytes) {
        throw "Staging closure byte count mismatch for $($entry.Path)"
    }
    if ($stagedEntry.Sha256.ToUpperInvariant() -ne $entry.Sha256.ToUpperInvariant()) {
        throw "Staging closure SHA-256 mismatch for $($entry.Path)"
    }
}

Compress-Archive -Path (Join-Path $stagingDirectory '*') -DestinationPath $packagePath -CompressionLevel Optimal

$expectedByPath = @{}
foreach ($entry in $publicManifest) {
    $expectedByPath[$entry.Path] = $entry
}

Add-Type -AssemblyName System.IO.Compression.FileSystem
$archive = [System.IO.Compression.ZipFile]::OpenRead($packagePath)
try {
    $archiveFiles = @($archive.Entries | Where-Object { -not [string]::IsNullOrEmpty($_.Name) })
    if ($archiveFiles.Count -ne $publicManifest.Count) {
        throw "ZIP manifest mismatch: expected $($publicManifest.Count) files, found $($archiveFiles.Count)."
    }

    foreach ($zipEntry in $archiveFiles) {
        $entryPath = $zipEntry.FullName.Replace('\', '/')
        if (-not $expectedByPath.ContainsKey($entryPath)) {
            throw "ZIP contains an unexpected path: $entryPath"
        }
        $expected = $expectedByPath[$entryPath]
        if ([int64]$zipEntry.Length -ne [int64]$expected.Bytes) {
            throw "ZIP byte count mismatch for $entryPath"
        }

        $stream = $zipEntry.Open()
        $sha256 = [System.Security.Cryptography.SHA256]::Create()
        try {
            $entryHash = (
                $sha256.ComputeHash($stream) |
                    ForEach-Object { $_.ToString('x2') }
            ) -join ''
        }
        finally {
            $sha256.Dispose()
            $stream.Dispose()
        }
        if ($entryHash.ToUpperInvariant() -ne $expected.Sha256.ToUpperInvariant()) {
            throw "ZIP SHA-256 mismatch for $entryPath"
        }
    }
}
finally {
    $archive.Dispose()
}

$packageHash = (Get-FileHash -LiteralPath $packagePath -Algorithm SHA256).Hash
$manifestHash = (Get-FileHash -LiteralPath $manifestPath -Algorithm SHA256).Hash
$dependencyManifestHash = (Get-FileHash -LiteralPath $dependencyManifestPath -Algorithm SHA256).Hash
$receipt = [ordered]@{
    schema = 'aureon-homepl-audited-release-v3'
    release = $Release
    built_at = (Get-Date).ToUniversalTime().ToString('o')
    source_root = $resolvedWebsiteRoot
    package = $packagePath
    package_sha256 = $packageHash
    manifest = $manifestPath
    manifest_sha256 = $manifestHash
    dependency_manifest = $dependencyManifestPath
    dependency_manifest_sha256 = $dependencyManifestHash
    staging_directory = $stagingDirectory
    file_count = $publicManifest.Count
    total_bytes = $manifestTotalBytes
    package_root = '/'
    remote_root = 'action-time-confirmation-required'
    deployment_state = 'audited-release-prepared-not-uploaded'
    package_validation = [ordered]@{
        state = 'verified'
        zip_file_count = $archiveFiles.Count
        manifest_paths_exact = $true
        manifest_bytes_exact = $true
        manifest_sha256_exact = $true
        staging_dependency_closure_exact = $true
        staging_fragment_targets_exact = $true
    }
    dependency_closure = $closureSummary
    files = $publicManifest
}
$receipt | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $receiptPath -Encoding utf8

[pscustomobject]@{
    State = 'audited-release-prepared'
    Release = $Release
    Package = $packagePath
    PackageSha256 = $packageHash
    Manifest = $manifestPath
    ManifestSha256 = $manifestHash
    DependencyManifest = $dependencyManifestPath
    DependencyManifestSha256 = $dependencyManifestHash
    Receipt = $receiptPath
    StagingDirectory = $stagingDirectory
    FileCount = $publicManifest.Count
    TotalBytes = $manifestTotalBytes
    LocalReferenceCount = $localReferenceCount
    RemoteReferenceCount = $remoteReferenceRecords.Count
    MissingLocalReferenceCount = 0
    PackageValidation = 'verified'
    PackageRoot = '/'
    RemoteRoot = 'action-time-confirmation-required'
} | Format-List
