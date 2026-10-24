"""Measure the three parts of the internal brain on the code that already exists.

The Harmonic Nexus Core figure is ``HarmonicRealityField.step`` with the
multiverse extension off, which is the master-formula branch in that method.
The class default turns the extension on, and that path draws unseeded noise,
so this run does not publish a number for it.

Auris coherence is ``QueenHiveMind.get_auris_coherence`` with the market
argument omitted, so the method uses its own default. A second set of calls
changes one input at a time between the clamp bounds already in
``read_auris_nodes``. Nodes that do not move are HOLD for a sensing claim.
There is no trade-outcome label.

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

PUBLIC_SERIES = "data/de440_timeseries.csv"
PUBLIC_COLUMN = "Lambda"
_METRIC_WINDOW = 100
_NOTE = (
    "These figures are the HNC master-formula path, Auris coherence, and the QGITA analyzer. "
    "They are not a claim that the system is conscious or alive."
)
_CLAMP = (0.0, 1.0)
_INPUTS = ("volatility", "momentum", "volume", "spread")


def _reader():
    from aureon.utils.aureon_queen_hive_mind import QueenHiveMind

    return QueenHiveMind.__new__(QueenHiveMind)


def _node_values(reading: dict[str, Any]) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {}
    for name, item in reading.items():
        out[str(name)] = {
            "value": float(item["value"]),
            "freq": float(item["freq"]),
            "weight": float(item["weight"]),
            "weighted_value": float(item["weighted_value"]),
        }
    return out


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
            "The class default enables the multiverse extension. "
            "That path applies TranslationMap noise that is not seeded, so this run does not publish a number for it. "
            "enable_multiverse=False is the master-formula branch already in step()."
        ),
        "multiverse_extension": {
            "verdict": "HOLD",
            "reason": "the default extension draws unseeded noise, so it has no committed number",
        },
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
    reading = _node_values(queen.read_auris_nodes(None))
    coherence, status = queen.get_auris_coherence(None)
    weights = sum(item["weight"] for item in reading.values())
    weighted = sum(item["weighted_value"] for item in reading.values())
    changed: dict[str, list[str]] = {name: [] for name in reading}
    probes: dict[str, dict[str, dict[str, float]]] = {}
    for key in _INPUTS:
        probes[key] = {}
        for bound in _CLAMP:
            probed = _node_values(queen.read_auris_nodes({key: bound}))
            probes[key][str(bound)] = {name: item["value"] for name, item in probed.items()}
            for name, item in probed.items():
                if item["value"] != reading[name]["value"] and key not in changed[name]:
                    changed[name].append(key)
    hold = sorted(name for name, keys in changed.items() if not keys)
    return {
        "source": "aureon.utils.aureon_queen_hive_mind.QueenHiveMind.get_auris_coherence",
        "market_data": None,
        "market_data_note": "the argument was omitted, so the method used its own default",
        "nodes": reading,
        "coherence": float(coherence),
        "coherence_status": status,
        "weighted_mean_of_returned_nodes": (weighted / weights) if weights else None,
        "sensitivity": {
            "clamp_bounds": list(_CLAMP),
            "clamp_source": "read_auris_nodes clamps each node value to the unit interval",
            "inputs": list(_INPUTS),
            "probes": probes,
            "inputs_that_move_each_node": changed,
        },
        "hold_nodes": hold,
        "hold_reason": "these nodes do not change when one documented input moves between the clamp bounds",
        "trade_readiness": {
            "verdict": "HOLD",
            "reason": "no trade-outcome labels; the status string is the method's own words, not a fill",
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
    stage1 = raw.get("stage1") or {}
    stage2 = raw.get("stage2") or {}
    valid = list(stage1.get("valid_ftcps") or [])
    events = list(stage2.get("lighthouse_events") or [])
    coherence = _plain(raw.get("coherence") or {})
    statistics = _plain(raw.get("statistics") or {})
    plain_signals = _plain(raw.get("signals") or {})
    regime = _plain(raw.get("regime") or {})
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
        "samples_analyzed": statistics.get("total_samples"),
        "signal_note": "the direction is the analyzer's return. It is not an order and it has no outcome label",
        "buffer_note": "QGITAMarketAnalyzer keeps a 1000-sample buffer; analyze sees that tail",
        "status": raw.get("status"),
        "ftcp_count": int(stage1.get("ftcp_count") or 0),
        "valid_ftcps": [_ftcp_record(item) for item in valid],
        "max_g_eff": float(stage1.get("max_g_eff") or 0.0),
        "lhe_count": int(stage2.get("lhe_count") or 0),
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
    path = root / PUBLIC_SERIES
    if not path.is_file():
        return {
            "verdict": "HOLD",
            "path": PUBLIC_SERIES,
            "reason": "the ephemeris series is not in this checkout",
            "values": [],
        }
    values: list[float] = []
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or PUBLIC_COLUMN not in reader.fieldnames:
            return {
                "verdict": "HOLD",
                "path": PUBLIC_SERIES,
                "reason": f"column {PUBLIC_COLUMN} is missing",
                "values": [],
            }
        for row in reader:
            try:
                values.append(float(row[PUBLIC_COLUMN]))
            except (TypeError, ValueError):
                continue
    if len(values) < 3:
        return {
            "verdict": "HOLD",
            "path": PUBLIC_SERIES,
            "reason": "the column has fewer than three numeric samples",
            "values": values,
        }
    return {"verdict": "loaded", "path": PUBLIC_SERIES, "column": PUBLIC_COLUMN, "values": values}


def evaluate_brain(root: Path | None = None) -> dict[str, Any]:
    """Run the HNC formula, Auris coherence, and the QGITA analyzer."""

    root = Path(root or Path.cwd())
    hnc = _run_hnc()
    auris = _run_auris()
    loaded = _load_lambda(root)
    if loaded["verdict"] != "loaded":
        public = {
            "source": "aureon.wisdom.aureon_qgita_framework.QGITAMarketAnalyzer.analyze",
            "series": PUBLIC_SERIES,
            "verdict": "HOLD",
            "reason": loaded["reason"],
            "detection_rate": None,
            "false_alarm_rate": None,
            "rates_verdict": "HOLD",
        }
    else:
        values = loaded["values"]
        public = _run_qgita(values, [float(index) for index in range(len(values))], PUBLIC_SERIES)
        public["column"] = PUBLIC_COLUMN
        public["timestamps"] = (
            "sample index. analyze_price_stream uses range(len(prices)) when no timestamps are passed"
        )
        public["verdict"] = "measured_counts_rates_hold"
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
            "public_series": public,
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
    public = report["qgita"]["public_series"]
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
            f"Nodes that did not move: {', '.join(auris['hold_nodes']) or 'none'}."
        ),
        f"Trade readiness: **{auris['trade_readiness']['verdict']}**. {auris['trade_readiness']['reason']}",
        (
            f"QGITA on `{public.get('series')}`: status `{public.get('status', public.get('verdict'))}`, "
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
