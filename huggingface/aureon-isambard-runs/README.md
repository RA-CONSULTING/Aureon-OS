---
pretty_name: Aureon Isambard Runs
license: other
tags:
  - aureon
  - hnc
  - isambard
  - checkpoints
---

# Aureon Isambard Runs

Checksum-tracked preservation of approved artifacts from `/projects/u6vs/hnc-organism/runs/`, including checkpoints, alternate lineages, exports, logs, evaluations, and historical run directories. Paths remain under `runs/` in this repository.

This is an evidence archive, not a collection of equally validated deployable models. The only canonical public model candidate is the label-fixed SFT export published separately at [GaryLeckey/aureon-7b](https://huggingface.co/GaryLeckey/aureon-7b).

## Lineage map

- `runs/aureon-7b-v65k/`: active pretraining lineage at inspection. `latest.json` identified `ckpt_0019000.pt`, step 19,000, and 35,180,308,800 tokens.
- `runs/aureon-7b-sft-label-fix/`: release candidate lineage. `sft_0001578.pt` corresponds to 1,578 SFT steps and 62,658,432 supervised tokens; its `hf/` export contains 6,995,383,808 parameters and a 65,536-token vocabulary.
- `runs/aureon-7b-sft-now/`: earlier lineage retained for history. It must not be confused with the label-fixed candidate.
- `runs/eval-sft-label-fix.json`: the 1,125-row candidate evaluation used by the model card.

Cancelled jobs `8593291`, `8593292`, and `8593293` are not evidence of completed SFT, export, or evaluation. Logs and status files remain historical evidence and must be read with that distinction.

## Candidate evaluation

The existing evaluation measured a parse rate of 46.24% over 1,125 rows, symbol recall of 0.2411196294744682 over 775 scored rows, implementation symbol recall of 0.30049261083743845 over 638 implementation rows, and overall line F1 of 0.035554558485818205. These values describe the recorded evaluation only; they are not broad capability or benchmark claims.

## Integrity, rights, and exclusions

Every regular file is inventoried with relative path, size, SHA-256, destination, and provenance. Batches upload directly from Isambard and are reconciled against exact Hub revisions. Credentials, private keys, session material, sensitive personal data, and unclear third-party material are blocked and explicitly reported rather than omitted from accounting.

Aureon-authored code and documentation retain their upstream terms. This archive does not relicense third-party content, upstream model artifacts, or datasets that may appear in historical runs. `license: other` reflects that mixed provenance. Exact repository revisions and any unresolved blockers will be recorded in the final release manifest.
