# Research Route Source-Performance Remediation Brief

## Status and authority

This is a read-only hand-off for a future, separately authorised candidate
cycle. It does not authorise a sixth retry in the V40–V44 cycle, canonical
promotion, package creation, Home.pl access, or deployment.

V44 was the fifth bounded candidate in that cycle. Preserve all V42–V44
evidence and require a new exact-path work order before staging any successor.

## What the evidence establishes

| Evidence | Established result | Decision |
| --- | --- | --- |
| `artifacts/website-candidates/v42-evidence-research-performance-20260728/performance-attribution/isolated-runs/V42_ISOLATED_TRACE_RECEIPT.json` | Chromium `/research/` traces include layout-heavy main-thread work. Run 2 contains a 427.05 ms task with 336.40 ms `Layout` and 82.74 ms `UpdateLayoutTree`; run 3 contains a 427.01 ms task with 332.72 ms `Layout` and 86.37 ms `UpdateLayoutTree`. | Investigate source-level style/layout cost; do not presume a single selector is causal. |
| `artifacts/website-candidates/v43-register-containment-20260728/feedback/AUREON_V43_INITIAL_GATE_20260728.json` | The deferred research register changed document height by 232 px and its candidate height by 232.37 px after reveal, far beyond the 2 px geometry tolerance. | Reject V43. Do not restore that containment variant for performance. |
| `artifacts/website-candidates/v44-register-reserve-correction-20260728/feedback/AUREON_V44_INITIAL_GATE_20260728.json` | The reserve correction preserved deferred-render geometry exactly (all recorded deltas 0 px), but still recorded 307 ms long-task time against the 300 ms release budget. | Reject V44 for performance. Do not run retry-seeking repeats. |

The trace points to layout and style work across the page; it does **not**
establish that a particular element, CSS rule, image, or browser implementation
is the sole cause. Treat any narrower explanation as a hypothesis to test.

## Required next-cycle work order

1. Start a fresh candidate under
   `artifacts/website-candidates/<new-run>/website/` with a v2 work order that
   names this brief and declares a source-level performance hypothesis.
2. Capture a source-bound Chromium trace of `/research/` at 1440 × 1000 before
   editing. Record the candidate tree hash, request count, transfer proxy
   bytes, long-task events, and the largest layout/style slices.
3. Change only the source area supported by that trace. The work order must
   list expected changed paths and explicitly rule out broad visual or copy
   rewrites unless they are independently approved.
4. Capture the same trace after the change and compare it with the pre-change
   source. A reduction in a passing outlier is not evidence of a cure.
5. Run the source-bound initial gate before any repeatability series:

   ```powershell
   python -m aureon.operator.design_candidate_initial_gate `
     --repo-root . `
     --candidate-receipt artifacts/website-candidates/<new-run>/candidate.v1.json `
     --visual-receipt artifacts/website-candidates/<new-run>/browser-qa/<focused-receipt>.json `
     --route-name research `
     --engine chromium `
     --output artifacts/website-candidates/<new-run>/feedback/INITIAL_GATE.json
   ```

6. Only an `eligible-for-repeatability` verdict permits the fixed sequential
   performance series. Require source stability and every run at or below the
   existing 300 ms long-task budget. The later full browser matrix, manual
   pixel review, named human visual acceptance, owner-controlled promotion,
   fresh canonical evidence, and WebsiteOperator release gate remain separate
   vetoes.

## Constraints for the remediation

- Do not reintroduce a deferred-render optimisation that changes document or
  candidate geometry. The V28 geometry gate now binds the policy in both the
  visual receipt and composite release gate.
- Do not increase a performance threshold, weaken the geometry tolerance, or
  remove a diagnostic to make a candidate pass.
- Do not edit the canonical `website/` tree during candidate experimentation.
- Do not infer a live-site outcome from local candidate evidence.
- Keep public claim, research, investor, graphics, and animation changes out
  of this focused performance work order unless separately scoped and
  evidence-reviewed.

## Closure condition

The remediation is complete only when a new candidate has a source-bound
initial-gate pass, a source-stable repeatability result, a passing full staged
matrix, completed named human review, and then the usual owner-controlled
release evidence. This brief itself conveys no release authority.
