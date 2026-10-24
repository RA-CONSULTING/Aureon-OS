"""Measure the three parts of the internal brain on the code that already exists.

The Harmonic Nexus Core figure is ``HarmonicRealityField.step`` with the
multiverse extension off, which is the master-formula branch in that method.
The class default turns the extension on. ``project_to_3d`` uses 0 when no
residual is supplied, and three constructions of that default match, so the
extension is measured beside the formula branch.

Auris coherence is ``QueenHiveMind.get_auris_coherence``. This harness has
no market series, so it does not supply a stand-in texture. The coherence
figure is no_data. A zero-input probe names the nodes that stay without a
value when the four market fields are present. There is no trade-outcome
label.

QGITA is ``QGITAMarketAnalyzer`` constructed with its own defaults, then
``analyze``. Detection rate and false-alarm rate stay HOLD: neither the
ephemeris column nor the formula series carries signal-in-noise labels.

No formula, threshold, or result is introduced here. Live trading stays off.
These figures are not a claim that the system is conscious or alive.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

DERIVED_SERIES = "data/de440_timeseries.csv"
DERIVED_COLUMN = "Lambda"
DERIVED_COMMIT = "6fd1d9d8"
_METRIC_WINDOW = 100
_NOTE = (
    "These figures are the HNC master-formula path, Auris coherence, and the QGITA analyzer. "
    "They are not a claim that the system is conscious or alive."
)
_INPUTS = ("volatility", "momentum", "volume", "spread")


def _optional_count(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _optional_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number or number in (float("inf"), float("-inf")):
        return None
    return number


def _one_default_field() -> dict[str, Any]:
    from aureon.harmonic.aureon_harmonic_reality import HarmonicRealityField

    field = HarmonicRealityField()
    series: list[float] = []
    while len(series) < _METRIC_WINDOW:
        series.append(float(field.step()))
    history = list(field.translation_map.projection_history) if field.translation_map is not None else []
    noises = [float(row["noise"]) for row in history]
    return {
        "series": series,
        "coherence": float(field.coherence),
        "state": str(field.state.value),
        "lambda_last": series[-1],
        "boundedness": float(field.boundedness),
        "echo_strength": float(field.echo_strength),
        "noises_all_zero": bool(noises) and all(item == 0.0 for item in noises),
        "noise_samples": len(noises),
        "noise_level_attribute": None if field.translation_map is None else float(field.translation_map.noise_level),
    }


def _default_extension() -> dict[str, Any]:
    """Measure the class-default extension. The noise claim is checked here."""

    runs = [_one_default_field() for _ in range(3)]
    identical = all(item["series"] == runs[0]["series"] for item in runs)
    noises_zero = all(item["noises_all_zero"] for item in runs)
    first = runs[0]
    if identical and noises_zero:
        verdict = "measured"
        reason = (
            "project_to_3d sets noise to 0 when no observed residual is supplied. "
            "TranslationMap.noise_level is stored and is not read by that method. "
            "Three constructions of the default HarmonicRealityField returned the same series."
        )
    elif not identical:
        verdict = "HOLD"
        reason = "three constructions of the default HarmonicRealityField did not return the same series"
    else:
        verdict = "HOLD"
        reason = "project_to_3d recorded a non-zero noise on the default path"
    return {
        "verdict": verdict,
        "reason": reason,
        "enable_multiverse": True,
        "constructions": len(runs),
        "series_identical": identical,
        "recorded_noise_all_zero": noises_zero,
        "noise_level_attribute_unread": first["noise_level_attribute"],
        "steps": len(first["series"]),
        "state": first["state"] if identical else None,
        "coherence": first["coherence"] if identical else None,
        "lambda_last": first["lambda_last"] if identical else None,
        "boundedness": first["boundedness"] if identical else None,
        "echo_strength": first["echo_strength"] if identical else None,
        "series": first["series"] if identical else None,
    }


def _reader():
    from aureon.utils.aureon_queen_hive_mind import QueenHiveMind

    return QueenHiveMind.__new__(QueenHiveMind)


def _run_hnc() -> dict[str, Any]:
    from aureon.harmonic.aureon_harmonic_reality import HarmonicRealityField

    field = HarmonicRealityField(enable_multiverse=False)
    series: list[float] = []
    while len(series) < _METRIC_WINDOW:
        series.append(float(field.step()))
    return {
        "source": "aureon.harmonic.aureon_harmonic_reality.HarmonicRealityField.step",
        "formula": "F_sub(t) + F_observer(t) + F_feedback(t)",
        "enable_multiverse": False,
        "why_multiverse_is_off": (
            "enable_multiverse=False is the master-formula branch already in step(). "
            "The class default turns the extension on. That extension is measured separately."
        ),
        "multiverse_extension": _default_extension(),
        "steps": len(series),
        "steps_are": "the history length HarmonicRealityField._update_metrics requires before it computes coherence",
        "parameters": {
            "alpha": float(field.observer.alpha),
            "beta": float(field.echo.beta),
            "tau": float(field.echo.tau),
            "g": float(field.observer.g),
            "delta_t": float(field.observer.delta_t),
            "sample_rate": float(field.sample_rate),
            "substrate_frequencies": [float(mode.frequency) for mode in field.substrate.modes],
        },
        "lambda_min": min(series),
        "lambda_max": max(series),
        "lambda_mean": sum(series) / len(series),
        "lambda_last": series[-1],
        "coherence": float(field.coherence),
        "boundedness": float(field.boundedness),
        "echo_strength": float(field.echo_strength),
        "state": str(field.state.value),
        "series": series,
        "dt": float(field.dt),
    }


def _run_auris() -> dict[str, Any]:
    queen = _reader()
    coherence, status = queen.get_auris_coherence(None)
    zeros = {key: 0.0 for key in _INPUTS}
    probed = queen.read_auris_nodes(zeros)
    hold = sorted(name for name, item in probed.items() if item.get("value") is None)
    return {
        "source": "aureon.utils.aureon_queen_hive_mind.QueenHiveMind.get_auris_coherence",
        "market_data": None,
        "market_data_note": "no market series was supplied, so the omitted call is no_data",
        "status": status,
        "nodes": None,
        "coherence": None if coherence is None else float(coherence),
        "coherence_status": status,
        "zero_input_probe": {
            "inputs": zeros,
            "note": "clamp-bound probe of the existing formulas, not a market reading; node values are not published",
            "nodes_without_reading": hold,
        },
        "hold_nodes": hold,
        "hold_reason": (
            "these nodes have no value when volatility, momentum, volume, and spread are all present as 0; "
            "memory and symbiosis have no market input in read_auris_nodes"
        ),
        "trade_readiness": {
            "verdict": "HOLD",
            "reason": "no market series and no trade-outcome labels",
        },
    }


def _ftcp_record(item: Any) -> dict[str, Any]:
    return {
        "timestamp": float(item.timestamp),
        "knot_index": int(item.knot_index),
        "curvature": float(item.curvature),
        "interval_ratio": float(item.interval_ratio),
        "phi_match": float(item.phi_match),
        "g_eff": float(item.g_eff),
        "local_contrast": float(item.local_contrast),
        "is_valid": bool(item.is_valid),
    }


def _lhe_record(item: Any) -> dict[str, Any]:
    return {
        "timestamp": float(item.timestamp),
        "lighthouse_intensity": float(item.lighthouse_intensity),
        "c_linear": float(item.c_linear),
        "c_nonlinear": float(item.c_nonlinear),
        "c_phi": float(item.c_phi),
        "g_eff": float(item.g_eff),
        "q_anomaly": float(item.q_anomaly),
        "confidence": float(item.confidence),
        "event_type": str(item.event_type.value),
    }


def _plain(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return int(value)
    if isinstance(value, float):
        return float(value)
    item = getattr(value, "item", None)
    if callable(item):
        return _plain(item())
    return str(value)


def _run_qgita(values: list[float], times: list[float], series_name: str) -> dict[str, Any]:
    from aureon.wisdom.aureon_qgita_framework import QGITAMarketAnalyzer

    analyzer = QGITAMarketAnalyzer()
    for stamp, value in zip(times, values):
        analyzer.feed_price(float(value), timestamp=float(stamp))
    raw = analyzer.analyze()
    stage1 = raw.get("stage1") if isinstance(raw.get("stage1"), dict) else {}
    stage2 = raw.get("stage2") if isinstance(raw.get("stage2"), dict) else {}
    valid = list(stage1.get("valid_ftcps") or [])
    events = list(stage2.get("lighthouse_events") or [])
    coherence = None if raw.get("coherence") is None else _plain(raw.get("coherence"))
    statistics = None if raw.get("statistics") is None else _plain(raw.get("statistics"))
    plain_signals = None if raw.get("signals") is None else _plain(raw.get("signals"))
    regime = None if raw.get("regime") is None else _plain(raw.get("regime"))
    return {
        "source": "aureon.wisdom.aureon_qgita_framework.QGITAMarketAnalyzer.analyze",
        "series": series_name,
        "detector": {
            "epsilon": float(analyzer.ftcp_detector.epsilon),
            "theta": float(analyzer.ftcp_detector.theta),
            "alpha": float(analyzer.ftcp_detector.alpha),
            "adaptive_threshold": bool(analyzer.ftcp_detector.adaptive_threshold),
        },
        "lighthouse_threshold_sigma": float(analyzer.lighthouse.threshold_sigma),
        "samples_fed": len(values),
        "samples_analyzed": None if not isinstance(statistics, dict) else statistics.get("total_samples"),
        "signal_note": "the direction is the analyzer's return. It is not an order and it has no outcome label",
        "buffer_note": "QGITAMarketAnalyzer keeps a 1000-sample buffer; analyze sees that tail",
        "status": raw.get("status"),
        "ftcp_count": _optional_count(stage1.get("ftcp_count")),
        "valid_ftcps": [_ftcp_record(item) for item in valid],
        "max_g_eff": _optional_float(stage1.get("max_g_eff")),
        "lhe_count": _optional_count(stage2.get("lhe_count")),
        "lighthouse_events": [_lhe_record(item) for item in events],
        "lighthouse_intensity": _plain(stage2.get("current_lighthouse_intensity")),
        "detection_threshold": _plain(stage2.get("detection_threshold")),
        "coherence": coherence,
        "regime": regime,
        "signals": plain_signals,
        "statistics": statistics,
        "detection_rate": None,
        "false_alarm_rate": None,
        "rates_verdict": "HOLD",
        "rates_reason": (
            "this series has no signal-in-noise labels in the repo, "
            "so the analyzer counts are not a detection rate or a false-alarm rate"
        ),
        "orders_placed": False,
    }


def _load_lambda(root: Path) -> dict[str, Any]:
    path = root / DERIVED_SERIES
    if not path.is_file():
        return {
            "verdict": "HOLD",
            "path": DERIVED_SERIES,
            "reason": "the derived series is not in this checkout",
            "values": [],
        }
    values: list[float] = []
    first_dt = ""
    last_dt = ""
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or DERIVED_COLUMN not in reader.fieldnames:
            return {
                "verdict": "HOLD",
                "path": DERIVED_SERIES,
                "reason": f"column {DERIVED_COLUMN} is missing",
                "values": [],
            }
        for row in reader:
            stamp = str(row.get("datetime") or "")
            try:
                values.append(float(row[DERIVED_COLUMN]))
            except (TypeError, ValueError):
                continue
            if stamp and not first_dt:
                first_dt = stamp
            if stamp:
                last_dt = stamp
    if len(values) < 3:
        return {
            "verdict": "HOLD",
            "path": DERIVED_SERIES,
            "reason": "the column has fewer than three numeric samples",
            "values": values,
        }
    return {
        "verdict": "loaded",
        "path": DERIVED_SERIES,
        "column": DERIVED_COLUMN,
        "values": values,
        "rows": len(values),
        "datetime_first": first_dt,
        "datetime_last": last_dt,
    }


def evaluate_brain(root: Path | None = None) -> dict[str, Any]:
    """Run the HNC formula, Auris coherence, and the QGITA analyzer."""

    root = Path(root or Path.cwd())
    hnc = _run_hnc()
    auris = _run_auris()
    loaded = _load_lambda(root)
    provenance = (
        f"{DERIVED_SERIES} column {DERIVED_COLUMN} is a precomputed derived series. "
        "This checkout has no generator for the column. It is not public market data."
    )
    if loaded["verdict"] != "loaded":
        derived = {
            "source": "aureon.wisdom.aureon_qgita_framework.QGITAMarketAnalyzer.analyze",
            "series": DERIVED_SERIES,
            "series_class": "derived",
            "evidence_tag": "cited-unverified",
            "provenance": provenance,
            "committed_in": DERIVED_COMMIT,
            "verdict": "HOLD",
            "reason": loaded["reason"],
            "detection_rate": None,
            "false_alarm_rate": None,
            "rates_verdict": "HOLD",
        }
    else:
        values = loaded["values"]
        derived = _run_qgita(values, [float(index) for index in range(len(values))], DERIVED_SERIES)
        derived["column"] = DERIVED_COLUMN
        derived["series_class"] = "derived"
        derived["evidence_tag"] = "cited-unverified"
        derived["provenance"] = (
            f"{provenance} {loaded['rows']} numeric rows, "
            f"{loaded['datetime_first']} to {loaded['datetime_last']}, committed in {DERIVED_COMMIT}."
        )
        derived["committed_in"] = DERIVED_COMMIT
        derived["datetime_first"] = loaded["datetime_first"]
        derived["datetime_last"] = loaded["datetime_last"]
        derived["timestamps"] = (
            "sample index. analyze_price_stream uses range(len(prices)) when no timestamps are passed"
        )
        derived["verdict"] = "measured_counts_rates_hold"
    hnc_values = list(hnc["series"])
    on_lambda = _run_qgita(
        hnc_values,
        [index * float(hnc["dt"]) for index in range(len(hnc_values))],
        "hnc_lambda_series",
    )
    on_lambda["timestamps"] = "step index times HarmonicRealityField.dt"
    on_lambda["verdict"] = "measured_counts_rates_hold"
    return {
        "schema": "aureon.brain-proof.v1",
        "live_trading": False,
        "orders_placed": False,
        "external_llm": False,
        "cognition": "internal",
        "note": _NOTE,
        "hnc": hnc,
        "auris": auris,
        "qgita": {
            "derived_series": derived,
            "on_hnc_series": on_lambda,
        },
        "together": {
            "qgita_on_the_formula_series": "measured_counts_rates_hold",
            "auris_joined_to_lambda": {
                "verdict": "HOLD",
                "reason": "no function in the repo passes Λ(t) into get_auris_coherence",
            },
        },
    }


def render_brain_markdown(report: dict[str, Any]) -> str:
    hnc = report["hnc"]
    auris = report["auris"]
    public = report["qgita"]["derived_series"]
    on_lambda = report["qgita"]["on_hnc_series"]
    lines = [
        "# HNC, Auris coherence, and QGITA",
        "",
        report["note"],
        "",
        "No outside model was called. Live trading stayed off. No order was placed.",
        (
            f"HNC formula path, multiverse off: state `{hnc['state']}`, "
            f"coherence `{hnc['coherence']}`, last Λ(t) `{hnc['lambda_last']}`, "
            f"steps `{hnc['steps']}`."
        ),
        f"Multiverse extension: **{hnc['multiverse_extension']['verdict']}**. {hnc['multiverse_extension']['reason']}",
        (
            f"Auris coherence `{auris['coherence']}` with status `{auris['coherence_status']}`. "
            f"Nodes without a reading: {', '.join(auris['hold_nodes']) or 'none'}."
        ),
        f"Trade readiness: **{auris['trade_readiness']['verdict']}**. {auris['trade_readiness']['reason']}",
        (
            f"QGITA on the derived series `{public.get('series')}` ({public.get('evidence_tag')}): "
            f"status `{public.get('status', public.get('verdict'))}`, "
            f"FTCP count `{public.get('ftcp_count')}`, lighthouse events `{public.get('lhe_count')}`. "
            f"Detection rate **{public.get('rates_verdict')}**. "
            f"Clock: {public.get('timestamps', '')}"
        ),
        (
            f"QGITA on the formula series: FTCP count `{on_lambda.get('ftcp_count')}`, "
            f"lighthouse events `{on_lambda.get('lhe_count')}`. "
            f"Detection rate **{on_lambda.get('rates_verdict')}**. "
            f"Clock: {on_lambda.get('timestamps', '')}"
        ),
        (
            "Auris is not joined to Λ(t): **"
            f"{report['together']['auris_joined_to_lambda']['verdict']}**. "
            f"{report['together']['auris_joined_to_lambda']['reason']}"
        ),
        "",
    ]
    return "\n".join(lines)
