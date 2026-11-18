"""Load an exported Aureon checkpoint and make it produce text.

This is the acceptance test for the pretrain path: if a directory saved by
export_hf.py cannot be loaded by `from_pretrained` and generate, the run produced
bytes rather than a model. Quality at this step count is irrelevant — the tokens
will be noise-ish — but the pipeline is proven end to end.

    python sample_model.py --model runs/aureon-7b-v65k/hf --prompt "def main"
"""

from __future__ import annotations

import argparse
import json

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--prompt", default="def main(argv):")
    ap.add_argument("--max-new-tokens", type=int, default=48)
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    args = ap.parse_args()

    tok = AutoTokenizer.from_pretrained(args.model)
    model = AutoModelForCausalLM.from_pretrained(
        args.model, dtype=torch.bfloat16, attn_implementation="sdpa"
    ).to(args.device).eval()

    ids = tok(args.prompt, return_tensors="pt").input_ids.to(args.device)
    with torch.no_grad():
        out = model.generate(
            ids, max_new_tokens=args.max_new_tokens, do_sample=True,
            temperature=0.8, top_p=0.95, pad_token_id=tok.eos_token_id,
        )

    print(json.dumps({
        "model": args.model,
        "params": sum(p.numel() for p in model.parameters()),
        "vocab_size": model.config.vocab_size,
        "eos_token": tok.eos_token,
        "device": args.device,
    }, indent=2), flush=True)
    print("--- prompt ---")
    print(args.prompt)
    print("--- continuation ---")
    print(tok.decode(out[0][ids.shape[1]:], skip_special_tokens=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
