---
language: en
license: mit
library_name: transformers
pipeline_tag: text-generation
tags:
  - aureon
  - causal-lm
  - qwen2
  - from-scratch
  - bf16
---

# Aureon 7B

Aureon 7B is a 6,995,383,808-parameter causal language model with a
`Qwen2ForCausalLM`-compatible shape. It was initialized randomly and trained
from scratch; it is **not** a fine-tune of Qwen or another pretrained model.
Its tokenizer is Aureon's own byte-level BPE with a 65,536-token vocabulary.
The Aureon code and model are owned by Gary Leckey / Aureon Institute and are
released under the MIT License.

## Checkpoint lineage

- Training run: `aureon-7b-sft-label-fix`
- Base pretrain checkpoint: `runs/aureon-7b-v65k/pinned/ckpt_0017000.pt` (source step **17,000**)
- Source SFT checkpoint: `sft_0001578.pt`
- Supervised fine-tuning step: **1,578**
- Evidence jobs: SFT **8602598**, export **8602600**, and evaluation **8602611** completed on Isambard
- Supervised tokens: **62,658,432**
- Layers: **28**
- Hidden size: **3,584**
- Native `max_position_embeddings`: **32,768**
- Weight dtype: **bf16**
- Weight file: `model.safetensors`, approximately **14 GB**

The architecture field describes compatibility only: the weights came from
random initialization, not from pretrained Qwen weights.

## Correct tokenizer and generation metadata

The original export inherited Qwen BOS/EOS IDs `151643` and `151645`, which are
outside this model's 65,536-token vocabulary. The preparation tool derives the
EOS ID from `tokenizer.json`, verifies it against the handoff, and writes
consistent metadata:

| Field | Correct value |
| --- | --- |
| EOS token | `<eos>` |
| BOS and padding tokens | `<eos>` |
| `config.json: bos_token_id` | `1` |
| `config.json: eos_token_id` | `1` |
| `generation_config.json: eos_token_id` | `1` |
| `tokenizer_config.json: eos_token` | `<eos>` |
| `tokenizer_config.json: model_max_length` | `4096` (preserved) |

The ID is not inferred from the inherited Qwen configuration. If `<eos>` is
missing, has conflicting IDs, does not verify as ID 1, or the vocabulary is not
exactly 65,536 contiguous token IDs, preparation fails. The configured BOS
token must also exist in the tokenizer; the real candidate uses `<eos>` for
BOS, EOS, and padding.

The native architecture and 32,768-position config setting are preserved. The
source tokenizer's `model_max_length=4096` is also preserved rather than
silently changing tokenizer behavior. **Neither setting is a claim that quality
or retrieval at any particular context length has been validated.**

## Use with Transformers

The metadata overlay does not contain the approximately 14 GB weight file.
Place `model.safetensors` from the source export alongside these metadata files
before loading the model. The preparation receipt records hashes; no weights
are copied by the preparation tool.

```python
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

# Use the local combined directory, or replace it with the uploaded Hub repo ID.
model_path = "/path/to/aureon-7b"
tokenizer = AutoTokenizer.from_pretrained(model_path)
model = AutoModelForCausalLM.from_pretrained(
    model_path,
    dtype=torch.bfloat16,
    device_map="auto",
)

prompt = "Explain the harmonic pattern in this sequence."
inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
with torch.inference_mode():
    output = model.generate(
        **inputs,
        max_new_tokens=256,
        eos_token_id=1,
    )
print(tokenizer.decode(output[0], skip_special_tokens=True))
```

bf16 weights alone require approximately 14 GB of storage; runtime memory use
is higher and depends on device, context, and inference settings.

## Reproduce the metadata overlay

The preparation script uses only the Python standard library:

```bash
python huggingface/prepare_aureon_model.py \
  /projects/u6vs/hnc-organism/runs/aureon-7b-sft-label-fix/hf \
  huggingface/aureon-7b
```

- **Source export:** `/projects/u6vs/hnc-organism/runs/aureon-7b-sft-label-fix/hf`
- **Canonical Hub destination:** `GaryLeckey/aureon-7b`
- **Metadata/model-card staging destination:** `huggingface/aureon-7b/` in the
  consolidated source repository

The command reads the existing export and writes `config.json`,
`generation_config.json`, `tokenizer_config.json`, `tokenizer.json`,
`aureon_export.json`, and `preparation_receipt.json` to the separate
destination. The receipt contains source/output SHA-256 hashes and the derived
EOS ID. The source must not equal the destination. The tool never edits the
source export and never copies `model.safetensors`.

## Evaluation

The only results reported here are from `eval-sft-label-fix.json`:

| Measure | Value |
| --- | ---: |
| Evaluation rows | 1,125 |
| Parse rate | 0.4624183006535948 (46.24%; 612 parsed) |
| Symbol recall | 0.2411196294744682 (775 scored rows) |
| Overall line F1 | 0.035554558485818205 |
| Implement rows | 638 |
| Implement symbol recall | 0.30049261083743845 |
| Implement line F1 | 0.016413346611668555 |
| Explain rows | 66 |
| Explain symbol recall | 0.061392267344648296 |
| Explain line F1 | 0.19042254384675905 |

The evaluation used at most 1,024 new tokens per row. These are the recorded
aggregate values for this SFT checkpoint and evaluation set; they are not
extrapolated to other tasks or datasets. `evaluation_summary.json` contains the
same aggregate, the evaluation job ID, and the source file's SHA-256. The full
result remains at `runs/eval-sft-label-fix.json` in the run archive.

## Limitations and scope of validation

- The measured parse rate, symbol recall, and implement line F1 show that this
  checkpoint remains unreliable for structured implementation output.
- The 66 explain rows have the aggregate symbol-recall and line-F1 values
  reported above; no separate human judgment of explanation quality is claimed.
- No HumanEval result is reported or claimed. No general reasoning, coding,
  long-context, production-readiness, or comparative performance result is
  claimed beyond the evaluation above.
- A 32,768-position architecture setting does not establish useful long-context
  behavior. Context quality has not been validated at that length.
- Random-initialization lineage and `Qwen2ForCausalLM` compatibility do not
  imply Qwen-level capability.
- The metadata overlay alone is not a loadable model; the original bf16 weights
  must be supplied separately.
