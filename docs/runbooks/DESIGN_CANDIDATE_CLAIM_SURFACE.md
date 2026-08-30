# Design candidate claim-surface control

## Purpose

`aureon.operator.design_candidate_claim_surface` closes the gap between a
staged candidate's declared claim-impact hash and the copy it actually renders.
It compares the exact owner-selected source baseline with the exact staged
candidate paths, then requires every newly rendered static public-text surface
to match the sealed route claim capsule or an explicit non-claim
classification.

It is a local staged-evidence control. It does not fetch evidence, access a
browser or provider, alter `website/`, create a package, access credentials,
approve a release, upload to Home.pl, or make a candidate live.

## Required inputs

The runner derives the claim context from its immutable brief binding; a
worker cannot supply or broaden it. The context retains only the route ID,
route, allowed paths, exact claim capsule and capsule SHA-256.

For every worker/broker submission, provide `claim_surface_manifest`. Use an
explicit empty list only when the candidate introduces no new public text
surface. Each non-empty entry contains exactly:

```json
{
  "path": "research/index.html",
  "kind": "permitted-wording",
  "claim_id": "research-method",
  "text_sha256": "<UPPERCASE-SHA-256>",
  "surface_sha256": "<UPPERCASE-SHA-256>",
  "rationale": "route-permitted-wording"
}
```

The manifest binds public wording by hash. `rationale` is a strict controlled
taxonomy label, not free text; do not put raw new public wording, claims
evidence, credentials, visitor data, Gmail, Drive, or Home.pl material in it.
The validator records hashes and bounded classifications rather than
duplicating new wording in its receipt.

## Classification contract

| `kind` | `claim_id` | Required proof | Required `rationale` label |
| --- | --- | --- | --- |
| `permitted-wording` | Exact claim ID | `text_sha256` equals one permitted wording in that sealed route capsule. | `route-permitted-wording` |
| `boundary` | Exact claim ID | `text_sha256` equals that claim's exact boundary. | `route-claim-boundary` |
| `non-claim` | Empty string | The surface is not known capsule wording/boundary and contains no prohibited company, adoption, validation, partnership, funding, or commercial inference. | One of `accessibility-label`, `citation-label`, `decorative-copy`, `interface-label`, `metadata-label`, `navigation-label`, or `source-label`. |

`path` and `surface_sha256` must refer to exactly one newly extracted public
surface. Duplicate entries, omitted surfaces, extra surfaces, a changed path
outside the sealed route allow-list, or an unknown claim ID block validation.

The static inspection covers public text in HTML, metadata and accessible
labels, JSON/JSON-LD, static JavaScript literals, CSS `content`, SVG/XML text
and labels, and text files. Dynamic DOM copy, JavaScript interpolation, script
content in SVG, malformed public text, non-UTF-8 text, or another
non-auditable rendering surface is a fail-closed veto. Do not change the
claim-register hash, reclassify a commercial assertion, or retry the same
candidate to evade that veto.

An exact claim boundary already rendered by a changed source must remain on
the same public surface type. Removing a visible boundary, or moving it into
metadata, is recorded only by path and hashes and blocks the candidate.
Commercial positioning terms controlled by the investor-copy policy (including
the Evidence OS and first-wedge concepts) are claim-bearing; they cannot be
classified as decorative or interface copy.

## Validation workflow

1. Create and stage one exact-path delivery job from a current audited brief,
   reconciliation and (when drift exists) backup plus owner source decision.
2. Obtain the broker lease and make the declared text-only patch only inside
   its staged candidate root.
3. Supply all declared tests, claim impacts and the `claim_surface_manifest`.
   Derive its hashes from the staged static surfaces; never invent or reuse
   them from a different candidate tree.
4. Validate through the runner. For a direct local runner invocation, pass the
   manifest file only when there are declared entries; omission is treated as
   `[]` and will therefore fail if new copy exists:

   ```powershell
   python -m aureon.autonomous.aureon_public_website_design_runner validate `
     --repo-root . `
     --run-id <run-id> `
     --claim-impacts artifacts/website-candidates/<run-id>/claim-impacts.v1.json `
     --claim-surfaces artifacts/website-candidates/<run-id>/claim-surfaces.v1.json
   ```

5. Treat `candidate-validated` as local provenance evidence only. A blocked
   result is `candidate-repair-required`: preserve it and use a separately
   scoped successor rather than overwriting the staged record.

## Authority boundary

The control cannot create evidence, determine research truth, authorise a
broader route, convert attention into traction, promote canonical source,
package a release, make a backup, grant owner approval, deploy, or prove the
public website is live. A passing claim-surface result remains one input to
candidate control; staged browser evidence, named human visual acceptance,
owner-controlled canonical promotion, current audit, verified Home.pl backup,
exact-package approval, deploy and live HTTPS read-back are separate gates.
