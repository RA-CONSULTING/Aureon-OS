# Aureon appliance static acceptance record — 2026-08-16

This is an **external-bootstrap** engineering receipt. It records local static
validation performed by Codex; it is not evidence that Aureon authored this
pipeline, built an image, booted itself, or operated Hyper-V.

Observed at `2026-08-16T17:21:21.3861923+01:00` on the Windows checkout rooted
at `C:\Users\user\Aureon-OS-aureon-selfbuild-20260816_132020`:

- source commit: `f5fb1916c07ac26eb7fc38c34ff2dc9bd029e21d`
- source tree: `adb85cc57284947d84520d28b8dc5472c317f9e2`
- profile SHA-256: `05d096c8d9a017da8fca1770b976dea1bbf79bcfe7791aa0a24a6cf2bc48c2ef`
- example input-lock SHA-256: `46c31e000ac92fcba7a9d0966921066ad1c06fba07615334a144fa4a760e67f1`
- focused packaging/workflow tests: 31 passed
- Ruff: passed
- POSIX shell syntax: passed for both mkosi hooks and both appliance runtime
  scripts using Git Bash `bash -n`
- PowerShell parser: passed for `Register-AureonAppliance.ps1`
- workflow YAML load: passed

The running-systemd checks were tightened during this acceptance pass. The
boot attestor and first-boot gate now require the exact expected enabled,
disabled, and masked states before owner approval, closing the case where a
generator-created wants link changes enablement without changing a managed
unit's fragment or drop-ins.

## Current outcome: HOLD

No ISO or VHDX was created. The live preflight returned 11 HOLD checks:

- the locked Git executable and nine required base/toolchain/boot files or
  directories are still placeholder Linux paths and are unavailable here;
- the host is Windows, while the mkosi build contract requires a Linux x86-64
  builder.

The Hyper-V module and `Test-VHD` command are installed, but the current
process is not elevated. The registration script correctly declares
`#Requires -RunAsAdministrator`; it was parsed only and was not executed.
Therefore there is no Hyper-V VM-registration or boot read-back evidence.

An owner-reviewed base image, locked toolchain/wheelhouse/QEMU/OVMF inputs, a
clean committed source snapshot containing the pipeline, a suitable Linux
builder, and an elevated Hyper-V handoff remain required for a verified
bootable result.
