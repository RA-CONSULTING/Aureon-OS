# Stage 1 v2: verified recovery comparison

12 September 2026 · A separate operational replication sensitivity

**The cache repair completed the whole failed shard with zero transport failures. In the combined recovery comparison, full supplied context scored 88.15%, baseline 84.06%, and neutral labels 88.36% for jointly correct verdict and action.** Full context improved on baseline by 4.089 percentage points, with a 95% interval from 2.174 to 6.198 points. It showed no clear advantage over neutral labels. These are conditional results for the authored prompt templates, not a demonstration that the complete live Aureon system or the connected historical/HNC theory has been validated.

The recovery reran all 46,080 requests assigned to original shard 0 after a separate 7,680-call development pilot. Both completed under unchanged scientific inputs, model snapshot, adapter, scoring, request order and numerical serving settings. Compiler caches moved to a fresh node-local location, all four rank paths were verified, and the health supervisor remained active. There were 19 invalid model replies in the new evaluation; they remain failures in its denominator.

The combined 184,320-request sensitivity uses the entire new shard 0 and original healthy shards 1–3. It has zero transport failures and 83 invalid model outputs. The original degraded first run, including its 39,484 terminal transport failures, remains unchanged. Its original full/baseline/neutral scores are 69.18%/66.07%/69.38%. The higher recovery scores cannot be described as a scientific improvement over that original run because repairing collection removed missing service responses.

## Declared contrasts

Differences and intervals below are percentage points. The analysis uses the frozen 20,000-draw family-stratified paired-template bootstrap and Holm adjustment across three primary contrasts.

| Contrast | Difference | 95% interval | Adjusted p |
|---|---:|---:|---:|
| full_baseline_policy_interaction | -1.367 | -3.932 to +1.367 | 0.635768 |
| full_minus_baseline_explicit | +4.089 | +2.174 to +6.198 | 0.000450 |
| full_minus_neutral_explicit | -0.208 | -1.419 to +1.185 | 0.765312 |

## All supplied-context conditions

These are controlled prompt-context variants. Their names do not demonstrate that a corresponding live module was executed or removed. The full condition does not dominate the other supplied variants.

| Condition | Listed action words only | Explicit action policy |
|---|---:|---:|
| auris_shuffled | 54.648% | 88.216% |
| field_disconnected | 51.367% | 87.865% |
| frozen_baseline | 48.698% | 84.062% |
| full_organism | 54.154% | 88.151% |
| neutral_labels | 54.531% | 88.359% |
| no_affect_heart | 50.234% | 87.526% |
| no_auris | 52.214% | 87.578% |
| no_conscience_simulation_only | 56.276% | 88.359% |
| no_memory | 54.036% | 88.815% |
| no_metacognition | 55.000% | 88.828% |
| no_queen | 53.698% | 87.865% |
| prompt_only_identity | 48.984% | 85.091% |

## Variation across families

Full-minus-baseline under the explicit policy is not positive in every family. Zero and negative differences are preserved.

| Frozen family | Difference in points |
|---|---:|
| supported | +0.781 |
| conflict | +1.432 |
| insufficient | -2.995 |
| injection | +0.000 |
| restricted | +7.943 |
| causality | +0.000 |
| stale_provenance | +2.214 |
| consent_boundary | +16.536 |
| care_under_cost | +1.953 |
| memory_continuity | +13.021 |

Among the 6,596 original shard-0 requests that had successful transport, joint correctness changed on 377 repeated requests: 177 gains and 200 losses. That is descriptive serving variability, despite temperature zero; it is not evidence that recovery reproduces each original reply exactly.

The 60 evaluation templates are drawn from ten related authored families; repeated instances and two repetitions do not create 184,320 independent research tasks. The evaluation uses a frozen context snapshot and synthetic fixtures. It does not resolve the connected legacy system's light-to-mark-to-passage mapping, and cannot stand in for a time-dependent reading of that research.

## Verification and costs

Recovery job **6503592 COMPLETED, exit 0**, in 2,742 seconds: **0.761667 node-hours** on one node/four GPUs. The service step's cancellation was intended cleanup after the client finished. Audit **6504504 COMPLETED, exit 0**, in 19 seconds. Every one of the 53,760 recovery calls had its actual request checked, raw response reparsed and score recomputed. Original source hashes were rechecked; the combined matrix and all paired statistics reproduced exactly locally at **14:50:01 UTC**. All 63 members of the 55,990,128-byte export were verified.

Evidence: [local verification](./stage1-v2-recovery-6504504/local-verification.json), [complete analysis](./stage1-v2-recovery-6504504/analysis/analysis.json), [export receipt](./stage1-v2-recovery-6504504/export-receipt.json). Archive SHA-256: `a0ef39e6531a5542f73054ddbab9ba6744f8c1499601335c776a7aefdd60b004`. The raw evidence remains in both the local workspace and Isambard evidence store.
