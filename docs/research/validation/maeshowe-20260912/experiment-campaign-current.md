# Experiment campaign — current verified state

Updated 12 September 2026 after Maeshowe controls 6501577 and repository checks 6501655. **The broad repair/expansion goal remains active.** The earlier phase completed final HNC analysis, consolidated amended acoustics, Stage 1 recovery/retrospective analysis, benchmark diagnosis and a verified response export. The prospective Stage 1 v2 experiment has not run.

## Maeshowe repair and archaeology review

The user's People of the Threshold / Maeshowe / two-twig-rune focus produced a full original-source review, a 23-entry People claim inventory and a reproducibility audit of both Maeshowe code versions. The two Maeshowe DOCX variants have identical extracted text. The original program gives Γ=0.493163, nine complete inscriptions and a 29.2832-Hz master beat, differing from the paper. Its phi examples include ratios imposed by its amplitude transform. All 24 hypothetical pivot inputs fail the original 0.945 threshold.

**6501577 COMPLETED, exit 0, three seconds allocated:** all 120,960 conditional rune/wall configurations saved and verified locally. Fractions at least as favourable as baseline: gamma 15.2778%, phi-hit count 58.1349%, Schumann proximity 25%; with the original wall-frequency mapping, gamma 41.6667% and phi count 47.6190%. These are conditional model ranks, not historical probabilities. Removing the phi amplitude factors eliminates the baseline phi matches.

The corrected 16-rune reader retains ambiguous and unobserved counts and requires explicit conventions. It is integrated into the existing Maeshowe command through `--epigraphy-input`; legacy model output is labelled and the unreproduced baseline documentation corrected. Unicode CLI output was fixed. **6501655 COMPLETED, exit 0, three seconds allocated:** all 16 reader/integration checks pass on Isambard as well as locally. Three source files are staged in the isolated worktree, with hashes verified; no commit or publication. Separate archaeology evidence packaging preserves package v6.

Physical branch counts, the exact pair meant by “two twig runes,” independently reviewed RTI readings, the complete inscription population and the historical geometry transformations remain missing. The People source review identifies corrections to the Herodotus route, Egyptian identity inference and attribution of the 1021 Norse date to Leif. Those source-level repairs are not historical validation of all 23 claims.

See `Maeshowe-repaired-experiment-results-2026-09-12.md`, `Threshold-Maeshowe-twig-runes-review-2026-09-12.md`, `maeshowe-controls-6501577/local-verification.json` and `maeshowe-repository-checks-6501655/verification.json`. Larger compute remains directed toward prospective Stage 1 repair, HNC throughput/initial-condition work and the other unresolved experiment families below.

## HNC complete

Production **6498143** completed 1h57m30s on 32 nodes/128 GPUs. All 128 cells reached 16,777,216 steps, covering 6,303,616 trajectories. Audit **6498144 PASS** checked 2,176 receipts and 4,352 result/checkpoint hashes, identities, chains and GPU ownership. Analysis **6500155 completed in 22 seconds**, rehashed result grids/receipt chains and matched final totals. Its downloaded SHA matches remote: `1f00556f009df26cafbeab1c67b053b19ccc627e3007f48d1aba7d6b656b691d`.

All 15,488 beta=1 cases meet the finite-time stable rule; no beta=1.1 control does. Across the entire grid: 4,541,472 escaped, 1,658,294 stable, 90,557 bounded with Lyapunov estimate above threshold, and 13,293 bounded without valid Lyapunov blocks. Median first downward 50% crossing moved from 1.000423625 at 1,048,576 steps to 1.000015067 at the final horizon. Final range is 1.000002542–1.000077614; the last segment adds 13,284 escapes. This is not an exact universal boundary or infinite-time proof.

Production used **62.6667 node-hours / 250.6667 GPU-hours**. Earlier limited GPU utilization sampling was 30–34%; profile useful throughput before expansion. Source and result roots remain `/projects/u6vs/hnc-organism/expansion-20260912/hnc-fine-v1` and `fine-campaign-v1`. Prior four-million-step campaign 6497438 and audit 6497683 remain preserved. See `HNC-fine-grid-results-2026-09-12.md`.

## Acoustics complete under amendment

All eight explicit consolidated numerical checks pass under the post-hoc amendment, supporting **SUBSTANTIATED-GENERIC** closed-room resonances. Primary 16.379981/32.759045 Hz pass 2% and octave gates but fail 1%. Distinctiveness fails: 6.28% of controls hit both 2% targets. Corrected Schumann comparison: 6,402/10,000 controls at least as close, plus-one rank 0.640236. The opening's nearest lower mode is 16.674212 Hz and its selected pair fails target/octave gates.

Historical frozen verdict remains INCONCLUSIVE. Eigenvectors were not retained for independent residual recomputation; dimension detuning is not coffer-position uncertainty. Jobs 6497961, 6497982 and all four geometry tasks in 6498032 completed. See `Acoustics-amended-assessment-2026-09-12.md` and `acoustics-amended-gates-20260912.json`.

## Stage 1 recovered, audited and diagnosed

Original array 6347216 lacked shard 99 after a vLLM startup-memory failure; report 6347217 was cancelled. Isolated recovery **6500368_99** reduced memory reservation from 90% to 85%, preserving source/model/fixtures/scoring/decoding. It saved 960 responses in 4m18s on one node/four GPUs. Five invalid JSON replies caused the unchanged frozen benchmark to exit 1; its scheduler state remains FAILED, with output hashes and the exit code retained.

Retrospective audit **6500947 completed in 12 seconds, PASS** across all **122,880 responses**. It regenerated fixtures, reparsed/rescored every response, checked complete paired identities and source/runtime/receipt hashes, and retained **280 invalid JSON replies as zero-score failures**. This does not retroactively pass the frozen protocol.

Full versus baseline: composite **0.630701 vs 0.645993**; verdict accuracy **65.98% vs 67.70%**; action accuracy **18.79% vs 22.11%**. Both inherited exploratory shard-bootstrap intervals lie below zero under the old scoring rules.

**Critical design limits:** diagnosis **6501165 completed in 8 seconds**. Most action failures use valid but target-mismatching action words. Full chose `report` 9,028 times and never `request_more`; baseline chose `report` 7,582 times and `request_more` once. The system prompt lists actions without fully defining the scorer's policy; restrictions in untrusted source text need an explicit trusted-policy distinction.

Frozen-fixture regeneration found only **514 distinct user prompts among 5,120 fixture records**. Four families repeat one prompt 512 times before two request repetitions. Distinct IDs are not independent tasks; the historical intervals are not generalization intervals for thousands of independent research tasks.

The local 7.5 MB archive `stage1-diagnostics-6501165/stage1-verified-responses.tar.gz` has **769 member hashes verified** against the audit. SHA-256: `2f18e2f57f11a41d91aef58fb6a07aed4a87bff9f85c3ad9c9b003baa41d97fa`. Reports: `Stage1-retrospective-results-2026-09-12.md` and `Stage1-error-diagnosis-2026-09-12.md`.

**Next concrete repair:** new prospective protocol with explicit shared action policy as a controlled factor, semantically varied held-out fixtures, duplicate-input checks, a meaningful independent analysis unit, strict receipts and request checkpointing. Run several shards per model allocation to amortize startup; the recovery benchmark took 86 of 258 allocated seconds. Do not simply enlarge the old repeated, underspecified matrix or change old scores to pass it.

## Access and allocation

Terminal access and browser SSO are verified. New SSH connections intermittently time out before authentication; check exact job IDs before retrying uncertain submissions. Browser usage tab 793494587 is authenticated and marked to remain open.

Portal labels: **4,992.53 NHR start-of-September balance**, **79.44 NHR estimated September spend**, **4,913.09 NHR estimated monthly closing balance**, **86.9 hours rounded refreshed all-time usage**. A separate exact real-time spendable balance was not exposed. The 500-record scheduler snapshot estimates 79.3511 NHR in September and 67.8769 after the September 8 email anchor of 4,980.98; later jobs add small costs. Do not use Slurm's billing field alone to estimate allocated GPU usage.

Expiry: **22 November 2026**. Conditional plan: major compute by November 15, verification/export by November 18. Approximately 4,913 NHR averages 76.8 NHR/day through November 15. These are conditional planning ceilings, not submitted jobs or a reason to allocate idle hardware. No located provider email established a technical minimum-node requirement. See `Isambard-compute-plan-2026-09-12.md` and the portal/accounting observations.

## Repository and original papers

**Package v6 verified locally and remotely: 104 staged files, 103 payload hashes.** Archive `experiment-repair-repository-package-v6.tar.gz`, SHA-256 `d4b0ab253662ddba1a759bc1fdf972f8df46be536f0a14a97cf26b613a6bce45`. Receipt: `completed-results-package-v6-verification.json`. No commit/publication occurred. Worktree: `/projects/u6vs/hnc-organism/worktrees/aureon-expansion-20260912`, under `docs/research/validation/isambard-20260912`. Older packages and the pre-existing remediation worktree are preserved.

Experiment documentary pin remains `f5fb1916c07ac26eb7fc38c34ff2dc9bd029e21d`; last refreshed GitHub main was `d6cc2e5ef82fca17f194e314889daa366f24d817`. No new-main performance is inferred from the old pin.

Original-source coverage: 3,431 Git commits, 36,396 file-content versions, 180 native documents; 75 Academia papers plus two talks; source sections of 29 Substack essays; ResearchGate-linked checksum-verified Zenodo Master Equations PDF. Its November 5, 2025 record includes mixed beta wording. July 2025 compilation metadata does not authenticate every passage. The author's beta=1 correction remains separate from unresolved reprint chronology. Some Academia downloads were blocked by browser security; do not bypass those routes. Full file-level review of every public upload remains incomplete.

## Remaining goal scope

QGITA's supplemental decision/structure audit passed while preserving byte-identity failure and poor missingness results. Continue QGITA, Tandem, LiDAR, AURIS, capability arena, illumination, Doorbell/C6/C9, HNC V3, Gamma/conscience/weights/MCP, Math Angel/L(t), observational/Schumann/EPAS and repository/module/daemon repairs. Missing observations are evidence requirements, not successful experiments.

Next useful priorities: prospective Stage 1 contract/data repair; HNC throughput profiling and new initial-condition ensembles; QGITA missing-data diagnosis; oracle/sensitivity bounds for failed detectors; systematic routing of remaining repository failures. Preserve negative outcomes and distinguish software/simulation results from independent scientific proof.
