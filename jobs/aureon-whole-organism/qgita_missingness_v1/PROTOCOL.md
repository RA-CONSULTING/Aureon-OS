# QGITA observed-triplet missingness study v1

This is a new researcher-run method-development and robustness study on the already known 250-series, 46-family UCR panel. Original clean and LOCF results remain frozen, including every negative noninferiority finding and the separate Isambard byte-identity failure. It is not a new held-out corpus or an independent scientific replication.

## Candidate and scientific question

Does selecting curvature only from actual observations avoid localization failures associated with LOCF-imputed knots? Preserve the corrected nonuniform second derivative, the 14 distinct Fibonacci knots, successor decision time, each component's clean-training 99th-percentile scale, earliest index ties and original UCR/strict endpoints. The sole candidate change excludes a component at a decision when its predecessor, centre or successor is masked. Missing values have no effect on eligible scores. The maximum over available components remains the score; when none are available, the decision is unscoreable. If a whole test region is unscoreable, record abstention and score localization as false in the full denominator.

Keep an unchanged LOCF control at every mask. Report the winning component and whether any of its three knots was imputed. This is attribution within the implemented score, not proof that every failure has one cause. Record whether the candidate retains a valid score at the clean winning index, overall scoreable coverage, missing fraction, selected peak, strict/UCR success and abstentions. Neither candidate scoring nor mask generation receives anomaly boundaries; endpoints are applied afterwards.

## Frozen phases

1. Historical diagnostic: all 250 series, original three scenarios and five original masks each, root seed 20260728. Require LOCF selected indices and success decisions to match all 3,750 original ledgers. Selected floating scores are reported with their observed numeric differences, while exact decision equality is mandatory. Compare candidate and LOCF on these known masks as method-development evidence.
2. New-mask expansion: all 250 series, 32 replicates of six scenarios. Exact MCAR rates 1%, 5%, 10% and 20%; five independently placed bursts of ceil(1% of test length) or ceil(2% of test length). Bursts may overlap and clip at the test end; report realized rates. Seeds use the first eight big-endian SHA-256 bytes of `20260912|dataset_id|scenario|replicate`. Names are mcar_01, mcar_05, mcar_10, mcar_20, burst_05 and burst_10. These 48,000 new masked sets produce 96,000 candidate/control outcomes. They increase mask coverage, not the number of independent source families.

No outcome-based method, series or mask selection is permitted. Candidate v1 is fixed before its new-mask outcomes. Any later repair must be separately versioned and retain v1's findings.

## Analysis

Average across replicates within each series, then series within each of the 46 original families, then equally across families. Use paired family-cluster resampling, 20,000 draws, generator SeedSequence([20260912,41]), common bootstrap family indices across contrasts. Report candidate-minus-LOCF and candidate-minus-clean for each scenario, with percentile 95% intervals. The six new-mask candidate-minus-LOCF comparisons form one primary family: use two-sided centered-bootstrap p values and Holm adjustment across six. A descriptive noninferiority decision against clean requires the lower interval to exceed -0.05; it is separate from the six superiority comparisons and does not establish universal missing-data robustness. Retain all series/family outcomes, including negative changes and abstentions. Historical diagnostic statistics remain separately labelled.

An improvement under supplied missingness metadata does not prove Fibonacci specificity, detect missingness without a mask, solve observational measurement bias, validate the full live Aureon system or establish a physical/HNC mechanism. The connected legacy/calendar reading remains a separate integrated evidence requirement.

## Validation, provenance and staging

Require no-mask bitwise parity with the original scorer, independent scalar observed-triplet calculations, missing-placeholder invariance, prefix causality, exact tie behaviour, honest all-missing abstention, original LOCF control equality and input validation. Use the existing NumPy 2.3.5 Isambard runtime. Verify original archive/member hashes and clean peak identities; private cached numeric arrays avoid repeated downloads under an explicit operational storage amendment. Do not redistribute source arrays or place them in Git.

First run a small representative implementation/throughput pilot, chosen by smallest numeric dataset ID per family, without selecting on performance. Measure per-series processing and memory before choosing the full allocation. Per-series immutable outputs and source/data/config hashes enable resumable waves; never overwrite completed outcomes or omit failed tasks. All 250 historical cases and all 250 new-mask cases must be present before aggregate conclusions.
