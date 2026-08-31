# Plumber Magic Star v0.2 Local-Lab Runbook

Status: experimental local laboratory only

Production decryption/release: unavailable
Default result when evidence is missing: HOLD

## What this runbook does

This runbook validates the Plumber protocol foundation and retained HNC
baseline without network, provider, trading, financial, filing, deployment,
outbound-message or credential actions.

Magic Star v0.2 identifies the controlled Plumber packet and its authenticated
symbolic context. It is not a separate autonomous authority, a source of key
entropy or permission to release plaintext.

There is intentionally no Plumber CLI or production release command.

The local v0.2 handler receives plaintext as an ordinary in-process Python
callable. It is not sandboxed or transactionally contained. Only pure,
deterministic, non-side-effecting test fixtures may be registered: a later
DENIED result cannot undo a file, process, network or provider action already
performed by a handler.

## Prerequisites

- Work in an isolated development checkout.
- Use Python 3.11 or newer; CI uses Python 3.12.
- For a CI-equivalent evidence run, provision the exact laboratory tool set
  used by the checked-in workflow:

~~~powershell
python -m pip install --disable-pip-version-check --no-input --only-binary=:all: cryptography==46.0.3 pytest==9.0.2 pytest-socket==0.8.0 ruff==0.15.21 mypy==2.3.0 PyYAML==6.0.3
~~~

- Do not load production credentials, root keys, exchange keys, provider tokens
  or protected plaintext.
- Do not alter the baseline manifest or create a tag as an incidental test
  step. Those are reviewed evidence operations.

## Establish the laboratory boundary

Set every control explicitly in the current PowerShell process:

~~~powershell
$env:CI='true'
$env:AUREON_AUDIT_MODE='1'
$env:AUREON_LIVE='0'
$env:LIVE='0'
$env:AUREON_DRY_RUN='1'
$env:DRY_RUN='1'
$env:AUREON_OFFLINE='1'
$env:AUREON_LIVE_TRADING='0'
$env:AUREON_DISABLE_REAL_ORDERS='1'
$env:AUREON_DISABLE_EXCHANGE_MUTATIONS='1'
$env:AUREON_LLM_OFFLINE='1'
$env:AUREON_DISABLE_LLM_HTTP='1'
$env:AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS='1'
$env:AUREON_LOCAL_ACTIONS_ARMED='0'
$env:AUREON_SOUL_ACT='0'
$env:AUREON_AUTONOMY='0'
$env:AUREON_CODE_AUTO_APPROVE='0'
$env:AUREON_ALLOW_PAID_PROVIDERS='false'
$env:AUREON_PROVIDER_MODE='offline'
$env:BINANCE_DRY_RUN='true'
$env:KRAKEN_DRY_RUN='true'
$env:ALPACA_DRY_RUN='true'
$env:CAPITAL_DEMO='true'
$env:PYTHONDONTWRITEBYTECODE='1'
$env:PYTHONHASHSEED='0'
~~~

If any required value cannot be established or a loaded process has already
armed live behavior, stop and use a fresh process. Do not try to compensate
with an HNC score or an approval string.

## Read-only preflight

~~~powershell
git branch --show-current
git rev-parse --verify HEAD
git status --short --untracked-files=all
python --version
python -c "import cryptography; print(cryptography.__version__)"
~~~

Record the exact commit and dirty-state description in the test receipt. A
dirty tree is not automatically invalid, but it must not be represented as a
clean-clone result. Preserve unrelated work.

## Retained baseline

Run with pytest cache disabled and sockets blocked:

~~~powershell
python -m pytest -o addopts='' --disable-socket -p no:cacheprovider -q tests/test_hnc_quantum_packet_crypto.py tests/test_hnc_symbolic_route_seal.py tests/test_hnc_field_freshness.py tests/test_coherence_gate.py tests/test_heart.py

python -m pytest -o addopts='' --disable-socket -p no:cacheprovider -q tests/test_unified_contract.py
~~~

The independent 2026-08-31 audit at parent commit
2359e25460d5eaf0864d39fea7912c7b96e7b921 recorded:

- 108 passed in 15.14 seconds for packet, symbolic route, field freshness,
  coherence and Heart.
- 5 passed in 3.94 seconds for the unified contract.

These 113 passes are a laboratory baseline, not a production security
certification.

## Plumber contract gate

~~~powershell
python -m compileall -q aureon/plumber aureon/saas/domains.py tests/plumber
ruff check aureon/plumber aureon/saas/domains.py tests/plumber tests/test_plumber_ci_workflow_contract.py
mypy --strict aureon/plumber
python -m pytest -o addopts='' -o filterwarnings=error --disable-socket -p no:cacheprovider -q tests/test_plumber_ci_workflow_contract.py tests/plumber

python -m pytest -o addopts='' -o filterwarnings=error --disable-socket -p no:cacheprovider -q tests/test_saas_catalog.py tests/test_saas_coverage.py
~~~

The final focused 2026-08-31 evidence run recorded `177 passed in 8.47s`;
additional repeats completed in 8.60 and 8.74 seconds, and an independent
repeat completed in 8.92 seconds. `compileall` and Ruff were clean, and
`mypy --strict` was clean across all 25 Plumber modules. This is focused
subsystem evidence, not a repository-wide test-suite claim.

An import, collection or test that attempts a socket is a failure. Do not
remove the socket gate or downgrade a warning to obtain a pass.

`--disable-socket` constrains these pytest processes only. Calling the local
API directly does not sandbox filesystem, subprocess, environment, network or
provider effects.

## Local-lab API boundary

- `LocalDevelopmentEnclave` requires the exact `INSECURE_OPT_IN_ACK` value.
- `LocalDevelopmentStarCustodyV02` and
  `LocalDevelopmentMagicStarReleaseBoundaryV02` require
  `allow_insecure_same_process=True`.
- These opt-ins enable an insecure laboratory path only; they cannot set
  `production_ready=True` or satisfy a promotion condition.
- Registered capability measurements are declared commitments, not measured
  executable identity or hardware attestation.
- `LocalReleaseEngine.issue_gate()` is the only supported gate issuer. A gate
  is bound to one exact inspection/evidence commitment, is consumed once, and
  expires with that inspection's aggregate evidence window. There is no
  independent shorter gate TTL.
- Packet inspection requires a registered temporal anchor and atomically
  reserves the prior state, increasing counter, nonce/replay token, canonical
  field and runtime commitments. The current replay store is in-memory, and
  inspection/execution accepts the caller's aware `now` value.
- The Spore manifest commits its stream identity and must exactly join packet,
  temporal epoch, challenge, ciphertext commitment and ciphertext size.
  Sympathetic identity must recompute from the joined evidence and match the
  trust policy's pinned hardware and operator commitments.
- Field, Heart, Conscience and governance receipt authorities must use
  distinct identifiers and keys. The retained HNC AEAD nonce must be valid
  base64url that decodes to exactly 12 bytes.
- The 528-centre Heart precondition must embed a valid existing
  `aureon.plumber.receipt.v0` Heart `SignedReceipt`. Its signer, packet,
  session, purpose, source, temporal, observer, policy, runtime and time window
  must exactly join the v0.2 release.
- Every Star point carries an explicit signed `APPROVE` verdict. A signed
  `VETO`, four-of-five point set or four-of-five permit set is denial.
- All five XOR shares and all local authority services remain co-resident in
  one process; they model role joins, not distributed threshold custody.
- A registered capability is bound to its policy commitment. Substitution of
  another capability or policy is denial, and the last expiry decision and
  receipt issuance use the same checked time sample.
- Handler exceptions are converted to a stable, non-secret failure without
  propagating their message or traceback cause. The laboratory implementation
  catches `BaseException`, so it also swallows `KeyboardInterrupt` and
  `SystemExit` instead of propagating them.
- Direct custody pops one-use material before handler invocation. Do not treat
  direct custody as a standalone terminal-state API: the outer release
  boundary owns post-pop success/denial handling.
- Release state is consumed before EPAS finalization. These in-memory updates
  are ordered but non-atomic; an EPAS failure cannot roll back a consumed
  release state.
- A consumed challenge, release session, custody record or EPAS predecessor is
  one-use. Build a fresh fixture after denial; never bypass replay controls.

## Production-promotion HOLD semantics

This matrix names required production outcomes. The current v0.2 laboratory
API has no production HOLD enum: it returns `ReleasePhase` values,
`production_ready=False`, and lower-case `ReleaseBoundaryError.code` values.
Labels such as `HOLD_MISSING_LIVE_EVIDENCE` below are policy semantics, not
implemented runtime reason-code spelling.

| Observation | Required result |
|---|---|
| No fresh validated canonical HNC field | HOLD_MISSING_LIVE_EVIDENCE |
| No hardware-rooted identity/attestation provider | HOLD_MISSING_HARDWARE_EVIDENCE |
| Test-only or in-memory source provider | LAB only; never production release |
| Missing protected counter or replay store | HOLD_MISSING_TEMPORAL_EVIDENCE |
| Gate unissued, wrong-inspection, reused, expired or evaluated before its window | DENIED; no capability invocation |
| Heart/Conscience/governance value is unsigned or in-process only | HOLD_MISSING_POLICY_EVIDENCE |
| Required authority class absent | HOLD_MISSING_QUORUM |
| Socket/provider/signing service unavailable | HOLD_PROVIDER_UNAVAILABLE |
| Runtime, packet, purpose, session or receipt mismatch | DENIED and quarantine |
| Fragment incomplete, mixed, duplicated, stale or tampered | DENIED; no reassembly |
| Secret canary appears in telemetry | FAIL gate and quarantine evidence |

Use actual emitted schema values in machine evidence. This table does not grant
permission to invent a success fallback.

## Evidence handling

May be recorded:

- commit, branch and explicit dirty-state description;
- Python/dependency versions;
- tracked module paths, sizes and SHA-256 hashes;
- exact commands, counts, durations and return codes;
- packet/receipt identifiers and commitments;
- policy versions and non-secret signer identifiers; and
- HOLD, DENIED or LAB-VALIDATED reason codes.

Must never be recorded:

- plaintext or plaintext-derived reconstruction hints;
- private, root, authority-share or session keys;
- credentials, tokens, biometric templates or provider secrets;
- unrestricted exception payloads containing protected input; or
- a production-ready claim based on a fake-provider pass.

The current direct-encoding canary checks cover selected serialized outputs;
they do not prove noninterference, covert-channel resistance or absence of
transformed/snippet leakage from a malicious handler. `CONSUMED`,
`plaintext_returned=False` and a valid signed result mean only that the local
protocol path completed under its fixtures.

Keep evidence metadata-only. Do not publish, upload or send a receipt without a
separate explicit instruction and provider read-back.

## Stop and incident procedure

Stop immediately when a test:

- attempts network or external mutation;
- requests credentials or live/hardware evidence not available in the lab;
- produces plaintext outside a test-owned temporary capability;
- indicates replay, rollback, clone or policy divergence;
- mutates operational state; or
- conflicts with concurrent repository work.

Preserve the exact command, return code, stable reason code, hashes and redacted
metadata. Do not retry with live flags, bypass the immune gate, delete
operational evidence or claim that best-effort memory clearing erased a secret.

## Promotion conditions

The subsystem remains local-lab/HOLD until all of the following have independent
evidence:

1. hardware-rooted source identity and runtime measurement;
2. protected monotonic temporal/replay state;
3. independently hosted packet-bound policy signing;
4. mandatory-class threshold key custody;
5. isolated purpose-specific release capability;
6. full attack-laboratory and leakage suite;
7. deterministic vectors and dependency review; and
8. external cryptographic review.

Only a separately approved work order may add a production endpoint, CLI
release command or public security claim.
