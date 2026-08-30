# Aureon public website staged-delivery V2 runbook

## Purpose and authority boundary

V2 coordinates one local, source-bound website candidate. It does not mutate
`website/`, promote a candidate, build a release package, access credentials,
or deploy. `awaiting-owner-promotion` means that the local evidence chain is
complete enough for a separate WebsiteOperator owner gate; it is not release
authority.

Historical V1 runner and worker-broker receipts remain verifiable evidence
only. No V1 job, lease, issuance, execution, or outcome may advance through a
V2 state-changing entrypoint.

## State sequence

```text
work-order-ready
  -> candidate-staged
  -> candidate-assets-ready (when required)
  -> candidate-validated
  -> candidate-qa-verified | candidate-qa-repair-required
  -> awaiting-browser-evidence | initial-gate-rejected
  -> awaiting-owner-promotion | visual-review-repair-required
```

The initial browser gate accepts only `candidate-qa-verified`. Every state
after candidate QA replays the unchanged QA claim, fixed compiler
verifications, trusted-toolchain hashes, configuration and policy hashes,
candidate and canonical tree hashes, and immutable motion/test receipts. The
candidate binding carries both historical tree algorithms and hashes from one
captured byte manifest; its manifest hash must equal the V2 motion-compiler
verification before the attempt is claimed and on every later replay.

## Worker-broker boundary

The V2 broker accepts declarative patch, claim-impact, claim-surface, and
feedback-response manifests only. A worker cannot select tests, commands,
interpreters, arguments, timeouts, thresholds, origins, or QA evidence.

Any `test_manifest` key is rejected recursively before the adapter writes a
candidate byte. A successful broker run stops at `candidate-validated`; it
cannot assert either candidate-QA state or enter the browser gate.

## Trusted one-attempt candidate QA

Before invoking `candidate-qa`, the trusted operator must have:

1. the exact passed candidate validation receipt;
2. the fixed candidate motion configuration produced for that candidate by
   the reviewed motion-config compiler;
3. the fixed candidate test policy produced for that candidate by
   `design_candidate_test_policy_compiler`;
4. independently captured uppercase SHA-256 hashes for both files.

Raw path-plus-hash inputs are insufficient. The runner replays both fixed
compilers against the exact candidate and reviewed source configurations
before it creates the attempt claim.

The V2 runner does not import either compiler. It delegates each read-only
verification to the exact absolute compiler file with
`sys.executable -I -S -B`, repository-root `cwd`, `shell=False`, a fixed
minimal child environment that inherits no caller or `PYTHON*` variables, a
bounded 300-second timeout and no retry. Each verifier must return exactly one UTF-8
canonical compact JSON object with one LF and empty stderr; duplicate keys,
non-finite values, additional/trailing JSON, non-canonical bytes and output
larger than 64 KiB fail closed. Concurrent pipe drainers hash and count without
retaining more than 64 KiB aggregate or per stream; overflow and timeout stop,
wait for, and clean up the same one child without a retry. The runner checks the exact schema, authority,
candidate and compiled-artifact paths, and bound hashes before it creates the
attempt claim or runs either QA engine. Imported compiler functions remain
available only as drift-check interfaces and do not claim pre-initializer
sealing.

The fixed test-policy compiler and downstream evidence executor share one
source-pinned Node resolver. It never consults ambient `PATH`, `PATHEXT`,
registry aliases, or shims. The reviewed Windows v24.14.0 binding is the exact
absolute `C:/Program Files/nodejs/node.exe`, 91,380,224 bytes, SHA-256
`63C259C81E5D472B5F11C8D506070130CB04A1ECF84B80377A34ED6EC9048088`.
An upgrade, relocation, or another platform blocks until that source trust
anchor is reviewed and changed; no discovered executable can become policy.

The compiler compilation and verification envelopes are V2. The executable
test-policy payload deliberately remains
`aureon.design-candidate-test-policy.v1`; its
`policy_content_core_sha256` is separately bound by the V2 compiler
verification. Candidate-test execution and structural verification use
`aureon.design-candidate-test-evidence.v2` and
`aureon.design-candidate-test-evidence-verification.v2`, with the immutable
receipt written as `candidate-qa/candidate-test-evidence.v2.json`.

The entrypoint shape is:

```powershell
python -m aureon.autonomous.aureon_public_website_design_runner `
  --repo-root <repo> candidate-qa `
  --run-id <run-id> `
  --motion-config <fixed-motion-config-path> `
  --motion-config-sha256 <UPPERCASE-SHA256> `
  --test-policy <fixed-test-policy-path> `
  --test-policy-sha256 <UPPERCASE-SHA256>
```

Immediately before claiming, the runner proves that its own source and the
complete compiler-bound source closure still equal current controlled files.
It checks them again after execution. This rejects current source drift; the
separate direct-file ingress is required to exclude ambient import hooks and
cached bytecode before local modules execute.

The candidate tree is read once into one sorted byte manifest. From that
single capture the runner binds the candidate-control tree hash, motion tree
hash, both algorithm identifiers, and `captured_manifest_sha256`. The motion
compiler must replay the same five values plus its reviewed source-policy hash;
two independently sampled or A/B-swapped candidate trees are rejected before
the attempt claim.

The runner then writes one immutable `attempt.v2.json` claim through the
shared handle-bound writer. The writer proves the created object identity,
final kernel path, exact bytes, and same-handle read-back; failure cleanup
cannot unlink a later lexical substitute. From that point the attempt is
consumed even if execution crashes or evidence fails. Execution order is
fixed:

1. run and immutably replay the complete motion/performance budget;
2. only when motion passes, execute the complete ordered test policy;
3. write, read, and structurally replay the test receipt in the same trusted
   process;
4. prove that neither the candidate nor canonical website changed;
5. write `candidate-qa-verified` only when both gates pass.

There is no retry, alternate policy, alternate threshold set, command subset,
or relaxed configuration within the run. A failure is preserved as
`candidate-qa-repair-required`, or as an orphan consumed claim when failure
occurs after the claim but before an advancing receipt. A successor requires a
separately authorised new delivery run.

## Read-back checks

After any state change:

1. load the latest numbered delivery receipt;
2. run the `status` action and require `verification.passed` to be `true`;
3. inspect the `compatibility` value (`current-v2` or
   `historical-v1-read-only`);
4. require `candidate-qa-binding`, `initial-gate-binding`, and
   `visual-review-binding` to pass whenever their states apply;
5. compare the canonical website tree binding with its pre-run value.

Do not describe a staged candidate, QA pass, browser capture, or
`awaiting-owner-promotion` receipt as a live deployment. Deployment requires a
separate owner-controlled WebsiteOperator flow and provider read-back.
