# Website runtime optimisation control plane (production blocked)

`aureon.operator.website_runtime_optimisation` can structurally validate a
measurement declaration and exercise proposal arithmetic in test fixtures. It
does not optimise files. Production proposal compilation and writing are
hard-blocked with
`blocked-reviewed-measurement-provenance-tool-not-installed`.

Structural validation is not freshness, provenance, derivative, execution, or
acceptance proof. In particular, a repo-relative tool path plus a self-supplied
hash cannot establish that projected bytes exist or that a measurement ran.

## Position in the website delivery chain

Production compilation may be reconsidered only after all of the following are
available and independently reviewed:

1. Home.pl has been read back and backed up through the owner-controlled gate.
2. One exact website source has been selected through the source-reconciliation
   protocol.
3. A current `aureon.website-source-rationalisation-plan.v1` identifies the
   exact retained public-runtime closure.
4. A reviewed, pinned read-only measurement tool has produced immutable strict
   JSON evidence using
   `aureon.website-runtime-optimisation-measurement-evidence.v1` and recorded
   its exact invocation provenance.
5. The measurement evidence binds the exact source plan and
   `data/website_operator/browser_acceptance_contract.v1.json` by path, file
   SHA-256, and payload SHA-256.
6. Every proposed derivative has an independently readable controlled artifact
   path, SHA-256, byte count, and decoded dimensions bound to the evidence.

The evidence and proposal formats are independently pinned by strict Draft
2020-12 schemas:

- `docs/research/schemas/AUREON_WEBSITE_RUNTIME_OPTIMISATION_MEASUREMENT_V1.schema.json`
- `docs/research/schemas/AUREON_WEBSITE_RUNTIME_OPTIMISATION_PROPOSAL_V1.schema.json`

The capability registry requires both schema files to match their reviewed
SHA-256 values before it reports the structural-validation source contract as
available. It still reports production compilation unavailable.

The compiler and registry also pin the canonical payload SHA-256 of
`data/website_operator/browser_acceptance_contract.v1.json`. Recomputing the
contract's embedded hash after weakening any nested criterion is insufficient:
the reviewed payload pin must still match. Updating that pin is a source-review
event and is never inferred from a modified contract file.

The current human Markdown asset/CSS audit is useful design evidence, but is
not a machine-authoritative measurement input. It must not be scraped into a
proposal or treated as transformation proof.

## What the installed source proves

The private test-fixture compiler path:

- accepts explicit input paths and caller-supplied uppercase SHA-256 values;
- rejects "latest" discovery, stale inputs, duplicate JSON keys, unsafe paths,
  links, reparse points, hard links, oversized inputs, or source drift;
- replays the exact canonical `website/` manifest and reviewed source-planning
  tool bindings;
- verifies each proposed transformation against one exact retained file;
- calculates a conceptual projected runtime manifest and the fixed
  4.5 MB total, 2.2 MB image, 350 KB CSS, and 500 KB single-asset limits;
- preserves every source master and records every transformation as
  `not-executed`;
- leaves every browser and human-acceptance requirement `blocked-not-run`;
- returns only an in-memory fixture for arithmetic and schema tests.

No current path writes a runtime-optimisation proposal artifact. The public
compiler and writer entrypoints stop before proposal construction, and the
isolated launcher must return the fixed blocker without creating an artifact.
`PublicWebsiteDesignQA` has structural validation only and no compile grant.

A passing projected byte budget is not a candidate, test result, package, or
release signal.

## Static measurement integrity V1

`aureon.operator.website_runtime_measurement_provenance` provides a separate,
read-only static-integrity check for one explicitly supplied existing artifact.
The isolated launcher and
`AUREON_WEBSITE_RUNTIME_MEASUREMENT_STATIC_INTEGRITY_V1.schema.json` can verify:

- the complete current `website/` manifest before and after the check;
- two pre-existing identical evidence replicas bound to one run and
  transformation identifier;
- exact stored file bytes, byte counts, payload hashes, and arithmetic; and
- header-derived PNG, JPEG, or WebP dimensions within the fixed safety limits.

Its successful CLI status is deliberately
`static-integrity-valid: provenance-unverified; production-blocked`. Header
inspection is not a full media decode. Matching copies do not prove which
producer, encoder, command, toolchain, source plan, or source-selection decision
created them; copying an otherwise valid artifact remains possible. Current
source equality does not establish freshness, deterministic replay, visual
quality, browser acceptance, or human approval. Reviewed source pins are an
external operator control and are not self-attested by the artifact.

The checker cannot write evidence, launch a producer, encode or transform
media, prune CSS, rewrite references, mutate source or candidates, compile a
runtime-optimisation proposal, package, publish, or deploy. It cannot satisfy
the production measurement-provenance blocker. `PublicWebsiteDesignQA` may use
this read/validate surface explicitly; `PublicWebsiteDesignWorker` receives no
access.

An imported Python module is not an attested process boundary because hostile
same-process code can monkeypatch module state. Security-relevant use must start
from the fresh isolated launcher with externally reviewed source pins; imported
functions remain non-authoritative test and drift-check APIs.

## What it can never do

The module and its launcher contain no encoder, minifier, CSS pruner, reference
rewriter, copy, delete, candidate, staging, package, credential, network,
publishing, or deployment entrypoint. Its authority object fixes all those
capabilities to `none` and fixes `release_eligible` to `false`.

`PublicWebsiteDesignQA` may structurally validate a declaration but may not
compile or write a production proposal. `PublicWebsiteDesignWorker` receives
neither capability. Any eventual transformation must occur in a separately
authorised staged-candidate workflow and must pass the full browser acceptance
contract before owner review.

## Production invocation

There is no successful production invocation in the current state. Any use of
the isolated launcher with compile arguments must stop with the fixed
measurement-provenance blocker and produce no output. The following shape is
reserved for a future separately reviewed re-enable; it is not currently an
authorised or successful command:

```powershell
python -I -S -B tools/run-website-runtime-optimisation.py `
  --expected-launcher-sha256 <REVIEWED_LAUNCHER_SHA256> `
  --expected-planner-sha256 <REVIEWED_COMPILER_SHA256> `
  -- `
  --source-plan <EXACT_PLAN_PATH> `
  --source-plan-sha256 <EXACT_PLAN_FILE_SHA256> `
  --measurement <EXACT_MEASUREMENT_PATH> `
  --measurement-sha256 <EXACT_MEASUREMENT_FILE_SHA256> `
  --acceptance-contract data/website_operator/browser_acceptance_contract.v1.json `
  --acceptance-contract-sha256 <EXACT_CONTRACT_FILE_SHA256> `
  --output artifacts/website-operator/runtime-optimisations/proposals/<NEW_NAME>.json
```

The output path must be new and directly inside the controlled proposal
directory. Existing artifacts are never overwritten.

## Mandatory downstream acceptance

Even when the projection fits all byte limits, a future staged candidate must
still pass all 20 routes in Chromium, Firefox, and WebKit; all seven viewports;
keyboard and skip-link checks; no-JavaScript and reduced-motion parity;
interactive, data-failure, and fragment states; crawler metadata and current
research/art evidence; performance limits; source-bound screenshot comparison;
and named human visual approval. Zero failures, errors, warnings, and failed
first-party requests are allowed by the current contract.
