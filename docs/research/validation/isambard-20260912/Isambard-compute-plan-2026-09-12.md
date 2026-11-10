# Isambard allocation and expansion plan

The authenticated project dashboard shows **4,913.09 NHR as its estimated end-of-month balance**, with **79.44 NHR estimated September spend** against **4,992.53 NHR at the start of September**. The refreshed all-time Usage Report shows **86.9 hours**, rounded to one decimal. Access ends **22 November 2026**. These labels are preserved: the dashboard did not expose a separate exact real-time spendable-credit figure.

The local scheduler extract contains 500 allocation records, excludes job steps, and estimates 79.3511 NHR for September using the provider's resource-fraction rule. It predates some work and differs from the dashboard by about 0.09 NHR. Subtracting the estimated 67.8769 NHR of subsequent visible work from the September 8 email balance of 4,980.98 NHR gives 4,913.1031 NHR. This supports the current scale of the balance without asserting an exact reconciliation of different reporting cutoffs.

The completed HNC production run alone consumed **62.6667 node-hours / 250.6667 GPU-hours**, from 32 nodes over 1h57m30s. Its eight-hour launch limit was a reservation ceiling of 256 node-hours, not its cost. Slurm's `billing` field alone would undercount this job relative to the allocated GPUs; the provider accounts by the largest allocated CPU, GPU or memory fraction. On Isambard-AI, one node contains four GPUs. [Provider accounting guide](https://docs.isambard.ac.uk/user-documentation/guides/accounting/)

## Pace and dates

There are 64 days from September 12 to November 15. Using an estimated 4,913 NHR by then would average about **76.8 NHR per day**, or **3.2 whole nodes running continuously**. A 32-node batch lasting roughly 2.4 hours consumes that daily amount. These are planning equivalents, not instructions to keep idle GPUs allocated.

Aim to finish major compute by **November 15**, finish verification and the main export by **November 18**, and keep November 19–21 for recovery and final checks before November 22 access ends. Start exporting completed, verified result packages now. The provider advises spreading use through the project and copying data off before expiry. [Provider accounting guide](https://docs.isambard.ac.uk/user-documentation/guides/accounting/)

## Conditional planning envelopes

These are ceilings for preparing useful experiments, not submitted jobs or mandatory spending targets. Reallocate after each pilot according to measured cost and information gained. Outstanding balance and reservations must be refreshed before each large wave.

| Workstream | Initial ceiling (NHR) | Next question or prerequisite |
|---|---:|---|
| HNC numerical dynamics | 1,300 | Profile throughput first; then test new initial-condition ensembles, precision sensitivity and longer horizons near the moving transition. Preserve the beta=1 correction as a reference, not a universal theorem. |
| QGITA | 900 | Fix and test missing-data handling; compare frozen baselines on held-out datasets and alternate endpoint definitions. CPU-heavy preprocessing should use proportionate resources. |
| Model-mediated Aureon: Stage 1 and capability arena | 800 | Finish shard recovery and strict retrospective audit. Repair execution/schema errors, then freeze new scenarios and seeds for a prospective comparison. Preserve old malformed responses and negative outcomes. |
| Tandem, LiDAR and AURIS | 1,000 | Establish oracle/sensitivity bounds and identify failure mechanisms before larger detector or integration runs. Use separate development and held-out evaluation data. |
| Acoustics, illumination and coincidence simulations | 200 | Test specified geometry/boundary uncertainties, independent random seeds and defined search corrections. No synthetic result substitutes for missing physical observations. |
| Repository, daemon and governance integration | 300 | Route all remaining failures to bounded reproducible checks; fix runtime dependencies and provenance/replay problems before wider execution. |
| Verification, export and recovery reserve | 413.09 | Retain headroom for audits, failed-job diagnosis and verified exports. Release surplus only to a defined useful experiment before the cutoff. |
| **Total planning allocation** | **4,913.09** | Based on the current dashboard estimate; refresh before scheduling. |

## Immediate wave

- HNC fine-grid production 6498143 and artifact audit 6498144 are complete. Analysis 6500155 completed in 22 seconds; its downloaded-file hash matches the remote result.
- Acoustics consolidated amended assessment is complete: ordinary closed-room resonances are supported; distinctiveness and corrected Schumann gates fail. The original frozen verdict stays inconclusive.
- Stage 1 recovery 6500368 targets only missing shard 99, with one node/four GPUs and a 15-minute ceiling: at most 0.25 NHR. It lowers the model server's memory reservation from 90% to 85%, preserving the original prompts, scoring and decoding.
- The retrospective audit has passed ten local checks, including rejection of changed scores, missing/duplicate pairs, wrong model/source identity and malformed receipt data. Audit 6500947 completed in 12 seconds and verified the entire 122,880-response matrix. The retrospective comparison is negative: full verdict accuracy 65.98% versus 67.70% baseline. Diagnosis and a new prospective protocol now precede further expansion in this lane.

The operational objective is to complete useful, auditable work across the families. Negative research findings call for better questions or bounds; changing acceptance thresholds to obtain a pass is not a repair. Missing observational data, provider restrictions and unfinished audits remain explicit holds on the affected work.

Evidence: `isambard-portal-observation-20260912.json`, `isambard-accounting-20260912.psv`, `isambard-accounting-reconciliation.json`, and the individual experiment audit receipts.

## Stage 1 diagnosis completed after the initial wave

Job 6501165 separated action-format failures from valid but wrong choices and exported the verified response corpus. All 769 archive members were checked locally. The frozen generator produces only 514 distinct user prompts across 5,120 records; action semantics are underspecified. The next Stage 1 experiment must add a shared explicit decision policy, semantically diverse held-out fixtures and an appropriate independent unit of analysis. Running several shards per server allocation can also amortize the roughly two-thirds setup/teardown share observed in the recovery. These repairs precede any broad use of the Stage 1 planning envelope.
