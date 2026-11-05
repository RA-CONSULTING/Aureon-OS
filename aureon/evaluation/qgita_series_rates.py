"""Planted-impulse harness for QGITA, tagged ``synthetic_planted``.

Seeded shuffles and planted impulses live here. The tag is ``synthetic_planted``.
These numbers are not market rates, not telemetry, and not a field labelled
measured. Callers that write ``reports/measured`` must not copy them into
``detection_rate`` or ``false_alarm_rate``.
"""

from __future__ import annotations

import math
import random
from typing import Any

from aureon.evidence.metrics import fraction_above, rates, upper_threshold
from aureon.evidence.qgita import (
    CALIBRATION_SEED_START,
    FALSE_ALARM_TAIL,
    MASTER_SEED,
    SNR_DB,
    _amplitude,
    _analyze,
    _sites,
)

HEADLINE_PLACEMENT = "tight_lattice"
HEADLINE_SNR_DB = 0
_PLACEMENTS = (
    ("tight_lattice", 0),
    ("mid_lattice", 1),
    ("off_lattice", 2),
)


SYNTHETIC_PLANTED = "synthetic_planted"
_LABEL = "synthetic_planted. Seeded shuffles and planted impulses. Not a measured market rate."


def _envelope(payload: dict[str, Any]) -> dict[str, Any]:
    """Stamp every harness return ``synthetic_planted`` before it leaves this module."""

    payload["tag"] = SYNTHETIC_PLANTED
    payload["role"] = SYNTHETIC_PLANTED
    payload["counts_as_market_rate"] = False
    payload["counts_as_telemetry"] = False
    payload["label"] = _LABEL
    payload["orders_placed"] = False
    payload["rates_verdict"] = SYNTHETIC_PLANTED
    nested = payload.get("signal_in_noise")
    if isinstance(nested, dict):
        nested["tag"] = SYNTHETIC_PLANTED
        nested["verdict"] = SYNTHETIC_PLANTED
        nested["counts_as_market_rate"] = False
        nested["counts_as_telemetry"] = False
    return payload


def _hold(reason: str, samples: int | None = None) -> dict[str, Any]:
    body: dict[str, Any] = {
        "harness_status": "not_scored",
        "detection_rate": None,
        "detection_rate_ci95": None,
        "false_alarm_rate": None,
        "false_alarm_ci95": None,
        "rates_reason": reason,
        "signal_in_noise": {
            "verdict": "test_only",
            "reason": reason,
            "orders_placed": False,
        },
    }
    if samples is not None:
        body["signal_in_noise"]["samples"] = samples
    return _envelope(body)


def _unit_variance(values: list[float]) -> tuple[list[float], float, float] | None:
    if not values or any(not math.isfinite(value) for value in values):
        return None
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / len(values)
    if not variance > 0.0:
        return None
    scale = math.sqrt(variance)
    return [(value - mean) / scale for value in values], mean, scale


def _rotated(values: list[float], shift: int) -> list[float]:
    count = len(values)
    offset = shift % count
    if offset == 0:
        return list(values)
    return values[offset:] + values[:offset]


def _split(count: int) -> tuple[list[int], list[int]]:
    order = list(range(count))
    random.Random(CALIBRATION_SEED_START).shuffle(order)
    cut = count // 2
    calibration = order[:cut]
    held_out = order[cut:]
    random.Random(MASTER_SEED).shuffle(held_out)
    return calibration, held_out


def _call_rates(labels: list[bool], predictions: list[bool]) -> dict[str, Any]:
    scored = rates(labels, predictions)
    return {
        "tp": scored["tp"],
        "fp": scored["fp"],
        "tn": scored["tn"],
        "fn": scored["fn"],
        "precision": scored["precision"],
        "recall": scored["recall"],
        "false_alarm_rate": scored["false_alarm_rate"],
        "precision_ci95": scored["precision_ci95"],
        "recall_ci95": scored["recall_ci95"],
        "false_alarm_ci95": scored["false_alarm_ci95"],
    }


def measure_signal_in_noise(values: list[float]) -> dict[str, Any]:
    """Score planted impulses. The return is a test result, not a market rate."""

    count = len(values)
    if count < 10:
        return _hold(
            f"the series has {count} samples; QGITA analyze does not score a series that short",
            count,
        )
    try:
        sites = _sites(count)
    except RuntimeError as exc:
        return _hold(
            f"the series has {count} samples; signal-in-noise labels were not built ({exc})",
            count,
        )
    scaled = _unit_variance(values)
    if scaled is None:
        return _hold(
            "the closes are not a finite series with variance, so an impulse on a unit-variance series is undefined",
            count,
        )
    unit, mean, scale = scaled
    calibration_shifts, evaluation_shifts = _split(count)
    if not calibration_shifts or not evaluation_shifts:
        return _hold("the alignment split left a side empty, so the held-out rate was not scored", count)
    if set(calibration_shifts) & set(evaluation_shifts):
        return _hold("calibration alignments overlap the held-out alignments", count)

    placements: list[tuple[str, int, int]] = []
    for name, placement_id in _PLACEMENTS:
        sample = sites[name]["sample"]
        placements.append((name, placement_id, int(sample)))

    try:
        calibration_g: list[float] = []
        calibration_l: list[float] = []
        detector = None
        for shift in calibration_shifts:
            reading = _analyze(_rotated(unit, shift))
            if detector is None:
                detector = {
                    "epsilon": reading["epsilon"],
                    "theta": reading["theta"],
                    "alpha": reading["alpha"],
                    "adaptive_threshold": reading["adaptive_threshold"],
                    "lighthouse_threshold_sigma": reading["lighthouse_threshold_sigma"],
                }
            calibration_g.append(float(reading["max_g_eff"]))
            calibration_l.append(float(reading["lighthouse"]))
        ftcp_threshold = upper_threshold(calibration_g, FALSE_ALARM_TAIL)
        lighthouse_threshold = upper_threshold(calibration_l, FALSE_ALARM_TAIL)
        nulls = [_analyze(_rotated(unit, shift)) for shift in evaluation_shifts]
        cells: list[dict[str, Any]] = []
        for placement, _placement_id, inject_index in placements:
            for snr_db in SNR_DB:
                amplitude = _amplitude(int(snr_db))
                labels: list[bool] = []
                g_calls: list[bool] = []
                l_calls: list[bool] = []
                native_g: list[bool] = []
                native_l: list[bool] = []
                for trial, shift in enumerate(evaluation_shifts):
                    window = _rotated(unit, shift)
                    signal = list(window)
                    signal[inject_index] += amplitude
                    signed = _analyze(signal)
                    null = nulls[trial]
                    labels.append(False)
                    g_calls.append(float(null["max_g_eff"]) > ftcp_threshold)
                    l_calls.append(float(null["lighthouse"]) > lighthouse_threshold)
                    native_g.append(int(null["ftcp_count"]) > 0)
                    native_l.append(int(null["lhe_count"]) > 0)
                    labels.append(True)
                    g_calls.append(float(signed["max_g_eff"]) > ftcp_threshold)
                    l_calls.append(float(signed["lighthouse"]) > lighthouse_threshold)
                    native_g.append(int(signed["ftcp_count"]) > 0)
                    native_l.append(int(signed["lhe_count"]) > 0)
                cells.append(
                    {
                        "placement": placement,
                        "snr_db": int(snr_db),
                        "amplitude": amplitude,
                        "inject_index": inject_index,
                        "signal_trials": len(evaluation_shifts),
                        "null_trials": len(evaluation_shifts),
                        "ftcp": _call_rates(labels, g_calls),
                        "lhe": _call_rates(labels, l_calls),
                        "native_ftcp": _call_rates(labels, native_g),
                        "native_lhe": _call_rates(labels, native_l),
                    }
                )
    except (RuntimeError, ValueError) as exc:
        return _hold(f"measurement failed while scoring planted impulses: {exc}", count)

    headline = next(
        (
            cell
            for cell in cells
            if cell["placement"] == HEADLINE_PLACEMENT and cell["snr_db"] == HEADLINE_SNR_DB
        ),
        None,
    )
    if headline is None:
        return _hold("the held-out grid has no tight-lattice cell at 0 dB", count)
    ftcp = headline["ftcp"]
    detection = ftcp["recall"]
    false_alarm = ftcp["false_alarm_rate"]
    if detection is None or false_alarm is None:
        return _hold("the held-out cell did not produce a detection rate and a false-alarm rate", count)
    reason = (
        "The closes were centered and scaled to unit variance. "
        f"random.Random({CALIBRATION_SEED_START}) shuffles the {count} circular shifts and "
        "keeps the first half for calibration; "
        f"random.Random({MASTER_SEED}) shuffles the held-out half. "
        "The two halves are disjoint. A one-sample impulse is added at the evidence lattice index. "
        "The call is max_g_eff above upper_threshold at tail "
        f"{FALSE_ALARM_TAIL}, fit only on the calibration alignments. "
        f"The detection rate is the held-out recall at {HEADLINE_PLACEMENT} and {HEADLINE_SNR_DB} dB. "
        "The false-alarm rate is the held-out false-alarm rate of that same call. "
        "Intervals are Wilson. The impulse is a harness label, not a trade outcome. "
        "This result is tagged synthetic_planted and is not a measured market rate. No order was sent."
    )
    result = {
        "harness_status": "scored",
        "detection_rate": detection,
        "detection_rate_ci95": ftcp["recall_ci95"],
        "false_alarm_rate": false_alarm,
        "false_alarm_ci95": ftcp["false_alarm_ci95"],
        "rates_reason": reason,
        "signal_in_noise": {
            "verdict": "test_only",
            "orders_placed": False,
            "labels": "planted one-sample impulse on a circular shift of the standardized closes",
            "source": "aureon.wisdom.aureon_qgita_framework.QGITAMarketAnalyzer.analyze",
            "detector_defaults": detector,
            "background": {
                "transform": "subtract the mean and divide by the population standard deviation",
                "samples": count,
                "mean": mean,
                "population_std": scale,
                "clock": "sample index, the evidence lattice clock",
            },
            "seeds": {
                "master_seed": MASTER_SEED,
                "calibration_seed_start": CALIBRATION_SEED_START,
                "seeds_disjoint": True,
                "split": (
                    "shuffle alignments with the calibration seed start; "
                    "first half calibrates; the master seed shuffles the held-out half"
                ),
            },
            "calibration_shifts": calibration_shifts,
            "evaluation_shifts": evaluation_shifts,
            "calibration": {
                "trials": len(calibration_shifts),
                "tail": FALSE_ALARM_TAIL,
                "threshold_index": "ceil((1 - tail) * n) - 1 on sorted null scores",
                "ftcp_max_g_eff_threshold": ftcp_threshold,
                "lighthouse_intensity_threshold": lighthouse_threshold,
                "ftcp_calibration_false_alarm_rate": fraction_above(calibration_g, ftcp_threshold),
                "lighthouse_calibration_false_alarm_rate": fraction_above(
                    calibration_l, lighthouse_threshold
                ),
                "note": (
                    "Calibration alignments are not the held-out alignments. "
                    "The reported false-alarm rate is the held-out rate. "
                    "Null scores do not depend on placement or SNR."
                ),
            },
            "headline": {
                "placement": HEADLINE_PLACEMENT,
                "snr_db": HEADLINE_SNR_DB,
                "score": "max_g_eff",
                "amplitude": headline["amplitude"],
                "amplitude_in_price_units": headline["amplitude"] * scale,
                "inject_index": headline["inject_index"],
                "detection_rate": detection,
                "detection_rate_ci95": ftcp["recall_ci95"],
                "false_alarm_rate": false_alarm,
                "false_alarm_ci95": ftcp["false_alarm_ci95"],
                "lighthouse_detection_rate": headline["lhe"]["recall"],
                "lighthouse_detection_rate_ci95": headline["lhe"]["recall_ci95"],
                "lighthouse_false_alarm_rate": headline["lhe"]["false_alarm_rate"],
                "lighthouse_false_alarm_ci95": headline["lhe"]["false_alarm_ci95"],
            },
            "injection": {
                "rule": sites["rule"],
                "epsilon": sites["epsilon"],
                "tight_lattice": sites["tight_lattice"],
                "mid_lattice": sites["mid_lattice"],
                "off_lattice": sites["off_lattice"],
            },
            "snr_grid_db": list(SNR_DB),
            "cells": cells,
        },
    }
    return _envelope(result)


def rate_phrase(block: dict[str, Any]) -> str:
    """Name the harness as ``synthetic_planted``. This sentence is not a market-rate line."""

    if block.get("harness_status") != "scored":
        return f"synthetic_planted harness, not scored. {block.get('rates_reason', '')}".rstrip()
    return (
        "synthetic_planted harness. "
        f"Planted-impulse detection `{block.get('detection_rate')}` "
        f"Wilson `{block.get('detection_rate_ci95')}`. "
        f"Planted-impulse false-alarm `{block.get('false_alarm_rate')}` "
        f"Wilson `{block.get('false_alarm_ci95')}`. "
        "Not a measured market rate."
    )
