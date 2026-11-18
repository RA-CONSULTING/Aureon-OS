"""LoRA SFT on the Aureon corpus.

Verified against the installed stack: transformers 4.57.6 / peft 0.18.1 /
trl 0.15.2, which uses `max_seq_length`, `dataset_text_field` and
`processing_class` (not `tokenizer`).

Launch under torchrun for the 4x GH200 node:
  torchrun --nproc_per_node=4 train_lora.py --model ... --data ...
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib

import torch
from datasets import load_dataset
from peft import LoraConfig
from transformers import AutoModelForCausalLM, AutoTokenizer
from trl import SFTConfig, SFTTrainer

from prompt_contract import SYSTEM


def render(tokenizer, instruction: str, response: str) -> str:
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": instruction},
        {"role": "assistant", "content": response},
    ]
    try:
        return tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=False)
    except Exception:
        return f"### Instruction\n{instruction}\n\n### Response\n{response}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--data", required=True, help="dir holding train.jsonl / eval.jsonl")
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-seq-length", type=int, default=4096)
    ap.add_argument("--epochs", type=float, default=1.0)
    ap.add_argument("--batch-size", type=int, default=2)
    ap.add_argument("--grad-accum", type=int, default=8)
    ap.add_argument("--lr", type=float, default=1e-4)
    ap.add_argument("--lora-r", type=int, default=32)
    ap.add_argument("--lora-alpha", type=int, default=64)
    ap.add_argument("--limit", type=int, default=0, help="cap train rows, for smoke tests")
    ap.add_argument("--resume", default="")
    args = ap.parse_args()

    data = pathlib.Path(args.data)
    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    tokenizer = AutoTokenizer.from_pretrained(args.model)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    raw_train = load_dataset("json", data_files=str(data / "train.jsonl"), split="train")
    if args.limit:
        raw_train = raw_train.select(range(min(args.limit, len(raw_train))))
    has_eval = (data / "eval.jsonl").exists()
    raw_eval = load_dataset("json", data_files=str(data / "eval.jsonl"), split="train") if has_eval else None

    def to_text(batch):
        return {"text": [render(tokenizer, i, r) for i, r in zip(batch["instruction"], batch["response"])]}

    train_ds = raw_train.map(to_text, batched=True, remove_columns=raw_train.column_names)
    eval_ds = raw_eval.map(to_text, batched=True, remove_columns=raw_eval.column_names) if raw_eval else None

    use_bf16 = torch.cuda.is_available() and torch.cuda.is_bf16_supported()
    dtype = torch.bfloat16 if use_bf16 else torch.float32

    model = AutoModelForCausalLM.from_pretrained(
        args.model,
        dtype=dtype,
        attn_implementation="sdpa",
    )
    model.config.use_cache = False

    lora = LoraConfig(
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules="all-linear",
    )

    cfg = SFTConfig(
        output_dir=str(out),
        max_seq_length=args.max_seq_length,
        dataset_text_field="text",
        packing=True,
        bf16=True,
        gradient_checkpointing=True,
        gradient_checkpointing_kwargs={"use_reentrant": False},
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        gradient_accumulation_steps=args.grad_accum,
        learning_rate=args.lr,
        num_train_epochs=args.epochs,
        lr_scheduler_type="cosine",
        warmup_ratio=0.03,
        weight_decay=0.01,
        optim="adamw_torch",
        logging_steps=10,
        save_strategy="steps",
        save_steps=200,
        save_total_limit=2,
        eval_strategy="steps" if eval_ds else "no",
        eval_steps=200 if eval_ds else None,
        report_to="none",
        seed=42,
        ddp_find_unused_parameters=False,
        run_name="aureon-sft",
    )

    trainer = SFTTrainer(
        model=model,
        args=cfg,
        train_dataset=train_ds,
        eval_dataset=eval_ds,
        peft_config=lora,
        processing_class=tokenizer,
    )

    print(json.dumps({
        "world_size": int(os.environ.get("WORLD_SIZE", 1)),
        "train_rows": len(train_ds),
        "eval_rows": len(eval_ds) if eval_ds else 0,
        "max_seq_length": args.max_seq_length,
    }, indent=2), flush=True)

    trainer.train(resume_from_checkpoint=args.resume or None)

    adapter_dir = out / "adapter"
    trainer.save_model(str(adapter_dir))
    tokenizer.save_pretrained(str(adapter_dir))
    print(f"[train] adapter saved to {adapter_dir}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
