# HNC four-history expansion v1

This prospective computational simulation expands fine-grid run 6498143. It keeps the same recurrence, forcing, 121 alpha values, 407 beta values and 128 gain/delay/window combinations. The author's corrected reference beta is 1.0; beta 1.1 remains a comparison value. No other beta role in the manuscripts is changed.

## Question and fixed design

Compare zero, constant +1, constant -1 and alternating signed-unit histories over 33,554,432 steps. The alternating history is +1 at even integer times and -1 at odd integer times, including -1 at t=-1. Stored initial columns correspond to times -max(tau,delta)-1 through -1. Each trajectory receives the same original forcing. Initial recent-window sums are derived from that history. The original zero-history case is an implementation control; no claim that four histories span all possible initial conditions is made.

The 25,214,464 trajectories represent four times the previous trajectory count and twice its duration: eight times its trajectory-work. The fourfold performance pilot used duplicates only; this ensemble uses distinct histories. The original source is retained byte-for-byte with SHA-256 1eac7d95222b480e3e54d02c0e92d939a2b6ac39d5b2e33c1d196f0dec96014c. Recurrence and perturbation-renormalization arithmetic remain unchanged. New endpoint measurements are read-only.

## Outputs and interpretation

Keep the original finite-time screen: unescaped, valid Lyapunov blocks, estimate at most 0.0001 per step. Escape means crossing 1e12 or nonfinite base output; subsequent values remain clamped according to the original method. Report escape, invalid-block and screen counts separately for every history and reference beta, and retain the full grids. An unescaped low-Lyapunov trajectory is not necessarily bounded for all time: linear drift may meet this finite-time screen.

Record mean stored history, last value and recent-window mean at each segment. At the final horizon, analyse mean stored history at the last eight regular segment endpoints (the final quarter). Fit ordinary least-squares mean against step. For an unescaped trajectory with eight finite, increasing-time observations, flag a descriptive secular trend only if absolute slope exceeds 1e-8 per step and fitted change exceeds both 1 unit and ten times residual RMS. These arbitrary but fixed descriptive thresholds do not establish asymptotic growth, and failure to flag does not establish boundedness. Show signed slopes and endpoint trends independently of the original screen. Include zero-history comparisons at the previous horizon and initial-history disagreement maps.

The full ordered legacy-system reading is a different, connected research target. This recurrence experiment does not supply the missing light-to-inscription-to-passage binding or validate an ancient transmission history. Those relationships remain in the connected temporal specification.

## Validation and staged allocation

Before the pilot, require bitwise original-zero parity on CPU and CUDA; independent chronological/direct-sum initial-history checks; batched versus separate history parity; bitwise interruption/resume equivalence; real USR1, TERM and KILL recovery; rejection of changed history identity, corrupt artifacts and forked chains; descriptive trend checks. Record source hashes, runtime and job identities.

The next stage is a 65,536-step pilot across all 128 cells on 32 nodes/128 GPUs with a 15-minute ceiling. It retains checkpoints in the same campaign chain for production. Require all 128 receipts, correct task/history/grid identities, unique GPU ownership, checkpoint and grid hashes, and terminal job success. Check project storage before continuing.

Estimate remaining production wall time from the slowest pilot trajectory rate, allowing 25 percent margin plus fifteen minutes, rounded up to half hours and capped at eight hours. If it exceeds eight hours, stop automatic expansion and reassess segmentation. Production uses the same 32 nodes and resumes the pilot with a fixed 33,554,432-step horizon. Time limits are ceilings, not target expenditure. Before submission, freeze the chosen wall-time decision and evidence. Each 1,048,576-step segment preserves a chained immutable receipt and checkpoint; interruption adds a new attempt without replacing completed evidence. No outcome-based pruning or stopping is allowed.

Audit all final chains and grid/checkpoint hashes before analysing results. Preserve failed and abandoned attempts. Scientific results, operational performance, authored theory and independent observations remain distinguishable throughout the campaign.
