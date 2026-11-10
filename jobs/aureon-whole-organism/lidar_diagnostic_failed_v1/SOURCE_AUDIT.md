# Source and scope audit

The benchmark is grounded in two supplied research documents. Exact hashes are
recorded in `MANIFEST.sha256` after staging.

- `HNC_Harmonic_LIDAR_WhitePaper_Leckey_2026.docx`: primary equation and the
  80x80, 6.7x6.3 km SRTM description.
- `HNC_Harmonic_LIDAR_v2_AluminiumFluid_Leckey.docx`: later document containing
  the 40x40, approximately 11x10.5 km figure and acoustic/material discussion.

The pinned Aureon OS snapshot at
`f5fb1916c07ac26eb7fc38c34ff2dc9bd029e21d` contained narrative references but
no tracked LiDAR/Walgidee analysis script, notebook, raw DEM, or configuration.
This package is therefore an independently written reference implementation,
not a claim that previously existing repository code was executed.

The source uses “LiDAR” as a system name, but its stated input is NASA SRTM
C-band synthetic-aperture-radar interferometric elevation data obtained through
OpenTopoData. Reports preserve that distinction.

The primary paper says “nine-shell” while its table enumerates indices 0–9.
The benchmark implements all ten table rows and emits the discrepancy.

No ground-truth labels for buried geology, volcanic glass, or material quality
were supplied. The real-data lane is descriptive and cannot adjudicate those
claims. Synthetic ground truth is used only for controlled algorithmic tests.
