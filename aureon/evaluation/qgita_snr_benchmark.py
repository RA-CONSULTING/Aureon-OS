"""QGITA curvature detection against a known bump, plus an unlabelled series.

Synthetic trials plant one spike on a golden-ratio lattice knot, or plant
nothing. The FTCP score is the largest valid ``g_eff``. The baseline score
is the largest absolute step on the same samples. Thresholds are frozen on
the calibration seed and scored on the evaluation seed. A series with no
signal-in-noise labels is HOLD for detection rate and false-alarm rate.
"""

from __future__ import annotations

import csv
import random
from pathlib import Path
from typing import Any

CALIBRATION_SEED = 20261024
EVAL_SEED = 777
TRIALS_PER_CLASS = 80
TARGET_FPR = 0.10
PUBLIC_SERIES = "data/de440_timeseries.csv"
PUBLIC_COLUMN = "Lambda"


def _auc(scores: list[float], labels: list[int]) -> float | None:
    positive = [score for score, label in zip(scores, labels) if label == 1]
    negative = [score for score, label in zip(scores, labels) if label == 0]
    if not positive or not negative:
        return None
    wins = 0.0
    for score in positive:
        wins += sum(score > other for other in negative)
        wins += 0.5 * sum(score == other for other in negative)
    return wins / (len(positive) * len(negative))


def _rates(scores: list[float], labels: list[int], threshold: float) -> dict[str, float | int | None]:
    tp = fp = tn = fn = 0
    for score, label in zip(scores, labels):
        called = score >= threshold
        if called and label == 1:
            tp += 1
        elif called and label == 0:
            fp += 1
        elif label == 0:
            tn += 1
        else:
            fn += 1
    detection = tp / (tp + fn) if (tp + fn) else None
    false_alarm = fp / (fp + tn) if (fp + tn) else None
    return {
        "threshold": threshold,
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "detection_rate": detection,
        "false_alarm_rate": false_alarm,
    }


def _roc(scores: list[float], labels: list[int]) -> list[dict[str, float | None]]:
    thresholds = sorted(set(scores), reverse=True)
    curve = [_rates(scores, labels, max(scores) + 1.0)]
    curve.extend(_rates(scores, labels, threshold) for threshold in thresholds)
    curve.append(_rates(scores, labels, min(scores) - 1.0))
    return [
        {"threshold": row["threshold"], "detection_rate": row["detection_rate"], "false_alarm_rate": row["false_alarm_rate"]}
        for row in curve
    ]


def _freeze_threshold(scores: list[float], labels: list[int], target_fpr: float) -> float:
    """Highest-detection threshold whose calibration false-alarm rate is at most the target.

    If every threshold exceeds the target, use the one closest to it.
    """

    candidates = sorted(set(scores))
    best_under: tuple[float, float] | None = None
    closest: tuple[float, float] | None = None
    for threshold in candidates:
        rates = _rates(scores, labels, threshold)
        false_alarm = float(rates["false_alarm_rate"] or 0.0)
        detection = float(rates["detection_rate"] or 0.0)
        gap = abs(false_alarm - target_fpr)
        if closest is None or gap < closest[0]:
            closest = (gap, threshold)
        if false_alarm <= target_fpr + 1e-12:
            if best_under is None or detection > best_under[0] or (
                detection == best_under[0] and threshold > best_under[1]
            ):
                best_under = (detection, threshold)
    if best_under is not None:
        return best_under[1]
    return closest[1] if closest is not None else 0.0


def _plant_design(detector: Any) -> dict[str, float | int]:
    knots = detector.lattice.knots
    chosen = None
    for knot in knots:
        if knot.k < 2:
            continue
        if knot.phi_deviation <= detector.epsilon:
            chosen = knot
            break
    if chosen is None:
        raise RuntimeError("lattice has no golden knot inside epsilon")
    prev_tau = knots[chosen.k - 1].tau
    next_tau = knots[chosen.k + 1].tau
    dt_back = chosen.tau - prev_tau
    dt_fwd = next_tau - chosen.tau
    # Noiseless curvature of a spike of height A is -2A / (dt_fwd * dt_back).
    amplitude = 5.0 * detector.theta * dt_fwd * dt_back / 2.0
    sigma = amplitude / 2.0
    return {
        "knot_index": int(chosen.k),
        "tau": float(chosen.tau),
        "dt_back": float(dt_back),
        "dt_fwd": float(dt_fwd),
        "amplitude": float(amplitude),
        "sigma": float(sigma),
        "noiseless_abs_curvature_over_theta": 5.0,
    }


def _trials(seed: int, design: dict[str, Any], per_class: int) -> list[dict[str, Any]]:
    from aureon.wisdom.aureon_qgita_framework import FTCPDetector
    import numpy as np

    rng = random.Random(seed)
    rows: list[dict[str, Any]] = []
    for planted in (0, 1):
        for _ in range(per_class):
            detector = FTCPDetector(epsilon=0.05, theta=0.1, alpha=1.0, adaptive_threshold=False)
            times = np.array([knot.tau for knot in detector.lattice.knots], dtype=float)
            values = [rng.gauss(0.0, float(design["sigma"])) for _ in times]
            index = int(design["knot_index"])
            if planted:
                values[index] += float(design["amplitude"])
            ftcps = detector.detect_ftcps(times, np.array(values, dtype=float))
            ftcp_score = max((float(item.g_eff) for item in ftcps if item.is_valid), default=0.0)
            steps = [abs(values[i] - values[i - 1]) for i in range(1, len(values))]
            baseline_score = max(steps) if steps else 0.0
            rows.append(
                {
                    "planted": planted,
                    "ftcp_score": ftcp_score,
                    "baseline_score": baseline_score,
                    "valid_ftcps": sum(1 for item in ftcps if item.is_valid),
                }
            )
    return rows


def _split_report(rows: list[dict[str, Any]], score_key: str, threshold: float | None) -> dict[str, Any]:
    scores = [float(row[score_key]) for row in rows]
    labels = [int(row["planted"]) for row in rows]
    frozen = _freeze_threshold(scores, labels, TARGET_FPR) if threshold is None else threshold
    rates = _rates(scores, labels, frozen)
    return {
        "score": score_key,
        "auc": _auc(scores, labels),
        "threshold": frozen,
        "threshold_source": "calibration" if threshold is None else "frozen_from_calibration",
        "detection_rate": rates["detection_rate"],
        "false_alarm_rate": rates["false_alarm_rate"],
        "tp": rates["tp"],
        "fp": rates["fp"],
        "tn": rates["tn"],
        "fn": rates["fn"],
        "roc": _roc(scores, labels) if threshold is not None else [],
    }


def _public_series(root: Path) -> dict[str, Any]:
    path = root / PUBLIC_SERIES
    if not path.is_file():
        return {
            "verdict": "HOLD",
            "path": str(path),
            "reason": "the public series file is not in this checkout",
            "detection_rate": None,
            "false_alarm_rate": None,
            "auc": None,
        }
    values: list[float] = []
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or PUBLIC_COLUMN not in reader.fieldnames:
            return {
                "verdict": "HOLD",
                "path": str(path),
                "reason": f"column {PUBLIC_COLUMN} is missing",
                "detection_rate": None,
                "false_alarm_rate": None,
                "auc": None,
            }
        for row in reader:
            try:
                values.append(float(row[PUBLIC_COLUMN]))
            except (TypeError, ValueError):
                continue
    if len(values) < 3:
        return {
            "verdict": "HOLD",
            "path": str(path),
            "reason": "the series has fewer than three numeric samples",
            "samples": len(values),
            "detection_rate": None,
            "false_alarm_rate": None,
            "auc": None,
        }
    from aureon.wisdom.aureon_qgita_framework import FTCPDetector
    import numpy as np

    detector = FTCPDetector(epsilon=0.05, theta=0.1, alpha=1.0, adaptive_threshold=False)
    last_fib = detector.lattice.knots[-1].fib_number
    delta = (len(values) - 1) / last_fib if last_fib else 1.0
    detector.lattice.delta_t = delta
    detector.lattice.knots = detector.lattice._generate_knots()
    times = np.arange(len(values), dtype=float)
    found = detector.detect_ftcps(times, np.array(values, dtype=float))
    valid = [item for item in found if item.is_valid]
    return {
        "verdict": "HOLD",
        "path": PUBLIC_SERIES,
        "column": PUBLIC_COLUMN,
        "samples": len(values),
        "reason": (
            "de440_timeseries.csv is the ephemeris series already in the repo. "
            "Its conjunction and opposition columns are not signal-in-noise ground truth, "
            "so detection rate, false-alarm rate, and AUC are not claimed."
        ),
        "valid_ftcp_count": len(valid),
        "max_g_eff": max((float(item.g_eff) for item in valid), default=0.0),
        "ftcps": [
            {"tau": float(item.timestamp), "knot_index": int(item.knot_index), "g_eff": float(item.g_eff)}
            for item in valid
        ],
        "detection_rate": None,
        "false_alarm_rate": None,
        "auc": None,
    }


def evaluate_qgita_snr(root: Path | None = None) -> dict[str, Any]:
    from aureon.wisdom.aureon_qgita_framework import FTCPDetector

    root = Path(root or Path.cwd())
    design = _plant_design(FTCPDetector(epsilon=0.05, theta=0.1, alpha=1.0, adaptive_threshold=False))
    calibration = _trials(CALIBRATION_SEED, design, TRIALS_PER_CLASS)
    evaluation = _trials(EVAL_SEED, design, TRIALS_PER_CLASS)
    ftcp_cal = _split_report(calibration, "ftcp_score", None)
    base_cal = _split_report(calibration, "baseline_score", None)
    ftcp_eval = _split_report(evaluation, "ftcp_score", float(ftcp_cal["threshold"]))
    base_eval = _split_report(evaluation, "baseline_score", float(base_cal["threshold"]))
    return {
        "schema": "aureon.qgita-snr-benchmark.v1",
        "live_trading": False,
        "detector": "aureon.wisdom.aureon_qgita_framework.FTCPDetector",
        "detector_settings": {
            "epsilon": 0.05,
            "theta": 0.1,
            "alpha": 1.0,
            "adaptive_threshold": False,
        },
        "baseline": "max absolute adjacent difference on the same lattice samples",
        "seeds": {"calibration": CALIBRATION_SEED, "evaluation": EVAL_SEED},
        "trials_per_class": TRIALS_PER_CLASS,
        "target_false_alarm_rate": TARGET_FPR,
        "plant": design,
        "calibration": {"ftcp": ftcp_cal, "baseline": base_cal},
        "evaluation": {"ftcp": ftcp_eval, "baseline": base_eval},
        "trials": {"calibration": calibration, "evaluation": evaluation},
        "public_series": _public_series(root),
    }


def render_qgita_markdown(report: dict[str, Any]) -> str:
    ftcp = report["evaluation"]["ftcp"]
    baseline = report["evaluation"]["baseline"]
    public = report["public_series"]
    lines = [
        "# QGITA signal-to-noise benchmark",
        "",
        f"Detector `{report['detector']}`. Baseline: {report['baseline']}.",
        f"Calibration seed `{report['seeds']['calibration']}`, evaluation seed `{report['seeds']['evaluation']}`.",
        f"{report['trials_per_class']} planted trials and {report['trials_per_class']} noise trials in each split.",
        "Thresholds are frozen on the calibration split at a false-alarm target of "
        f"{report['target_false_alarm_rate']}. Live trading is off.",
        "",
        "| detector | AUC | detection rate | false-alarm rate |",
        "| --- | ---: | ---: | ---: |",
        f"| FTCP | {ftcp['auc']:.4f} | {ftcp['detection_rate']:.4f} | {ftcp['false_alarm_rate']:.4f} |",
        f"| baseline | {baseline['auc']:.4f} | {baseline['detection_rate']:.4f} | {baseline['false_alarm_rate']:.4f} |",
        "",
        f"Public series `{public.get('path', '')}`: **{public['verdict']}**. {public['reason']}",
        "",
    ]
    return "\n".join(lines)
