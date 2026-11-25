# Aureon own-model organism: production and training plan

Status: active integration plan, not a production release or training authorization.
Observed on 24 November 2026. Later SSH checks currently fail publickey
authentication even though the local certificate's printed validity has not
expired; refresh Clifton auth before relying on live queue or storage state.

## One system

Aureon-OS is the governed harness and UI. Aureon's own checkpoint is the only
language-model provider on the own-model route. HNC, Auris, and QGITA supply
measured, receipt-bound evidence before inference and remain visible in the
response. Tool and external mutations retain their separate typed authority
checks; an organism reading never becomes an execution permit.

The shared evidence schema is `aureon.hnc-llm-organism.v1`, implemented by
`aureon.core.hnc_llm_gears`. Operator and Cognition carry the same snapshot
through their result and SSE envelopes. The Operator UI shows HNC, Auris, and
QGITA engagement, measurements, grounded-input counts, and blockers. The pinned
own-model adapter serializes the evidence into the model prompt and associates
its raw response with that snapshot. Cache hits identify their evidence as
belonging to the original inference. Tenant-isolated requests explicitly lack
host evidence rather than falling back to host trace files.

## Evidence now

- The Isambard 7B run's `latest.json` records checkpoint `ckpt_0019000.pt`,
  step 19,000, and 35,180,308,800 tokens. This is a storage record, not a fresh
  quality measurement.
- `/projects/u6vs/hnc-organism/runs/aureon-7b-sft-now/hf/` exists. Its config
  still describes a 7B-class model (28 layers, hidden size 3584, 65,536-token
  vocabulary).
- `runs/eval-sft-label-fix.json` has 1,125 rows. Aggregate parse rate is
  0.462418, symbol recall 0.241120, and line F1 0.035555. These scores do not
  establish a production-capable coding model.
- No jobs were queued under `garyleckey.u6vs` when checked. The local pinned
  endpoint `127.0.0.1:11435/v1` refused connections, so no live generation was
  tested. Do not claim an online model from an offline/mock test.
- The repository's production HOLD remains in force. Passing focused tests is
  quality evidence only; it does not clear containment, release provenance,
  external HNC anchoring, census closure, or provider read-back requirements.

## Corpus acquisition on Isambard

Hugging Face is reachable from the login node. Use the NGC container's training
Python for `huggingface_hub`/`pyarrow`; the login host's Python is an older
environment and the venv interpreter intentionally requires the container mount.

```bash
apptainer exec --bind /projects/u6vs:/projects/u6vs \
  /projects/u6vs/hnc-organism/containers/pytorch-25.05-py3.sif \
  /projects/u6vs/hnc-organism/venvs/aureon-sft/bin/python \
  /projects/u6vs/hnc-organism/training/scratch/fetch_corpus.py \
  --verify --source code --max-files 1 --out /projects/u6vs/pretrain/data
```

`--list` resolves and prints a pinned commit. `--verify` hashes and validates a
bounded existing selection without downloading or changing its manifest.
`--audit` checks the whole selected source without truncation. A download accepts
`--max-files` or `--limit-gb`, resumes `.part` files, and requires size, Hub LFS
SHA256, and container/text validation before manifest inclusion. Auth uses
HF_TOKEN or the protected Hub token store; credentials never enter the manifest.

Verified on Isambard: `codeparrot/codeparrot-clean` file 1 passed at revision
`35a59fb025bc0a102f7d96eac09d145b896d487b`. Hub metadata lists 140 fineweb-edu
shards (286.4 GB), 150 fineweb shards (302.6 GB), 54 code shards (12.8 GB), and
2 code-python-edu shards (0.6 GB). `bigcode/the-stack-dedup` lists 144 Python
shards (28.6 GB), but listing alone does not prove download permission.

No bulk acquisition is running or approved by this plan. Existing corpus state,
licenses, and evaluation-split isolation must be checked before more data enters
training. Never mix the frozen evaluation corpus into training.

## Phase 1: close the inference evidence path

1. Use the shared evidence schema for every own-model call, including direct
   adapter streaming and non-Operator internal inference callers.
2. Bind a call id, exact request digest, model identity, field receipt, memory
   receipt, and raw-response digest into an append-only receipt. Keep raw user
   content out of shared tenant logs.
3. Make `hnc_core.py` a CLI diagnostic over these existing interfaces, not a
   second agent runtime. Its offline self-test must use temporary receipt
   directories and cannot create or publish model output.
4. Add real HNC measurements for any Auris input promoted to grounded. Tiger
   (Casimir drift) and Panda (vault capacity) currently remain explicitly
   ungrounded. Never replace them with constants to make all nine look healthy.
5. Expose per-call failures and stale evidence in health/readiness without
   leaking tenant content or changing mutation authority.

## Phase 2: measured 7B acceptance and training closure

1. Validate the selected checkpoint's identity, tokenizer/config alignment,
   model load, generation, resume behavior, and evaluation on compute nodes.
2. Use a frozen evaluation suite and immutable dataset/eval hashes. Measure
   syntactic validity, behavioral unit tests, security/regression cases,
   latency, throughput, and memory. Syntax alone is not model correctness.
3. Continue the 7B pretraining/SFT path only through separately approved jobs
   with node counts, wall limits, output locations, and budget limits stated
   before submission. No Slurm job is authorized by this document.
4. Publish a signed/hash-chained training manifest containing code commit,
   tokenizer and corpus provenance, checkpoint lineage, hyperparameters,
   evaluation results, and failed-run records. Keep durable artifacts under
   `/projects/u6vs`, with manifests suitable for version control.

## Phase 3: engineer 70B before allocating its budget

The current 7B data-parallel FSDP layout and full-state checkpoints do not
translate directly to 70B. On 120 GB GH200 devices, a 70B bf16 weight tensor is
about 140 GB before gradients or optimizer state. Full-state optimizer
checkpoints would be multiple terabytes each. A 70B program therefore needs:

- a frozen architecture/tokenizer decision and explicit from-scratch versus
  continued-training lineage;
- tensor/pipeline parallelism combined with sharded data parallelism, with
  activation checkpointing and measured memory headroom;
- distributed sharded checkpoints with atomic manifests, checksums, verified
  resume, and retention budgets rather than rank-0 full optimizer exports;
- single-node memory/allocation smoke tests followed by small multi-node
  throughput and resume tests, all individually approved;
- an acceptance gate proving the larger model is materially better than 7B on
  the frozen evaluation before a long run.

The stated 20,000-node-hour ceiling is a resource budget to measure and manage,
not a license to submit work. Propose each run's node-hour estimate and
acceptance criteria first; reserve the majority of the budget until the small
scaling and recovery tests have measured real throughput and failure rates.

## Operational rule

No job submission, model loading on a login node, production release, external
publication, or economic action follows from this plan alone. Each needs its
existing authorization path and evidence suitable for that exact operation.
