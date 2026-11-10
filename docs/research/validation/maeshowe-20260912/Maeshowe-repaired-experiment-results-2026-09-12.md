# Maeshowe repaired experiment — results

12 September 2026. The broad experiment repair and expansion goal remains active.

The repaired twig reader now uses a separately declared medieval alphabet and preserves uncertain counts. The original frequency model remains available for reproduction, with its output identified as a symbolic model. A complete conditional control experiment ran successfully on Isambard: **job 6501577, COMPLETED, exit 0, three seconds allocated**, no GPUs requested. It evaluated **120,960 configurations** and retained every result.

## What changed

The repository repair introduces `aureon/wisdom/maeshowe_epigraphy.py` and connects it through the existing Maeshowe command's `--epigraphy-input` option. A mark record must specify the alphabet, which side supplies the group count, and group order. It can retain several possible left/right counts or use null for unobserved counts. Invalid alternatives remain visible. It never selects a reading by its frequency, proposed word meaning or coherence score.

The medieval preset follows the 16-character, 6:5:5 structure described by Barnes, with explicit reverse or forward numbering. For example, under reverse numbering with the group count on the left, left 3/right 1 produces candidate **f**. The older program's forward 24-character mapping produces **t**. That difference is why the two operations now have distinct interfaces. [Barnes, printed p. 5, note 1](https://www.arild-hauge.com/PDF/Barnes_Orkney_2003_pp_4-17.pdf)

The repaired historical-model output includes its evidence class and states that physical reading is unverified. Its documentation records the actual baseline, **Γ=0.493163 with 9/13 complete**, rather than the report's unreproduced 0.8223 with 8/13. The command also handles Unicode output on Windows. No model weights or thresholds were changed to improve a result; original source copies remain preserved by hash.

**Validation:** 12 reader checks passed locally and in Isambard job 6501577. Four additional command-integration checks passed locally, giving 16 local checks. The same **16 checks passed in Isambard job 6501655**, COMPLETED, exit 0, three seconds allocated. The three repository-file hashes match the staged patch. No commit or publication occurred. [Integration receipt](C:/Users/samle/Documents/Codex/2026-09-05/k/outputs/maeshowe-repository-checks-6501655/verification.json)

## Full conditional control results

The protocol fixed the original nine completed rune choices, the 13-entry catalogue, the frequency vocabulary and the scoring formula. There are 5,040 distinct allocations of those nine runes to the original completed-wall counts (3, 1, 2, 3). Combining these with 24 permutations of four wall frequencies gives 120,960 configurations. The original configuration is included once.

| Comparison | Configurations as favourable as the original | Exact fraction |
|---|---:|---:|
| Coherence Γ at least as high, both mappings varied | 18,480 / 120,960 | **15.2778%** |
| At least as many phi hits, both mappings varied | 70,320 / 120,960 | **58.1349%** |
| At least as close to a Schumann target, both mappings varied | 30,240 / 120,960 | **25.0000%** |
| Coherence Γ at least as high, original wall frequencies retained | 2,100 / 5,040 | **41.6667%** |
| At least as many phi hits, original wall frequencies retained | 2,400 / 5,040 | **47.6190%** |

These are exact fractions within a declared finite model comparison. They are **not probabilities that a historical theory is true or false**. The original rune and inscription selection, phi-based amplitude choices and target selection are inherited. This test cannot undo unrecorded researcher choices or establish historical intention.

The Schumann comparison follows the original program's selection of the nearest of seven stored targets. It is not a comparison with a contemporaneous measured electromagnetic recording. Because permuting rune placement does not change the mean selected rune frequency, the beat statistic does not vary over the 5,040 assignments within a wall-frequency permutation; the raw rows record that dependency.

## Sensitivity to the built-in phi multiplier

At the original mapping, changing all three amplitude factors to 1 while keeping the phi detection targets fixed changes the result as follows:

| Quantity | Original model | Neutral amplitude comparison |
|---|---:|---:|
| Phi-resonant completed entries | 1 | 0 |
| Exact phi entries under the program's tolerance | 1 | 0 |
| Mean seer frequency | 398.9756 Hz | 442.6667 Hz |
| Master beat | 29.2832 Hz | 72.9744 Hz |
| Coherence Γ | 0.493163 | 0.333362 |

This demonstrates dependence on the chosen amplitude transformation. It does not measure a change in the chamber. The model's “active” and “dead” labels should be read only as threshold labels for its numerical score.

Both preserved code versions reproduce the same baseline. All 96 original rune/frequency-pair calculations were checked against a separate numerical implementation before the control population was evaluated. All 24 hypothetical original pivot inputs were retained; none reaches 0.945. The pivot-only upper bound remains 0.930769 even if the other two component scores are perfect.

## Evidence and resource receipts

The downloaded export's SHA-256 is `ef00715678676572465309cb1fe83fee0ad14add89046ec02b33538a455a9e9a`. Local verification checked the four result-file hashes, frozen input manifest and protocol, terminal scheduler state, all **120,960 unique configuration identifiers**, and independently recounted all five reported rank numerators from the saved CSV.

The batch request used one node, four requested CPUs, 4 GB and a ten-minute ceiling. The scheduler recorded a 72-CPU allocation and three seconds elapsed. Under the account's previously verified quarter-node minimum this corresponds to about **0.000208 NHR**; this is a scheduler-based estimate, not a refreshed portal debit. The finite comparison completed in approximately 0.62 seconds inside the allocation. More nodes would not improve this experiment.

[Complete results](C:/Users/samle/Documents/Codex/2026-09-05/k/outputs/maeshowe-controls-6501577/results/summary.json) · [Raw configuration outcomes](C:/Users/samle/Documents/Codex/2026-09-05/k/outputs/maeshowe-controls-6501577/results/conditional-controls.csv.gz) · [Independent local verification](C:/Users/samle/Documents/Codex/2026-09-05/k/outputs/maeshowe-controls-6501577/local-verification.json) · [Frozen protocol](C:/Users/samle/Documents/Codex/2026-09-05/k/work/maeshowe-repair-v1/PROTOCOL.md)

## What remains to complete this research strand

There is still no observed branch-count record for inscription 15, and the particular pair meant by “two twig runes” remains unidentified. The pending record correctly returns **UNOBSERVED_COUNTS**. These software results do not constitute a decipherment. The original historical-source corrections, complete inscription/wall register and independent readings of the RTI images remain necessary.

The People of the Threshold manuscript's 23 numbered claims are inventoried in the [source review](C:/Users/samle/Documents/Codex/2026-09-05/k/outputs/Threshold-Maeshowe-twig-runes-review-2026-09-12.md). Its source-level historical tests and the original calendar-wheel/polar-specificity transformations remain outstanding. The new reader is ready to accept source-backed count alternatives when available.

For the wider compute programme, the next expansion dependencies remain the prospective Stage 1 action-policy/fixture repair and HNC throughput profiling with new initial-condition ensembles. Those need useful new data and improved throughput; this small completed archaeology calculation does not use up their allocation envelopes.
