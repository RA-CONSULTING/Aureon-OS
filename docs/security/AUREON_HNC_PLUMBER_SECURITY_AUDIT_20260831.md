# Aureon HNC, Plumber, and Magic-Star Security Evidence

Date: 2026-08-31

Checkout: `Aureon-OS-master-system-20260830_231506`

Branch: `main`

Base commit: `648d45036b60ed399b317a191ab8a60e4ada5258`

## Decision

This hardening tranche is locally validated and fail-closed. It is **not** a
certification that the full Aureon OS is impenetrable or production-ready.
No provider, trade, desktop, filesystem-mutation, self-code promotion, command,
or remote publication was authorized during this audit.

The checked-in Magic-Star profile and local OS boundary both report
`production_ready: false`. Production release remains unavailable until an
independently trusted authority service/HSM and provider read-back path exist.

## Implemented controls

- Added bounded HNC admission, metadata-only quarantine, replay rejection,
  opaque local handles, explicit burn/discard, capacity limits, and stable
  fail-closed receipts.
- Added an HNC-sealed proposal forge. It parses bounded unified diffs and cannot
  apply, import, compile, evaluate, execute, or promote generated code.
- Converted the internal self-coder to proposal-only review. Suggested tests are
  recorded but never executed; source mutation and production handover are HOLD.
- Protected Operator HTTP/MCP ingress with authentication, bounds, HNC admission,
  replay quarantine, and burn-on-HOLD semantics. Its production mutation routes
  remain unavailable.
- Made Nexus loopback-first, bearer-authenticated, origin/payload bounded, and
  HOLD-only for every command effect.
- Disabled Agent Core process, desktop-input, browser-launch, file-mutation,
  dynamic-code, notification, and unverified provider effects. Workspace reads
  reject VCS, `.env*`, credential, wallet, key, traversal, symlink-escape, and
  oversized paths. Audit logs retain outcome metadata, not tool plaintext.
- Removed Samuel's implicit QueenHiveMind, King, Lyra, and ThoughtBus attachment;
  removed its process/socket probes; repaired its direct-script entrypoint; and
  made all status and capability language observation-only.
- Prevented Face rule/parser routes from bypassing its exact tool allowlist and
  removed false live, sentient, desktop, provider, and trading claims.
- Removed runtime pickle loading/writing from the whale trainer and harmonic seed
  cache. The seed cache now uses bounded, exact-schema canonical JSON.
- Made all dispatcher acknowledgements non-authoritative. A callback cannot
  self-certify `EXECUTED`; the outcome stays pending reconciliation until an
  independent provider read-back exists.
- Demonstrated that an in-process Python authorization token can be introspected,
  then ensured that even the forged exact-plan object cannot release a trade.
  The checked-in path remains HOLD pending a separate production authority.

## Test evidence

- Combined offline/security regression: **602 passed, 2 skipped**.
- Economic focused hostile suites: **68 passed, 1 skipped**.
- Economic census suite: **66 passed**.
- Whole-OS census contract: **15 passed**.
- Nexus Node security contract: **5 passed**.
- MyPy: no issues in `os_protection.py`, `proposal_forge.py`, or
  `operator_server.py`.
- Ruff `E9,F`, Python byte-compilation, and `git diff --check`: passed.
- Diff secret-pattern scan: zero matches.
- Static deserialization scan: no `pickle.load`, `joblib.load`, `torch.load`, or
  unsafe `yaml.load` call in `aureon/`.

The two combined-suite skips are optional Socket.IO runtime tests on this host.
Socket/DNS attempts reported by `pytest-socket` were denied as intended.

## HNC benchmark

Schema: `aureon.hnc-crypto-boundary-benchmark.v1`

Mode: offline, performance-only, not a security proof

| Payload | Seal mean | Decode mean | Seal throughput | Decode throughput |
|---:|---:|---:|---:|---:|
| 1 KiB | 6.117 ms | 1.356 ms | 163.48 ops/s | 737.73 ops/s |
| 64 KiB | 8.215 ms | 3.946 ms | 7.608 MiB/s | 15.839 MiB/s |
| 1 MiB | 56.485 ms | 53.929 ms | 17.704 MiB/s | 18.543 MiB/s |

All exact round trips and ciphertext-tamper negative controls passed. The 4 KiB
OS admit-and-burn boundary averaged 8.700 ms / 114.94 ops/s and finished with
zero active handles and zero active ingress bytes.

## Census receipts

Economic mutation census:

- Source files: 5,098
- Detected/classified: 1,618 / 1,618
- Unknown/stale/parse errors: 0 / 0 / 0
- Blockers: 1,247
- `inventory_aligned: true`
- `certified_no_bypass: false`
- Inventory SHA-256:
  `521d924ba02c64cd30d6121e658525613626045014012c8149b1d1fc3e576ec6`

Whole-OS high-risk boundary census:

- Source files: 5,098 (4,170 Python; 928 JavaScript/TypeScript)
- Detected/classified: 6,874 / 6,874
- Parse errors: 0
- Protected by a complete production-release proof: 0
- Remaining blockers: 6,874
- `certified_full_os_protection: false`
- Inventory SHA-256:
  `72e710a31c16903e633814d138f899f5650d42677527ce0b71fffd852736215c`

## Remaining release blockers

- LocalProposalForge is tested and exported but is not yet the self-coder's
  runtime proposal path. The current self-coder is contained, but HNC proposal
  sealing is not end-to-end integrated.
- Operator and Nexus mutation/command surfaces intentionally return HOLD because
  no production Magic-Star release implementation exists.
- No independently deployed authority service/HSM or independent provider
  reconciliation path exists.
- The repository still contains 6,874 high-risk routes without a complete
  structural HNC-to-custody-to-registered-release proof, including 1,247
  economic mutation blockers.
- GitHub publication remains owner-controlled and was not performed by this
  audit.
