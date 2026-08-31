# Aureon Plumber Security Charter

Status: local laboratory protocol only

Version: Magic Star v0.2 foundation
Production release authority: unavailable

## Purpose

The Aureon Plumber is an observer-bound cryptographic release protocol built
above the retained HNC packet. Its job is to keep protected material sealed
unless the exact packet, purpose, source, time, observer, Heart, Conscience,
governance and quorum evidence all validate.

This charter is an engineering boundary, not a claim that the current
repository provides production hardware identity, clone resistance, an HSM, a
production or isolated release enclave, or independently reviewed
cryptography.

## Master invariant

1. No source equivalence, no grammar.
2. No temporal continuity, no identity.
3. No fresh coherent observer state, no alignment.
4. No signed Heart, Conscience and governance evidence, no authority.
5. No mandatory-class quorum, no key.
6. No key, no plaintext.

Missing, stale, malformed, unverifiable or unavailable evidence produces
HOLD or DENIED. It never produces a weaker release mode, a caller-approved
fallback or an emergency bypass.

For production promotion in particular:

- Missing live canonical HNC evidence produces HOLD.
- Missing hardware-rooted source evidence produces HOLD.
- A dark field is not release authority, even though the general Operator
  coherence membrane may remain open for introspection and repair.
- A model, prompt, HNC score, symbolic rune or star cannot mint authority.
- Public HNC geometry is authenticated context and never secret entropy.

## Current assurance boundary

The v0.2 foundation may:

- define strict schemas and canonical commitments;
- sign and verify metadata contracts using reviewed library primitives;
- wrap the retained HNC AES-GCM/HKDF packet without changing its API;
- evaluate an offline, deterministic immune gate;
- model a verifier-issued recipient challenge and proof of possession;
- bridge the existing signed Heart-receipt contract into the 528-centre
  precondition with exact source, policy, runtime and time joins;
- require five explicit signed point approvals, seven-organ evidence, a
  continuity decision, authorization snapshot, all five permits and custody
  authorization;
- model centrally held five-share wrapping plus in-memory release and EPAS
  compare-and-set state;
- execute a registered same-process test handler and create a signed result
  object; and
- exercise a positive path with deterministic test-only providers.

It must not:

- claim production release, uncrackability or independent validation;
- treat Windows DPAPI alone as hardware attestation or clone resistance;
- accept in-process JSON fields such as APPROVED as policy signatures;
- expose a general plaintext-returning decrypt API;
- expose a public, tenant, HTTP, MCP, daemon or autonomous release endpoint;
- register an operational or side-effecting capability handler;
- present declared SHA-256 strings as measured code or hardware attestation;
- present five co-resident XOR shares as distributed threshold custody;
- present output allowlists or direct-encoding scans as exfiltration
  prevention;
- present `CONSUMED`, `plaintext_returned=False` or a signed local result as
  containment, noninterference, durable provider read-back or production
  release proof;
- place plaintext, root keys, session keys or reconstruction hints in logs,
  ThoughtBus, assimilation, exceptions, status responses or evidence files;
- trade, transfer funds, file with an authority, send messages, deploy, mutate
  providers, reveal credentials or perform other external actions; or
- use AUREON_LOCAL_ACTIONS_ARMED, AUREON_AUTONOMY, a live-trading flag or an
  auto-approval flag to enable Plumber release.

## Evidence and authority

Evidence describes a condition. Authority permits a narrowly bound action.
They are deliberately separate.

Every release receipt must be signed by its named authority and bound to:

- packet and session identifiers;
- exact requested purpose;
- source and temporal commitments;
- observer commitment;
- policy version and runtime measurement;
- verdict, issue time and expiry; and
- receipt hash and signing identity.

Receipt validation must occur outside the requesting model/process for a
production design. Test fakes are fixtures, not trusted providers and must be
impossible to select through production configuration.

In the current laboratory adapter, signers, probes, verifier, custody, handler
and result validator may all coexist in one Python process. Distinct keys,
principals and roles enforce protocol joins; they do not establish operational
independence, hardware attestation or separate administration.

Quorum is by mandatory authority class, not a generic count. Source, observer
and policy evidence are mandatory. Operator authorization may also be mandatory
for high-value material. Duplicate authorities or multiple shares from one
class do not satisfy another class.

## Cryptographic boundary

- Use the existing HNC packet for authenticated encryption and HKDF-based key
  derivation until a separately reviewed migration is approved.
- The controlled packet magic is AUREON-HNC-PLUMBER.
- Rune, star, observer and HNC values are authenticated associated context.
- Canonical encodings reject duplicate keys, unknown consequential fields,
  non-finite numbers and ambiguous numeric encodings.
- Permanent roots never enter prompts, packets, environment-visible status,
  frontends or model context.
- Fragment reassembly verifies transport completeness only. It does not itself
  authorize or perform release.
- Ephemeral clearing is best effort; documentation must not claim guaranteed
  erasure in a managed-language runtime.

## Plaintext and telemetry

Production design returns only a purpose-specific capability or minimal data
view. For example, a document-signature purpose may return valid/invalid plus a
receipt, but not unrestricted document contents.

Allowed telemetry is limited to non-secret identifiers, hashes, policy
versions, timestamps, HOLD/DENIED outcomes and stable reason codes. Tests use a
secret canary on selected serialized surfaces. Those checks do not establish
absence from every log, exception, bus, file, side channel or transformed
handler output.

## Operational states

The protocol must distinguish at least:

- HOLD: required live, hardware or independent evidence is unavailable.
- DENIED: supplied evidence is invalid, stale, mismatched or prohibited.
- QUARANTINED: replay, tamper, clone or policy-divergence evidence exists.
- LAB-VALIDATED: a deterministic test-only path completed.

LAB-VALIDATED is not production approval. No production RELEASED state may be
implemented or asserted until the source identity, protected counter, external
policy signer, mandatory-class quorum and isolated capability release have
independent security review.

`ReleasePhase.CONSUMED` is an internal laboratory one-use transition. It is not
the prohibited production `RELEASED` claim.

## Change and claim control

The retained HNC baseline must pass unchanged before and after Plumber changes.
Changes to schemas, canonical encoding, commitments, key derivation, quorum,
receipt binding or release behavior require:

1. explicit security review;
2. deterministic negative tests and vectors;
3. offline and socket-blocked CI;
4. a new version identifier rather than silent reinterpretation; and
5. an updated metadata-only evidence receipt.

External descriptions must say experimental local-laboratory protocol until an
independent cryptographic review and the missing production providers are
complete.

## Source basis

This charter translates the repository working order, especially its master
invariant, WP-00 baseline gate, signed-receipt rule, mandatory-class quorum,
release-enclave boundary, zero-plaintext rule and claim boundary. The retained
implementation anchors are:

- aureon/harmonic/hnc_quantum_packet_crypto.py
- aureon/harmonic/hnc_symbolic_route_seal.py
- aureon/harmonic/rainbow_reference.py
- aureon/core/hnc_field.py
- aureon/operator/coherence_gate.py
- aureon/operator/heart.py
- aureon/queen/queen_conscience.py
- aureon/governance/tool_route_authority.py
