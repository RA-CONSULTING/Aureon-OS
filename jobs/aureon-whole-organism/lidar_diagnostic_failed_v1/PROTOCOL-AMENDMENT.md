# Harmonic LiDAR diagnostic expansion v1 — 12 September 2026

This new diagnostic protocol is fixed before observing its new-seed results.
The earlier reference benchmark, original papers and old outcomes remain
immutable. No claim of original preregistration is made: the old protocol's
recorded registration time is later than its submission receipt.

The original synthetic generator, all random draws, signal amplitude/scale
ranges, slope/ridge backgrounds, missing patch and blur are preserved. A
source-hash-locked return amendment exposes the generated template, transforms
it through the same missing/blur operations and reports parameters without
changing the returned images or random state. Tests require bitwise parity.
The first three old nuisance names denote the same composite background;
indices 3 and 4 add missingness and blur. Report those indices literally and
never claim separate pure-slope or pure-ridge robustness.

Historical diagnostics repeat 5,000 tests and 1,500 calibration examples on
shards 0 and 32 using the original seeds, precision, batch size and container.
Report every difference in the original eleven methods; original data contain
aggregate outcomes, not per-example score arrays. These diagnostics may assess
reproduction but must not enter the independent new-seed aggregate.

New study: 128 shards, alternating the original two grid geometries, each with
10,000 test examples and 3,000 independent all-null calibration examples.
Total 1,280,000 test examples plus 384,000 calibration examples. Original batch
size 64 and FP64 remain fixed; seeds are in diagnostic-config.json. This is a
larger synthetic replication from the same generator, not a new physical corpus.

Retain all eleven original filters. New operational candidates use only each
image, grid and predeclared synthetic center support. phi2_roi restricts the
original maximum to that support; whitened_phi2_roi and whitened_log_roi divide
Fourier coefficients by the square root of the image's annular mean power, with
a relative 1e-6 power floor, and use fixed white-noise filter-energy scaling.
Integer frequency annuli are measured in pixel units. All share the same ROI.
The 3-template Gaussian and 27-template core-plus-ring controls weight template
correlation by inverse estimated power. Their shapes/ranges are explicitly
model-informed controls, not the paper's formula and not universally optimal
detectors. The ring bank assumes circular periodic template boundaries; the
finite generated target is not periodic. Do not equate a control gain to HNC
specificity. No target amplitude or data distribution is made easier.

Four privileged diagnostics use the true subpixel center rounded to the nearest
pixel (phi2, whitened phi2, ring-bank response) or the exact transformed planted
template at its exact original location. These consume truth metadata sampled
for nulls as well as positives. They are explicitly labelled truth diagnostics;
they are not deployable detections or mathematical upper bounds. Model-informed
operational candidates cannot read that metadata; test the isolation.

Each method's full maximum/search statistic receives its own independent
calibration 95th percentile threshold, with strict score > threshold. This
calibrates the search operation as used, rather than applying a pointwise
Gaussian cutoff to an image maximum. See Vio et al., A&A 627 A103 (2019),
https://www.aanda.org/articles/aa/full_html/2019/07/aa34854-18/aa34854-18.html
for why unknown-position matched-filter peaks require suitable false-detection
calibration. The empirical calibration here does not assume Gaussian peak tails.

New metrics: tie-averaged AUROC, grouped average precision, realized FPR/TPR,
positive localization median/p90 and fractions localized within three pixels,
including joint detection/localization. Truth-informed positions have no
meaningful localization comparison. Report both grids separately and combined
equal-shard means; pixel errors are not pooled across physical grid spacings.
Use 20,000 paired shard bootstrap draws separately within each grid and pooled,
fixed seed 29120926; compare four operational changes (ROI phi vs original phi,
whitened phi vs ROI phi, whitened LoG vs whitened phi, ring vs whitened phi).
Two-sided paired sign flips with 20,000 draws, Holm adjustment across these
four comparisons in each of the two grids (eight tests total). Pooled comparisons
are descriptive. Report all methods, all strata and negative results.

Pilot ceiling: one node/one GPU, ten minutes; full ceiling: one node/four GPUs,
ten minutes, at most 1/3 node-hour total. Launch full only after pilot tests and
source checks pass, both original grids reproduce or discrepancies are resolved,
and extrapolated full execution plus 50% and one minute stays within ten minutes.
The four full workers process disjoint shards and must prove distinct GPU UUIDs.
Save per-example scores, labels, nuisance, parameters, predicted positions,
errors, calibration scores, and first four full images/templates per lane/shard
for independent NumPy audit. Hash every result array and immutable input pack.

Physical subsurface, material, calendar, epigraphic and legacy-system claims are
outside this detector diagnostic. It informs the reliability of one measurement
component in the connected HNC account; it cannot establish its historical story.
