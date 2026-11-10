# Aureon Stage 1: complete retrospective comparison

**The full Aureon condition underperformed the frozen baseline in this retrospective synthetic comparison.** The complete matrix now contains 128 shards, 12 conditions and 122,880 responses. Strict artifact audit **6500947 passed** after recovery of the previously missing shard 99. This is not a pass of the original frozen protocol.

| Metric | Full Aureon | Frozen baseline |
|---|---:|---:|
| Composite score | 0.630701 | 0.645993 |
| Verdict accuracy | 65.98% | 67.70% |
| Action accuracy | 18.79% | 22.11% |
| Source completeness | 88.88% | 89.88% |
| Mean Brier score (lower is better) | 0.651531 | 0.649248 |
| Valid JSON | 99.736% | 100.000% |
| Mean response latency, seconds | 3.420 | 2.452 |

Each main condition has 10,240 responses, paired by the same scenario and repetition. The inherited 20,000-draw bootstrap treats the shard as its cluster, with random seed 10091.

| Exploratory full-minus-baseline contrast | Difference | 95% shard-bootstrap interval |
|---|---:|---:|
| score | -0.015292 | [-0.019917, -0.010667] |
| verdict_accuracy | -1.718750 percentage points | [-2.841797, -0.595703] |

Both intervals lie below zero. The exploratory advantage rule is not met. These intervals are conditional on the synthetic fixtures, inherited scoring, model/runtime and retrospective amendment; they are not prospective confirmation or a statement about every Aureon configuration.

## What was repaired

The old shard 99 failed before requests began: the model server requested 85.5 GiB while 84.59 GiB was free on a device. Recovery **6500368_99** reduced the memory reservation from 90% to 85% and wrote to an isolated directory. Its model snapshot, original benchmark code, source pin, fixtures, 12 conditions, temperature zero, 8,192-token budget and concurrency 32 were preserved. It ran for 4m18s on one node/four GPUs, or **0.071667 NHR / 0.286667 GPU-hours**.

All 960 recovery responses were saved. Five were invalid JSON, so the unchanged frozen benchmark correctly exited 1 and the job state is FAILED. The amended wrapper saved the output hashes and exit code despite that failure. The original shard and original failed campaign remain untouched.

The separate retrospective analysis retains invalid model output with the original zero score rather than dropping it or changing it. The full matrix contains **280 invalid replies (0.228%)**, including 27 in the full condition and none in the frozen baseline. An invalid model reply is an observed performance failure; malformed receipt data, mismatched source/runtime identity, missing pairs or changed scores still stop the audit.

## Audit coverage

- All 128 × 960 expected condition/scenario/repetition keys are present exactly once.
- Every scenario file was regenerated from the frozen seed and compared. Every raw response was reparsed, rescored with the original function and checked against its recorded score; condition summaries were recomputed.
- Raw/scenario hashes, known benchmark/protocol/voice/adapter/serving-configuration hashes, recorded model snapshot and vLLM 0.15.1 were checked. The aggregate helper hash matches the locally recovered original.
- Ten local preflight checks cover zero-score retention and rejection of altered scores, duplicate/missing pairs, wrong model/source identity, type-confused safety declarations and malformed JSON receipts.
- The audit completed in 12 seconds. The downloaded report hash matches the remote file: `91e5281235f954c62a4fffb98d15bfecf0d36450dd5f6bea9eb69e2bf22b1395`.

## Secondary condition summaries

These are descriptive comparisons across the tested ablations, not multiplicity-adjusted claims or a selected new winner.

| Condition | Composite score | Verdict accuracy | Action accuracy | Invalid JSON |
|---|---:|---:|---:|---:|
| full_organism | 0.630701 | 65.98% | 18.79% | 27 |
| frozen_baseline | 0.645993 | 67.70% | 22.11% | 0 |
| prompt_only_identity | 0.631697 | 63.38% | 23.41% | 1 |
| neutral_labels | 0.656579 | 70.58% | 23.49% | 22 |
| no_memory | 0.619100 | 63.49% | 16.10% | 34 |
| no_metacognition | 0.629678 | 65.97% | 17.93% | 22 |
| no_affect_heart | 0.632203 | 63.16% | 21.46% | 36 |
| no_conscience_simulation_only | 0.639494 | 68.48% | 19.29% | 13 |
| field_disconnected | 0.626667 | 58.13% | 26.60% | 40 |
| auris_shuffled | 0.616269 | 61.29% | 18.02% | 18 |
| no_auris | 0.639478 | 64.67% | 22.72% | 40 |
| no_queen | 0.655961 | 67.65% | 25.24% | 27 |

## Next repair and limits

Action accuracy is poor for both main conditions, and composite calibration is weak. The next useful step is to classify the wrong actions, invalid schemas and family-specific errors, then repair the execution/response contract and freeze a new prospective comparison. Merely adding compute to the same setup would not repair this negative result.

The original permissive parser and score semantics are preserved: syntactically valid JSON does not necessarily satisfy a strict response schema. Model-weight files were not independently hashed; snapshot/runtime metadata is the available evidence. Safety flags are recorded declarations, not independent proof of all runtime effects. The recovery occurs later and changes the memory reservation. Synthetic software behaviour does not establish a physical field or consciousness.

Evidence: `stage1-retrospective-audit-6500947.json`, `stage1-recovery-collection.json`, `stage1-recovery-6500368-summary.json`, and the separate recovery/retrospective amendments.

## Follow-up design audit

Error diagnosis 6501165 and local frozen-fixture regeneration found only **514 distinct user prompts across 5,120 fixture records**, including four families with one repeated prompt each. The original system prompt enumerates actions but does not fully define the action policy expected by the scorer. Most action failures are valid action words that differ from those targets, not malformed JSON.

The scores and inherited exploratory intervals above are preserved. They are not evidence of performance across thousands of independent tasks and must not be generalized beyond this repeated, synthetic benchmark. The concrete prospective repair specification, family counts, action distributions and verified local 769-file export are in `Stage1-error-diagnosis-2026-09-12.md`.
