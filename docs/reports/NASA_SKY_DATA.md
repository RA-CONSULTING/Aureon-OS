# NASA sky data — scanning real host-star numbers through the engine

*Same song, different singer: the same phenolic engine — φ logic unchanged —
pointed at real, openly published NASA data instead of molecules or catalog lines.*

## What it is

`scripts/validation/fetch_nasa_sky_data.py` pulls a real snapshot from the **NASA
Exoplanet Archive** and caches it in the repo; `scripts/validation/benchmark_nasa_sky.py`
scans that cache through the **identical** governed pipeline every other adapter
uses (`score_sky` → `score_signal`: controls → Test A / Test B → separability at
`ALPHA`). Nothing about the engine is modified — the scan verdict is printed exactly
as the pre-registered test returns it.

## Source (open, no API key required)

- **NASA Exoplanet Archive** — `pscomppars` composite-parameters table (one row per
  confirmed planet), pulled over the keyless **TAP** service:
  <https://exoplanetarchive.ipac.caltech.edu/docs/TAP/usingTAP.html>
- Columns fetched: `pl_name, hostname, st_teff, pl_orbper`.
- The TAP endpoint needs **no key**. An optional `NASA_API_KEY` env var is honoured
  for any `api.nasa.gov` call (none is required here) — no key is invented or
  hard-coded.
- Cached snapshot: `data/sky/nasa_exoplanet_hosts.csv` (real data, committed, with a
  provenance header recording the source URL, the exact query, and the row count).

## Two honest lanes

Real NASA numbers, fed straight into the unchanged sky adapter:

1. **Stellar light (spectral)** — host-star effective temperature `st_teff` (K) →
   Wien's-law peak wavelength `λ_peak(nm) = 2.897771955e6 / T` → the adapter's
   line path. Real starlight colour.
2. **Planetary rhythm (radio_hz)** — orbital period `pl_orbper` (days) → frequency
   `Hz = 1 / (period · 86400)` → the adapter's radio path (`fold_to_band` folds the
   tiny orbital Hz up into the modulation band). On-theme for the HNC planetary-
   harmonics thread.

Wavelengths and radio frequencies both fold cleanly into the modulation band via the
engine's own constant (`_wavelength_nm_to_hz`).

## Scan results (whatever the test returns)

Reported exactly as the engine outputs them, neutrally, on the committed 1000-planet
snapshot (seed-fixed, deterministic):

| Lane | inputs | Test A p | Test B p | separable |
|------|--------|----------|----------|-----------|
| Stellar Wien wavelengths (starlight colour) | 1000 | 0.002 | 0.002 | True |
| Orbital-period frequencies (planetary rhythm) | 1000 | 0.002 | 0.429 | False |

(The snapshot now also carries each host's real `ra`/`dec`, which the
[sky map](SKY_MAP.md) bins by celestial position.)

Both scans are `valid` (controls pass, tones fold into band). The verdicts are the
engine's own — no claim is asserted here about what the sky "should" score.

## Run it

```bash
# fetch the real NASA snapshot (keyless TAP) → data/sky/nasa_exoplanet_hosts.csv
python scripts/validation/fetch_nasa_sky_data.py

# scan the cached data through the engine (offline; --fetch to refresh first)
python scripts/validation/benchmark_nasa_sky.py
```

Benchmarked as Tier-A invariant **b12 "NASA sky data"** in
`tests/benchmarks/benchmark_aureon_scope.py` (Tier-A 12/12). The benchmark and
`tests/bio/test_nasa_sky_data.py` read the **committed cache offline**, so CI never
depends on the network; if the cache is absent the invariant degrades to a skip-pass.
