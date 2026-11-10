# Harmonic LiDAR: verified diagnostic expansion

12 September 2026. Local verification: **2026-09-12T16:12:21.106788+00:00**. This is a component of the connected HNC research review. The full repair/expansion goal remains active.

**The original amplitude detector remains near chance on a larger, unchanged synthetic terrain model.** Its mean AUROC is **0.5073**. A control designed around the planted core/ring shape improves detection, but is still well below the original 0.80 target. Simple background whitening did not repair the φ² detector. A diagnostic supplied with the true target shape and location performs much better, showing that useful signal is present in these simulated images. That privileged diagnostic is neither a deployable detector nor an upper bound on what an unknown-location detector can achieve.

This preserves the user's connected account: the HNC research describes interacting observation, signal, memory and timing components. Testing this amplitude component does not adjudicate the People of the Threshold, Maeshowe, two-channel twig readings, light-to-passage binding, daily/solstice/annual timing or nineteen-year cycle. Those links remain in the [connected legacy review](Legacy-system-connected-review-2026-09-12.md).

## What ran and what was verified

The new study contains **1,280,000 test images plus 384,000 independent null calibration images**, across 128 disjoint seed streams and the two original grids. This is four times the old 320,000-example test size. Signal amplitudes, shape ranges, backgrounds, missing patches, blur, FP64 precision and batch size were retained. Eleven original filters and nine new operational or privileged diagnostics were scored on the same images. Thresholds were calibrated separately for each complete search statistic at the 95th percentile of its independent null samples. No improvement was obtained by making targets stronger or backgrounds easier.

Two historical diagnostic shards add 10,000 tests and 3,000 calibration images. All recorded original metrics, thresholds, confusion counts and localization summaries for all eleven methods in both shards reproduce **exactly** using the original container. The original 64 result files were separately verified against their stored output hashes; their old mean φ² AUROC remains 0.5104214. Historical diagnostic results do not enter the new-seed estimates.

The first pilot, **6505264**, failed an exact repeatability check before writing experiment results. The cause was confirmed by repeated CUDA atomic sums producing small numerical differences. A separate immutable v2 replaces them with a fixed matrix reduction; all nine grouped checks pass, including original image/RNG identity, independent NumPy numerical checks, sign invariance, tie handling and exclusion of truth metadata from operational scores. The original failure is retained.

**6505275 pilot, 6505304 full study and 6505336 independent audit all COMPLETED, exit 0**, in 16, 53 and 161 seconds. The full study used four distinct GPUs on one node; their UUIDs are verified. Including the failed nine-second pilot, actual allocation is **239 node-seconds = 0.066389 node-hours**. The larger study was sized from the pilot before submission and remained within its ten-minute ceiling.

All **274 archive members**, every array/result hash, all 1,677,000 stored test/calibration examples, 20 methods' metrics and all five recorded strata were verified. Independent NumPy calculations also checked 16 method scores and all selected positions on **1,040 saved image/template pairs**. The four jitter-null maps are not included in that numerical map sample, but their complete recorded score arrays and statistics are checked. Local verification repeated these checks; statistical analysis exact agreement is **True**, maximum cross-runtime difference 0. This is a computational audit, not independent physical validation.

## New-seed results

AUROC measures class separation: 0.5 is chance and 1.0 is perfect. It is not classification accuracy. Each grid contains 640,000 test images. The final column gives true-positive rates on the two grids at independently calibrated thresholds; realized mean false-positive rates for the displayed methods are approximately 5%.

| Method | 80×80 AUROC | 40×40 AUROC | True-positive rate, 80×80 / 40×40 |
|---|---:|---:|---:|
| Original φ² filter, entire image | 0.5071 | 0.5074 | 5.58% / 5.42% |
| Original LoG control, entire image | 0.5110 | 0.5134 | 5.78% / 5.71% |
| φ² filter, common search area | 0.5282 | 0.5363 | 6.79% / 6.78% |
| Background-whitened φ², common search area | 0.5275 | 0.5092 | 5.97% / 5.46% |
| Background-whitened LoG, common search area | 0.5223 | 0.5102 | 5.61% / 5.42% |
| Model-informed Gaussian bank | 0.5674 | 0.5401 | 9.47% / 6.78% |
| Model-informed core/ring bank | 0.6344 | 0.5779 | 23.66% / 10.71% |
| Ring bank GIVEN the true location | 0.8537 | 0.7518 | 58.52% / 35.16% |
| Matched diagnostic GIVEN exact shape and location | 0.9428 | 0.8432 | 82.75% / 38.19% |

The last two rows use otherwise unavailable truth information and must not be compared as practical detector successes. Their reported positions are supplied, not discovered. All twenty methods, confidence intervals and strata are retained in [the full statistical ledger](lidar-diagnostic-6505336/audit/analysis.json).

Restricting φ² to the common permitted search area improves its AUROC by 0.02106 and 0.02892 on the two grids, but leaves it weak. Adding whitening changes that result by −0.00070 on 80×80 (interval includes zero) and **−0.02708** on 40×40 (clear deterioration). The proposed whitening candidate is therefore **not supported as a repair**.

The model-informed ring bank reaches 0.6344 and 0.5779 AUROC, with true-positive rates **23.66% and 10.71%**, at false-positive rates **5.11% and 5.10%**. Its mean within-shard median location error is **14.83 pixels** on 80×80 and **9.80 pixels** on 40×40. Only **20.20% and 5.15%** of planted positives are both detected and localized within three pixels. Better class separation is therefore not reliable localization. Missing patches weaken this control on both grids; blur also weakens its 40×40 arm. This improvement is a conventional, generator-informed comparison and supplies no evidence of unique φ² performance.

The ring bank's AUROC rises to **0.8537/0.7518** when the true location is given, and to **0.9428/0.8432** when exact transformed shape and location are given. These successive diagnostics show a substantial gap associated with searching unknown locations and using approximate templates. They do not identify the single cause of every failure or prove optimal attainable performance under the full non-Gaussian nuisance model.

## Paired uncertainty, including negative results

These are the four declared contrasts in each grid, using 20,000 paired shard bootstrap draws, two-sided sign flips and Holm adjustment across all eight tests. Confidence intervals are unadjusted 95% intervals; adjusted p values do not make the intervals simultaneous. The pooled two-grid analysis is descriptive. No mixed-grid pixel-error summary is interpreted physically.

| Grid | Contrast | AUROC difference | 95% interval | Holm p |
|---|---|---:|---|---:|
| 80×80 | phi2_roi − phi2 | +0.02106 | [+0.01966, +0.02249] | 0.000400 |
| 80×80 | whitened_phi2_roi − phi2_roi | -0.00070 | [-0.00262, +0.00122] | 0.474976 |
| 80×80 | whitened_log_roi − whitened_phi2_roi | -0.00521 | [-0.00635, -0.00403] | 0.000400 |
| 80×80 | matched_ring_roi − whitened_phi2_roi | +0.10694 | [+0.10488, +0.10904] | 0.000400 |
| 40×40 | phi2_roi − phi2 | +0.02892 | [+0.02752, +0.03027] | 0.000400 |
| 40×40 | whitened_phi2_roi − phi2_roi | -0.02708 | [-0.02910, -0.02501] | 0.000400 |
| 40×40 | whitened_log_roi − whitened_phi2_roi | +0.00095 | [-0.00007, +0.00194] | 0.135893 |
| 40×40 | matched_ring_roi − whitened_phi2_roi | +0.06865 | [+0.06657, +0.07073] | 0.000400 |

## What the original papers still require

Both native DOCX files were verified by SHA-256 and Git blob identity. The earliest located Git additions are **24 March 2026**, commit **7787e45c832ccb216c55dc965df51a16db45a895**. This dates located versions, not definitive first authorship. Native files, exact hashes and later version paths accompany [the source coverage record](lidar-source-coverage-20260912.json).

The original paper gives a ten-row shell table while calling it nine shells; the reference implements all ten table rows. On the supplied grids, shell centers 3–6 (80×80) and 3–5 (40×40) lie within the conservative full-annulus sampling band. Out-of-band filter tails may still contribute, but that does not resolve their nominal center wavelengths. The corresponding shortest full-annulus wavelengths are about **169.6 m and 564.1 m**. The v2 paper's **5.30–12.15 m** material wavelengths at the stated seed frequency cannot be resolved by these grids.

The phase/coherence map and v2 material-specific extension were not executed by this amplitude benchmark. The amplitude filter is real and nonnegative, so wherever it is positive it preserves each Fourier coefficient's phase. A frequency-plane phase coefficient is not automatically a phase measurement at a spatial location. An explicit phase construction and spatial mapping are needed before testing the claimed core/boundary classification; guessing this missing rule would change the hypothesis.

The source calls the system LiDAR while describing SRTM radar-derived surface elevations. No paired subsurface/material ground truth is supplied by this benchmark. Synthetic detection cannot validate obsidian probabilities, buried geology, acoustic coupling or excavation targets.

Additional harness corrections are documented: old nuisance indices 0–2 all contain terrain, slope and ridges; they are not isolated nuisance tests. Missing patches are set to zero before final centering. Ties were previously order-dependent. The old aggregate glob can pick up stdout sidecars, and its adjustment is Bonferroni multiplication despite its Holm label. Its stored protocol time also follows the submission receipt, so prior registration is not established by those timestamps. These issues are retained openly; they do not explain away the reproducible weak amplitude result. The two grids also change physical target dimensions because shapes are sampled in pixels, preventing attribution of cross-grid changes solely to resolution.

## Evidence and next decision

The independent-calibration choice follows the need to assess the complete unknown-position search statistic, discussed by [Vio et al., A&A 627 A103 (2019)](https://www.aanda.org/articles/aa/full_html/2019/07/aa34854-18/aa34854-18.html). Here thresholds are empirical; no Gaussian pointwise-tail assumption is imposed on searched maxima.

Evidence archive: **591,862,567 bytes**, SHA-256 **b357480b54e4ba14def1835809d07839b03daf6395d2725943434162ea02869f**. Analysis SHA-256 **7890876dcfd67185bdd2c0aeec5a744cafcba05618b8bbed78061a8529036f7d**. Frozen implementation-v2 manifest **255d45a1222770eac0916adbab1233b7480a0b719f8cbca42a30b8681b4cbb13**; original implementation remains **62800896433e36512e84b4dff9928f2512c7c6cdc491e6481c0cdedbac2e9c05**. See [local verification](lidar-diagnostic-6505336/local-verification.json) and [source/coverage audit](lidar-source-coverage-20260912.json).

The next LiDAR experiment should specify the phase/spatial mapping from source evidence and separate physical sampling from target size; detector search and template mismatch also warrant a new, frozen design. Whitening is retained as a failed candidate. The model-informed control is diagnostic, not promoted to a validated HNC detector. The integrated legacy/time account and remaining experiment families remain open.
