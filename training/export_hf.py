"""Turn a pretrain checkpoint into a directory `from_pretrained` can load.

The checkpoint holds a full state dict gathered from FSDP, so the tensor names
are already the ones `Qwen2ForCausalLM` expects. What it does not hold is a
config, a tokenizer, or a file layout — without this step the run produces 43 GB
that nothing can open, which is the difference between a training job and a
model.

    python export_hf.py --ckpt runs/aureon-7b-pretrain/ckpt_0000030.pt \
        --config-from models/Qwen2.5-Coder-7B-Instruct \
        --tokenizer training/aureon_tokenizer.json \
        --out runs/aureon-7b-pretrain/hf
"""

from __future__ import annotations

import argparse
import json
import pathlib
import shutil

import torch
from safetensors.torch import save_file
from tokenizers import Tokenizer


def clean_state(raw: dict) -> dict:
    """Strip wrapper prefixes and drop anything that is not a model tensor."""
    out = {}
    for key, value in raw.items():
        if not torch.is_tensor(value):
            continue
        for prefix in ("_orig_mod.", "module."):
            if key.startswith(prefix):
                key = key[len(prefix):]
        out[key] = value
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", required=True)
    ap.add_argument("--config-from", required=True,
                    help="dir whose config.json describes the architecture")
    ap.add_argument("--tokenizer", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    # Accept a latest.json (as resume-aware callers do) or a checkpoint file.
    ckpt_path = pathlib.Path(args.ckpt)
    if ckpt_path.name == "latest.json":
        payload_latest = json.loads(ckpt_path.read_text(encoding="utf-8"))
        ckpt_path = ckpt_path.parent / payload_latest["checkpoint"]

    tok = Tokenizer.from_file(args.tokenizer)
    vocab = tok.get_vocab_size(with_added_tokens=True)

    # mmap=True keeps the 43 GB checkpoint on disk and pages tensors in as they
    # are written, instead of needing the whole state dict resident.
    payload = torch.load(ckpt_path, map_location="cpu", mmap=True, weights_only=False)
    raw = payload.get("model", payload)
    state = clean_state(raw)

    embed = state.get("model.embed_tokens.weight")
    if embed is None:
        raise SystemExit(f"{ckpt_path}: no model.embed_tokens.weight among {list(state)[:5]}")
    if embed.shape[0] != vocab:
        raise SystemExit(
            f"embedding has {embed.shape[0]} rows but the tokenizer has {vocab}; "
            f"checkpoint {ckpt_path} was trained before --tokenizer was wired in, "
            "and exporting it would attach the wrong vocabulary")

    # clone(): safetensors refuses to serialise a read-only mmap view.
    save_file({k: v.clone().contiguous() for k, v in state.items()},
              str(out / "model.safetensors"),
              metadata={"format": "pt"})

    config = json.loads((pathlib.Path(args.config_from) / "config.json").read_text(encoding="utf-8"))
    config["vocab_size"] = vocab
    config["architectures"] = ["Qwen2ForCausalLM"]
    config["torch_dtype"] = "bfloat16"
    config["use_cache"] = True
    (out / "config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")

    shutil.copyfile(args.tokenizer, out / "tokenizer.json")
    eos_id = tok.token_to_id("<eos>")
    eos = tok.id_to_token(eos_id) if eos_id is not None else None
    (out / "tokenizer_config.json").write_text(json.dumps({
        "tokenizer_class": "PreTrainedTokenizerFast",
        "model_max_length": 4096,
        "eos_token": eos,
        "bos_token": eos,
        "pad_token": eos,
        "unk_token": None,
        "clean_up_tokenization_spaces": False,
    }, indent=2), encoding="utf-8")

    params = sum(v.numel() for v in state.values())
    (out / "aureon_export.json").write_text(json.dumps({
        "source_checkpoint": ckpt_path.name,
        "step": payload.get("step"),
        "tokens": payload.get("tokens"),
        "params": params,
        "params_b": round(params / 1e9, 3),
        "vocab_size": vocab,
        "eos_token": eos,
    }, indent=2), encoding="utf-8")
    print(f"[export] {params/1e9:.3f}B params, vocab {vocab} -> {out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
