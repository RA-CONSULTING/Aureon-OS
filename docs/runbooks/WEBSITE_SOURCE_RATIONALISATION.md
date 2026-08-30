# Website source rationalisation

## Purpose

`aureon.operator.website_source_rationalisation` creates a read-only proposal
for an exact projection of the current canonical `website/` tree and validates
one separately supplied named-owner decision. It is a planning and decision-
validation control only.

The module writes immutable plan and validation artifacts beneath
`artifacts/website-operator/source-rationalisations/`. It does not modify or
remove canonical source, create a reduced source tree, stage a projection,
create or mutate a candidate, build a package, approve a release, access
credentials, use a provider, publish, or deploy.

Use this control only after the normal live-surface observation and source-
reconciliation requirements have selected the current canonical `website/`
tree. It does not choose between local source and a verified live backup and
does not replace that reconciliation.

## What the plan proves

The planner:

- records the exact manifest, tree hash, file count, and byte count of the
  unchanged canonical `website/` tree;
- runs the reviewed
  `tools/build-homepl-v28-narrow-release.ps1` builder in `-VerifyOnly` mode and
  requires a complete public-runtime dependency closure with no missing local
  or fragment references; the exact reviewed builder bytes are authenticated
  before execution and supplied to the pinned PowerShell process through a
  bounded, minimal-environment runner;
- partitions every source-manifest row exactly once into a retained projection
  or an omitted projection, preserving each source path, byte count, and
  SHA-256;
- gives every omitted row only the controlled reason
  `not-in-public-runtime-closure`;
- binds the planner, release-builder, PowerShell binary, immutable writer,
  fixed runner/environment policy, and fixed motion-policy source hashes; and
- projects the retained closure against the fixed footprint limits below.

The planner fails closed if the canonical source, release builder, or motion
policy changes during planning. Its state is always `proposal-only`; its
budget state remains `blocked-candidate-qa-not-run`, with
`eligible_for_next_local_gate: false` and no candidate-QA authority.

## Fixed footprint projection

The projection uses the same fixed values bound by the motion-performance
policy:

| Limit | Exact maximum |
| --- | ---: |
| Total retained bytes | 4,500,000 bytes |
| Retained image bytes | 2,200,000 bytes |
| Retained CSS bytes | 350,000 bytes |
| Largest retained non-code asset | 500,000 bytes |

These are planning projections, not a motion/performance pass. A projection
within all four limits does not run candidate QA or prove browser behaviour,
interaction parity, accessibility, visual acceptance, candidate validity,
package completeness, or release readiness. A projection above a limit is a
planning blocker, not permission to omit, move, compress, replace, or delete
any source file.

## Create the proposal

Choose one safe lowercase run ID and use its exact immutable output path:

```powershell
$rationalisationRunId = "source-rationalisation-20260802t180000z"
$rationalisationLauncher = "tools/run-website-source-rationalisation.py"
$expectedLauncherSha256 = "827D4112E6C6042B4931E987237E1E7B6035B5A147373CDE202D9DC95184B009"
$expectedPlannerSha256 = "D79397371038912C26056A4C8A154671B0269DF54DDBBB2BAD0BE472D070DD09"
$observedLauncherSha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $rationalisationLauncher).Hash
if (-not [string]::Equals($observedLauncherSha256, $expectedLauncherSha256, [StringComparison]::Ordinal)) {
  throw "Website source-rationalisation launcher hash mismatch."
}
python -I -S -B $rationalisationLauncher `
  --expected-launcher-sha256 $expectedLauncherSha256 `
  --expected-planner-sha256 $expectedPlannerSha256 `
  -- plan `
  --run-id $rationalisationRunId `
  --output "artifacts/website-operator/source-rationalisations/plans/$rationalisationRunId.plan.v1.json"
```

Do not invoke this planner by file path or with `python -m`. Those paths lack
the isolated launcher's exact path/hash attestation and are rejected. The
external `Get-FileHash` comparison above is the launcher trust anchor; `-I -S
-B` is mandatory and the launcher independently checks both supplied hashes
before executing the exact planner bytes without importing the `aureon`
package initializers.

The output path must be
`artifacts/website-operator/source-rationalisations/plans/<run-id>.plan.v1.json`.
The plan schema is `aureon.website-source-rationalisation-plan.v1`.
The writer will not replace an existing artifact. Preserve failed proposals;
use a new run ID after repairing a changed or incomplete input.

Review the complete retained and omitted manifests. An omitted path means only
that the fixed builder did not place it in the current reviewed public-runtime
closure. It does **not** prove that the path is obsolete, safe to delete,
unreferenced by another workflow, unsuitable for a future route, or unnecessary
to source history. A retained-only projection does **not** prove that a staged
source or candidate would be complete or ready.

## Owner decision contract

The module never creates, infers, or broadens an owner decision. After reviewing
the exact plan, a named human owner may separately create one deterministic JSON
decision at:

`artifacts/website-operator/source-rationalisations/owner-decisions/<run-id>.decision.v1.json`

The object has exactly these fields:

- `schema`: `aureon.website-source-rationalisation-owner-decision.v1`;
- `decision`: `acknowledged-review-only`;
- `scope`: `acknowledge-exact-source-rationalisation-proposal`;
- `plan_run_id`;
- `plan_file_sha256`, `plan_payload_sha256`, `source_tree_sha256`,
  `retained_tree_sha256`, and `omitted_manifest_sha256` copied from the exact
  reviewed evidence;
- canonical second-precision UTC `acknowledged_at` and `expires_at` timestamps
  ending in `Z`;
- a non-generic named human `acknowledged_by` and a non-empty canonical `note`; and
- the exact authority object below.

```json
{
  "scope": "review-only acknowledgement of one exact source-projection proposal",
  "canonical_website_mutation": "none",
  "physical_source_file_removal": "none",
  "staging_authority": "none",
  "candidate_mutation": "none",
  "candidate_removal_authority": "none",
  "package_authority": "none",
  "release_eligible": false,
  "deployment_authority": "none",
  "credential_access": "none",
  "network_access": "none"
}
```

Acknowledgement must follow plan generation, remain unexpired at validation,
and span no more than four hours from `acknowledged_at` to `expires_at`. Broad access, a
24-hour permission, conversational approval, deployment approval, or an
approval for another plan cannot substitute for this exact run-bound decision.

## Validate the supplied decision

Validation is a separate read-only decision check:

```powershell
python -I -S -B $rationalisationLauncher `
  --expected-launcher-sha256 $expectedLauncherSha256 `
  --expected-planner-sha256 $expectedPlannerSha256 `
  -- validate-decision `
  --plan "artifacts/website-operator/source-rationalisations/plans/$rationalisationRunId.plan.v1.json" `
  --decision "artifacts/website-operator/source-rationalisations/owner-decisions/$rationalisationRunId.decision.v1.json" `
  --output "artifacts/website-operator/source-rationalisations/validations/$rationalisationRunId.validation.v1.json"
```

The `validate-decision` writer owns validation receipt generation; it does not
accept a caller-supplied receipt object. It requires the exact run-bound paths and deterministic plan bytes,
checks every decision binding and the four-hour window, reruns the authenticated
bounded VerifyOnly closure, and confirms that the canonical source, planner,
builder, PowerShell binary, immutable writer, runner/environment policy, and
motion policy still match the plan. Immediately before its immutable write it
reopens both evidence files and requires a byte-identical deterministic replay
at the writer-captured validation instant. It writes one immutable
`aureon.website-source-rationalisation-owner-validation.v1` receipt. A failing
receipt is `blocked`; repair the evidence and create a separately reviewed
successor run.

A passing receipt uses the state `owner-decision-validated-review-only`. It
records only that the exact review acknowledgement validated. No staging
implementation exists in this module, and neither the decision nor its receipt
grants staging authority or advances the website release state machine.

## Stop boundary and handoff

The complete workflow in this phase is:

`plan -> named-human review -> separately supplied exact decision -> validate -> stop`

This protocol cannot be used as a source-projection stage. Any separately
proposed future stage needs its own reviewed implementation and a new explicit
authority boundary; it cannot inherit authority from this plan, decision, or
validation. It must not infer physical deletion from the omitted manifest. The
existing v4 candidate controls still reject file removals, and
all normal work-order, candidate, browser, human-visual, canonical-promotion,
package, verified-backup, exact-hash owner-approval, deployment, and live-
readback gates remain separate and mandatory.
