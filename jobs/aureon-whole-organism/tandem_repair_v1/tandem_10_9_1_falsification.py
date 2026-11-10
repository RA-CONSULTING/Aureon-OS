#!/usr/bin/env python3
"""One FP64 shard of the Tandem 10-9-1 synthetic identifiability campaign.

This program tests whether a declared cross-domain echo is distinguishable
from the pinned HNC single-domain recurrence and registered negative controls.
It does not ingest physical measurements and cannot produce an ontological
verdict.
"""

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


SCHEMA = "tandem-10-9-1-identifiability-shard/v1"
CLAIM_CLASS = "computational_simulation"
EVIDENCE_BOUNDARY = (
    "Synthetic sensitivity and false-positive calibration for a candidate 10-9-1 "
    "echo signature. This is not a physical observation, independent replication, "
    "or proof that reality contains timeline branches."
)
FS = 1000.0
ALPHA = 0.85
BETA = 0.90
GAINS = (0.75, 1.50)
TAU_STEPS = (10, 25, 50, 100)
DELTA_STEPS = (1, 10, 50, 100)
FREQUENCIES = np.asarray(
    [
        7.83, 14.3, 20.8, 27.3, 33.8, 39.0, 45.0, 111.0, 174.0,
        188.0, 285.0, 396.0, 417.0, 528.0, 639.0, 741.0, 852.0, 963.0,
    ],
    dtype=np.float64,
)
WEIGHTS = 1.0 / (1.0 + np.log(FREQUENCIES / 7.83))
WEIGHTS /= WEIGHTS.sum()
ETA_LEVELS = np.asarray([0.0, 0.002, 0.005, 0.01, 0.02, 0.05, 0.10, 0.20], dtype=np.float64)
SNR_LEVELS_DB = np.asarray([-10.0, 0.0, 10.0, 20.0], dtype=np.float64)
OPERATORS = ("source_lock", "echo_coherence", "minimum_action")
NOISE_MODELS = ("white", "ar1_0p9", "two_timescale")
TRUTH_MODELS = ("h0_delay", "h0_phase_mix", "h1_echo")


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
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (float, np.floating)):
        number = float(value)
        return number if math.isfinite(number) else None
    return value


def shard_parameters(shard: int) -> tuple[float, int, int]:
    if not 0 <= shard < 32:
        raise ValueError("shard must be in 0..31")
    gain_index = shard // 16
    within = shard % 16
    tau_index = within // 4
    delta_index = within % 4
    return GAINS[gain_index], TAU_STEPS[tau_index], DELTA_STEPS[delta_index]


def normalised_corr(a: torch.Tensor, b: torch.Tensor, dim: int = -1) -> torch.Tensor:
    a0 = a - a.mean(dim=dim, keepdim=True)
    b0 = b - b.mean(dim=dim, keepdim=True)
    numerator = (a0 * b0).sum(dim=dim)
    denominator = torch.sqrt((a0.square().sum(dim=dim) * b0.square().sum(dim=dim)).clamp_min(1.0e-24))
    return numerator / denominator


def build_forcing(phases: torch.Tensor, steps: int, device: torch.device) -> torch.Tensor:
    """Return HNC substrate forcing for phase tensors [batch, branches, modes]."""
    dtype = torch.float64
    times = torch.arange(steps, device=device, dtype=dtype) / FS
    freqs = torch.as_tensor(FREQUENCIES, device=device, dtype=dtype)
    weights = torch.as_tensor(WEIGHTS, device=device, dtype=dtype)
    angles = 2.0 * math.pi * freqs[:, None] * times[None, :]
    sin_basis = torch.sin(angles) * weights[:, None]
    cos_basis = torch.cos(angles) * weights[:, None]
    flat = phases.reshape(-1, phases.shape[-1])
    forcing = torch.cos(flat) @ sin_basis + torch.sin(flat) @ cos_basis
    return forcing.reshape(phases.shape[0], phases.shape[1], steps)


def run_hnc_branches(
    forcing: torch.Tensor,
    gain: float,
    tau: int,
    delta: int,
) -> torch.Tensor:
    """Run the pinned discrete HNC recurrence for every sampled phase domain."""
    batch, branches, steps = forcing.shape
    history_length = max(tau, delta) + 1
    history = torch.zeros((batch, branches, history_length), device=forcing.device, dtype=forcing.dtype)
    rolling = torch.zeros((batch, branches), device=forcing.device, dtype=forcing.dtype)
    series = torch.empty_like(forcing)
    pointer = 0
    for step in range(steps):
        echo_index = (pointer - tau) % history_length
        outgoing_index = (pointer - delta) % history_length
        value = forcing[:, :, step] + ALPHA * torch.tanh(gain * rolling / delta) + BETA * history[:, :, echo_index]
        if not torch.isfinite(value).all():
            raise FloatingPointError("non-finite HNC recurrence value")
        outgoing = history[:, :, outgoing_index].clone()
        history[:, :, pointer] = value
        rolling += value - outgoing
        series[:, :, step] = value
        pointer = (pointer + 1) % history_length
    return series


def ar_noise(white: torch.Tensor, rho: float) -> torch.Tensor:
    result = torch.empty_like(white)
    result[:, 0] = white[:, 0]
    scale = math.sqrt(max(1.0e-12, 1.0 - rho * rho))
    for step in range(1, white.shape[1]):
        result[:, step] = rho * result[:, step - 1] + scale * white[:, step]
    return result


def make_unit_noise(batch: int, steps: int, model_ids: torch.Tensor, generator: torch.Generator) -> torch.Tensor:
    device = model_ids.device
    white = torch.randn((batch, steps), generator=generator, device=device, dtype=torch.float64)
    ar09 = ar_noise(torch.randn((batch, steps), generator=generator, device=device, dtype=torch.float64), 0.90)
    slow = ar_noise(torch.randn((batch, steps), generator=generator, device=device, dtype=torch.float64), 0.97)
    fast = ar_noise(torch.randn((batch, steps), generator=generator, device=device, dtype=torch.float64), 0.45)
    coloured = 0.65 * slow + 0.35 * fast
    result = white.clone()
    result = torch.where((model_ids == 1)[:, None], ar09, result)
    result = torch.where((model_ids == 2)[:, None], coloured, result)
    result -= result.mean(dim=1, keepdim=True)
    result /= result.square().mean(dim=1, keepdim=True).sqrt().clamp_min(1.0e-12)
    return result


def orthogonal_echo(
    echo_raw: torch.Tensor,
    selected: torch.Tensor,
    source10: torch.Tensor,
    tau: int,
    valid_start: int,
) -> torch.Tensor:
    """Remove registered single-domain nuisance components from the echo template."""
    delayed = torch.zeros_like(selected)
    delayed[:, tau:] = selected[:, :-tau]
    x = torch.stack(
        [torch.ones_like(selected), selected, source10, delayed],
        dim=-1,
    )[:, valid_start:, :]
    y = echo_raw[:, valid_start:, None]
    xtx = x.transpose(1, 2) @ x
    ridge = 1.0e-8 * torch.eye(xtx.shape[-1], device=xtx.device, dtype=xtx.dtype)[None, :, :]
    coeff = torch.linalg.solve(xtx + ridge, x.transpose(1, 2) @ y)
    residual = y - x @ coeff
    result = torch.zeros_like(echo_raw)
    result[:, valid_start:] = residual[:, :, 0]
    return result


def run_batch(
    *,
    shard: int,
    trial_offset: int,
    batch: int,
    steps: int,
    branches: int,
    gain: float,
    tau: int,
    delta: int,
    device: torch.device,
    generator: torch.Generator,
) -> dict[str, np.ndarray]:
    dtype = torch.float64
    mode_count = len(FREQUENCIES)
    global_ids = shard * 10_000_000 + trial_offset + torch.arange(batch, device=device, dtype=torch.int64)
    eta_ids = global_ids % len(ETA_LEVELS)
    snr_ids = (global_ids // len(ETA_LEVELS)) % len(SNR_LEVELS_DB)
    noise_ids = (global_ids // (len(ETA_LEVELS) * len(SNR_LEVELS_DB))) % len(NOISE_MODELS)
    operator_ids = (
        global_ids // (len(ETA_LEVELS) * len(SNR_LEVELS_DB) * len(NOISE_MODELS))
    ) % len(OPERATORS)
    truth_model_ids = (
        global_ids // (
            len(ETA_LEVELS) * len(SNR_LEVELS_DB) * len(NOISE_MODELS) * len(OPERATORS)
        )
    ) % len(TRUTH_MODELS)
    split_ids = (
        global_ids // (
            len(ETA_LEVELS) * len(SNR_LEVELS_DB) * len(NOISE_MODELS)
            * len(OPERATORS) * len(TRUTH_MODELS)
        )
    ) % 2
    eta = torch.as_tensor(ETA_LEVELS, device=device, dtype=dtype)[eta_ids]
    snr_db = torch.as_tensor(SNR_LEVELS_DB, device=device, dtype=dtype)[snr_ids]

    base_phases = 2.0 * math.pi * torch.rand(
        (batch, 1, mode_count), generator=generator, device=device, dtype=dtype
    )
    offsets = 2.0 * math.pi * (
        torch.rand((batch, branches, mode_count), generator=generator, device=device, dtype=dtype) - 0.5
    )
    offsets[:, 0, :] = 0.0
    possibility_phases = base_phases + offsets
    source10 = build_forcing(base_phases, steps, device)[:, 0, :]
    possibility_forcing = build_forcing(possibility_phases, steps, device)
    possibilities = run_hnc_branches(possibility_forcing, gain, tau, delta)

    train_start = max(2 * max(tau, delta), steps // 8)
    split = steps // 2
    if split - train_start <= max(tau, 32):
        raise ValueError("insufficient training segment for registered scores")
    train = possibilities[:, :, train_start:split]
    source_train = source10[:, train_start:split]
    source_score = normalised_corr(train, source_train[:, None, :])
    echo_score = normalised_corr(
        possibilities[:, :, train_start + tau:split],
        possibilities[:, :, train_start:split - tau],
    )
    velocity = torch.diff(train, dim=-1)
    action_score = -velocity.square().mean(dim=-1) / train.square().mean(dim=-1).clamp_min(1.0e-12)
    all_scores = torch.stack([source_score, echo_score, action_score], dim=1)
    chosen_score = all_scores[torch.arange(batch, device=device), operator_ids, :]
    selected_index = torch.argmax(chosen_score, dim=1)
    selected = torch.gather(
        possibilities,
        1,
        selected_index[:, None, None].expand(-1, 1, steps),
    )[:, 0, :]

    standardized = (chosen_score - chosen_score.mean(dim=1, keepdim=True)) / chosen_score.std(
        dim=1, keepdim=True
    ).clamp_min(1.0e-8)
    echo_weights = torch.softmax(standardized, dim=1)
    delayed_possibilities = torch.zeros_like(possibilities)
    lag_span = max(1, tau // 4)
    for branch in range(branches):
        lag = tau + (branch % lag_span)
        delayed_possibilities[:, branch, lag:] = possibilities[:, branch, :-lag]
    echo_raw = (echo_weights[:, :, None] * delayed_possibilities).sum(dim=1)
    phase_mix_raw = (echo_weights[:, :, None] * possibilities).sum(dim=1)
    valid_start = max(train_start, tau + lag_span)
    echo = orthogonal_echo(echo_raw, selected, source10, tau, valid_start)
    phase_mix = orthogonal_echo(phase_mix_raw, selected, source10, tau, valid_start)

    test_slice = slice(split, steps)
    selected_rms = selected[:, test_slice].square().mean(dim=1).sqrt().clamp_min(1.0e-10)
    echo_rms = echo[:, test_slice].square().mean(dim=1).sqrt().clamp_min(1.0e-10)
    echo_scaled = echo / echo_rms[:, None] * selected_rms[:, None]
    phase_mix_rms = phase_mix[:, test_slice].square().mean(dim=1).sqrt().clamp_min(1.0e-10)
    phase_mix_scaled = phase_mix / phase_mix_rms[:, None] * selected_rms[:, None]
    unit_noise = make_unit_noise(batch, steps, noise_ids, generator)
    noise_sigma = selected_rms / torch.pow(torch.tensor(10.0, device=device, dtype=dtype), snr_db / 20.0)
    injected = torch.zeros_like(selected)
    injected = torch.where((truth_model_ids == 1)[:, None], phase_mix_scaled, injected)
    injected = torch.where((truth_model_ids == 2)[:, None], echo_scaled, injected)
    observation = selected + eta[:, None] * injected + noise_sigma[:, None] * unit_noise
    residual = observation - selected

    true_template = echo_scaled[:, test_slice]
    residual_test = residual[:, test_slice]
    shift = min(true_template.shape[1] // 3, 3 * tau + 17)
    shifted_template = torch.roll(true_template, shifts=shift, dims=1)
    corr_true = normalised_corr(residual_test, true_template)
    corr_shift = normalised_corr(residual_test, shifted_template).abs()
    discriminant = corr_true - corr_shift
    eta_hat = (residual_test * true_template).sum(dim=1) / true_template.square().sum(dim=1).clamp_min(1.0e-24)

    return {
        "trial_id": global_ids.cpu().numpy(),
        "eta": eta.cpu().numpy(),
        "snr_db": snr_db.cpu().numpy(),
        "noise_model": noise_ids.cpu().numpy(),
        "operator": operator_ids.cpu().numpy(),
        "truth_model": truth_model_ids.cpu().numpy(),
        "null_split": split_ids.cpu().numpy(),
        "selected_branch": selected_index.cpu().numpy(),
        "corr_true": corr_true.cpu().numpy(),
        "corr_shift": corr_shift.cpu().numpy(),
        "discriminant": discriminant.cpu().numpy(),
        "eta_hat": eta_hat.cpu().numpy(),
    }


def summarise(arrays: dict[str, np.ndarray]) -> dict[str, Any]:
    eta = arrays["eta"]
    score = arrays["discriminant"]
    alternative = (arrays["truth_model"] == 2) & (eta > 0.0)
    null = ~alternative
    calibration = null & (arrays["null_split"] == 0)
    evaluation = null & (arrays["null_split"] == 1)
    if calibration.sum() < 20 or evaluation.sum() < 20:
        raise RuntimeError("insufficient separated null trials")
    threshold = float(np.quantile(score[calibration], 0.99))
    fpr = float(np.mean(score[evaluation] > threshold))
    powers: dict[str, float] = {}
    for level in ETA_LEVELS[1:]:
        mask = alternative & np.isclose(eta, level)
        powers[f"{level:.3f}"] = float(np.mean(score[mask] > threshold))
    target = alternative & (eta >= 0.05) & (arrays["snr_db"] >= 0.0)
    target_power = float(np.mean(score[target] > threshold))
    shifted_win_rate = float(np.mean(arrays["corr_true"][alternative] > arrays["corr_shift"][alternative]))
    null_fpr_by_model = {
        TRUTH_MODELS[model]: float(np.mean(score[(arrays["truth_model"] == model) & evaluation] > threshold))
        for model in range(len(TRUTH_MODELS))
        if np.any((arrays["truth_model"] == model) & evaluation)
    }
    return {
        "threshold_from_calibration_null_p99": threshold,
        "held_out_null_false_positive_rate": fpr,
        "power_by_eta": powers,
        "target_power_eta_ge_0p05_snr_ge_0db": target_power,
        "correct_template_beats_shifted_rate_nonzero_eta": shifted_win_rate,
        "held_out_null_fpr_by_truth_model": null_fpr_by_model,
        "shard_gate": bool(fpr <= 0.015 and target_power >= 0.80 and shifted_win_rate > 0.50),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--shard", type=int, required=True)
    parser.add_argument("--output-prefix", required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--paper", required=True)
    parser.add_argument("--repo-implementation", required=True)
    parser.add_argument("--protocol", required=True)
    parser.add_argument("--trials", type=int, default=6144)
    parser.add_argument("--steps", type=int, default=2048)
    parser.add_argument("--branch-samples", type=int, default=16)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--device", choices=("cuda", "cpu"), default="cuda")
    args = parser.parse_args()
    if args.trials <= 0 or args.steps < 512 or args.branch_samples < 4 or args.batch_size <= 0:
        raise ValueError("invalid simulation scale")
    if args.device == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA is required for the production run")

    device = torch.device(args.device)
    gain, tau, delta = shard_parameters(args.shard)
    output_prefix = Path(args.output_prefix).resolve()
    output_prefix.parent.mkdir(parents=True, exist_ok=True)
    paper = Path(args.paper).resolve()
    implementation = Path(args.repo_implementation).resolve()
    protocol = Path(args.protocol).resolve()
    for required in (paper, implementation, protocol):
        if not required.is_file():
            raise FileNotFoundError(required)

    generator = torch.Generator(device=device)
    generator.manual_seed(10_901_000 + args.shard)
    outputs: dict[str, list[np.ndarray]] = {}
    started = time.perf_counter()
    for offset in range(0, args.trials, args.batch_size):
        current = min(args.batch_size, args.trials - offset)
        batch = run_batch(
            shard=args.shard,
            trial_offset=offset,
            batch=current,
            steps=args.steps,
            branches=args.branch_samples,
            gain=gain,
            tau=tau,
            delta=delta,
            device=device,
            generator=generator,
        )
        for key, values in batch.items():
            outputs.setdefault(key, []).append(values)
    arrays = {key: np.concatenate(chunks) for key, chunks in outputs.items()}
    elapsed = time.perf_counter() - started
    if any(values.shape[0] != args.trials for values in arrays.values()):
        raise RuntimeError("trial-count mismatch")
    if any(not np.isfinite(values).all() for key, values in arrays.items() if key not in {"trial_id", "noise_model", "operator", "null_split", "selected_branch"}):
        raise FloatingPointError("non-finite result array")

    npz_path = output_prefix.with_suffix(".npz")
    np.savez_compressed(npz_path, **arrays)
    summary = summarise(arrays)
    receipt = {
        "schema": SCHEMA,
        "claim_class": CLAIM_CLASS,
        "evidence_boundary": EVIDENCE_BOUNDARY,
        "authoritative_mapping": {
            "10": "Source / Harmonic Fish / finite harmonic potential",
            "9": "Possibility Sea / Phase Fish / sampled phase-domain possibilities",
            "1": "Realised Now / Motion Fish / selected trajectory containing candidate echoes",
        },
        "shard": args.shard,
        "source_commit": args.source_commit,
        "parameters": {
            "alpha": ALPHA,
            "beta": BETA,
            "gain": gain,
            "tau_steps": tau,
            "delta_steps": delta,
            "sample_rate_hz": FS,
            "trials": args.trials,
            "steps": args.steps,
            "branch_samples": args.branch_samples,
            "precision": "float64",
            "operators": OPERATORS,
            "noise_models": NOISE_MODELS,
            "truth_models": TRUTH_MODELS,
            "eta_levels": ETA_LEVELS,
            "snr_levels_db": SNR_LEVELS_DB,
        },
        "registered_gates": {
            "held_out_null_fpr_max": 0.015,
            "power_min_eta_ge_0p05_snr_ge_0db": 0.80,
            "correct_template_win_rate_min": 0.50,
        },
        "summary": summary,
        "inputs": {
            "paper_sha256": sha256_file(paper),
            "implementation_sha256": sha256_file(implementation),
            "protocol_sha256": sha256_file(protocol),
            "harness_sha256": sha256_file(Path(__file__).resolve()),
        },
        "output": {"npz": str(npz_path), "npz_sha256": sha256_file(npz_path)},
        "runtime": {
            "elapsed_seconds": elapsed,
            "device": str(device),
            "device_name": torch.cuda.get_device_name(0) if device.type == "cuda" else platform.processor(),
            "torch": torch.__version__,
            "cuda": torch.version.cuda,
            "python": platform.python_version(),
            "slurm_job_id": os.environ.get("SLURM_JOB_ID"),
            "array_job_id": os.environ.get("SLURM_ARRAY_JOB_ID"),
            "array_task_id": os.environ.get("SLURM_ARRAY_TASK_ID"),
        },
    }
    receipt_path = output_prefix.with_suffix(".json")
    receipt_path.write_text(
        json.dumps(serializable(receipt), indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(serializable(receipt), indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
