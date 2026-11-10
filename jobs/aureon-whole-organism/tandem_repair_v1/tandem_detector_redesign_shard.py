#!/usr/bin/env python3
"""Detector-redesign shard for the Tandem 10-9-1 synthetic identifiability benchmark.

Registry entry: "Detector redesign or larger-eta regime before any Stage 2".

This program reuses the pre-registered Stage 1 data-generating process EXACTLY:
the registered harness module is imported read-only and every DGP primitive
(build_forcing, run_hnc_branches, make_unit_noise, orthogonal_echo,
normalised_corr) is the registered code object. The run_batch body below is a
statement-for-statement copy of the registered run_batch up to and including
the original return-dict construction; only AFTER that point are additional
detector statistics computed. No RNG is consumed outside the registered draw
sequence, so with the same seed, device, batch size and trial count the
synthetic trials are bit-identical to Stage 1.

Detectors computed per trial (test slice only):
  D0  pre-registered discriminant (control): corr_true - |corr_shift|
  D1  matched filter / signed GLRT t-statistic with the exact template
  D2  cross-correlation peak over a circular lag sweep around the delay
  D3  spectral-comb (real-cepstrum) detector at the registered delay quefrency
  D4  windowed feature vector for a downstream learned detector (trained only
      on training-fold synthetics in the aggregate job)

This is a synthetic identifiability calculation. It ingests no physical
measurement and cannot prove that physical reality branches.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
import platform
import time
from pathlib import Path
from typing import Any

import numpy as np
import torch


REGISTERED_HARNESS_PATH = "/projects/u6vs/hnc-organism/jobs/tandem_10_9_1_falsification.py"
SCHEMA = "tandem-detector-redesign-shard/v1"
CLAIM_CLASS = "computational_simulation"
INTERPRETATION_BOUNDARY = (
    "Synthetic detector-benchmark identifiability only: detector statistics are computed on the "
    "pre-registered synthetic data-generating process. This is not a physical observation, not "
    "independent replication, and cannot prove branching of physical reality."
)
FEATURE_NAMES = [
    "corr_true",
    "corr_shift_abs",
    "discriminant",
    "eta_hat",
    "d1_glrt_t",
    "d2_xcf_max",
    "d2_argmax_lag_norm",
    "d2_xcf_prominence",
    "d3_cepstral_z_tau",
    "residual_std",
    "residual_log_std",
    "residual_lag1_autocorr",
    "residual_skew",
    "residual_kurtosis",
    "spectral_centroid_norm",
    "bandpower_low_ratio",
    "bandpower_mid_ratio",
    "bandpower_high_ratio",
]


def load_registered_harness(path: str):
    spec = importlib.util.spec_from_file_location("tandem_10_9_1_registered", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


REG = load_registered_harness(REGISTERED_HARNESS_PATH)


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


def run_batch_redesign(
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
    """Registered DGP (verbatim copy) + appended detector statistics.

    The body up to the original return dict mirrors the registered run_batch
    statement for statement, calling the registered module's own functions so
    the synthetic data-generating process is byte-for-byte the registered code.
    """
    dtype = torch.float64
    mode_count = len(REG.FREQUENCIES)
    global_ids = shard * 10_000_000 + trial_offset + torch.arange(batch, device=device, dtype=torch.int64)
    eta_ids = global_ids % len(REG.ETA_LEVELS)
    snr_ids = (global_ids // len(REG.ETA_LEVELS)) % len(REG.SNR_LEVELS_DB)
    noise_ids = (global_ids // (len(REG.ETA_LEVELS) * len(REG.SNR_LEVELS_DB))) % len(REG.NOISE_MODELS)
    operator_ids = (
        global_ids // (len(REG.ETA_LEVELS) * len(REG.SNR_LEVELS_DB) * len(REG.NOISE_MODELS))
    ) % len(REG.OPERATORS)
    truth_model_ids = (
        global_ids // (
            len(REG.ETA_LEVELS) * len(REG.SNR_LEVELS_DB) * len(REG.NOISE_MODELS) * len(REG.OPERATORS)
        )
    ) % len(REG.TRUTH_MODELS)
    split_ids = (
        global_ids // (
            len(REG.ETA_LEVELS) * len(REG.SNR_LEVELS_DB) * len(REG.NOISE_MODELS)
            * len(REG.OPERATORS) * len(REG.TRUTH_MODELS)
        )
    ) % 2
    eta = torch.as_tensor(REG.ETA_LEVELS, device=device, dtype=dtype)[eta_ids]
    snr_db = torch.as_tensor(REG.SNR_LEVELS_DB, device=device, dtype=dtype)[snr_ids]

    base_phases = 2.0 * math.pi * torch.rand(
        (batch, 1, mode_count), generator=generator, device=device, dtype=dtype
    )
    offsets = 2.0 * math.pi * (
        torch.rand((batch, branches, mode_count), generator=generator, device=device, dtype=dtype) - 0.5
    )
    offsets[:, 0, :] = 0.0
    possibility_phases = base_phases + offsets
    source10 = REG.build_forcing(base_phases, steps, device)[:, 0, :]
    possibility_forcing = REG.build_forcing(possibility_phases, steps, device)
    possibilities = REG.run_hnc_branches(possibility_forcing, gain, tau, delta)

    train_start = max(2 * max(tau, delta), steps // 8)
    split = steps // 2
    if split - train_start <= max(tau, 32):
        raise ValueError("insufficient training segment for registered scores")
    train = possibilities[:, :, train_start:split]
    source_train = source10[:, train_start:split]
    source_score = REG.normalised_corr(train, source_train[:, None, :])
    echo_score = REG.normalised_corr(
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
    echo = REG.orthogonal_echo(echo_raw, selected, source10, tau, valid_start)
    phase_mix = REG.orthogonal_echo(phase_mix_raw, selected, source10, tau, valid_start)

    test_slice = slice(split, steps)
    selected_rms = selected[:, test_slice].square().mean(dim=1).sqrt().clamp_min(1.0e-10)
    echo_rms = echo[:, test_slice].square().mean(dim=1).sqrt().clamp_min(1.0e-10)
    echo_scaled = echo / echo_rms[:, None] * selected_rms[:, None]
    phase_mix_rms = phase_mix[:, test_slice].square().mean(dim=1).sqrt().clamp_min(1.0e-10)
    phase_mix_scaled = phase_mix / phase_mix_rms[:, None] * selected_rms[:, None]
    unit_noise = REG.make_unit_noise(batch, steps, noise_ids, generator)
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
    corr_true = REG.normalised_corr(residual_test, true_template)
    corr_shift = REG.normalised_corr(residual_test, shifted_template).abs()
    discriminant = corr_true - corr_shift
    eta_hat = (residual_test * true_template).sum(dim=1) / true_template.square().sum(dim=1).clamp_min(1.0e-24)

    # ------------------------------------------------------------------
    # Detector-redesign battery. No RNG is consumed below this line; the
    # registered trial stream above is therefore identical to Stage 1.
    # ------------------------------------------------------------------
    n_test = residual_test.shape[1]
    rc = residual_test - residual_test.mean(dim=1, keepdim=True)
    sc = true_template - true_template.mean(dim=1, keepdim=True)
    rc_norm = rc.square().sum(dim=1).sqrt().clamp_min(1.0e-24)
    sc_norm = sc.square().sum(dim=1).sqrt().clamp_min(1.0e-24)
    denom = (rc_norm * sc_norm).clamp_min(1.0e-24)

    # D1: matched filter / signed GLRT. Known template, unknown amplitude and
    # unknown noise level: the GLRT is the t-statistic of the template
    # regression coefficient, a monotone map of the signed correlation.
    rho_d1 = corr_true.clamp(-1.0 + 1.0e-12, 1.0 - 1.0e-12)
    d1_glrt_t = rho_d1 * math.sqrt(n_test - 2) / torch.sqrt((1.0 - rho_d1 * rho_d1).clamp_min(1.0e-24))

    # D2: cross-correlation peak over a circular lag sweep around the
    # pre-registered delay. Sweep half-width equals the registered shifted
    # control scale 3*tau+17. Computed exactly by FFT circular correlation,
    # consistent with the harness's own torch.roll convention.
    xcf_half = 3 * tau + 17
    spec_r = torch.fft.rfft(rc, dim=1)
    spec_s = torch.fft.rfft(sc, dim=1)
    ccf = torch.fft.irfft(spec_r * torch.conj(spec_s), n=n_test, dim=1) / denom[:, None]
    col_index = torch.cat(
        [
            torch.arange(0, xcf_half + 1, device=device),
            torch.arange(n_test - xcf_half, n_test, device=device),
        ]
    )
    lag_values = torch.cat(
        [
            torch.arange(0, xcf_half + 1, device=device),
            torch.arange(-xcf_half, 0, device=device),
        ]
    )
    xcf = ccf[:, col_index]
    d2_xcf_max = xcf.max(dim=1).values
    d2_argmax_lag = lag_values[xcf.argmax(dim=1)].to(dtype)
    d2_xcf_median = xcf.median(dim=1).values
    d2_xcf_prominence = d2_xcf_max - d2_xcf_median
    d2_xcf0 = ccf[:, 0]
    d2_xcf_shift = ccf[:, shift]

    # D3: spectral-comb detector. A delay-and-add echo imprints a cos(omega*tau)
    # ripple on the log spectrum, i.e. a real-cepstrum peak at quefrency tau.
    # Statistic: robust z-score of the cepstral peak at quefrency tau (+-2 bins)
    # against the cepstrum body; control at an off-delay quefrency.
    log_mag = torch.log(spec_r.abs().clamp_min(1.0e-12))
    cep = torch.fft.irfft(log_mag, n=n_test, dim=1)
    q_lo = 8
    q_hi = n_test // 4
    body = cep[:, q_lo:q_hi]
    cep_med = body.median(dim=1, keepdim=True).values
    cep_mad = (body - cep_med).abs().median(dim=1, keepdim=True).values
    cep_scale = (1.4826 * cep_mad).clamp_min(1.0e-12)

    def cepstral_z(quefrency: int) -> torch.Tensor:
        window = cep[:, quefrency - 2:quefrency + 3]
        return ((window - cep_med) / cep_scale).max(dim=1).values

    d3_cepstral_z_tau = cepstral_z(tau)
    d3_cepstral_z_control = cepstral_z(2 * tau + 13)

    # D4 feature vector: windowed statistics of the residual and its relation
    # to the registered template. Stratum labels are deliberately excluded.
    residual_std = rc.std(dim=1).clamp_min(1.0e-24)
    residual_log_std = torch.log(residual_std)
    residual_lag1 = (rc[:, 1:] * rc[:, :-1]).sum(dim=1) / rc.square().sum(dim=1).clamp_min(1.0e-24)
    m3 = (rc**3).mean(dim=1)
    m4 = (rc**4).mean(dim=1)
    residual_skew = m3 / residual_std.pow(3)
    residual_kurtosis = m4 / residual_std.pow(4)
    psd = spec_r.abs().square()
    freqs_hz = torch.fft.rfftfreq(n_test, d=1.0 / REG.FS, device=device, dtype=dtype)
    psd_total = psd.sum(dim=1).clamp_min(1.0e-24)
    spectral_centroid_norm = (psd * freqs_hz[None, :]).sum(dim=1) / psd_total / (REG.FS / 2.0)
    band_low = (freqs_hz >= 0.0) & (freqs_hz < 50.0)
    band_mid = (freqs_hz >= 50.0) & (freqs_hz < 200.0)
    band_high = (freqs_hz >= 200.0) & (freqs_hz <= 500.0)
    bandpower_low_ratio = psd[:, band_low].sum(dim=1) / psd_total
    bandpower_mid_ratio = psd[:, band_mid].sum(dim=1) / psd_total
    bandpower_high_ratio = psd[:, band_high].sum(dim=1) / psd_total
    d2_argmax_lag_norm = d2_argmax_lag / float(xcf_half)
    features = torch.stack(
        [
            corr_true,
            corr_shift,
            discriminant,
            eta_hat,
            d1_glrt_t,
            d2_xcf_max,
            d2_argmax_lag_norm,
            d2_xcf_prominence,
            d3_cepstral_z_tau,
            residual_std,
            residual_log_std,
            residual_lag1,
            residual_skew,
            residual_kurtosis,
            spectral_centroid_norm,
            bandpower_low_ratio,
            bandpower_mid_ratio,
            bandpower_high_ratio,
        ],
        dim=1,
    )

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
        "d1_glrt_t": d1_glrt_t.cpu().numpy(),
        "d2_xcf_max": d2_xcf_max.cpu().numpy(),
        "d2_argmax_lag": d2_argmax_lag.cpu().numpy(),
        "d2_xcf_prominence": d2_xcf_prominence.cpu().numpy(),
        "d2_xcf0": d2_xcf0.cpu().numpy(),
        "d2_xcf_shift": d2_xcf_shift.cpu().numpy(),
        "d3_cepstral_z_tau": d3_cepstral_z_tau.cpu().numpy(),
        "d3_cepstral_z_control": d3_cepstral_z_control.cpu().numpy(),
        "d4_features": features.cpu().numpy(),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--shard", type=int, required=True)
    parser.add_argument("--output-prefix", required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--paper", required=True)
    parser.add_argument("--repo-implementation", required=True)
    parser.add_argument("--protocol", required=True)
    parser.add_argument("--trials", type=int, default=10368)
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
    gain, tau, delta = REG.shard_parameters(args.shard)
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
        batch = run_batch_redesign(
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
    one_d_keys = [key for key, values in arrays.items() if values.ndim == 1]
    if any(values.shape[0] != args.trials for values in arrays.values()):
        raise RuntimeError("trial-count mismatch")
    if arrays["d4_features"].shape != (args.trials, len(FEATURE_NAMES)):
        raise RuntimeError("feature-matrix shape mismatch")
    if any(
        not np.isfinite(values).all()
        for key, values in arrays.items()
        if key not in {"trial_id", "noise_model", "operator", "null_split", "selected_branch"}
    ):
        raise FloatingPointError("non-finite result array")

    npz_path = output_prefix.with_suffix(".npz")
    np.savez_compressed(npz_path, **arrays)
    receipt = {
        "schema": SCHEMA,
        "claim_class": CLAIM_CLASS,
        "interpretation_boundary": INTERPRETATION_BOUNDARY,
        "benchmark": "detector-redesign",
        "registry_entry": "Detector redesign or larger-eta regime before any Stage 2",
        "dgp_statement": (
            "The synthetic data-generating process is the pre-registered Stage 1 harness imported "
            "read-only; the run_batch body is a verbatim copy up to the original return dict; no RNG "
            "is consumed by the appended detector statistics."
        ),
        "shard": args.shard,
        "source_commit": args.source_commit,
        "parameters": {
            "alpha": REG.ALPHA,
            "beta": REG.BETA,
            "gain": gain,
            "tau_steps": tau,
            "delta_steps": delta,
            "sample_rate_hz": REG.FS,
            "trials": args.trials,
            "steps": args.steps,
            "branch_samples": args.branch_samples,
            "precision": "float64",
            "operators": REG.OPERATORS,
            "noise_models": REG.NOISE_MODELS,
            "truth_models": REG.TRUTH_MODELS,
            "eta_levels": REG.ETA_LEVELS,
            "snr_levels_db": REG.SNR_LEVELS_DB,
            "d2_lag_sweep_halfwidth_steps": 3 * tau + 17,
            "d3_cepstral_body_quefrency_range": [8, args.steps // 8],
            "d4_feature_names": FEATURE_NAMES,
        },
        "registered_gates": {
            "held_out_null_fpr_max": 0.015,
            "power_min_eta_ge_0p05_snr_ge_0db": 0.80,
            "correct_template_win_rate_min": 0.50,
        },
        "inputs": {
            "paper_sha256": sha256_file(paper),
            "implementation_sha256": sha256_file(implementation),
            "protocol_sha256": sha256_file(protocol),
            "registered_harness_sha256": sha256_file(Path(REGISTERED_HARNESS_PATH).resolve()),
            "redesign_harness_sha256": sha256_file(Path(__file__).resolve()),
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
