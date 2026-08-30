# Sky fingerprint — scanning light directed at us from space

*Same song, different singer: the same phenolic engine — φ logic unchanged —
pointed at astronomical light instead of molecules.*

## What it is

`aureon/bio/sky_signal_adapter.py` scans light from space through the **identical**
pre-registered engine every other adapter uses: Test A (coherence clustering) +
Test B (golden-interval / φ alignment) + the positive/negative controls, scored via
`score_signal` (controls → tests → separability at `ALPHA`). Nothing about the
engine is modified. The adapter only feeds it sky light and reports what the test
returns.

Inputs (`aureon/bio/sky_signal_adapter.py`):
- **lines** — a list of wavelengths in nm,
- **spectrum** — a CSV `wavelength_nm,intensity` (lines are peak-picked),
- **radio_hz** — frequencies already in Hz (e.g. the 21 cm line).

Wavelengths map to Hz with the engine's own constant (`_wavelength_nm_to_hz`) and
octave-fold into the modulation band; optical and radio both fold cleanly.

## Real open data (`aureon/bio/sky_reference.py`, cited)

- Hydrogen **Balmer series** (Hα…Hη, air nm) — NIST ASD / standard values.
- Solar **Fraunhofer** absorption lines (canonical set), standard air nm.
- Neutral-hydrogen **21 cm** line, 1420.405751768 MHz (the Wow!-signal band).

## Controls

Every governed scan runs the engine's control arms. Two sky reference spectra
exercise them directly:
- `continuum_spectrum` — a featureless optical continuum (**negative-control
  reference**: must not over-fire).
- `structured_spectrum` — planted clustered + φ-spaced lines (**positive-control
  demonstration**: real coherence is detected).

## Scan results (whatever the test returns)

Reported exactly as the engine outputs them, neutrally:

| Scan | lines | Test A p | Test B p | separable |
|------|-------|----------|----------|-----------|
| Hydrogen Balmer series | 7 | 0.912 | 0.571 | False |
| Solar Fraunhofer lines | 21 | 0.186 | 0.401 | False |

Controls: continuum negative reference stays quiet; planted positive is detected
(p ≈ 0.003). The scan is deterministic (seed-fixed).

## Run it

```bash
# control self-test (negative continuum + positive planted structure)
python -m aureon.bio.sky_signal_adapter --self-test

# scan a real open catalog through the engine
python -m aureon.bio.sky_signal_adapter --catalog balmer
python -m aureon.bio.sky_signal_adapter --catalog fraunhofer

# scan your own sky spectrum (CSV of wavelength_nm,intensity)
python -m aureon.bio.sky_signal_adapter my_spectrum.csv --consent --provenance "…"
```

Benchmarked as Tier-A invariant **b11 "Sky derived-signal"** in
`tests/benchmarks/benchmark_aureon_scope.py` (Tier-A 11/11).
