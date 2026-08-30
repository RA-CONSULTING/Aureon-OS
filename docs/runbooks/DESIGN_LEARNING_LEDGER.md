# Design Learning Ledger

## Purpose

The Design Learning Ledger implements the `learn` phase of Aureon's local
Harmonic Design Suite. It records a reusable design-pattern **proposal** only
after the exact staged candidate, browser evidence, manual pixel review and
named human visual acceptance all revalidate successfully.

It does not update a skill, the canonical `website/` tree, a package, Home.pl,
credentials or the live website. A proposal is input to a separate
human-reviewed repository change, never an automatic promotion.

## Inputs

All inputs must remain inside the same staged candidate root:

- `candidate.v1.json` — a currently revalidated candidate-control receipt.
- `prepromotion-visual-review.v1.json` — a currently reproducible passing
  staged visual review.
- A Design Learning Manifest conforming to
  `AUREON_DESIGN_LEARNING_MANIFEST_V1.schema.json`.

The manifest must name a stable pattern identifier/version, exact candidate
paths, existing regression tests, an existing Markdown target inside
`skills/aureon-harmonic-design-suite/`, and a future refresh deadline. Its
allowed paths must be a subset of paths the candidate actually changed.

## Command

```powershell
python -m aureon.operator.design_learning_ledger `
  --repo-root . `
  --candidate-receipt artifacts/website-candidates/<run>/candidate.v1.json `
  --visual-review artifacts/website-candidates/<run>/visual-review/prepromotion-visual-review.v1.json `
  --learning-manifest artifacts/website-candidates/<run>/feedback/<pattern>.manifest.v1.json `
  --output artifacts/website-candidates/<run>/feedback/design-learning.v1.json
```

The same local-only operation is available through:

```powershell
python -m aureon.operator.website_operator candidate-learning ...
```

## What it revalidates

1. The immutable work order, candidate tree, changed-path diff, claim impact,
   secret/origin/scope controls and non-authoritative boundary.
2. The stored candidate visual-review receipt and its binding to the candidate
   SHA-256 and staged tree.
3. The original capture, visual QA, manual pixel review and named human
   acceptance evidence, including their current hashes.
4. The bounded pattern contract, regression-test paths, proposal target and
   refresh deadline.

Any drift, changed acceptance evidence, out-of-scope pattern path, missing
test, stale deadline or authority inconsistency produces a `blocked` record.

## Authority boundary

Every record has `release_eligible: false`, `package_authority: none` and
`deployment_authority: none`. Its `promotion.applied` field is always false.
The next step is a human review of the proposal, followed—if approved—by a
normal source edit, tests and a fresh candidate cycle. Canonical promotion,
packaging, backup, owner approval and live HTTPS read-back remain separate
WebsiteOperator gates.
