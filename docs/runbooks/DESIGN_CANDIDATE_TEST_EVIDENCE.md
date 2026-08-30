# Trusted staged-candidate test evidence

Status: local evidence control only  
Policy schema: `aureon.design-candidate-test-policy.v1`  
Receipt schema: `aureon.design-candidate-test-evidence.v2`  
Implementation: `aureon/operator/design_candidate_test_evidence.py`

## Purpose

A design worker's statement that tests passed is not test evidence. This
control lets an operator pin one complete, ordered suite to one already
validated staged candidate and then derive status from the subprocess exit
code and integrity observations.

The caller supplies only:

- the policy file;
- the exact SHA-256 of the policy **file bytes**;
- the complete ordered command-ID list already present in the policy; and
- an optional receipt ID and clock value.

There is no parameter for an executable, argument, environment variable,
shell, retry, width, browser, pass state, or raw output. A caller cannot select
a passing subset: the requested IDs must equal the complete ordered policy.

## Authority boundary

The control grants no authority to:

- validate or promote a candidate;
- mutate the canonical `website/` tree;
- build or approve a package;
- release or deploy;
- access credentials; or
- treat a passing test as human visual acceptance.

Both policy and receipt carry exact negative authority objects. Any extra,
missing, or changed authority value fails replay.

## Honest execution boundary

The module supplies a small sanitised environment, does not inherit arbitrary
developer variables, enables Python isolation, sets package managers offline,
and sends common HTTP proxy variables to a loopback null route. A named
OS-runtime allowlist (`COMSPEC`, `LOCALAPPDATA`, `PATHEXT`, `PROGRAMFILES`,
`PROGRAMFILES(X86)`, `SYSTEMROOT`, `TEMP`, `TMP`, `WINDIR`) is copied only
when present and is listed explicitly in the receipt. The operator tool and
executable are hash-pinned.

Node discovery is stricter than that environment allowlist. The shared resolver
never consults `PATH`, `PATHEXT`, registry aliases, package-manager shims, or a
caller-provided locator. It accepts only the source-reviewed absolute
`C:/Program Files/nodejs/node.exe` binding for Windows v24.14.0 when both its
91,380,224-byte size and SHA-256
`63C259C81E5D472B5F11C8D506070130CB04A1ECF84B80377A34ED6EC9048088`
match. The manifest has its own source-pinned canonical hash. Compilation,
policy replay, and later evidence execution all call this same resolver. A Node
upgrade, relocation, or non-Windows host fails closed until a reviewer updates
the source binding; there is no ambient fallback.

This is **not** a kernel network sandbox and is **not** a filesystem sandbox.
A reviewed tool can deliberately open a raw socket or write elsewhere in the
repository. The policy therefore states
`offline-intent-no-kernel-network-sandbox`; the receipt states the same
residual limitation. Do not describe this as OS-enforced network denial.

Endpoint filesystem mutation is detected, not prevented, on these exact
surfaces:

1. the staged candidate website tree;
2. the candidate receipt file;
3. the exact policy file;
4. every trusted tool input;
5. the canonical website tree; and
6. the policy's scoped repository-control manifest;
7. the interpreter executable;
8. the loaded candidate-test-evidence implementation; and
9. the loaded secure immutable-writer implementation.

All nine are observed immediately before and after every executed command. A
different post endpoint makes the command and suite fail. This is endpoint
consistency, not continuous monitoring: a mutate-then-restore action between
the observations, or a detached write after the post endpoint, is not
observed. An equally privileged same-user process can also mutate
implementation bytes, run, and restore them between observations. Without OS
process/filesystem isolation this is not prevented and the receipt cannot be
described as origin attestation. The scoped manifest must include
`pyproject.toml` and every trusted command input. Add further files or trees
that the suite must prove remained unchanged. Files or trees omitted from that
manifest remain a stated residual detection gap.

## Policy contract

The policy is strict JSON: duplicate keys, non-finite values, unknown fields,
links, reparse traversal, hard-linked files, stale hashes, and path escapes
are rejected.

Top-level fields are exactly:

```json
{
  "schema": "aureon.design-candidate-test-policy.v1",
  "policy_id": "candidate-suite-v2-<lowercase-content-sha256>",
  "candidate": {},
  "repository_control": {},
  "required_command_ids": [],
  "commands": [],
  "execution": {},
  "authority": {}
}
```

### Candidate binding

`candidate` contains exactly:

- `receipt_path`: repository-relative path to one
  `aureon.design-candidate.v1` receipt;
- `receipt_file_sha256`: exact candidate-receipt file-byte hash;
- `receipt_json_sha256`: canonical JSON hash;
- `tree_sha256`: exact staged website tree hash.

The candidate receipt must still be boolean-passed `validated-local`, retain
negative package/release/deploy/credential authority, and match current tree
hash, file count, and byte count. The receipt and website must be under one
staged candidate root.

### Repository control

`repository_control` contains exactly:

```json
{
  "canonical_website_path": "website",
  "canonical_website_tree_sha256": "<UPPERCASE_SHA256>",
  "entries": [
    {
      "path": "pyproject.toml",
      "kind": "file",
      "sha256": "<UPPERCASE_SHA256>"
    }
  ],
  "manifest_sha256": "<CANONICAL_JSON_SHA256_OF_ENTRIES>"
}
```

Entries are sorted by path, unique, repository-relative, outside the staged
candidate, and use `file` or `tree`. A tree hash is the canonical JSON hash of
its sorted `{path, sha256, bytes}` manifest. All files and tree members must be
regular, non-link, non-reparse entries with one hard link.

### Command templates

Each command has exactly `id`, `template`, and `template_sha256`. The template
hash is the canonical JSON SHA-256 of:

```json
{
  "engine": "python",
  "argv": [
    "{python}",
    "-I",
    "{repo_root}/tools/reviewed_candidate_check.py",
    "{candidate_root}"
  ],
  "cwd": ".",
  "timeout_seconds": 120,
  "viewport_widths": [],
  "trusted_inputs": [
    {
      "path": "tools/reviewed_candidate_check.py",
      "sha256": "<UPPERCASE_SHA256>"
    }
  ],
  "tool_executable_sha256": "<UPPERCASE_SHA256>",
  "required_outputs": [
    "exit-code",
    "stdout-sha256",
    "stderr-sha256"
  ]
}
```

Interpreter grammar is deliberately narrow:

- Python: `{python} -I {one hash-bound .py tool} [tool arguments]`;
- Node and Playwright: `{node} {one hash-bound .js tool} [tool arguments]`.

The trusted tool must occupy the sole executable-script position. An unused
trusted-tool argument cannot bless Python `-c`, `-m`, stdin, Node `-p`,
`--input-type`, preload/import/require, inspector, eval, or another execution
route. Raw absolute paths, URLs, shell fragments, environment assignments,
unknown placeholders, and parent traversal are rejected. `shell=False` and
closed stdin are fixed.

Supported engines are:

- `python`;
- `node`;
- `playwright-chromium`;
- `playwright-firefox`;
- `playwright-webkit`.

Plain Python and Node commands may not claim viewport coverage. A Playwright
template must claim at least one sorted, unique supported width from:
`320, 360, 390, 768, 1280, 1440, 1920`. These claims come from the pinned
operator policy, never worker output.

### Fixed execution policy

`execution` must equal:

```json
{
  "mode": "ordered-once-fail-fast",
  "shell": false,
  "inherit_environment": false,
  "network": "offline-intent-no-kernel-network-sandbox",
  "output_privacy": "sha256-only",
  "preserve_failures": true,
  "retry_count": 0
}
```

A non-zero exit, timeout, output-limit breach, tool-version failure, spawn
failure, or endpoint-integrity drift is retained as the first failed
observation. It is never retried. Stdout and stderr are captured to anonymous
temporary files, hashed without being retained in the receipt, and actively
polled against a 2 MiB per-stream threshold. A final size check catches a fast
process that exits between polls. This bounds in-memory capture but is not an
OS disk quota; a fast process can transiently exceed the threshold before it is
killed or observed. Remaining commands are recorded as
`not-run-prior-failure`, so omission cannot be reinterpreted as success.

## Execution and immutable receipt

```python
import hashlib
from pathlib import Path

from aureon.operator.design_candidate_test_evidence import (
    execute_candidate_test_evidence,
    verify_candidate_test_evidence_receipt,
    write_candidate_test_evidence_receipt,
)

root = Path(r"C:\path\to\Aureon-OS")
policy_path = root / "artifacts/website-operator/pinned-candidate-test-policy.json"
# Load this from an independently preserved trusted orchestration/owner seal.
# Never treat a hash freshly computed from an untrusted live policy as approval.
trusted_policy_file_sha256 = "<UPPERCASE_SHA256_FROM_TRUSTED_POLICY_SEAL>"
observed_policy_file_sha256 = hashlib.sha256(
    policy_path.read_bytes()
).hexdigest().upper()
if observed_policy_file_sha256 != trusted_policy_file_sha256:
    raise RuntimeError("Pinned policy file no longer matches its trusted seal")

receipt = execute_candidate_test_evidence(
    policy_path,
    expected_policy_sha256=trusted_policy_file_sha256,
    command_ids=["javascript-syntax", "candidate-visual-check"],
    repo_root=root,
    receipt_id="candidate-tests-v30",
)

candidate_root = root / receipt["candidate"]["root"]
receipt_path = candidate_root / "candidate-test-evidence.v2.json"
write_candidate_test_evidence_receipt(
    receipt,
    receipt_path,
    policy_path=policy_path,
    expected_policy_sha256=trusted_policy_file_sha256,
    repo_root=root,
)

receipt_file_sha256 = hashlib.sha256(receipt_path.read_bytes()).hexdigest().upper()
verification = verify_candidate_test_evidence_receipt(
    receipt_path,
    expected_receipt_file_sha256=receipt_file_sha256,
    policy_path=policy_path,
    expected_policy_sha256=trusted_policy_file_sha256,
    repo_root=root,
)
```

The output directory must already exist below the staged candidate root and
outside its hash-bound website subtree. Creation uses the shared handle-bound
immutable-artifact writer: kernel-resolved final path and identity remain
bound through same-handle and post-close byte/identity read-back. NTFS
alternate streams are rejected. An existing receipt is never replaced. The
writer also requires a process-local fresh-issue token created by
`execute_candidate_test_evidence`, which prevents ordinary code from rewriting
a mapping and passing it to the writer in the same workflow. This token is a
single-use token claimed atomically under a lock before validation or I/O; two
concurrent writers cannot consume one issuance. A failed write does not make
the issuance replayable. This is a misuse guard, not a cryptographic signature
or cross-process origin attestation.

The strict file verifier requires an external exact receipt-file SHA-256 and
rejects links, reparse traversal, hard links, duplicate JSON keys, input drift,
and self-hash drift. The external hash is trustworthy only when trusted
orchestration seals it immediately after the fresh writer returns and preserves
that seal independently. An attacker-selected receipt plus attacker-selected
hash is not origin evidence.

Every public execute, validate, write, and verify entrypoint also compares the
loaded evidence and immutable-writer source hashes with their current
single-link source files. A long-lived process therefore fails closed if
either file changes after import, instead of executing cached bytes while
binding different on-disk control bytes.

## Receipt evidence

For every command, the receipt binds:

- command ID, template hash, engine and pinned width claims;
- exact expanded argv hash and candidate-relative working directory;
- sanitised environment key/value hashes;
- trusted-input manifest hash;
- tool executable file and path hashes;
- tool-version argv, exit code, stdout hash, and stderr hash;
- start/end UTC timestamps and monotonic duration;
- one attempt, zero retries, timeout and exit code;
- stdout/stderr SHA-256 and byte count with `retained: false`;
- before/after endpoint-integrity hashes for all nine controlled surfaces;
- exact candidate-test-evidence and secure-writer implementation hashes.

Pass is derived only when the tool-version probe exits zero, the exact command
exits zero, required outputs exist, no timeout occurs, and every integrity
surface has matching trusted endpoints. Strings such as `"passed"` are
rejected.

`validate_candidate_test_evidence_receipt` returning `passed: true` means the
receipt structure and current live bindings replayed correctly. It explicitly
returns `origin_attested: false` and
`trusted_orchestration_seal_required: true`; pure validation cannot prove that
the executor originated a mapping. Its `evidence_passed` field separately
states whether the represented suite passed. A correctly preserved non-zero
or timeout receipt therefore has verifier `passed: true` and
`evidence_passed: false`.

## Required release interpretation

This receipt is one post-patch test observation. It does not replace:

- staged candidate validation and claim-surface replay;
- browser-source and visual evidence;
- named human pixel/brand acceptance;
- accessibility and motion review;
- verified live backup;
- package-hash approval;
- Home.pl deployment controls; or
- production HTTPS read-back.

Never promote `evidence_passed: true` into candidate, package, release, or
deployment authority.
