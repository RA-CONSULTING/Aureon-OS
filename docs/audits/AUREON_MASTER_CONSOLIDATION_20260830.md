# Aureon master-system consolidation receipt — 2026-08-30

## Status

- Candidate checkout: `C:\Users\user\Aureon-OS-master-consolidation-20260830_210920`
- Candidate branch: `consolidate/master-system-20260830`
- Publication state: **LOCAL CANDIDATE — GitHub publication and provider read-back pending**
- Runtime mode used for validation: offline, dry-run, audit, and import-side-effect suppression

This receipt records source reconciliation. It does not authorize or claim a live trade,
grant/portal submission, email send, filing, deployment, identity action, or finance action.
Every pre-existing checkout remains in place; none was pulled, reset, cleaned, stashed, or
overwritten.

## Inventory boundary

Twenty-five valid pre-existing Aureon Git worktrees were found directly under
`C:\Users\user`; this dated candidate is the twenty-sixth. `aureon-trading` has an invalid,
empty `.git` directory and was not treated as a source worktree. Other Aureon-named folders
without `.git` were retained as non-Git evidence, release, appliance, backup, or tool folders.

| Checkout or group | Observed HEAD | Reconciliation |
| --- | --- | --- |
| `Aureon-OS` | `047d0a863e1e` | Dirty original; preserved and separately audited |
| `Aureon-OS-github-latest-20260714_123957` | `54f3f9c9a291` | Historical ancestor |
| `Aureon-OS-github-latest-20260714_143606` | `1157e3b78f33` | Historical ancestor |
| `Aureon-OS-github-latest-20260714_152836` | `dd1eff78046c` | Historical ancestor |
| `Aureon-OS-github-latest-20260714_181610` | `456cb9172f76` | Historical ancestor |
| `Aureon-OS-github-latest-20260714_214047` | `f16e5b770438` | Historical ancestor |
| `Aureon-OS-github-latest-20260715_120157` | `f7b629382e9f` | Historical ancestor |
| `Aureon-OS-github-latest-20260715_131031` | `d217c39e24fd` | Historical ancestor |
| `Aureon-OS-github-latest-20260715_143939` | `2f8516275133` | Historical ancestor |
| `Aureon-OS-github-latest-20260715_145258` | `b0e733d4df6f` | Historical ancestor |
| `Aureon-OS-github-latest-20260719` | `908c4c424d98` | Reviewed dirty website/operator layer |
| `Aureon-OS-github-latest-20260726_151235` | `a893c0713354` | Historical ancestor |
| `Aureon-OS-github-latest-20260726_234916` | `a893c0713354` | Historical duplicate |
| `Aureon-OS-github-latest-20260726_235845` | `a893c0713354` | Historical duplicate |
| Five `Aureon-OS-github-latest-20260727_*` checkouts | `a893c0713354` | Historical duplicates |
| `Aureon-OS-github-latest-20260728_071500` | `7440c66fa812` | Reviewed dirty accounting layer |
| `Aureon-OS-github-latest-20260810_091213` | `f5fb1916c07a` | Reviewed latest operator layer and runtime-file source |
| `Aureon-OS-aureon-selfbuild-20260816_132020` | `f5fb1916c07a` | Reviewed appliance layer |
| `Aureon-OS-benchmark-20260816` | `f5fb1916c07a` | Reviewed; regressive/generated benchmark deltas held |
| `Aureon-OS-autonomous-handoff-20260820_203535` | `f5fb1916c07a` | Reviewed autonomous/governance layer |
| `Aureon-OS-website-v45-20260820` | `65747fcf9b4f` | Merged current V45 website branch |

All historical-chain HEADs above are contained by the current upstream lineage; the V45
website branch is the intentional cloud divergence merged separately. No checkout had
local-only committed history that needed a wholesale branch merge. Dirty and untracked
working-tree source was therefore reconciled path by path.

## GitHub reconciliation

Live `git ls-remote` read-back on 2026-08-30 returned:

| GitHub branch | Read-back SHA | Candidate merge |
| --- | --- | --- |
| `main` | `f5fb1916c07ac26eb7fc38c34ff2dc9bd029e21d` | Candidate base |
| `recovery/plumber-main-export-20260827` | `03098b1eabd486839efe3b27ec64a4b81c33016e` | `c78f090f` |
| `website/v45-investor-rebuild-20260820` | `65747fcf9b4fd96e04646c30f26456db266b22fe` | `cc83287b` |

The recovery branch contributes its source-export workflow. The V45 branch contributes six
website commits and supersedes the older V28 website tree. Twenty-two other divergent remote
branches were patch-reviewed; twelve were patch-equivalent to main and the remaining old
patches were superseded, experimental, or unsafe to merge wholesale. A historical Flask-Cors
4-to-6 dependency-only patch remains conditional and was not imported without a current need.

## Selected local source imports

| Source checkout | Synthetic import commit | Selected paths | Principal decision |
| --- | --- | ---: | --- |
| autonomous handoff, 2026-08-20 | `6ac217bd` | 149 | Governance/operator source and tests; state logs and scratch output excluded |
| appliance self-build, 2026-08-16 | `b75805b2` | 25 | Appliance source and tests |
| accounting control plane, 2026-07-28 | `d56b938b` | 22 | Accounting source/tests; later vault predicates retained in conflicts |
| website/operator, 2026-07-19 | `af9aace9` | 204 | Governed operator/research source; V28, unlicensed images, temp/runtime output excluded |
| latest operator, 2026-08-10 | `c9cba9ff` | 117 | Tracked operator deltas and selected source/tests; logs and scratch examples excluded |
| original dirty checkout | pending final reviewed import | pending | Governed dormant grant/approval source and tests under independent review |

The V45/operator reconciliation keeps 41 executable core brain roles. Nine public-design roles
are registry-only and explicitly unprovisioned; they are not silently added to the executable
brain fabric. The latest `LocalActionBridge` merge retains blocked-result propagation so a
JSON result with `blocked=true` remains a HOLD. `RouteDecision` uses Python 3.11 `StrEnum`;
repository search found no external consumer and its JSON/value behavior is unchanged.

## Explicit holds and exclusions

- Runtime ledgers, receipts, backups, screenshots, generated website assets, caches, temporary
  files, and bulk grant evidence remain in their preserved source locations; they are not source
  code and were not copied into Git history.
- The benchmark checkout's tracked TSX delta reverses a later semantic-token change and was held.
  Its JSON audit output is reproducible/generated and was not imported.
- An experimental bootstrap patch has undefined imports, unsafe path handling, no bounds, and no
  tests; it was not imported.
- Supabase dirty functions that use service-role clients with caller-supplied `user_id` remain on
  HOLD pending explicit authorization and caller-scoped controls.
- The original checkout's broad console rewrite calls a helper at import time in many modules,
  contrary to its own main-entry-only contract. It requires a fresh bounded forward-port rather
  than a 263-file overlay.
- `aureon/core/aureon_lambda_engine.py` still defaults `BETA` to `1.0`; a dirty comment saying the
  runtime environment supplies `0.85` is not a source fix. A bounded source default/clamp and test
  remain a separate defect, not an environment-derived consolidation decision.
- Dated grant, state-support, website-release, and stakeholder evidence remains dated evidence.
  It is not current provider status or submission authority.
- `force_trade_all_platforms.py` was not executed.

## Cross-platform integrity and local runtime files

Six raw-hash-bound GUI fixtures are forced to LF in `.gitattributes` and were rematerialized
byte-identically to their Git blobs. The local benchmark manifest matches its pinned SHA-256
`e5ee3d3eee2a2f53e139cf662d169cadb04e65bbdaccc00118ecf1026e37c0bf`; the five-file CourseOps
tree matches root SHA-256 `94af778677996a90f47ca22a3cb5dee9798a4a5932714de295c76c8d138d9b3a`.

Runtime files were copied locally from the reviewed 2026-08-10 checkout without displaying their
contents and are excluded from Git:

| Local-only file | Bytes | SHA-256 | Ignore source |
| --- | ---: | --- | --- |
| `.env` | 14,853 | `0967c7ec0df3669b80a2b0e46e3783a8a441bb59002d8901e32328c5d54257f2` | `.gitignore` |
| `.env1` | 1,232 | `b3334d906cf7fe7ed10ba134eacefa57020dd3feb605a2da48c3dfa9ec141aa5` | clone-local `.git/info/exclude` |

## Validation record

The following completed under explicit offline/dry-run/audit/import-suppressed controls:

- website runtime and role registry: 36 passed
- website source rationalisation, motion compiler, secure artifact writer, and motion budget: passed
- SCORM-focused suite: passed
- governance group: 112 passed
- hash-bound local/CourseOps fixture group after LF repair: 51 passed
- state-support, grounded-action, desktop, and VM safety group: 28 passed
- selected economic-mutation governance group: 102 passed
- accounting integration tests: 80 passed
- isolated `Kings_Accounting_Suite`: 12 passed
- appliance packaging/workflow: 31 passed
- canonical bootstrap and unified organism builder: 7 passed
- `git fsck --no-dangling --no-reflogs`: passed

A high-confidence credential-pattern scan of the merged diff found only deliberately synthetic
negative-test fixtures in six test files; their values are test-only and no production credential
material was accepted from those signals.

Full-repository validation, final root-checkout import verification, final secret scan, GitHub
publication, and remote branch read-back are intentionally left pending here until their receipts
exist. A local test pass or commit is not a GitHub outcome.
