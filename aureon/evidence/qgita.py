"""QGITA analyzer on synthetic impulses, scored against two standard detectors.

The system under test is a fresh `QGITAMarketAnalyzer` per trial, using its
constructor defaults. A positive QGITA call is the analyzer's own gate:
`ftcp_count > 0` or `lhe_count > 0`. Scores used for ROC are the analyzer's
own `max_g_eff`, lighthouse intensity, `q_anomaly`, and `global_R`.

The impulse, the SNR ladder, and the energy and oracle detectors are harness
baselines. They are not QGITA formulas, and no QGITA threshold is tuned.
"""

from __future__ import annotations

import random
from typing import Any

from aureon.evidence.metrics import auroc, auroc_interval, fraction_above, rates, upper_threshold
from aureon.evidence.serialize import csv_text

MASTER_SEED = 20261105
SAMPLES = 180
TRIALS = 200
CALIBRATION_TRIALS = 400
CALIBRATION_SEED_START = 50_000_000
SNR_DB = (-12, -6, 0, 6, 12, 18, 24, 30, 36)
FALSE_ALARM_TAIL = 0.05
TRIAL_FIELDS = [
    "placement",
    "snr_db",
    "trial",
    "kind",
    "seed",
    "inject_index",
    "amplitude",
    "ftcp_count",
    "lhe_count",
    "max_g_eff",
    "lighthouse",
    "q_anomaly",
    "global_r",
    "c_linear",
    "c_phi",
    "structural_event",
    "energy",
    "oracle",
    "shuffled_ftcp_count",
    "shuffled_max_g_eff",
]


def _amplitude(snr_db: int) -> float:
    return 10.0 ** (snr_db / 20.0)


def _sites(n: int) -> dict[str, Any]:
    from aureon.wisdom.aureon_qgita_framework import FibonacciTimeLattice, FTCPDetector

    lattice = FibonacciTimeLattice()
    epsilon = float(FTCPDetector().epsilon)
    eligible = []
    knot_indexes = set()
    for knot in lattice.knots:
        if 0 <= knot.tau < n and abs(knot.tau - round(knot.tau)) <= 1e-9:
            knot_indexes.add(int(round(knot.tau)))
        if knot.k < 2 or knot.k + 1 >= len(lattice.knots):
            continue
        prev_tau = float(lattice.knots[knot.k - 1].tau)
        next_tau = float(lattice.knots[knot.k + 1].tau)
        if not (0 <= prev_tau < n and 0 <= knot.tau < n and 0 <= next_tau < n):
            continue
        if knot.phi_deviation > epsilon:
            continue
        sample = int(round(knot.tau))
        if abs(knot.tau - sample) > 1e-9:
            continue
        eligible.append(
            {
                "knot_index": int(knot.k),
                "tau": float(knot.tau),
                "phi_deviation": float(knot.phi_deviation),
                "gap_product": (next_tau - float(knot.tau)) * (float(knot.tau) - prev_tau),
                "sample": sample,
            }
        )
    if not eligible:
        raise RuntimeError("no Fibonacci knot with both neighbors inside the series")
    tight = min(eligible, key=lambda item: (item["gap_product"], item["knot_index"]))
    mid = min(eligible, key=lambda item: (abs(item["tau"] - (n / 3.0)), item["knot_index"]))
    next_tau = float(lattice.knots[mid["knot_index"] + 1].tau)
    midpoint = int(round((mid["tau"] + next_tau) / 2.0))
    off_index = None
    for delta in range(n):
        for candidate in (midpoint - delta, midpoint + delta):
            if 0 <= candidate < n and candidate not in knot_indexes:
                off_index = candidate
                break
        if off_index is not None:
            break
    if off_index is None:
        raise RuntimeError("no off-lattice sample")
    return {
        "samples": n,
        "rule": (
            "Eligible knots have phi_deviation <= FTCPDetector.epsilon and both neighbor knots inside "
            "the series. tight_lattice is the eligible knot with the smallest product of the adjacent "
            "knot gaps. mid_lattice is the eligible knot closest to N/3. off_lattice is the integer "
            "nearest the midpoint from mid_lattice toward the next knot that is not itself a knot time."
        ),
        "epsilon": epsilon,
        "tight_lattice": tight,
        "mid_lattice": mid,
        "off_lattice": {"sample": off_index},
    }


def _noise(seed: int, n: int) -> list[float]:
    rng = random.Random(seed)
    return [rng.gauss(0.0, 1.0) for _ in range(n)]


def _analyze(samples: list[float]) -> dict[str, float | int | bool]:
    from aureon.wisdom.aureon_qgita_framework import QGITAMarketAnalyzer

    analyzer = QGITAMarketAnalyzer()
    for index, value in enumerate(samples):
        analyzer.feed_price(float(value), timestamp=float(index))
    raw = analyzer.analyze()
    if raw.get("status") != "complete":
        raise RuntimeError(f"QGITA analyze status {raw.get('status')!r}")
    stage1 = raw["stage1"]
    stage2 = raw["stage2"]
    coherence = raw["coherence"]
    signals = raw["signals"]
    return {
        "ftcp_count": int(stage1["ftcp_count"]),
        "lhe_count": int(stage2["lhe_count"]),
        "max_g_eff": float(stage1["max_g_eff"]),
        "lighthouse": float(stage2["current_lighthouse_intensity"]),
        "q_anomaly": float(coherence["q_anomaly"]),
        "global_r": float(coherence["global_R"]),
        "c_linear": float(coherence["c_linear"]),
        "c_phi": float(coherence["c_phi"]),
        "structural_event": bool(signals["structural_event"]),
        "epsilon": float(analyzer.ftcp_detector.epsilon),
        "theta": float(analyzer.ftcp_detector.theta),
        "alpha": float(analyzer.ftcp_detector.alpha),
        "adaptive_threshold": bool(analyzer.ftcp_detector.adaptive_threshold),
        "lighthouse_threshold_sigma": float(analyzer.lighthouse.threshold_sigma),
    }


def _energy(samples: list[float]) -> float:
    return max(value * value for value in samples)


def _oracle(samples: list[float], index: int) -> float:
    value = samples[index]
    return value * value


def _trial_seed(placement_id: int, snr_index: int, trial: int) -> int:
    return MASTER_SEED + placement_id * 100_000 + snr_index * 1_000 + trial


def _row(
    placement: str,
    snr_db: int,
    trial: int,
    kind: str,
    seed: int,
    inject_index: int,
    samples: list[float],
    reading: dict[str, Any],
    shuffled: dict[str, Any] | None,
) -> dict[str, Any]:
    amplitude = 0.0 if kind == "null" else _amplitude(snr_db)
    return {
        "placement": placement,
        "snr_db": snr_db,
        "trial": trial,
        "kind": kind,
        "seed": seed,
        "inject_index": inject_index,
        "amplitude": amplitude,
        "ftcp_count": reading["ftcp_count"],
        "lhe_count": reading["lhe_count"],
        "max_g_eff": reading["max_g_eff"],
        "lighthouse": reading["lighthouse"],
        "q_anomaly": reading["q_anomaly"],
        "global_r": reading["global_r"],
        "c_linear": reading["c_linear"],
        "c_phi": reading["c_phi"],
        "structural_event": reading["structural_event"],
        "energy": _energy(samples),
        "oracle": _oracle(samples, inject_index),
        "shuffled_ftcp_count": None if shuffled is None else shuffled["ftcp_count"],
        "shuffled_max_g_eff": None if shuffled is None else shuffled["max_g_eff"],
    }


def _cell(
    rows: list[dict[str, Any]],
    energy_threshold: float,
    oracle_threshold: float,
    ftcp_threshold: float,
    lighthouse_threshold: float,
) -> dict[str, Any]:
    labels = [row["kind"] == "signal" for row in rows]
    signal_rows = [row for row in rows if row["kind"] == "signal"]
    n_signal = sum(1 for label in labels if label)
    n_null = sum(1 for label in labels if not label)

    def score_auroc(key: str) -> dict[str, Any]:
        positive = [float(row[key]) for row in rows if row["kind"] == "signal"]
        negative = [float(row[key]) for row in rows if row["kind"] == "null"]
        score = auroc(positive, negative)
        return {
            "auroc": score,
            "ci95": auroc_interval(score, len(positive), len(negative)),
            "interval": "Hanley-McNeil normal approximation; it collapses at 0 and 1",
        }

    shuffled = [row for row in signal_rows if row["shuffled_ftcp_count"] is not None]
    shuffled_rate = None
    if shuffled:
        shuffled_rate = sum(1 for row in shuffled if row["shuffled_ftcp_count"] > 0) / len(shuffled)
    return {
        "placement": rows[0]["placement"],
        "snr_db": rows[0]["snr_db"],
        "amplitude": rows[0]["amplitude"] if rows[0]["kind"] == "signal" else _amplitude(int(rows[0]["snr_db"])),
        "inject_index": rows[0]["inject_index"],
        "signal_trials": n_signal,
        "null_trials": n_null,
        "ftcp": rates(labels, [row["max_g_eff"] > ftcp_threshold for row in rows]),
        "lhe": rates(labels, [row["lighthouse"] > lighthouse_threshold for row in rows]),
        "native_ftcp": rates(labels, [row["ftcp_count"] > 0 for row in rows]),
        "native_lhe": rates(labels, [row["lhe_count"] > 0 for row in rows]),
        "energy": rates(labels, [row["energy"] > energy_threshold for row in rows]),
        "oracle": rates(labels, [row["oracle"] > oracle_threshold for row in rows]),
        "auroc": {
            "max_g_eff": score_auroc("max_g_eff"),
            "lighthouse": score_auroc("lighthouse"),
            "q_anomaly": score_auroc("q_anomaly"),
            "global_r": score_auroc("global_r"),
            "c_linear": score_auroc("c_linear"),
            "c_phi": score_auroc("c_phi"),
            "energy": score_auroc("energy"),
            "oracle": score_auroc("oracle"),
        },
        "shuffled_signal_ftcp_rate": shuffled_rate,
    }


def run_qgita() -> dict[str, Any]:
    sites = _sites(SAMPLES)
    placements = (
        ("tight_lattice", 0, int(sites["tight_lattice"]["sample"])),
        ("mid_lattice", 1, int(sites["mid_lattice"]["sample"])),
        ("off_lattice", 2, int(sites["off_lattice"]["sample"])),
    )
    calibration_energy: list[float] = []
    calibration_oracle: list[float] = []
    calibration_g_eff: list[float] = []
    calibration_lighthouse: list[float] = []
    calibration_rows: list[dict[str, Any]] = []
    detector = None
    oracle_index = int(sites["tight_lattice"]["sample"])
    for trial in range(CALIBRATION_TRIALS):
        seed = CALIBRATION_SEED_START + trial
        samples = _noise(seed, SAMPLES)
        reading = _analyze(samples)
        energy = _energy(samples)
        oracle = _oracle(samples, oracle_index)
        calibration_energy.append(energy)
        calibration_oracle.append(oracle)
        calibration_g_eff.append(float(reading["max_g_eff"]))
        calibration_lighthouse.append(float(reading["lighthouse"]))
        if detector is None:
            detector = {
                "epsilon": reading["epsilon"],
                "theta": reading["theta"],
                "alpha": reading["alpha"],
                "adaptive_threshold": reading["adaptive_threshold"],
                "lighthouse_threshold_sigma": reading["lighthouse_threshold_sigma"],
            }
        calibration_rows.append(
            {
                "trial": trial,
                "seed": seed,
                "energy": energy,
                "oracle_at_calibration_index": oracle,
                "max_g_eff": reading["max_g_eff"],
                "lighthouse": reading["lighthouse"],
                "ftcp_count": reading["ftcp_count"],
                "lhe_count": reading["lhe_count"],
            }
        )
    energy_threshold = upper_threshold(calibration_energy, FALSE_ALARM_TAIL)
    oracle_threshold = upper_threshold(calibration_oracle, FALSE_ALARM_TAIL)
    ftcp_threshold = upper_threshold(calibration_g_eff, FALSE_ALARM_TAIL)
    lighthouse_threshold = upper_threshold(calibration_lighthouse, FALSE_ALARM_TAIL)

    rows: list[dict[str, Any]] = []
    for placement, placement_id, inject_index in placements:
        for snr_index, snr_db in enumerate(SNR_DB):
            amplitude = _amplitude(snr_db)
            for trial in range(TRIALS):
                seed = _trial_seed(placement_id, snr_index, trial)
                noise = _noise(seed, SAMPLES)
                signal = list(noise)
                signal[inject_index] += amplitude
                null_reading = _analyze(noise)
                signal_reading = _analyze(signal)
                shuffled_samples = list(signal)
                random.Random(seed + 50_000).shuffle(shuffled_samples)
                shuffled_reading = _analyze(shuffled_samples)
                rows.append(
                    _row(placement, snr_db, trial, "null", seed, inject_index, noise, null_reading, None)
                )
                rows.append(
                    _row(
                        placement,
                        snr_db,
                        trial,
                        "signal",
                        seed,
                        inject_index,
                        signal,
                        signal_reading,
                        shuffled_reading,
                    )
                )

    cells = []
    for placement, _placement_id, _inject_index in placements:
        for snr_db in SNR_DB:
            group = [row for row in rows if row["placement"] == placement and row["snr_db"] == snr_db]
            cells.append(
                _cell(group, energy_threshold, oracle_threshold, ftcp_threshold, lighthouse_threshold)
            )

    summary = {
        "schema": "aureon.evidence.qgita.v1",
        "live_trading": False,
        "external_llm": False,
        "orders_placed": False,
        "source": "aureon.wisdom.aureon_qgita_framework.QGITAMarketAnalyzer.analyze",
        "detector_defaults": detector,
        "harness": {
            "signal": "one-sample impulse added to unit-variance Gaussian noise",
            "noise": "random.Random(seed).gauss(0, 1), one generator per trial",
            "snr_db": "10 * log10(A**2 / 1) = 20 * log10(A), with noise variance 1",
            "snr_grid_db": list(SNR_DB),
            "samples": SAMPLES,
            "trials_per_kind": TRIALS,
            "master_seed": MASTER_SEED,
            "trial_seed": "master + placement_id * 100000 + snr_index * 1000 + trial",
            "null_and_signal_share_noise": True,
            "shuffle": "stdlib Random(seed + 50000).shuffle of the signal trial",
            "energy_detector": "max of squared samples; location unknown; harness baseline",
            "oracle_detector": "squared sample at the known injection index; harness baseline",
            "positive_call": (
                "score > threshold. QGITA thresholds are on max_g_eff and lighthouse intensity, "
                "the analyzer's existing scores. Energy and oracle use their own scores."
            ),
            "qgita_thresholds": (
                "fit only on calibration nulls so about 5 percent of those null scores lie strictly above "
                "the threshold. Evaluation seeds are disjoint. Constructor defaults of the analyzer are unchanged. "
                "native_ftcp and native_lhe in each cell are the untuned gates, kept for comparison."
            ),
            "auroc": "Mann-Whitney, ties count 1/2, higher score ranks as the injected class",
            "scores_not_flipped": True,
        },
        "injection": sites,
        "calibration": {
            "trials": CALIBRATION_TRIALS,
            "seed_start": CALIBRATION_SEED_START,
            "tail": FALSE_ALARM_TAIL,
            "threshold_index": "ceil((1 - tail) * n) - 1 on sorted null scores",
            "energy_threshold": energy_threshold,
            "oracle_threshold": oracle_threshold,
            "ftcp_max_g_eff_threshold": ftcp_threshold,
            "lighthouse_intensity_threshold": lighthouse_threshold,
            "ftcp_calibration_false_alarm_rate": fraction_above(calibration_g_eff, ftcp_threshold),
            "lighthouse_calibration_false_alarm_rate": fraction_above(
                calibration_lighthouse, lighthouse_threshold
            ),
            "oracle_index": oracle_index,
            "energy_calibration_false_alarm_rate": fraction_above(calibration_energy, energy_threshold),
            "oracle_calibration_false_alarm_rate": fraction_above(calibration_oracle, oracle_threshold),
            "note": (
                "Calibration nulls are not the evaluation nulls. "
                "The cell false-alarm rates for energy and oracle are on the evaluation nulls."
            ),
        },
        "cells": cells,
    }
    return {
        "summary": summary,
        "trials_csv": csv_text(TRIAL_FIELDS, rows),
        "calibration_csv": csv_text(
            [
                "trial",
                "seed",
                "energy",
                "oracle_at_calibration_index",
                "max_g_eff",
                "lighthouse",
                "ftcp_count",
                "lhe_count",
            ],
            calibration_rows,
        ),
    }
