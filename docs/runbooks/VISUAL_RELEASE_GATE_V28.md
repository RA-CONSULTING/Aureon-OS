# V28 Composite Visual Release Gate

The V28 composite gate separates automated browser evidence from a distinct
technical pixel-review receipt without changing either record. The technical
node dispositions are produced by the named Codex visual-QA reviewer; they do
not imply that Gary inspected thousands of axe nodes. Gary's separate whole-site
visual acceptance remains the WebsiteOperator owner-acceptance gate. An
automated V28.3 receipt that contains `axe.incomplete` remains `FAIL`; the
composite gate may return `pass` only when a separate, current, hash-bound
manual receipt accounts
for every incomplete node and every other release condition passes.

The gate has no publication authority and does not edit `website/`.

## Inputs

The command accepts one canonical manifest:

```powershell
node tools/aureon_visual_release_gate_v28.js `
  --manifest docs/audits/AUREON_VISUAL_RELEASE_GATE_<UTC>_V28.manifest.json
```

Use `--output <repository-relative-path>` to retain the full composite receipt.
The validator refuses to overwrite an existing output.

Schemas:

- `docs/research/schemas/AUREON_VISUAL_RELEASE_GATE_MANIFEST_V28.schema.json`
- `docs/research/schemas/AUREON_MANUAL_PIXEL_REVIEW_V28.schema.json`

The manifest binds exact SHA-256 hashes for:

- one strict `aureon-website-visual-qa-v28.3` receipt;
- one separate `aureon-manual-pixel-review-receipt-v28.1` receipt;
- the current website-tree hash recorded by the visual audit.

Evidence must be no more than 24 hours old. Visual, manual and manifest
timestamps must be canonical UTC timestamps and occur in that order.

## Engine intent

`intent: "final-release"` requires the exact default engine scope:

```json
["chromium", "firefox", "webkit"]
```

`intent: "remediation-evidence"` permits explicit Chromium evidence so an
uncapped axe run can be reviewed, but the composite state remains `blocked`
with `manifest.remediation_only`. A remediation receipt is never described as
a browser matrix or final release evidence.

Both intents require all 14 routes and all seven V28 viewports. The final gate
recomputes the expected route, interaction, accessibility, performance and
screenshot sets for every required engine.

## Axe and manual-review boundary

The gate requires:

- axe installed and run on every engine and route;
- `completeNodeEvidence: true`;
- each rule's `nodeCount` equal to the complete persisted `nodes` array;
- zero axe violations;
- only `color-contrast` incomplete rules at this policy version;
- zero non-axe route, interaction, custom-contrast, keyboard, 200% reflow,
  performance, motion, diagnostic or screenshot failures.

For every route, the visual receipt also binds the V28 deferred-render
geometry policy and records a `renderingGeometry` result. If
`content-visibility: auto` is active, a deterministic full-page reveal must
leave the document height and each in-flow deferred candidate within the
two-pixel tolerance and settle within its bounded reveal sweep. A missing,
weakened, failed, method- or policy-mismatched geometry record blocks the
composite gate; this is an integrity check, not a ninth performance budget.

Every incomplete node receives this deterministic identity:

```text
axei1-SHA256(JSON.stringify([
  "aureon-axe-incomplete-node-v1",
  NFC(engine),
  NFC(route),
  NFC(ruleId),
  deepNFC(target)
]))
```

The ordered axe target is not sorted. Duplicate identities fail closed. The
manual receipt separately binds the complete visual-receipt hash and source
hash, so identities remain stable without allowing review reuse across changed
evidence.

Each manual record must repeat the exact node context and use one disposition:

- `verified-pass`;
- `not-applicable`, with an explicit inspection note;
- `fail`;
- `unreviewed`.

Composite `pass` requires exact set equality between incomplete-node identities
and manual records, with no duplicate, extra, missing, context-mismatched,
failed or unreviewed record. Missing manual evidence is never treated as an
empty successful review.

## Integration boundary

Release-eligible WebsiteOperator configuration requires exactly one enabled,
required check with the ID `v28-composite-visual-release-gate` and this
six-token command:

```json
[
  "node",
  "{repo_root}/tools/aureon_visual_release_gate_v28.js",
  "--repo-root",
  "{repo_root}",
  "--manifest",
  "{repo_root}/docs/audits/AUREON_VISUAL_RELEASE_GATE_<UTC>_V28.manifest.json"
]
```

The timestamped manifest path is immutable release evidence. Do not use a
mutable `latest` alias, and do not add `--output` to the repeated external
check: the validator deliberately refuses to overwrite an existing receipt.
Generate a retained composite receipt separately when one is required.

WebsiteOperator records every successful external-check ID, return code,
current operator source hash and parseable composite result. Audit and design
receipts retain the exact manifest, automated visual and manual pixel-review
paths and SHA-256 hashes. Build reruns the configured composite gate and binds
the same release ID, source hashes and evidence hashes into the package
receipt. Package validation reruns the gate again, so a missing, changed,
rebound or stale evidence file blocks backup, deployment and read-back.

Until the final timestamped three-engine manifest exists, the default
configuration intentionally remains non-release-eligible rather than pointing
at a placeholder or mutable path.
