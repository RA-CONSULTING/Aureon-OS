# The harmonic core — the HNC's OWN harmonic substrate, through the one engine

*The sacred-lattice lanes mapped the sky through Earth's harmonic lattice. This goes one
level deeper — to the frequency substrate the whole framework is built on. Same unchanged
φ engine; the repo's own core harmonic system as the input.*

## What it is

Three repo-native harmonic tone systems, pointed at the **same** phenolic engine
(`phenolic_fingerprint.py`: Test A coherence-clustering + Test B golden-interval/φ
alignment + positive/negative controls). Nothing about the engine is modified; every
verdict is reported exactly as the pre-registered test returns it.

The literal constants are **copied** into `aureon/bio/harmonic_core_reference.py` (not
imported) — the Ghost Dance module runs an import-time `_baton_link` heartbeat that
writes a log line and wires the Mycelium sonar. Copying keeps the reference module pure
stdlib: no repo import, no network, no import-time writes (the same guarantee
`cosmic_reference` / `sacred_lattice_reference` give).

## The three systems

| System | In-repo source | What it supplies |
|--------|----------------|------------------|
| **Master Formula Λ(t)** | `aureon/core/aureon_lambda_engine.py::FREQUENCIES` / `WEIGHTS` | The **6 weighted harmonic modes** of the HNC master equation `Λ(t) = Σ wᵢ sin(2πfᵢt + φᵢ) + α·tanh(g·Λ̄(t)) + β·Λ(t−τ)`: `7.83, 14.3, 20.8, 33.8, 528.0, 963.0 Hz` with weights `0.25, 0.15, 0.10, 0.05, 0.30, 0.15` (**528 Hz dominant**, weights sum to 1.0). This **is** "the harmonic system" the framework centres on, as concrete data. |
| **Celtic Ogham** | `aureon/decoders/celtic_ogham.py::_FEDA` | **25 tree-tones** across 5 aicme — each a Solfeggio base tone (`174, 285, 396, 417, 528`) φ-scaled by its aett rule: aicme 1,4 ×1 · aicme 2,5 ×φ · aicme 3 ×φ⁻¹. Folds to 15 distinct tones (e.g. Huath = 174×φ ≈ 281.5, Ruis = 528×φ⁻¹ ≈ 326.4). |
| **Ghost Dance** | `aureon/wisdom/aureon_ghost_dance_protocol.py::ANCESTRAL_FREQUENCIES` | The full **9-tone Solfeggio ladder** (`174 … 963 Hz`) mapped to ancestral archetypes (foundation_elders … chief_council). |

Each tone list is octave-folded into the modulation band `[1000, 2000) Hz` by
`fold_to_band` and scanned through `score_sky` → `score_signal` (consent/provenance →
controls → Operator/conscience veto → Test A / Test B → separability at `ALPHA`).

## The boundary (load-bearing)

`HARMONIC_CORE_BOUNDARY`: statistical structure in a derived tone set built from the
repo's own HNC harmonic frequency tables, through one unchanged φ engine — **NOT** a
claim about consciousness, ancestral spirits, sacred trees, the reality field, or any
esoteric effect, and no efficacy claim. Each verdict is exactly what the pre-registered
test returned.

## The results (whatever the tests return)

Reported exactly as the engine outputs them, neutrally (seed-fixed, deterministic):

| Lane | tones | Test A p | Test B p | separable |
|------|-------|----------|----------|-----------|
| Master Formula Λ(t) | 6 | 1.000 | 0.384 | False |
| Celtic Ogham | 15 | 0.841 | 0.715 | False |
| Ghost Dance | 9 | 1.000 | 0.709 | False |

Every number is the engine's own verdict — the lanes make no claim beyond tabulating
them. The Λ(t) `WEIGHTS` vector is carried as traceable `(frequency, weight)` metadata
(`lambda_weighted()`), and the 25 named Ogham feda are preserved for citation.

## Run it

```bash
python -m aureon.bio.harmonic_core_scan --system all
python -m aureon.bio.celestial_observatory        # the 3 harmonic-core lanes now appear
```

Benchmarked as Tier-A invariant **b23 "Harmonic core"** in
`tests/benchmarks/benchmark_aureon_scope.py` (Tier-A **23/23**). Fully offline; the
lanes are copied static data, so they run anywhere with no network. See
[SENSOR_SUITE.md](SENSOR_SUITE.md) for the whole picture,
[SACRED_LATTICE.md](SACRED_LATTICE.md) for the sky-lattice companion, and
[CELESTIAL_OBSERVATORY.md](CELESTIAL_OBSERVATORY.md) for the consolidated instrument.
