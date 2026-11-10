# QGITA missing-data repair: verified results

12 September 2026 · Method-development study on the known UCR panel

**The observed-triplet repair substantially improved QGITA's missing-data performance in every tested scenario.** On the primary measure, which gives each of the 46 source families equal weight, success was **26.13–28.40%**, compared with **12.01–15.54%** for the original last-value filling method. All six unadjusted 95% improvement intervals excluded zero; the Holm-adjusted tests also supported improvement across the six comparisons. Absolute localization performance remains limited: even the complete-data reference scores only **28.55%** on this family-balanced measure.

The repair is specific. QGITA's score uses three observations at a time. Filling a gap by carrying a previous value forward can alter the curvature when the signal resumes. The new method requires all three contributing observations to be present; it skips an unavailable calculation and takes the strongest remaining valid component. It retains the original curvature equation, time indices, training scales, peak-selection rule and endpoints. It requires an explicit missing-data mask, uses no future observations and does not manufacture an answer where no component is valid.

## New-mask results

The complete study includes all 250 original series and 46 provenance families. Each new scenario has 32 deterministic masks per series: **8,000 masked sets per scenario**, or **48,000 new masked sets** overall, evaluated with both methods. Random masks have exact specified counts; burst percentages are approximate because blocks overlap or clip at the test boundary.

The primary columns average within series and then equally across families. The separate series-average column gives each of the 250 series equal weight; its higher values reflect the unequal sizes and performance of source families. These measures must not be interchanged.

| Scenario | Old filling: family-balanced | Observed triplets: family-balanced | Observed triplets: series-average | Improvement in points |
|---|---:|---:|---:|---:|
| 1% random missing | 15.54% | 28.40% | 42.95% | +12.86 |
| 5% random missing | 14.15% | 28.34% | 42.65% | +14.19 |
| 10% random missing | 12.87% | 27.53% | 41.56% | +14.66 |
| 20% random missing | 12.07% | 26.45% | 39.49% | +14.38 |
| Five bursts, about 5% missing | 13.35% | 27.62% | 41.95% | +14.27 |
| Five bursts, about 10% missing | 12.01% | 26.13% | 39.79% | +14.12 |

The confidence intervals below use 20,000 paired family-cluster bootstrap draws with the frozen seed. Holm adjustment covers the six new-mask candidate-versus-LOCF comparisons. Differences are percentage points.

| Scenario | Improvement: 95% interval | Adjusted p | Difference from complete data | Difference from complete data: 95% interval |
|---|---:|---:|---:|---:|
| 1% random missing | +5.69 to +21.27 | 0.001600 | -0.15 | -0.31 to -0.01 |
| 5% random missing | +6.74 to +22.83 | 0.001600 | -0.21 | -0.71 to +0.37 |
| 10% random missing | +7.60 to +22.83 | 0.001050 | -1.02 | -2.11 to +0.15 |
| 20% random missing | +7.68 to +22.07 | 0.001000 | -2.10 | -3.97 to -0.16 |
| Five bursts, about 5% missing | +7.78 to +21.33 | 0.000900 | -0.94 | -1.62 to -0.41 |
| Five bursts, about 10% missing | +7.82 to +20.94 | 0.000900 | -2.42 | -3.49 to -1.40 |

All six candidate scenarios satisfy the separately declared noninferiority margin: their lower difference-from-clean limits exceed −5 percentage points. **This does not mean missingness has no cost.** At 20% random missingness, the estimate is 2.10 points below clean; the larger-burst condition is 2.42 points below clean. Their intervals remain below zero. Noninferiority here means the decline stays within the particular declared margin, not equality or universal robustness.

## Failures and unavailable scores remain visible

Each scenario contains 8,000 paired mask cases. Gains mean a previously incorrect LOCF localization became correct; losses mean the reverse. Improvement is not universal across the source families.

| Scenario | Gains over LOCF | Losses versus LOCF | Families worse | Families unchanged | Mean scoreable test positions |
|---|---:|---:|---:|---:|---:|
| 1% random missing | 1,431 | 77 | 13/46 | 16/46 | 99.00% |
| 5% random missing | 1,566 | 116 | 13/46 | 13/46 | 95.00% |
| 10% random missing | 1,594 | 119 | 11/46 | 13/46 | 90.00% |
| 20% random missing | 1,636 | 173 | 12/46 | 12/46 | 79.96% |
| Five bursts, about 5% missing | 1,982 | 83 | 9/46 | 16/46 | 95.09% |
| Five bursts, about 10% missing | 1,984 | 116 | 10/46 | 16/46 | 90.44% |

There were no whole-series abstentions in this panel, but individual times can be unscoreable. At 20% random missingness, only about 79.96% of test positions receive a valid score. The method does not claim to reconstruct observations inside gaps. Negative series/family changes and counts of unscoreable positions remain in the ledgers.

## What supports the proposed failure mechanism

The audit recomputed the winning three-point component and checked whether it contained an imputed value. It also counted complete-data successes lost under LOCF and recovered by the repair.

| Scenario | Failed LOCF selections using an imputed knot | Clean successes lost under LOCF and recovered |
|---|---:|---:|
| 1% random missing | 4,174/5,918 (70.5%) | 1,428/1,444 (98.9%) |
| 5% random missing | 5,051/6,038 (83.7%) | 1,527/1,585 (96.3%) |
| 10% random missing | 5,410/6,150 (88.0%) | 1,522/1,689 (90.1%) |
| 20% random missing | 5,882/6,304 (93.3%) | 1,515/1,874 (80.8%) |
| Five bursts, about 5% missing | 4,236/6,543 (64.7%) | 1,966/2,067 (95.1%) |
| Five bursts, about 10% missing | 4,356/6,685 (65.2%) | 1,964/2,229 (88.1%) |

These observations support the specific explanation that imputation-sensitive curvature contributes to the tested failures. An imputed knot alone is not proof that it caused every incorrect selection. Other failures remain, including those already present on complete data.

## Original masks and original results

The diagnostic phase reran all **3,750 original masks** and required exact agreement with the historical LOCF peak indices and localization decisions. All matched. This phase is explicitly retrospective; it was not relabelled as a new held-out evaluation.

| Historical scenario | Original LOCF family-balanced | New candidate family-balanced | Gains | Losses |
|---|---:|---:|---:|---:|
| 5% random missing | 14.36% | 28.03% | 235 | 18 |
| 10% random missing | 12.12% | 27.87% | 254 | 13 |
| Five bursts, about 5% missing | 12.86% | 27.29% | 323 | 18 |

The original negative LOCF findings remain unchanged. The previous Isambard byte-identity failure and supplemental numerical/decision audit also remain separate. A newly versioned method does not turn the old protocol's failure into a pass.

## Verification, sources and allocation

The source-preparation job verified the original 184,066,400-byte archive and all 250 canonical member hashes, representing 19,353,766 values. The data originates from the [UCR anomaly archive linked by its maintainers](https://www.cs.ucr.edu/~eamonn/time_series_data_2018/). The source ZIP was checked in memory; private numerical arrays are retained on Isambard under the new declared storage amendment, without redistribution or Git inclusion.

Eight candidate checks passed locally and on Isambard: original no-mask parity, scalar reference calculations, missing-placeholder invariance, prefix causality, all-missing abstention, earliest ties, original-control equality and input validation. Two additional audit checks validated a distinct matrix-form implementation and analytically known family contrasts.

Preparation **6504865** completed in 16 seconds; pilot **6504958** in 17 seconds; full study **6504999** in 134 seconds using 32 CPU workers; independent numerical audit **6505031** in 146 seconds using 16 workers. All four jobs completed with exit 0. Their combined allocated time was **0.086944 node-hours**. A rejected dependency submission had no compute job; preparation receipts were checked directly before the successful pilot submission.

The audit independently recomputed the complete original and candidate score timelines for **51,750 masked sets / 103,500 outcomes**, checked masks, peaks, contributing knots, endpoints and coverage, and verified every historical LOCF decision. All **9,506 exported members** were checked locally. The local review rechecked hashes, endpoints and original decisions, rebuilt all counters from the raw ledgers, and reproduced the family statistics exactly. Raw numerical source arrays were not exported.

Evidence: [local verification](./qgita-missingness-6505031/local-verification.json), [complete analysis and all family results](./qgita-missingness-6505031/audit/analysis-6505031.json), [export receipt](./qgita-missingness-6505031/export-receipt.json), [execution accounting](./qgita-missingness-status-v1.json). Export SHA-256: `52e8da3b3751f7fb8960bc8c793e0ae3c0be19a6d8dc163f4d8a443f5f9ace9e`.

The implementation is ready for further studies that supply reliable missingness masks. These are researcher-run results on an already known corpus; new masks do not create new independent source families. This experiment does not establish Fibonacci-specific superiority, independent scientific replication, a validated physical mechanism, or execution of the complete live Aureon system. It does not resolve the connected legacy/calendar system's missing light-to-mark-to-passage bindings. Those broader requirements remain active.
