# Research notebooks

This folder holds reproducible research bundles published alongside each monthly release. Store exported `.ipynb` files and the exact CSV/Parquet snapshots referenced by the accompanying paper trail.

Recommended pattern:

1. Create a subfolder per release (`2024-05_observatory`).
2. Copy the validated mart snapshot and freeze it with a SHA256 checksum.
3. Include a `RUNBOOK.md` describing how to re-run the notebook with open data sources.
