#!/usr/bin/env python3
"""Falsification-grade benchmark for the tabled HNC Harmonic LiDAR filter.

Outputs from this program are reference arithmetic, simulations, or descriptive
transformations of SRTM elevations. They are never physical measurements or
independent proof of subsurface material.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import random
import time
from pathlib import Path
from typing import Any

import torch


SCHEMA = "hnc-harmonic-lidar-benchmark/v1"
PHI = (1.0 + math.sqrt(5.0)) / 2.0
PHI2 = PHI * PHI
OUTER_RADIUS_M = 15000.0
TABLE_SHELLS = 10
BANDWIDTH_FRACTION = 0.25
BOUNDARY = (
    "Synthetic or SRTM results are not physical measurements, independent "
    "validation, proof of a subsurface deposit, an excavation recommendation, "
    "or evidence of extractable energy."
)
NUISANCE_NAMES = [
    "spectral_terrain",
    "planar_slope",
    "directional_ridge",
    "missing_patch",
    "resampling_blur",
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def environment(device: torch.device, dtype: torch.dtype) -> dict[str, Any]:
    gpu_name = None
    if device.type == "cuda":
        gpu_name = torch.cuda.get_device_name(device)
    return {
        "hostname": platform.node(),
        "python": platform.python_version(),
        "torch": torch.__version__,
        "device": str(device),
        "gpu_name": gpu_name,
        "dtype": str(dtype).replace("torch.", ""),
        "slurm_job_id": os.environ.get("SLURM_JOB_ID"),
        "slurm_array_job_id": os.environ.get("SLURM_ARRAY_JOB_ID"),
        "slurm_array_task_id": os.environ.get("SLURM_ARRAY_TASK_ID"),
    }


def shell_spec(ratio: float = PHI2, count: int = TABLE_SHELLS) -> list[dict[str, float]]:
    rows = []
    for n in range(count):
        radius = OUTER_RADIUS_M / (ratio**n)
        wavelength = 2.0 * math.pi * radius
        frequency = 1.0 / wavelength
        rows.append(
            {
                "index": n,
                "radius_m": radius,
                "wavelength_m": wavelength,
                "frequency_cycles_per_m": frequency,
                "bandwidth_cycles_per_m": BANDWIDTH_FRACTION * frequency,
                "weight": 1.0 / (n + 1.0),
            }
        )
    return rows


def radial_frequency(
    rows: int,
    cols: int,
    dy_m: float,
    dx_m: float,
    device: torch.device,
    dtype: torch.dtype,
) -> torch.Tensor:
    fy = torch.fft.fftfreq(rows, d=dy_m, device=device).to(dtype)
    fx = torch.fft.fftfreq(cols, d=dx_m, device=device).to(dtype)
    return torch.sqrt(fy[:, None] ** 2 + fx[None, :] ** 2)


def gaussian_cascade(
    fr: torch.Tensor,
    centers: torch.Tensor,
    weights: torch.Tensor,
) -> torch.Tensor:
    sigma = BANDWIDTH_FRACTION * centers
    terms = torch.exp(-0.5 * ((fr[None, :, :] - centers[:, None, None]) / sigma[:, None, None]) ** 2)
    transfer = torch.sum(weights[:, None, None] * terms, dim=0)
    # The input field is mean-subtracted, so DC has no contribution. Setting the
    # DC cell to zero makes that invariant explicit without changing the paper's
    # non-zero-frequency equation or any filtered output.
    transfer[0, 0] = 0.0
    return transfer


def build_transfers(
    rows: int,
    cols: int,
    dy_m: float,
    dx_m: float,
    device: torch.device,
    dtype: torch.dtype,
    jitter_seed: int,
) -> tuple[list[str], torch.Tensor, dict[str, list[float]]]:
    fr = radial_frequency(rows, cols, dy_m, dx_m, device, dtype)
    exact_centers = torch.tensor(
        [row["frequency_cycles_per_m"] for row in shell_spec()],
        device=device,
        dtype=dtype,
    )
    weights = torch.tensor(
        [1.0 / (n + 1.0) for n in range(TABLE_SHELLS)], device=device, dtype=dtype
    )
    log_mid = torch.mean(torch.log(exact_centers))

    names: list[str] = []
    filters: list[torch.Tensor] = []
    centre_audit: dict[str, list[float]] = {}

    def add_ratio(name: str, ratio: float) -> None:
        offsets = torch.arange(TABLE_SHELLS, device=device, dtype=dtype) - (TABLE_SHELLS - 1.0) / 2.0
        centers = torch.exp(log_mid + offsets * math.log(ratio))
        names.append(name)
        filters.append(gaussian_cascade(fr, centers, weights))
        centre_audit[name] = [float(x) for x in centers.detach().cpu()]

    # Exact primary hypothesis first, then preregistered fixed controls.
    names.append("phi2")
    filters.append(gaussian_cascade(fr, exact_centers, weights))
    centre_audit["phi2"] = [float(x) for x in exact_centers.detach().cpu()]
    add_ratio("sqrt2", math.sqrt(2.0))
    add_ratio("phi", PHI)
    add_ratio("octave", 2.0)
    add_ratio("three", 3.0)

    linear_centers = torch.linspace(
        float(exact_centers[0]), float(exact_centers[-1]), TABLE_SHELLS, device=device, dtype=dtype
    )
    names.append("linear_frequency")
    filters.append(gaussian_cascade(fr, linear_centers, weights))
    centre_audit["linear_frequency"] = [float(x) for x in linear_centers.detach().cpu()]

    # Conventional multi-scale Laplacian-of-Gaussian-like radial response.
    log_terms = []
    for center in exact_centers:
        q = fr / center
        log_terms.append((q * q) * torch.exp(-0.5 * q * q))
    log_transfer = torch.sum(weights[:, None, None] * torch.stack(log_terms), dim=0)
    log_transfer[0, 0] = 0.0
    names.append("laplacian_of_gaussian")
    filters.append(log_transfer)
    centre_audit["laplacian_of_gaussian"] = [float(x) for x in exact_centers.detach().cpu()]

    # Equal-complexity null ensemble: perturb shell centres without using labels.
    cpu_generator = torch.Generator(device="cpu")
    cpu_generator.manual_seed(jitter_seed)
    for index in range(4):
        jitter = torch.randn(TABLE_SHELLS, generator=cpu_generator, dtype=torch.float64) * 0.18
        centers_cpu = torch.tensor(
            [row["frequency_cycles_per_m"] for row in shell_spec()], dtype=torch.float64
        ) * torch.exp(jitter)
        centers_cpu, _ = torch.sort(centers_cpu)
        centers = centers_cpu.to(device=device, dtype=dtype)
        name = f"jitter_null_{index:02d}"
        names.append(name)
        filters.append(gaussian_cascade(fr, centers, weights))
        centre_audit[name] = [float(x) for x in centers_cpu]

    return names, torch.stack(filters), centre_audit


def make_generator(device: torch.device, seed: int) -> torch.Generator:
    generator = torch.Generator(device=device)
    generator.manual_seed(seed)
    return generator


def generate_terrain_batch(
    size: int,
    rows: int,
    cols: int,
    start_index: int,
    device: torch.device,
    dtype: torch.dtype,
    generator: torch.Generator,
    force_null: bool,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
    # Fractal-like terrain with beta sampled independently per trial.
    white = torch.randn(size, rows, cols, device=device, dtype=dtype, generator=generator)
    fy = torch.fft.fftfreq(rows, device=device).to(dtype)
    fx = torch.fft.fftfreq(cols, device=device).to(dtype)
    fr = torch.sqrt(fy[:, None] ** 2 + fx[None, :] ** 2)
    fr[0, 0] = 1.0
    beta = 1.4 + 2.2 * torch.rand(size, 1, 1, device=device, dtype=dtype, generator=generator)
    spectrum = torch.fft.fft2(white) * torch.pow(fr[None, :, :], -0.5 * beta)
    spectrum[:, 0, 0] = 0.0
    terrain = torch.fft.ifft2(spectrum).real
    terrain -= terrain.mean(dim=(1, 2), keepdim=True)
    terrain /= torch.clamp(terrain.std(dim=(1, 2), keepdim=True), min=1.0e-9)

    yy = torch.linspace(-1.0, 1.0, rows, device=device, dtype=dtype)[None, :, None]
    xx = torch.linspace(-1.0, 1.0, cols, device=device, dtype=dtype)[None, None, :]
    slope_x = 0.8 * (torch.rand(size, 1, 1, device=device, dtype=dtype, generator=generator) - 0.5)
    slope_y = 0.8 * (torch.rand(size, 1, 1, device=device, dtype=dtype, generator=generator) - 0.5)
    terrain = terrain + slope_x * xx + slope_y * yy

    # Directional ridges are a conventional false-positive challenge.
    angle = math.pi * torch.rand(size, 1, 1, device=device, dtype=dtype, generator=generator)
    ridge_f = 1.5 + 4.5 * torch.rand(size, 1, 1, device=device, dtype=dtype, generator=generator)
    phase = 2.0 * math.pi * torch.rand(size, 1, 1, device=device, dtype=dtype, generator=generator)
    ridge = torch.sin(2.0 * math.pi * ridge_f * (torch.cos(angle) * xx + torch.sin(angle) * yy) + phase)
    terrain = terrain + 0.20 * ridge

    if force_null:
        labels = torch.zeros(size, device=device, dtype=torch.bool)
    else:
        labels = torch.rand(size, device=device, dtype=dtype, generator=generator) < 0.5

    margin_y = max(8, rows // 5)
    margin_x = max(8, cols // 5)
    center_y = margin_y + (rows - 2 * margin_y) * torch.rand(
        size, device=device, dtype=dtype, generator=generator
    )
    center_x = margin_x + (cols - 2 * margin_x) * torch.rand(
        size, device=device, dtype=dtype, generator=generator
    )
    ypix = torch.arange(rows, device=device, dtype=dtype)[None, :, None]
    xpix = torch.arange(cols, device=device, dtype=dtype)[None, None, :]
    distance = torch.sqrt(
        (ypix - center_y[:, None, None]) ** 2 + (xpix - center_x[:, None, None]) ** 2
    )
    core_sigma = 2.0 + 3.5 * torch.rand(size, 1, 1, device=device, dtype=dtype, generator=generator)
    ring_multiple = 2.0 + 2.0 * torch.rand(size, 1, 1, device=device, dtype=dtype, generator=generator)
    ring_radius = core_sigma * ring_multiple
    ring_width = 0.7 + 1.1 * torch.rand(size, 1, 1, device=device, dtype=dtype, generator=generator)
    core = torch.exp(-0.5 * (distance / core_sigma) ** 2)
    ring = torch.exp(-0.5 * ((distance - ring_radius) / ring_width) ** 2)
    amplitude = 0.45 + 1.55 * torch.rand(size, 1, 1, device=device, dtype=dtype, generator=generator)
    sign = torch.where(
        torch.rand(size, 1, 1, device=device, dtype=dtype, generator=generator) < 0.5,
        -torch.ones(1, device=device, dtype=dtype),
        torch.ones(1, device=device, dtype=dtype),
    )
    target = sign * amplitude * (core + 0.45 * ring)
    terrain = terrain + labels[:, None, None].to(dtype) * target

    nuisance = (
        torch.arange(start_index, start_index + size, device=device, dtype=torch.long)
        % len(NUISANCE_NAMES)
    )

    # Missing-data challenge: replace a random circular patch with the image mean.
    missing = nuisance == 3
    if bool(torch.any(missing)):
        miss_y = rows * torch.rand(size, device=device, dtype=dtype, generator=generator)
        miss_x = cols * torch.rand(size, device=device, dtype=dtype, generator=generator)
        miss_r = 2.0 + 5.0 * torch.rand(size, 1, 1, device=device, dtype=dtype, generator=generator)
        miss_d = torch.sqrt(
            (ypix - miss_y[:, None, None]) ** 2 + (xpix - miss_x[:, None, None]) ** 2
        )
        missing_mask = (miss_d < miss_r) & missing[:, None, None]
        terrain = torch.where(missing_mask, torch.zeros_like(terrain), terrain)

    # Resampling challenge: one low-pass/reconstruction step.
    blurred = nuisance == 4
    if bool(torch.any(blurred)):
        pixel_fr = torch.sqrt(fy[:, None] ** 2 + fx[None, :] ** 2)
        blur_transfer = torch.exp(-0.5 * (pixel_fr / 0.18) ** 2)
        blurred_images = torch.fft.ifft2(torch.fft.fft2(terrain) * blur_transfer).real
        terrain = torch.where(blurred[:, None, None], blurred_images, terrain)

    terrain -= terrain.mean(dim=(1, 2), keepdim=True)
    terrain /= torch.clamp(terrain.std(dim=(1, 2), keepdim=True), min=1.0e-9)
    return terrain, labels, center_y, center_x, nuisance


def score_batch(
    images: torch.Tensor,
    transfers: torch.Tensor,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    transformed = torch.fft.fft2(images)
    filtered = torch.fft.ifft2(transformed[:, None, :, :] * transfers[None, :, :, :]).real
    magnitude = torch.abs(filtered)
    flat = magnitude.flatten(start_dim=2)
    score, location = torch.max(flat, dim=2)
    cols = images.shape[2]
    location_y = torch.div(location, cols, rounding_mode="floor")
    location_x = location % cols
    return score, location_y, location_x


def binary_metrics(scores: torch.Tensor, labels: torch.Tensor, threshold: float) -> dict[str, Any]:
    labels = labels.to(torch.bool)
    predictions = scores > threshold
    positives = int(labels.sum())
    negatives = int((~labels).sum())
    tp = int((predictions & labels).sum())
    fp = int((predictions & ~labels).sum())
    tn = int((~predictions & ~labels).sum())
    fn = int((~predictions & labels).sum())

    order = torch.argsort(scores, descending=False)
    ordered_labels = labels[order].to(torch.float64)
    ranks = torch.arange(1, scores.numel() + 1, dtype=torch.float64)
    rank_sum = float(ranks[ordered_labels.bool()].sum())
    if positives and negatives:
        auroc = (rank_sum - positives * (positives + 1) / 2.0) / (positives * negatives)
    else:
        auroc = 0.5

    descending = torch.argsort(scores, descending=True)
    desc_labels = labels[descending].to(torch.float64)
    cumulative_tp = torch.cumsum(desc_labels, dim=0)
    positions = torch.arange(1, scores.numel() + 1, dtype=torch.float64)
    precision = cumulative_tp / positions
    auprc = float((precision * desc_labels).sum() / max(positives, 1))
    tpr = tp / max(positives, 1)
    fpr = fp / max(negatives, 1)
    tnr = tn / max(negatives, 1)
    return {
        "threshold": threshold,
        "positives": positives,
        "negatives": negatives,
        "true_positives": tp,
        "false_positives": fp,
        "true_negatives": tn,
        "false_negatives": fn,
        "auroc": float(auroc),
        "auprc": auprc,
        "tpr": tpr,
        "fpr": fpr,
        "balanced_accuracy": 0.5 * (tpr + tnr),
    }


def quantile(values: torch.Tensor, q: float) -> float:
    return float(torch.quantile(values.to(torch.float64), q))


def run_synthetic(args: argparse.Namespace) -> dict[str, Any]:
    if args.device == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA requested but torch.cuda.is_available() is false")
    device = torch.device(args.device)
    dtype = torch.float64 if args.precision == "float64" else torch.float32
    names, transfers, centre_audit = build_transfers(
        args.rows,
        args.cols,
        args.dy_m,
        args.dx_m,
        device,
        dtype,
        jitter_seed=770000 + args.shard,
    )
    calibration_generator = make_generator(device, 31000000 + args.shard)
    test_generator = make_generator(device, 91000000 + args.shard)
    started = time.time()

    calibration_parts: list[torch.Tensor] = []
    done = 0
    while done < args.calibration_samples:
        size = min(args.batch_size, args.calibration_samples - done)
        images, _, _, _, _ = generate_terrain_batch(
            size,
            args.rows,
            args.cols,
            done,
            device,
            dtype,
            calibration_generator,
            force_null=True,
        )
        scores, _, _ = score_batch(images, transfers)
        calibration_parts.append(scores.detach().cpu())
        done += size
    calibration = torch.cat(calibration_parts, dim=0)
    thresholds = [quantile(calibration[:, method], 0.95) for method in range(len(names))]

    score_parts: list[torch.Tensor] = []
    label_parts: list[torch.Tensor] = []
    error_parts: list[torch.Tensor] = []
    nuisance_parts: list[torch.Tensor] = []
    done = 0
    while done < args.samples:
        size = min(args.batch_size, args.samples - done)
        images, labels, center_y, center_x, nuisance = generate_terrain_batch(
            size,
            args.rows,
            args.cols,
            done,
            device,
            dtype,
            test_generator,
            force_null=False,
        )
        scores, found_y, found_x = score_batch(images, transfers)
        errors = torch.sqrt(
            (found_y.to(dtype) - center_y[:, None]) ** 2
            + (found_x.to(dtype) - center_x[:, None]) ** 2
        )
        score_parts.append(scores.detach().cpu())
        label_parts.append(labels.detach().cpu())
        error_parts.append(errors.detach().cpu())
        nuisance_parts.append(nuisance.detach().cpu())
        done += size

    all_scores = torch.cat(score_parts, dim=0)
    all_labels = torch.cat(label_parts, dim=0)
    all_errors = torch.cat(error_parts, dim=0)
    all_nuisance = torch.cat(nuisance_parts, dim=0)
    method_reports: dict[str, Any] = {}
    predictions = []
    for index, name in enumerate(names):
        report = binary_metrics(all_scores[:, index], all_labels, thresholds[index])
        positive_errors = all_errors[all_labels, index]
        report["localisation_error_pixels"] = {
            "median": quantile(positive_errors, 0.50),
            "p90": quantile(positive_errors, 0.90),
        }
        strata: dict[str, Any] = {}
        for nuisance_index, nuisance_name in enumerate(NUISANCE_NAMES):
            mask = all_nuisance == nuisance_index
            strata[nuisance_name] = binary_metrics(
                all_scores[mask, index], all_labels[mask], thresholds[index]
            )
        report["nuisance_strata"] = strata
        method_reports[name] = report
        predictions.append(all_scores[:, index] > thresholds[index])

    correctness = torch.stack(predictions, dim=1) == all_labels[:, None]
    paired: dict[str, Any] = {}
    phi_correct = correctness[:, 0]
    for index, name in enumerate(names[1:], start=1):
        other = correctness[:, index]
        paired[name] = {
            "phi2_correct_control_wrong": int((phi_correct & ~other).sum()),
            "phi2_wrong_control_correct": int((~phi_correct & other).sum()),
            "auroc_delta_phi2_minus_control": method_reports["phi2"]["auroc"]
            - method_reports[name]["auroc"],
        }

    protocol_path = Path(args.protocol)
    elapsed = time.time() - started
    return {
        "schema": SCHEMA,
        "claim_class": "simulation",
        "boundary": BOUNDARY,
        "protocol_sha256": sha256_file(protocol_path),
        "environment": environment(device, dtype),
        "design": {
            "shard": args.shard,
            "samples": args.samples,
            "calibration_samples": args.calibration_samples,
            "calibration_quantile": 0.95,
            "rows": args.rows,
            "cols": args.cols,
            "dy_m": args.dy_m,
            "dx_m": args.dx_m,
            "calibration_seed": 31000000 + args.shard,
            "test_seed": 91000000 + args.shard,
            "jitter_seed": 770000 + args.shard,
            "target_scale_sampling": "independent of phi",
            "elapsed_seconds": elapsed,
        },
        "reference_discrepancy": {
            "paper_prose_shell_count": 9,
            "paper_table_shell_count": 10,
            "implemented_shell_count": 10,
        },
        "filter_centres_cycles_per_m": centre_audit,
        "methods": method_reports,
        "paired_correctness": paired,
    }


def pearson(a: torch.Tensor, b: torch.Tensor) -> float:
    av = a.flatten().to(torch.float64)
    bv = b.flatten().to(torch.float64)
    av -= av.mean()
    bv -= bv.mean()
    denominator = torch.sqrt(torch.sum(av * av) * torch.sum(bv * bv))
    return float(torch.sum(av * bv) / torch.clamp(denominator, min=1.0e-15))


def run_real(args: argparse.Namespace) -> dict[str, Any]:
    dem_path = Path(args.dem)
    payload = json.loads(dem_path.read_text(encoding="utf-8"))
    rows = int(payload["grid"]["rows"])
    cols = int(payload["grid"]["cols"])
    elevations = torch.tensor(payload["elevations_m"], dtype=torch.float64).reshape(rows, cols)
    dx_m = float(payload["grid"]["east_west_spacing_m"])
    dy_m = float(payload["grid"]["north_south_spacing_m"])
    names, transfers, centres = build_transfers(
        rows, cols, dy_m, dx_m, torch.device("cpu"), torch.float64, jitter_seed=770000
    )
    image = elevations - elevations.mean()
    filtered = torch.fft.ifft2(torch.fft.fft2(image)[None, :, :] * transfers).real
    lats = torch.tensor(payload["latitudes"], dtype=torch.float64)
    lons = torch.tensor(payload["longitudes"], dtype=torch.float64)

    method_reports: dict[str, Any] = {}
    phi_image = filtered[0]
    for index, name in enumerate(names):
        layer = filtered[index]
        absolute = torch.abs(layer)
        top_count = min(20, rows * cols)
        values, locations = torch.topk(absolute.flatten(), top_count)
        top = []
        layer_std = float(layer.std())
        for value, location in zip(values, locations):
            row = int(location) // cols
            col = int(location) % cols
            top.append(
                {
                    "row": row,
                    "col": col,
                    "lat": float(lats[row]),
                    "lon": float(lons[col]),
                    "absolute_response_m": float(value),
                    "standardised_absolute_response": float(value) / max(layer_std, 1.0e-12),
                }
            )
        method_reports[name] = {
            "response_mean_m": float(layer.mean()),
            "response_std_m": layer_std,
            "response_min_m": float(layer.min()),
            "response_max_m": float(layer.max()),
            "correlation_with_phi2": pearson(layer, phi_image),
            "top_absolute_response_pixels_descriptive_only": top,
        }

    extent_y = dy_m * (rows - 1)
    extent_x = dx_m * (cols - 1)
    min_frequency = 1.0 / max(extent_x, extent_y)
    nyquist = min(1.0 / (2.0 * dx_m), 1.0 / (2.0 * dy_m))
    shells = shell_spec()
    for shell in shells:
        f = shell["frequency_cycles_per_m"]
        shell["resolvable_on_grid"] = bool(min_frequency <= f <= nyquist)

    return {
        "schema": SCHEMA,
        "claim_class": "descriptive_real_data",
        "ground_truth": "none supplied",
        "boundary": BOUNDARY,
        "input": {
            "path": str(dem_path),
            "sha256": sha256_file(dem_path),
            "source": payload.get("source"),
            "retrieved_utc": payload.get("retrieved_utc"),
            "grid": payload["grid"],
            "elevation_min_m": float(elevations.min()),
            "elevation_max_m": float(elevations.max()),
            "elevation_mean_m": float(elevations.mean()),
            "elevation_std_m": float(elevations.std()),
        },
        "resolution": {
            "minimum_sampled_frequency_cycles_per_m": min_frequency,
            "nyquist_frequency_cycles_per_m": nyquist,
            "nyquist_wavelength_m": 1.0 / nyquist,
            "shells": shells,
        },
        "reference_discrepancy": {
            "paper_prose_shell_count": 9,
            "paper_table_shell_count": 10,
            "implemented_shell_count": 10,
        },
        "filter_centres_cycles_per_m": centres,
        "methods": method_reports,
        "interpretation": "Top-response pixels and inter-filter correlations are descriptive diagnostics, not candidate dig sites or validation of buried geology.",
    }


def run_selftest(args: argparse.Namespace) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    def check(name: str, passed: bool, detail: Any) -> None:
        checks.append({"name": name, "passed": bool(passed), "detail": detail})

    shells = shell_spec()
    check("table_shell_count_is_ten", len(shells) == 10, len(shells))
    check(
        "outer_wavelength",
        abs(shells[0]["wavelength_m"] - 94247.7796077) < 1.0e-4,
        shells[0]["wavelength_m"],
    )
    check(
        "phi2_radius_recursion",
        max(abs(shells[n]["radius_m"] / shells[n + 1]["radius_m"] - PHI2) for n in range(9))
        < 1.0e-12,
        PHI2,
    )
    names, filters, _ = build_transfers(
        40, 40, 280.0, 270.0, torch.device("cpu"), torch.float64, jitter_seed=770000
    )
    check("primary_method_first", names[0] == "phi2", names)
    check("all_transfers_finite", bool(torch.isfinite(filters).all()), list(filters.shape))
    check("dc_removed", bool(torch.all(filters[:, 0, 0] == 0.0)), filters[:, 0, 0].tolist())
    rms_values = torch.sqrt(torch.mean(filters**2, dim=(1, 2)))
    check("all_transfers_have_positive_energy", bool(torch.all(rms_values > 0.0)), rms_values.tolist())
    generator_a = make_generator(torch.device("cpu"), 12345)
    generator_b = make_generator(torch.device("cpu"), 12345)
    a = generate_terrain_batch(4, 40, 40, 0, torch.device("cpu"), torch.float64, generator_a, False)[0]
    b = generate_terrain_batch(4, 40, 40, 0, torch.device("cpu"), torch.float64, generator_b, False)[0]
    check("deterministic_generator", bool(torch.equal(a, b)), sha256_file(Path(args.protocol)))
    passed = all(item["passed"] for item in checks)
    return {
        "schema": SCHEMA,
        "claim_class": "reference_implementation",
        "boundary": BOUNDARY,
        "passed": passed,
        "checks": checks,
        "protocol_sha256": sha256_file(Path(args.protocol)),
        "environment": environment(torch.device("cpu"), torch.float64),
    }


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser()
    root.add_argument("--protocol", default=str(Path(__file__).with_name("protocol.json")))
    subparsers = root.add_subparsers(dest="command", required=True)

    selftest = subparsers.add_parser("selftest")
    selftest.add_argument("--output", required=True)

    synthetic = subparsers.add_parser("synthetic")
    synthetic.add_argument("--output", required=True)
    synthetic.add_argument("--shard", type=int, required=True)
    synthetic.add_argument("--samples", type=int, default=5000)
    synthetic.add_argument("--calibration-samples", type=int, default=1500)
    synthetic.add_argument("--rows", type=int, default=80)
    synthetic.add_argument("--cols", type=int, default=80)
    synthetic.add_argument("--dy-m", type=float, default=80.0)
    synthetic.add_argument("--dx-m", type=float, default=84.0)
    synthetic.add_argument("--batch-size", type=int, default=64)
    synthetic.add_argument("--device", choices=["cpu", "cuda"], default="cpu")
    synthetic.add_argument("--precision", choices=["float32", "float64"], default="float64")

    real = subparsers.add_parser("real")
    real.add_argument("--dem", required=True)
    real.add_argument("--output", required=True)
    return root


def main() -> int:
    args = parser().parse_args()
    if args.command == "selftest":
        result = run_selftest(args)
    elif args.command == "synthetic":
        result = run_synthetic(args)
    elif args.command == "real":
        result = run_real(args)
    else:
        raise AssertionError(args.command)
    write_json(Path(args.output), result)
    print(json.dumps(result, sort_keys=True, allow_nan=False))
    return 0 if result.get("passed", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())
