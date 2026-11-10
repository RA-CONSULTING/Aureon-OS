# Stage 1 v2 — operational recovery amendment

12 September 2026. Frozen before recovery model outcomes. Original protocol, inputs, journals and scores remain immutable.

## Observed failure and repair

Evaluation 6502171_0 suffered `OSError: [Errno 116] Stale file handle` in Triton's cache group read at 12:41:28 UTC. Its engine later timed out and shut down. The benchmark continued producing failed transport records. Shards 1 and 2 completed with no terminal transport failures; shard 3 was still making progress at the last diagnostic inspection. This indicates an operational cache failure, not an observed GPU memory exhaustion or a scientific result.

The repair gives this allocation a new cache tree under Isambard's node-local `LOCALDIR`, setting VLLM_CACHE_ROOT, TRITON_CACHE_DIR and TORCHINDUCTOR_CACHE_DIR. Installed vLLM 0.15.1 source confirms that it derives per-rank compilation directories from VLLM_CACHE_ROOT and redirects the dependent caches there. The job verifies a local filesystem and available space, records the actual paths, and exports compiler cache-path evidence. It does not delete shared caches or change model weights, numerical settings, request contents, gold labels or the pinned adapter.

A service supervisor checks the loopback model health endpoint every five seconds with a three-second timeout. Three consecutive failed checks terminate the benchmark and preserve its durable journals. An incomplete attempt remains unresolved and cannot be silently retried or counted as successful. Batch finalization records the exit code and hashes available evidence even after failure. This addresses the previous cascade of futile requests after the engine failed.

Provider reference: [Isambard storage](https://docs.isambard.ac.uk/user-documentation/information/system-storage/). LOCALDIR on compute nodes is temporary local storage; all experiment evidence stays on project storage.

## Fixed recovery plan

One node, four GPUs, 128 evaluation requests in flight, 90-minute allocation ceiling (1.5 node-hours). Use the same gpt-oss-120b snapshot, vLLM 0.15.1, 0.85 memory fraction, tensor parallel size 4 and server sequence ceiling 256 as the original evaluation.

First run the unchanged development throughput pilot (7,680 calls in the original 32/128/128/32 sequence) on the new cache tree. Require zero terminal transport failures and successful service supervision in all four blocks. Accuracy and malformed answers do not control continuation. This pilot tests the cache/lifecycle change without tuning to evaluation answers.

If that operational gate passes, repeat **all 46,080 original shard-0 requests**, using the unchanged benchmark and original order seed 91300. The complete shard is repeated so selection does not depend on a model answer or on which individual request happened to fail. The original shard's successful and malformed replies are still preserved as first-run outcomes; the new replies are a separate replication, never overwritten first-run records. No performance-based retry is permitted. If the recovery fails, stop and retain its evidence for diagnosis.

Total planned new calls: 53,760. The 90-minute ceiling covers the earlier 7-minute development pilot, approximately 40 minutes of shard service, fresh cache compilation and margin. No additional node is allocated merely to increase billing.

## Analysis and interpretation

The original 184,320-request matrix is audited with its 39,484 shard-0 transport failures retained in the frozen denominator. Its evidence integrity and degraded collection status are reported separately. A failed Slurm task is never relabelled completed. The original scheduled audit remains preserved, including its failure on the scheduler gate.

After a successful recovery, a clearly labelled **operational replication sensitivity analysis** combines the new entire shard 0 with the original healthy shards 1–3. The selection is fixed by the failed allocation, not by accuracy. It uses the same paired template analysis and reports every arm and primary contrast, including negative outcomes. It is not a fresh unseen benchmark or independent scientific validation. Report agreement/disagreement on the shard-0 request keys that had successful transport in the original run; this is a descriptive serving-variability check, not a pass threshold or reason to choose one response.

Every included response must be linked to its original or recovery job, source/input hash, actual request body, raw output, attempt journal and re-scored result. Complete identities, authoritative job state and unchanged source bytes remain required. Model weight bytes are not included in the export; their pinned provider snapshot identity and available metadata are retained.
