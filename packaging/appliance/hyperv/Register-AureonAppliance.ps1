#Requires -Version 7.2

[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string] $ManifestPath,

    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[A-Za-z0-9][A-Za-z0-9_. -]{0,63}$')]
    [string] $VmName,

    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string] $VmStoragePath,

    [ValidateRange(2GB, 64GB)]
    [UInt64] $MemoryStartupBytes = 4GB,

    [ValidateRange(1, 8)]
    [int] $ProcessorCount = 2,

    [string] $SwitchName,
    [string] $VerificationPath,
    [switch] $EnableLinuxSecureBoot,
    [switch] $Start
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

[ordered]@{
    schema = 'aureon.appliance.hyperv-registration-hold.v2'
    decision = 'HOLD'
    vm_created = $false
    vhdx_copied = $false
    vm_started = $false
    receipt_written = $false
    requested_start = [bool] $Start
    reason = 'native_appliance_release_boundary_required'
} | ConvertTo-Json -Compress | Write-Output

throw 'Aureon Hyper-V registration and start are on terminal protection HOLD.'
