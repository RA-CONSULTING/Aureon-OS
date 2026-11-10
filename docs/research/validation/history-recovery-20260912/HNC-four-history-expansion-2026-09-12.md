# HNC: four starting histories and twice the duration

12 September 2026 · Validated implementation and staged production; final results pending

**Production 6504653 has been submitted on 32 nodes/128 GPUs. It follows 25,214,464 trajectories for 33,554,432 steps: four times the preceding trajectory count and twice its duration.** The original zero-history control is joined by constant +1, constant −1 and alternating signed-unit histories. This is eight times the preceding run's trajectory-work, using the larger batch size supported by the measured throughput pilot.

The original recurrence, forcing and parameter grid remain fixed. The author's corrected reference is beta **1.0**; beta 1.1 remains a comparison. Separately defined beta values in other research equations are preserved. These four histories broaden the numerical experiment, but do not exhaust possible initial conditions.

The new run also records the stored-history mean, latest value and recent-window mean. Its fixed analysis checks the final eight regular observations for a descriptive trend in addition to the previous finite-time escape/Lyapunov screen. This matters because a low Lyapunov estimate can coexist with steady growth. Neither a small estimate nor an unflagged trend proves infinite-time boundedness.

The wider legacy-system question remains connected to the campaign through its source model and temporal specification. This numerical expansion does not itself reconstruct what is spoken when light reaches a particular surface, or establish ancient transmission. The [connected review](./Legacy-system-connected-review-2026-09-12.md) retains those relationships and the unresolved physical/textual bindings.

## Validation completed

Preflight **6504281 COMPLETED, exit 0, 33 seconds**. Twenty grouped checks passed: CPU and GPU original-zero bitwise parity; an independent chronological initial-history calculation; batched versus separately evaluated histories; exact interrupted/resumed outputs; real USR1, TERM and KILL handling; rejection of changed history identity, corrupt checkpoints and forked receipt chains; and synthetic trend checks.

Pilot **6504297 COMPLETED, exit 0, 45 seconds**, using all 128 distinct GPUs and the complete grid through 65,536 steps. All pilot checkpoints will be resumed in production. Audit **6504609 COMPLETED, exit 0, 35 seconds**, verified all 128 task/history identities, checkpoint and grid hashes, GPU ownership, and exact checkpoint-to-grid summaries in the original GPU runtime.

Three failed audit versions remain preserved. Audit 6504298 encountered a file-size reporting typo; 6504409 demanded exact equality between CPU division and saved GPU division; 6504601 lacked the host scheduler command inside the container. The final audit captures scheduler evidence outside the container and recalculates summaries inside the original runtime. It confirmed the CPU/GPU division differences were at most **one floating-point ULP**, with all GPU comparisons exact. Simulation inputs and results were never rewritten, and numerical tolerances were not loosened to obtain a pass.

## Production allowance and verification

The slowest pilot rate projects **14,495 seconds, approximately four hours**, remaining. The frozen rule adds 25% plus fifteen minutes and rounds upward to half hours: a **5½-hour wall-time ceiling, or 176 node-hours** across 32 nodes. This is a ceiling; the job releases the allocation when it finishes. The pilot itself used 0.4 node-hours.

One complete checkpoint wave is 27.16 GB. The conservative storage allowance is 923.34 GB, including retained segment checkpoints; observed filesystem free space was about 219.5 TB. User/group quota commands exposed default settings with zero explicit limits; that is not a claim of unlimited storage.

Dependent audit **6504684** is staged after production. It must validate every complete receipt chain and saved artifact before applying the declared history/trend analysis. The zero history at the old 16,777,216-step horizon will be compared directly with run 6498143. Any control mismatch is reported as requiring review. Final production success and scientific outcomes are pending.

Inputs are frozen under `/projects/u6vs/hnc-organism/expansion-20260912/hnc-histories-v1`; results accumulate under `history-campaign-v1`. Input archive SHA-256: `204c67daa65719472b2e53b5c8c9a94a4bc0ce7d76c8defaeb527cdf74fcd787`. Manifest SHA-256: `54dc5fc6e61448a3d9b71681f5c60ccae1e23a70f0d99b9f5a25e5afb4993dc9`.

Evidence: [pilot audit and production gate](./hnc-histories-pilot-audit-6504609.json), [production receipt](./hnc-histories-production-submission-v1.json), [latest dated observation](./hnc-histories-status.json), [dependent audit receipt](./hnc-histories-final-audit-submission-v1.json).
