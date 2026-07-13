# Aureon HNC Symbolic Route Seal

Generated: `2026-05-14T20:00:43.972800+00:00`

## Summary

- Status: `symbolic_route_seal_ready`
- Catalogs present: `5`
- Symbol count: `114`
- Sample routes valid: `True`
- Tamper effect: route changes alter the HNC alignment hash and packet hash before decode

## Security Boundary

- Role: authenticated symbolic packet metadata
- Not a cipher: `True`
- Not a secret store: `True`
- Does not replace: AES-GCM, HKDF, DPAPI, Windows Credential Manager, KMS, HSM, or OS permissions

## Sample Routes

### `repo:singularity_vault`

- Valid: `True`
- Route seal SHA-256: `261c5a51589d9e6249e294f9efa0e85e4cfda5ec7d5498d47df0364b480ef8e8`
- Rune: `Jera`
- Auris symbol: `∞`
- Threshold layer: `threshold_people_crossing_from_observation_to_authenticated_action`

### `env:exchange_credential_packet`

- Valid: `True`
- Route seal SHA-256: `e0b4194d1f415966923599ba9f3378c2cffeb0b13b2c54b79189a375637c6ce4`
- Rune: `Fehu`
- Auris symbol: `⭐`
- Threshold layer: `threshold_people_crossing_from_observation_to_authenticated_action`

### `trading:decision_route`

- Valid: `True`
- Route seal SHA-256: `656f5945e295259a4e61cecffdd2704db223cc5a923b6423b79b512433336696`
- Rune: `Nauthiz`
- Auris symbol: `◊`
- Threshold layer: `threshold_people_crossing_from_observation_to_authenticated_action`
