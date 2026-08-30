[CmdletBinding()]
param(
    [string]$SiteRoot,
    [string]$OutputDirectory,
    [string]$RunId = (Get-Date -Format "yyyyMMdd_HHmmss")
)

$ErrorActionPreference = "Stop"
$useDefaultSiteRoot = -not $PSBoundParameters.ContainsKey('SiteRoot')
$useDefaultOutputDirectory = -not $PSBoundParameters.ContainsKey('OutputDirectory')
if ($useDefaultSiteRoot -or $useDefaultOutputDirectory) {
    $scriptDirectory = $PSScriptRoot
    if ([string]::IsNullOrWhiteSpace($scriptDirectory)) {
        $scriptPath = $PSCommandPath
        if ([string]::IsNullOrWhiteSpace($scriptPath)) {
            $scriptPath = $MyInvocation.MyCommand.Path
        }
        if ([string]::IsNullOrWhiteSpace($scriptPath)) {
            throw "Unable to resolve the website audit script directory for default paths."
        }
        $scriptDirectory = Split-Path -Path $scriptPath -Parent
    }
    $repositoryRoot = [IO.Path]::GetFullPath((Join-Path $scriptDirectory ".."))
    if ($useDefaultSiteRoot) {
        $SiteRoot = Join-Path $repositoryRoot "website"
    }
    if ($useDefaultOutputDirectory) {
        $OutputDirectory = Join-Path $repositoryRoot "docs\audits"
    }
}

$sitePath = (Resolve-Path -LiteralPath $SiteRoot).Path.TrimEnd([IO.Path]::DirectorySeparatorChar)
if (-not (Test-Path -LiteralPath $OutputDirectory)) {
    New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null
}
$outputPath = (Resolve-Path -LiteralPath $OutputDirectory).Path

function Get-FirstMatch {
    param([string]$Text, [string]$Pattern)
    $match = [regex]::Match($Text, $Pattern, [Text.RegularExpressions.RegexOptions]::IgnoreCase -bor [Text.RegularExpressions.RegexOptions]::Singleline)
    if (-not $match.Success) { return $null }
    return ([Net.WebUtility]::HtmlDecode($match.Groups[1].Value) -replace '<[^>]+>', ' ' -replace '\s+', ' ').Trim()
}

function Write-Utf8NoBom {
    param(
        [Parameter(Mandatory = $true)]
        [string]$LiteralPath,
        [Parameter(Mandatory = $true)]
        [string]$Content
    )

    [IO.File]::WriteAllText(
        $LiteralPath,
        $Content,
        (New-Object Text.UTF8Encoding($false))
    )
}

$pages = @()
$references = @()
$brokenReferences = @()
$encodingFindings = @()
$blockedClaimFindings = @()
$missingImageAltFindings = @()
$emptyTargetFindings = @()
$canonicalOgUrlMismatchFindings = @()
$personalMailboxFindings = @()
$staleIndexableCopyrightFindings = @()
$unsupportedOwnershipClaimFindings = @()
$currentYear = (Get-Date).Year
$blockedClaims = @(
    '4,?500\s+clones',
    '715\s+modules',
    '2,?694\s+files',
    'guaranteed\s+returns?',
    'live[- ]trading\s+performance'
)

$htmlFiles = @(Get-ChildItem -LiteralPath $sitePath -Recurse -File -Filter "*.html")
foreach ($file in $htmlFiles) {
    $raw = Get-Content -Raw -LiteralPath $file.FullName -Encoding UTF8
    $relativePage = $file.FullName.Substring($sitePath.Length).TrimStart([char]92)
    $title = Get-FirstMatch -Text $raw -Pattern '<title[^>]*>(.*?)</title>'
    $h1 = Get-FirstMatch -Text $raw -Pattern '<h1[^>]*>(.*?)</h1>'
    $description = Get-FirstMatch -Text $raw -Pattern '<meta\s+name="description"\s+content="(.*?)"'
    $canonical = Get-FirstMatch -Text $raw -Pattern '<link\s+rel="canonical"\s+href="(.*?)"'
    $ogTitle = Get-FirstMatch -Text $raw -Pattern '<meta\s+property="og:title"\s+content="(.*?)"'
    $ogDescription = Get-FirstMatch -Text $raw -Pattern '<meta\s+property="og:description"\s+content="(.*?)"'
    $ogUrl = Get-FirstMatch -Text $raw -Pattern '<meta\s+property="og:url"\s+content="(.*?)"'
    $ogImage = Get-FirstMatch -Text $raw -Pattern '<meta\s+property="og:image"\s+content="(.*?)"'
    $ogImageAlt = Get-FirstMatch -Text $raw -Pattern '<meta\s+property="og:image:alt"\s+content="(.*?)"'
    $twitterCard = Get-FirstMatch -Text $raw -Pattern '<meta\s+name="twitter:card"\s+content="(.*?)"'
    $twitterImage = Get-FirstMatch -Text $raw -Pattern '<meta\s+name="twitter:image"\s+content="(.*?)"'
    $twitterImageAlt = Get-FirstMatch -Text $raw -Pattern '<meta\s+name="twitter:image:alt"\s+content="(.*?)"'
    $noindex = [regex]::IsMatch($raw, '<meta\s+name="robots"[^>]*content="[^"]*noindex', 'IgnoreCase')
    $pages += [pscustomobject]@{
        page = $relativePage
        title = $title
        h1 = $h1
        description = $description
        canonical = $canonical
        og_title = $ogTitle
        og_description = $ogDescription
        og_url = $ogUrl
        og_image = $ogImage
        og_image_alt = $ogImageAlt
        twitter_card = $twitterCard
        twitter_image = $twitterImage
        twitter_image_alt = $twitterImageAlt
        noindex = $noindex
        title_present = -not [string]::IsNullOrWhiteSpace($title)
        h1_present = -not [string]::IsNullOrWhiteSpace($h1)
        description_present = -not [string]::IsNullOrWhiteSpace($description)
        canonical_present = -not [string]::IsNullOrWhiteSpace($canonical)
        og_title_present = -not [string]::IsNullOrWhiteSpace($ogTitle)
        og_description_present = -not [string]::IsNullOrWhiteSpace($ogDescription)
        og_url_present = -not [string]::IsNullOrWhiteSpace($ogUrl)
        og_image_present = -not [string]::IsNullOrWhiteSpace($ogImage)
        og_image_alt_present = -not [string]::IsNullOrWhiteSpace($ogImageAlt)
        twitter_card_present = -not [string]::IsNullOrWhiteSpace($twitterCard)
        twitter_image_present = -not [string]::IsNullOrWhiteSpace($twitterImage)
        twitter_image_alt_present = -not [string]::IsNullOrWhiteSpace($twitterImageAlt)
    }

    foreach ($match in [regex]::Matches($raw, '<img\b(?![^>]*\balt\s*=)[^>]*>', 'IgnoreCase')) {
        $missingImageAltFindings += [pscustomobject]@{ page = $relativePage; tag = $match.Value }
    }
    foreach ($match in [regex]::Matches($raw, '(?:href|src)\s*=\s*["'']\s*["'']', 'IgnoreCase')) {
        $emptyTargetFindings += [pscustomobject]@{ page = $relativePage; tag = $match.Value }
    }
    if (-not $noindex -and $canonical -and $ogUrl -and $canonical -ne $ogUrl) {
        $canonicalOgUrlMismatchFindings += [pscustomobject]@{ page = $relativePage; canonical = $canonical; og_url = $ogUrl }
    }
    if (-not $noindex) {
        foreach ($match in [regex]::Matches($raw, '[A-Z0-9._%+-]+@(gmail|outlook|hotmail|yahoo)\.[A-Z]{2,}', 'IgnoreCase')) {
            $personalMailboxFindings += [pscustomobject]@{ page = $relativePage; mailbox = $match.Value }
        }
        foreach ($match in [regex]::Matches($raw, '(?:&copy;|©)\s*(20\d{2})', 'IgnoreCase')) {
            $year = [int]$match.Groups[1].Value
            if ($year -ne $currentYear) {
                $staleIndexableCopyrightFindings += [pscustomobject]@{ page = $relativePage; year = $year; expected_year = $currentYear }
            }
        }
        foreach ($pattern in @('\bsole\s+owner\b', '\bone\s+owner\b', '\baccountable\s+owner\b', '\bdirector\s+and\s+owner\b')) {
            foreach ($match in [regex]::Matches($raw, $pattern, 'IgnoreCase')) {
                $unsupportedOwnershipClaimFindings += [pscustomobject]@{ page = $relativePage; claim = $match.Value; issue = 'ownership_precision_not_supported_by_public_psc_record' }
            }
        }
    }

    foreach ($match in [regex]::Matches($raw, '(?:href|src)="([^"]+)"', 'IgnoreCase')) {
        $value = $match.Groups[1].Value.Trim()
        if (-not $value -or $value.StartsWith('#') -or $value -match '^(https?:|mailto:|tel:|data:|javascript:)') { continue }
        $clean = ($value -split '[?#]')[0]
        if (-not $clean) { continue }
        if ($clean.StartsWith('/')) {
            $candidate = Join-Path $sitePath $clean.TrimStart('/')
        } else {
            $candidate = Join-Path $file.DirectoryName $clean
        }
        try { $candidate = [IO.Path]::GetFullPath($candidate) } catch { continue }
        if ($candidate.EndsWith([IO.Path]::DirectorySeparatorChar) -or (Test-Path -LiteralPath $candidate -PathType Container)) {
            $candidate = Join-Path $candidate "index.html"
        }
        $exists = Test-Path -LiteralPath $candidate
        $record = [pscustomobject]@{ page = $relativePage; reference = $value; resolved = $candidate; exists = $exists }
        $references += $record
        if (-not $exists) { $brokenReferences += $record }
    }

    if (
        $raw.Contains([string][char]0xFFFD) -or
        $raw.Contains([string][char]0x00C3) -or
        $raw.Contains([string][char]0x00C2) -or
        [regex]::IsMatch($raw, '\u00E2(?:\u20AC|\u2020|\u0080|\u0086|\u009C)')
    ) {
        $encodingFindings += [pscustomobject]@{ file = $relativePage; issue = "possible_mojibake" }
    }
    foreach ($pattern in $blockedClaims) {
        if ($raw -match $pattern) {
            $blockedClaimFindings += [pscustomobject]@{ file = $relativePage; pattern = $pattern }
        }
    }
}

$sitemapPath = Join-Path $sitePath "sitemap.xml"
$sitemapUrls = @()
$sitemapParseError = $null
if (Test-Path -LiteralPath $sitemapPath -PathType Leaf) {
    try {
        [xml]$sitemapXml = Get-Content -Raw -LiteralPath $sitemapPath -Encoding UTF8
        $sitemapUrls = @($sitemapXml.urlset.url | ForEach-Object { [string]$_.loc } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
    } catch {
        $sitemapParseError = $_.Exception.Message
    }
} else {
    $sitemapParseError = "sitemap.xml not found"
}
$indexableCanonicals = @($pages | Where-Object { -not $_.noindex -and $_.canonical_present } | ForEach-Object { $_.canonical })
$indexablePagesMissingFromSitemap = @($pages | Where-Object { -not $_.noindex -and $_.canonical_present -and $sitemapUrls -notcontains $_.canonical } | ForEach-Object {
    [pscustomobject]@{ page = $_.page; canonical = $_.canonical }
})
$sitemapUrlsWithoutIndexablePage = @($sitemapUrls | Where-Object { $indexableCanonicals -notcontains $_ } | ForEach-Object {
    [pscustomobject]@{ url = $_ }
})
$duplicateSitemapUrls = @($sitemapUrls | Group-Object | Where-Object Count -gt 1 | ForEach-Object {
    [pscustomobject]@{ url = $_.Name; count = $_.Count }
})

$jsonFindings = @()
$jsonFiles = @(Get-ChildItem -LiteralPath (Join-Path $sitePath "data") -Recurse -File -Filter "*.json")
foreach ($file in $jsonFiles) {
    $valid = $true
    $errorMessage = $null
    try { Get-Content -Raw -LiteralPath $file.FullName -Encoding UTF8 | ConvertFrom-Json | Out-Null } catch { $valid = $false; $errorMessage = $_.Exception.Message }
    $jsonFindings += [pscustomobject]@{
        file = $file.FullName.Substring($sitePath.Length).TrimStart([char]92)
        valid = $valid
        error = $errorMessage
    }
}

$duplicateTitles = @($pages | Where-Object title_present | Group-Object title | Where-Object Count -gt 1 | ForEach-Object {
    [pscustomobject]@{ title = $_.Name; count = $_.Count; pages = @($_.Group.page) }
})
$duplicateIndexableCanonicals = @($pages | Where-Object { -not $_.noindex -and $_.canonical_present } | Group-Object canonical | Where-Object Count -gt 1 | ForEach-Object {
    [pscustomobject]@{ canonical = $_.Name; count = $_.Count; pages = @($_.Group.page) }
})

$requiredClaimStates = @('Source-linked', 'Company-built', 'Research proposition', 'Independently reviewed', 'Next validation')
$claimLanguagePath = Join-Path $sitePath 'diligence\index.html'
$claimLanguageRaw = if (Test-Path -LiteralPath $claimLanguagePath -PathType Leaf) { Get-Content -Raw -LiteralPath $claimLanguagePath -Encoding UTF8 } else { '' }
$missingRequiredClaimStates = @($requiredClaimStates | Where-Object { $claimLanguageRaw -notmatch [regex]::Escape($_) } | ForEach-Object {
    [pscustomobject]@{ state = $_; expected_page = 'diligence\index.html' }
})

$requiredDiligenceQueueTerms = @('Public investor evidence', 'Company source', 'Platform', 'Research', 'Commercial path', 'Investor conversation', 'Companies House controls current company status', 'ORCID', 'What Aureon will prove next', 'Talk to the founder')
$diligenceQueueRaw = [Net.WebUtility]::HtmlDecode($claimLanguageRaw)
$missingRequiredDiligenceQueueTerms = @($requiredDiligenceQueueTerms | Where-Object { $diligenceQueueRaw -notmatch [regex]::Escape($_) } | ForEach-Object {
    [pscustomobject]@{ term = $_; expected_page = 'diligence\index.html' }
})

$requiredContactJourneyTerms = @('Start an investor conversation', 'Talk to the founder', 'Investor', 'Design partner', 'Independent review', 'gary@aureonzorzatechnologies.com')
$contactJourneyPath = Join-Path $sitePath 'contact\index.html'
$contactJourneyRaw = if (Test-Path -LiteralPath $contactJourneyPath -PathType Leaf) { [Net.WebUtility]::HtmlDecode((Get-Content -Raw -LiteralPath $contactJourneyPath -Encoding UTF8)) } else { '' }
$missingRequiredContactJourneyTerms = @($requiredContactJourneyTerms | Where-Object { $contactJourneyRaw -notmatch [regex]::Escape($_) } | ForEach-Object {
    [pscustomobject]@{ term = $_; expected_page = 'contact\index.html' }
})

$requiredEngagementRouterTerms = @('Choose the conversation', 'The investor route is primary', 'Design partner', 'Sector partnership', 'Independent review', 'Direct route', 'company-domain email')
$missingRequiredEngagementRouterTerms = @($requiredEngagementRouterTerms | Where-Object { $contactJourneyRaw -notmatch [regex]::Escape($_) } | ForEach-Object {
    [pscustomobject]@{ term = $_; expected_page = 'contact\index.html' }
})

$requiredVisionJourneyTerms = @('Current foundation', 'Next proof', 'Longer horizon', 'Independent technical review', 'Operational controls', 'Repeatable value', 'Direction', 'delivery commitment', 'Human decision')
$visionJourneyPath = Join-Path $sitePath 'vision\index.html'
$visionJourneyRaw = if (Test-Path -LiteralPath $visionJourneyPath -PathType Leaf) { [Net.WebUtility]::HtmlDecode((Get-Content -Raw -LiteralPath $visionJourneyPath -Encoding UTF8)) } else { '' }
$missingRequiredVisionJourneyTerms = @($requiredVisionJourneyTerms | Where-Object { $visionJourneyRaw -notmatch [regex]::Escape($_) } | ForEach-Object {
    [pscustomobject]@{ term = $_; expected_page = 'vision\index.html' }
})

$requiredLiveFreshnessTerms = @('Public proof', 'controlled diligence', 'Research depth. Inspectable architecture. Serious boundaries.', 'Inspect the implementation record directly.', 'ORCID & Zenodo', 'Public architecture record', 'Attributable sources', 'Human decision authority', 'bounded outputs', 'selector changes the reading view only', 'Supporting diligence is shared only in a qualified, scoped review.')
$liveFreshnessPath = Join-Path $sitePath 'live\index.html'
$liveFreshnessRaw = if (Test-Path -LiteralPath $liveFreshnessPath -PathType Leaf) { [Net.WebUtility]::HtmlDecode((Get-Content -Raw -LiteralPath $liveFreshnessPath -Encoding UTF8)) } else { '' }
$missingRequiredLiveFreshnessTerms = @($requiredLiveFreshnessTerms | Where-Object { $liveFreshnessRaw -notmatch [regex]::Escape($_) } | ForEach-Object {
    [pscustomobject]@{ term = $_; expected_page = 'live\index.html' }
})

$requiredPlatformLayers = @('Sources & context', 'Provenance & state', 'Human review gate', 'Accountable outputs')
$platformArchitecturePath = Join-Path $sitePath 'projects\index.html'
$platformArchitectureRaw = if (Test-Path -LiteralPath $platformArchitecturePath -PathType Leaf) { [Net.WebUtility]::HtmlDecode((Get-Content -Raw -LiteralPath $platformArchitecturePath -Encoding UTF8)) } else { '' }
$missingRequiredPlatformLayers = @($requiredPlatformLayers | Where-Object { $platformArchitectureRaw -notmatch [regex]::Escape($_) } | ForEach-Object {
    [pscustomobject]@{ layer = $_; expected_page = 'projects\index.html' }
})

$requiredPlatformPacketTerms = @('One research engine. One evidence operating system. Many high-consequence applications.', 'Research defines the principles. Aureon OS operationalises the discipline.', 'Inspect the four layers of a public evidence packet', 'Source-linked', 'Company-built', 'Authority required', 'Approval bounded', 'public repository', 'Independent technical review', 'selecting a layer changes the reading view only', 'does not run a workflow', 'create secure data-room access')
$missingRequiredPlatformPacketTerms = @($requiredPlatformPacketTerms | Where-Object { $platformArchitectureRaw -notmatch [regex]::Escape($_) } | ForEach-Object {
    [pscustomobject]@{ term = $_; expected_page = 'projects\index.html' }
})

$requiredPlatformRecordTerms = @('One evidence record. Four control layers.', 'Begin with the source, not the answer.', 'Human authority is never inferred from system access.', 'Four rules the interface should not hide.', 'Follow the proof route in the right order.', 'Move from source to trust one gate at a time.')
$platformRecordPath = Join-Path $sitePath 'projects\aureon-trading-system\index.html'
$platformRecordRaw = if (Test-Path -LiteralPath $platformRecordPath -PathType Leaf) { [Net.WebUtility]::HtmlDecode((Get-Content -Raw -LiteralPath $platformRecordPath -Encoding UTF8)) } else { '' }
$missingRequiredPlatformRecordTerms = @($requiredPlatformRecordTerms | Where-Object { $platformRecordRaw -notmatch [regex]::Escape($_) } | ForEach-Object {
    [pscustomobject]@{ term = $_; expected_page = 'projects\aureon-trading-system\index.html' }
})

$requiredCompanyRecordTerms = @('Official public source', 'Companies House is the authoritative source', 'controlling current source', 'Gary Anthony Leckey', 'ORCID', 'What Aureon will prove next')
$companyRecordPath = Join-Path $sitePath 'about\index.html'
$companyRecordRaw = if (Test-Path -LiteralPath $companyRecordPath -PathType Leaf) { [Net.WebUtility]::HtmlDecode((Get-Content -Raw -LiteralPath $companyRecordPath -Encoding UTF8)) } else { '' }
$missingRequiredCompanyRecordTerms = @($requiredCompanyRecordTerms | Where-Object { $companyRecordRaw -notmatch [regex]::Escape($_) } | ForEach-Object {
    [pscustomobject]@{ term = $_; expected_page = 'about\index.html' }
})

$requiredHomeControlTerms = @('Evidence infrastructure for decisions that cannot afford ambiguity.', 'From research question to accountable decision', 'Question', 'Source', 'Claim', 'Human gate', 'Decision', 'final receipt')
$homeControlPath = Join-Path $sitePath 'index.html'
$homeControlRaw = if (Test-Path -LiteralPath $homeControlPath -PathType Leaf) { [Net.WebUtility]::HtmlDecode((Get-Content -Raw -LiteralPath $homeControlPath -Encoding UTF8)) } else { '' }
$missingRequiredHomeControlTerms = @($requiredHomeControlTerms | Where-Object { $homeControlRaw -notmatch [regex]::Escape($_) } | ForEach-Object {
    [pscustomobject]@{ term = $_; expected_page = 'index.html' }
})

$requiredInvestorLensTerms = @('Investment thesis', 'Value creation path', 'Measured public attention', 'Evidence today', 'Next milestones', 'Investor lens', 'Funder lens', 'Technical-review lens', 'Research-partner lens', 'What will Aureon prove next?', 'Talk to the founder')
$investorLensPath = Join-Path $sitePath 'funding\investor-deck\index.html'
$investorLensRaw = if (Test-Path -LiteralPath $investorLensPath -PathType Leaf) { [Net.WebUtility]::HtmlDecode((Get-Content -Raw -LiteralPath $investorLensPath -Encoding UTF8)) } else { '' }
$missingRequiredInvestorLensTerms = @($requiredInvestorLensTerms | Where-Object { $investorLensRaw -notmatch [regex]::Escape($_) } | ForEach-Object {
    [pscustomobject]@{ term = $_; expected_page = 'funding\investor-deck\index.html' }
})

$requiredResearchJourneyTerms = @('Many fields. One reusable research contract.', 'Carries forward', 'Stops when', 'Reviewer opens', 'Research framework', 'Aureon OS', 'PULSE-CAL', 'EPAS Space Shield', 'Public research orientation', 'Flagship questions', 'independent challenge', 'Selected formal research index')
$researchJourneyPath = Join-Path $sitePath 'research\index.html'
$researchJourneyRaw = if (Test-Path -LiteralPath $researchJourneyPath -PathType Leaf) { [Net.WebUtility]::HtmlDecode((Get-Content -Raw -LiteralPath $researchJourneyPath -Encoding UTF8)) } else { '' }
$missingRequiredResearchJourneyTerms = @($requiredResearchJourneyTerms | Where-Object { $researchJourneyRaw -notmatch [regex]::Escape($_) } | ForEach-Object {
    [pscustomobject]@{ term = $_; expected_page = 'research\index.html' }
})

$researchSchemaFindings = @()
$researchDataPath = Join-Path $sitePath 'data\research.json'
if (Test-Path -LiteralPath $researchDataPath -PathType Leaf) {
    try {
        $parsedResearchData = Get-Content -Raw -LiteralPath $researchDataPath -Encoding UTF8 | ConvertFrom-Json
        foreach ($field in @('schema_version', 'coverage', 'profiles', 'papers')) {
            if (-not ($parsedResearchData.PSObject.Properties.Name -contains $field)) {
                $researchSchemaFindings += [pscustomobject]@{ field = $field; issue = 'missing_top_level_field' }
            }
        }
        if ([int]$parsedResearchData.schema_version -ne 3) {
            $researchSchemaFindings += [pscustomobject]@{ field = 'schema_version'; issue = 'unsupported_value'; value = $parsedResearchData.schema_version }
        }
        foreach ($field in @('scope', 'breadth', 'selection_policy', 'record_status_policy', 'public_research_notes', 'repository_working_material_note')) {
            if (-not ($parsedResearchData.coverage.PSObject.Properties.Name -contains $field) -or [string]::IsNullOrWhiteSpace([string]$parsedResearchData.coverage.$field)) {
                $researchSchemaFindings += [pscustomobject]@{ field = "coverage.$field"; issue = 'missing_or_empty_required_field' }
            }
        }
        if (@($parsedResearchData.coverage.breadth).Count -lt 3) {
            $researchSchemaFindings += [pscustomobject]@{ field = 'coverage.breadth'; issue = 'minimum_three_research_themes_required' }
        }
        foreach ($legacyField in @('checked_on', 'zenodo_records_listed', 'additional_indexed_record_count', 'unique_public_records_listed', 'orcid_public_work_groups', 'zenodo_current_records', 'full_public_research_view', 'catalogue_url', 'selected_register_note')) {
            if ($parsedResearchData.coverage.PSObject.Properties.Name -contains $legacyField) {
                $researchSchemaFindings += [pscustomobject]@{ field = "coverage.$legacyField"; issue = 'legacy_ledger_field_publicly_exposed' }
            }
        }
        $researchPapers = @($parsedResearchData.papers | ForEach-Object { $_ })
        if ($researchPapers.Count -eq 0) {
            $researchSchemaFindings += [pscustomobject]@{ field = 'papers'; issue = 'at_least_one_public_record_required' }
        }
        foreach ($requiredPlatform in @('Zenodo', 'ResearchGate')) {
            if (@($researchPapers | Where-Object { $_.platform -eq $requiredPlatform }).Count -eq 0) {
                $researchSchemaFindings += [pscustomobject]@{ field = 'papers.platform'; issue = 'required_public_source_missing'; value = $requiredPlatform }
            }
        }
        foreach ($paper in $researchPapers) {
            foreach ($field in @('author', 'title', 'type', 'platform', 'verification_status', 'url')) {
                if (-not ($paper.PSObject.Properties.Name -contains $field) -or [string]::IsNullOrWhiteSpace([string]$paper.$field)) {
                    $researchSchemaFindings += [pscustomobject]@{ record = $paper.title; field = $field; issue = 'missing_or_empty_required_field' }
                }
            }
            [uri]$parsedResearchUri = $null
            if ($paper.url -and -not [uri]::TryCreate([string]$paper.url, [UriKind]::Absolute, [ref]$parsedResearchUri)) {
                $researchSchemaFindings += [pscustomobject]@{ record = $paper.title; field = 'url'; issue = 'invalid_absolute_url'; value = $paper.url }
            }
            if (([string]$paper.url -match '17527830') -or ([string]$paper.doi -match '17527830')) {
                $researchSchemaFindings += [pscustomobject]@{ record = $paper.title; field = 'url_or_doi'; issue = 'concept_doi_must_not_be_counted_as_separate_record' }
            }
        }
        foreach ($duplicateUrl in @($researchPapers | Group-Object url | Where-Object Count -gt 1)) {
            $researchSchemaFindings += [pscustomobject]@{ field = 'url'; issue = 'duplicate_record_url'; value = $duplicateUrl.Name; count = $duplicateUrl.Count }
        }
        foreach ($profile in @($parsedResearchData.profiles | ForEach-Object { $_ })) {
            if ([string]$profile.role -match 'Director\s*&\s*Owner') {
                $researchSchemaFindings += [pscustomobject]@{ record = $profile.name; field = 'role'; issue = 'unsupported_ownership_precision'; value = $profile.role }
            }
        }
    } catch {
        $researchSchemaFindings += [pscustomobject]@{ field = $null; issue = 'research_parse_error'; error = $_.Exception.Message }
    }
} else {
    $researchSchemaFindings += [pscustomobject]@{ field = $null; issue = 'research_file_missing' }
}

$researchCatalogueSchemaFindings = @()
$parsedResearchCatalogueData = $null
$researchCataloguePath = Join-Path $sitePath 'data\research-catalogue.json'
if (Test-Path -LiteralPath $researchCataloguePath -PathType Leaf) {
    try {
        $parsedResearchCatalogueData = Get-Content -Raw -LiteralPath $researchCataloguePath -Encoding UTF8 | ConvertFrom-Json
        foreach ($field in @('schema_version', 'record_type', 'orcid', 'zenodo', 'research_breadth', 'evidence_boundary', 'recent_records')) {
            if (-not ($parsedResearchCatalogueData.PSObject.Properties.Name -contains $field)) {
                $researchCatalogueSchemaFindings += [pscustomobject]@{ field = $field; issue = 'missing_top_level_field' }
            }
        }
        if ([int]$parsedResearchCatalogueData.schema_version -ne 2) {
            $researchCatalogueSchemaFindings += [pscustomobject]@{ field = 'schema_version'; issue = 'unsupported_value'; value = $parsedResearchCatalogueData.schema_version }
        }
        if ([string]$parsedResearchCatalogueData.record_type -ne 'public_research_orientation') {
            $researchCatalogueSchemaFindings += [pscustomobject]@{ field = 'record_type'; issue = 'unsupported_value'; value = $parsedResearchCatalogueData.record_type }
        }
        foreach ($identityCheck in @(
            @{ parent = 'orcid'; field = 'id' },
            @{ parent = 'orcid'; field = 'url' },
            @{ parent = 'orcid'; field = 'role' },
            @{ parent = 'zenodo'; field = 'url' },
            @{ parent = 'zenodo'; field = 'role' }
        )) {
            $identityObject = $parsedResearchCatalogueData.($identityCheck.parent)
            if (-not ($identityObject.PSObject.Properties.Name -contains $identityCheck.field) -or [string]::IsNullOrWhiteSpace([string]$identityObject.($identityCheck.field))) {
                $researchCatalogueSchemaFindings += [pscustomobject]@{ field = "$($identityCheck.parent).$($identityCheck.field)"; issue = 'missing_or_empty_required_field' }
            }
        }
        foreach ($field in @('themes', 'method', 'review_posture', 'translation_gate')) {
            if (-not ($parsedResearchCatalogueData.research_breadth.PSObject.Properties.Name -contains $field) -or [string]::IsNullOrWhiteSpace([string]$parsedResearchCatalogueData.research_breadth.$field)) {
                $researchCatalogueSchemaFindings += [pscustomobject]@{ field = "research_breadth.$field"; issue = 'missing_or_empty_required_field' }
            }
        }
        if (@($parsedResearchCatalogueData.research_breadth.themes).Count -lt 3) {
            $researchCatalogueSchemaFindings += [pscustomobject]@{ field = 'research_breadth.themes'; issue = 'minimum_three_research_themes_required' }
        }
        $researchCatalogueRaw = Get-Content -Raw -LiteralPath $researchCataloguePath -Encoding UTF8
        foreach ($legacyField in @('checked_at', 'public_work_groups', 'last_modified_at', 'current_records', 'unique_dois', 'preprints', 'technical_notes', 'records_dated_2026_07_24', 'site_view', 'counting_note', 'independently_validated_records')) {
            if ($researchCatalogueRaw -match ('"' + [regex]::Escape($legacyField) + '"\s*:')) {
                $researchCatalogueSchemaFindings += [pscustomobject]@{ field = $legacyField; issue = 'legacy_ledger_field_publicly_exposed' }
            }
        }
        $recentResearchRecords = @($parsedResearchCatalogueData.recent_records | ForEach-Object { $_ })
        if ($recentResearchRecords.Count -eq 0) {
            $researchCatalogueSchemaFindings += [pscustomobject]@{ field = 'recent_records'; issue = 'at_least_one_orientation_record_required' }
        }
        foreach ($record in $recentResearchRecords) {
            foreach ($field in @('id', 'title', 'record_type', 'publication_date', 'doi', 'doi_url', 'url')) {
                if (-not ($record.PSObject.Properties.Name -contains $field) -or [string]::IsNullOrWhiteSpace([string]$record.$field)) {
                    $researchCatalogueSchemaFindings += [pscustomobject]@{ record = $record.id; field = $field; issue = 'missing_or_empty_required_field' }
                }
            }
        }
        foreach ($duplicateDoi in @($recentResearchRecords | Group-Object doi | Where-Object Count -gt 1)) {
            $researchCatalogueSchemaFindings += [pscustomobject]@{ field = 'recent_records.doi'; issue = 'duplicate_doi'; value = $duplicateDoi.Name; count = $duplicateDoi.Count }
        }
    } catch {
        $researchCatalogueSchemaFindings += [pscustomobject]@{ field = $null; issue = 'research_catalogue_parse_error'; error = $_.Exception.Message }
    }
} else {
    $researchCatalogueSchemaFindings += [pscustomobject]@{ field = $null; issue = 'research_catalogue_file_missing' }
}

$requiredJournalJourneyTerms = @('Questions first. Sources visible. Claims bounded.', 'Question before conclusion', 'Source before synthesis', 'Test before translation', 'Enter through the map', 'archive', 'not peer-reviewed publications')
$journalPagePath = Join-Path $sitePath 'research\journal\index.html'
$journalScriptPath = Join-Path $sitePath 'script.js'
$journalJourneyRaw = if (Test-Path -LiteralPath $journalPagePath -PathType Leaf) { [Net.WebUtility]::HtmlDecode((Get-Content -Raw -LiteralPath $journalPagePath -Encoding UTF8)) } else { '' }
if (Test-Path -LiteralPath $journalScriptPath -PathType Leaf) { $journalJourneyRaw += "`n" + (Get-Content -Raw -LiteralPath $journalScriptPath -Encoding UTF8) }
$missingRequiredJournalJourneyTerms = @($requiredJournalJourneyTerms | Where-Object { $journalJourneyRaw -notmatch [regex]::Escape($_) } | ForEach-Object {
    [pscustomobject]@{ term = $_; expected_page = 'research\journal\index.html' }
})

$journalSchemaFindings = @()
$journalDataPath = Join-Path $sitePath 'data\substack-research-index.json'
if (Test-Path -LiteralPath $journalDataPath -PathType Leaf) {
    try {
        $journalData = Get-Content -Raw -LiteralPath $journalDataPath -Encoding UTF8 | ConvertFrom-Json
        foreach ($field in @('schema_version', 'publication', 'publisher', 'profile_url', 'archive_url', 'catalogue_scope', 'verification_status', 'themes', 'entries')) {
            if (-not ($journalData.PSObject.Properties.Name -contains $field)) {
                $journalSchemaFindings += [pscustomobject]@{ field = $field; issue = 'missing_top_level_field' }
            }
        }
        if ([int]$journalData.schema_version -ne 3) {
            $journalSchemaFindings += [pscustomobject]@{ field = 'schema_version'; issue = 'unsupported_value'; value = $journalData.schema_version }
        }
        foreach ($legacyField in @('checked_on', 'archive_entry_count', 'direct_entry_count')) {
            if ($journalData.PSObject.Properties.Name -contains $legacyField) {
                $journalSchemaFindings += [pscustomobject]@{ field = $legacyField; issue = 'legacy_ledger_field_publicly_exposed' }
            }
        }
        $journalThemes = @($journalData.themes | ForEach-Object { $_ })
        $journalEntries = @($journalData.entries | ForEach-Object { $_ })
        if ($journalThemes.Count -lt 6) {
            $journalSchemaFindings += [pscustomobject]@{ field = 'themes'; issue = 'minimum_six_reading_themes_required'; value = $journalThemes.Count }
        }
        if ($journalEntries.Count -lt 1) {
            $journalSchemaFindings += [pscustomobject]@{ field = 'entries'; issue = 'at_least_one_verified_public_link_required'; value = $journalEntries.Count }
        }
        $themeIds = @($journalThemes | ForEach-Object { [string]$_.id })
        foreach ($theme in $journalThemes) {
            foreach ($field in @('id', 'label', 'description', 'prompt')) {
                if (-not ($theme.PSObject.Properties.Name -contains $field) -or [string]::IsNullOrWhiteSpace([string]$theme.$field)) {
                    $journalSchemaFindings += [pscustomobject]@{ record = $theme.id; field = $field; issue = 'missing_or_empty_theme_field' }
                }
            }
        }
        foreach ($entry in $journalEntries) {
            foreach ($field in @('title', 'url', 'published_utc', 'topic', 'archive_visible')) {
                if (-not ($entry.PSObject.Properties.Name -contains $field) -or (($field -ne 'archive_visible') -and [string]::IsNullOrWhiteSpace([string]$entry.$field))) {
                    $journalSchemaFindings += [pscustomobject]@{ record = $entry.title; field = $field; issue = 'missing_or_empty_entry_field' }
                }
            }
            if ($themeIds -notcontains [string]$entry.topic) {
                $journalSchemaFindings += [pscustomobject]@{ record = $entry.title; field = 'topic'; issue = 'unknown_theme'; value = $entry.topic }
            }
            [uri]$journalEntryUri = $null
            if (-not [uri]::TryCreate([string]$entry.url, [UriKind]::Absolute, [ref]$journalEntryUri) -or $journalEntryUri.Host -ne 'garyleckey.substack.com') {
                $journalSchemaFindings += [pscustomobject]@{ record = $entry.title; field = 'url'; issue = 'invalid_or_unexpected_public_source'; value = $entry.url }
            }
            [datetime]$journalPublished = [datetime]::MinValue
            if (-not [datetime]::TryParse([string]$entry.published_utc, [ref]$journalPublished)) {
                $journalSchemaFindings += [pscustomobject]@{ record = $entry.title; field = 'published_utc'; issue = 'invalid_timestamp'; value = $entry.published_utc }
            }
        }
        foreach ($duplicateUrl in @($journalEntries | Group-Object url | Where-Object Count -gt 1)) {
            $journalSchemaFindings += [pscustomobject]@{ field = 'url'; issue = 'duplicate_public_note_url'; value = $duplicateUrl.Name; count = $duplicateUrl.Count }
        }
    } catch {
        $journalSchemaFindings += [pscustomobject]@{ field = $null; issue = 'journal_parse_error'; error = $_.Exception.Message }
    }
} else {
    $journalSchemaFindings += [pscustomobject]@{ field = $null; issue = 'journal_file_missing' }
}

$requiredFundingJourneyTerms = @('One evidence core. Multiple sector routes. A disciplined path to scale.', 'Public boundary:', 'Public route map', 'Disclosure rule:', 'qualified, scoped review', 'Strategic relevance', 'Public evidence', 'Next validation', 'Qualified diligence', 'Grant & R&D', 'Compute access', 'Research partner', 'Mission-aligned capital')
$fundingPagePath = Join-Path $sitePath 'funding\index.html'
$fundingPageRaw = if (Test-Path -LiteralPath $fundingPagePath -PathType Leaf) { [Net.WebUtility]::HtmlDecode((Get-Content -Raw -LiteralPath $fundingPagePath -Encoding UTF8)) } else { '' }
$fundingStateFindings = @($requiredFundingJourneyTerms | Where-Object { $fundingPageRaw -notmatch [regex]::Escape($_) } | ForEach-Object {
    [pscustomobject]@{ record = 'Funding journey'; issue = 'missing_required_page_term'; value = $_ }
})
$fundingStatusPath = Join-Path $sitePath 'data\funding-status.json'
if (Test-Path -LiteralPath $fundingStatusPath -PathType Leaf) {
    try {
        $fundingStatusRaw = Get-Content -Raw -LiteralPath $fundingStatusPath -Encoding UTF8
        $fundingStatusData = $fundingStatusRaw | ConvertFrom-Json
        if ([int]$fundingStatusData.schema_version -ne 4) {
            $fundingStateFindings += [pscustomobject]@{ record = 'Funding register'; field = 'schema_version'; issue = 'unsupported_value'; value = $fundingStatusData.schema_version }
        }
        if ([string]$fundingStatusData.record_type -ne 'public_capital_and_partnership_route_map') {
            $fundingStateFindings += [pscustomobject]@{ record = 'Funding register'; field = 'record_type'; issue = 'unsupported_value'; value = $fundingStatusData.record_type }
        }
        $fundingRecords = @($fundingStatusData.routes)
        if ($fundingRecords.Count -ne 5) {
            $fundingStateFindings += [pscustomobject]@{ record = 'Funding register'; field = 'routes'; issue = 'expected_five_public_route_themes'; count = $fundingRecords.Count }
        }
        $fundingRouteTypes = @($fundingStatusData.route_types)
        $uniqueFundingRouteTypes = @($fundingRouteTypes | ForEach-Object { [string]$_.label } | Sort-Object -Unique)
        if ($fundingRouteTypes.Count -ne 5 -or $uniqueFundingRouteTypes.Count -ne 5) {
            $fundingStateFindings += [pscustomobject]@{ record = 'Funding register'; field = 'route_types'; issue = 'expected_five_unique_route_types'; count = $fundingRouteTypes.Count; unique_count = $uniqueFundingRouteTypes.Count }
        }
        $expectedRouteTypes = @('Grant', 'Compute access', 'Procurement', 'Defence innovation', 'Investor')
        foreach ($expectedRouteType in $expectedRouteTypes) {
            if ($uniqueFundingRouteTypes -notcontains $expectedRouteType) {
                $fundingStateFindings += [pscustomobject]@{ record = 'Funding register'; field = 'route_types'; issue = 'required_route_type_missing'; value = $expectedRouteType }
            }
        }
        foreach ($routeType in $fundingRouteTypes) {
            foreach ($field in @('label', 'description')) {
                if ([string]::IsNullOrWhiteSpace([string]$routeType.$field)) {
                    $fundingStateFindings += [pscustomobject]@{ record = 'Funding route type'; field = $field; issue = 'required_value_missing' }
                }
            }
        }
        foreach ($signalField in @('route_areas', 'external_routes', 'diligence_detail', 'disclosure_boundary')) {
            if ([string]::IsNullOrWhiteSpace([string]$fundingStatusData.public_signals.$signalField)) {
                $fundingStateFindings += [pscustomobject]@{ record = 'Funding public signals'; field = $signalField; issue = 'required_value_missing' }
            }
        }
        foreach ($coverageField in @('scope', 'status_policy', 'refresh_policy')) {
            if ([string]::IsNullOrWhiteSpace([string]$fundingStatusData.coverage.$coverageField)) {
                $fundingStateFindings += [pscustomobject]@{ record = 'Funding coverage'; field = $coverageField; issue = 'required_value_missing' }
            }
        }
        if ([string]$fundingStatusData.coverage.refresh_policy -notmatch 'qualified,\s*scoped review') {
            $fundingStateFindings += [pscustomobject]@{ record = 'Funding coverage'; field = 'refresh_policy'; issue = 'qualified_diligence_boundary_missing' }
        }
        foreach ($record in $fundingRecords) {
            foreach ($field in @('route_type', 'state_group', 'programme', 'title', 'status_label', 'status_detail', 'innovation_type', 'summary', 'public_signal', 'next_gate', 'public_boundary')) {
                if ([string]::IsNullOrWhiteSpace([string]$record.$field)) {
                    $fundingStateFindings += [pscustomobject]@{ record = [string]$record.title; field = $field; issue = 'required_value_missing' }
                }
            }
            if ($uniqueFundingRouteTypes -notcontains [string]$record.route_type) {
                $fundingStateFindings += [pscustomobject]@{ record = [string]$record.title; field = 'route_type'; issue = 'unknown_route_type'; value = $record.route_type }
            }
            if ([string]$record.state_group -ne 'strategic-theme') {
                $fundingStateFindings += [pscustomobject]@{ record = [string]$record.title; field = 'state_group'; issue = 'unsupported_public_state'; value = $record.state_group }
            }
        }
        foreach ($duplicateRoute in @($fundingRecords | Group-Object -Property route_type | Where-Object { $_.Count -gt 1 })) {
            $fundingStateFindings += [pscustomobject]@{ record = 'Funding register'; field = 'route_type'; issue = 'duplicate_public_route_type'; value = $duplicateRoute.Name; count = $duplicateRoute.Count }
        }
        foreach ($duplicateTitle in @($fundingRecords | Group-Object -Property title | Where-Object { $_.Count -gt 1 })) {
            $fundingStateFindings += [pscustomobject]@{ record = 'Funding register'; field = 'title'; issue = 'duplicate_public_title'; value = $duplicateTitle.Name; count = $duplicateTitle.Count }
        }
        $forbiddenFundingFields = @(
            'application_number',
            'application_id',
            'provider_reference',
            'submission_reference',
            'company_request',
            'request_amount',
            'evidence_basis',
            'source_snapshot',
            'provider_delta',
            'source_counts',
            'run_id',
            'monitor_id',
            'monitor_run_id',
            'closing_label',
            'email_evidence',
            'correspondence',
            'meeting_time',
            'portal_url',
            'published_at',
            'awards_or_investment_claimed',
            'status_tone',
            'applications',
            'internal_records'
        )
        foreach ($forbiddenField in $forbiddenFundingFields) {
            if ($fundingStatusRaw -match ('"' + [regex]::Escape($forbiddenField) + '"\s*:')) {
                $fundingStateFindings += [pscustomobject]@{ record = 'Funding register'; field = $forbiddenField; issue = 'internal_field_publicly_exposed' }
            }
        }
        if ($fundingStatusRaw -match '(?i)"[^"]*(?:_id|_reference)"\s*:') {
            $fundingStateFindings += [pscustomobject]@{ record = 'Funding register'; field = $Matches[0]; issue = 'internal_identifier_field_publicly_exposed' }
        }
        foreach ($forbiddenPattern in @(
            '(?i)AUREON_[A-Z0-9_-]*MONITOR[A-Z0-9_-]*',
            '(?i)\b(?:gmail|calendly)\b',
            '(?i)/public_html',
            '(?i)\bgpu\s+hours?\b',
            '(?:\u00A3|\u20AC|\u0024)',
            '(?i)\b(?:GBP|EUR|USD)\s*\d',
            '(?i)\b(?:pounds?|euros?|dollars?)\b',
            '(?<![\d-])\d{8,}(?![\d-])',
            '(?i)\b[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\b'
        )) {
            if ($fundingStatusRaw -match $forbiddenPattern) {
                $fundingStateFindings += [pscustomobject]@{ record = 'Funding register'; issue = 'internal_value_pattern_publicly_exposed'; pattern = $forbiddenPattern; value = $Matches[0] }
            }
        }
    } catch {
        $fundingStateFindings += [pscustomobject]@{ record = 'Funding register'; issue = 'funding_status_parse_error'; error = $_.Exception.Message }
    }
} else {
    $fundingStateFindings += [pscustomobject]@{ record = 'Funding register'; issue = 'funding_status_file_missing' }
}

$requiredEvidenceRoomTerms = @('Research you can inspect at source', 'Question', 'Source', 'Method', 'Next validation', 'ORCID', 'Zenodo', 'No records match these filters')
$evidenceRoomPath = Join-Path $sitePath 'publications\index.html'
$scriptPath = Join-Path $sitePath 'script.js'
$evidenceRoomPageRaw = if (Test-Path -LiteralPath $evidenceRoomPath -PathType Leaf) { [Net.WebUtility]::HtmlDecode((Get-Content -Raw -LiteralPath $evidenceRoomPath -Encoding UTF8)) } else { '' }
$evidenceRoomRaw = $evidenceRoomPageRaw
if (Test-Path -LiteralPath $scriptPath -PathType Leaf) { $evidenceRoomRaw += "`n" + (Get-Content -Raw -LiteralPath $scriptPath -Encoding UTF8) }
$missingRequiredEvidenceRoomTerms = @($requiredEvidenceRoomTerms | Where-Object { $evidenceRoomRaw -notmatch [regex]::Escape($_) } | ForEach-Object {
    [pscustomobject]@{ term = $_; expected_page = 'publications\index.html' }
})

# Investor-facing surfaces must express the opportunity without publishing
# fundraising mechanics, internal operating records, or obsolete defensive copy.
$investorSurfaceTexts = [ordered]@{
    'about\index.html' = $companyRecordRaw
    'diligence\index.html' = $diligenceQueueRaw
    'publications\index.html' = $evidenceRoomPageRaw
    'contact\index.html' = $contactJourneyRaw
    'funding\investor-deck\index.html' = $investorLensRaw
}
$investorSurfaceBlockedPatterns = @(
    '(?i)\b(?:valuation|runway|fundraising target|raise target|annual recurring revenue|ARR|committed capital)\b',
    '(?i)\binternal (?:company |operating )?records?\b',
    '(?i)\bapplication values?\b',
    '(?i)\bgrant (?:reference|application|value)\b',
    '(?i)\bportal records?\b',
    '(?i)\bfinancing (?:requirements?|assumptions?|forecasts?)\b',
    '(?i)\bcurrent revenue\b',
    '(?i)\bopen evidence gaps\b',
    '(?i)\bdo not send\b',
    '(?i)\bprovider receipt\b',
    '(?i)\bsubmission receipt\b',
    '(?i)\brecord path\s*/\s*v\d+\b',
    '(?i)\bdoes not submit a form\b',
    '(?i)\bpromise a reply\b',
    '(?i)\b75%\s+or\s+more\b',
    '(?i)\bidentity.verification due\b',
    '(?i)\bconfirmation statement.{0,60}\boverdue\b',
    '(?i)\bcontrolled (?:investor materials|diligence)\b'
)
foreach ($surface in $investorSurfaceTexts.GetEnumerator()) {
    foreach ($pattern in $investorSurfaceBlockedPatterns) {
        if ([regex]::IsMatch([string]$surface.Value, $pattern)) {
            $blockedClaimFindings += [pscustomobject]@{ file = $surface.Key; pattern = $pattern; issue = 'investor_surface_disclosure_or_residue' }
        }
    }
}

$publicationSchemaFindings = @()
$publicationRecords = @()
$publicationsDataPath = Join-Path $sitePath 'data\publications.json'
if (Test-Path -LiteralPath $publicationsDataPath -PathType Leaf) {
    try {
        $parsedPublicationsData = Get-Content -Raw -LiteralPath $publicationsDataPath -Encoding UTF8 | ConvertFrom-Json
        if ($parsedPublicationsData -is [array]) {
            $publicationSchemaFindings += [pscustomobject]@{ id = $null; field = $null; issue = 'schema_v3_object_required' }
        } else {
            foreach ($field in @('schema_version', 'scope', 'boundary', 'records')) {
                if (-not ($parsedPublicationsData.PSObject.Properties.Name -contains $field)) {
                    $publicationSchemaFindings += [pscustomobject]@{ id = $null; field = $field; issue = 'missing_top_level_field' }
                }
            }
            if ([int]$parsedPublicationsData.schema_version -ne 3) {
                $publicationSchemaFindings += [pscustomobject]@{ id = $null; field = 'schema_version'; issue = 'unsupported_value'; value = $parsedPublicationsData.schema_version }
            }
            $publicationRecords = @($parsedPublicationsData.records | ForEach-Object { $_ })
            if ($publicationRecords.Count -eq 0) {
                $publicationSchemaFindings += [pscustomobject]@{ id = $null; field = 'records'; issue = 'empty_public_register' }
            }
            if ($parsedPublicationsData.PSObject.Properties.Name -contains 'checked_on') {
                $publicationSchemaFindings += [pscustomobject]@{ id = $null; field = 'checked_on'; issue = 'legacy_ledger_field_publicly_exposed' }
            }
            $requiredPublicationFields = @('id', 'record_group', 'title', 'record_type', 'author', 'channel', 'evidence_state', 'source_url', 'boundary', 'featured')
            $allowedPublicationGroups = @('Company source', 'Research catalogue', 'Current research orientation', 'Research record', 'Author commentary')
            $requiredPublicationGroups = @('Company source', 'Research catalogue', 'Research record', 'Author commentary')
            $allowedPublicationEvidenceStates = @('Source-linked', 'Company-built', 'Research proposition', 'Independently reviewed', 'Next validation')
            foreach ($record in $publicationRecords) {
                foreach ($field in $requiredPublicationFields) {
                    if (-not ($record.PSObject.Properties.Name -contains $field)) {
                        $publicationSchemaFindings += [pscustomobject]@{ id = $record.id; field = $field; issue = 'missing_field' }
                    } elseif ($field -ne 'featured' -and [string]::IsNullOrWhiteSpace([string]$record.$field)) {
                        $publicationSchemaFindings += [pscustomobject]@{ id = $record.id; field = $field; issue = 'empty_required_field' }
                    }
                }
                if ($record.record_group -and $allowedPublicationGroups -notcontains [string]$record.record_group) {
                    $publicationSchemaFindings += [pscustomobject]@{ id = $record.id; field = 'record_group'; issue = 'unsupported_value'; value = $record.record_group }
                }
                if ($record.evidence_state -and $allowedPublicationEvidenceStates -notcontains [string]$record.evidence_state) {
                    $publicationSchemaFindings += [pscustomobject]@{ id = $record.id; field = 'evidence_state'; issue = 'unsupported_value'; value = $record.evidence_state }
                }
                [uri]$parsedPublicationUri = $null
                if ($record.source_url -and -not [uri]::TryCreate([string]$record.source_url, [UriKind]::Absolute, [ref]$parsedPublicationUri)) {
                    $publicationSchemaFindings += [pscustomobject]@{ id = $record.id; field = 'source_url'; issue = 'invalid_absolute_url'; value = $record.source_url }
                }
                if ($record.PSObject.Properties.Name -contains 'checked_on') {
                    $publicationSchemaFindings += [pscustomobject]@{ id = $record.id; field = 'checked_on'; issue = 'legacy_ledger_field_publicly_exposed' }
                }
            }
            foreach ($duplicateId in @($publicationRecords | Group-Object id | Where-Object Count -gt 1)) {
                $publicationSchemaFindings += [pscustomobject]@{ id = $duplicateId.Name; field = 'id'; issue = 'duplicate_id'; count = $duplicateId.Count }
            }
            foreach ($duplicateSourceUrl in @($publicationRecords | Group-Object source_url | Where-Object Count -gt 1)) {
                $publicationSchemaFindings += [pscustomobject]@{ id = $null; field = 'source_url'; issue = 'duplicate_source_url'; value = $duplicateSourceUrl.Name; count = $duplicateSourceUrl.Count }
            }
            foreach ($conceptDoiRecord in @($publicationRecords | Where-Object { [string]$_.source_url -match '17527830' -or [string]$_.doi_url -match '17527830' })) {
                $publicationSchemaFindings += [pscustomobject]@{ id = $conceptDoiRecord.id; field = 'source_url_or_doi_url'; issue = 'concept_doi_must_not_be_counted_as_separate_record' }
            }
            foreach ($requiredGroup in $requiredPublicationGroups) {
                if (@($publicationRecords | Where-Object { $_.record_group -eq $requiredGroup }).Count -eq 0) {
                    $publicationSchemaFindings += [pscustomobject]@{ id = $null; field = 'record_group'; issue = 'required_group_missing'; value = $requiredGroup }
                }
            }
        }
    } catch {
        $publicationSchemaFindings += [pscustomobject]@{ id = $null; field = $null; issue = 'publications_parse_error'; error = $_.Exception.Message }
    }
} else {
    $publicationSchemaFindings += [pscustomobject]@{ id = $null; field = $null; issue = 'publications_file_missing' }
}

$publicDataConsistencyFindings = @()

$updatesSchemaFindings = @()
$updatesSortFindings = @()
$missingRequiredUpdateStates = @()
$updatesDataPath = Join-Path $sitePath 'data\updates.json'
$updatesPagePath = Join-Path $sitePath 'updates\index.html'
$updatesPageRaw = if (Test-Path -LiteralPath $updatesPagePath -PathType Leaf) { [Net.WebUtility]::HtmlDecode((Get-Content -Raw -LiteralPath $updatesPagePath -Encoding UTF8)) } else { '' }
$requiredUpdatePageStates = @('Investor milestone brief', 'Research authority', 'Shared platform', 'Sector reach', 'Public recognition', 'Next validation')
$missingRequiredUpdateStates += @($requiredUpdatePageStates | Where-Object { $updatesPageRaw -notmatch [regex]::Escape($_) } | ForEach-Object {
    [pscustomobject]@{ state = $_; expected_page = 'updates\index.html' }
})
foreach ($legacyPageTerm in @('Evidence state', 'Company-recorded', 'Provider-confirmed', 'Implementation ledger', 'Public boundary', 'Permitted reading')) {
    if ($updatesPageRaw -match [regex]::Escape($legacyPageTerm)) {
        $updatesSchemaFindings += [pscustomobject]@{ id = 'updates-page'; field = $null; issue = 'legacy_ledger_language_publicly_exposed'; value = $legacyPageTerm }
    }
}
if (Test-Path -LiteralPath $updatesDataPath -PathType Leaf) {
    try {
        $parsedUpdatesData = Get-Content -Raw -LiteralPath $updatesDataPath -Encoding UTF8 | ConvertFrom-Json
        $updatesData = @($parsedUpdatesData | ForEach-Object { $_ })
        $requiredUpdateFields = @('id', 'date', 'title', 'summary', 'category', 'investor_relevance', 'source_name', 'source_label', 'source_url', 'next_validation')
        $requiredNonEmptyUpdateFields = @($requiredUpdateFields)
        $allowedUpdateCategories = @('Research authority', 'Platform', 'Sector reach', 'Public recognition')
        $legacyUpdateFields = @('evidence_state', 'deployment_state', 'public_boundary', 'status', 'completed', 'next_gate', 'application_number', 'application_id', 'provider_reference', 'request_amount', 'monitor_run_id', 'correspondence')
        $previousUpdateDate = [datetime]::MaxValue
        foreach ($update in $updatesData) {
            foreach ($field in $requiredUpdateFields) {
                if (-not ($update.PSObject.Properties.Name -contains $field)) {
                    $updatesSchemaFindings += [pscustomobject]@{ id = $update.id; field = $field; issue = 'missing_field' }
                }
            }
            foreach ($field in $requiredNonEmptyUpdateFields) {
                if (-not ($update.PSObject.Properties.Name -contains $field) -or [string]::IsNullOrWhiteSpace([string]$update.$field)) {
                    $updatesSchemaFindings += [pscustomobject]@{ id = $update.id; field = $field; issue = 'empty_required_field' }
                }
            }
            if ($update.category -and $allowedUpdateCategories -notcontains [string]$update.category) {
                $updatesSchemaFindings += [pscustomobject]@{ id = $update.id; field = 'category'; issue = 'unsupported_value'; value = $update.category }
            }
            foreach ($legacyField in $legacyUpdateFields) {
                if ($update.PSObject.Properties.Name -contains $legacyField) {
                    $updatesSchemaFindings += [pscustomobject]@{ id = $update.id; field = $legacyField; issue = 'legacy_ledger_field_publicly_exposed' }
                }
            }
            $parsedUpdateDate = [datetime]::MinValue
            if (-not [datetime]::TryParseExact([string]$update.date, 'yyyy-MM-dd', [Globalization.CultureInfo]::InvariantCulture, [Globalization.DateTimeStyles]::None, [ref]$parsedUpdateDate)) {
                $updatesSortFindings += [pscustomobject]@{ id = $update.id; date = $update.date; issue = 'invalid_iso_date' }
            } elseif ($parsedUpdateDate -gt $previousUpdateDate) {
                $updatesSortFindings += [pscustomobject]@{ id = $update.id; date = $update.date; issue = 'not_descending' }
            } else {
                $previousUpdateDate = $parsedUpdateDate
            }
        }
        foreach ($requiredCategory in $allowedUpdateCategories) {
            if (@($updatesData | Where-Object { $_.category -eq $requiredCategory }).Count -eq 0) {
                $missingRequiredUpdateStates += [pscustomobject]@{ state = $requiredCategory; expected_file = 'data\updates.json' }
            }
        }
    } catch {
        $updatesSchemaFindings += [pscustomobject]@{ id = $null; field = $null; issue = 'updates_parse_error'; error = $_.Exception.Message }
    }
} else {
    $updatesSchemaFindings += [pscustomobject]@{ id = $null; field = $null; issue = 'updates_file_missing' }
}

$result = [ordered]@{
    schema_version = 1
    run_id = $RunId
    generated_at = (Get-Date).ToString('o')
    site_root = $sitePath
    summary = [ordered]@{
        html_pages = $pages.Count
        missing_titles = @($pages | Where-Object { -not $_.title_present }).Count
        missing_h1 = @($pages | Where-Object { -not $_.h1_present }).Count
        missing_descriptions = @($pages | Where-Object { -not $_.description_present }).Count
        missing_canonicals = @($pages | Where-Object { -not $_.canonical_present -and -not $_.noindex }).Count
        missing_indexable_og_titles = @($pages | Where-Object { -not $_.noindex -and -not $_.og_title_present }).Count
        missing_indexable_og_descriptions = @($pages | Where-Object { -not $_.noindex -and -not $_.og_description_present }).Count
        missing_indexable_og_urls = @($pages | Where-Object { -not $_.noindex -and -not $_.og_url_present }).Count
        missing_indexable_og_images = @($pages | Where-Object { -not $_.noindex -and -not $_.og_image_present }).Count
        missing_indexable_og_image_alts = @($pages | Where-Object { -not $_.noindex -and -not $_.og_image_alt_present }).Count
        missing_indexable_twitter_cards = @($pages | Where-Object { -not $_.noindex -and -not $_.twitter_card_present }).Count
        missing_indexable_twitter_images = @($pages | Where-Object { -not $_.noindex -and -not $_.twitter_image_present }).Count
        missing_indexable_twitter_image_alts = @($pages | Where-Object { -not $_.noindex -and -not $_.twitter_image_alt_present }).Count
        sitemap_urls = $sitemapUrls.Count
        sitemap_parse_errors = if ($sitemapParseError) { 1 } else { 0 }
        indexable_pages_missing_from_sitemap = $indexablePagesMissingFromSitemap.Count
        sitemap_urls_without_indexable_page = $sitemapUrlsWithoutIndexablePage.Count
        duplicate_sitemap_urls = $duplicateSitemapUrls.Count
        local_references = $references.Count
        broken_local_references = $brokenReferences.Count
        json_files = $jsonFindings.Count
        invalid_json_files = @($jsonFindings | Where-Object { -not $_.valid }).Count
        duplicate_titles = $duplicateTitles.Count
        duplicate_indexable_canonicals = $duplicateIndexableCanonicals.Count
        canonical_og_url_mismatches = $canonicalOgUrlMismatchFindings.Count
        missing_image_alt_attributes = $missingImageAltFindings.Count
        empty_link_or_asset_targets = $emptyTargetFindings.Count
        missing_required_claim_states = $missingRequiredClaimStates.Count
        missing_required_diligence_queue_terms = $missingRequiredDiligenceQueueTerms.Count
        missing_required_contact_journey_terms = $missingRequiredContactJourneyTerms.Count
        missing_required_engagement_router_terms = $missingRequiredEngagementRouterTerms.Count
        missing_required_vision_journey_terms = $missingRequiredVisionJourneyTerms.Count
        missing_required_live_freshness_terms = $missingRequiredLiveFreshnessTerms.Count
        missing_required_platform_layers = $missingRequiredPlatformLayers.Count
        missing_required_platform_packet_terms = $missingRequiredPlatformPacketTerms.Count
        missing_required_platform_record_terms = $missingRequiredPlatformRecordTerms.Count
        missing_required_company_record_terms = $missingRequiredCompanyRecordTerms.Count
        missing_required_home_control_terms = $missingRequiredHomeControlTerms.Count
        missing_required_investor_lens_terms = $missingRequiredInvestorLensTerms.Count
        missing_required_research_journey_terms = $missingRequiredResearchJourneyTerms.Count
        research_schema_findings = $researchSchemaFindings.Count
        research_catalogue_schema_findings = $researchCatalogueSchemaFindings.Count
        missing_required_journal_journey_terms = $missingRequiredJournalJourneyTerms.Count
        journal_schema_findings = $journalSchemaFindings.Count
        funding_state_findings = $fundingStateFindings.Count
        publication_records = $publicationRecords.Count
        publication_schema_findings = $publicationSchemaFindings.Count
        public_data_consistency_findings = $publicDataConsistencyFindings.Count
        missing_required_evidence_room_terms = $missingRequiredEvidenceRoomTerms.Count
        updates_schema_findings = $updatesSchemaFindings.Count
        updates_sort_findings = $updatesSortFindings.Count
        missing_required_update_states = $missingRequiredUpdateStates.Count
        personal_mailboxes_on_indexable_pages = $personalMailboxFindings.Count
        stale_indexable_copyright_years = $staleIndexableCopyrightFindings.Count
        unsupported_ownership_claims = $unsupportedOwnershipClaimFindings.Count
        possible_encoding_findings = $encodingFindings.Count
        blocked_claim_findings = $blockedClaimFindings.Count
    }
    pages = $pages
    sitemap = [ordered]@{
        urls = $sitemapUrls
        parse_error = $sitemapParseError
        indexable_pages_missing_from_sitemap = $indexablePagesMissingFromSitemap
        urls_without_indexable_page = $sitemapUrlsWithoutIndexablePage
        duplicate_urls = $duplicateSitemapUrls
    }
    broken_references = $brokenReferences
    json = $jsonFindings
    duplicate_titles = $duplicateTitles
    duplicate_indexable_canonicals = $duplicateIndexableCanonicals
    canonical_og_url_mismatches = $canonicalOgUrlMismatchFindings
    missing_image_alt_attributes = $missingImageAltFindings
    empty_link_or_asset_targets = $emptyTargetFindings
    missing_required_claim_states = $missingRequiredClaimStates
    missing_required_diligence_queue_terms = $missingRequiredDiligenceQueueTerms
    missing_required_contact_journey_terms = $missingRequiredContactJourneyTerms
    missing_required_engagement_router_terms = $missingRequiredEngagementRouterTerms
    missing_required_vision_journey_terms = $missingRequiredVisionJourneyTerms
    missing_required_live_freshness_terms = $missingRequiredLiveFreshnessTerms
    missing_required_platform_layers = $missingRequiredPlatformLayers
    missing_required_platform_packet_terms = $missingRequiredPlatformPacketTerms
    missing_required_platform_record_terms = $missingRequiredPlatformRecordTerms
    missing_required_company_record_terms = $missingRequiredCompanyRecordTerms
    missing_required_home_control_terms = $missingRequiredHomeControlTerms
    missing_required_investor_lens_terms = $missingRequiredInvestorLensTerms
    missing_required_research_journey_terms = $missingRequiredResearchJourneyTerms
    research_schema_findings = $researchSchemaFindings
    research_catalogue_schema_findings = $researchCatalogueSchemaFindings
    missing_required_journal_journey_terms = $missingRequiredJournalJourneyTerms
    journal_schema_findings = $journalSchemaFindings
    funding_state_findings = $fundingStateFindings
    publication_schema_findings = $publicationSchemaFindings
    public_data_consistency_findings = $publicDataConsistencyFindings
    missing_required_evidence_room_terms = $missingRequiredEvidenceRoomTerms
    updates_schema_findings = $updatesSchemaFindings
    updates_sort_findings = $updatesSortFindings
    missing_required_update_states = $missingRequiredUpdateStates
    personal_mailboxes_on_indexable_pages = $personalMailboxFindings
    stale_indexable_copyright_years = $staleIndexableCopyrightFindings
    unsupported_ownership_claims = $unsupportedOwnershipClaimFindings
    encoding_findings = $encodingFindings
    blocked_claim_findings = $blockedClaimFindings
}

$jsonPath = Join-Path $outputPath ("AUREON_WEBSITE_AUDIT_{0}.json" -f $RunId)
$markdownPath = Join-Path $outputPath ("AUREON_WEBSITE_AUDIT_{0}.md" -f $RunId)

$s = $result.summary
$status = if ($s.missing_required_live_freshness_terms -eq 0 -and $s.broken_local_references -eq 0 -and $s.invalid_json_files -eq 0 -and $s.missing_titles -eq 0 -and $s.missing_h1 -eq 0 -and $s.blocked_claim_findings -eq 0 -and $s.missing_indexable_og_titles -eq 0 -and $s.missing_indexable_og_descriptions -eq 0 -and $s.missing_indexable_og_urls -eq 0 -and $s.missing_indexable_og_images -eq 0 -and $s.missing_indexable_og_image_alts -eq 0 -and $s.missing_indexable_twitter_cards -eq 0 -and $s.missing_indexable_twitter_images -eq 0 -and $s.missing_indexable_twitter_image_alts -eq 0 -and $s.sitemap_parse_errors -eq 0 -and $s.indexable_pages_missing_from_sitemap -eq 0 -and $s.sitemap_urls_without_indexable_page -eq 0 -and $s.duplicate_sitemap_urls -eq 0 -and $s.duplicate_indexable_canonicals -eq 0 -and $s.canonical_og_url_mismatches -eq 0 -and $s.missing_image_alt_attributes -eq 0 -and $s.empty_link_or_asset_targets -eq 0 -and $s.missing_required_claim_states -eq 0 -and $s.missing_required_diligence_queue_terms -eq 0 -and $s.missing_required_contact_journey_terms -eq 0 -and $s.missing_required_engagement_router_terms -eq 0 -and $s.missing_required_vision_journey_terms -eq 0 -and $s.missing_required_platform_layers -eq 0 -and $s.missing_required_platform_packet_terms -eq 0 -and $s.missing_required_platform_record_terms -eq 0 -and $s.missing_required_company_record_terms -eq 0 -and $s.missing_required_home_control_terms -eq 0 -and $s.missing_required_investor_lens_terms -eq 0 -and $s.missing_required_research_journey_terms -eq 0 -and $s.research_schema_findings -eq 0 -and $s.research_catalogue_schema_findings -eq 0 -and $s.missing_required_journal_journey_terms -eq 0 -and $s.journal_schema_findings -eq 0 -and $s.funding_state_findings -eq 0 -and $s.publication_schema_findings -eq 0 -and $s.public_data_consistency_findings -eq 0 -and $s.missing_required_evidence_room_terms -eq 0 -and $s.updates_schema_findings -eq 0 -and $s.updates_sort_findings -eq 0 -and $s.missing_required_update_states -eq 0 -and $s.personal_mailboxes_on_indexable_pages -eq 0 -and $s.stale_indexable_copyright_years -eq 0 -and $s.unsupported_ownership_claims -eq 0) { "PASS_WITH_REVIEW" } else { "ACTION_REQUIRED" }
$result["status"] = $status
Write-Utf8NoBom -LiteralPath $jsonPath -Content ($result | ConvertTo-Json -Depth 8)
$markdown = @"
# Aureon website audit - $RunId

Status: **$status**
Generated: $($result.generated_at)
Site root: $sitePath

| Check | Result |
|---|---:|
| HTML pages | $($s.html_pages) |
| Missing titles | $($s.missing_titles) |
| Missing H1 | $($s.missing_h1) |
| Missing descriptions | $($s.missing_descriptions) |
| Missing canonicals on indexable pages | $($s.missing_canonicals) |
| Missing Open Graph titles on indexable pages | $($s.missing_indexable_og_titles) |
| Missing Open Graph descriptions on indexable pages | $($s.missing_indexable_og_descriptions) |
| Missing Open Graph URLs on indexable pages | $($s.missing_indexable_og_urls) |
| Missing Open Graph images on indexable pages | $($s.missing_indexable_og_images) |
| Missing Open Graph image alt text on indexable pages | $($s.missing_indexable_og_image_alts) |
| Missing Twitter cards on indexable pages | $($s.missing_indexable_twitter_cards) |
| Missing Twitter images on indexable pages | $($s.missing_indexable_twitter_images) |
| Missing Twitter image alt text on indexable pages | $($s.missing_indexable_twitter_image_alts) |
| Sitemap URLs | $($s.sitemap_urls) |
| Sitemap parse errors | $($s.sitemap_parse_errors) |
| Indexable pages missing from sitemap | $($s.indexable_pages_missing_from_sitemap) |
| Sitemap URLs without an indexable page | $($s.sitemap_urls_without_indexable_page) |
| Duplicate sitemap URLs | $($s.duplicate_sitemap_urls) |
| Local references | $($s.local_references) |
| Broken local references | $($s.broken_local_references) |
| JSON files | $($s.json_files) |
| Invalid JSON files | $($s.invalid_json_files) |
| Duplicate titles | $($s.duplicate_titles) |
| Duplicate indexable canonicals | $($s.duplicate_indexable_canonicals) |
| Canonical / Open Graph URL mismatches | $($s.canonical_og_url_mismatches) |
| Images missing an alt attribute | $($s.missing_image_alt_attributes) |
| Empty link or asset targets | $($s.empty_link_or_asset_targets) |
| Missing required claim states | $($s.missing_required_claim_states) |
| Missing required Diligence-queue terms | $($s.missing_required_diligence_queue_terms) |
| Missing required contact-journey terms | $($s.missing_required_contact_journey_terms) |
| Missing required engagement-router terms | $($s.missing_required_engagement_router_terms) |
| Missing required vision-journey terms | $($s.missing_required_vision_journey_terms) |
| Missing required Live-freshness terms | $($s.missing_required_live_freshness_terms) |
| Missing required platform layers | $($s.missing_required_platform_layers) |
| Missing required Platform packet-inspector terms | $($s.missing_required_platform_packet_terms) |
| Missing required Platform-record terms | $($s.missing_required_platform_record_terms) |
| Missing required company-register terms | $($s.missing_required_company_record_terms) |
| Missing required homepage control-path terms | $($s.missing_required_home_control_terms) |
| Missing required investor-lens terms | $($s.missing_required_investor_lens_terms) |
| Missing required Research-journey terms | $($s.missing_required_research_journey_terms) |
| Research schema findings | $($s.research_schema_findings) |
| Research catalogue schema findings | $($s.research_catalogue_schema_findings) |
| Missing required Journal-journey terms | $($s.missing_required_journal_journey_terms) |
| Journal schema findings | $($s.journal_schema_findings) |
| Funding-state findings | $($s.funding_state_findings) |
| Publication records | $($s.publication_records) |
| Publication schema findings | $($s.publication_schema_findings) |
| Public data consistency findings | $($s.public_data_consistency_findings) |
| Missing required Evidence-room terms | $($s.missing_required_evidence_room_terms) |
| Updates schema findings | $($s.updates_schema_findings) |
| Updates chronology findings | $($s.updates_sort_findings) |
| Missing required update states | $($s.missing_required_update_states) |
| Personal mailboxes on indexable pages | $($s.personal_mailboxes_on_indexable_pages) |
| Stale copyright years on indexable pages | $($s.stale_indexable_copyright_years) |
| Unsupported ownership claims on indexable pages | $($s.unsupported_ownership_claims) |
| Possible encoding findings | $($s.possible_encoding_findings) |
| Blocked claim findings | $($s.blocked_claim_findings) |

The machine-readable companion contains page-level metadata, sitemap coverage, broken-reference details, JSON parse results, canonical consistency, image-alt and empty-target checks, required public claim states, the current public Diligence queue, homepage control-path, contact, vision, investor-lens, Research proof-path, current ORCID and Zenodo catalogue and Journal observatory journey controls, the Platform packet inspector and detail-record terms, company-register terms, public-safe capital and partnership route-map checks, Research, Journal and publication-register schema checks, public Evidence-room content, investor milestone schema and chronology checks, indexable-page mailbox, copyright and ownership-precision checks, possible encoding findings and blocked-claim matches. Possible encoding findings require human review because archived material may intentionally preserve source text.
"@
Write-Utf8NoBom -LiteralPath $markdownPath -Content $markdown

Write-Output "AUDIT_STATUS=$status"
Write-Output "AUDIT_JSON=$jsonPath"
Write-Output "AUDIT_MARKDOWN=$markdownPath"
