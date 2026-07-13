# Aureon HNC Singularity Vault

Generated: `2026-05-14T19:57:09.523893+00:00`

This note is the Obsidian key-holder map. It stores public hashes, packet summaries, and locknote instructions only. It must never hold raw agent keys.

## Repo Root

- `.`

## Singularity Root

- Files wrapped: `7144`
- Skipped by safety profile: `499`
- Root SHA-256: `9a38195739f007d952171eb21da72dc7863b868c1ee7983653fa6f658c0213a6`

## Swarm Locknote Policy

- One agent key alone cannot decode the sealed packet.
- Any valid two-agent pair can unite their locknotes and decode.
- Agent keys belong in Windows Credential Manager or another OS secret store, not in this vault note.
- The live repo is not encrypted in place; this is a sealed snapshot/wrapper so Aureon keeps running.

## Sealed Packet

- Packet SHA-256: `60d560ddbc26c909eab5b4a53ec3487eec63d723a640e101dc3fc78d85e3e49d`
- HNC alignment SHA-256: `b0ad8bc9d8aa7f90bbe0b43b6fa40aa50a19220ae8d1f70df02a148df4247236`
- Fragment count: `68102`
- Swarm breaker passed: `True`

## Reassembly Flow

1. Load the public singularity report JSON.
2. Gather the required two agent keys from OS secret storage.
3. Reassemble all temporal fragments.
4. Verify packet hash, HNC geometry, locknotes, and AAD.
5. Decode the archive into a quarantine/recovery directory.
