"""Grounded HNC, Auris, and QGITA receipts for one Aureon reply.

None of these gears calls another model. A gear is engaged only when it has
real input evidence; completing a vote or returning nine nodes is not enough.
"""

from __future__ import annotations

import json
import math
from typing import Any


def parse_hnc_object(text: str) -> dict[str, Any] | None:
    """Pull one JSON object out of a reply, matching the HNC-5000 worker."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.startswith("json"):
            cleaned = cleaned[4:].lstrip()
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        value = json.loads(cleaned[start : end + 1])
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def _load_hnc_history() -> dict[str, Any] | None:
    from aureon.core.aureon_lambda_engine import LambdaEngine

    return LambdaEngine().last_history_receipt


def _qgita_gear(field: Any) -> dict[str, Any]:
    gear: dict[str, Any] = {"name": "qgita", "turned": True, "engaged": False}
    if field is None or not bool(getattr(field, "available", False)):
        gear["blocker"] = "fresh_canonical_field_unavailable"
        return gear

    try:
        from aureon.core.aureon_lambda_engine import validate_history_receipt

        raw_history = _load_hnc_history()
        if raw_history is None:
            gear["blocker"] = "canonical_hnc_history_unavailable"
            return gear
        history = validate_history_receipt(raw_history)
    except Exception as exc:  # noqa: BLE001
        gear["turned"] = False
        gear["error"] = f"{type(exc).__name__}: {exc}"
        return gear

    if history is None:
        gear["blocker"] = "invalid_hnc_history_receipt"
        return gear
    if (
        history["receipt_id"] != getattr(field, "memory_receipt_id", None)
        or history["canonical_hash"] != getattr(field, "memory_canonical_hash", None)
    ):
        gear["blocker"] = "hnc_history_receipt_mismatch"
        return gear

    values = history["history"]
    gear.update({
        "source": "hnc_lambda_history",
        "receipt_id": history["receipt_id"],
        "canonical_hash": history["canonical_hash"],
        "field_receipt_id": getattr(field, "receipt_id", None),
        "step_count": history["step_count"],
        "samples": len(values),
        "time_basis": "hnc_step_index",
    })
    if len(values) < 10:
        gear["blocker"] = "insufficient_hnc_history"
        return gear

    try:
        from aureon.wisdom.aureon_qgita_framework import QGITAMarketAnalyzer

        analyzer = QGITAMarketAnalyzer()
        for index, value in enumerate(values):
            analyzer.feed_price(value, timestamp=float(index))
        analysis = analyzer.analyze()
        if analysis.get("status") != "complete":
            gear["blocker"] = "qgita_analysis_incomplete"
            return gear

        stage1 = analysis["stage1"]
        stage2 = analysis["stage2"]
        coherence = analysis["coherence"]
        metrics = {
            "max_g_eff": stage1["max_g_eff"],
            "current_lighthouse_intensity": stage2["current_lighthouse_intensity"],
            "global_R": coherence["global_R"],
            "c_linear": coherence["c_linear"],
            "c_nonlinear": coherence["c_nonlinear"],
            "c_phi": coherence["c_phi"],
            "q_anomaly": coherence["q_anomaly"],
        }
        for name, value in metrics.items():
            number = float(value)
            if not math.isfinite(number):
                raise ValueError(f"nonfinite_qgita_metric:{name}")
            gear[name] = number
        gear["ftcp_count"] = int(stage1["ftcp_count"])
        gear["lhe_count"] = int(stage2["lhe_count"])
        gear["structural_event"] = gear["lhe_count"] > 0
        gear["engaged"] = True
    except Exception as exc:  # noqa: BLE001
        gear["turned"] = False
        gear["engaged"] = False
        gear["error"] = f"{type(exc).__name__}: {exc}"
    return gear


def capture_organism(bus: Any = None) -> dict[str, Any]:
    """Capture the field, grounded Auris panel, and QGITA before inference."""
    gears: list[dict[str, Any]] = []
    field = None
    field_gear: dict[str, Any] = {"name": "field", "turned": False, "engaged": False}
    try:
        from aureon.core.hnc_field import read_canonical_field

        field = read_canonical_field(bus)
        field_available = bool(field.available)
        field_gear.update({
            "turned": True,
            "engaged": field_available,
            "available": field_available,
            "receipt_id": getattr(field, "receipt_id", None),
            "memory_receipt_id": getattr(field, "memory_receipt_id", None),
            "freshness_status": getattr(field, "freshness_status", None),
            "lambda_t": getattr(field, "lambda_t", None) if field_available else None,
            "coherence_gamma": getattr(field, "coherence_gamma", None) if field_available else None,
            "symbolic_life_score": getattr(field, "symbolic_life_score", None) if field_available else None,
            "consciousness_psi": getattr(field, "consciousness_psi", None) if field_available else None,
            "step": getattr(field, "step", None) if field_available else None,
            "source_timestamp": getattr(field, "source_timestamp", None) if field_available else None,
        })
        if not field_available:
            field_gear["blocker"] = "fresh_canonical_field_unavailable"
    except Exception as exc:  # noqa: BLE001
        field_gear["error"] = f"{type(exc).__name__}: {exc}"
    gears.append(field_gear)

    auris_gear: dict[str, Any] = {"name": "auris", "turned": False, "engaged": False}
    try:
        from aureon.gates.panel import auris_panel

        if field is None:
            raise RuntimeError("canonical_field_read_failed")
        reading = auris_panel(bus, canonical=field)
        auris_gear.update(reading.to_dict())
        auris_gear["turned"] = reading.available
        auris_gear["engaged"] = reading.available and reading.grounded_inputs > 0
        if not auris_gear["engaged"] and not auris_gear.get("blocker"):
            auris_gear["blocker"] = "no_grounded_auris_inputs"
    except Exception as exc:  # noqa: BLE001
        auris_gear["error"] = f"{type(exc).__name__}: {exc}"
    gears.append(auris_gear)
    gears.append(_qgita_gear(field))
    return {
        "gears": gears,
        "all_turned": all(gear["turned"] for gear in gears),
    }


def turn_gears(
    text: str,
    bus: Any = None,
    *,
    organism: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Parse one reply against the same organism snapshot used for its prompt."""
    parsed = parse_hnc_object(text)
    snapshot = capture_organism(bus) if organism is None else organism
    gears: list[dict[str, Any]] = [{
        "name": "parse",
        "turned": True,
        "engaged": parsed is not None,
    }, *snapshot["gears"]]
    return {
        "gears": gears,
        "all_turned": all(gear["turned"] for gear in gears),
        "parsed": parsed is not None,
    }


def attach_gears(
    body: dict[str, Any],
    text: str,
    bus: Any = None,
    *,
    organism: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Add the gear receipt beside the reply. The reply text stays unchanged."""
    out = dict(body)
    out["hnc_gears"] = turn_gears(text, bus=bus, organism=organism)
    return out
