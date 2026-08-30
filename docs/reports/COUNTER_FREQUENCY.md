# The counter-frequency canon — φ & Fibonacci, through the one engine

*The observatory already carries planetary, Schumann, coherence, sacred-site, and
Master-Formula tones. This adds the repo's one table anchored on the **Fibonacci
ladder and golden-ratio harmonics** — the `SACRED_FREQUENCIES` canon of the
planetary harmonic **counter-frequency** engine. Same unchanged φ engine.*

## What it is

The `SACRED_FREQUENCIES` canon of `aureon/harmonic/aureon_harmonic_counter_frequency.py`
(the engine that FFTs volume patterns and maps them to sacred harmonics), scanned
through the **same** phenolic engine (`phenolic_fingerprint.py`: Test A coherence-
clustering + Test B golden-interval/φ alignment + positive/negative controls). Nothing
about the engine is modified; every verdict is reported exactly as the pre-registered
test returns it.

The constants are **copied** into `aureon/bio/counter_frequency_reference.py` (not
imported) — the source module runs an import-time `_baton_link` heartbeat and imports
`requests`/`numpy`. Copying keeps the reference module pure stdlib: no repo import, no
network, no import-time writes (the same guarantee the other bio reference modules give).

## The canon

| Group | Tones (Hz) | Note |
|-------|-----------|------|
| **Fibonacci ladder** | 8 · 13 · 21 · 34 | the distinctive low-Hz set — new to the observatory |
| **φ-harmonics** | φ ≈ 1.618 · 2φ ≈ 3.236 · 24/φ ≈ 14.83 | golden-ratio anchors |
| Schumann | 7.83 | Earth base |
| Solfeggio | 396 · 417 · 432 · 528 · 639 · 741 · 852 · 963 | shared with other lanes |

The full canon folds to **16 distinct tones**. Each is octave-folded into the
modulation band `[1000, 2000) Hz` by `fold_to_band` and scanned through `score_sky`
(consent/provenance → controls → Operator/conscience veto → Test A / Test B →
separability at `ALPHA`). Sub-catalogs `fibonacci` (4) and `phi` (3) can be scanned
in isolation.

## The boundary (load-bearing)

`COUNTER_FREQUENCY_BOUNDARY`: statistical structure in a derived tone set built from
the repo's own φ/Fibonacci harmonic canon, through one unchanged φ engine — **NOT** a
claim about markets, whales, manipulation, consciousness, or any esoteric effect, and
no efficacy claim. Each verdict is exactly what the pre-registered test returned.

## The results (whatever the tests return)

Reported exactly as the engine outputs them, neutrally (seed-fixed, deterministic):

| Lane | tones | Test A p | Test B p | separable |
|------|-------|----------|----------|-----------|
| Counter-frequency (full canon) | 16 | 0.324 | 0.066 | False |
| Fibonacci ladder | 4 | 1.000 | 0.448 | False |
| φ-harmonics | 3 | 0.493 | 1.000 | False |

Every number is the engine's own verdict — the lane makes no claim beyond tabulating it.

## Run it

```bash
python -m aureon.bio.counter_frequency_scan --system all
python -m aureon.bio.celestial_observatory        # the counter-frequency lane now appears
```

Benchmarked as Tier-A invariant **b24 "Counter-frequency"** in
`tests/benchmarks/benchmark_aureon_scope.py` (Tier-A **25/25**). Fully offline; the
lane is copied static data, so it runs anywhere with no network. See
[SENSOR_SUITE.md](SENSOR_SUITE.md) for the whole picture and
[CELESTIAL_OBSERVATORY.md](CELESTIAL_OBSERVATORY.md) for the consolidated instrument.
