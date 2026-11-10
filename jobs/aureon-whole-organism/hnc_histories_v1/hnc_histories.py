#!/usr/bin/env python3
"""One FP64 shard of the HNC Grand Challenge phase-diagram campaign."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import time
from pathlib import Path
from typing import Any

import numpy as np
import torch


SCHEMA = "hnc-history-ensemble/v1"
HISTORY_NAMES = ("zero", "positive_one", "negative_one", "alternating_one")
INITIALIZATION_VERSION = "signed-unit-history/v1"
CLAIM_CLASS = "computational_simulation"
BOUNDARY = (
    "Finite-horizon recurrence, escape and Lyapunov classifications test the specified "
    "HNC numerical model only. They are not physical or ontological validation."
)
FS = 1000.0
FREQUENCIES = np.asarray(
    [7.83, 14.3, 20.8, 27.3, 33.8, 39.0, 45.0, 111.0, 174.0,
     188.0, 285.0, 396.0, 417.0, 528.0, 639.0, 741.0, 852.0, 963.0],
    dtype=np.float64,
)
GAINS = (0.5, 0.75, 1.0, 1.5, 2.5, 4.0, 8.0, 16.0)
TAU_STEPS = (10, 25, 50, 100)
DELTA_STEPS = (1, 10, 50, 100)
ALPHAS = np.round(np.linspace(0.0, 1.5, 121), 8)
BETAS = np.round(np.linspace(0.0, 1.6, 161), 8)
STEPS = 65536
BURN_IN = 8192
RENORMALIZE_EVERY = 64
ESCAPE_THRESHOLD = 1.0e12


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def serializable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): serializable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [serializable(v) for v in value]
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (float, np.floating)):
        number = float(value)
        return number if math.isfinite(number) else None
    if isinstance(value, np.integer):
        return value.item()
    return value


def shard_parameters(shard: int) -> tuple[float, int, int]:
    if not 0 <= shard < len(GAINS) * len(TAU_STEPS) * len(DELTA_STEPS):
        raise ValueError("shard must be in 0..127")
    gain_index = shard // (len(TAU_STEPS) * len(DELTA_STEPS))
    within = shard % (len(TAU_STEPS) * len(DELTA_STEPS))
    tau_index = within // len(DELTA_STEPS)
    delta_index = within % len(DELTA_STEPS)
    return GAINS[gain_index], TAU_STEPS[tau_index], DELTA_STEPS[delta_index]


def run_grid(device: torch.device, gain: float, tau: int, delta: int, *, resume=None, checkpoint=None, stop_step=None, stop_requested=None, return_progress=False) -> dict[str, np.ndarray]:
    dtype = torch.float64
    aa, bb = np.meshgrid(ALPHAS, BETAS, indexing="ij")
    names = tuple(HISTORY_NAMES)
    allowed = {"zero", "positive_one", "negative_one", "alternating_one"}
    if not names or len(set(names)) != len(names) or any(name not in allowed for name in names):
        raise ValueError("Initial histories must be unique named supported cases")
    output_shape = (len(names), len(ALPHAS), len(BETAS))
    alpha = torch.as_tensor(np.tile(aa.ravel(), len(names)), device=device, dtype=dtype)
    beta = torch.as_tensor(np.tile(bb.ravel(), len(names)), device=device, dtype=dtype)
    batch = alpha.numel()
    history_length = max(tau, delta) + 1
    # Columns represent times -history_length, ..., -1; pointer=0 is overwritten at t=0.
    templates = []
    for name in names:
        if name == "zero": row = np.zeros(history_length, dtype=np.float64)
        elif name == "positive_one": row = np.ones(history_length, dtype=np.float64)
        elif name == "negative_one": row = -np.ones(history_length, dtype=np.float64)
        else: row = np.where(np.arange(-history_length, 0) % 2 == 0, 1.0, -1.0)
        templates.append(row)
    initial = np.repeat(np.stack(templates), aa.size, axis=0)
    base = torch.as_tensor(initial, device=device, dtype=dtype).clone()
    perturbed = base.clone()
    epsilon = 1.0e-8
    perturbed[:, -1] += epsilon
    rolling_base = base[:, -delta:].sum(dim=1)
    rolling_perturbed = perturbed[:, -delta:].sum(dim=1)

    weights = 1.0 / (1.0 + np.log(FREQUENCIES / 7.83))
    weights /= weights.sum()
    phases = 2.0 * np.pi * np.arange(FREQUENCIES.size) / FREQUENCIES.size
    weights_t = torch.as_tensor(weights, device=device, dtype=dtype)
    phases_t = torch.as_tensor(phases, device=device, dtype=dtype)
    frequencies_t = torch.as_tensor(FREQUENCIES, device=device, dtype=dtype)
    times = torch.arange(STEPS, device=device, dtype=dtype) / FS
    forcing = torch.sum(
        weights_t[:, None] * torch.sin(
            2.0 * math.pi * frequencies_t[:, None] * times[None, :] + phases_t[:, None]
        ),
        dim=0,
    )

    max_abs = torch.zeros(batch, device=device, dtype=dtype)
    escaped = torch.zeros(batch, device=device, dtype=torch.bool)
    first_escape = torch.full((batch,), -1, device=device, dtype=torch.int32)
    lyapunov_sum = torch.zeros(batch, device=device, dtype=dtype)
    lyapunov_blocks = torch.zeros(batch, device=device, dtype=torch.int32)
    pointer = 0
    start_step = 0
    end_step = STEPS if stop_step is None else int(stop_step)
    identity = {
        "initial_history_names": list(names), "initialization_version": INITIALIZATION_VERSION,
        "gain": gain, "tau": tau, "delta": delta, "steps": STEPS,
        "burn_in": BURN_IN, "renormalize_every": RENORMALIZE_EVERY,
        "escape_threshold": ESCAPE_THRESHOLD, "fs": FS,
        "alphas": ALPHAS.tolist(), "betas": BETAS.tolist(),
        "frequencies": FREQUENCIES.tolist(),
        "harness_sha256": sha256_file(Path(__file__)),
        "torch_version": str(torch.__version__), "device_type": device.type,
    }
    if resume is not None:
        payload = torch.load(resume, map_location=device, weights_only=True)
        if payload["identity"] != identity:
            raise ValueError("Checkpoint configuration or implementation mismatch")
        start_step = payload["step"]
        pointer = payload["pointer"]
        tensors = payload["tensors"]
        base = tensors["base"]
        perturbed = tensors["perturbed"]
        rolling_base = tensors["rolling_base"]
        rolling_perturbed = tensors["rolling_perturbed"]
        max_abs = tensors["max_abs"]
        escaped = tensors["escaped"]
        first_escape = tensors["first_escape"]
        lyapunov_sum = tensors["lyapunov_sum"]
        lyapunov_blocks = tensors["lyapunov_blocks"]
    if not 0 <= start_step < end_step <= STEPS:
        raise ValueError("Require 0 <= resumed step < stop step <= horizon")
    for step in range(start_step, end_step):
        echo_index = (pointer - tau) % history_length
        outgoing_index = (pointer - delta) % history_length
        base_value = forcing[step] + alpha * torch.tanh(gain * rolling_base / delta) + beta * base[:, echo_index]
        perturbed_value = forcing[step] + alpha * torch.tanh(gain * rolling_perturbed / delta) + beta * perturbed[:, echo_index]
        bad = (~torch.isfinite(base_value)) | (base_value.abs() > ESCAPE_THRESHOLD)
        newly_bad = bad & (~escaped)
        first_escape = torch.where(newly_bad, torch.tensor(step + 1, device=device, dtype=torch.int32), first_escape)
        escaped |= bad
        base_value = torch.nan_to_num(base_value, nan=0.0, posinf=ESCAPE_THRESHOLD, neginf=-ESCAPE_THRESHOLD).clamp(-ESCAPE_THRESHOLD, ESCAPE_THRESHOLD)
        perturbed_value = torch.nan_to_num(perturbed_value, nan=0.0, posinf=ESCAPE_THRESHOLD, neginf=-ESCAPE_THRESHOLD).clamp(-ESCAPE_THRESHOLD, ESCAPE_THRESHOLD)
        max_abs = torch.maximum(max_abs, base_value.abs())
        outgoing_base = base[:, outgoing_index].clone()
        outgoing_perturbed = perturbed[:, outgoing_index].clone()
        base[:, pointer] = base_value
        perturbed[:, pointer] = perturbed_value
        rolling_base += base_value - outgoing_base
        rolling_perturbed += perturbed_value - outgoing_perturbed
        pointer = (pointer + 1) % history_length

        if step >= BURN_IN and (step + 1) % RENORMALIZE_EVERY == 0:
            difference = perturbed - base
            norm = torch.linalg.vector_norm(difference, dim=1) / math.sqrt(history_length)
            valid = (~escaped) & torch.isfinite(norm) & (norm > 1.0e-30)
            lyapunov_sum += torch.where(valid, torch.log(norm / epsilon), torch.zeros_like(norm))
            lyapunov_blocks += valid.to(torch.int32)
            scale = torch.where(valid, epsilon / norm, torch.ones_like(norm))
            perturbed = base + difference * scale[:, None]
            recent = torch.as_tensor((pointer - np.arange(1, delta + 1)) % history_length, device=device)
            rolling_base = base[:, recent].sum(dim=1)
            rolling_perturbed = perturbed[:, recent].sum(dim=1)

        if (step + 1) % 1024 == 0 and stop_requested is not None and stop_requested():
            end_step = step + 1
            break

    if checkpoint is not None:
        target = Path(checkpoint)
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(target.name + ".tmp")
        torch.save({
            "identity": identity, "step": end_step, "pointer": pointer,
            "tensors": {"base": base, "perturbed": perturbed,
                "rolling_base": rolling_base, "rolling_perturbed": rolling_perturbed,
                "max_abs": max_abs, "escaped": escaped, "first_escape": first_escape,
                "lyapunov_sum": lyapunov_sum, "lyapunov_blocks": lyapunov_blocks},
        }, temporary)
        os.replace(temporary, target)
    exponent = lyapunov_sum / (lyapunov_blocks.clamp_min(1).to(dtype) * RENORMALIZE_EVERY)
    result = {
        "initial_history_names": np.asarray(names, dtype="U32"),
        "mean_history": base.mean(dim=1).reshape(output_shape).cpu().numpy(),
        "last_value": base[:, (pointer - 1) % history_length].reshape(output_shape).cpu().numpy(),
        "rolling_mean": (rolling_base / delta).reshape(output_shape).cpu().numpy(),
        "alpha": ALPHAS,
        "beta": BETAS,
        "max_abs": max_abs.reshape(output_shape).cpu().numpy(),
        "escaped": escaped.reshape(output_shape).cpu().numpy(),
        "first_escape_step": first_escape.reshape(output_shape).cpu().numpy(),
        "lyapunov_per_step": exponent.reshape(output_shape).cpu().numpy(),
        "lyapunov_blocks": lyapunov_blocks.reshape(output_shape).cpu().numpy(),
    }
    return (result, end_step) if return_progress else result
