# Aureon Master System Hardening Supplement

Date: 2026-08-31

Checkout: `Aureon-OS-master-system-20260830_231506`

Branch: `main`

Local HEAD: `6ca7af63393655223be4749e7cd308a044239ed8`

Current GitHub `main` read-back: `957e007c2e15d936168c01f93fa4a7d2e8889176`

## Decision

**HOLD — the current hardening tranche is locally verified and fail-closed,
but the complete Aureon OS is not certified as fully protected or
production-ready.**

This supplement records the final current-working-tree verification after the
additional HNC, Plumber, Magic Star, Vault, voice, capability-demo, credential,
and import-safety hardening. Its current counts and benchmark measurements
supersede older same-day working-tree figures where they differ. It does not
alter historical commit or provider receipts.

No live provider, trade, browser, desktop-input, external message, deployment,
GitHub push, code-promotion, credential write, or production release was
executed during this gate.

## Self-coder privacy and launcher-authority correction

A hostile review found that the first proposal bridge was not correct end to
end. Although the final diff was HNC-sealed, raw goals, source, and model answers
could first reach the hosted Ollama route and the ordinary Hive/Mycelia JSONL
traces. The integration also labelled an in-memory opaque handle as a created,
pending-review proposal even though no supported recovery handle survived the
function return. Those claims have been withdrawn.

The corrected local boundary now:

- preflights a valid HNC key before workforce construction or inference;
- requires a literal loopback Ollama client endpoint at port 11434, disables
  ambient and per-request proxies, rejects redirects, and never configures the
  sensitive client to send a prompt to a hosted endpoint;
- requires a truth-gated commitment-only Hive/Mycelia propagator whose bus and
  trace payloads contain the answer digest, never the answer;
- constructs the default confidential path only from an explicit typed truth
  authority bundle and exact `LocalHncAurisEvidenceResolver`,
  `ReceiptBackedTenNineOneTruthGate`, and
  `CommitmentOnlyHiveMyceliaPropagator` components. A missing bundle HOLDs as
  `authenticated_self_coder_truth_authority_bundle_required` before any brain
  adapter, while malicious lookalike outer paths, resolvers, and truth gates are
  rejected before callbacks;
- forbids plaintext decision observers on the sensitive coding path;
- reports the current forge result only as a transient HNC seal with
  `proposal_recoverable=false`, `proposal_reviewable=false`, and
  `pending_senior_review=false`, then explicitly burns the forge handle, OS
  admission, and mutable packet-key copy because no durable review vault exists;
- disables the senior-review adapter and self-run promotion route until a
  durable authenticated ciphertext proposal vault exists;
- routes the raw self-coder goal only to the guarded self-coder runner. Other
  self-run tasks receive a digest-only support prompt, and outer state, audit,
  public, bridge, exception, status, summary, and output-path fields are
  schema-filtered so a raw-goal canary cannot persist. Untrusted positive
  authority/effect booleans are clamped to false rather than forwarded;
- treats every locally recomputed JSON self-coder receipt as unattested generic
  HOLD rather than inferring that an HNC seal or reviewable proposal existed,
  bumps the current patch/self-coder receipt schemas to v2 while legacy v1 JSON
  remains unattested, and rechecks the evidence file before every multi-cycle
  patch pass; and
- prevents both the primary live/production launcher and the independent
  production wrapper from converting an evidence-only ACCEPT/exit code into
  `Start-Process` authority. `ValidateOnly` completes after its validator Python
  child without starting supervised/runtime services; `WhatIf` starts no
  processes.

This correction does not prove that a loopback model server retains no prompt
history. The receipt explicitly records that local-model non-retention is not
verified. The default autonomous self-coder therefore HOLDs before model use
when no authenticated authority bundle is supplied, and its default switchboard
still cannot issue the required local HNC-protected provider passport. The
executable local path remains a test/injected transient-seal experiment, not a
durable review or release system.

## Controls verified in this tranche

- Public Vault UI ingress is loopback-only, authenticated, bounded, replay
  checked, HNC admitted, and burned. Body-bearing, unknown, command, and effect
  routes remain on exact release HOLD.
- Integrated Cognitive System, voice/runtime owners, self-dialogue, goal/action
  dispatch, persona mutation, feedback, self-enhancement, public live scripts,
  and the stress harness now stop at explicit preflight HOLD before runtime
  ownership, subscriptions, threads, providers, subprocesses, or effects.
- Capability results have an exact signed/registered ABI. The released local
  profile currently accepts exact `bool` values only; byte vectors, integers,
  strings, lists, nested structures, and reversible plaintext encodings are
  denied.
- OS admission preflights the exact Magic Star inner carrier capacity before
  issuing an opaque handle. Predictably oversized carriers quarantine without
  an admit-then-burn failure.
- Plumber base64url decoding is bounded before decode. Spore transport caps
  total ciphertext, per-fragment bytes, and fragment count; reassembly checks
  encoded syntax and aggregate predicted size before any second decode.
- HNC geometry requires the exact bounded geometry and node schemas, finite
  positive values, nine meaningful nodes, distinct node names, and the pinned
  SHA alias. Nested geometry is snapshotted to prevent alias poisoning.
- HNC credential evidence is fixed-shape metadata derived from a valid packet.
  The environment key must match both authenticated purpose and operator AAD.
  Tokens and plaintext are omitted, and the filesystem evidence writer HOLDs
  before path inspection or creation.
- Credential packetization has no plaintext fallback. Public credential writes
  HOLD before filesystem, process-environment, intent, backup, or evidence
  mutation. Public credential-status reads also HOLD before inspecting sources.
  CORS no longer grants non-local origins and loopback origins use parsed exact
  host matching rather than vulnerable string prefixes.
- Committed capability/benchmark reports are marked `STALE_SUPERSEDED`, cannot
  promote a release, have bounded reads, require exact boolean result rows, and
  keep `production_ready` and current-effect claims false.
- Plumber v0.3 now has an immutable, canonical, metadata-only release command;
  four distinct pinned Ed25519 review/dispatch/executor/receipt authorities; exact
  signed joins across packet, admission, effect, capability, runtime, nonce,
  deadline, result, and provider read-back commitments; and bounded canonical
  wire decoders. Its reference coordinator accepts no plaintext or in-process
  capability callback.
- The v0.3 SQLite reference ledger atomically claims unique effect IDs and
  nonces with exact schema/index/trigger validation, `WAL`, `synchronous=FULL`,
  foreign keys, and durability read-back on every open. `PENDING_DISPATCH`
  reservations survive signer failure and renew with a fresh, atomically fenced
  nonce after expiry; `EVIDENCED` state survives receipt-signer failure without
  redispatching the executor. Receipt identity and content are canonical for one
  executor-evidence commitment, and the ledger accepts a receipt only after an
  idempotent signer read-back. It returns a fully reauthenticated terminal chain
  after restart and never retries an uncertain remote effect. A stale signed
  dispatch remains unresolved pending authenticated executor/provider
  reconciliation; it is never converted into a fabricated terminal denial.

## V0.4 local Python runtime audit reference

The new `aureon.plumber.runtime_guard_v04` candidate is an explicitly
installed, process-local CPython audit reference. Importing `aureon.plumber`
does not install the hook or perform an external/mutating action. Once installed
in a disposable interpreter, the hook defaults to denial for **110 declared
audit events** covering post-install file opens, filesystem/config mutation,
process/thread creation, native loading, dynamic code/deserialization,
network/protocol calls, SQLite connection/loading, and registry mutation.

Only **one** event is manifest-authorizable: exact built-in-string,
absolute-path `os.mkdir(path, mode, dir_fd=-1)`. The other **109** events are
deny-only. Raw `open` is deny-only because CPython does not audit subsequent
file-handle writes. Directory-FD-bearing mutation forms are not authorized, so
an unaudited `dup2` cannot redirect a signed rule through this reference API.

The local release join requires current signed v0.3 command, review, and
dispatch material; exact effect/capability/runtime/manifest commitments; a
registered handler; one-use dispatch, command, command-ID, effect-ID, and
request-nonce identities; serialized execution; and complete consumption of
the bounded audit-event rule. Replay memory is bounded and consumed before
handler-controlled work. Caught denials on the owner thread, copied context, or
a pre-existing worker thread invalidate the claim. A second concurrent release
is rejected before its identity is consumed.

Denied event metadata is bounded before hashing and sent through the exact
`LocalOSProtectionBoundary` as commitment-only HNC quarantine evidence. The
recorder reserves capacity atomically, deep-copies nested evidence, and refuses
installation unless the underlying boundary can hold the preflight probe plus
every configured receipt. A vetoed/unproven installation permanently poisons
that process-level guard slot.

The adversarial tests cover signed exact success, write/append and raw-open
denial, malicious `str` path-subclass collision attempts, dispatch and release
identity replay, copied-context escape, pre-existing-worker denials, concurrent
release, post-install thread/process/socket/config/file-read denial, audit-hook
injection, synthetic audit events, recorder concurrency/capacity, deep-copy
integrity, and terminal installation veto. Current candidate hashes are:

- runtime-guard source SHA-256:
  `3e53b98723ba7430a256bca03ad2db45e5cde029fbb1b38c2118288ce1e70368`
- runtime-guard-test SHA-256:
  `3b86fe91f1cc3f23c6b3e0e719dfa66c994f65e179e511f4a856e22a1244fd59`

This is not system-wide or production enforcement. No Aureon bootstrap installs
it. A Python hook cannot attest event origin, handler/runtime measurement,
effect success, provider read-back, interpreter/native isolation, symlink or
reparse-point identity, pre-opened descriptors/sockets, existing SQLite/native
objects, memory maps, direct Python-object mutation, inbound socket payloads,
JavaScript, or alternate interpreters. Resource commitments are deterministic
and unkeyed, so they are pseudonymous rather than confidential. Synthetic
`sys.audit` calls can consume a permitted event or exhaust bounded evidence.
Every public receipt therefore keeps the corresponding attestation fields and
`production_ready` false. Native pre-interpreter installation, OS isolation,
exclusive gateway ingress, durable monotonic replay/evidence storage, measured
out-of-process handlers, and provider read-back remain release blockers.

## Final offline verification

Most earlier audit commands used audit/offline flags, disabled import side
effects and LLM HTTP, blocked pytest sockets, and disabled the pytest cache where
relevant. The 40 strict-transport tests deliberately enabled the HTTP code path
against an injected fake session so redirects and proxies could be exercised;
they made no real network request.

| Gate | Result |
|---|---:|
| Earlier changed-test snapshot (56-file manifest was not retained) | **556 passed at that time; not current full coverage** |
| Adjacent HNC/Plumber attack and release regressions | **39 passed** |
| Post-format/import/credential/HNC focused rerun with warnings as errors | **86 passed** |
| Independent HNC/Plumber review suite | **184 passed** |
| Independent census-inclusive custody/release compatibility suite | **93 passed** |
| Plumber strict typing | **27 source files, no issues** |
| Hardened-scope Ruff | **all checks passed** |
| Earlier changed-Python Ruff snapshot (`E9,F63,F7,F82`; manifest not retained) | **117 files passed at that time** |
| Earlier changed-Python byte-compilation snapshot (manifest not retained) | **117 files passed at that time** |
| `git diff --check` | **passed** |
| Git object integrity (`git fsck --no-dangling --full`) | **passed** |
| Current dirty-tree Python inventory | **142 changed/untracked Python files; 69 are tests; 147 total status entries; not fully rerun** |
| Self-coder privacy, strict loopback transport, thought-path, workforce, Plumber, self-run, and launcher authority addendum | **227 passed; 11 adjacent truth-gate tests also passed (238 combined)** |
| Shared-adapter adjacent compatibility sweep | **23 passed; 1 unrelated static-inventory fixture failed because `flameborn/dist-workers/app.js` is absent** |
| Corrected proposal/entrypoint/transport/self-run focused MyPy | **9 source files, no issues** |
| Corrected Python scope Ruff (`E9,F`) and byte compilation | **passed** |
| Primary and wrapper PowerShell parser checks | **passed** |
| Confidential self-coder composition and adversarial type checks | **81 passed** |
| V0.3 durable broker, restart/crash, concurrency, wire, and package-surface checks | **47 passed** |
| V0.4 runtime guard adversarial checks plus package import/public surface | **9 passed** |
| Complete current Plumber package sweep, including V0.4 | **299 passed** |
| Current Plumber V0/V0.2/V0.3 package and attack sweep | **175 passed** |
| HNC crypto/schema/transport attack regressions | **67 passed** |
| OS-protection boundary census regressions | **19 passed** |
| OS-protection plus economic-boundary census regressions | **85 passed; one pre-existing SyntaxWarning** |
| V0.3 broker MyPy, Ruff (`E9,F`), and byte compilation | **passed** |
| Current confidential self-coder + Plumber + HNC sweep, excluding census | **346 passed** |
| Consolidated current self-coder + Plumber + HNC + census suite | **365 passed; one pre-existing SyntaxWarning** |

The nine-file MyPy row used the repository's default MyPy configuration (not
`--strict`) and exactly these files: `llm_adapter.py`,
`aureon_internal_coding_workforce.py`, `aureon_internal_patch_loop.py`,
`aureon_internal_self_coder.py`, `aureon_self_run_coding_task.py`,
`aureon_autonomous_self_run_loop.py`, `aureon_truth_gated_ten_nine_one.py`,
`os_protection.py`, and `proposal_forge.py`. It is not a claim that the adjacent
thought-path module or whole repository is type-clean.

The strict transport subset contributes **40 passing tests**. It covers literal
IPv4/IPv6 loopback admission, ambient and per-request proxy denial,
direct-loopback success, mutated/external request-origin denial, external
200-response-origin denial, and 301/302/303/307/308 rejection across native
prompt, OpenAI-compatible prompt, stream, health-listing, and model-probe paths.
Adjacent workforce tests cover root-to-`/v1` endpoint canonicalization and one
late non-strict adapter among otherwise strict runtimes. The adapter disables
environment proxy discovery and validates the response origin. This proves the
client boundary's audited current call paths; a source ratchet is not proof
against a future networking alias or new client. It also does not attest the
downstream behavior or retention policy of the local model server.

The first frozen run emitted four warnings when legacy probes attempted
socket/DNS access; `pytest-socket` denied those calls. The three affected
checks subsequently passed with warnings treated as errors after replacing
deprecated naive UTC calls. One unrelated repository file still emits a
`SyntaxWarning` for an invalid escape sequence during the census.

The dedicated HNC module still has **54 strict MyPy errors**. The new geometry
code introduces no strict errors, but the older module-wide typing debt remains
a release blocker; it is not represented as type-clean.

The first broad final sweep exposed 15 stale patch-loop test fixtures that still
used lookalike test resolver/truth-gate types. Production correctly rejected
them before any model call. The test-only fixture now uses the existing exact
confidential composition helper; all 24 patch-loop tests pass, and an
independent read-only review confirmed that no production exact-type gate was
weakened.

The independently reviewed v0.3 candidate was pinned as:

- broker source SHA-256:
  `bfbf8638d5d896c20f6d3152a6d2ce6b8d127aa134d9f5849181c7ea334cbea7`
- broker-test SHA-256:
  `6daf84021fd532f3f7302533d462895e71d9af26c3c7d1763acfe06d257d0a5c`

The reviewer reproduced and then verified fixes for Windows SQLite handle
release, expired unsigned-dispatch recovery, late-response fencing, and
receipt-service idempotency/read-back. Its final verdict was suitable as a
fail-closed local reference, not production-ready.

## HNC security/encryption benchmark

Schema: `aureon.hnc-crypto-boundary-benchmark.v1`

Mode: offline performance measurement only; not a security proof

| Payload | Seal mean | Decode mean | Seal throughput | Decode throughput |
|---:|---:|---:|---:|---:|
| 1 KiB | 4.799 ms | 1.029 ms | 208.36 ops/s | 971.47 ops/s |
| 64 KiB | 6.803 ms | 3.099 ms | 9.187 MiB/s | 20.169 MiB/s |
| 1 MiB | 48.010 ms | 44.240 ms | 20.829 MiB/s | 22.604 MiB/s |

Exact round trips passed at every size. Ciphertext tampering was rejected at
every size and all benchmark negative controls passed. The 4 KiB OS
admit-and-burn boundary averaged **9.294 ms / 107.60 operations per second**
and ended with zero active handles and zero active ingress bytes.

Runtime versions used for this measurement:

- Python `3.12.0`
- `cryptography 46.0.3`
- cryptography backend OpenSSL `3.5.4`
- Python `ssl` OpenSSL `3.0.11`

Fresh post-v0.3 in-memory confirmation (medians, not means) also completed with
exact round trips and no network or provider use:

| Payload | Iterations | Seal median | Validate median | Decode median | Seal throughput | Decode throughput |
|---:|---:|---:|---:|---:|---:|---:|
| 1 KiB | 100 | 4.605 ms | 0.706 ms | 0.965 ms | 0.21 MiB/s | 1.01 MiB/s |
| 64 KiB | 30 | 6.477 ms | 1.852 ms | 2.887 ms | 9.65 MiB/s | 21.65 MiB/s |
| 1 MiB | 5 | 44.230 ms | 26.457 ms | 42.723 ms | 22.61 MiB/s | 23.41 MiB/s |

These timings measure local AES-GCM packet build/contract validation/decode
overhead only. They do not establish cryptographic strength, remote custody,
hardware isolation, or production throughput.

## Stable whole-repository protection census

- Source files scanned: **5,113** (**4,185 Python; 928 JavaScript/TypeScript**)
- Detected/classified high-risk routes: **6,850 / 6,850**
- Complete local-development registered-release proofs recognized: **0**
- Explicit holds recognized by this structural sink auditor: **0**
- Remaining blockers: **6,850**
- Parse errors: **0**
- `certified_full_os_protection: false`
- Inventory SHA-256:
  `99d3173e79ce1477829c490daf4f66107095ef7e8e4ad4a97a598750f62de6d3`
- Receipt file:
  `C:\Users\user\aureon_boundary_census_20260831_v04.json`
- Receipt-file SHA-256:
  `812d9949d9186f11f573eaa7102168bfbd13e3b20cf563f9ad89718c829a5f6f`

| Static risk category | Count |
|---|---:|
| Filesystem mutation | 3,438 |
| Economic mutation | 1,563 |
| Credential/config write | 899 |
| Subprocess/shell | 345 |
| HTTP server ingress | 327 |
| Dynamic code execution | 253 |
| WebSocket server ingress | 12 |
| Interprocess capability dispatch | 1 |
| Unsafe deserialization | 6 |
| Local action bridge | 6 |

This auditor requires a complete structural HNC-to-custody-to-registered
release proof at each detected sink. It does not infer protection from names,
comments, tests, imports, or a surrounding HOLD facade. The zero protected/hold
counts therefore do not negate the focused fail-closed tests above; they prove
that organism-wide exclusive protected routing has not been established. The
v0.4 census is the current working-tree receipt and supersedes the v0.3 receipt
and earlier same-day 6,840-, 6,842-, 6,844-, 6,845-, and 6,846-route snapshots.
The v0.3 remote executor call remains intentionally classified as the single
interprocess blocker; the auditor cannot misclassify it through the old
same-process V0.2 pattern.

## Secret and dependency checks

The changed-file high-confidence secret scan found no real credential. Its only
match was an intentional, synthetic OpenAI-token-shaped sentinel in
`tests/test_whole_knowledge_voice.py`, where the test proves recursive
redaction.

`pip check` is not clean: installed `selenium 4.45.0` requires
`urllib3[socks] >= 2.6.3, < 3.0`, while this host has `urllib3 2.6.2`. No global
package installation or environment mutation was authorized during this gate.

## Remaining release blockers

- The production Magic Star authority/custody service does not exist. V0.3 now
  defines the signed out-of-process contract and a durable SQLite reference
  ledger, but no independently administered HSM/KMS signer, remote executor,
  TEE attestation, mTLS channel, monotonic production database, or provider
  effect read-back service is connected. Every checked-in implementation stays
  `production_ready=false`.
- A privileged writer can roll back or replace the local SQLite file and replay
  a previously terminal effect. Exactly-once production execution therefore
  requires protected append-only storage plus an independently administered
  monotonic anchor; local schema and signature checks cannot defeat privileged
  storage rollback.
- The production executor/provider must durably deduplicate effect and dispatch
  IDs, fence retries, and expose signed status/evidence lookup. The production
  receipt authority must durably honor evidence-commitment idempotency and
  read-back. These are enforced as adapter contracts locally but have no live
  service attestation.
- A same-process capability handler receives plaintext before result validation
  and can create effects, retain data, or use a semantic/covert bit channel.
  The boolean result ABI closes direct return-shape exfiltration, not process
  isolation.
- Raw hostile outer packet JSON still needs a byte/node bound before the
  `PlumberPacketV0` parse/freeze boundary.
- V0.2 replay, release, recipient, and EPAS state remain in-memory and
  rollbackable. The v0.3 SQLite ledger survives restart but remains locally
  administered and is not a durable multi-host/monotonic production authority.
- The repository census still identifies 6,850 high-risk routes without a
  complete protected release proof.
- The self-coder has no durable authenticated ciphertext proposal vault. Its
  transient opaque handle is now burned after seal verification and is not a
  recoverable review capability. Local model prompt non-retention and
  downstream-server egress policy are not verified.
- The local transport passport and strict-adapter marker are same-process
  checks, not independent attestation against a malicious injected resolver or
  a compromised local model server. Any future HTTP client/call path requires
  renewed code review and strict-origin tests.
- The default model switchboard still requires its hosted Ollama provider mode;
  it cannot currently issue the exact local self-coder provider passport. The
  default self-coder therefore holds before source or prompt release.
- No independent production-supervisor start-authority type exists. Live and
  production process launch is therefore intentionally HOLD rather than being
  inferred from an evidence-only release verdict.
- The HNC module has 54 strict typing errors and the Python environment has one
  dependency-version conflict.
- Long-lived processes started before this patch must be restarted; clearing a
  singleton reference cannot unload an already registered callback or thread.
- The full effectful benchmark/provider/stress system was not run. Only the
  local in-memory HNC crypto microbenchmark above ran; committed production
  reports remain explicitly stale and superseded.

## Git and publication state

Local `main` is two commits ahead of its remote-tracking branch. The current
hardening supplement and code changes remain uncommitted in the preserved dirty
working tree. No commit, merge, force operation, reset, cleanup, or GitHub push
was performed. The configured push URL remains
`disabled://owner-approval-required`.

Current live GitHub `main` read-back is
`957e007c2e15d936168c01f93fa4a7d2e8889176`; therefore these local changes are
not a verified GitHub/cloud outcome.

## 2026-09-01 durable intrusion and lifecycle addendum

This addendum supersedes the earlier v0.4 ledger/lifecycle and census evidence
in this document. It does not supersede the explicit production and whole-OS
holds.

### Durable HNC intrusion evidence

The local SQLite reference ledger now uses a domain-separated keyed genesis
HMAC and a per-entry HMAC over every stored field, the exact sequence, and the
previous authenticated head. It authenticates the stored HNC packet and its
exact runtime-guard AAD/content join, revalidates the complete schema and
durability PRAGMAs for every operation, excludes unexpected `sqlite_` objects,
uses `BEGIN IMMEDIATE` snapshots, and performs exact post-commit read-back.
The runtime route is restricted to the fixed v0.4 source, purpose, ingress
kinds, supported audit events, and violation reason. Runtime-guard installation
irreversibly seals the in-process sink; closing it after seal is rejected.

This closes the tested wrong-key, public-rehash, source-forgery, row-reorder,
metadata-canary, durability-downgrade, hidden-schema, DDL-race, and
close-during-install attacks. A valid authenticated prefix can still be rolled
back by a privileged storage owner because no external monotonic head exists.
Accordingly `external_head_anchor_attested`,
`magic_star_durable_custody_attested`, and `production_ready` remain false.

Short lifecycle leases now linearize guard installation, release admission,
each audit authorization decision, and the final execution/admission/custody
return against completed terminal transitions. Deterministic tests reject a
completed terminal transition during permit use, HNC admission, or Magic Star
custody. CPython has no post-syscall audit hook, so a transition that linearizes
after an authorized audit decision but before or during the OS syscall remains
outside the local proof and requires OS/process isolation.

Final source SHA-256 values:

- `runtime_intrusion_ledger_v04.py`:
  `1aac6fe3a824e24356bd43390cf484bf1ff9bdad41de1b93afa0ffee0e1a1f79`
- `os_protection.py`:
  `c70db00ea50fceae54d9328e400b119bee21e3b4968d25ce78d6d91e68e6b8e1`
- `runtime_guard_v04.py`:
  `0269593bc0dbe11474ac36c909d3202eae776a7387237ebb352ae9a02f9fe280`

### Final verification snapshot

These rows overlap and must not be summed:

| Verification | Result |
|---|---:|
| Complete `tests/plumber` suite | **378 passed** |
| Adjacent HNC/release/census/launcher suite | **88 passed** |
| Final adversarial ledger/lifecycle matrix | **85 passed** |
| Independent race probes | **3 passed** |
| Independent false-claim read-backs | **3 passed** |
| Focused Ruff | **passed** |
| Focused MyPy | **4 source files, no issues** |
| Focused Python byte compilation | **passed** |
| Primary PowerShell parser checks | **passed** |
| `git diff --check` and `git fsck --no-dangling --full` | **passed** |

The high-confidence changed-file secret scan found only the intentional
OpenAI-token-shaped redaction sentinel in
`tests/test_whole_knowledge_voice.py`. `pip check` remains blocked by the
pre-existing environment mismatch: Selenium 4.45.0 requires
`urllib3[socks] >= 2.6.3`, while the host has urllib3 2.6.2.

### Fresh quick HNC benchmark

Schema: `aureon.hnc-crypto-boundary-benchmark.v1`

Mode: offline microbenchmark only; this is not a security or production proof.

| Payload | Iterations | Seal mean | Decode mean | Seal throughput | Decode throughput |
|---:|---:|---:|---:|---:|---:|
| 1 KiB | 20 | 7.076 ms | 1.508 ms | 0.138 MiB/s | 0.648 MiB/s |
| 64 KiB | 10 | 8.392 ms | 3.904 ms | 7.448 MiB/s | 16.011 MiB/s |
| 1 MiB | 3 | 60.318 ms | 59.430 ms | 16.579 MiB/s | 16.827 MiB/s |

Exact round trips and ciphertext-tamper rejection passed at every size. The
4 KiB OS admit-and-burn path averaged **11.497 ms / 86.98 operations per
second** and ended with zero active handles and zero active ingress bytes.
The cryptography remains classical rather than post-quantum.

### Final whole-OS structural census

- Source files scanned: **5,122** (**4,194 Python; 928 TypeScript/JavaScript**)
- Detected/classified high-risk routes: **6,858 / 6,858**
- Complete registered protection proofs recognized: **0**
- Explicit structural holds recognized: **0**
- Remaining blockers: **6,858**
- Parse errors: **0**
- `certified_full_os_protection: false`
- Inventory SHA-256:
  `4aecc5fccf9c93bb5ddf97d907713038df67d67d8e8d574d1f31b132a7309222`
- Receipt file:
  `C:\Users\user\aureon_boundary_census_20260901_v08.json`
- Receipt-file SHA-256:
  `70ae1739bae630f9e64aa758458f896b35a659ac49bdb8761a296e74bbff7daa`

| Static risk category | Count |
|---|---:|
| Filesystem mutation | 3,440 |
| Economic mutation | 1,563 |
| Credential/config write | 899 |
| Subprocess/shell | 349 |
| HTTP server ingress | 327 |
| Dynamic code execution | 255 |
| WebSocket server ingress | 12 |
| Interprocess capability dispatch | 1 |
| Unsafe deserialization | 6 |
| Local action bridge | 6 |

The focused guard and ledger are therefore substantially hardened, but the
repository is not a fully protected Aureon OS. In particular, native code,
JavaScript/Node, child runtimes, pre-opened descriptors and sockets, privileged
storage rollback, and thousands of direct mutation routes remain outside the
proved boundary.

### Bootstrap and installed-command state

The five declared future console commands now route only to the top-level,
stdlib-only `protected_console_bootstrap_v05` module. Fresh-process tests prove
that each route imports zero `aureon` modules, accepts no caller-controlled
root, starts no target or child, performs no network or file write, and returns
HOLD. The two primary Windows launchers still invoke the standalone isolated
script with `python -I -S -B` before side effects.

A wheel and source distribution built from a temporary source copy passed
archive and entry-point inspection. The wheel contained exactly one top-level
inert console module whose hash matched the checkout, and all five unpacked
wheel entry points returned HOLD under `python -I -S -B` with zero `aureon`
imports and no detected action. The audited wheel SHA-256 was
`63313f809216df57d09a7a1f0de8b899d2ec5d771369317ab8de0e2475ecfd45`;
the source-distribution SHA-256 was
`4f01feec1d4089677608b20253db1c8a6e3ae4cd72c95ae13bdd25e5edf3d8ec`.
These are audit artifacts in a temporary directory, not an installed or
released package. The source distribution does not include the standalone
`scripts/bootstrap/protected_bootstrap_v05.py`, so the PowerShell launcher path
remains checkout-only.

The machine-wide editable Aureon 2.1.0 installation was not changed. It still
points to `C:\Users\user\Aureon-OS` and exposes three older direct-daemon
entry points, not this audited checkout. Those global commands remain outside
the verified route until a pinned wheel is installed in a dedicated,
owner-authorized environment and its origin and entry-point manifest are read
back.

## 2026-09-01 settled HNC, deployment, and executable-surface audit

### Decision

**HOLD — the current canonical launch/deployment/package paths are correctly
fail-closed, and the HNC reference boundary passes its current attack suite,
but the complete checkout is not a fully protected or production-ready Aureon
OS.**

This addendum supersedes the earlier same-day benchmark, deployment-surface,
economic-inventory, and whole-repository census snapshots where they differ.
It does not turn a local test, static HOLD receipt, archive, or checksum into a
native containment attestation, provider receipt, GitHub publication, or
production release.

### HNC intrusion evidence and bridge result

The authenticated local v0.4 intrusion ledger now binds the exact ledger
object, immutable per-ledger instance commitment, KDF metadata, keyed entry
chain, sequence, previous head, HNC packet, runtime-guard AAD, durable receipt,
and public projection. Tests reject forged or publicly rehashed projections,
cross-ledger replay under the same key and requested ledger ID, schema/PRAGMA
tampering, row reorder, replaced function bytecode, DDL races, plaintext
canaries, and duplicate proposal creation. The intrusion bridge produces only
a commitment-bearing **HOLD proposal** and never invokes work, forge, release,
provider, or other downstream authority.

The complete selected HNC/Plumber sweep collected and passed **431 tests**.
The focused independent bridge/ledger attack slice passed **50/50**. Strict
MyPy passed all **31** `aureon/plumber` source files, and focused Ruff passed.

Two fundamental limits remain explicit:

- a privileged owner can copy or roll back a valid SQLite ledger. A copied
  pre-incident ledger accepted the same authenticated packet with the same
  entry commitment in both forks; both correctly report
  `external_head_anchor_attested=false`;
- arbitrary same-process Python compromise can replace globals, closures, or
  caller state. The reference can pin tested function identities and bytecode,
  but Python alone cannot provide native code identity or process isolation.

An independently administered monotonic head anchor, native outer supervisor,
exclusive ingress gateway, measured out-of-process executor, durable custody,
and provider read-back remain mandatory.

### Fresh offline HNC benchmark

Schema: `aureon.hnc-crypto-boundary-benchmark.v1`

Mode: local offline microbenchmark; performance measurement only, not a
security, post-quantum, custody, or production proof.

| Payload | Iterations | Seal mean | Decode mean | Seal throughput | Decode throughput |
|---:|---:|---:|---:|---:|---:|
| 1 KiB | 200 | 6.530 ms | 1.511 ms | 153.15 ops/s | 661.67 ops/s |
| 64 KiB | 100 | 9.207 ms | 4.286 ms | 6.788 MiB/s | 14.582 MiB/s |
| 1 MiB | 20 | 73.998 ms | 69.063 ms | 13.514 MiB/s | 14.480 MiB/s |

Exact round trips, ciphertext-tamper rejection, and all negative controls
passed at every size. The 4 KiB OS admit-and-burn path averaged **13.707 ms /
72.95 operations per second** across 200 iterations and ended with zero active
handles and zero retained ingress bytes. The benchmark itself reports
`production_ready=false`, `production_claim=false`, and
`performance_only_not_security_proof=true`.

### Canonical deployment and legacy entrypoint closure

Root and production Dockerfiles, five compose manifests, systemd units,
supervisor definitions, cloud specs, appliance/package facades, primary
Windows launchers, shell start/util routes, runner CMD/PowerShell/Python paths,
desktop launch/build surfaces, ignition, self-enhancement restart handoff, and
selected operational scripts now terminate at an isolated fixed bootstrap or
emit a non-mutating structured HOLD receipt. Environment flags cannot enable
real orders through `aureon_runtime_safety`; production release attestation is
hard-coded false.

The adversarial review found two directly executable economic-mutation bypasses
after the first launcher sweep:

- `scripts/python/quick_sniper.py` could place Kraken orders using most
  available funds;
- `scripts/reports/LIVE_NOW.py` could run an autonomous multi-provider buy/sell
  loop.

Their original source is preserved only as `.txt` evidence beneath
`docs/archive/unprotected_entrypoints/`. The executable paths are now inert
facades. Direct isolated probes returned exit code 2 with HOLD,
`provider_accessed=false`, `credentials_loaded=false`,
`order_submitted=false`, and `file_written=false`. The focused launcher and
legacy-surface matrix passed **65 tests** after this correction. A second
static review found no remaining directly executable economic-mutation bypass
in the registered canonical launcher set.

The Node/Murge hardening inventory covers **81 files**: 67 operational npm
routes HOLD and 14 offline static routes remain active. The exact Node contract
suite passed **39/39**; its aggregate audited SHA-256 is
`5b3d5b8a1d3a183219cec9deabb0c010638c9c1cc56bcb252ccbb499ead67808`.
All five compose files passed `docker compose config --quiet`. Bash syntax
passed for 79 changed shell scripts and PowerShell parsing passed for 17
changed scripts. A real Linux image build was not run because the Docker Linux
daemon was unavailable.

The settled verification matrix also records **223/223 Python tests** across
the selected deployment, appliance, import, launcher, Murge, release, voice,
and packaging scope, followed by **81/81** affected packaging/Linux tests on a
stable tree. The later economic/legacy/acceptance sweep passed 177 tests and
exposed only two stale exact-count assertions after eleven dangerous call-site
fingerprints were removed; after correcting those receipt constants, the two
census assertions and the new credential regression passed **3/3**.

### Credential correction

A high-confidence whole-tree scan found one hard-coded Gamma API-token fallback
in `scripts/traders/gammaSync.ts`. The embedded value was removed; the code now
requires `GAMMA_API_KEY` from the runtime environment and fails before a Gamma
request when it is absent. The current working-tree scan finds high-confidence
secret-shaped material only in six test-fixture files.

The removed value is still present in local Git history at commit
`18fe19d78a75e2376088f9a30bf961f3c1a4d225`. Removal from the working tree is
not revocation. The credential owner must revoke/rotate it at the provider and
then decide, under owner authority, whether repository-history remediation is
required. The value is intentionally omitted from this report and was not
reused, tested against a provider, or rotated during this audit.

### Settled economic mutation census

The allowlist and source inventory are exact after removing eleven stale
fingerprints for the four now-held surfaces (`quick_sniper.py`, `LIVE_NOW.py`,
`GO_LIVE.py`, and `run_snowball.py`).

- Source files scanned: **5,126**
- Economic mutation routes detected/classified: **1,607 / 1,607**
- Live-capable unguarded blockers: **1,236**
- Provider raw-transport guards: **245**
- Dry-run/test/demo-only routes: **122**
- Exact economic-boundary last-mile routes: **4**
- Unallowlisted routes: **0**
- Stale allowlist entries: **0**
- Parse errors: **0**
- `inventory_aligned=true`
- `certified_no_bypass=false`
- Allowlist SHA-256:
  `05e445a78eabe189ce4738d3d1fa9dbc3fffd554cdc29fefac828b2ed9f7c112`

Inventory alignment proves that the known routes are classified; it does not
authorize the 1,236 blocker routes or prove they are unreachable from arbitrary
imports/manual execution.

### Settled whole-repository protection census

Receipt:
`C:\Users\user\aureon_boundary_census_20260901_v15_proposal_vault.json`

- Source files scanned: **5,128** (**4,199 Python; 929 JavaScript/TypeScript**)
- High-risk routes detected/classified: **6,721 / 6,721**
- Structurally proven registered protected routes: **0**
- Structurally recognized explicit holds: **0**
- Remaining blockers: **6,721**
- Parse errors: **0**
- `certified_full_os_protection=false`
- Inventory SHA-256:
  `41d95cecf92e78e74ceda60b976b9944d1f0c410eed6fa4baebc0b43e7a33c93`
- Receipt SHA-256:
  `20eabbb6d03fb4693cf4a9d6193b960ed53f26e55bcd70c68bd35d20ce4d1eb3`

| Static risk category | Count |
|---|---:|
| Filesystem mutation | 3,388 |
| Economic mutation | 1,552 |
| Credential/config write | 875 |
| HTTP server ingress | 333 |
| Subprocess/shell | 301 |
| Dynamic code execution | 254 |
| Local action bridge | 6 |
| Unsafe deserialization | 6 |
| WebSocket server ingress | 5 |
| Interprocess capability dispatch | 1 |

The structural auditor intentionally does not trust comments, facade names, or
tests as complete HNC-to-custody-to-registered-release proof. Its zero
protected/hold count does not contradict the focused fail-closed probes; it
proves that focused launcher closure is not organism-wide exclusive routing.
Unregistered diagnostic/provider scripts, demo/research material, directly
invocable unreleased source, preserved import/Kimi snapshots, native and Node
code, pre-opened capabilities, and thousands of mutation functions remain
outside a complete protected boundary.

### Durable encrypted intrusion-proposal vault

`aureon/autonomous/aureon_runtime_protection_proposal_vault_v05.py` now
materializes one deterministic Aureon remediation-review proposal and one
fixed-template protection-code candidate only from an exact, authenticated
`SQLiteRuntimeIntrusionLedgerV04` source entry. The candidate is an import-free
new-file unified diff whose exact event/reason returns `HOLD` and whose other
inputs return `OUT_OF_SCOPE`; it contains no `ALLOW` route. The canonical
proposal/candidate envelope is stored only inside an authenticated HNC packet
in a strict append-only SQLite/HMAC chain. No candidate file is written,
compiled, imported, executed, applied, registered, or released.

The complete transitive source-authentication call chain is identity- and
code-pinned. Per-instance method shadows, class replacement, same-function
`__code__` replacement, `__getattribute__` interception, vault resolver
replacement, candidate renderer replacement, and projection-helper global
replacement all fail before append. Bridge and vault pin manifests are compared
in CI so the two consumers cannot silently drift. Source projections for all
stored vault rows are authenticated in one atomic batch, changing revalidation
from `O(vault_entries * source_entries)` to
`O(vault_entries + source_entries)`. Declared source capacity, proposal
capacity, and batch size are each capped at 64. A generic source ledger still
defaults to 1,024 entries, so a ledger attached to this vault must be explicitly
configured at 64 or lower.

Standalone receipt and review objects do not self-attest. Their public
summaries report authentication and persistence as false; only a live
`verify_receipt` read-back against the exact vault and exact source ledger may
report keyed authentication, ciphertext persistence, and durability as true.
Private factories require internal tokens, raw proposal/candidate mappings are
private fields, and every returned plaintext review envelope repeats that live
vault read-back is required. Technical provenance records the candidate owner
as Aureon and discloses OpenAI assistance, while
`legal_title_attested=false` remains explicit.

The dedicated vault adversarial suite passed **63/63**. The intrusion ledger,
bridge, and vault matrix passed **118/118**. The broader
Plumber/HNC/self-coder/attack-lab regression matrix passed **540/540**, and the
separate economic/whole-OS census regression matrix passed **89/89**. Strict
mypy, Ruff, and bytecode compilation passed for the three core source modules,
the benchmark harness, and focused tests. Covered attacks include wrong or
missing keys, restart-key discontinuity, all nine source-method instance/class/
code substitutions, `__getattribute__` interception, resolver/renderer/helper
substitution, direct receipt/review construction, factory detachment, concurrent
replay, row/ciphertext/metadata/candidate tamper, oversized SQLite blobs, rogue
indexes, `ANALYZE`/`sqlite_stat1`, exact trigger-literal tamper, restart, final
capacity, plaintext scans, and downstream-authority tripwires.

Benchmark receipt:
`docs/security/AUREON_RUNTIME_PROTECTION_PROPOSAL_VAULT_V05_BENCHMARK_20260901.json`

| Local HOLD-only operation | Result |
|---|---:|
| Empty vault open | 347.601 ms |
| Seal proposal + encrypted candidate, median / p95 (8 entries) | 385.596 / 1,485.240 ms |
| Live receipt verification, median / p95 | 82.808 / 95.697 ms |
| Authenticated review read, median / p95 | 59.319 / 68.929 ms |
| Idempotent replay, median / p95 (20 runs) | 84.039 / 91.939 ms |
| Restart and authenticate all 8 entries | 139.507 ms |

Independent instrumented scaling at the selected 64-entry source cap measured
501.616 ms median / 647.779 ms maximum preflight and 621.526 ms maximum
aggregate source-lock occupancy. A 128-entry source measured 1,157.779 ms
median / 1,305.198 ms maximum preflight and 1,282.820 ms maximum aggregate lock
occupancy, so the vault rejects that declared capacity.

The benchmark confirmed a stable head across restart and no plaintext canary,
raw intrusion ID, resource commitment, candidate target, candidate function,
event, or reason in the vault database/WAL/SHM or public summaries. It also
confirmed zero candidate files written and no self-coder, external model,
proposal forge, apply, import, execute, release, repository-mutation, Magic
Star, or economic route. It is a performance and local-integrity measurement,
not a production-security claim.

The generated candidate is deliberately generic to the authenticated event
family because the source projection is commitment-only; semantic correctness
and integration are not attested. SQLite valid-prefix rollback and byte-copy
clones remain indistinguishable without an independent monotonic head anchor.
Future key-provider continuity and independent key custody are not attested,
and arbitrary same-process Python compromise remains outside the proof. Native
isolation, independently administered key custody/review, measured execution,
full-organism exclusive ingress, production Magic Star, and provider read-back
remain required. Every receipt therefore remains HOLD with
`external_head_anchor_attested=false` and `production_ready=false`.

The refreshed v16 conservative whole-tree census scans 5,129 source files
(4,200 Python and 929 JavaScript/TypeScript) and classifies 6,722 high-risk
routes, all as blockers, with zero parse errors. Its inventory SHA-256 is
`8290c9159674e63ea8e481dfc71b2ff4f8a8ee53a3dfa17b4ceb64565ce9ce28`; the
external receipt SHA-256 is
`538441b7560a65cb9a7e1a4b6c5d63d80666a6f04cb11b450e6fd998ad01d788`.
The new benchmark harness adds the one filesystem-mutation route. The static
auditor correctly does not treat focused authenticated local storage or a
review-only diff as a production registered-release boundary; this prevents
the component proof from being misreported as full-OS containment.

### Final local integrity and environment notes

- `git diff --check`: passed (line-ending conversion warnings only).
- `git fsck --no-dangling --full`: passed.
- Focused Ruff, strict mypy, and bytecode compilation: passed for the runtime
  ledger, intrusion bridge, proposal vault, benchmark harness, and focused
  tests.
- Final Plumber/HNC/self-coder/attack-lab matrix: 540/540 passed.
- Final economic/whole-OS boundary matrix: 89/89 passed (one pre-existing
  invalid-escape `SyntaxWarning`).
- Quick HNC crypto boundary benchmark: exact round trips and ciphertext-tamper
  negative controls passed at 1 KiB, 64 KiB, and 1 MiB; admission retained zero
  handles and zero ingress bytes.
- Five compose configuration parses: passed.
- Changed Bash syntax: 79/79 passed.
- Changed PowerShell parsing: 17/17 passed.
- High-confidence current-tree secret scan: six test-fixture files only.
- `pip check`: failed because installed Selenium 4.45.0 requires
  `urllib3[socks] >= 2.6.3`, while the host has urllib3 2.6.2.
- One unrelated census source emits an existing invalid-escape
  `SyntaxWarning` in `scripts/reports/MULTIVERSE_REALITY_INTEGRATION.py`.
- A TypeScript compiler probe accidentally resolved the deprecated npm `tsc`
  package rather than the TypeScript compiler and failed; no repository file
  was generated or changed by that probe.

Local `main` remains at
`6ca7af63393655223be4749e7cd308a044239ed8`, two commits ahead of the local
`origin/main` tracking ref, with **485** dirty status entries (448 tracked and
37 untracked). These are preserved local working-tree changes, not one reviewed
commit. The push URL remains `disabled://owner-approval-required`. No commit,
merge, reset, cleanup, provider operation, Docker deployment, cloud read-back,
GitHub push, or release publication was performed.
