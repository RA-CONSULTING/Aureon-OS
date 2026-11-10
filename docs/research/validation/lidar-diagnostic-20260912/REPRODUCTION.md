# Reproduction and evidence storage

The diagnostic source v2 and separate NumPy audit are staged alongside this
report. V1 is preserved as a failed repeatability pilot, not a valid result.
Run in the original e4s-cuda90-aarch64-25.11.sif container on an allocated GPU;
the frozen scripts are configured for the recorded Isambard paths. Retain the
source manifest, FP64, batch size 64 and exact seed mapping. Use a new output
directory for a distinct experiment; do not overwrite the 2026-09-12 evidence.
The historical diagnostics reproduce original shards 0 and 32. Full new seeds
are 0..127, with four disjoint workers. Threshold calibration must include the
complete candidate search operation and truth-informed arms must stay labelled.

The 591,862,567-byte computed evidence archive is retained in the local workspace
and Isambard, with its hash and export manifest in this package. Raw per-example
NPZ score arrays and image samples are outside Git. The local verifier reads that
archive, rechecks all payloads, independently computes 16 score maps on each saved
sample, checks 20 methods' statistics and repeats all paired inference. Native
paper bytes, SHA-256 and Git blob identities are included in the source packs.
The connected legacy review here is an unchanged convenience copy of its earlier
dated evidence package; that broader account remains in scope.

Whitening did not repair the detector; model-informed and truth-informed arms
are diagnostics, not a validated replacement or a historical/physical proof.
