# Ephemeris + Coupling Validation Pipeline

This pipeline generates Skyfield (DE440) ephemerides, fetches JPL Horizons truth (RA/DEC/elongation and heliocentric distance), performs error/validation gates, parses GFZ Kp/F10.7, computes a Gamma aggregate, and writes lag-correlation + coherence spectra.

## Outputs
- radar_ephem_skyfield_de440.csv
- radar_ephem_horizons_truth_with_r.csv
- ephem_error_detail.csv
- gate2_alignment_event_diff.csv
- gate2_distance_extrema_diff.csv (or skyfield-only fallback)
- kp_ap_f107.csv
- radar_timeseries.csv
- gate3_lag_corr.csv
- gate3_coherence.csv

## Quick Start

Prereqs: place `Kp_ap_Ap_SN_F107_since_1932.txt` in repo root.

Local run:

```bash
chmod +x ./run_pipeline.sh
./run_pipeline.sh
```

Docker (reproducible):

```bash
docker build -f Dockerfile.ephemeris -t ephem-pipeline .
docker run --rm -v "$PWD:/app" ephem-pipeline
```

If Horizons access is rate-limited, re-run; the script is idempotent and will re-write CSVs.
