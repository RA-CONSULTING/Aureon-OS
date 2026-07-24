# Coherence lane — the repo's DE440 coherence spectrum through the engine

*Nothing consumed it before. The repo already computed a frequency-domain coherence
spectrum of the DE440 planetary timeseries — this directs it at the φ engine.*

## What it is

`aureon/bio/coherence_scan.py` reads `data/de440_gate3_coherence.csv`
(`freq_hz,coherence`, 129 bins — a repo-computed gate3 coherence analysis), picks the
highest-coherence frequency bins, folds them into the modulation band, and scans them
through the **identical** governed pipeline every other sensor uses (`score_signal`:
controls → Test A / Test B → separability at `ALPHA` → Operator/conscience veto →
`SCIENTIFIC_BOUNDARY`). Nothing about the engine is modified; the verdict is reported
exactly as the test returns it. `data/sim_gate3_coherence.csv` is the simulated
control.

## Method

- `load_coherence(path)` → `(freq_hz, coherence)`.
- `coherence_peak_tones(path, top_k=32, min_coherence=0.0)` → the `top_k` bins with the
  greatest coherence, each octave-folded into `[1000, 2000)` Hz (the ~1e-7 Hz bins fold
  up), sorted and de-duplicated.
- `score_coherence(path, …)` → builds a `HumanSignal(modality="sky")` and scores it.

## Scan results (whatever the test returns)

Reported exactly as the engine outputs them, neutrally (seed-fixed, deterministic):

| Source | tones | Test A p | Test B p | separable |
|--------|-------|----------|----------|-----------|
| DE440 coherence | 23 | 0.940 | 0.704 | False |
| sim control | 26 | 0.638 | 0.807 | False |

## Run it

```bash
python -m aureon.bio.coherence_scan --sim
```

Benchmarked as Tier-A invariant **b19 "Coherence lane"** in
`tests/benchmarks/benchmark_aureon_scope.py` (Tier-A 19/19). Fully offline;
skip-passes if the coherence data is absent.
