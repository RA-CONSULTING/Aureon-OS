"""Pretrain Aureon's own 7B from random weights on the token shards.

This is the metamorphosis step: no borrowed weights enter here. The *shape* is
copied from Qwen2.5-Coder (same layer count, heads, rope, vocab) because a
proven architecture is not lineage, but every parameter is initialised from
scratch and trained only on Aureon's staged corpus.

Deliberate simplifications, each with its cost stated:

- **bf16 parameters, not fp32 master weights.** Halves per-GPU state so a 7B
  fits comfortably on four 96 GB GH200s. Cost: slightly lossy optimizer
  moments. The upgrade path is fp32 params with bf16 compute once throughput
  on this fabric is known, which is the thing this run is meant to measure.
- **Manual batches, no DataLoader.** The data is already token ids; a loader
  with workers would only add copies. Each rank walks the same shard order
  with the same seed and takes every world_size-th window, so no token is seen
  twice or missed in an epoch.
- **Full-state checkpoints, rank 0 only.** Sharded checkpoints are faster but
  produce files only FSDP can read; a full state dict is what a GGUF converter
  or an HF `from_pretrained` can consume later.

    torchrun --nproc_per_node=4 pretrain.py \
        --config-from .../Qwen2.5-Coder-7B-Instruct \
        --tokens /projects/u6vs/pretrain/tokens \
        --out /projects/u6vs/hnc-organism/runs/aureon-7b-pretrain
"""

from __future__ import annotations

import argparse
import functools
import json
import math
import os
import pathlib
import time

import numpy as np
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


class TokenStream:
    """Deterministic, rank-strided windows over a set of mmapped shards."""

    def __init__(self, shards: list[pathlib.Path], seq_len: int, batch_size: int,
                 rank: int, world: int, seed: int) -> None:
        self.arrays = [np.memmap(p, dtype=np.uint16, mode="r") for p in shards]
        self.seq_len = seq_len
        self.batch_size = batch_size
        self.rank = rank
        self.world = world
        self.seed = seed
        self.epoch = 0
        self._gen = self._windows()

    def _windows(self):
        rng = np.random.default_rng(self.seed)
        while True:
            order = rng.permutation(len(self.arrays))
            for shard_idx in order:
                arr = self.arrays[int(shard_idx)]
                usable = (len(arr) // self.seq_len) * self.seq_len
                count = usable // self.seq_len
                if count == 0:
                    continue
                offsets = rng.permutation(count) * self.seq_len
                for i in range(self.rank, count, self.world):
                    start = int(offsets[i])
                    yield arr[start:start + self.seq_len]
            self.epoch += 1

    def batch(self) -> tuple[torch.Tensor, torch.Tensor]:
        rows = [np.asarray(next(self._gen)) for _ in range(self.batch_size)]
        block = np.stack(rows).astype(np.int64)
        x = torch.from_numpy(block[:, :-1])
        y = torch.from_numpy(block[:, 1:])
        return x, y


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
    path = out / f"ckpt_{step:07d}.pt"
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
            }, tmp)
            tmp.replace(path)
            (out / "latest.json").write_text(json.dumps({
                "checkpoint": path.name, "step": step, "tokens": tokens,
            }, indent=2), encoding="utf-8")
            olds = sorted(out.glob("ckpt_*.pt"))
            for old in olds[:-keep]:
                old.unlink(missing_ok=True)
    dist.barrier()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config-from", required=True,
                    help="model dir whose config.json defines the architecture")
    ap.add_argument("--tokens", required=True, help="dir with index.json + shard_*.bin")
    ap.add_argument("--out", required=True)
    ap.add_argument("--seq-len", type=int, default=4096)
    ap.add_argument("--batch-size", type=int, default=2, help="per device")
    ap.add_argument("--grad-accum", type=int, default=8)
    ap.add_argument("--lr", type=float, default=3e-4)
    ap.add_argument("--warmup", type=int, default=2000)
    ap.add_argument("--steps", type=int, default=0, help="0 = one full pass over the shards")
    ap.add_argument("--save-every", type=int, default=1000)
    ap.add_argument("--keep", type=int, default=2)
    ap.add_argument("--shard", choices=("full", "hybrid"), default="full",
                    help="FSDP layout. full shards across every rank. hybrid "
                         "shards inside a node and replicates across nodes.")
    ap.add_argument("--log-every", type=int, default=10)
    ap.add_argument("--seed", type=int, default=1337)
    ap.add_argument("--grad-checkpoint", action="store_true")
    ap.add_argument("--tokenizer", default="",
                    help="Aureon tokenizer.json. Its vocab size overrides the "
                         "config's: the shards hold ids from THIS tokenizer "
                         "(65k), not from the model the config came from "
                         "(151k). Without the override the embedding carries "
                         "86k rows that can never be indexed.")
    ap.add_argument("--resume", default="",
                    help="'auto' to continue from <out>/latest.json, or a path")
    args = ap.parse_args()

    dist.init_process_group("nccl")
    rank, world = dist.get_rank(), dist.get_world_size()
    local_rank = int(os.environ.get("LOCAL_RANK", rank))
    torch.cuda.set_device(local_rank)

    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    # Parallel tokenizer workers each keep a private index; merge them here so
    # the training loop sees one flat shard list regardless of worker count.
    tdir = pathlib.Path(args.tokens)
    index_paths = ([tdir / "index.json"] if (tdir / "index.json").exists()
                   else sorted(tdir.glob("worker_*/index.json")))
    if not index_paths:
        print(f"[pretrain] no index.json under {tdir}", flush=True)
        return 2

    shards: list[pathlib.Path] = []
    total_tokens = 0
    for ip in index_paths:
        payload = json.loads(ip.read_text(encoding="utf-8"))
        shards.extend(ip.parent / e["name"] for e in payload["shards"])
        total_tokens += int(payload["total_tokens"])
    shards.sort()
    if not shards:
        print("[pretrain] no shards to train on", flush=True)
        return 2

    # Random init. from_config builds the architecture and fills it with
    # initial weights; nothing is loaded from --config-from except config.json.
    config = AutoConfig.from_pretrained(args.config_from)
    config.use_cache = False
    if args.tokenizer:
        from tokenizers import Tokenizer

        vocab = Tokenizer.from_file(args.tokenizer).get_vocab_size(with_added_tokens=True)
        if vocab != config.vocab_size:
            print(f"[pretrain] vocab_size {config.vocab_size} -> {vocab} "
                  f"to match the tokenizer that produced the shards", flush=True)
            config.vocab_size = vocab
    torch.set_default_dtype(torch.bfloat16)
    model = AutoModelForCausalLM.from_config(config)
    n_params = sum(p.numel() for p in model.parameters())

    if args.grad_checkpoint:
        model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
        model.config.use_cache = False

    layer_cls = type(model.model.layers[0])
    policy = functools.partial(transformer_auto_wrap_policy,
                               transformer_layer_cls={layer_cls})
    strategy = (ShardingStrategy.HYBRID_SHARD if args.shard == "hybrid"
                else ShardingStrategy.FULL_SHARD)
    if rank == 0:
        print(f"[pretrain] shard={args.shard}", flush=True)
    model = FSDP(
        model,
        sharding_strategy=strategy,
        auto_wrap_policy=policy,
        mixed_precision=MixedPrecision(param_dtype=torch.bfloat16,
                                        reduce_dtype=torch.bfloat16,
                                        buffer_dtype=torch.bfloat16),
        device_id=torch.cuda.current_device(),
        sync_module_states=True,
    )
    optim = torch.optim.AdamW(model.parameters(), lr=args.lr, betas=(0.9, 0.95),
                              weight_decay=0.1, fused=True)

    per_step_tokens = args.seq_len * args.batch_size * args.grad_accum * world
    est_steps = args.steps or max(total_tokens // per_step_tokens, 1)

    # A 24 h QOS cap means no run finishes in one job, so resume is not a
    # convenience here: without it the 157-day single-node estimate is
    # unreachable by construction. 'auto' picks up <out>/latest.json.
    start_step = start_tokens = 0
    ckpt_path = pathlib.Path(args.resume) if args.resume not in ("", "auto") else None
    if args.resume == "auto" and (out / "latest.json").exists():
        ckpt_path = out / json.loads((out / "latest.json").read_text(encoding="utf-8"))["checkpoint"]
    if ckpt_path is not None and ckpt_path.exists():
        payload = torch.load(ckpt_path, map_location="cpu", weights_only=False)
        cfg_full = FullStateDictConfig(offload_to_cpu=True, rank0_only=True)
        ocfg = FullOptimStateDictConfig(offload_to_cpu=True, rank0_only=True)
        with FSDP.state_dict_type(model, StateDictType.FULL_STATE_DICT, cfg_full, ocfg):
            model.load_state_dict(payload["model"])
            loaded_optim = FSDP.optim_state_dict_to_load(model, optim, payload["optim"])
            optim.load_state_dict(loaded_optim)
        start_step = int(payload.get("step", 0))
        start_tokens = int(payload.get("tokens", 0))
        if rank == 0:
            print(f"[pretrain] resumed {ckpt_path.name} at step {start_step}", flush=True)
        del payload

    stream = TokenStream(shards, args.seq_len, args.batch_size, rank, world, args.seed)
    # A resumed run recreates the same deterministic window order from zero (same
    # seed), so without this skip the stream would replay windows the restored
    # weights already trained on while the token counter moved ahead. Windows
    # consumed per rank = start_tokens / ((seq_len - 1) * world): tokens are
    # counted as batch*(seq_len-1)*world per micro-batch, so batch and grad_accum
    # cancel out and the position stays valid if BATCH/ACCUM change across jobs.
    if start_tokens:
        windows_done = start_tokens // ((args.seq_len - 1) * world)
        t_ff = time.time()
        for _ in range(windows_done):
            next(stream._gen)
        if rank == 0:
            print(f"[pretrain] fast-forwarded {windows_done} windows/rank in "
                  f"{time.time() - t_ff:.1f}s to resume the data stream", flush=True)

    if rank == 0:
        print(json.dumps({
            "params": n_params,
            "params_b": round(n_params / 1e9, 3),
            "world_size": world,
            "shards": len(shards),
            "corpus_tokens": total_tokens,
            "tokens_per_optimizer_step": per_step_tokens,
            "planned_steps": est_steps,
        }, indent=2), flush=True)

    step, tokens_done, t0 = start_step, start_tokens, time.time()
    while step < est_steps:
        lr = lr_at(step, est_steps, args.lr, args.warmup, 0.1)
        for group in optim.param_groups:
            group["lr"] = lr

        for _ in range(args.grad_accum):
            x, y = stream.batch()
            x = x.to(local_rank, non_blocking=True)
            y = y.to(local_rank, non_blocking=True)
            with torch.autocast("cuda", dtype=torch.bfloat16):
                loss = model(input_ids=x, labels=y).loss
            (loss / args.grad_accum).backward()
            tokens_done += x.numel() * world

        model.clip_grad_norm_(1.0)
        optim.step()
        optim.zero_grad(set_to_none=True)
        step += 1

        if rank == 0 and step % args.log_every == 0:
            elapsed = max(time.time() - t0, 1e-9)
            rate = ((tokens_done - start_tokens) / elapsed) if t0 else 0.0
            remaining = max(est_steps - step, 0) * per_step_tokens
            print(json.dumps({
                "step": step, "loss": round(float(loss.item()), 4),
                "lr": f"{lr:.3e}", "tokens": tokens_done,
                "tokens_per_s": round(rate), "eta_h": round(remaining / rate / 3600, 1) if rate else None,
            }), flush=True)

        if args.save_every and step % args.save_every == 0:
            save_checkpoint(model, optim, out, step, tokens_done, est_steps, args.keep)

    save_checkpoint(model, optim, out, step, tokens_done, est_steps, args.keep)
    if rank == 0:
        print(f"[pretrain] done: {step} steps, {tokens_done/1e9:.2f}B tokens", flush=True)
    dist.barrier()
    dist.destroy_process_group()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
