[CmdletBinding()]
param(
  [string]$OperatorBaseUrl = "http://127.0.0.1:8790",
  [string]$OutputPath = (Join-Path $PSScriptRoot "data\operator-evidence.json"),
  [switch]$VerifyLocalProvider,
  [string]$OperatorBearerToken = ""
)

$ErrorActionPreference = "Stop"

function Get-OperatorJson {
  param([Parameter(Mandatory = $true)][string]$Path)
  Invoke-RestMethod -Uri ("{0}/{1}" -f $OperatorBaseUrl.TrimEnd("/"), $Path) -Method Get -TimeoutSec 10
}

try {
  $health = Get-OperatorJson -Path "healthz"
  $readiness = Get-OperatorJson -Path "readyz"
} catch {
  throw "Could not collect the operator's read-only health evidence. No snapshot was written. $($_.Exception.Message)"
}

$providers = @($health.providers)
$usesStub = @($providers | Where-Object { [string]$_.adapter -match "stub" }).Count -gt 0
$usesLocalModel = @($providers | Where-Object { [string]$_.adapter -eq "AureonLocalAdapter" }).Count -gt 0
$providerProbe = $null
# A local provider line is only investor-useful when the model has answered a
# fixed probe. Verify it by default so an unattended refresh cannot silently
# replace stronger evidence with an untested "active" label. The switch is kept
# for compatibility with existing operator commands.
if ($usesLocalModel) {
  $headers = @{}
  if ($OperatorBearerToken) { $headers.Authorization = "Bearer $OperatorBearerToken" }
  try {
    $providerProbe = Invoke-RestMethod `
      -Uri ("{0}/api/providers/ollama/test" -f $OperatorBaseUrl.TrimEnd("/")) `
      -Method Post `
      -Headers $headers `
      -ContentType "application/json" `
      -Body "{}" `
      -TimeoutSec 90
  } catch {
    throw "The local provider proof did not complete. No snapshot was written. $($_.Exception.Message)"
  }
  if (-not [bool]$providerProbe.ok) {
    throw "The local provider proof failed. No snapshot was written. $([string]$providerProbe.error)"
  }
}
$providerMode = if ($usesStub) { "Offline fallback" } elseif ($usesLocalModel) { "Local model active" } elseif ($providers.Count -gt 0) { "Configured operator providers" } else { "No providers reported" }
$providerDetail = if ($usesStub) {
  "AureonStubAdapter observed. This snapshot does not claim a live external model provider."
} elseif ($providerProbe -and [bool]$providerProbe.ok) {
  "A self-hosted model completed Aureon's fixed read-only provider probe. Only the safe adapter and model identifiers are published; the operator route remains private."
} elseif ($usesLocalModel) {
  "AureonLocalAdapter was reported active. A separate provider-response proof was not requested for this snapshot."
} elseif ($providers.Count -gt 0) {
  "Providers were reported by the local health check. Provider credentials and configuration are not published."
} else {
  "No provider line-up was returned by the local health check."
}
$providerLines = @($providers | ForEach-Object {
  [ordered]@{
    name = [string]$_.name
    adapter = [string]$_.adapter
    model = [string]$_.model
  }
})

$policy = $readiness.checks.real_data_policy
$snapshot = [ordered]@{
  schema_version = (Get-Date).ToString("yyyy-MM-dd")
  evidence_type = "operator_runtime_snapshot"
  observed_at_utc = (Get-Date).ToUniversalTime().ToString("o")
  source = [ordered]@{
    service = [string]$health.service
    collection_method = if ($providerProbe) { "Redacted loopback checks: GET /healthz, GET /readyz, and one fixed read-only local-provider probe" } else { "Redacted read-only loopback checks: GET /healthz and GET /readyz" }
    publication_mode = "Static dated snapshot; not a public operator endpoint"
  }
  health = [ordered]@{ ok = [bool]$health.ok }
  readiness = [ordered]@{
    ready = [bool]$readiness.ready
    checks = [ordered]@{
      providers = [bool]$readiness.checks.providers
      repository_index = [bool]$readiness.checks.repo_index
      cognition = [bool]$readiness.checks.cognition
    }
  }
  provider_mode = [ordered]@{
    label = $providerMode
    detail = $providerDetail
    line_count = [int]$providers.Count
    lines = $providerLines
  }
  provider_probe = if ($providerProbe) {
    [ordered]@{
      status = "Verified"
      ok = [bool]$providerProbe.ok
      model = [string]$providerProbe.model
      latency_ms = [int]$providerProbe.latency_ms
      verification = "Fixed response received; response content not published"
    }
  } else {
    [ordered]@{
      status = "Not run"
      ok = $false
      model = ""
      latency_ms = 0
      verification = "No provider-response proof requested"
    }
  }
  real_data_evidence = [ordered]@{
    status = if (($policy.probe_summary.live -gt 0) -or ($policy.probe_summary.cached_real -gt 0)) { "Evidence reported by readiness policy" } else { "Not available in this snapshot" }
    live_sources = [int]($policy.probe_summary.live | ForEach-Object { $_ })
    cached_real_sources = [int]($policy.probe_summary.cached_real | ForEach-Object { $_ })
    probe_report_status = [string]$policy.probe_report_status
  }
  public_boundary = @(
    "No prompts, actions, controls, credentials, sessions, base URLs, or provider secrets are published.",
    "A healthy snapshot is not a claim of financial, scientific, or commercial performance.",
    "A separate authenticated host is required before any operator service is deployed beyond loopback."
  )
}

$json = $snapshot | ConvertTo-Json -Depth 7
$utf8WithoutBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($OutputPath, "$json`r`n", $utf8WithoutBom)
Write-Output "Wrote redacted operator evidence snapshot: $OutputPath"
