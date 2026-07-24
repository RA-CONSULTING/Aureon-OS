# UPE from the sky — scanning the sky's real faint emission through the engine

*Same song, different singer: the same phenolic engine — φ logic unchanged — pointed
at the sky's own faint self-emission through the faint-emission lens.*

## The honest bridge

UPE (ultraweak photon emission) proper is **biological** — biophotons from living
tissue, ~10–10³ photons/cm²/s. The sky does **not** emit biophotons, and a photograph
records reflected light, not emission. But the night sky **does** faintly emit light of
its own, and that is the legitimate "faint light from the sky" to scan through the same
lens:

- **Airglow / nightglow** — the sky's real faint self-emission: atomic oxygen
  (557.7, 630.0, 636.4 nm), the mesospheric sodium layer (Na D, 589.0/589.6 nm), the
  O₂ atmospheric bands, and the OH Meinel bands (`AIRGLOW_NM`, standard nightglow
  reference values). Genuinely faint, genuinely structured (discrete lines).
- **Diffuse night-sky background** — the smooth optical background (integrated
  starlight + zodiacal light + diffuse galactic light + the airglow continuum). It is
  featureless, so it peak-picks to nothing and scans **non-separable** — the honest
  non-structure anchor, exactly as a broadband UPE spectrum does.

Both run through the **identical** governed pipeline (`score_signal`: controls →
Test A / Test B → separability at `ALPHA`). Nothing about the engine is modified. The
scan reports whatever the pre-registered test returns — no claim is asserted about
what airglow "should" score.

## Data (`aureon/bio/sky_reference.py`, cited)

- `AIRGLOW_NM` — night-sky airglow emission lines (atomic O, Na D, O₂ atmospheric,
  OH Meinel), standard nightglow reference values (`AIRGLOW_CITATION`). The citation
  states the boundary explicitly: *the sky's own faint self-emission — NOT biological
  UPE.*
- `diffuse_night_sky_spectrum()` — the featureless diffuse-background reference.

## Scan results (whatever the test returns)

Reported exactly as the engine outputs them, neutrally (seed-fixed, deterministic):

| Scan | tones | Test A p | Test B p | separable |
|------|-------|----------|----------|-----------|
| Airglow lines (10) | 10 | 0.872 | 0.671 | False |
| Diffuse background | 0 | — | — | False (featureless anchor) |

Controls: the diffuse background stays quiet (featureless → 0 lines → non-separable);
a planted clustered + φ line set is detected (p ≈ 0.003).

## Run it

```bash
# UPE-from-the-sky: scan real airglow lines + the diffuse-background anchor
python -m aureon.bio.sky_signal_adapter --faint-sky

# scan the airglow catalog on its own
python -m aureon.bio.sky_signal_adapter --catalog airglow
```

Benchmarked as Tier-A invariant **b14 "Faint sky / UPE-from-sky"** in
`tests/benchmarks/benchmark_aureon_scope.py` (Tier-A 14/14). Fully offline — the
airglow catalog and diffuse background are cited/generated reference values, no
network required.
