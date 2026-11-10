# Stage 1 v2: audited first-run results and operational recovery

12 September 2026 · Original array 6502171 · Forensic audit 6503602 · Recovery 6503592

The full supplied context scored **69.18%**, compared with **66.07%** for the baseline, when both received the explicit decision policy. Neutral labels scored **69.38%**; the experiment does not show a clear full-context advantage over that condition. The original collection suffered a model-service failure, so these are the frozen first-run results with all failed requests retained. The collection's operational status is **degraded**.

The service failure is diagnosed, a repair has passed its local and Isambard supervision tests, and a separate replication is running. Its outcome is not yet available. The original record remains unchanged.

## What this experiment asks

The experiment asks whether the repository's pinned prompt context improves a local model's evidence decisions on synthetic cases, and how providing an explicit action policy changes the comparison. Each case has a required verdict and action; the main score requires both to be correct in strict JSON.

There are 60 evaluation templates across ten authored families, 3,840 parameterised cases, twelve contexts, two policy arms and two serving repetitions: 184,320 planned request records. Every case is paired across conditions. The full-context label denotes a supplied prompt context. This run does not execute or validate every live Aureon component, physical HNC behaviour, consciousness or the integrated ancient-calendar reading. Repetitions and parameter substitutions are not independent reasoning skills.

## Complete first-run evidence

- **184,320** final request records, all planned identities accounted for.
- **39,484** terminal transport failures, retained as failures in the frozen denominator.
- **144,836** successful transport responses, including **66** invalid model outputs; **144,770** passed the strict output schema.
- Original shard 0: FAILED, exit 2. Shards 1–3: COMPLETED, exit 0. Scheduled audit 6502172: FAILED on its scheduler gate.
- Forensic audit 6503602: COMPLETED, exit 0, in 48 seconds. It verifies evidence integrity while preserving the degraded operational state.
- The downloaded archive is **193,647,524 bytes**. All **135 members**, recorded source/result hashes, actual request bodies, raw replies and re-scored outcomes were checked locally. The 20,000-draw paired template analysis reproduced exactly. Local verification completed at 2026-09-12T14:09:03.365326+00:00.

The original four evaluation allocations used **2.149167 node-hours**. This excludes separate pilot, audit and recovery allocations.

## All 24 conditions

Scores below use every planned request, including transport failures and invalid answers. The vocabulary-only arm deliberately omits the scorer's action mapping and is an underspecified-policy control.

| Context | Explicit policy | Vocabulary-only control |
|---|---:|---:|
| Full supplied context | 69.18% | 42.28% |
| Baseline | 66.07% | 38.22% |
| Neutral labels | 69.38% | 42.88% |
| Identity prompt only | 66.81% | 38.50% |
| Memory reminder removed | 70.34% | 42.42% |
| Metacognition wording removed | 69.71% | 43.19% |
| Affect/heart wording removed | 69.13% | 39.40% |
| Conscience wording removed | 69.23% | 43.97% |
| Field-disconnected context | 69.02% | 40.60% |
| AURIS shuffled-label context | 69.34% | 43.19% |
| AURIS context removed | 68.66% | 40.95% |
| Queen context removed | 69.04% | 42.23% |

The explicit policy raises scores in every listed context. That descriptive observation does not establish a full-system architectural effect. Some removed-context variants score above the full context; they are reported rather than hidden, and were not predeclared as confirmatory winners.

## Predeclared paired comparisons

| Planned comparison | Difference in percentage points | Paired 95% interval | Holm-adjusted p |
|---|---:|---:|---:|
| Full − baseline, explicit policy | +3.112 | +1.497 to +4.883 | 0.000450 |
| Full − neutral labels, explicit policy | -0.195 | -1.315 to +1.055 | 0.759212 |
| Change in the full−baseline gap between policies | -0.951 | -2.917 to +1.185 | 0.721664 |

The full-versus-baseline comparison is positive in this first-run analysis; the full-versus-neutral comparison and the policy interaction do not exclude zero. The intervals use the frozen family-stratified template bootstrap, with Holm adjustment across the three planned comparisons. Related authored templates and the operational failure limit generalisation. These are conditional summaries of this benchmark, not independent scientific proof.

| Authored task family | Full − baseline, explicit policy (points) |
|---|---:|
| supported | +1.172 |
| conflict | +0.521 |
| insufficient | -2.995 |
| injection | -2.083 |
| restricted | +7.552 |
| causality | +0.521 |
| stale provenance | +2.604 |
| consent boundary | +13.411 |
| care under cost | +1.823 |
| memory continuity | +8.594 |

The positive overall average includes negative effects in some families. Earlier Stage 1 v1 scores are not directly comparable because v2 changed fixtures, action definitions and scoring prospectively.

## Failure, repair and recovery

At 12:41:28 UTC, a worker in shard 0 raised `OSError: [Errno 116] Stale file handle` while reading a Triton compiler-cache group. The model engine stalled, timed out and shut down. The client kept issuing requests and exhausted the three transport attempts for the affected records. This identifies the failure site; it does not establish the storage service's underlying cause.

The recovery allocation uses a new compiler-cache tree under node-local storage. Installed vLLM 0.15.1 source was checked to confirm how it derives per-rank cache paths and redirects the dependent caches. Actual runtime receipts confirm **all four rank directories** are beneath the new **tmpfs** tree. Experiment journals remain on project storage. [Isambard storage documentation](https://docs.isambard.ac.uk/user-documentation/information/system-storage/)

A supervisor checks the model's local health endpoint every five seconds. Three failed checks stop the benchmark while retaining its durable journals. Five tests cover healthy completion, preservation of a nonzero client exit, stopping an unhealthy service's workload while retaining partial evidence, refusing to start against an unhealthy service, and refusing to overwrite an earlier receipt. Batch finalisation saves the exit code and available evidence hashes after failure as well as success.

Recovery **6503592** uses one node/four GPUs with a 90-minute ceiling. It first runs the unchanged 7,680-call development pilot. Only operational reliability controls continuation. If that gate passes, it repeats the entire 46,080-request failed shard using the original model, request generation, numerical settings and order seed. It does not select requests based on their answers. Total planned new calls: **53,760**; allocation ceiling: **1.5 node-hours**.

The first-run results above remain primary under their original protocol. A successful recovery will support a separately labelled operational replication sensitivity analysis using the repeated whole shard 0 and the original healthy shards 1–3. The two collections will not be silently merged into a claimed clean first run. Agreement on the originally successful shard-0 requests will be reported as a serving-variability check.

## Evidence links

- [Local verification](</C:/Users/samle/Documents/Codex/2026-09-05/k/outputs/stage1-v2-forensic-6503602/local-verification.json>)
- [Complete analysis and source hashes](</C:/Users/samle/Documents/Codex/2026-09-05/k/outputs/stage1-v2-forensic-6503602/analysis/analysis.json>)
- [Downloaded original evidence](</C:/Users/samle/Documents/Codex/2026-09-05/k/outputs/stage1-v2-forensic-6503602/evidence.tar.gz>)
- [Frozen operational amendment](</C:/Users/samle/Documents/Codex/2026-09-05/k/work/stage1-v2-recovery-v1/AMENDMENT.md>)
- [Latest recorded recovery status](</C:/Users/samle/Documents/Codex/2026-09-05/k/outputs/stage1-v2-recovery-status.json>)

Original evidence archive SHA-256: `8acf289adf05a241270d4744ed8337bf9b1f4c2e7024c8c3d049ef8200152e8e`.

Recovery input archive SHA-256: `f28d32698bea5042411c9fb7ebae325b6f4771b867ae62a08572d73819ba827b`.

The beta=1 correction, remaining research families and the legacy system's unresolved physical/time-to-text bindings remain within the broader active campaign. This repaired benchmark is one part of that work.
