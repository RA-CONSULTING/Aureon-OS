[CmdletBinding()]
param(
    [string]$OutputDirectory = (Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'Aureon-Releases')
)

$ErrorActionPreference = 'Stop'

throw 'This legacy packager is retired because it can select non-public working surfaces. From the repository root, run: python -m scripts.website.build_package --out artifacts/website-releases'

$websiteRoot = (Resolve-Path -LiteralPath $PSScriptRoot).Path
$releaseDirectory = [System.IO.Path]::GetFullPath($OutputDirectory)
$timestamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$packageBaseName = "aureon-homepl-$timestamp"
$packagePath = Join-Path $releaseDirectory "$packageBaseName.zip"
$manifestPath = Join-Path $releaseDirectory "$packageBaseName-manifest.csv"
$stagingPath = Join-Path ([System.IO.Path]::GetTempPath()) ("aureon-homepl-stage-" + [guid]::NewGuid().ToString('N'))

$excludedFiles = @(
    'CHANGES.md',
    'data\projects.json',
    'assets\aureon-lux-aoia-runtime.svg',
    'assets\aureon-lux-hero-cosmic-map.svg',
    'assets\aureon-lux-lsc-waveform.svg',
    'assets\aureon-lux-route-architecture.svg',
    'assets\aureon-lux-source-registry.svg',
    'assets\aureon-lux\lsc-cosmic\lsc-solar-neutrino-cutaway.webp',
    'assets\images\projects\aioa-core.webp',
    'assets\images\projects\lsc-research.webp',
    'assets\images\projects\mhlm-mdlh.webp',
    'HOMEPL_PACKAGE_MANIFEST.txt',
    'HOMEPL_UPLOAD_README.md',
    'OWNER_CONTROL.md',
    'build-homepl-package.ps1',
    'backup-homepl-ftps.ps1',
    'publish-homepl-ftps.ps1',
    'refresh-operator-evidence.ps1'
)
$blockedExtensions = @('.env', '.key', '.pem', '.pfx', '.p12')
$blockedPathFragments = @('\.git\', '\node_modules\', '\__pycache__\')

New-Item -ItemType Directory -Path $releaseDirectory -Force | Out-Null
New-Item -ItemType Directory -Path $stagingPath -Force | Out-Null

try {
    $sourceFiles = foreach ($candidate in Get-ChildItem -LiteralPath $websiteRoot -File -Recurse) {
        $relativePath = $candidate.FullName.Substring($websiteRoot.Length).TrimStart([char]'\', [char]'/')
        $hasBlockedFragment = $false
        foreach ($fragment in $blockedPathFragments) {
            if ($candidate.FullName -like "*$fragment*") {
                $hasBlockedFragment = $true
                break
            }
        }

        if (
            $relativePath -notin $excludedFiles -and
            $blockedExtensions -notcontains $candidate.Extension.ToLowerInvariant() -and
            -not $hasBlockedFragment
        ) {
            $candidate
        }
    }

    if ($sourceFiles.Count -eq 0) {
        throw 'No website files were selected for the package.'
    }

    $manifest = foreach ($sourceFile in $sourceFiles) {
        $relativePath = $sourceFile.FullName.Substring($websiteRoot.Length).TrimStart([char]'\', [char]'/')
        $destinationPath = Join-Path $stagingPath $relativePath
        $destinationDirectory = Split-Path -Parent $destinationPath
        New-Item -ItemType Directory -Path $destinationDirectory -Force | Out-Null
        Copy-Item -LiteralPath $sourceFile.FullName -Destination $destinationPath

        [pscustomobject]@{
            Path = $relativePath.Replace('\', '/')
            Bytes = $sourceFile.Length
            Sha256 = (Get-FileHash -LiteralPath $sourceFile.FullName -Algorithm SHA256).Hash
        }
    }

    $manifest = @($manifest | Sort-Object Path)
    $manifest | Export-Csv -LiteralPath $manifestPath -NoTypeInformation -Encoding utf8

    Add-Type -AssemblyName System.IO.Compression
    $zipStream = [System.IO.File]::Open($packagePath, [System.IO.FileMode]::CreateNew)
    $zipArchive = [System.IO.Compression.ZipArchive]::new(
        $zipStream,
        [System.IO.Compression.ZipArchiveMode]::Create,
        $false
    )
    try {
        foreach ($manifestEntry in $manifest) {
            $sourcePath = Join-Path $stagingPath $manifestEntry.Path
            $zipEntry = $zipArchive.CreateEntry(
                $manifestEntry.Path,
                [System.IO.Compression.CompressionLevel]::Optimal
            )
            $inputStream = [System.IO.File]::OpenRead($sourcePath)
            $outputStream = $zipEntry.Open()
            try {
                $inputStream.CopyTo($outputStream)
            }
            finally {
                $outputStream.Dispose()
                $inputStream.Dispose()
            }
        }
    }
    finally {
        $zipArchive.Dispose()
        $zipStream.Dispose()
    }
    $packageHash = (Get-FileHash -LiteralPath $packagePath -Algorithm SHA256).Hash

    [pscustomobject]@{
        Package = $packagePath
        PackageSha256 = $packageHash
        Manifest = $manifestPath
        FileCount = @($manifest).Count
    } | Format-List
}
finally {
    if (Test-Path -LiteralPath $stagingPath) {
        Remove-Item -LiteralPath $stagingPath -Recurse -Force
    }
}
