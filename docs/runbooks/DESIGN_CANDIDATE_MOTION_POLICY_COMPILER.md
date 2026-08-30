# Candidate motion-policy compiler

## Purpose

`aureon/operator/design_candidate_motion_policy_compiler.py` prevents
threshold shopping before staged-candidate QA. A caller-supplied configuration
and a matching caller-supplied hash are not enough.

The compiler accepts only an exact current-contract candidate whose complete
staged-candidate and v4 work-order replay passes; only the historical
baseline-current comparison may be relaxed. It captures one sorted byte
manifest and derives both the candidate-control tree hash and the
motion-control tree hash from that one observation. Verification reports both
hashes and both algorithms.

Before replay, the compiler applies the same exact runtime field-and-type
contract as candidate control and its strict raw JSON parser rejects duplicate
keys and non-finite numbers. Candidate replay reloads the fixed, create-once
`candidate-validation-input.v1.json` sidecar and derives the validation
instant, claim declarations, and claim-surface context and manifest only from
that immutable local input. The receipt binds its exact path, raw file SHA-256,
canonical JSON SHA-256, and payload self-hash. Complete type-strict recursive
receipt equality means boolean/integer substitutions, unknown nested fields,
appended checks, receipt-only timestamp shifts, substituted claim context,
altered gates, and injected authority markers fail before a motion
configuration can be compiled.

The sidecar is local provenance only. It is not trusted wall-clock,
operating-system, or input-origin attestation; it grants no authority, cannot
be overwritten, and changed immutable inputs require a successor candidate.

The sidecar and candidate receipt also bind the complete sorted
AST-derived raw-byte closure of all 15 currently reachable local Python
sources, including both package initializers and conditional editorial
validation dependencies. Exact replay rejects missing, extra, relocated,
linked, reparsed, hard-linked, alternate-stream-shaped, or byte-different
sources before candidate-control replay. Bounded dormant lazy exports and the
runtime-dead `TYPE_CHECKING` branch are explicit manifest exclusions. The
sealed direct-file ingress executes bound imports through a first-position
raw-source loader rather than ambient hooks or cached bytecode.

The following values are fixed in reviewed operator code:

- the exact design doctrine path and reviewed doctrine SHA-256;
- every byte, asset, media, JavaScript, CSS, HTML, font, motion-duration, and
  declaration-count threshold;
- zero allowed remote origins and no data URLs;
- forbidden autoplay, infinite animation, dynamic motion, and undeclared
  origins;
- mandatory reduced-motion override.

The entire WebsiteOperator source-policy file is hard-pinned to
`3956D6AACC2B122086D8E2AC1FBB93AB9D01750CAE9B693D2C6DB6148F31741D`.
Any route, budget, authority or other byte change blocks pending explicit code
review.

The worker and caller cannot supply a threshold, origin, policy value, output
path, retry, or decision.

## Fixed immutable output

The writer chooses the only output location:

```text
artifacts/website-operator/motion-performance-budget/candidate-configs/<config-id>.json
```

The v2 config id is the full SHA-256 of the exact canonical config file bytes.
An exact existing content address is verified idempotently; a legitimate
changed config receives a new coexisting path. V1 outputs remain historical
staleable evidence. Creation accepts only a fresh same-process compiler result
and uses the shared handle-bound immutable-artifact writer:
kernel-resolved final path and file identity remain bound through same-handle
and post-close read-back. Alternate streams are rejected, and a replay failure
never deletes a lexical path.

`verify_compiled_candidate_motion_config_file(...)` recompiles from current
trusted inputs, requires the exact fixed path and bytes, and requires the
motion-budget control to accept the configuration. A relaxed configuration
plus its matching substitute hash still fails.

## Runner contract

The historical imported verifier remains available for trusted in-process
inspection:

```python
verify_compiled_candidate_motion_config_file(
    config_path,
    expected_config_sha256=sealed_hash,
    candidate_receipt_path=candidate_receipt,
    repo_root=repo_root,
)
```

The public website runner does not import either compiler. Before claiming the
one-shot QA attempt it starts this exact compiler file in a fresh process with
`sys.executable -I -S -B`, an absolute compiler path, repository-root `cwd`,
`shell=False`, a fixed minimal environment with no caller or `PYTHON*`
inheritance, a 300-second timeout and no retry:

```powershell
python -I -S -B aureon/operator/design_candidate_motion_policy_compiler.py `
  --verify-config artifacts/website-operator/motion-performance-budget/candidate-configs/<content-address>.json `
  --expected-config-sha256 <UPPERCASE-SHA256> `
  --candidate-receipt artifacts/website-candidates/<run-id>/candidate.v1.json
```

This verifier mode is read-only: it must not create an output directory,
rewrite the configuration, or emit bytecode. The runner accepts exactly one
UTF-8 canonical compact JSON object terminated by one LF, rejects duplicate
keys, non-finite values, trailing or additional JSON, non-canonical encoding,
stderr and output larger than 64 KiB, then checks the exact field set, schema,
authority, candidate/config paths and all bound hashes before any motion audit
or candidate-QA attempt receipt can run. It preserves and replays the exact
verification object. The worker submission must not contain a motion config,
hash, threshold, origin, or audit result.

The runner drains stdout and stderr concurrently, hashes and counts bytes
incrementally, and retains at most 64 KiB across both pipes and per stream. An
excess byte or timeout stops the one child, escalates from terminate to kill if
needed, waits, joins both pipe drainers, and is never retried.

The compiler and verifier do not run the motion audit. The runner executes the
audit only after the immutable attempt claim exists.

## Sealed command-line ingress

The existing write-mode command remains supported and creates or replays the
one immutable content-addressed configuration:

```powershell
python -I -S -B aureon/operator/design_candidate_motion_policy_compiler.py `
  --candidate-receipt artifacts/website-candidates/<run-id>/candidate.v1.json
```

Do not use `python -m` for an exact pre-import claim: Python would execute both
package initializers before compiler preflight. Imported functions remain a
trusted in-process drift-check interface, not a pre-initializer execution
boundary.

## Authority and limits

Compilation grants no audit pass, candidate validation, promotion, package,
release, credential, network, or deployment authority. Verification reports
`origin_attested: false`; trusted orchestration must bind it into its own
immutable claim.

The generic motion CLI remains static audit tooling, not the candidate gate.
Candidate orchestration must use this compiler and verifier; it may not supply
an ad hoc generic configuration. The downstream motion control remains static analysis. Browser performance,
interaction parity, source-bound visual evidence, named human pixel review,
owner acceptance, promotion, packaging, deployment, and live read-back remain
separate gates.
