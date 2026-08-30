# Aureon ISO/VHDX appliance pipeline

This directory defines a real, fail-closed path to a UEFI-bootable Aureon
appliance. It does **not** contain a prebuilt operating-system image, and it
does not download one. The canonical image is a Debian Linux appliance whose
default control plane is Aureon's operator, organism, and HNC daemons. It is
not a new kernel and is not evidence that Aureon is the sole OS on a physical
computer.

## Current boundary

The pipeline code and its offline contract can be validated on Windows. Image
construction requires a Linux x86-64 builder because mkosi relies on Linux
namespaces and systemd-repart. The committed `inputs.example.json` is
deliberately unusable: its zero hashes and placeholder paths force a HOLD until
an owner supplies the missing base root filesystem, tools tree, wheelhouse,
QEMU/OVMF assets, and their real hashes.

No pipeline command elevates privileges, downloads media, starts a VM, mounts
an image, alters Hyper-V, or copies `.env` files. A generated VHDX is registered
only by the separate owner-invoked PowerShell handoff, which requires an
elevated Hyper-V session and does not start the VM unless `-Start` is explicit.

## Trust and build model

The build has four ordered stages:

1. `preflight` binds the clean Git commit/tree to every external file and tool.
2. `stage` exports only `LICENSE`, `README.md`, `pyproject.toml`, and `aureon/`
   plus the exact appliance template from the locked Git object. Worktree
   files and ignored state never enter the staging tree; conventional runtime
   secret paths and key-file suffixes are rejected.
3. `build` asks pinned mkosi to create one UEFI GPT image with an El Torito boot
   catalog, then converts those same raw bytes to a fixed VHDX using pinned
   `qemu-img`.
4. `verify` re-hashes both artifacts, runs `qemu-img check`, and can separately
   boot the VHDX (snapshot mode) and the ISO candidate (read-only optical mode)
   under QEMU/OVMF with `-nic none`. Both boots must emit the serial marker
   `AUREON_APPLIANCE_BOOTABLE_FIRSTBOOT_REQUIRED`.

Each successful or held transition is appended to a SHA-256-linked receipt
ledger. The ledger is useful tamper evidence, not a signature. An independent
host-held signing key is still required for third-party attestation.

## Required locked inputs

Copy `inputs.example.json` outside the source checkout and replace every
placeholder path, size, digest, and tool-version-output digest. The final lock
must remain outside the checkout and must name:

- a Debian Bookworm x86-64 base-tree tar or disk image containing systemd,
  Python 3.11+, `venv`, a kernel, initramfs support, and `systemd-boot-efi`;
- a pinned mkosi tools tree;
- a pip-compile-style requirements lock with exact `==` versions and a
  lowercase SHA-256 hash for every wheel;
- a wheelhouse plus a sorted `aureon.appliance.wheelhouse.v1` manifest;
- exact mkosi and qemu-img executables. The locked mkosi must accept the full
  rendered configuration in both `summary` and `cat-config`; this capability
  probe is required because the El Torito option is newer than the latest
  numbered mkosi release available when this pipeline was authored;
- qemu-system-x86_64 and immutable OVMF CODE/VARS templates for boot testing.

The base tree and toolchain are trusted computing-base inputs, not hostile
guest content. Their hashes provide identity, not trust: obtain them from an
owner-reviewed source, keep them on owner-controlled read-only storage during
the build, and independently retain their provenance/signatures. A malicious
base can forge console output or install a systemd generator before Aureon's
own attestation code runs; this pipeline does not claim to solve that problem.

The base tree must retain package-manager metadata so mkosi can consume it as a
base tree. Acquire and verify these inputs in a separately authorized,
network-capable preparation environment. The image build itself is configured
with `CacheOnly=always`, `WithNetwork=no`, `Ssh=never`, and a pinned tools tree.

Example wheelhouse manifest:

```json
{
  "schema": "aureon.appliance.wheelhouse.v1",
  "files": [
    {
      "path": "flask-3.1.2-py3-none-any.whl",
      "sha256": "replace-with-64-lowercase-hex-characters",
      "size": 123456
    }
  ]
}
```

## Commands

Use a fresh output directory outside the repository. Global options precede
the subcommand.

```bash
python -m aureon.appliance.build_pipeline \
  --repo /src/Aureon-OS \
  --profile /src/Aureon-OS/packaging/appliance/profile.json \
  --inputs /secure-build-inputs/inputs.lock.json \
  --work-dir /work/aureon-2.1.0-preflight \
  preflight

python -m aureon.appliance.build_pipeline \
  --repo /src/Aureon-OS \
  --profile /src/Aureon-OS/packaging/appliance/profile.json \
  --inputs /secure-build-inputs/inputs.lock.json \
  --work-dir /work/aureon-2.1.0 \
  build

python -m aureon.appliance.build_pipeline \
  --repo /src/Aureon-OS \
  --inputs /secure-build-inputs/inputs.lock.json \
  --work-dir /work/aureon-2.1.0 \
  verify --boot
```

The build output is:

- `artifacts/aureon-os-2.1.0.iso`: UEFI GPT/El Torito disk-image candidate;
- `artifacts/aureon-os-2.1.0.vhdx`: fixed VHDX derived from the ISO bytes;
- `artifacts/aureon-artifacts.json`: hashes and honest verification state;
- `receipts.jsonl`: ordered build receipts;
- complete mkosi/qemu-img logs with no intentional truncation.

The pipeline does not claim byte-reproducible VHDX headers. Rebuild the
canonical ISO twice in isolated roots and compare its SHA-256. Treat VHDX as a
derived transport until a VHDX-aware reproducibility audit proves otherwise.

## First boot and runtime safety

Among Aureon units, only `aureon-boot-attestation.service` and the no-shell
`aureon-firstboot-console.service` are enabled in the image. At `/dev/tty1`,
the latter requires the exact phrase `ENABLE AUREON OFFLINE CORE`; no password
or owner secret is embedded. The three core daemons remain disabled until that
hypervisor-console gate succeeds. Finalization runs after systemd presets and
rejects persistent exact, prefix, and type-wide overrides before checking
enablement state. At boot and again before approval, the running systemd
manager must report the exact `/usr/lib` fragments, no effective drop-ins, and
no prematurely active core unit. The root-owned receipt is stored outside
Aureon's writable runtime directory.

The boot attestor also checks the effective enablement state reported by the
running systemd manager. Before the console grant, the target and all three
core services must still be disabled, the two bootstrap services must be
enabled, and `getty@tty1.service` must remain masked. This closes the gap where
a runtime systemd generator could add a wants symlink without changing a unit
fragment or drop-in.

The staging rules reject `.env*`, conventional private-key files, and runtime
state; post-installation also removes SSH host keys, the random seed, and
machine ID inherited from the base. A post-build filesystem scan is still
required before claiming the whole image is secret-free, because the owner
supplies the base tree and source code can contain arbitrary text. The operator
binds to `127.0.0.1:8790`.
Trading, exchange mutations, LLM HTTP, autonomous local actions, and Soul
actions are all hard-disabled. Systemd address-family and IP policies block
remote access even if application configuration drifts.

After a VHDX passes QEMU boot verification, an owner may register it on Windows:

```powershell
& .\packaging\appliance\hyperv\Register-AureonAppliance.ps1 `
  -ManifestPath 'D:\AureonBuild\artifacts\aureon-artifacts.json' `
  -VmName 'Aureon-OS-2.1.0' `
  -VmStoragePath 'D:\Hyper-V\Aureon-OS-2.1.0.vhdx'
```

The script hash-checks the canonical artifact, copies it to the fresh
`VmStoragePath`, and attaches only that VM-owned copy. It defaults to a
disconnected Generation-2 VM with Secure Boot off and does not start it.
Enable Linux Secure Boot only after the image's signing chain is independently
validated. `-Start` additionally requires `-VerificationPath` naming the
passing `aureon-boot-verification.json` for this exact VHDX hash.

## What “verified bootable” means here

Do not call a build bootable merely because files exist. The verified state
requires all of the following:

- locked inputs and clean source preflight passed;
- ISO and VHDX hashes match the artifact manifest;
- `qemu-img check` passed;
- QEMU/OVMF emitted the exact first-boot serial marker from both the snapshot
  VHDX and the read-only El Torito optical path, immediately followed by the
  exact structured first-boot attestation, with no policy-HOLD marker and with
  networking absent;
- on Hyper-V, `Test-VHD` passed and a Generation-2 boot produced a separate
  console or event-log read-back.

Until those checks run, the manifest status remains `built_unbooted` or the
pipeline remains on HOLD. Static tests on a machine without the base image,
toolchain, or Hyper-V authority are valuable, but are not boot evidence.

See `HNC_RESEARCH_MAPPING.md` for the deliberately bounded translation from the
film-reel research into this engineering design.
