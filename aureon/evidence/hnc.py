"""Λ(t) and coherence from HarmonicRealityField, plus null baselines.

The field is stepped with the constructor defaults. Seeds are set around each
run. The field's own coherence method scores a zero series, a shuffle of Λ(t),
and unit Gaussian noise. Those three series are baselines, not new fields.
"""

from __future__ import annotations

import hashlib
import random
from typing import Any

from aureon.evidence.serialize import csv_text, dump

STEPS = 1000
SEEDS = (0, 1, 7, 42, 20261105)
SHUFFLE_SEED = 20261105
GAUSSIAN_SEED = 20261105
REPEAT_SEED = 0


def _sha(series: list[float]) -> str:
    return hashlib.sha256(dump(series).encode("utf-8")).hexdigest()


def _max_abs_diff(left: list[float], right: list[float]) -> float:
    if len(left) != len(right):
        raise ValueError("series lengths differ")
    return max(abs(a - b) for a, b in zip(left, right, strict=True))


def _run(enable_multiverse: bool, seed: int) -> dict[str, Any]:
    import numpy as np

    from aureon.harmonic.aureon_harmonic_reality import HarmonicRealityField

    random.seed(seed)
    np.random.seed(seed)
    field = HarmonicRealityField(enable_multiverse=enable_multiverse)
    series = [float(field.step()) for _ in range(STEPS)]
    if len(series) != STEPS:
        raise RuntimeError("step count drifted")
    half = len(series) // 2
    nyquist = float(field.sample_rate) / 2.0
    above = [
        float(mode.frequency)
        for mode in field.substrate.modes
        if float(mode.frequency) >= nyquist
    ]
    return {
        "enable_multiverse": enable_multiverse,
        "seed": seed,
        "series": series,
        "steps": len(series),
        "dt": float(field.dt),
        "sample_rate": float(field.sample_rate),
        "sample_rate_requested": float(field.sample_rate_requested),
        "sample_rate_rule": field.sample_rate_rule,
        "coherence": float(field.coherence),
        "boundedness": float(field.boundedness),
        "echo_magnitude_ratio": float(field.echo.get_echo_magnitude_ratio()),
        "echo_magnitude_ratio_source": "aureon.harmonic.aureon_harmonic_reality.CausalEcho.get_echo_magnitude_ratio",
        "echo_magnitude_ratio_is_correlation": False,
        "state": str(field.state.value),
        "parameters": {
            "alpha": float(field.observer.alpha),
            "beta": float(field.echo.beta),
            "tau": float(field.echo.tau),
            "g": float(field.observer.g),
            "delta_t": float(field.observer.delta_t),
            "alpha_plus_beta": float(field.observer.alpha) + float(field.echo.beta),
        },
        "finite": all(value == value and abs(value) != float("inf") for value in series),
        "series_min": min(series),
        "series_max": max(series),
        "series_mean": sum(series) / len(series),
        "series_last": series[-1],
        "max_abs": max(abs(value) for value in series),
        "first_half_max_abs": max(abs(value) for value in series[:half]),
        "second_half_max_abs": max(abs(value) for value in series[half:]),
        "sha256": _sha(series),
        "modes": len(field.substrate.modes),
        "nyquist_hz": nyquist,
        "modes_at_or_above_nyquist": above,
        "metrics_note": (
            "HarmonicRealityField._update_metrics runs when the history length is a multiple of 100 "
            "and scores the last 1000 samples. 1000 steps is that window."
        ),
        "_field": field,
    }


def _baselines(reference: dict[str, Any]) -> dict[str, Any]:
    import numpy as np

    field = reference["_field"]
    series = reference["series"]
    shuffled = list(series)
    random.Random(SHUFFLE_SEED).shuffle(shuffled)
    gaussian_rng = random.Random(GAUSSIAN_SEED)
    gaussian = [gaussian_rng.gauss(0.0, 1.0) for _ in range(len(series))]
    zeros = [0.0] * len(series)

    def coherence(values: list[float]) -> float:
        return float(field._calculate_coherence(np.asarray(values, dtype=float)))

    return {
        "method": "HarmonicRealityField._calculate_coherence",
        "shuffle_seed": SHUFFLE_SEED,
        "gaussian_seed": GAUSSIAN_SEED,
        "gaussian": "unit variance, length equal to the formula-path series, stdlib random.Random.gauss",
        "shuffled_coherence": coherence(shuffled),
        "gaussian_coherence": coherence(gaussian),
        "zero_coherence": coherence(zeros),
        "shuffled_sha256": _sha(shuffled),
    }


def _public(run: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in run.items() if key not in {"series", "_field"}}


def _path(enable_multiverse: bool) -> dict[str, Any]:
    runs = [_run(enable_multiverse, seed) for seed in SEEDS]
    repeat = _run(enable_multiverse, REPEAT_SEED)
    reference = runs[0]
    seed_diffs = {
        str(run["seed"]): _max_abs_diff(reference["series"], run["series"]) for run in runs
    }
    summary = _public(reference)
    summary["seeds"] = list(SEEDS)
    summary["seed_sha256"] = {str(run["seed"]): run["sha256"] for run in runs}
    summary["max_abs_diff_across_seeds"] = max(seed_diffs.values())
    summary["seed_max_abs_diff"] = seed_diffs
    summary["repeat_seed"] = REPEAT_SEED
    summary["repeat_max_abs_diff"] = _max_abs_diff(reference["series"], repeat["series"])
    summary["head"] = reference["series"][:8]
    summary["tail"] = reference["series"][-8:]
    summary["source"] = "aureon.harmonic.aureon_harmonic_reality.HarmonicRealityField.step"
    if not enable_multiverse:
        summary["baselines"] = _baselines(reference)
    else:
        summary["baselines"] = {
            "note": (
                "The shuffled, Gaussian, and zero coherences are scored on the formula path. "
                "They are not repeated on the multiverse path."
            )
        }
    summary["series_reference_seed"] = reference["seed"]
    return {"summary": summary, "series": reference["series"]}


def _csv(series: list[float]) -> str:
    rows = [{"index": index, "lambda": value} for index, value in enumerate(series)]
    return csv_text(["index", "lambda"], rows)


def run_hnc() -> dict[str, Any]:
    formula = _path(False)
    multiverse = _path(True)
    formula["summary"]["multiverse_max_abs_diff"] = _max_abs_diff(
        formula["series"], multiverse["series"]
    )
    return {
        "summary": {
            "schema": "aureon.evidence.hnc.v1",
            "live_trading": False,
            "external_llm": False,
            "formula": formula["summary"],
            "multiverse": multiverse["summary"],
        },
        "formula_csv": _csv(formula["series"]),
        "multiverse_csv": _csv(multiverse["series"]),
    }
