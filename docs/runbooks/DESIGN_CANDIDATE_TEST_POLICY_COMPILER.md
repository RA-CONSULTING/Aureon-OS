# Candidate test policy compiler

## Purpose

`aureon/operator/design_candidate_test_policy_compiler.py` closes policy
shopping between staged candidate validation and trusted local QA. A design
worker cannot supply command ids, commands, arguments, interpreters, timeouts,
trusted inputs, source configuration, output location, retry behaviour, or a
pass/fail interpretation.

The compiler reads only:

1. one exact current-contract boolean-passed
   `artifacts/website-candidates/<run-id>/candidate.v1.json`;
2. the fixed `aureon/operator/website_operator.defaults.json`;
3. the fixed candidate-safe Python and Node adapters;
4. the current Python executable bytes and the source-pinned reviewed Node
   v24.14.0 absolute-path, size, and SHA-256 binding;
5. `pyproject.toml`, the complete AST-derived executable-source closure, and
   the current canonical `website/` tree for repository-control binding.

The compiler calls the complete staged-candidate/work-order verifier with only
the historical baseline-current check relaxed. Exact receipt, work-order,
candidate and authority fields remain mandatory. A structural receipt or a
caller-selected receipt hash is not execution origin and is insufficient.
Before replay, the compiler applies the same exact runtime field-and-type
contract as candidate control and its strict raw JSON parser rejects duplicate
keys and non-finite numbers. The verifier reloads the candidate's fixed,
create-once `candidate-validation-input.v1.json` sidecar and derives the replay
instant, claim declarations, and claim-surface context and manifest only from
that sidecar. The receipt binds the exact sidecar path, raw file SHA-256,
canonical JSON SHA-256, and payload self-hash. Complete type-strict recursive
receipt equality means boolean/integer substitutions, unknown nested fields,
appended checks, altered gates, receipt-only timestamps, or substituted claim
contexts cannot be smuggled into compilation.

The sidecar is local provenance, not a trusted wall clock, operating-system or
input-origin attestation. It grants no authority and changed immutable inputs
require a successor candidate rather than an overwrite.

The immutable validation input and receipt bind a sorted raw-byte manifest for
all 15 currently reachable local Python sources: both compilers, candidate
control, all direct and conditional validation dependencies, the closure
helper, and both executed package initializers. The manifest is derived from
the AST using repository-root-only resolution. Missing, extra, relocated,
linked, reparsed, hard-linked, alternate-stream-shaped, or byte-different
sources fail before candidate-control replay.

The manifest explicitly records the runtime-dead `TYPE_CHECKING` branch and
the bounded lazy-export sites in the two package initializers. It does not
silently treat an unresolved dynamic import as safe. The sealed direct-file
ingress installs a first-position raw-source loader for the bound modules, so
ambient import hooks and cached bytecode cannot substitute their execution.

It does not execute tests. It does not mutate the candidate or canonical
website. It grants no candidate validation, promotion, package, release,
credential, or deployment authority.

## Fixed projection

The complete ordered executable suite is:

1. `candidate.website-operator-static.v1`;
2. `candidate.javascript-syntax.v1`;
3. `candidate.v28-design-system-static.v1`;
4. `candidate.v28-metadata-ethos-static.v1`.

The source check `v28-composite-visual-release-gate` is bound and recorded as
`deferred-to-source-bound-visual-review`. It is never translated into a static
pass and is never included in the executable candidate suite.

The entire WebsiteOperator source-policy file is hard-pinned to reviewed hash
`3956D6AACC2B122086D8E2AC1FBB93AB9D01750CAE9B693D2C6DB6148F31741D`.
Any byte change, including an optional check, relaxed budget, route, authority
or packaging/deployment setting, blocks until an explicit code review updates
the pin. The known external checks are then projected exactly.

## Immutable output and replay

The v2 policy id is the full SHA-256 content address of a canonical core that
includes the exact candidate and receipt, source policy, mappings, commands,
trusted tools, interpreter hashes, repository/canonical-tree control,
execution policy, authority and compiler hash. The writer chooses the only
permitted location:

```text
artifacts/website-operator/candidate-test-policies/<policy-id>.json
```

An exact existing content address is verified idempotently and never
overwritten; a legitimate changed core receives a different path so revisions
coexist. V1 paths remain historical staleable evidence. The writer accepts
only a fresh same-process compiler result and uses
handle-bound creation through `secure_immutable_artifact`. Kernel-resolved
final path and file identity remain bound through same-handle and post-close
read-back. Alternate streams are rejected and replay failures never trigger
lexical-path deletion.

`verify_compiled_candidate_test_policy_file(...)` is the trusted runner seam.
It does not trust an arbitrary policy path and hash. It recompiles the fixed
policy from the exact candidate, current source policy, current tools,
interpreters, and canonical tree; requires the fixed output path; compares
exact file bytes; and then requires the strict test-evidence parser to accept
the policy. A caller-provided substitute policy and its matching substitute
hash still fail.

The runner must preserve the returned policy file hash independently and pass
that exact hash to `design_candidate_test_evidence`. The worker submission must
not contain a policy path, hash, command id, test manifest, or test result.

The public website runner does not import either compiler. It verifies the
fixed policy before any QA engine or immutable attempt claim by launching this
exact file in a fresh process with `sys.executable -I -S -B`, an absolute
compiler path, repository-root `cwd`, `shell=False`, a fixed minimal environment
that inherits no caller or `PYTHON*` variables, a 300-second timeout and no
retry:

```powershell
python -I -S -B aureon/operator/design_candidate_test_policy_compiler.py `
  --verify-policy artifacts/website-operator/candidate-test-policies/<content-address>.json `
  --expected-policy-sha256 <UPPERCASE-SHA256> `
  --candidate-receipt artifacts/website-candidates/<run-id>/candidate.v1.json
```

Verifier mode is read-only: it creates no directory or policy and emits no
bytecode. The runner accepts exactly one UTF-8 canonical compact JSON object
terminated by one LF. Duplicate keys, non-finite values, trailing or second
JSON values, non-canonical bytes, stderr, and output larger than 64 KiB are
rejected. Stdout and stderr are drained concurrently while hashes and byte
counts are updated incrementally; at most 64 KiB is retained across both pipes
and per stream. The first excess byte stops the child, and timeout/overflow
cleanup terminates then kills and waits for the same one process. The exact
response field set, schema, authority, candidate/policy
paths and all bound hashes must match before the candidate-QA attempt is
claimed or any motion/test engine runs.

The compiler and the downstream evidence executor share the reviewed Node
resolver. `PATH`, `PATHEXT`, registry aliases, and shims cannot select the Node
whose SHA-256 enters a policy. The current Windows binding is v24.14.0 at
`C:/Program Files/nodejs/node.exe`, 91,380,224 bytes, SHA-256
`63C259C81E5D472B5F11C8D506070130CB04A1ECF84B80377A34ED6EC9048088`.
Upgrade, relocation, and portability to another platform are explicit source
review events and fail closed until the binding is updated.

## Command-line interface

The existing write-mode CLI still has one input and no policy-selection
controls:

```powershell
python -I -S -B aureon/operator/design_candidate_test_policy_compiler.py `
  --candidate-receipt artifacts/website-candidates/<run-id>/candidate.v1.json
```

It prints one canonical JSON verification object. The object records the fixed
ordered command ids and the deferred composite source id. It does not claim
that tests ran or that the composite visual release gate passed.

Direct execution of the compiler file is the only sealed pre-import ingress.
Do not replace it with `python -m`, because Python would execute
`aureon/__init__.py` and `aureon/operator/__init__.py` before compiler
preflight. Imported functions remain available for trusted in-process
inspection and reject current closure drift at call time, but they do not
claim prevention before package-initializer execution.

## Residual boundary

Deterministic replay proves that current bytes equal the compiler's current
fixed projection. It is not independent provenance attestation, and the
verification object therefore reports `origin_attested: false`.

The downstream test-evidence executor still has its documented
`offline-intent-no-kernel-network-sandbox` and endpoint-consistency limitations.
Source-bound browser evidence, named human pixel review, owner visual
acceptance, WebsiteOperator promotion, packaging, and live deployment remain
separate gates.
