#!/usr/bin/env python3
"""DGP code-path equivalence check: registered run_batch vs redesign copy.

Runs both implementations on CPU with identically seeded generators and
requires bit-identical values for every original output key. This validates
that the redesign shard reproduces the pre-registered data-generating process
exactly (same statements, same RNG consumption order).
"""

from __future__ import annotations

import importlib.util
import json
import sys

import numpy as np
import torch


ORIG_PATH = "/projects/u6vs/hnc-organism/jobs/tandem_10_9_1_falsification.py"
REDESIGN_PATH = sys.argv[1]


def load(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


orig = load("tandem_orig_check", ORIG_PATH)
redesign = load("tandem_redesign_check", REDESIGN_PATH)

original_keys = [
    "trial_id", "eta", "snr_db", "noise_model", "operator", "truth_model",
    "null_split", "selected_branch", "corr_true", "corr_shift", "discriminant", "eta_hat",
]

results = []
ok_all = True
for shard in (0, 7, 19, 31):
    gain, tau, delta = orig.shard_parameters(shard)
    device = torch.device("cpu")
    gen_a = torch.Generator(device=device)
    gen_a.manual_seed(10_901_000 + shard)
    gen_b = torch.Generator(device=device)
    gen_b.manual_seed(10_901_000 + shard)
    batch_kwargs = dict(
        shard=shard, trial_offset=0, batch=8, steps=1024, branches=16,
        gain=gain, tau=tau, delta=delta, device=device,
    )
    out_orig = orig.run_batch(generator=gen_a, **batch_kwargs)
    out_new = redesign.run_batch_redesign(generator=gen_b, **batch_kwargs)
    shard_ok = True
    for key in original_keys:
        if not np.array_equal(out_orig[key], out_new[key]):
            shard_ok = False
            ok_all = False
            diff = np.max(np.abs(out_orig[key] - out_new[key]))
            print(f"MISMATCH shard={shard} key={key} maxabs={diff}")
    results.append({"shard": shard, "tau": tau, "delta": delta, "gain": gain, "bit_identical": shard_ok})

print(json.dumps({"dgp_cpu_equivalence": ok_all, "shards_tested": results}, indent=2))
if not ok_all:
    raise SystemExit(1)
