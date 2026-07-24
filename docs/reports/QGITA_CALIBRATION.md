# QGITA ⇄ phenolic-φ calibration — two golden-ratio detectors, one constant

*φ is the key. QGITA and the phenolic engine are both golden-ratio detectors — this
calibrates one against the other, without tuning the engine.*

## Why this exists

**QGITA ("Quantum Gravity in the Act",** Gary Leckey, Aureon Institute**)** is a
two-stage golden-ratio event detector: it embeds a **Fibonacci time lattice** whose
intervals scale by φ and flags structure only under golden-ratio tuning. The
**phenolic fingerprint engine** is an *independent* golden-ratio detector: its Test B
measures how closely a tone set's pairwise ratios align to integer powers of φ.

Both systems hinge on the **same constant** — and the repo confirms it literally:

```
engine.PHI == qgita.PHI == 1.618033988749895
```

So the two φ-detectors can be **calibrated against each other**. This module does it
by the repo's standing contract (`calibration.py`): *calibrate by validation, never
tune the engine.*

## What is calibrated (`aureon/bio/qgita_calibration.py`)

Reusing the **real** QGITA framework (`aureon.wisdom.aureon_qgita_framework`:
`PHI`, `FibonacciTimeLattice`; `aureon.wisdom.aureon_qgita`: the 9 Auris frequencies),
`calibrate_qgita()` confirms — with **no** engine threshold changed:

1. **Shared φ** — `qgita_phi() == engine.PHI` exactly.
2. **The engine detects QGITA's golden lattice** — QGITA's `base·φ^k` lattice
   (the FibonacciTimeLattice φ-scaling) fires the engine's φ-alignment arm (Test B),
   `p ≈ 0.0025 < ALPHA`. This is the crux: the phenolic engine's own pre-registered
   positive control plants centres at `1000·φ^k` — QGITA's golden lattice **is** the
   structure the engine is built to detect.
3. **Bounded false-positive rate** — at that lattice's scale, envelope-matched random
   nulls keep the separable FPR at/below `ALPHA + 3·SE` (measured `0.0000`, ceiling
   `≈ 0.096`).
4. **Engine controls hold** — `positive_control` detects (`p_A = p_B = 0.0025`),
   `negative_control` passes.

`calibrated = (2) and (3) and (4)`. It never touches `ALPHA`, `TARGET_BAND_HZ`, the
separability rule, or the control construction.

## Result

```
φ shared with engine : True  (φ=1.618033988749895)
φ-alignment detect   : p=0.0025  detected=True
empirical FPR        : test_A=0.0000 test_B=0.0500 separable=0.0000
positive control p   : A=0.0025 B=0.0025
controls_valid=True  CALIBRATED=True
```

The 9 QGITA **Auris frequencies** (174, 396, 412.3, 432, 528, 639, 741, 852, 963 Hz)
also scan through the governed pipeline (`score_qgita_auris`), reported neutrally
(9 tones, valid, non-separable) — a real QGITA line list through the same lens, with
the shared `SCIENTIFIC_BOUNDARY` and consent gate intact.

## Run it

```bash
python -m aureon.bio.qgita_calibration --auris
```

Benchmarked as Tier-A invariant **b15 "QGITA φ calibration"** in
`tests/benchmarks/benchmark_aureon_scope.py` (Tier-A 15/15). Fully offline;
deterministic given the seed.
