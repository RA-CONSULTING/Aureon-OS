# Aureon Hugging Face consolidation — version map

Measured 2026-11-22. This map records the inputs to the consolidated release. It is
not a release receipt: the final model, dataset, source, and Space revisions are
added only after their real validation paths pass.

## Source identities

| Source | Observed identity | Role |
| --- | --- | --- |
| Local primary | `C:\Users\samle\Aureon-OS`, branch `consolidation/20261121`, `950caa61f014b3f46a0837e6380c712222921ae1` | Baseline with the local organism, monitoring, logging, and Windows fixes |
| GitHub | `RA-CONSULTING/Aureon-OS`, `origin/main` at `c0f38a7a714d0b6e83245d8d6399f09aec7e675e` | Current public source; 23 commits after the common ancestor |
| Common ancestor | `f21fb3ec05179f994a8012a4c37aea5a63cb3c03` | Verified after unshallowing; local baseline has 9 commits on its side |
| Integration worktree | `C:\Users\samle\Aureon-OS-integration`, `7ed6896e4683baf9c253c6497610f33fa2da310a` | Audit input; no tracked changes at inspection |
| Merge worktree | `C:\Users\samle\Aureon-OS-merge`, `592a18ca3810fc4752a6bbb574a5c68c6c08cbf8` | Six paths containing pending shell-hardening work; preserve the source and review both staged and unstaged edits |
| Hugging Face Space | `GaryLeckey/aureon-os`, revision `1db8ae32f24643bde87f5ceda0a57544c8b33fc8` | Public Docker Space, paused on `cpu-basic`; older full-tree deployment |
| Hugging Face code mirror | `GaryLeckey/aureon-public` | Partial MCP code mirror, not an Aureon LLM weight repository |

The release branch is `release/hf-consolidation-20261122` in
`C:\Users\samle\Aureon-OS-hf-release`. GitHub changes are merged into the local
baseline; local-only behavior is not discarded in favor of the older public
Space.

## Isambard model identities

All paths in this table are under `/projects/u6vs/hnc-organism/`.

| Artifact | Observed state |
| --- | --- |
| Active pretrain lineage | `runs/aureon-7b-v65k`, latest `ckpt_0019000.pt`, step 19,000, 35,180,308,800 tokens |
| Release candidate | `runs/aureon-7b-sft-label-fix/hf` |
| SFT state | `sft_0001578.pt`, step 1,578, 62,658,432 supervised tokens |
| Export | 6,995,383,808 parameters, 65,536 vocabulary, `<eos>` EOS, approximately 14 GB Safetensors |
| Earlier SFT lineage | `runs/aureon-7b-sft-now`; preserve it in the run archive rather than silently replacing it |
| Full candidate evaluation | `runs/eval-sft-label-fix.json`, 1,125 rows |
| Parse rate | 0.4624183006535948 (46.24%) |
| Symbol recall | 0.2411196294744682 over 775 scored rows |
| Implement symbol recall | 0.30049261083743845 over 638 implementation rows |

The cancelled original chain jobs `8593291`, `8593292`, and `8593293` are not
proof of a completed SFT/export/eval. The later `sft-label-fix` artifacts and
`eval-sft-label-fix.json` are the actual candidate evidence.

## Training-file comparison

A SHA-256 comparison covered every regular file directly inside local and
Isambard `training/`: 34 local files and 36 remote files. Thirty files matched.
The differences are:

| File | Decision |
| --- | --- |
| `aureon_chat_server.py` | Keep the consolidated local version. It captures organism state before generation and reuses that snapshot in the HNC receipt; the Isambard copy lacks this behavior. The GitHub `Path` import fix is retained. |
| `stage_model.sh` | Keep the local byte and parameter reporting fix. The Isambard copy prints the older, ambiguous parameter calculation. |
| `sweep.sbatch` | Record the Isambard 2-hour operational limit; retain the local 6-hour canonical default. No training run is part of this migration. |
| `train_lora.sbatch` | Record the Isambard 6-hour operational limit; retain the local 8-hour canonical default. No LoRA run is part of this migration. |
| `aureon_tokenizer.json` | Isambard-only in this comparison; package directly with the model and preserve in the data archive. |
| `aureon_tokenizer.report.json` | Isambard-only; use as tokenizer provenance and preserve it with the model/archive metadata. |

The comparison does not claim that historical run directories, corpora, token
shards, logs, or nested source mirrors are identical. Those are covered by the
full archive inventory and per-file transfer manifests, not by this source-file
sample.

## Canonical release mapping

The final release manifest will link these destinations by exact revision:

| Destination | Contents |
| --- | --- |
| `GaryLeckey/aureon-7b` | Verified label-fixed SFT model, tokenizer, card, export receipt, and evaluation summary |
| `GaryLeckey/aureon-isambard-data` | `/projects/u6vs/pretrain` plus approved SFT/tokenizer-building data |
| `GaryLeckey/aureon-isambard-runs` | `/projects/u6vs/hnc-organism/runs` with all approved checkpoints, exports, logs, evaluations, and historical runs |
| `GaryLeckey/aureon-isambard-archive` | Remaining approved `hnc-organism` content, including HNC evidence and cluster-source snapshots |
| `GaryLeckey/aureon-os` | Consolidated source deployment with the pinned own-model server and HNC routes |

Credentials, private keys, session material, sensitive personal data, and content
without redistribution permission are not public release inputs. A blocked batch
must be reported explicitly; it must not disappear from the reconciliation.
