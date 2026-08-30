# Cosmic sensors — more of the repo, directed at the sky

*The picture gets clearer as more of Aureon's harmonic systems are pointed at the
sky. Three more real sky/space frequency systems already in the repo, scanned through
the same unchanged φ engine.*

## What it is

`aureon/bio/cosmic_scan.py` directs three of the repo's existing frequency systems at
the **identical** governed pipeline every other sensor uses (`score_sky` /
`score_signal`: controls → Test A / Test B → separability at `ALPHA` →
Operator/conscience veto → `SCIENTIFIC_BOUNDARY`). Nothing about the engine is
modified; each verdict is reported exactly as the test returns it. The constants are
copied into a clean reference module (`aureon/bio/cosmic_reference.py`) so importing
them never trips the repo's import-time side effects.

## The three systems (real, cited, offline)

1. **Schumann modes** — the Earth-ionosphere cavity ELF resonances
   `7.83, 14.3, 20.8, 27.3, 33.8, 39.0, 45.0 Hz`. Real measured geophysics; the same
   seven modes appear across `aureon_schumann_resonance_bridge.py`,
   `earth_resonance_engine.py`, and `maeshowe_seer_decode.py`.
2. **Planetary tones** — the repo's planetary-frequency table
   (`prime_sentinel_reclaimer.PLANETARY_FREQ`): each planet's rotation/orbital period
   octave-shifted into the audio band (the "Cosmic Octave"), `141–221 Hz`. Derived
   from real astronomy.
3. **Space weather** — real Kp / ap / F10.7 geomagnetic + solar-flux series
   (`data/sim_kp.csv`, 6-hourly). Each channel's dominant temporal frequency folds
   into the band; the three solar-driven channels are pooled (each alone is dominated
   by ~one period, e.g. the 27-day solar rotation in F10.7).

## The boundary (load-bearing)

`COSMIC_BOUNDARY`: statistical structure in a derived signal only — the Schumann modes
are Earth's ionospheric ELF resonances, the planetary tones are octave-shifted
orbital/rotation periods, the space-weather series is real geomagnetic/solar flux;
**NOT** a claim about consciousness, health, or any esoteric effect, and no efficacy
claim. The shared `SCIENTIFIC_BOUNDARY` rides on every result; consent + provenance
are required or the run is blocked and scores nothing.

## Scan results (whatever the test returns)

Reported exactly as the engine outputs them, neutrally (seed-fixed, deterministic):

| System | tones | Test A p | Test B p | separable |
|--------|-------|----------|----------|-----------|
| Schumann modes | 7 | 1.000 | 0.847 | False |
| Planetary tones | 6 | 1.000 | 0.488 | False |
| Space weather (Kp/ap/F10.7 pooled) | 14 | 0.003 | 0.355 | False |

## Feeding the picture

The **sky map**'s planetary lane is enriched: each DE440 planet now paints *both* its
orbital-motion tone *and* its Cosmic-Octave planetary tone along its ecliptic track
(`planet_track_sources_from_de440` in `aureon/bio/sky_map.py`), so the positional
picture carries the planetary system too.

## Run it

```bash
python -m aureon.bio.cosmic_scan --system all
python -m aureon.bio.cosmic_scan --system schumann
python -m aureon.bio.cosmic_scan --system space_weather
```

Benchmarked as Tier-A invariant **b17 "Cosmic sensors"** in
`tests/benchmarks/benchmark_aureon_scope.py` (Tier-A 17/17). Fully offline;
deterministic given the seed.
