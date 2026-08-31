# Plumber Magic Star v0.2 Validation Record — 2026-08-31

Status: `LAB-VALIDATED`; production promotion remains `HOLD`

Repository parent: `2359e25460d5eaf0864d39fea7912c7b96e7b921`

Baseline tag: `plumber-baseline-hncqp-v1`
Implementation branch: `feature/plumber-magic-star-v02-20260831`

## Outcome

The repository now contains the complete mandatory same-process v0.2
laboratory path described by the reconciled working order and Magic Star
profile:

```text
retained HNC carrier
  -> source-signed encrypted v0.2 packet
  -> verifier-issued recipient challenge and proof
  -> EPAS precondition
  -> existing v0 signed Heart receipt and v0.2 Heart bridge
  -> five explicit APPROVE Star points, fixed route and Rainbow
  -> final Star seal
  -> seven signed organ receipts and release proof
  -> continuity and authorization snapshots
  -> five role-specific permits and custody authorization
  -> one-use state and EPAS reservation
  -> registered purpose-limited laboratory handler
  -> pre-consume-verified signed result object
  -> state and EPAS read-back consistency validation
```

The source profile commitment remains
`8a263a1af1067fb997eefeeff4c2beec43a8fad83bab9338a1b5a2cc8c0d9935`.
The implemented control profile, including the mandatory Heart-receipt bridge
and point verdict, is
`9e9921fecf27ff9fb103fcf181d5bcf0b3ac5fc66fa6204a1b92252c1f00121e`.
The canonical Rainbow source commitment is
`d1ee15b84a2ec69b7ca4807e3ddfabadbb50aa57ab424b9ef587410d102846a4`.

## Source reconciliation

The Drive download was retained in a dated local source cache outside the
repository. Raw cloud resource identifiers and the user-specific cache path
are intentionally omitted from this public record.

| Source | SHA-256 | Disposition |
|---|---|---|
| `Aureon_Plumber_Full_Working_Order.pdf` | `3d69c14c171dc32e4fdd7019d5bf2d00c1a8d1d6a2b6abea3c594908240bdb45` | Controlling working order |
| `AUREON_PLUMBER_MAGIC_STAR_V0_2_PROFILE.md` | `bc1c7f96a2c68f92985b1b4daa2025f9581095403d104f9d6e9151236461b204` | v0.2 extension profile |
| `AUREON_PLUMBER_MAGIC_STAR_V0_2_PROFILE-1.md` | same as profile | Exact duplicate; not treated as a second source |
| `AUREON_PLUMBER_MAGIC_STAR_V0_2_ATTACK_REPORT.md` | `1eebd86c767adaa7f3be96677219179e5704b1473cec176249e3425ce62960ca` | Historic claimed evidence; used as an attack checklist only |
| `AUREON_PLUMBER_MAGIC_STAR_V0_2_ATTACK_REPORT-1.md` | same as report | Exact duplicate; not treated as a second result |

No implementation archive was present in the Drive set or the inspected
Plumber-named remote branches. The external report's historic `151`, `933` and
`39` pass counts were not inherited or represented as current evidence.

## Current verification

All commands ran with live/provider/trading actions disabled, import side
effects suppressed, pytest sockets blocked and cache disabled.

| Gate | Current result |
|---|---|
| Magic Star v0.2 protocol and hostile-path files | `128 passed in 8.68s` |
| Complete `tests/plumber` plus workflow contract | `177 passed in 8.47s`; additional repeats in `8.60s`, `8.74s` and independently `8.92s` |
| Retained HNC, field, coherence, Heart and unified baseline | `113 passed in 23.45s` |
| Optimized-interpreter authorization and boundary invariants | `21 passed in 3.05s` |
| SaaS taxonomy integration after registering `plumber` under security | `17 passed in 66.13s` |
| SaaS capability roll-up after the same registration fix | `12 passed, 1 warning in 60.47s` |
| Strict typing | `mypy --strict aureon/plumber`, clean across 25 modules |
| Static checks | `ruff check aureon/plumber aureon/saas/domains.py tests/plumber tests/test_plumber_ci_workflow_contract.py`, clean |
| Bytecode compilation | `python -m compileall -q aureon/plumber aureon/saas/domains.py tests/plumber`, clean |
| Synthetic retained-HNC breaker | seven tamper cases rejected; laboratory metadata only |

The no-exclusion repository compatibility snapshot collected 8,343 tests and
completed with `8074 passed, 177 failed, 91 errors, 1 skipped, 88 warnings in
5828.66s (1:37:08)`. Eight failures were attributable to this branch: four
SaaS catalog/coverage checks and four capability-demo roll-ups initially
reported the new `plumber` package as uncategorized. Registering it under the
`security` product domain repaired that single cause; the exact reruns passed
all 17 catalog/coverage tests and all 12 capability-demo tests. Every collected
Plumber test and the branch-adjacent workflow, retained HNC, Heart, Coherence
and Unified Contract tests passed.

No other failing file referenced or imported Plumber. The remaining broad-run
failures and setup errors were outside the changed surface and included a
shared missing investor-copy artifact, missing design-source fixtures,
socket-blocked legacy integration expectations, unavailable Windows DPAPI and
strict-offline/live-state expectation mismatches. This snapshot is preserved
as compatibility evidence; it is not represented as a green repository-wide
test result.

## GitHub synchronization read-back

The reviewed implementation commit
`5b207dde3d2461b9c82212c25b33ef0842921c0c` was fast-forwarded to GitHub
`main` from parent `2359e25460d5eaf0864d39fea7912c7b96e7b921` without force.
The remote annotated tag `plumber-baseline-hncqp-v1` has tag-object commitment
`5e0c8fce778ce76a73598813444a6b7d28f44c6d` and peels to that exact parent.

GitHub created [Plumber Security Contract run 33350608176](https://github.com/RA-CONSULTING/Aureon-OS/actions/runs/33350608176)
for the implementation commit, but both matrix jobs failed before a runner or
any workflow step started. GitHub's check annotation attributes this to an
account billing lock. This is a provider-level execution blocker, not a hosted
test result; the record therefore does not claim that GitHub CI passed.

The final focused gate covers the following v0 foundation attacks and joins:

- only an engine-issued gate bound to one exact inspection and its exact
  evidence set is executable; the inspection and gate are both one-use;
- execution-time expiry and clock rollback are denied, and the gate's lifetime
  is the same bounded window as its underlying evidence;
- temporal anchor reservation atomically joins the prior state, monotonic
  counter, nonce/replay token, canonical field and runtime commitments, and
  rejects replay or rewrapping;
- the Spore manifest commits its stream identity and exactly joins packet,
  temporal epoch, challenge, ciphertext commitment and ciphertext size;
- sympathetic identity is recomputed and its hardware and operator
  commitments are pinned by the trust policy;
- field, Heart, Conscience and governance receipt authorities require distinct
  authority identifiers and keys; and
- retained HNC binding rejects malformed base64url or any nonce that does not
  decode to exactly 12 bytes.

The v0.2 hostile-path coverage includes every seven-organ omission, organ
reorder, every five-permit omission, three/four-of-five threshold rejection,
signed point VETO, packet/channel/Star/authorization substitution, recipient
replay, v0/v0.2 parser separation, final live-state change, capability-policy
substitution across registered capabilities, expiry during capability
execution, and a single checked time sample shared by the last expiry decision
and receipt issuance. It also covers sanitized handler failures without
returning the handler's exception payload or traceback cause, receipt-signer
failure and corruption, EPAS predecessor/concurrency attacks, recursive
forbidden output, deep aggregate mutation and absence of public raw-share
entry points.

The final receipt is signature- and payload-verified before release state can
be consumed or EPAS can record `CONSUMED`. A corrupt or unavailable receipt
signer therefore leaves release state `DENIED` and records a denial lineage
transition instead of a false successful terminal state.

## Assurance boundary

This result validates a deterministic local protocol path, not containment or
production security:

- the registered handler receives plaintext in the same Python process and
  must be a pure, deterministic, non-side-effecting fixture;
- handler effects cannot be rolled back by a later denial;
- capability/runtime measurements are declared commitments, not hardware
  attestation or measured executable identity;
- all five XOR shares, authority keys, state and plaintext are co-resident;
- recipient, temporal/replay, release and EPAS stores are in-memory and
  rollbackable; v0 inspection/execution time is supplied by the caller and
  v0.2 time comes from an injected process-local callable;
- v0 gate expiry is exactly the aggregate evidence-expiry window, not an
  independently shorter service-issued lease;
- result allowlists and direct canary checks do not prevent transformed or
  covert-channel exfiltration;
- handler-failure sanitization catches `BaseException`, so process-control
  interrupts such as `KeyboardInterrupt` and `SystemExit` are swallowed and
  converted to a stable laboratory denial;
- direct custody pops its one-use material before calling the handler; the
  outer release boundary, not direct custody, owns post-pop terminal-state
  handling;
- Python does not guarantee erasure of immutable secret copies;
- release state is consumed before EPAS finalization, so receipt,
  release-state and EPAS transitions are neither atomic nor one durable
  distributed transaction;
- legacy laboratory APIs remain available, so organism-wide exclusive v0.2
  routing is not established; and
- there is no production CLI, service endpoint, HSM/KMS/enclave adapter,
  hardware identity provider or independently administered live signer.

Production promotion still requires isolated measured capability execution,
non-exporting independent custody, durable rollback-resistant multi-host
state, hardware-rooted identity and time, verifier-owned live adapters,
exclusive routing, operational key ceremonies and independent cryptographic
and deployment review.
