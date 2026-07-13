# Antarctic Candidate — True-to-Data Replay Report

## Purpose

This replay uses the supplied `object_antarctic_pointcloud.csv` rather than generative illustration. It reconstructs the shape directly from the point-cloud values and derives first-pass dimensional and morphology metrics.

## Data replay dimensions

- Grid size: 38 rows x 128 columns = 4,864 points.
- Point-cloud x span: 228.00 km.
- Point-cloud y span: 999.00 km.
- Point-cloud z span: 230.89 m.
- Median cell spacing: 1.795 km x 27.000 km, approx 48.47 km² per cell.

Important interpretation note: the point cloud represents the broad reconstruction grid, not only the final refined local core. The briefing scale model should therefore be kept separate:
- Refined local core: approximately 17 x 20 km.
- Regional envelope: approximately 526 x 226 km.

## Scale mathematics

### Refined local core

- Rectangle estimate: 340 km².
- Ellipse estimate: pi x 10 x 8.5 = 267.0 km².

### Regional envelope

- Rectangle estimate: 118,876 km².
- Ellipse estimate: pi x 263 x 113 = 93,365 km².

## Threshold morphology from actual point cloud

| Threshold | Area km² | Major axis km | Minor axis km | Eccentricity | Principal angle |
|---:|---:|---:|---:|---:|---:|
| top 50% / q=0.5 | 117867 | 614.3 | 266.9 | 0.901 | 83.9° |
| top 25% / q=0.75 | 58933 | 581.3 | 221.0 | 0.925 | 71.0° |
| top 19% / q=0.8 | 47156 | 578.0 | 210.5 | 0.931 | 70.1° |
| top 9% / q=0.9 | 23602 | 333.0 | 171.3 | 0.858 | 61.8° |
| top 5% / q=0.95 | 11825 | 286.2 | 141.0 | 0.870 | 61.9° |


## First-pass lineation orientation from point-cloud gradients

This is not a final Hough transform. It is a first-pass orientation check using the top 10 percent of gradient magnitudes from the point-cloud surface.

Top folded angle bins:

- 85-90 degrees: 282 edge pixels
- 80-85 degrees: 160 edge pixels
- 75-80 degrees: 34 edge pixels
- 70-75 degrees: 11 edge pixels
- 65-70 degrees: 0 edge pixels
- 60-65 degrees: 0 edge pixels
- 55-60 degrees: 0 edge pixels
- 50-55 degrees: 0 edge pixels


## Hollow / worked-zone scale scenarios

If the refined local core were used as the area model, a hypothetical internal void or worked layer would scale as:

volume = area x thickness x worked fraction

These values are not evidence of hollowing. They are size estimates only.

| Thickness m | Worked fraction | Volume km³ |
|---:|---:|---:|
| 10 | 1% | 0.027 |
| 10 | 5% | 0.134 |
| 10 | 10% | 0.267 |
| 25 | 1% | 0.067 |
| 25 | 5% | 0.334 |
| 25 | 10% | 0.668 |
| 50 | 1% | 0.134 |
| 50 | 5% | 0.668 |
| 50 | 10% | 1.335 |
| 100 | 1% | 0.267 |
| 100 | 5% | 1.335 |
| 100 | 10% | 2.670 |
| 200 | 1% | 0.534 |
| 200 | 5% | 2.670 |
| 200 | 10% | 5.341 |


## Interpretation

The true-to-data point cloud confirms a large elongated reconstruction with strong eccentricity under thresholding. The correct evidence wording is:

A broad reconstructed envelope exists in the supplied point cloud, while the briefings identify a much smaller refined local core. Any artificial or worked-zone hypothesis must be tested inside the local core and along high-regularity lineation zones, not inferred from the full regional envelope alone.

Next required tests:
1. Hough-transform line detection on the original raster products.
2. 50-100 matched near-pole control sites.
3. BedMachine v4 500 m extraction.
4. IceBridge/CReSIS radar profile search.
5. Sentinel-1 SAR and ice velocity overlays.
6. Gravity/magnetic cross-checks for density or basement structure.
