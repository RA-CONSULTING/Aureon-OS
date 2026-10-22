# Platypus / Song of the Sphaerae

**Mathematical Coherence Framework for Planetary Ephemeris Validation**

---

## Overview

Platypus is a coherence analysis engine that computes normalized coupling scores between planetary configurations and geomagnetic indices. It implements the complete Song of the Sphaerae process tree:

```
S(t) → Q(t) → H(t) → E(t) → O(t) → Λ(t) → Γ(t) → Validation
```

## Mathematical Framework

### Process Tree

| Symbol | Name | Formula | Description |
|--------|------|---------|-------------|
| **S(t)** | Substrate State | `[α, δ, ε, r]` | Raw observables: RA, Dec, Elongation, Distance |
| **Q(t)** | Geometric Coherence | `(1/N) Σ\|cos(εᵢ)\|` | Alignment score (0=orthogonal, 1=aligned) |
| **H(t)** | Forcing Context | `(1/N) Σ(1/rᵢ²)` | Inverse-square distance weighting |
| **E(t)** | Echo Memory | `αE(t-1) + (1-α)Λ(t)` | Exponential decay persistence |
| **O(t)** | Observer Term | `βΛ(t-Δt)` | Self-reference / inertia |
| **Λ(t)** | Lambda Field | `wₛS' + wqQ + wₕH + wₑE + wₒO` | Unified state equation |
| **Γ(t)** | Coherence Score | `(Λ-min)/(max-min)` | Normalized to [0,1] |
| **L(t)** | Lighthouse Events | `\|ε\|<ε₀ OR \|ε-π\|<ε₀` | Conjunctions/Oppositions |

### Default Parameters

```python
# Lambda weights (sum to 1.0)
w_S = 0.20  # Substrate
w_Q = 0.25  # Geometric coherence
w_H = 0.25  # Forcing context  
w_E = 0.20  # Echo memory
w_O = 0.10  # Observer term

# Memory/Observer
α = 0.2    # Exponential decay rate
β = 0.1    # Self-reference scaling

# Events
ε₀ = 3.0°  # Alignment threshold
```

## Installation

```bash
# Required packages
pip install numpy pandas scipy skyfield astroquery astropy

# Or from requirements
pip install -r requirements.txt
```

## Quick Start

### Full Pipeline

```bash
# Run complete pipeline (2020-2024)
python run_platypus.py --start 2020-01-01 --end 2024-12-31

# Using geometric-focused preset
python run_platypus.py --preset geometric --start 2023-01-01 --end 2024-01-01

# Offline mode (skip external fetches)
python run_platypus.py --skip-horizons --skip-gfz-download
```

### Component Scripts

```bash
# Generate ephemeris only
python ephemeris_generator.py --start 2020-01-01 --end 2024-12-31

# Parse GFZ data only
python gfz_parser.py --download --start 2020-01-01 --end 2024-12-31

# Run coherence engine only (requires ephemeris CSV)
python platypus.py --ephemeris radar_ephem_skyfield_de440.csv
```

### Programmatic Usage

```python
from platypus import Platypus
from platypus_presets import get_preset

# Create engine with preset
config = get_preset('geometric')
engine = Platypus(config)

# Run pipeline
engine.load_ephemeris('radar_ephem_skyfield_de440.csv')
engine.compute_coherence()
engine.save_timeseries('radar_timeseries.csv')

# Validate against Kp
import pandas as pd
kp_df = pd.read_csv('kp_ap_f107.csv', parse_dates=['datetime'])
engine.validate_against_index(kp_df, 'Kp')

# Print results
print(engine.summary())
```

## Pipeline Steps

### Step 1-2: Ephemeris Generation

- **Skyfield DE440**: Local ephemeris computation (~145MB kernel)
- **JPL Horizons**: Truth data via API for validation

### Step 3: Gate 1 — Positional Accuracy

| Criterion | Threshold |
|-----------|-----------|
| Median angular error | < 1 arcmin |
| Max angular error | < 5 arcmin |

### Step 4-5: Gate 2 — Event Detection

- **2A**: Conjunction/Opposition (elongation thresholds)
- **2B**: Perihelion/Aphelion (distance extrema)

### Step 6: GFZ Index Parsing

Parses `Kp_ap_Ap_SN_F107_since_1932.txt` into 3-hour resolution CSV.

### Step 7: Coherence Computation

Full Λ(t) → Γ(t) calculation with memory and observer terms.

### Step 8: Gate 3 — Coupling Validation

| Test | Measure | Significance |
|------|---------|--------------|
| Lag Correlation | `ρ(τ) = corr(Γ,Y_τ)` | Permutation p < 0.05 |
| Spectral Coherence | `C(f) = \|S_ΓY\|²/(S_ΓΓ·S_YY)` | Permutation p < 0.05 |
| Superposed Epoch | Mean Kp around L2 events | Permutation p < 0.05 |

## Output Files

| File | Description |
|------|-------------|
| `radar_ephem_skyfield_de440.csv` | Skyfield ephemeris |
| `radar_ephem_horizons_truth.csv` | JPL Horizons truth |
| `gate1_errors.csv` | Position comparison |
| `alignment_events.csv` | Conjunctions/Oppositions |
| `distance_extrema.csv` | Perihelion/Aphelion |
| `kp_ap_f107.csv` | GFZ indices (3h resolution) |
| `radar_timeseries.csv` | **Main output**: Q, H, E, O, Λ, Γ |
| `gate3_lag_corr.csv` | Lag correlation results |
| `gate3_coherence.csv` | Spectral coherence |

## Configuration Presets

| Preset | Focus | Key Settings |
|--------|-------|--------------|
| `default` | Balanced | wQ=0.25, wH=0.25, α=0.2, β=0.1 |
| `high_memory` | Persistence | wE=0.35, α=0.4 |
| `low_latency` | Fast response | wE=0.10, α=0.05 |
| `geometric` | Alignments | wQ=0.40 |
| `forcing` | Distances | wH=0.40 |
| `observer` | Self-reference | wO=0.25, β=0.25 |
| `moving_avg` | W-step avg | 8-step window |
| `strict` | Rigorous testing | n_perms=5000 |

```bash
# List all presets
python run_platypus.py --list-presets
```

## Validation Interpretation

```
═══════════════════════════════════════════════════════════════
PLATYPUS VALIDATION SUMMARY
═══════════════════════════════════════════════════════════════
Samples: 5840

Lag Correlation:
  Best r = 0.1234 at lag 12h
  p-value = 0.0023

Spectral Coherence:
  Peak = 0.5678
  p-value = 0.0156

Epoch Analysis:
  Events = 42
  Peak = 0.8901
  p-value = 0.0089
═══════════════════════════════════════════════════════════════
✓ COHERENCE VALIDATED (≥2 tests significant at p<0.05)
═══════════════════════════════════════════════════════════════
```

### Verdict Criteria

| Result | Condition |
|--------|-----------|
| ✓ VALIDATED | ≥2 tests at p<0.05 |
| ◐ MARGINAL | 1 test at p<0.05 |
| ✗ NOT SIGNIFICANT | 0 tests at p<0.05 |

## Data Sources

- **Ephemeris**: Skyfield DE440 (JPL Development Ephemeris)
- **Truth**: JPL Horizons via `astroquery`
- **Geomagnetic**: GFZ Potsdam Kp/ap/F10.7
  - https://kp.gfz-potsdam.de/

## Architecture

```
┌─────────────────┐
│ ephemeris_      │   Skyfield DE440 + Horizons
│ generator.py    │   Gate 1, 2A, 2B
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ gfz_parser.py   │   Kp, ap, F10.7 extraction
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ platypus.py     │   Q, H, E, O, Λ, Γ computation
│                 │   Gate 3 validation
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ run_platypus.py │   Pipeline orchestration
└─────────────────┘
```

## License

Part of the Aureon Trading ecosystem.

---

*Gary Leckey & GitHub Copilot | December 2025*
