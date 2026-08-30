# Research Route Layout Timing Observation

Use this diagnostic only after a source-bound Research route fails the initial performance gate and the existing trace leaves the source-level explanation unresolved. It gathers at most one minimized, read-only, self-hosted Chromium observation at `1440 x 1000`. This is an analysis-only investigative hint, not a repeatability run or a gate.

It is not causal proof, a performance gate or performance-budget result, owner-work-order evidence, or authority to create a candidate, change the website, relax a budget, replace visual QA, package a release, or deploy anything. Do not repeat it to seek a different correlation or a lower performance observation.

## Run

```powershell
node tools/aureon_research_hydration_attribution.js `
  --source-root artifacts/website-candidates/v44-register-reserve-correction-20260728/website
```

The runner inserts temporary browser-only markers for the two same-origin research JSON fetches and for MutationObserver delivery from the exact research containers: the register, profile cards, selected notes, and research catalogue. Chromium trace timestamps record only timing proximity between those observer-delivery markers and a document-root `Layout` event; the instrumentation changes the diagnostic runtime and cannot establish a cause.

The output is append-only below `artifacts/website-operator/research-hydration-attribution/` and includes a minimized trace plus `AUREON_RESEARCH_HYDRATION_ATTRIBUTION.json`; the raw browser trace is not persisted. The source tree is hashed before and after observation; a changed source makes the receipt incomplete.

## Interpretation

`temporally-correlated` means a named runtime event was observed inside or within 50 ms before a document-root layout. It is a one-capture timing observation, not causal proof, performance-budget evidence, a pass/fail result, or owner-work-order evidence. `not-correlated-in-capture` means the named marker and a document-root layout were both observed but not near each other; it does not rule out causation, only a relationship not observed in this one capture. `inconclusive` means the capture lacks one of those evidence sets. The receipt also records whether the initial document-root layout preceded all observed dynamic research hydration; if it did, do not attribute that initial layout to the fetched research records.

Even a complete receipt is only an investigative hint. It cannot justify, approve, or provide sufficient evidence for an owner work order, a successor candidate, or any release action, and cannot satisfy candidate-control, source-reconciliation, or owner-decision requirements. A separately scoped investigation must independently establish any proposed remediation before a new exact-path work order may be considered. A future candidate still needs the normal candidate-control, visual, performance, accessibility, owner, package, deployment, and live-readback gates. Rejected V43/V44 evidence must remain preserved and non-deployable.
