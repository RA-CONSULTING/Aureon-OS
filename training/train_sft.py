"""Supervised full fine-tune of Aureon's own from-scratch checkpoint.

The metamorphosis made a model; the SFT makes it an assistant. Every training
row is byte-identical to what aureon_chat_server.py puts on the wire:

    system: {SYSTEM}\nuser: {instruction}\nassistant: {response}<eos>

- The prompt half is encoded separately from the response half. That matches
  inference, where the server encodes the prompt alone and the model continues,
  and it pins the label-mask boundary exactly where generation begins.
- Targets end with the tokenizer's own <eos> id (1), which is what the chat
  server uses as its stop id. A model that never learned <eos> cannot stop.
- Rows whose prompt exceeds --seq-len/2 are dropped and counted, never
  silently truncated into half a response the model would learn to emit.
- Checkpoints reuse pretrain.py's full-state-dict schema so export_hf.py can
  consume an SFT checkpoint unchanged.

    torchrun --nproc_per_node=4 train_sft.py \
        --config-from .../Qwen2.5-Coder-7B-Instruct \
        --tokenizer training/aureon_tokenizer.json \
        --ckpt runs/aureon-7b-v65k/latest.json \
        --data training/sft/train.jsonl \
        --out runs/aureon-7b-sft
"""

from __future__ import annotations

import argparse
import functools
import json
import math
import os
import pathlib
import random
import time

import torch
import torch.distributed as dist
from torch.distributed.fsdp import (
    FullOptimStateDictConfig,
    FullStateDictConfig,
    FullyShardedDataParallel as FSDP,
    MixedPrecision,
    ShardingStrategy,
    StateDictType,
)
from torch.distributed.fsdp.wrap import transformer_auto_wrap_policy
from transformers import AutoConfig, AutoModelForCausalLM

from prompt_contract import SYSTEM


def build_rows(args) -> tuple[list[dict], int, int]:
    """Tokenized rows: prompt ids, target ids. Drops are counted, not silent."""
    from tokenizers import Tokenizer

    tok = Tokenizer.from_file(args.tokenizer)
    eos_id = tok.get_vocab().get("<eos>")
    if eos_id is None:
        raise SystemExit("aureon tokenizer has no <eos> token; cannot train a model that stops")

    rows: list[dict] = []
    dropped_long = dropped_bad = 0
    with open(args.data, encoding="utf-8") as fh:
        for line in fh:
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                dropped_bad += 1
                continue
            instruction = payload.get("instruction", "")
            response = payload.get("response", "")
            if not instruction or not response:
                dropped_bad += 1
                continue
            prompt = f"system: {SYSTEM}\nuser: {instruction}\nassistant:"
            ids_p = tok.encode(prompt).ids
            if len(ids_p) > args.seq_len // 2:
                dropped_long += 1
                continue
            ids_t = tok.encode(" " + response).ids + [eos_id]
            if len(ids_p) + len(ids_t) > args.seq_len:
                dropped_long += 1
                continue
            rows.append({"prompt": ids_p, "target": ids_t})
            if args.max_samples and len(rows) >= args.max_samples:
                break
    return rows, dropped_long, dropped_bad


def make_batches(rows: list[dict], batch_size: int, rank: int, world: int,
                 seed: int, seq_len: int) -> tuple[list[dict[str, torch.Tensor]], int]:
    """Length-bucketed padded batches, stride-sharded across ranks.

    Returns the rank-global batch list (every rank builds the same list) and
    the number of batches THIS rank will consume, which equals
    len(batches) // world on every rank — ranks stay in optimizer-step lockstep.
    """
    order = sorted(range(len(rows)),
                   key=lambda i: len(rows[i]["prompt"]) + len(rows[i]["target"]))
    batches: list[list[int]] = [
        order[i:i + batch_size] for i in range(0, len(order), batch_size)
    ]
    batches = [b for b in batches if len(b) == batch_size]
    random.Random(seed).shuffle(batches)
    mine = batches[rank::world]

    eos_id = 1
    tensors: list[dict[str, torch.Tensor]] = []
    for idxs in mine:
        seqs = [rows[i]["prompt"] + rows[i]["target"] for i in idxs]
        n = min(max(len(s) for s in seqs), seq_len)
        input_ids = torch.ones((len(idxs), n - 1), dtype=torch.int64) * eos_id
        labels = torch.full((len(idxs), n - 1), -100, dtype=torch.int64)
        attn = torch.zeros((len(idxs), n - 1), dtype=torch.int64)
        for r, i in enumerate(idxs):
            s = seqs[r]
            n_prompt = len(rows[i]["prompt"])
            take = s[:-1]
            input_ids[r, : len(take)] = torch.tensor(take)
            labels[r] = -100
            # y[j] = s[j + 1]; targets start at s[n_prompt], so label positions
            # j >= n_prompt - 1 are supervised, everything before stays masked.
            labels[r, n_prompt - 1 : len(s) - 1] = torch.tensor(s[n_prompt:])
            attn[r, : len(take)] = 1
        tensors.append({"input_ids": input_ids, "labels": labels, "attention_mask": attn})
    return tensors, len(tensors), len(batches) // world


def lr_at(step: int, total: int, peak: float, warmup: int, floor_ratio: float) -> float:
    if step < warmup:
        return peak * (step + 1) / max(warmup, 1)
    progress = (step - warmup) / max(total - warmup, 1)
    cosine = 0.5 * (1.0 + math.cos(math.pi * min(progress, 1.0)))
    return peak * (floor_ratio + (1 - floor_ratio) * cosine)


def save_checkpoint(model, optim, out: pathlib.Path, step: int, tokens: int,
                    total: int, keep: int) -> None:
    cfg = FullStateDictConfig(offload_to_cpu=True, rank0_only=True)
    ocfg = FullOptimStateDictConfig(offload_to_cpu=True, rank0_only=True)
    path = out / f"sft_{step:07d}.pt"
    tmp = path.with_suffix(".pt.tmp")
    with FSDP.state_dict_type(model, StateDictType.FULL_STATE_DICT, cfg, ocfg):
        state = model.state_dict()
        optim_state = FSDP.optim_state_dict(model, optim)
        if dist.get_rank() == 0:
            torch.save({
                "model": state,
                "optim": optim_state,
                "step": step,
                "tokens": tokens,
                "total_steps": total,
                "format": "sft-v1",
            }, tmp)
            tmp.replace(path)
            (out / "latest.json").write_text(json.dumps({
                "checkpoint": path.name, "step": step, "tokens": tokens,
            }, indent=2), encoding="utf-8")
            olds = sorted(out.glob("sft_*.pt"))
            for old in olds[:-keep]:
                old.unlink(missing_ok=True)
    dist.barrier()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config-from", required=True,
                    help="dir whose config.json defines the architecture")
    ap.add_argument("--tokenizer", required=True)
    ap.add_argument("--ckpt", required=True,
                    help="from-scratch checkpoint file or its latest.json")
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--seq-len", type=int, default=4096)
    ap.add_argument("--batch-size", type=int, default=2, help="per rank")
    ap.add_argument("--grad-accum", type=int, default=8)
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--lr", type=float, default=2e-5)
    ap.add_argument("--warmup", type=int, default=40)
    ap.add_argument("--save-every", type=int, default=200)
    ap.add_argument("--keep", type=int, default=3)
    ap.add_argument("--log-every", type=int, default=5)
    ap.add_argument("--seed", type=int, default=1337)
    ap.add_argument("--grad-checkpoint", action="store_true")
    ap.add_argument("--max-samples", type=int, default=0, help="0 = all rows")
    args = ap.parse_args()

    dist.init_process_group("nccl")
    rank, world = dist.get_rank(), dist.get_world_size()
    local_rank = int(os.environ.get("LOCAL_RANK", rank))
    torch.cuda.set_device(local_rank)

    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    rows, dropped_long, dropped_bad = build_rows(args)
    batches, n_micro, _ = make_batches(
        rows, args.batch_size, rank, world, args.seed, args.seq_len)
    # len(batches) is the GLOBAL batch list: one optimizer step consumes
    # grad_accum batches PER RANK, i.e. grad_accum*world batches globally.
    # The training loop below is bound by this number; computing it here (not
    # inside make_batches) keeps the LR schedule and resume math consistent.
    steps_per_epoch = (len(batches) + args.grad_accum * world - 1) // (
        args.grad_accum * world)
    total_steps = steps_per_epoch * args.epochs
    if rank == 0:
        print(json.dumps({
            "rows": len(rows), "dropped_long": dropped_long,
            "dropped_bad": dropped_bad, "micro_batches_per_rank_epoch": n_micro,
            "optimizer_steps_per_epoch": steps_per_epoch, "total_steps": total_steps,
        }, indent=2), flush=True)

    torch.set_default_dtype(torch.bfloat16)
    config = AutoConfig.from_pretrained(args.config_from)
    config.use_cache = False
    from tokenizers import Tokenizer

    vocab_size = Tokenizer.from_file(args.tokenizer).get_vocab_size(with_added_tokens=True)
    if vocab_size != config.vocab_size:
        print(f"[sft] vocab_size {config.vocab_size} -> {vocab_size}", flush=True)
        config.vocab_size = vocab_size
    model = AutoModelForCausalLM.from_config(config)

    ckpt_path = pathlib.Path(args.ckpt)
    if args.ckpt.endswith("latest.json"):
        ckpt_path = ckpt_path.parent / json.loads(ckpt_path.read_text(encoding="utf-8"))["checkpoint"]
    payload = torch.load(ckpt_path, map_location="cpu", weights_only=False)
    model.load_state_dict(payload["model"])
    if rank == 0:
        print(f"[sft] base weights from {ckpt_path.name} "
              f"(source step {int(payload.get('step', 0))})", flush=True)
    del payload

    if args.grad_checkpoint:
        model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
        model.config.use_cache = False

    layer_cls = type(model.model.layers[0])
    policy = functools.partial(transformer_auto_wrap_policy, transformer_layer_cls={layer_cls})
    model = FSDP(
        model,
        sharding_strategy=ShardingStrategy.FULL_SHARD,
        auto_wrap_policy=policy,
        mixed_precision=MixedPrecision(param_dtype=torch.bfloat16,
                                        reduce_dtype=torch.bfloat16,
                                        buffer_dtype=torch.bfloat16),
        device_id=torch.cuda.current_device(),
        sync_module_states=True,
    )
    optim = torch.optim.AdamW(model.parameters(), lr=args.lr, betas=(0.9, 0.95),
                              weight_decay=0.1, fused=True)

    t0 = time.time()
    tokens_done = 0
    step = 0
    for epoch in range(args.epochs):
        for optimizer_step in range(steps_per_epoch):
            step = optimizer_step + epoch * steps_per_epoch + 1
            lr = lr_at(step - 1, total_steps, args.lr, args.warmup, 0.1)
            for group in optim.param_groups:
                group["lr"] = lr
            loss_value = 0.0
            did_work = False
            for micro in range(args.grad_accum):
                gi = optimizer_step * (args.grad_accum * world) + micro * world + rank
                if gi >= len(batches):
                    continue
                did_work = True
                batch = batches[gi]
                input_ids = batch["input_ids"].to(local_rank, non_blocking=True)
                labels = batch["labels"].to(local_rank, non_blocking=True)
                attn = batch["attention_mask"].to(local_rank, non_blocking=True)
                with torch.autocast("cuda", dtype=torch.bfloat16):
                    loss = model(
                        input_ids=input_ids, labels=labels, attention_mask=attn
                    ).loss
                (loss / args.grad_accum).backward()
                tokens_done += int((labels != -100).sum().item()) * world
                loss_value = loss
            if did_work:
                model.clip_grad_norm_(1.0)
                optim.step()
                optim.zero_grad(set_to_none=True)

            if rank == 0 and step % args.log_every == 0 and loss_value != 0.0:
                elapsed = max(time.time() - t0, 1e-9)
                print(json.dumps({
                    "step": step, "of": total_steps,
                    "loss": round(float(loss_value.item()), 4),
                    "lr": f"{lr:.3e}", "supervised_tokens": tokens_done,
                    "elapsed_s": round(elapsed),
                }), flush=True)
            if args.save_every and (step % args.save_every == 0 or step == total_steps):
                save_checkpoint(model, optim, out, step, tokens_done, total_steps, args.keep)

    save_checkpoint(model, optim, out, step, tokens_done, total_steps, args.keep)
    if rank == 0:
        print(f"[sft] done: {step} steps, {tokens_done/1e6:.1f}M supervised tokens", flush=True)
    dist.barrier()
    dist.destroy_process_group()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
