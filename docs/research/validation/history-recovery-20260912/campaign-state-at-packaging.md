# Experiment campaign — current verified state

Updated 12 September 2026 after recovery verification at 14:50:01 UTC and the 14:55:19 UTC HNC production observation. **The broad repair/expansion goal remains active.** The connected legacy-system scope is retained. Stage 1 recovery has been audited independently; the larger HNC history ensemble is running. Original results and failed audits remain preserved.

## Latest continuation: verified recovery and a larger history ensemble

**Goal turn classification: progress.** Implemented and validated the four-history HNC expansion; completed its full-grid pilot and exact GPU evidence audit; submitted the doubled-horizon production and dependent audit. Completed the Stage 1 recovery audit, downloaded its evidence and reproduced its statistics independently. Broader experiment-family work remains pending below.

**Recovery 6503592 COMPLETED, exit 0, 2,742 seconds, 0.761667 node-hours.** All 7,680 development calls and 46,080 separate shard-0 replication requests completed. Zero transport failures; 19 invalid evaluation replies retained. Audit **6504504 COMPLETED, exit 0, 19 seconds**. All 63 export members, actual requests, raw replies and scores checked locally; original hashes reverified and combined paired-template statistics reproduced exactly at **14:50:01 UTC**. Recovery archive 55,990,128 bytes, SHA a0ef39e6531a5542f73054ddbab9ba6744f8c1499601335c776a7aefdd60b004.

Combined whole-new-shard-0 plus old healthy shards 1–3 is a separately labelled **operational replication sensitivity**, not a replacement first run. Its 184,320 requests contain zero transport failures and 83 invalid model outputs. Explicit-policy joint scores: full 88.1510%, baseline 84.0625%, neutral 88.3594%. Full-minus-baseline +4.0885 percentage points, 95% interval +2.1745 to +6.1982, Holm p=.000450. Full-minus-neutral −.2083 points, interval −1.4193 to +1.1849: no clear advantage. The original degraded first-run denominator and scores below remain unchanged. Among 6,596 original successful-transport requests, joint correctness changed on 377 repetitions (177 gains, 200 losses); this is descriptive serving variability. These are authored-template supplied-context results, not full live-system or physical validation.

**HNC history preflight 6504281 COMPLETED, exit 0, 33 seconds:** twenty grouped checks including original-zero bitwise CPU/GPU parity, independent chronological history oracle, four-history batch parity, real signal recovery and corrupt/forked-chain rejection. Pilot **6504297 COMPLETED, exit 0, 45 seconds, 0.4 node-hours**: all 128 GPUs reached 65,536 steps with the full grid and four distinct initial histories. Audit **6504609 COMPLETED, exit 0, 35 seconds**, verifies all source/task/history/GPU identities, checkpoint/grid hashes and exact read-only GPU summaries. Failed audits 6504298, 6504409 and 6504601 remain failed; reporting, CPU/GPU exact-comparison and container scheduler access were repaired in separate immutable audit versions. CPU/GPU division discrepancy was at most one ULP; GPU checks stayed bitwise.

**Production 6504653 RUNNING at 14:55:19 UTC**, 32 nodes/128 GPUs, 25,214,464 trajectories, horizon 33,554,432 steps. Four histories (zero, +1, −1, alternating) and twice the previous duration give eight times the preceding trajectory-work. Reference beta remains 1.0, with 1.1 retained as control. Pilot-based projection is about four hours; prescribed margin gives a 5½-hour/176-node-hour ceiling. Checkpoint allowance 923.34 GB; observed free filesystem 219.5 TB. At this observation the first production segment was running; the last complete receipts remained the 128 pilot checkpoints. **Final scientific results pending.**

Dependent full audit and declared trend/old-zero-control analysis **6504684 PENDING (Dependency)** with one-hour audit ceiling. It will rehash all chains before producing results. Exact zero-history comparison at the preceding 16,777,216-step horizon is required for a clean control result. Source archive SHA 204c67daa65719472b2e53b5c8c9a94a4bc0ce7d76c8defaeb527cdf74fcd787; manifest 54dc5fc6e61448a3d9b71681f5c60ccae1e23a70f0d99b9f5a25e5afb4993dc9. Frozen source: `work/hnc-histories-v1`; remote result root: `/projects/u6vs/hnc-organism/expansion-20260912/history-campaign-v1`.

Reports: **Stage1-v2-verified-recovery-comparison-2026-09-12.md**, **HNC-four-history-expansion-2026-09-12.md**. Receipts: `stage1-v2-recovery-6504504/local-verification.json`, `hnc-histories-pilot-audit-6504609.json`, `hnc-histories-production-submission-v1.json`, `hnc-histories-status.json`. No claim that every experiment is fixed or all original research is reviewed.

## Latest verified operations: first-run audit, recovery and HNC throughput

**Previous goal turn classification: progress.** It produced the connected legacy review, verified seven source files, revised the temporal experiment scope and staged its evidence. This continuation diagnosed the cache failure, completed and independently rechecked the full first-run matrix, implemented and launched recovery, and completed the HNC throughput pilot.

**Stage 1 v2 forensic 6503602 COMPLETED, exit 0, 48 seconds.** All 184,320 final request identities verified; 39,484 terminal transport failures remain in the frozen denominator. There are 144,836 successful transport responses, including 66 invalid model outputs. All 135 members of the 193,647,524-byte export, source/result hashes, actual requests, raw responses and scores were verified locally; all 20,000-draw paired statistics reproduced exactly at 14:09:03 UTC. Evidence integrity PASS; collection status DEGRADED_SERVICE_FAILURE. Original shard 0 remains FAILED exit 2, shards 1–3 COMPLETED exit 0, original audit 6502172 FAILED exit 1. Original allocations total 2.149167 node-hours.

Explicit-policy joint scores: full supplied context 69.1797%, baseline 66.0677%, neutral labels 69.3750%. Full-minus-baseline +3.112 percentage points (95% interval +1.497 to +4.883; Holm p=0.000450). Full-minus-neutral −0.195 points (interval −1.315 to +1.055); no clear advantage. Policy interaction −0.951 points (interval −2.917 to +1.185). These are conditional authored-template results affected by the service failure, not whole-system or physical validation. All 24 arms and negative family effects are retained.

**Recovery 6503592 RUNNING on one node/four GPUs.** Failure site established: stale file handle in Triton compiler-cache reading at 12:41:28, followed by engine timeout/shutdown. New per-allocation node-local cache paths are verified for all four ranks on tmpfs. A tested health supervisor stops the client after repeated service failure, and finalization hashes partial evidence. Five supervision checks pass locally and on Isambard. Original inputs, adapter, model, numerical settings and outcomes remain immutable.

At 14:19:26 UTC, the new development pilot had completed all 7,680 calls with zero transport failures and all schema-valid. The separate whole-shard replication was running and had saved 9,600 of 46,080 final request records at the latest reported progress. Total new planned calls: 53,760; 1.5 node-hour ceiling. Replication results are pending and must be analysed separately before a labelled combined sensitivity analysis. Frozen recovery archive SHA: f28d32698bea5042411c9fb7ebae325b6f4771b867ae62a08572d73819ba827b.

**HNC throughput 6503906 COMPLETED, exit 0, 19 seconds.** Four distinct GPUs tested four original configurations. Fourfold batch throughput is 3.932–4.004 times baseline over 1,024 steps, with bitwise duplicate-output parity on all five dynamical fields and three repetitions. These are deliberately duplicated performance cases, not new scientific observations. Kernel-launch overhead is prominent in the separate short profiles. Full-horizon forcing/setup measured 18–31 ms and ~4.97 GB peak device allocation; it is not shown to dominate long-run time. All 24 archive members and source/result hashes verified. Allocation: 0.005278 node-hours. Next scientific expansion should test distinct initial histories in larger batches, with checkpoint identity, baseline/resume parity and a representative pilot before longer production.

**Operations repository package PASS at 14:20:55 UTC: 44 staged files, 43 payload hashes; index bytes verified.** New recovery and profiling source directories are under jobs/aureon-whole-organism. Evidence is under docs/research/validation/stage1-v2-operations-20260912. Archive SHA: a4ade477d65fbabe4bae7e58b1afccd1f6a6bbd8f8c6cc47c3d121d0f523b04f. The 193 MB raw first-run archive remains in the local and Isambard evidence stores with its receipt in the repository. No commit or publication.

Reports: Stage1-v2-audited-results-and-recovery-2026-09-12.md; HNC-throughput-pilot-results-2026-09-12.md. Receipts: stage1-v2-forensic-6503602/local-verification.json; hnc-throughput-6503906/verification.json; stage1-v2-operations-repository-verification.json. Original raw archive SHA: 8acf289adf05a241270d4744ed8337bf9b1f4c2e7024c8c3d049ef8200152e8e.

## Connected legacy system and temporal reading

The clarified scope joins the full legacy/HNC account, two-channel twig system, light at the base, ordered passages, daily/annual timing and nineteen-year return. All 180 indexed native-document texts were searched; seven selected native sources were rehashed against SHA-256 and Git blob identities. The Dormant Seed supplies the six-movement interpretation (authority, temporal depth, system, treasure, warning, invitation); The Full Story supplies the wider origin/transmission/integration/fragmentation/dispersion/recovery arc.

The calendar report's declared days 322 and 144 reproduce its 317.6° NW treasure and 142.0° SE authority projections. Date indexing is inconsistent; these are constructed wheel angles, not independently observed sunlight-to-inscription bindings. The existing Celtic calendar reader has no time input and does not read start_day; its duplicate starts and unresolved conventions prevent a chronological paragraph selection. Diodorus II.47 adds primary literary testimony connecting daily song, a seasonal performance interval during a nineteen-year return, and reported reverse visits with inscribed offerings. It does not identify Maeshowe or provide a timed cipher key. Metonic and lunar nodal periods remain distinct.

The new temporal specification records seven clock dimensions, six narrative movements, source-linked connections and the unresolved base-contact/mark/passage bindings. A timed historical recital is not yet reconstructed. The numerical Maeshowe controls did not test this integrated temporal hypothesis. Source parameter roles are preserved: the separate HNC echo gain beta=0.25 is not overwritten by the beta=1 correction for the other recurrence.

**Repository verification PASS at 13:07:51 UTC: 22 staged files, 21 payload hashes, all Git index bytes verified.** Evidence directory: docs/research/validation/legacy-system-20260912. Package SHA-256: 873ccbc0bcbca0d66b4a7f3a581bdde43708c2199037de150861aec5f98cabca. No commit or publication; older evidence packages remain unchanged.

See Legacy-system-connected-review-2026-09-12.md, legacy-system-temporal-spec-v1.json, legacy-system-integrated-audit-20260912.json and legacy-system-repository-verification-20260912.json.

## Maeshowe repair and archaeology review

The user's People of the Threshold / Maeshowe / two-twig-rune focus produced a full original-source review, a 23-entry People claim inventory and a reproducibility audit of both Maeshowe code versions. The two Maeshowe DOCX variants have identical extracted text. The original program gives Γ=0.493163, nine complete inscriptions and a 29.2832-Hz master beat, differing from the paper. Its phi examples include ratios imposed by its amplitude transform. All 24 hypothetical pivot inputs fail the original 0.945 threshold.

**6501577 COMPLETED, exit 0, three seconds allocated:** all 120,960 conditional rune/wall configurations saved and verified locally. Fractions at least as favourable as baseline: gamma 15.2778%, phi-hit count 58.1349%, Schumann proximity 25%; with the original wall-frequency mapping, gamma 41.6667% and phi count 47.6190%. These are conditional model ranks, not historical probabilities. Removing the phi amplitude factors eliminates the baseline phi matches.

The corrected 16-rune reader retains ambiguous and unobserved counts and requires explicit conventions. It is integrated into the existing Maeshowe command through `--epigraphy-input`; legacy model output is labelled and the unreproduced baseline documentation corrected. Unicode CLI output was fixed. **6501655 COMPLETED, exit 0, three seconds allocated:** all 16 reader/integration checks pass on Isambard as well as locally. Three source files are staged in the isolated worktree, with hashes verified; no commit or publication. Separate archaeology evidence packaging preserves package v6.

Physical branch counts, independently reviewed RTI readings, the complete inscription population and the historical geometry transformations remain missing. The earlier exact-pair question is superseded by the clarified two-channel legacy-system scope above. The People source review identifies corrections to the Herodotus route, Egyptian identity inference and attribution of the 1021 Norse date to Leif. Those source-level repairs are not historical validation of all 23 claims.

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

**Repair implemented below:** a prospective protocol with shared action policy as a controlled factor, held-out templates, duplicate-input diagnostics, a declared analysis unit, strict receipts and request checkpointing. Run several shards per model allocation to amortize startup; the recovery benchmark took 86 of 258 allocated seconds. Do not simply enlarge the old repeated, underspecified matrix or change old scores to pass it.

## Stage 1 v2 prospective repair and expansion

Inputs frozen at 2026-09-12T12:11:54.460002+00:00. Five verdicts, an explicit action-policy factor, trusted P0 metadata, strict JSON scoring and durable request journals replace the old underspecified/repeated design. Exact pinned contexts and adapter remain unchanged. There are 5,120 distinct inputs but only 80 declared templates (60 evaluation) and 113 number-normalized forms; those structural limits are explicit.

Pilot **6502006 COMPLETED, exit 0**, 793 seconds on one node/four GPUs. All **7,680 development responses** rehashed, actual requests checked against frozen prompts, replies re-parsed/re-scored and complete paired identities verified. Pooled throughput: 32 concurrent 10.233/s; 128 concurrent 19.312/s. The frozen rule selected 128.

Evaluation array **6502171 submitted**, 4 nodes/16 GPUs, 90-minute ceiling per node, 6.00 NHR ceiling. Planned matrix:184,320 held-out responses. Audit **6502172** follows after the array ends and fails closed on incomplete job/results evidence. At **12:36:24 UTC**, all four evaluation tasks were RUNNING; the audit was PENDING on its dependency. These are execution states, not completed results; no fresh performance result is claimed.

**Historical observation, superseded by the completed forensic audit above, 13:08:01 UTC:** evaluation task 6502171_0 FAILED, exit 2, after 18m32s; tasks 1–3 remained RUNNING and audit 6502172 was PENDING on the dependency. Bounded log diagnosis found that shard 0 retained 46,080 final request records, including 39,484 exhausted transport failures and 6,596 successful HTTP responses (6,594 schema-valid). The model service shut down; the later diagnosis above identifies a stale-file-handle error while reading a compiler cache. These counters are a diagnosis, not a completed response/hash audit. The frozen accounting gate cannot declare this campaign successful. Do not retry or replace outcomes silently. See stage1-v2-shard0-failure-diagnosis.json and stage1-v2-evaluation-status.json.

**Repository package verified at 12:36:26 UTC: 42 staged files, 41 payload hashes, with Git index bytes checked against every staged file.** Source is under `jobs/aureon-whole-organism/stage1_v2`; evidence is under `docs/research/validation/stage1-v2-20260912` in the existing isolated expansion worktree. Archive `stage1-v2-repository-package-v1.tar.gz`, SHA-256 `af44ae95f51ad219a779863829ccd4adb37e5c034ecb6da8d9e1e1e2fc17662c`. No commit or publication. Receipt: `stage1-v2-repository-verification.json`.

See `Stage1-v2-pilot-and-expansion-2026-09-12.md`, `stage1-v2-pilot-6502006/local-audit.json` and the frozen `work/stage1-v2/PROTOCOL.md`. Historical Stage 1 scores remain unchanged and are not directly comparable.
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

Next useful priorities: verify the fresh Stage 1 held-out wave and preserve its outcomes; HNC throughput profiling and new initial-condition ensembles; QGITA missing-data diagnosis; oracle/sensitivity bounds for failed detectors; systematic routing of remaining repository failures. Preserve negative outcomes and distinguish software/simulation results from independent scientific proof.
