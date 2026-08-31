# Aureon Plumber Threat Model

Status: local laboratory model; not a production security certification
Applies to: Magic Star v0.2 protocol foundation

## Security objective

Protected material stays cryptographically inert unless one exact,
purpose-bound request proves fresh source, temporal, observer, Heart,
Conscience, governance and mandatory-class quorum evidence. Failure must withhold
shares and leave plaintext absent, not merely emit an ethical warning.

## Assets

- Protected plaintext and purpose-limited derived results.
- Root, authority-share, session and signing keys.
- Packet and receipt commitments.
- Source identity and runtime measurement.
- Temporal continuity, nonce/counter state and replay memory.
- Policy, Heart, Conscience and governance signing authority.
- Observer transcripts and canonical HNC field provenance.
- Metadata-only audit evidence.

## Trust boundaries

The following are mutually distinct in the production target:

1. Requesting model or process.
2. Canonical HNC field and observer adapters.
3. Source/hardware identity provider.
4. Protected temporal/replay store.
5. Heart, Conscience and governance signers.
6. Mandatory-class quorum participants.
7. Transport/reassembly process.
8. Isolated release process and purpose-specific capability.
9. Metadata-only logging and evidence sink.

Production trust must not collapse these boundaries into one Python process,
one environment variable, one agent or one caller-supplied JSON document.

The current laboratory topology does collapse signers, verifier, probes,
custody shares, keys, state, plaintext handler and result validation into one
process. Distinct protocol roles and keys test exact joins; they do not prove
operational isolation or independent administration.

## Attacker capabilities

Assume an attacker may:

- read the public repository, HNC formulas, schemas and symbolic catalogs;
- copy packets, fragments, receipts and a filesystem or VM snapshot;
- control prompt text and caller-supplied fields;
- reorder, duplicate, omit, mix or replay messages and fragments;
- change the wall clock or present stale/future timestamps;
- patch the requesting runtime, delete Conscience or hard-code approval;
- run on another user, device, instance, branch or measured runtime;
- steal one authority credential or compromise one quorum class;
- race two consumers against one nonce, lease or receipt;
- cause exceptions and inspect logs, status, ThoughtBus and artifacts; and
- attempt network, provider, financial, trading, filing, deployment or
  credential side effects during import or validation.

The model does not assume that metaphysical alignment changes an attacker.
HNC, rune and star knowledge is public context and supplies no secret entropy.

## Threats, required controls and failure result

| Threat | Required control | Failure result |
|---|---|---|
| Packet or receipt ambiguity | Versioned schema, bounded canonical encoding, duplicate/unknown-key rejection | DENIED |
| Packet field tamper | One commitment over every consequential field, committed Spore stream identity, exact Spore context joins and authenticated encryption | QUARANTINED |
| Malformed or weak AEAD nonce | Strict base64url decoding to the protocol-required 12 bytes | DENIED |
| Replay or rollback | Secure nonce, protected monotonic counter, previous commitment, atomic temporal reservation and one-use store | QUARANTINED |
| Unissued, substituted or stale immune gate | Engine-issued gate bound to one exact inspection/evidence set, one-use consumption and execution-time window checks | DENIED |
| VM/filesystem clone | Hardware-rooted instance evidence plus runtime measurement and continuity | HOLD without provider; DENIED on mismatch |
| Hostile fork/hard-coded approval | Independent signed policy share bound to runtime measurement and exact purpose | DENIED |
| Caller-supplied approval | Verify trusted signer and key identifier outside requester; never trust booleans/verdict strings | DENIED |
| Dark/stale HNC field | Require freshly validated canonical field; never inherit generic dark-field full aperture | HOLD or DENIED |
| Observer forgery | Recompute transcript from trusted live adapters; bind it to source, time and purpose | DENIED |
| One-agent or same-class quorum | Mandatory source, observer and policy classes; unique signing identities | Shares withheld |
| Fragment mixing/tamper | Packet/session/route/epoch binding and AEAD authentication | Reassembly refused |
| Reassembly mistaken for authority | Separate transport completeness from immune gate and key release | No session key |
| Plaintext/model leakage | Current lab: registered same-process callable plus post-call schema, size, direct-full-plaintext checks and sanitized handler failures. Production: isolated measured capability and covert-channel policy | Session terminated |
| Key leakage | External custody, non-exportable roots where available, no prompt/env/status roots | HOLD or DENIED |
| Import-time side effect | Lean package imports, injected providers, socket-blocked tests | CI failure |
| Autonomous/external action | No public/network/autonomous endpoint; the local handler executor is restricted to pure fixtures by policy | DENIED and CI failure |
| Dependency or CI weakening | Exact CI versions, binary-only install, read-only workflow permissions and no persisted checkout credential; dependency hashes are not locked | CI failure |

## Mandatory fail-closed cases

A production adapter must prove no share release, no session key and no
plaintext for all of these cases. The current positive laboratory fixture does
not substitute for unavailable hardware or independent-provider evidence:

- missing, stale, dark, future-dated or malformed canonical field;
- missing hardware-rooted source evidence;
- instance, device, runtime, branch or measurement mismatch;
- missing/old nonce, repeated counter, rollback or concurrent reuse;
- malformed base64url or an HNC nonce that does not decode to exactly 12 bytes;
- an unissued, already-used, wrong-inspection, expired or rollback-time immune
  gate;
- unsigned, expired, wrong-packet, wrong-session, wrong-purpose or
  wrong-runtime receipt;
- aliased receipt authority identifiers or keys, or unpinned sympathetic
  hardware/operator identity;
- deleted Conscience or a plain JSON APPROVED value;
- one agent, duplicate authority, same-class substitution or generic three of
  five without every mandatory class;
- missing, duplicate, mixed, expired, tampered or wrong-route fragment;
- altered packet commitment or symbolic route context;
- provider, socket or signing-service unavailability;
- caller request to reveal a credential or unrestricted protected content; and
- any request whose purpose is trading, payment, filing, deployment, outbound
  messaging, provider mutation or safety bypass.

## Current residual risks and unavailable proofs

The repository currently has useful cryptographic and governance precursors,
but it does not yet prove:

- TPM/HSM-backed source identity or measured boot;
- a protected monotonic counter resistant to VM rollback;
- an independently deployed Heart/Conscience/governance signer;
- hardware-separated mandatory quorum shares;
- a capability-constrained release enclave;
- guaranteed key erasure in Python;
- side-channel resistance; or
- external cryptanalysis.

It also does not prove distributed custody: all five XOR shares and authority
private keys are co-resident. Recipient, temporal/replay, release and EPAS
stores are process-local and rollbackable. v0 inspection/execution accepts a
caller-supplied aware time, while v0.2 relies on an injected process-local time
callable. The v0 gate lifetime is the aggregate evidence window rather than an
independent shorter TTL. Live/continuity `valid` values and runtime or
capability measurements are injected or declared, not attested.

A registered handler receives plaintext before output checks and may
exfiltrate transformed data or perform irreversible effects before a later
denial. Its sanitization boundary catches `BaseException`; this prevents a
handler exception payload from escaping, but also swallows process-control
interrupts such as `KeyboardInterrupt` and `SystemExit`. Direct custody pops
one-use material before invoking the handler and depends on the outer release
boundary to own post-pop terminal-state handling. Release state is consumed
before EPAS finalization, so receipt signing, state consumption and EPAS
advancement are ordered but non-atomic in-memory steps. Python retains
immutable secret copies that best-effort bytearray overwrites cannot guarantee
to clear.

Windows current-user DPAPI key storage is useful at-rest protection, but is not
evidence of hardware identity or clone resistance. Deterministic in-memory test
providers establish protocol behavior only. When any unavailable production
proof is required, the correct operational result is HOLD.

## Promotion-required verification strategy

Before production promotion, the security gate must combine:

- retained HNC packet, symbolic route, field freshness, coherence, Heart and
  unified-contract regression tests;
- schema and commitment mutation tests;
- strict decoded-nonce length, Spore exact-join and sympathetic
  hardware/operator-pin tests;
- receipt signature, binding, expiry and signer-substitution tests;
- distinct receipt-authority tests;
- temporal anchor, counter, nonce, field/runtime continuity, rollback, replay
  and concurrent-use tests;
- engine-issued, inspection-bound, one-use gate and execution-time-window
  tests;
- mandatory-class quorum and fragment-mixing tests;
- subprocess/import tests proving no sockets, writes or provider calls;
- recursive secret-canary leakage tests;
- purpose-capability tests proving policy binding, sanitized failure and no
  unrestricted plaintext return; and
- an attack laboratory covering clone, hostile fork, stolen share, prompt
  injection and evidence-channel leakage.

The checked-in focused tests run offline with sockets disabled and cover the
listed protocol joins and selected hostile paths. They do not yet constitute
complete subprocess write/provider isolation, recursive leakage, hostile-fork,
clone, stolen-share, prompt-injection, side-channel or sandbox-escape testing.
A positive fake-provider test is labelled laboratory-only and cannot satisfy a
production-readiness claim. `run_synthetic_offline_breaker_lab()` wraps the
retained HNC tamper checks; its `plaintext_exposed=False` field is report-shape
metadata, not an independent leakage observation.

## Claims boundary

Permitted claim:

> Experimental, fail-closed local-laboratory protocol foundation using standard
> cryptographic primitives and metadata-bound governance evidence.

Prohibited claims include production-ready, uncrackable, impossible to clone,
hardware-attested, independently validated or safely autonomous until those
properties have separate evidence and review.
