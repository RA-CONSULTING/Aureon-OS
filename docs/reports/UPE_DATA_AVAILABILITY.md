# Open-source data for the bio pipeline — availability & test/benchmark

*What open data exists for the bio / UPE adapters, what doesn't, and how the
system is tested and benchmarked on the data we legitimately have.*

## The honest finding on open UPE data

A search for a **standalone, downloadable open ultraweak-photon-emission (UPE) /
biophoton dataset** (numeric emission spectra or photon-count series) came up
empty. Biophoton data is published **inside individual papers' supplementary
material**, not as reusable datasets:

- [Advanced Data Analysis of Spontaneous Biophoton Emission (arXiv:2511.11080)](https://arxiv.org/abs/2511.11080)
  — methods paper, **no data-availability statement or repository**.
- [Biophotons: New Experimental Data and Analysis, *Entropy* 2023, 25(10):1431](https://www.mdpi.com/1099-4300/25/10/1431)
  — analysis in-paper.
- [Imaging UPE from living/dead mice and plants, *J. Phys. Chem. Lett.* 2024](https://pubs.acs.org/doi/10.1021/acs.jpclett.4c03546)
  ([bioRxiv](https://www.biorxiv.org/content/10.1101/2024.11.08.622743v1.full)) —
  the imaging study behind the popular coverage.
- The one [figshare item](https://figshare.com/articles/dataset/Edgepass_filters_used_for_spectral_analysis_/6534320/1)
  is edgepass **filter** data, not emission spectra.

**We do not fabricate a "real" UPE dataset.** The literature is consistent that a
true UPE spectrum is **broadband and featureless** (~200–800 nm, subtle orange
maximum) — so a genuine UPE measurement is *expected* to score **non-separable**
through the phenolic engine. A real featureless measurement scoring null is a
**pass** (the honest anchor), not a failure.

## Drop-in path for real UPE data

When you have a real dark-chamber measurement, no code change is needed:

```bash
# emission spectrum: CSV of wavelength_nm,intensity
python -m aureon.bio.upe_signal_adapter my_upe_spectrum.csv \
    --consent --provenance "my dark-chamber UPE measurement"

# or a photon-count time-series via the same adapter (kind='timeseries')
```

`aureon/bio/upe_signal_adapter.py` peak-picks emission lines (or FFT-picks dominant
photon-count modes), maps them to the engine's modulation band, and scores them
under full governance (consent + controls + Operator/conscience veto + boundary).

## What we test + benchmark on (data we legitimately have)

1. **Bio anchor (synthetic / cited reference).** `synthetic_upe("broadband")` (the
   cited featureless profile) → **non-separable**; `synthetic_upe("structured")`
   (planted narrow lines) → **separable**. Plus the convergence map under governance.
2. **Real open molecular data.** The repo already holds genuine open-source spectra
   — **NIST WebBook IR peaks** (`data/spectra/nist_ir_peaks.csv`, fetched via
   `fetcher.py`) + curated DOI-sourced peaks. The falsifiable phenolic engine runs
   on them via `connector.run_analysis`, deterministically.

Both lanes are exercised by:
- `python scripts/validation/benchmark_bio_open_data.py` — ✅/❌ end-to-end driver.
- `tests/benchmarks/benchmark_aureon_scope.py` — Tier-A invariant
  **b10 "Bio derived-signal"** (UPE anchor + governance gate + convergence
  semantics), recorded in `report.{json,md}`.

## Guarantee

No person/subject reading anywhere. The bio pipeline reports **statistical
structure in a derived signal only** — never a claim about a person's health,
state, emotion, relationships, or identity — and it must not manufacture structure
from featureless data (the b10 broadband invariant enforces exactly that).
