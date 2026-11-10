#!/usr/bin/env python3
"""Fail-closed aggregation + detector battery verdict for the Tandem 10-9-1 detector-redesign benchmark.

Mirrors the pre-registered Stage 1 aggregation methodology exactly:
per-stratum thresholds (99th percentile of the stratum's calibration nulls),
detections applied to held-out nulls and non-zero-eta alternatives, and the
registered gates (held-out null FPR <= 1.5%, power >= 80% at eta >= 0.05 and
SNR >= 0 dB, correct template beats shifted control).

Detectors: D0 (pre-registered control), D1 (matched filter / GLRT),
D2 (lag-sweep cross-correlation peak), D3 (cepstral spectral comb),
D4 (gradient-boosted windowed features, cross-fitted, trained only on
training-fold synthetics).
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


SHARD_SCHEMA = "tandem-detector-redesign-shard/v1"
AGGREGATE_SCHEMA = "tandem-detector-redesign-aggregate/v1"
CLAIM_CLASS = "computational_simulation"
INTERPRETATION_BOUNDARY = (
    "Synthetic identifiability of a candidate 10-9-1 echo signature with redesigned detectors on the "
    "pre-registered synthetic data-generating process. Not a physical observation, not independent "
    "replication, cannot prove branching of physical reality."
)
OPERATORS = ("source_lock", "echo_coherence", "minimum_action")
NOISE_MODELS = ("white", "ar1_0p9", "two_timescale")
TRUTH_MODELS = ("h0_delay", "h0_phase_mix", "h1_echo")
ETA_CURVE_LEVELS = (0.02, 0.05, 0.10, 0.20)
ORIGINAL_KEYS = [
    "trial_id", "eta", "snr_db", "noise_model", "operator", "truth_model",
    "null_split", "selected_branch", "corr_true", "corr_shift", "discriminant", "eta_hat",
]


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
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, (float, np.floating)):
        number = float(value)
        return number if math.isfinite(number) else None
    return value


def detector_analysis(
    score: np.ndarray,
    eta: np.ndarray,
    snr: np.ndarray,
    noise: np.ndarray,
    oper: np.ndarray,
    truth: np.ndarray,
    split: np.ndarray,
    restrict: np.ndarray | None = None,
) -> dict[str, Any]:
    """Stage-1-style per-stratum threshold analysis for one detector score."""
    if restrict is None:
        restrict = np.ones_like(eta, dtype=bool)
    alternative = restrict & (truth == 2) & (eta > 0.0)
    null = restrict & ~((truth == 2) & (eta > 0.0))
    detections = np.zeros_like(eta, dtype=bool)
    held_out_null = np.zeros_like(eta, dtype=bool)
    strata: list[dict[str, Any]] = []
    for operator_id, operator_name in enumerate(OPERATORS):
        for noise_id, noise_name in enumerate(NOISE_MODELS):
            for snr_level in sorted(np.unique(snr[restrict])):
                stratum = (
                    restrict
                    & (oper == operator_id)
                    & (noise == noise_id)
                    & np.isclose(snr, snr_level)
                )
                cal = stratum & null & (split == 0)
                test_null = stratum & null & (split == 1)
                if cal.sum() < 20 or test_null.sum() < 20:
                    raise RuntimeError(
                        f"insufficient nulls for {operator_name}/{noise_name}/{snr_level}dB: "
                        f"cal={cal.sum()} test={test_null.sum()}"
                    )
                threshold = float(np.quantile(score[cal], 0.99))
                detections[stratum] = score[stratum] > threshold
                held_out_null |= test_null
                powers: dict[str, float] = {}
                minimum_eta = None
                for level in sorted(np.unique(eta[restrict & (eta > 0.0)])):
                    mask = stratum & alternative & np.isclose(eta, level)
                    power = float(np.mean(detections[mask]))
                    powers[f"{level:.3f}"] = power
                    if minimum_eta is None and power >= 0.80:
                        minimum_eta = float(level)
                strata.append(
                    {
                        "operator": operator_name,
                        "noise_model": noise_name,
                        "snr_db": float(snr_level),
                        "threshold": threshold,
                        "calibration_null_trials": int(cal.sum()),
                        "held_out_null_trials": int(test_null.sum()),
                        "held_out_null_fpr": float(np.mean(detections[test_null])),
                        "power_by_eta": powers,
                        "minimum_eta_at_80pct_power": minimum_eta,
                    }
                )
    target = alternative & (eta >= 0.05) & (snr >= 0.0)
    overall_fpr = float(np.mean(detections[held_out_null]))
    target_power = float(np.mean(detections[target]))
    # Per-trial threshold lookup (operator x noise x snr) for out-of-analysis
    # diagnostics such as apparent (in-sample) power.
    snr_levels_sorted = sorted(np.unique(snr))
    thr_cube = np.full((len(OPERATORS), len(NOISE_MODELS), len(snr_levels_sorted)), np.nan)
    for entry in strata:
        thr_cube[
            OPERATORS.index(entry["operator"]),
            NOISE_MODELS.index(entry["noise_model"]),
            snr_levels_sorted.index(entry["snr_db"]),
        ] = entry["threshold"]
    snr_index = np.searchsorted(np.asarray(snr_levels_sorted), snr)
    threshold_by_trial = thr_cube[oper, noise, snr_index]
    null_fpr_by_model = {
        TRUTH_MODELS[model]: float(np.mean(detections[held_out_null & (truth == model)]))
        for model in range(len(TRUTH_MODELS))
        if np.any(held_out_null & (truth == model))
    }
    # Pooled power curves over operators, per noise family x SNR x eta.
    curves: dict[str, Any] = {}
    for noise_id, noise_name in enumerate(NOISE_MODELS):
        for snr_level in sorted(np.unique(snr[restrict])):
            key = f"{noise_name}/{snr_level:g}dB"
            entry = {}
            for level in ETA_CURVE_LEVELS:
                mask = alternative & (noise == noise_id) & np.isclose(snr, snr_level) & np.isclose(eta, level)
                entry[f"{level:.3f}"] = float(np.mean(detections[mask])) if mask.sum() else None
            curves[key] = entry
    # Pooled minimum eta at 80% power.
    def min_eta(mask_base: np.ndarray) -> float | None:
        for level in sorted(np.unique(eta[restrict & (eta > 0.0)])):
            mask = mask_base & np.isclose(eta, level)
            if mask.sum() and float(np.mean(detections[mask])) >= 0.80:
                return float(level)
        return None

    pooled = {
        "snr_ge_0db_all_noise": min_eta(alternative & (snr >= 0.0)),
    }
    for noise_id, noise_name in enumerate(NOISE_MODELS):
        pooled[f"snr_ge_0db_{noise_name}"] = min_eta(alternative & (snr >= 0.0) & (noise == noise_id))
    # Power at the registered target corner eta=0.05, SNR=0 dB (pooled over operator and noise).
    corner = alternative & np.isclose(eta, 0.05) & np.isclose(snr, 0.0)
    corner_power = float(np.mean(detections[corner]))
    # Best stratum (echo_coherence, ar1_0p9, 20 dB) power at eta=0.2 for continuity with Stage 1.
    best = alternative & (oper == 1) & (noise == 1) & np.isclose(snr, 20.0) & np.isclose(eta, 0.20)
    best_stratum_power_eta_0p2 = float(np.mean(detections[best]))
    return {
        "strata": strata,
        "detections": detections,
        "held_out_null_mask": held_out_null,
        "alternative_mask": alternative,
        "threshold_by_trial": threshold_by_trial,
        "overall": {
            "held_out_null_false_positive_rate": overall_fpr,
            "held_out_null_false_positive_rate_by_truth_model": null_fpr_by_model,
            "target_power_eta_ge_0p05_snr_ge_0db": target_power,
            "power_at_eta_0p05_snr_0db": corner_power,
            "power_curves_pooled_over_operators": curves,
            "minimum_eta_at_80pct_power": pooled,
            "best_stratum_echo_coherence_ar1_20db_power_eta_0p2": best_stratum_power_eta_0p2,
            "target_trials": int(target.sum()),
            "held_out_null_trials": int(held_out_null.sum()),
        },
    }


def train_d4_scores(
    features: np.ndarray,
    alternative: np.ndarray,
    null: np.ndarray,
    split: np.ndarray,
    trial_seq: np.ndarray,
) -> dict[str, Any]:
    """Cross-fitted gradient-boosted detector trained only on training-fold synthetics.

    - Positives (h1_echo, eta>0) split by within-shard trial parity: even -> train, odd -> test.
    - Nulls use the registered calibration (split 0) / evaluation (split 1) separation.
    - Calibration-null scores for thresholding are 5-fold out-of-fold (never scored by a model
      that saw them); evaluation nulls and test positives are scored by the final model trained
      on train positives + all calibration nulls.
    """
    from sklearn.ensemble import HistGradientBoostingClassifier

    params = dict(
        max_iter=400,
        learning_rate=0.06,
        max_leaf_nodes=31,
        l2_regularization=1.0,
        early_stopping=True,
        validation_fraction=0.1,
        random_state=10901,
    )
    # Stratum-safe split: the deterministic stratum cycle is 1728 trials long, so a
    # trial-parity split is confounded with eta (gid%8 parity fixes the eta level).
    # Splitting by 1728-trial cycle parity gives both halves complete, identical
    # coverage of every (eta x snr x noise x operator x truth) stratum.
    cycle = trial_seq // 1728
    pos_train = alternative & (cycle % 2 == 0)
    pos_test = alternative & (cycle % 2 == 1)
    cal = null & (split == 0)
    ev = null & (split == 1)
    fold = cycle % 5
    oof_score = np.full(features.shape[0], np.nan, dtype=np.float64)
    fit_seconds = []
    for k in range(5):
        train_mask = pos_train | (cal & (fold != k))
        model = HistGradientBoostingClassifier(**params)
        t0 = time.perf_counter()
        model.fit(features[train_mask], alternative[train_mask].astype(np.int8))
        fit_seconds.append(time.perf_counter() - t0)
        fold_mask = cal & (fold == k)
        oof_score[fold_mask] = model.predict_proba(features[fold_mask])[:, 1]
    final_model = HistGradientBoostingClassifier(**params)
    t0 = time.perf_counter()
    final_model.fit(features[pos_train | cal], alternative[pos_train | cal].astype(np.int8))
    fit_seconds.append(time.perf_counter() - t0)
    final_score = final_model.predict_proba(features)[:, 1]
    score_all = np.where(cal, oof_score, final_score)
    # Calibration honesty on fully held-out data (evaluation nulls + test positives).
    ho = ev | pos_test
    prob = final_score[ho]
    label = alternative[ho].astype(np.int8)
    deciles = np.quantile(prob, np.linspace(0.0, 1.0, 11))
    reliability = []
    for lo, hi in zip(deciles[:-1], deciles[1:]):
        m = (prob >= lo) & (prob <= hi)
        if m.sum():
            reliability.append(
                {"bin": [float(lo), float(hi)], "mean_predicted": float(prob[m].mean()),
                 "empirical_positive_rate": float(label[m].mean()), "count": int(m.sum())}
            )
    max_cal_gap = max((abs(r["mean_predicted"] - r["empirical_positive_rate"]) for r in reliability), default=None)
    return {
        "score_all": score_all,
        "pos_train_mask": pos_train,
        "pos_test_mask": pos_test,
        "train_positives": int(pos_train.sum()),
        "test_positives": int(pos_test.sum()),
        "calibration_nulls": int(cal.sum()),
        "evaluation_nulls": int(ev.sum()),
        "fit_seconds_total": float(sum(fit_seconds)),
        "reliability_deciles_held_out": reliability,
        "max_calibration_gap_held_out": max_cal_gap,
        "params": {k: (v if not isinstance(v, bool) else int(v)) for k, v in params.items()},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--stage1-dir", required=True)
    parser.add_argument("--output-prefix", required=True)
    parser.add_argument("--expected-shards", type=int, default=32)
    parser.add_argument("--stage1-trials", type=int, default=6912)
    args = parser.parse_args()
    started_utc = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    run_dir = Path(args.run_dir).resolve()
    stage1_dir = Path(args.stage1_dir).resolve()
    output_prefix = Path(args.output_prefix).resolve()

    stage1_aggregate = json.loads((stage1_dir / "aggregate.stdout.json").read_text(encoding="utf-8"))
    stage1_inputs = stage1_aggregate["inputs"]

    receipts = sorted(run_dir.glob("shard-[0-9][0-9][0-9].json"))
    if len(receipts) != args.expected_shards:
        raise RuntimeError(f"expected {args.expected_shards} shard receipts, found {len(receipts)}")
    seen: set[int] = set()
    input_hashes: dict[str, set[str]] = {
        "paper_sha256": set(),
        "implementation_sha256": set(),
        "protocol_sha256": set(),
        "registered_harness_sha256": set(),
        "redesign_harness_sha256": set(),
    }
    arrays: dict[str, list[np.ndarray]] = {}
    shard_hashes: list[dict[str, Any]] = []
    trials_per_shard = None
    slurm_jobs = []
    for receipt_path in receipts:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        if receipt.get("schema") != SHARD_SCHEMA:
            raise RuntimeError(f"wrong schema in {receipt_path}")
        shard = int(receipt["shard"])
        if shard in seen:
            raise RuntimeError(f"duplicate shard {shard}")
        seen.add(shard)
        npz_path = Path(receipt["output"]["npz"])
        if not npz_path.is_file():
            raise RuntimeError(f"missing NPZ for shard {shard}")
        actual_npz_hash = sha256_file(npz_path)
        if actual_npz_hash != receipt["output"]["npz_sha256"]:
            raise RuntimeError(f"NPZ hash mismatch for shard {shard}")
        for key in input_hashes:
            input_hashes[key].add(receipt["inputs"][key])
        with np.load(npz_path) as data:
            for key in data.files:
                values = np.asarray(data[key])
                if key == "d4_features":
                    if values.ndim != 2:
                        raise RuntimeError("d4_features must be 2D")
                elif values.ndim != 1:
                    raise RuntimeError(f"non-vector {key} in shard {shard}")
                if np.issubdtype(values.dtype, np.floating) and not np.isfinite(values).all():
                    raise RuntimeError(f"non-finite {key} in shard {shard}")
                arrays.setdefault(key, []).append(values)
        if trials_per_shard is None:
            trials_per_shard = int(receipt["parameters"]["trials"])
        elif trials_per_shard != int(receipt["parameters"]["trials"]):
            raise RuntimeError("inconsistent trials per shard")
        slurm_jobs.append(
            {
                "shard": shard,
                "array_job_id": receipt["runtime"]["array_job_id"],
                "array_task_id": receipt["runtime"]["array_task_id"],
                "slurm_job_id": receipt["runtime"]["slurm_job_id"],
                "elapsed_seconds": receipt["runtime"]["elapsed_seconds"],
                "device_name": receipt["runtime"]["device_name"],
            }
        )
        shard_hashes.append(
            {
                "shard": shard,
                "receipt": str(receipt_path),
                "receipt_sha256": sha256_file(receipt_path),
                "npz_sha256": actual_npz_hash,
            }
        )
    if seen != set(range(args.expected_shards)):
        raise RuntimeError(f"shard set mismatch: {sorted(seen)}")
    for key, hashes in input_hashes.items():
        if len(hashes) != 1:
            raise RuntimeError(f"inconsistent {key}: {sorted(hashes)}")
    merged = {key: np.concatenate(parts) for key, parts in arrays.items()}
    total_trials = int(merged["eta"].shape[0])
    trial_seq = np.tile(np.arange(trials_per_shard), args.expected_shards)

    # --- Input provenance check against the Stage 1 registered hashes.
    provenance = {
        "paper_matches_stage1": next(iter(input_hashes["paper_sha256"])) == stage1_inputs["paper_sha256"],
        "implementation_matches_stage1": next(iter(input_hashes["implementation_sha256"]))
        == stage1_inputs["implementation_sha256"],
        "protocol_matches_stage1": next(iter(input_hashes["protocol_sha256"]))
        == stage1_inputs["protocol_sha256"],
        "registered_harness_matches_stage1": next(iter(input_hashes["registered_harness_sha256"]))
        == stage1_inputs["harness_sha256"],
    }
    if not all(provenance.values()):
        raise RuntimeError(f"registered input hash mismatch: {provenance}")

    # --- Machinery check A: bit-reproduction of the Stage 1 trial stream (first 6912 trials/shard).
    bit_repro: dict[str, Any] = {"stage1_trials_compared_per_shard": args.stage1_trials, "keys": {}}
    exact_all = True
    for key in ORIGINAL_KEYS:
        key_exact = True
        max_abs = 0.0
        for shard in range(args.expected_shards):
            with np.load(stage1_dir / f"shard-{shard:03d}.npz") as s1:
                a = np.asarray(s1[key])
            lo = shard * trials_per_shard
            b = merged[key][lo:lo + args.stage1_trials]
            if a.shape != b.shape or not np.array_equal(a, b):
                key_exact = False
                if a.shape == b.shape and a.dtype.kind == "f":
                    max_abs = max(max_abs, float(np.max(np.abs(a - b))))
                else:
                    max_abs = -1.0
        bit_repro["keys"][key] = {"bit_identical": key_exact, "max_abs_diff": max_abs}
        exact_all = exact_all and key_exact
    bit_repro["dgp_gpu_bit_reproduction_all_shards"] = exact_all

    # --- Machinery check B: reproduce the Stage 1 headline numbers with the redesign pipeline.
    eta = merged["eta"]
    snr = merged["snr_db"]
    noise = merged["noise_model"]
    oper = merged["operator"]
    truth = merged["truth_model"]
    split = merged["null_split"]
    restrict_stage1 = trial_seq < args.stage1_trials
    d0_check = detector_analysis(
        merged["discriminant"], eta, snr, noise, oper, truth, split, restrict=restrict_stage1
    )
    s1_overall = stage1_aggregate["overall"]
    alt_check = d0_check["alternative_mask"]
    shifted_check = float(np.mean(merged["corr_true"][alt_check] > merged["corr_shift"][alt_check]))
    machinery = {
        "dgp_bit_reproduction": bit_repro,
        "d0_stage1_headline_reproduction": {
            "redesign_fpr": d0_check["overall"]["held_out_null_false_positive_rate"],
            "stage1_fpr": s1_overall["held_out_null_false_positive_rate"],
            "redesign_target_power": d0_check["overall"]["target_power_eta_ge_0p05_snr_ge_0db"],
            "stage1_target_power": s1_overall["target_power_eta_ge_0p05_snr_ge_0db"],
            "redesign_shifted_win_rate": shifted_check,
            "stage1_shifted_win_rate": s1_overall["correct_template_beats_shifted_rate_nonzero_eta"],
        },
    }
    machinery["d0_stage1_headline_reproduction"]["all_match_1e_12"] = bool(
        abs(machinery["d0_stage1_headline_reproduction"]["redesign_fpr"] - machinery["d0_stage1_headline_reproduction"]["stage1_fpr"]) < 1e-12
        and abs(machinery["d0_stage1_headline_reproduction"]["redesign_target_power"] - machinery["d0_stage1_headline_reproduction"]["stage1_target_power"]) < 1e-12
        and abs(machinery["d0_stage1_headline_reproduction"]["redesign_shifted_win_rate"] - machinery["d0_stage1_headline_reproduction"]["stage1_shifted_win_rate"]) < 1e-12
    )

    # --- Detector battery on the full redesign dataset.
    alt_all = (truth == 2) & (eta > 0.0)
    null_all = ~alt_all
    shared_shifted_win = float(np.mean(merged["corr_true"][alt_all] > merged["corr_shift"][alt_all]))
    detectors: dict[str, Any] = {}

    score_map = {
        "D0_preregistered_discriminant": merged["discriminant"],
        "D1_matched_filter_glrt": merged["d1_glrt_t"],
        "D2_xcf_peak_lag_sweep": merged["d2_xcf_max"],
        "D3_spectral_comb_cepstrum": merged["d3_cepstral_z_tau"],
    }
    detector_specific_gate3 = {
        "D0_preregistered_discriminant": shared_shifted_win,
        "D1_matched_filter_glrt": shared_shifted_win,
        "D2_xcf_peak_lag_sweep": float(np.mean(merged["d2_xcf0"][alt_all] > merged["d2_xcf_shift"][alt_all])),
        "D3_spectral_comb_cepstrum": float(
            np.mean(merged["d3_cepstral_z_tau"][alt_all] > merged["d3_cepstral_z_control"][alt_all])
        ),
    }

    for name, score in score_map.items():
        result = detector_analysis(score, eta, snr, noise, oper, truth, split)
        gates = {
            "held_out_null_fpr_le_0p015": result["overall"]["held_out_null_false_positive_rate"] <= 0.015,
            "target_power_ge_0p80": result["overall"]["target_power_eta_ge_0p05_snr_ge_0db"] >= 0.80,
            "correct_template_beats_shifted": detector_specific_gate3[name] > 0.50,
        }
        detectors[name] = {
            "score": name,
            "gates": gates,
            "gates_passed": bool(all(gates.values())),
            "gate3_correct_template_beats_shifted": detector_specific_gate3[name],
            "gate3_shared_stage1_definition": shared_shifted_win,
            "overall": result["overall"],
            "strata": result["strata"],
        }
    detectors["D2_xcf_peak_lag_sweep"]["peak_at_lag_zero_rate"] = float(
        np.mean(merged["d2_argmax_lag"][alt_all] == 0.0)
    )

    # --- D4: learned detector (cross-fitted GBT on windowed features).
    d4 = train_d4_scores(merged["d4_features"], alt_all, null_all, split, trial_seq)
    # Honest evaluation: power is measured ONLY on held-out test positives
    # (nulls are unaffected by the restriction: all calibration + evaluation
    # nulls are retained for thresholds and FPR).
    d4_honest_restrict = null_all | d4["pos_test_mask"]
    d4_result = detector_analysis(
        d4["score_all"], eta, snr, noise, oper, truth, split, restrict=d4_honest_restrict
    )
    d4_gates = {
        "held_out_null_fpr_le_0p015": d4_result["overall"]["held_out_null_false_positive_rate"] <= 0.015,
        "target_power_ge_0p80": d4_result["overall"]["target_power_eta_ge_0p05_snr_ge_0db"] >= 0.80,
        "correct_template_beats_shifted": shared_shifted_win > 0.50,
    }
    detections4 = d4_result["detections"]
    # Apparent (in-sample) power on train positives must apply the honest
    # per-stratum thresholds to the final model's in-sample scores directly;
    # the restricted `detections` array deliberately covers test positives only.
    thr4 = d4_result["threshold_by_trial"]
    train_target = d4["pos_train_mask"] & (eta >= 0.05) & (snr >= 0.0)
    apparent_train_power = float(np.mean(d4["score_all"][train_target] > thr4[train_target]))
    honest_test_power = float(
        np.mean(detections4[d4["pos_test_mask"] & (eta >= 0.05) & (snr >= 0.0)])
    )
    detectors["D4_learned_gbt_windowed_features"] = {
        "score": "D4_learned_gbt_windowed_features",
        "gates": d4_gates,
        "gates_passed": bool(all(d4_gates.values())),
        "gate3_correct_template_beats_shifted": shared_shifted_win,
        "gate3_note": "D4 has no alignment structure; gate 3 uses the shared Stage-1 template comparison.",
        "overall": d4_result["overall"],
        "strata": d4_result["strata"],
        "training_protocol": {
            "trained_on": "h1_echo positives from even 1728-trial stratum cycles + registered calibration nulls only",
            "evaluated_on": "h1_echo positives from odd 1728-trial stratum cycles + registered held-out evaluation nulls",
            "split_scheme": "stratum-safe: (trial_seq // 1728) %% 2 cycle parity; plain trial parity is confounded with eta (gid %% 8) and was rejected",
            "calibration_thresholds": "5-fold out-of-fold calibration-null scores (folds by 1728-trial cycle), per stratum p99",
            "train_positives": d4["train_positives"],
            "test_positives": d4["test_positives"],
            "calibration_nulls": d4["calibration_nulls"],
            "evaluation_nulls": d4["evaluation_nulls"],
            "model": "HistGradientBoostingClassifier",
            "params": d4["params"],
            "fit_seconds_total": d4["fit_seconds_total"],
        },
        "generalization": {
            "apparent_target_power_on_train_positives": apparent_train_power,
            "honest_target_power_on_test_positives": honest_test_power,
            "generalization_gap": apparent_train_power - honest_test_power,
        },
        "calibration": {
            "max_abs_reliability_gap_held_out": d4["max_calibration_gap_held_out"],
            "reliability_deciles_held_out": d4["reliability_deciles_held_out"],
        },
    }

    # --- Overall verdict.
    any_pass = any(det["gates_passed"] for det in detectors.values())
    passing = [name for name, det in detectors.items() if det["gates_passed"]]
    overall_verdict = "SYNTHETIC_SIGNATURE_IDENTIFIABLE" if any_pass else "SYNTHETIC_SIGNATURE_NOT_IDENTIFIABLE"
    stage2_justified = bool(any_pass)

    completed_utc = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    report = {
        "schema": AGGREGATE_SCHEMA,
        "claim_class": CLAIM_CLASS,
        "interpretation_boundary": INTERPRETATION_BOUNDARY,
        "benchmark": "detector-redesign",
        "registry_entry": "Detector redesign or larger-eta regime before any Stage 2",
        "verdict": overall_verdict,
        "stage2_justified": stage2_justified,
        "passing_detectors": passing,
        "trial_count": total_trials,
        "trials_per_shard": trials_per_shard,
        "shard_count": len(receipts),
        "held_out_null_trials_total": int(np.sum(null_all & (split == 1))),
        "registered_gates": {
            "held_out_null_fpr_max": 0.015,
            "power_min_eta_ge_0p05_snr_ge_0db": 0.80,
            "correct_template_win_rate_min": 0.50,
        },
        "machinery_checks": machinery,
        "provenance": {
            **provenance,
            "inputs": {key: next(iter(hashes)) for key, hashes in input_hashes.items()},
            "stage1_aggregate_sha256": sha256_file(stage1_dir / "aggregate.stdout.json"),
        },
        "detectors": detectors,
        "runtime": {
            "aggregate_started_utc": started_utc,
            "aggregate_completed_utc": completed_utc,
            "slurm_job_id": os.environ.get("SLURM_JOB_ID"),
            "python": platform.python_version(),
            "shard_jobs": slurm_jobs,
        },
        "shards": shard_hashes,
    }
    output_prefix.parent.mkdir(parents=True, exist_ok=True)
    json_path = output_prefix.with_suffix(".json")
    json_path.write_text(
        json.dumps(serializable(report), indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )

    # --- Markdown verdict report (verdict first).
    lines: list[str] = []
    lines.append("# Tandem 10-9-1 detector-redesign benchmark verdict")
    lines.append("")
    lines.append(f"**VERDICT: `{overall_verdict}`**")
    lines.append("")
    lines.append(
        f"**Stage 2 justified:** {'YES — at least one redesigned detector meets the pre-registered gates' if stage2_justified else 'NO — no detector meets the pre-registered gates; the claim is not testable at the pre-registered effect size (decisive negative)'}"
    )
    lines.append("")
    lines.append(
        f"- Trials: {total_trials:,} ({args.expected_shards} shards x {trials_per_shard}); "
        f"held-out nulls: {int(np.sum(null_all & (split == 1))):,} (gate estimation >= 100k requirement)"
    )
    lines.append(
        f"- DGP: pre-registered Stage 1 harness, verified bit-identical (see machinery checks); "
        f"commit f5fb1916, harness sha256 {next(iter(input_hashes['registered_harness_sha256']))[:16]}..."
    )
    lines.append("")
    lines.append("## Machinery checks")
    lines.append("")
    lines.append(
        f"- Stage 1 trial-stream bit-reproduction (first {args.stage1_trials} trials/shard, 12 keys): "
        f"{'EXACT' if bit_repro['dgp_gpu_bit_reproduction_all_shards'] else 'NOT EXACT — see verdict JSON'}"
    )
    mm = machinery["d0_stage1_headline_reproduction"]
    lines.append(
        f"- D0 control headline reproduction on the Stage 1 subset: FPR {mm['redesign_fpr']:.6%} "
        f"(Stage 1: {mm['stage1_fpr']:.6%}), target power {mm['redesign_target_power']:.6%} "
        f"(Stage 1: {mm['stage1_target_power']:.6%}), shifted-win {mm['redesign_shifted_win_rate']:.6%} "
        f"(Stage 1: {mm['stage1_shifted_win_rate']:.6%}); match: {mm['all_match_1e_12']}"
    )
    lines.append("")
    lines.append("## Per-detector gates")
    lines.append("")
    lines.append(
        "| Detector | Held-out null FPR (gate <= 1.5%) | Power eta>=0.05, SNR>=0 dB (gate >= 80%) | Power eta=0.05, SNR=0 dB | Template beats shifted | Gates passed |"
    )
    lines.append("|---|---|---|---|---|---|")
    label = {
        "D0_preregistered_discriminant": "D0 pre-registered discriminant (control)",
        "D1_matched_filter_glrt": "D1 matched filter / GLRT",
        "D2_xcf_peak_lag_sweep": "D2 cross-correlation lag sweep",
        "D3_spectral_comb_cepstrum": "D3 spectral comb (cepstrum)",
        "D4_learned_gbt_windowed_features": "D4 learned GBT (cross-fitted)",
    }
    for name, det in detectors.items():
        ov = det["overall"]
        lines.append(
            f"| {label[name]} | {ov['held_out_null_false_positive_rate']:.4%} | "
            f"{ov['target_power_eta_ge_0p05_snr_ge_0db']:.4%} | "
            f"{ov['power_at_eta_0p05_snr_0db']:.4%} | "
            f"{det['gate3_correct_template_beats_shifted']:.4%} | "
            f"{'PASS' if det['gates_passed'] else 'FAIL'} |"
        )
    lines.append("")
    lines.append("## Minimum eta at 80% power (pooled over operators, SNR >= 0 dB)")
    lines.append("")
    lines.append("| Detector | all noise | white | AR(1) | two-timescale |")
    lines.append("|---|---|---|---|---|")
    for name, det in detectors.items():
        mn = det["overall"]["minimum_eta_at_80pct_power"]
        def fmt(v):
            return f"{v:g}" if v is not None else "none (not reached at eta <= 0.2)"
        lines.append(
            f"| {label[name]} | {fmt(mn['snr_ge_0db_all_noise'])} | {fmt(mn['snr_ge_0db_white'])} | "
            f"{fmt(mn['snr_ge_0db_ar1_0p9'])} | {fmt(mn['snr_ge_0db_two_timescale'])} |"
        )
    lines.append("")
    lines.append(
        "Per-stratum minimum-eta values (3 operators x 3 noise families x 4 SNR) are in the verdict JSON."
    )
    lines.append("")
    lines.append("## Power curves (pooled over operators)")
    lines.append("")
    for name, det in detectors.items():
        lines.append(f"### {label[name]}")
        lines.append("")
        lines.append("| Noise / SNR | eta=0.02 | eta=0.05 | eta=0.10 | eta=0.20 |")
        lines.append("|---|---|---|---|---|")
        curves = det["overall"]["power_curves_pooled_over_operators"]
        for noise_name in ("white", "ar1_0p9"):
            for snr_level in (-10.0, 0.0, 10.0, 20.0):
                entry = curves[f"{noise_name}/{snr_level:g}dB"]
                lines.append(
                    f"| {noise_name} {snr_level:g} dB | {entry['0.020']:.3f} | {entry['0.050']:.3f} | "
                    f"{entry['0.100']:.3f} | {entry['0.200']:.3f} |"
                )
        lines.append("")
    lines.append("## D4 learned-detector honesty checks")
    lines.append("")
    d4det = detectors["D4_learned_gbt_windowed_features"]
    lines.append(
        f"- Training: {d4det['training_protocol']['train_positives']:,} train positives + "
        f"{d4det['training_protocol']['calibration_nulls']:,} calibration nulls; thresholds from 5-fold "
        "out-of-fold calibration-null scores (per-stratum p99)."
    )
    lines.append(
        f"- Honest evaluation: {d4det['training_protocol']['test_positives']:,} test positives + "
        f"{d4det['training_protocol']['evaluation_nulls']:,} held-out evaluation nulls, never used in training."
    )
    lines.append(
        f"- Generalization: apparent target power on train positives "
        f"{d4det['generalization']['apparent_target_power_on_train_positives']:.4%} vs honest held-out "
        f"{d4det['generalization']['honest_target_power_on_test_positives']:.4%} "
        f"(gap {d4det['generalization']['generalization_gap']:.4%})."
    )
    lines.append(
        f"- Held-out probability calibration max |decile gap|: "
        f"{d4det['calibration']['max_abs_reliability_gap_held_out']}"
    )
    lines.append("")
    lines.append("## Interpretation boundary")
    lines.append("")
    lines.append(
        "This benchmark measures synthetic identifiability only, on the pre-registered synthetic "
        "data-generating process. It is not a physical observation, not independent replication, and "
        "cannot prove that physical reality branches. A positive identifiability verdict only makes a "
        "pre-registered Stage 2 physical-protocol design justifiable; it is not itself evidence for H1."
    )
    lines.append("")
    md_path = output_prefix.with_suffix(".md")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(serializable(report), indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
