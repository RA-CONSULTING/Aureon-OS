# Aureon HNC Packet Security Comparison

Generated: `2026-05-14T19:56:14.337040+00:00`

## Summary

- Current HNC packet score: `78/100`
- Current HNC swarm score: `86/100`
- Rating: `strong_local_envelope_when_master_key_is_protected`
- Breaker checks passed: `True`
- Swarm breaker checks passed: `True`
- Symbolic route bound to packets: `True`
- Symbolic route catalogs present: `5`
- Symbolic route symbols indexed: `114`
- Main weakness: `operator-managed key custody`
- Top recommendation: store HNC/swarm agent keys in Windows Credential Manager or another OS secret store, keep only hncqp1 packets and public locknotes in .env/state, and require two agent keys for high-value decode

## Comparison

| Method | Score | Confidentiality | Integrity | Key management | Aureon fit |
| --- | ---: | --- | --- | --- | --- |
| Cloud KMS / HSM-backed envelope encryption | 94 | strong with hardware or managed key custody | managed audit and policy controls | centralized, rotatable, auditable | best production/server target when multiple users or hosted SaaS are involved |
| OS keychain / Windows Credential Manager | 88 | OS-protected secret storage | OS-managed | user/session/OS-managed | best next local upgrade: store the HNC master key outside .env |
| Aureon HNC swarm two-way locknote packet v1 | 86 | AES-GCM payload secrecy with two-agent key-share reconstruction | packet hash, AES-GCM authentication, locknote authentication, HNC geometry, and symbolic route contract | two independent agent master keys required per decode | best local HNC design for high-value secrets because a single agent/key cannot decode alone |
| Generic AES-GCM envelope encryption | 82 | AES-GCM payload secrecy | AES-GCM authentication | operator-managed or app-managed | excellent baseline; HNC packet adds Aureon-specific authenticated context |
| Aureon HNC harmonic packet v1 | 78 | AES-GCM payload secrecy | packet hash, AES-GCM authentication, HNC geometry, and symbolic route seal | operator-managed AUREON_HNC_PACKET_MASTER_KEY | strong local upgrade for .env credential-at-rest protection and HNC decode proof |
| Post-quantum / hybrid public-key envelope | 76 | depends on selected standardized/hybrid scheme | scheme dependent | more complex | future transport upgrade; not required for local symmetric .env protection today |
| AES-CBC without separate authentication | 46 | medium when implemented correctly | weak unless paired with a MAC | operator-managed | not preferred because tamper detection is easy to get wrong |
| SHA-256 hash only | 24 | one-way fingerprint only | detects equality when original is known | none | good for packet fingerprints, not for storing API keys Aureon must reuse |
| Base64/encoding only | 12 | none | none | none | not acceptable for real credential protection |
| Plaintext .env values | 8 | none | none | none | bootstrap only; acceptable for local dev, weak for live credentials |

## Security Boundary

- HNC geometry role: authenticated decode contract and evidence context
- Symbolic route role: authenticated rune/star/Maeshowe context seal; proves route intent and catalog provenance but is not secret key material
- Cryptographic secret role: AES-GCM payload secrecy under a master key or two-agent swarm key-share reconstruction
- Swarm locknote role: split-knowledge dual-control gate where one agent key cannot decode alone
- HNC does not replace: key custody, OS permissions, KMS/HSM policy, endpoint authentication, and process memory protection

## Next Upgrades

- Move AUREON_HNC_PACKET_MASTER_KEY and swarm agent keys out of .env and into Windows Credential Manager or an equivalent local secret store.
- Use two-way swarm locknotes for high-value credentials and keep single-master HNC packets for lower-risk local bootstrap values.
- Add key rotation: decrypt old hncqp1 tokens, re-encrypt with a new master key, and write a rotation evidence report.
- Add optional KMS/HSM envelope mode for hosted or multi-user deployments.
- Keep breaker checks in CI so tampered geometry, fragments, or AAD never decode.
- Keep the symbolic route catalogs under audit so rune/star route seals stay reproducible and evidence-linked.

## References

- [NIST SP 800-38D: Galois/Counter Mode](https://nvlpubs.nist.gov/nistpubs/legacy/sp/nistspecialpublication800-38d.pdf) - AES-GCM authenticated encryption expectations
- [RFC 5869: HMAC-based Extract-and-Expand Key Derivation Function](https://datatracker.ietf.org/doc/html/rfc5869) - HKDF-SHA256 key derivation basis
- [NIST FIPS 180-4: Secure Hash Standard](https://csrc.nist.gov/pubs/fips/180-4/upd1/final) - SHA-256 digest/fingerprint basis
- [NIST SP 800-57 Part 1 Rev. 5: Recommendation for Key Management](https://csrc.nist.gov/pubs/sp/800/57/pt1/r5/final) - split knowledge, dual control, and key custody basis
