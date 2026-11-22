# Publish the consolidated Aureon / HNC release

This is the canonical publication path for the logical release under `GaryLeckey`. It replaces the earlier private, CPU-only standalone-Space instructions. The older `hnc-field`, `auris-coherence`, `qgita-snr`, and `organism-replay` bundles remain reproducible evidence sources, not competing OS frontends.

The release is connected by exact revisions and receipts:

| Component | Destination | Publication path |
| --- | --- | --- |
| Aureon 7B weights, tokenizer, card, export receipt, evaluation | `GaryLeckey/aureon-7b` | `huggingface/publish_aureon_model.py` |
| Isambard source/token/SFT data | `GaryLeckey/aureon-isambard-data` | `huggingface/isambard_archive.py` |
| Isambard runs and evaluations | `GaryLeckey/aureon-isambard-runs` | `huggingface/isambard_archive.py` |
| Remaining approved HNC organism archive | `GaryLeckey/aureon-isambard-archive` | `huggingface/isambard_archive.py` |
| Consolidated console, operator, own-model server, and HNC | Existing `GaryLeckey/aureon-os` Space | `deploy/huggingface/publish_space.py` |
| Canonical source | Existing `RA-CONSULTING/Aureon-OS` GitHub repository | Normal branch, PR, CI, and merge process |

No publisher accepts a token as a command-line argument. Set only `HF_TOKEN` or `HUGGING_FACE_HUB_TOKEN` in the execution environment. Never print, commit, upload, or place that token in Space secrets. The Space itself needs no Hub, exchange, or external-provider credential.

## 1. Validate the exact consolidated source

Create a clean commit only after reviewing the complete diff. Run the targeted source, routing, HNC, SFT, packaging, archive, shell, and Space tests. Syntax-check shell and Slurm files. Record the source commit and stream that exact commit to Isambard; do not edit the streamed tree in place.

Run the bounded validator in `huggingface/validate_aureon_model.sbatch`. It performs no training and no checkpoint writes. Direct CUDA checks run in a spawned worker; the parent requires a clean worker exit and zero parent-side CUDA allocation before starting the HTTP server, while retaining the worker's pre-exit memory diagnostics. A failed receipt remains evidence and is never overwritten. Do not continue to publication until the actual weight hash, tokenizer round trips, deterministic CUDA generation, HTTP chat path, HNC gears, and model cleanup pass.

## 2. Dry-run the canonical model release

The model publisher reads the original Isambard export and the reviewed overlay without changing either. It hashes the actual 13,990,806,664-byte weight before any Hub call and requires SHA-256 `48487f800623474ab99371d71b369694cae64f8ebc4ef038019c7e60da3d45bb`.

```bash
python huggingface/publish_aureon_model.py \
  --source /projects/u6vs/hnc-organism/runs/aureon-7b-sft-label-fix/hf \
  --overlay /projects/u6vs/aureon-hf-release/model-overlay \
  --manifest /projects/u6vs/aureon-hf-release/model-publication-dry-run.json
```

The dry-run imports no Hub client, needs no token, writes no repository, and copies no weight. Review the nine-file allowlist, hashes, provenance, model card, license, and measured capability limits. Unexpected files are not silently included.

On Isambard, use the login-node `transfer_python` container function documented in `ISAMBARD_TRANSFER.md`; its Python and Hub versions are known. Do not use the host's legacy Python.

## 3. Upload to private model staging

Only after the real source-model GPU receipt passes:

```bash
transfer_python huggingface/publish_aureon_model.py \
  --source /projects/u6vs/hnc-organism/runs/aureon-7b-sft-label-fix/hf \
  --overlay /projects/u6vs/aureon-hf-release/model-overlay \
  --execute \
  --acknowledge-execution PUBLISH_AUREON_7B_TO_PRIVATE_STAGING \
  --receipt /projects/u6vs/aureon-hf-release/model-private-receipt.json
```

The publisher creates or reconciles only `GaryLeckey/aureon-7b` as private staging. It refuses local or remote hash/size mismatches, unexpected remote files, secret-pattern findings, symlinks, conflicting token variables, and output paths inside the source or overlay. Matching remote files are skipped on retry. The weight is uploaded directly from Isambard, never staged on the local PC.

The receipt records the exact model commit. Remote reconciliation checks LFS SHA-256 or Git blob identity, but this alone is not an independent download or a fresh-GPU generation result.

## 4. Make the complete model public

This is a separate, deliberate operation requiring complete reconciliation of the private commit:

```bash
transfer_python huggingface/publish_aureon_model.py \
  --source /projects/u6vs/hnc-organism/runs/aureon-7b-sft-label-fix/hf \
  --overlay /projects/u6vs/aureon-hf-release/model-overlay \
  --execute \
  --make-public \
  --acknowledge-execution PUBLISH_AUREON_7B_TO_PRIVATE_STAGING \
  --acknowledge-public MAKE_GARYLECKEY_AUREON_7B_PUBLIC \
  --receipt /projects/u6vs/aureon-hf-release/model-public-receipt.json
```

Use the exact `revision` from this receipt as `AUREON_MODEL_REVISION`; never use `main`. The Space publisher independently resolves that revision with an anonymous Hub client before any Space write.

Before Space publication, submit the bounded `huggingface/validate_aureon_hub.sbatch` validation job. It anonymously requires the public, ungated model at the exact pinned revision, downloads only the nine allowlisted files into a new job-specific directory as regular files, and verifies every path, size, and SHA-256 against `model-public-receipt.json`. It then runs the same direct CUDA, cleanup, HTTP, and HNC validation entirely offline. This path uses no Hub token, original export, metadata overlay, training command, or checkpoint write. Preserve its fresh-download receipt and do not treat a local fake-based test as a substitute.

## 5. Publish the approved Isambard archive

Follow `huggingface/ISAMBARD_TRANSFER.md`. Inventory and hashing may run as a bounded migration job; Hub uploads must use the login-node path because compute nodes have no outbound network. Do not stage the archive on this PC.

Every batch remains subject to secret, privacy, provenance, licensing, checksum, and remote reconciliation gates. Raw Git internals, unknown provenance, private material, external models/caches, and third-party corpus without redistribution permission remain blocked and explicitly reported. An approved-only partial upload is not represented as a complete archive.

## 6. Stage and publish the existing OS Space

The Space publisher requires a clean source `HEAD` and stages Git blobs from that exact commit, not dirty working-tree files. It refuses secret/key paths and high-confidence embedded credentials, symlinks, stale `frontend/dist`, runtime state, tests, model/checkpoint binaries, and unreviewed source. It generates the Space-root `Dockerfile`, `.dockerignore`, and card from `deploy/huggingface/`.

Dry-run locally or on Isambard without a token:

```bash
python deploy/huggingface/publish_space.py \
  --repo /path/to/Aureon-OS-hf-release \
  --source-revision FULL_CONSOLIDATED_SOURCE_COMMIT \
  --model-revision FULL_PUBLIC_MODEL_COMMIT \
  --receipt /path/to/space-dry-run-receipt.json
```

Review the staged file manifest. Against the existing Space, first run publication without legacy deletion or paid activation. Unknown remote files are listed and refused before upload. After reviewing those paths and confirming that history must remain intact, rerun with `--reviewed-legacy-deletion`.

The model must already be public. The publisher validates the token identity as `GaryLeckey`, writes only `GaryLeckey/aureon-os`, sets the nonsecret `AUREON_MODEL_REVISION` variable, and preserves `.gitattributes`.

Activate the approved paid hardware only in the deliberate launch command:

```bash
python deploy/huggingface/publish_space.py \
  --repo /path/to/Aureon-OS-hf-release \
  --source-revision FULL_CONSOLIDATED_SOURCE_COMMIT \
  --model-revision FULL_PUBLIC_MODEL_COMMIT \
  --publish \
  --reviewed-legacy-deletion \
  --activate-l40s \
  --acknowledge-paid-l40s \
  --receipt /path/to/space-publication-receipt.json
```

This requests one L40S with `sleep_time=-1`. The listed price at approval was $1.80/hour while running; confirm the current price first. A successful API request is recorded only as **request accepted**, not as a running or validated Space. Real runtime evidence comes afterward.

## 7. Verify the real public release

Require the actual image build, strict `/readyz`, and a passing `runtime/smoke-receipt.json`. Then test the public console and APIs in a real browser and with independent clients. Cover startup, first completion, deterministic generation, HNC snapshot/replay evidence, authentication boundaries, mutation denial, rate limits, model-download refusal, CPU refusal, and restart behavior.

Measure cold start, first-token latency, throughput, GPU/RAM use, concurrency, and a sustained soak on the L40S. Record first-call and worst-case values. Fresh-download the complete model and representative archive objects into independent storage and compare bytes/hashes; Hub metadata alone is insufficient.

Finally, generate the cross-linked release manifest with the canonical GitHub commit, model weight hash and Hub revision, every archive revision, Space revision, tested hardware, receipts, measurements, and unresolved blockers. Update `GaryLeckey/aureon-public` as a legacy pointer without deleting its history. Tag only after validation passes.
