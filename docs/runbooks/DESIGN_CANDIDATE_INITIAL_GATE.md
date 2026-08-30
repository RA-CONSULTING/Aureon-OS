# Design candidate initial gate

## Purpose

`aureon.operator.design_candidate_initial_gate` converts one focused staged-browser receipt into a source-bound operational decision. It prevents an agent from retrying a browser run until a passing number appears.

It is a diagnostic and feedback control only. It cannot edit `website/`, promote a candidate, build a package, access credentials, approve a release, upload to Home.pl, or call a candidate live.

## Inputs

The control requires all of the following from the same staged candidate:

- a validated `candidate.v1.json`;
- a focused Visual QA JSON receipt under that candidate artifact;
- an explicit route name and browser engine; and
- an output path under the candidate artifact.

Before deciding anything, it revalidates the candidate-control receipt and recomputes the candidate website tree using the exact V28 QA snapshot algorithm. The focused browser receipt must be self-hosted, stable, and bound to that unchanged tree.

## Decision contract

The control has four states:

| State | Meaning | Next action |
| --- | --- | --- |
| `eligible-for-repeatability` | Candidate control, focused source binding, route runtime, deferred-render geometry, and every initial performance check pass. | Run the fixed sequential performance series; then run the full staged browser matrix and complete named human review. |
| `rejected-geometry` | Deferred rendering changes document or candidate geometry. | Preserve the receipt. Do not run a retry-seeking performance series. A successor needs a fresh exact-path work order. |
| `rejected-performance` | Geometry is safe, but a required initial runtime or performance check fails. | Preserve the receipt. Do not retry for a passing outlier; profile the source-level cause before an independently authorised successor. |
| `blocked` | Candidate control or focused source binding cannot be proved. | Repair provenance first. A browser rerun cannot cure unbound evidence. |

`full_visual_status` is recorded but does not turn a focused performance diagnosis into release approval. Any full-browser accessibility, visual, manual-pixel, or human-acceptance failure remains a separate veto on promotion.

## Command

```powershell
python -m aureon.operator.design_candidate_initial_gate `
  --repo-root . `
  --candidate-receipt artifacts/website-candidates/<run-id>/candidate.v1.json `
  --visual-receipt artifacts/website-candidates/<run-id>/browser-qa/run-01/<receipt>.json `
  --route-name research `
  --engine chromium `
  --output artifacts/website-candidates/<run-id>/feedback/INITIAL_GATE.json
```

The command exits non-zero for every non-passing state. Treat the written JSON receipt, rather than terminal text alone, as the decision record.

## Authority boundary

A passing result permits only the next local diagnostic step. It never grants canonical mutation, package, deployment, credential, or release authority. After an accepted candidate is separately owner-promoted, the canonical WebsiteOperator audit, complete V28 evidence, package closure, verified Home.pl backup, exact-hash owner approval, deployment, and live HTTPS read-back must all be rerun.
