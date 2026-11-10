# HNC throughput pilot: four times the batch in almost the same time

12 September 2026 · Isambard job 6503906 · Completed, exit 0

The unchanged HNC fine-grid kernel processed a fourfold batch with **3.93–4.00× higher trajectory-step throughput** across four sampled configurations. Bitwise duplicate-output comparisons passed for all five reported dynamical fields in all three repetitions at each batch size. This supports testing larger batches before spending more node-hours on the next scientific ensemble.

This was a short performance diagnostic. The larger batches deliberately repeated parameter points; they are not additional scientific observations or new initial conditions. The original beta=1 reference and 16,777,216-step evidence remain unchanged.

| Gain | Echo delay | Integration window | Baseline median seconds | Fourfold median seconds | Fourfold throughput gain |
|---:|---:|---:|---:|---:|---:|
| 0.5 | 10 | 1 | 0.3966 | 0.3980 | 3.986× |
| 0.75 | 100 | 100 | 0.4212 | 0.4230 | 3.982× |
| 2.5 | 10 | 1 | 0.4109 | 0.4105 | 4.004× |
| 16 | 100 | 100 | 0.4080 | 0.4151 | 3.932× |

Each baseline contains 49,247 trajectories; the fourfold batch contains 196,988. Timings cover 1,024 steps after warm-up, with three repetitions and burn-in 256. The short horizon is chosen to measure execution cost, not to assess long-term stability. The doubled batch gave 1.98–2.01× throughput.

The separate 128-step operator profiles each recorded 5,198 GPU kernel launches. The launch routine was the largest recorded CPU self-time category, at approximately 26–30 ms. Combined with the nearly flat batch timings, this is consistent with substantial launch overhead at the tested batch sizes. Profiled and unprofiled timings are kept separate; summing CPU/device events does not produce a valid overall GPU-utilisation percentage.

The full-horizon setup probe used the original 16,777,216-element forcing horizon but executed just one trajectory step. It took 18–31 ms after the earlier work and peaked at approximately 4.97 GB of allocated device memory. This includes setup and the single step. It identifies a temporary-memory cost; these measurements do not show it dominating the long run's runtime.

The allocation used one node and four distinct GPUs for 19 seconds: **0.005278 node-hours**, or **0.021111 GPU-hours**. All 24 exported archive members, source identities and result hashes were verified locally. The fourfold result is a candidate for the next scientific run's batch size, not a guaranteed speedup for every horizon, configuration, machine or changed kernel.

The next useful scientific expansion is a separately specified initial-history ensemble, retaining the existing zero-history case as a control and adding distinct histories within larger batches. Its checkpoint identity, output axes and analysis must identify those histories. Baseline parity, interrupted/resumed equivalence and a representative GPU pilot are required before a longer production allocation. This pilot has not implemented or executed that new ensemble.

- [Verified timings, profiles and receipts](</C:/Users/samle/Documents/Codex/2026-09-05/k/outputs/hnc-throughput-6503906/verification.json>)
- [Performance protocol](</C:/Users/samle/Documents/Codex/2026-09-05/k/work/hnc-throughput-v1/PROTOCOL.md>)
- [Exported evidence](</C:/Users/samle/Documents/Codex/2026-09-05/k/outputs/hnc-throughput-6503906/evidence.tar.gz>)

Source kernel SHA-256: `1eac7d95222b480e3e54d02c0e92d939a2b6ac39d5b2e33c1d196f0dec96014c`.

Evidence archive SHA-256: `6d8bd196c9d1f95216f2f440b19e779f962c017fb1cd74385137f52dc1a9ae9a`.
