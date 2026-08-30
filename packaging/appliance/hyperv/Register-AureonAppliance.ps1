#Requires -Version 7.2
#Requires -RunAsAdministrator

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

Import-Module Hyper-V -ErrorAction Stop

function Assert-LocalNoReparsePath {
    param(
        [Parameter(Mandatory = $true)]
        [string] $Path,
        [Parameter(Mandatory = $true)]
        [string] $Label,
        [switch] $LeafMayBeMissing
    )

    if (-not [IO.Path]::IsPathFullyQualified($Path)) {
        throw "$Label must be an absolute local path."
    }
    $fullPath = [IO.Path]::GetFullPath($Path)
    if ($fullPath.StartsWith('\\')) {
        throw "$Label may not use a UNC path."
    }
    $root = [IO.Path]::GetPathRoot($fullPath)
    if (-not $root -or $root.Length -lt 2) {
        throw "$Label has no local drive root."
    }
    $pathTail = $fullPath.Substring($root.Length)
    if ($pathTail.Contains(':')) {
        throw "$Label may not use an NTFS alternate data stream."
    }
    foreach ($segment in $pathTail.Split([IO.Path]::DirectorySeparatorChar)) {
        if (-not $segment) {
            continue
        }
        if ($segment.EndsWith('.') -or $segment.EndsWith(' ')) {
            throw "$Label contains a trailing dot or space."
        }
        if ($segment -match '^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)') {
            throw "$Label contains a reserved Windows device name."
        }
    }
    $drive = Get-PSDrive -Name $root.Substring(0, 1) -PSProvider FileSystem -ErrorAction Stop
    if ($drive.DisplayRoot) {
        throw "$Label may not use a mapped network drive."
    }
    if (-not $LeafMayBeMissing -and -not (Test-Path -LiteralPath $fullPath)) {
        throw "$Label does not exist."
    }
    $cursorPath = if (Test-Path -LiteralPath $fullPath) {
        $fullPath
    } else {
        [IO.Path]::GetDirectoryName($fullPath)
    }
    $cursor = Get-Item -LiteralPath $cursorPath -Force -ErrorAction Stop
    while ($null -ne $cursor) {
        if ($cursor.Attributes -band [IO.FileAttributes]::ReparsePoint) {
            throw "$Label traverses a reparse point: $($cursor.FullName)"
        }
        $cursor = $cursor.Parent
    }
    return $fullPath
}

if ($VmName.EndsWith('.') -or $VmName.EndsWith(' ') -or $VmName -match '^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)') {
    throw 'VmName contains a reserved or ambiguous Windows filename.'
}

$manifestFullPath = Assert-LocalNoReparsePath -Path $ManifestPath -Label 'ManifestPath'
$manifestItem = Get-Item -LiteralPath $manifestFullPath -ErrorAction Stop
if ($manifestItem.PSIsContainer -or ($manifestItem.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
    throw 'ManifestPath must be a regular local file, not a directory or reparse point.'
}
$manifest = Get-Content -LiteralPath $manifestItem.FullName -Raw -Encoding UTF8 | ConvertFrom-Json -Depth 20
if ($manifest.schema -ne 'aureon.appliance.artifacts.v1') {
    throw "Unsupported artifact manifest schema: $($manifest.schema)"
}
if ($manifest.status -ne 'built_unbooted') {
    throw "Unexpected artifact manifest status: $($manifest.status)"
}

if ($Start) {
    if (-not $VerificationPath) {
        throw '-Start requires -VerificationPath from a passing offline QEMU/OVMF boot verification.'
    }
    $verificationFullPath = Assert-LocalNoReparsePath -Path $VerificationPath -Label 'VerificationPath'
    $verificationItem = Get-Item -LiteralPath $verificationFullPath -ErrorAction Stop
    if ($verificationItem.PSIsContainer -or ($verificationItem.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
        throw 'VerificationPath must be a regular local file, not a directory or reparse point.'
    }
    $verification = Get-Content -LiteralPath $verificationItem.FullName -Raw -Encoding UTF8 | ConvertFrom-Json -Depth 20
    if ($verification.schema -ne 'aureon.appliance.verification.v1' -or $verification.status -ne 'pass') {
        throw 'The verification report is not a passing Aureon appliance verification.'
    }
    if ($verification.boot.status -ne 'pass' -or $verification.boot.marker -ne 'AUREON_APPLIANCE_BOOTABLE_FIRSTBOOT_REQUIRED') {
        throw 'The verification report does not contain the required offline boot marker.'
    }
}

$vhdxEntries = @($manifest.artifacts | Where-Object { $_.format -eq 'vhdx' })
if ($vhdxEntries.Count -ne 1) {
    throw 'Artifact manifest must contain exactly one fixed VHDX.'
}
$vhdxEntry = $vhdxEntries[0]
if ($vhdxEntry.path -notmatch '^[A-Za-z0-9][A-Za-z0-9_.-]*\.vhdx$') {
    throw 'VHDX artifact path must be a canonical filename.'
}
$vhdxPath = Join-Path -Path $manifestItem.DirectoryName -ChildPath $vhdxEntry.path
$vhdxFullPath = Assert-LocalNoReparsePath -Path $vhdxPath -Label 'canonical VHDX'
$vhdxItem = Get-Item -LiteralPath $vhdxFullPath -ErrorAction Stop
if ($vhdxItem.PSIsContainer -or ($vhdxItem.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
    throw 'VHDX must be a regular local file, not a directory or reparse point.'
}
if ([UInt64] $vhdxItem.Length -ne [UInt64] $vhdxEntry.size) {
    throw 'VHDX size does not match the artifact manifest.'
}
$actualHash = (Get-FileHash -LiteralPath $vhdxItem.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
if ($actualHash -ne [string] $vhdxEntry.sha256) {
    throw 'VHDX SHA-256 does not match the artifact manifest.'
}
if (-not (Test-VHD -Path $vhdxItem.FullName)) {
    throw 'Hyper-V Test-VHD rejected the artifact.'
}
if (Get-VM -Name $VmName -ErrorAction SilentlyContinue) {
    throw "A Hyper-V VM named '$VmName' already exists; refusing to alter it."
}

$vmVhdxPath = Assert-LocalNoReparsePath -Path $VmStoragePath -Label 'VmStoragePath' -LeafMayBeMissing
if ([IO.Path]::GetExtension($vmVhdxPath) -ine '.vhdx') {
    throw 'VmStoragePath must end in .vhdx.'
}
if ($vmVhdxPath -ieq $vhdxItem.FullName) {
    throw 'VmStoragePath must differ from the immutable canonical artifact.'
}
if (Test-Path -LiteralPath $vmVhdxPath) {
    throw 'VmStoragePath already exists; refusing to overwrite it.'
}
$vmStorageParent = Get-Item -LiteralPath ([IO.Path]::GetDirectoryName($vmVhdxPath)) -ErrorAction Stop
if (-not $vmStorageParent.PSIsContainer -or ($vmStorageParent.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
    throw 'VmStoragePath parent must be an existing regular local directory.'
}
$receiptPath = Join-Path -Path $manifestItem.DirectoryName -ChildPath "$VmName.hyperv-registration.json"
if (Test-Path -LiteralPath $receiptPath) {
    throw 'Registration receipt already exists; refusing to overwrite it.'
}

if ($Start) {
    $verifiedVhdx = @(
        $verification.artifacts | Where-Object {
            $_.format -eq 'vhdx' -and [string] $_.sha256 -eq $actualHash
        }
    )
    if ($verifiedVhdx.Count -ne 1) {
        throw 'The passing verification report is not bound to this VHDX hash.'
    }
}

$newVmParameters = @{
    Name = $VmName
    Generation = 2
    MemoryStartupBytes = $MemoryStartupBytes
    VHDPath = $vmVhdxPath
}
if ($SwitchName) {
    if (-not (Get-VMSwitch -Name $SwitchName -ErrorAction SilentlyContinue)) {
        throw "Hyper-V switch '$SwitchName' does not exist."
    }
    $newVmParameters['SwitchName'] = $SwitchName
}

if ($PSCmdlet.ShouldProcess($VmName, 'Create disconnected-by-default Aureon Generation-2 VM')) {
    $copyCreated = $false
    $vmCreated = $false
    $receiptTemporary = "$receiptPath.$PID.tmp"
    $receiptTemporaryCreated = $false
    $receiptCreated = $false
    $registrationLockPath = Join-Path -Path $manifestItem.DirectoryName -ChildPath "$VmName.hyperv-registration.lock"
    $registrationLock = $null
    $registrationLockCreated = $false
    try {
        $registrationLock = [IO.File]::Open(
            $registrationLockPath,
            [IO.FileMode]::CreateNew,
            [IO.FileAccess]::Write,
            [IO.FileShare]::None
        )
        $registrationLockCreated = $true
        $lockBytes = [Text.Encoding]::UTF8.GetBytes("pid=$PID`n")
        $registrationLock.Write($lockBytes, 0, $lockBytes.Length)
        $registrationLock.Flush($true)
        $sourceStream = $null
        $destinationStream = $null
        try {
            $sourceStream = [IO.File]::Open(
                $vhdxItem.FullName,
                [IO.FileMode]::Open,
                [IO.FileAccess]::Read,
                [IO.FileShare]::Read
            )
            $destinationStream = [IO.File]::Open(
                $vmVhdxPath,
                [IO.FileMode]::CreateNew,
                [IO.FileAccess]::Write,
                [IO.FileShare]::None
            )
            $copyCreated = $true
            $sourceStream.CopyTo($destinationStream)
            $destinationStream.Flush($true)
        } finally {
            if ($destinationStream) {
                $destinationStream.Dispose()
            }
            if ($sourceStream) {
                $sourceStream.Dispose()
            }
        }
        $vmDiskHash = (Get-FileHash -LiteralPath $vmVhdxPath -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($vmDiskHash -ne $actualHash -or -not (Test-VHD -Path $vmVhdxPath)) {
            throw 'The VM-owned VHDX copy failed hash or Hyper-V validation.'
        }
        $vm = New-VM @newVmParameters
        $vmCreated = $true
        Set-VM -VM $vm -AutomaticStartAction Nothing -AutomaticStopAction ShutDown `
            -CheckpointType Disabled
        Set-VMProcessor -VM $vm -Count $ProcessorCount
        if ($EnableLinuxSecureBoot) {
            Set-VMFirmware -VM $vm -EnableSecureBoot On `
                -SecureBootTemplate 'MicrosoftUEFICertificateAuthority'
        } else {
            Set-VMFirmware -VM $vm -EnableSecureBoot Off
        }

        if ($Start) {
            Start-VM -VM $vm
        }
        $receipt = [ordered]@{
            schema = 'aureon.appliance.hyperv-registration.v1'
            status = if ($Start) { 'started_not_hyperv_boot_verified' } else { 'registered_not_boot_verified' }
            vm_name = $VmName
            generation = 2
            canonical_vhdx_sha256 = $actualHash
            artifact_manifest_sha256 = (Get-FileHash -LiteralPath $manifestItem.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
            offline_verification_sha256 = if ($Start) { (Get-FileHash -LiteralPath $verificationItem.FullName -Algorithm SHA256).Hash.ToLowerInvariant() } else { $null }
            vm_vhdx_path = $vmVhdxPath
            vm_vhdx_sha256 = $vmDiskHash
            secure_boot_enabled = [bool] $EnableLinuxSecureBoot
            secure_boot_template = if ($EnableLinuxSecureBoot) { 'MicrosoftUEFICertificateAuthority' } else { $null }
            network_switch = if ($SwitchName) { $SwitchName } else { $null }
            started = [bool] $Start
        }
        $receiptBytes = [Text.UTF8Encoding]::new($false).GetBytes(
            ($receipt | ConvertTo-Json -Depth 8)
        )
        $receiptStream = [IO.File]::Open(
            $receiptTemporary,
            [IO.FileMode]::CreateNew,
            [IO.FileAccess]::Write,
            [IO.FileShare]::None
        )
        $receiptTemporaryCreated = $true
        try {
            $receiptStream.Write($receiptBytes, 0, $receiptBytes.Length)
            $receiptStream.Flush($true)
        } finally {
            $receiptStream.Dispose()
        }
        Move-Item -LiteralPath $receiptTemporary -Destination $receiptPath
        $receiptCreated = $true
        $receiptTemporaryCreated = $false
        $receipt | ConvertTo-Json -Depth 8
    } catch {
        $originalError = $_
        $cleanupErrors = [Collections.Generic.List[string]]::new()
        if ($vmCreated) {
            try {
                $createdVm = Get-VM -Name $VmName -ErrorAction SilentlyContinue
                if ($createdVm) {
                    if ($createdVm.State -ne 'Off') {
                        Stop-VM -VM $createdVm -TurnOff -Confirm:$false
                    }
                    Remove-VM -VM $createdVm -Force
                }
            } catch {
                $cleanupErrors.Add("VM cleanup failed: $($_.Exception.Message)")
            }
        }
        if ($copyCreated -and (Test-Path -LiteralPath $vmVhdxPath)) {
            try {
                Remove-Item -LiteralPath $vmVhdxPath -Force
            } catch {
                $cleanupErrors.Add("VHDX cleanup failed: $($_.Exception.Message)")
            }
        }
        if ($receiptTemporaryCreated -and (Test-Path -LiteralPath $receiptTemporary)) {
            try {
                Remove-Item -LiteralPath $receiptTemporary -Force
            } catch {
                $cleanupErrors.Add("receipt-temporary cleanup failed: $($_.Exception.Message)")
            }
        }
        if ($receiptCreated -and (Test-Path -LiteralPath $receiptPath)) {
            try {
                Remove-Item -LiteralPath $receiptPath -Force
            } catch {
                $cleanupErrors.Add("published-receipt cleanup failed: $($_.Exception.Message)")
            }
        }
        if ($cleanupErrors.Count -gt 0) {
            throw "Registration failed: $($originalError.Exception.Message); partial-state cleanup errors: $($cleanupErrors -join '; ')"
        }
        throw $originalError
    } finally {
        if ($registrationLock) {
            $registrationLock.Dispose()
        }
        if ($registrationLockCreated -and (Test-Path -LiteralPath $registrationLockPath)) {
            Remove-Item -LiteralPath $registrationLockPath -Force -ErrorAction SilentlyContinue
        }
    }
}
