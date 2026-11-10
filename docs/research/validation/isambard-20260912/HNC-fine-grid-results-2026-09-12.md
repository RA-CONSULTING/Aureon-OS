# HNC: final fine-grid results

Production **6498143** completed on 12 September 2026 at 09:35:50 UTC after **1h57m30s**, using 32 nodes and 128 GPUs. Artifact audit **6498144 passed**. Analysis **6500155** rehashed all result grids and receipt chains and reproduced the final audit totals.

The campaign tested **6,303,616 trajectories**: 128 gain/delay/window cells, 121 alpha settings and 407 beta settings. Gains were 0.5, 0.75, 1, 1.5, 2.5, 4, 8 and 16; delays 10, 25, 50 and 100; averaging windows 1, 10, 50 and 100. The fine beta grid spans 0.9995–1.0015 at 0.000005 spacing, with separate controls. The maximum horizon was **16,777,216 steps**.

## Outcome

At the final horizon, **15,488/15,488 tested beta=1 cases** meet the finite-time stable rule. No beta=1.1 control meets it. Across the entire beta grid, 4,541,472 trajectories escaped, 1,658,294 met the stable rule, 90,557 remained bounded with a Lyapunov estimate above the threshold, and 13,293 remained bounded without a valid Lyapunov block. These four categories sum to all 6,303,616 trajectories.

The stable rule requires no escape beyond the 1e12 numerical threshold, at least one valid Lyapunov block and a finite-time Lyapunov estimate no greater than 1e-4 per step. It does not establish infinite-time stability.

| Steps | Stable beta=1 / tested | Escaped across all beta values | Cells with a downward 50% crossing | Median first crossing |
|---:|---:|---:|---:|---:|
| 65,536 | 15,381 / 15,488 | 38,587 | 34 / 128 | 1.000950937 |
| 1,048,576 | 15,488 / 15,488 | 2,221,316 | 128 / 128 | 1.000423625 |
| 4,194,304 | 15,488 / 15,488 | 4,013,004 | 128 / 128 | 1.000083512 |
| 8,388,608 | 15,488 / 15,488 | 4,369,379 | 128 / 128 | 1.000036271 |
| 16,777,216 | 15,488 / 15,488 | 4,541,472 | 128 / 128 | 1.000015067 |

The pilot median covers only 34 cells whose crossing fell inside the fine grid; it is not directly comparable to later medians covering all 128 cells. From 1,048,576 steps onward, all cells have a crossing. Their median moves from 1.000423625 to **1.000015067** by the final horizon. The final cell range is **1.000002542–1.000077614**. Those differences are parameter-dependent finite-time results, not an uncertainty interval for a universal constant.

The final million-step segment still adds **13,284 escapes**. The transition has therefore not stopped changing with observation time. At the final horizon 31 cells have an upward step somewhere in the curve and one has multiple downward crossings. The analysis retains every crossing, reports the first consistently and never interpolates across distant controls.

## Meaning for the correction

The expanded results support beta=1 as the author-directed reference to investigate for this delayed-feedback model and contradict treating beta=1.1 as its stable control under the tested conditions. They do not prove beta=1 is an exact universal stability boundary. The historical papers contain mixed beta wording; their preserved chronology and the dated author correction remain separate evidence. No correction to unrelated models that use beta for another parameter follows.

## Integrity, cost and limits

- Audit 6498144 checked **2,176 receipts and 4,352 result/checkpoint hashes**, configuration/source identities, chains and grid consistency. It established 128 distinct physical GPU UUIDs on 32 hosts.
- This analysis rehashes all 2,176 result grids and receipt files, checks their chains and matches the final classification totals. It does not independently recompute checkpoint tensor semantics.
- Production consumed **62.6667 physical node-hours / 250.6667 GPU-hours**, from the scheduler elapsed time and allocation. The eight-hour launch limit was a ceiling, not the consumption.
- The earlier four-GPU utilization sample was 30–34%; no campaign-average utilization was recorded. Profiling useful trajectories per second and per node-hour remains required before further scale-up.
- This is an author-run deterministic simulation grid, not an independent replication or physical measurement. A new initial-condition ensemble would answer a different robustness question.

Evidence: `hnc-fine-audit-6498144.json`, `hnc-fine-analysis-6500155.json`, and the frozen `hnc-fine-v1` configuration and source.
