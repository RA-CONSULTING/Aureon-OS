"""The nine public tools. Each returns JSON text. No orders and no state/ writes."""

from __future__ import annotations

import csv
import json
import math
import os
import tempfile
from pathlib import Path
from typing import Any

from aureon_public.guard_loader import apply_space_guard
from aureon_public import paths
from aureon_public.quiet import quiet
from aureon_public.text import AURIS_FOUR, HOLD_LINE

apply_space_guard()

_AURIS_FIELDS = ("volatility", "momentum", "volume", "spread")


def _plain(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return value
    if isinstance(value, int):
        return int(value)
    if isinstance(value, float):
        return float(value)
    item = getattr(value, "item", None)
    if callable(item):
        try:
            return _plain(item())
        except Exception:
            pass
    return str(value)


def _dumps(payload: dict[str, Any]) -> str:
    return json.dumps(_plain(payload), ensure_ascii=False, allow_nan=False, sort_keys=True)


def _load(path: Path) -> dict[str, Any]:
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise TypeError(path.name)
    return loaded


def _finite(value: object) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if not isinstance(value, (int, float)):
        return None
    number = float(value)
    if not math.isfinite(number):
        return None
    return number


def _brain() -> dict[str, Any]:
    return _load(paths.brain_json())


def _path_block(brain: dict[str, Any], enable_multiverse: bool) -> dict[str, Any]:
    hnc = brain.get("hnc")
    if not isinstance(hnc, dict):
        raise KeyError("hnc")
    if enable_multiverse:
        block = hnc.get("multiverse_extension")
    else:
        block = hnc
    if not isinstance(block, dict):
        raise KeyError("brain path")
    return block


def _cap(enable_multiverse: bool) -> int:
    steps = _path_block(_brain(), enable_multiverse).get("steps")
    if isinstance(steps, bool) or not isinstance(steps, int) or steps < 1:
        raise ValueError("committed step count is missing")
    return steps


def _hnc_doc() -> str:
    brain = _brain()
    on = json.dumps(_path_block(brain, True)["coherence"])
    off = json.dumps(_path_block(brain, False)["coherence"])
    return f"""Call HarmonicRealityField.step. Label: inferred. This is a rerun in this process.

The class default HarmonicRealityField() sets enable_multiverse=True (multiverse on). This tool's default is that class default. The output field enable_multiverse is the value used for this call.

Do not mix the two committed brain paths. Cited, huggingface/hnc-field/replay/brain.json: multiverse on coherence is {on}; multiverse off coherence is {off}.

steps is capped at the committed steps field for the selected path. There is no frequencies argument. Trade readiness: HOLD. {HOLD_LINE}

Args:
    alpha: Observer gain passed to HarmonicRealityField. Label: cited, DEFAULT_ALPHA in aureon/harmonic/aureon_harmonic_reality.py.
    beta: Echo gain passed to HarmonicRealityField. Label: cited, DEFAULT_BETA.
    tau: Echo delay passed to HarmonicRealityField. Label: cited, DEFAULT_TAU.
    g: Observer nonlinearity passed to HarmonicRealityField. Label: cited, DEFAULT_G.
    delta_t: Observer window passed to HarmonicRealityField. Label: cited, DEFAULT_DELTA_T.
    sample_rate: Samples per second. Signature default 1000.0. Label: cited, HarmonicRealityField.__init__.
    enable_multiverse: Class default is True (multiverse on). False selects the other committed brain path. Reported in the output. Label: cited.
    steps: Step count. Omitted uses the committed steps for the selected path. Values above that cap are unavailable. Label: cited, vendored brain.json steps.
"""


@quiet
def hnc_reality_step(
    alpha: float = 0.85,
    beta: float = 0.9,
    tau: float = 0.05,
    g: float = 1.5,
    delta_t: float = 0.01,
    sample_rate: float = 1000.0,
    enable_multiverse: bool = True,
    steps: int | None = None,
) -> str:
    turned_on = enable_multiverse is True
    if not isinstance(enable_multiverse, bool):
        return _dumps(
            {
                "class_default_enable_multiverse": True,
                "enable_multiverse": None,
                "label": "cited",
                "reason": "enable_multiverse is missing",
                "status": "unavailable",
            }
        )
    try:
        cap = _cap(turned_on)
    except (OSError, ValueError, KeyError, TypeError):
        return _dumps(
            {
                "class_default_enable_multiverse": True,
                "enable_multiverse": turned_on,
                "label": "cited",
                "reason": "The committed step count is missing.",
                "status": "unavailable",
            }
        )
    chosen: int | None
    if steps is None:
        chosen = cap
    elif isinstance(steps, bool) or not isinstance(steps, int) or steps < 1:
        chosen = None
    elif steps > cap:
        return _dumps(
            {
                "class_default_enable_multiverse": True,
                "enable_multiverse": turned_on,
                "label": "cited. The cap is the steps field on the selected brain path.",
                "reason": "steps is above the committed replay length for this path",
                "status": "unavailable",
                "steps_cap": cap,
            }
        )
    else:
        chosen = steps
    numbers = {
        "alpha": _finite(alpha),
        "beta": _finite(beta),
        "tau": _finite(tau),
        "g": _finite(g),
        "delta_t": _finite(delta_t),
        "sample_rate": _finite(sample_rate),
    }
    if (
        chosen is None
        or any(value is None for value in numbers.values())
        or numbers["sample_rate"] is None
        or numbers["sample_rate"] <= 0
    ):
        return _dumps(
            {
                "class_default_enable_multiverse": True,
                "enable_multiverse": turned_on,
                "label": "cited",
                "reason": "A parameter is missing.",
                "status": "unavailable",
                "steps_cap": cap,
            }
        )
    from aureon.harmonic.aureon_harmonic_reality import HarmonicRealityField

    field = HarmonicRealityField(
        alpha=float(numbers["alpha"]),
        beta=float(numbers["beta"]),
        tau=float(numbers["tau"]),
        g=float(numbers["g"]),
        delta_t=float(numbers["delta_t"]),
        sample_rate=float(numbers["sample_rate"]),
        enable_multiverse=turned_on,
    )
    series = [float(field.step()) for _ in range(chosen)]
    payload: dict[str, Any] = {
        "class_default_enable_multiverse": True,
        "coherence": float(field.coherence),
        "committed_replay_match": None,
        "committed_replay_path": "multiverse_extension" if turned_on else "hnc",
        "enable_multiverse": bool(field.enable_multiverse),
        "get_state": field.get_state(),
        "label": "inferred. Rerun of HarmonicRealityField.step in this process.",
        "lambda_last": series[-1],
        "series": series,
        "state_name": field.state.name,
        "state_value": field.state.value,
        "status": "inferred",
        "steps": chosen,
        "steps_cap": cap,
    }
    payload["committed_replay_match"] = _committed_match(
        payload,
        {key: float(value) for key, value in numbers.items()},
        turned_on,
    )
    return _dumps(payload)


def _committed_match(payload: dict[str, Any], numbers: dict[str, float], enable_multiverse: bool) -> bool | None:
    brain = _brain()
    parameters = brain.get("hnc", {}).get("parameters")
    if not isinstance(parameters, dict):
        return None
    expected = {
        "alpha": parameters.get("alpha"),
        "beta": parameters.get("beta"),
        "delta_t": parameters.get("delta_t"),
        "g": parameters.get("g"),
        "sample_rate": parameters.get("sample_rate"),
        "tau": parameters.get("tau"),
    }
    if any(numbers[key] != expected[key] for key in expected):
        return None
    block = _path_block(brain, enable_multiverse)
    if payload["steps"] != block.get("steps"):
        return None
    fresh = {
        "coherence": payload["coherence"],
        "lambda_last": payload["lambda_last"],
        "series": payload["series"],
    }
    rounded = json.loads(json.dumps(fresh))
    return (
        rounded["coherence"] == block.get("coherence")
        and rounded["lambda_last"] == block.get("lambda_last")
        and rounded["series"] == block.get("series")
        and payload["state_value"] == block.get("state")
    )


hnc_reality_step.__doc__ = _hnc_doc()


@quiet
def hnc_canonical_read(envelope_jsonl: str | None = None) -> str:
    """Read CanonicalField. An empty envelope does not touch state/.

    Label: inferred when an envelope was supplied and available is true. Otherwise the field is unavailable. Cited: read_canonical_field does not run unless a temp trace was set. The bundled brain replay is a formula record, not a canonical envelope.

    Args:
        envelope_jsonl: Optional JSONL text for one canonical envelope. Empty or omitted returns the unavailable field and does not read state/. Label: cited, aureon/core/hnc_field.py read_canonical_field.
    """

    if envelope_jsonl is None or not str(envelope_jsonl).strip():
        from aureon.core.hnc_field import CanonicalField

        body = CanonicalField().to_dict()
        body["label"] = (
            "cited. No envelope was supplied, so state/ was not read. "
            "The bundled brain replay is a formula record, not a canonical envelope."
        )
        body["status"] = "unavailable"
        return _dumps(body)
    return _dumps(_with_envelope(str(envelope_jsonl), blend=False))


@quiet
def hnc_blend_read(envelope_jsonl: str | None = None) -> str:
    """Read BlendedField. Does not call publish_subfield. An empty envelope does not touch state/.

    Label: inferred when an envelope was supplied and available is true. Otherwise unavailable.

    Args:
        envelope_jsonl: Optional JSONL text. Empty or omitted returns the unavailable blend and does not read state/. Label: cited, aureon/core/hnc_field.py blend_field.
    """

    if envelope_jsonl is None or not str(envelope_jsonl).strip():
        from aureon.core.hnc_field import BlendedField

        body = BlendedField().to_dict()
        body["label"] = "cited. No envelope was supplied, so state/ was not read."
        body["status"] = "unavailable"
        return _dumps(body)
    return _dumps(_with_envelope(str(envelope_jsonl), blend=True))


def _with_envelope(text: str, *, blend: bool) -> dict[str, Any]:
    from aureon.core.hnc_field import blend_field, read_canonical_field

    previous_trace = os.environ.get("AUREON_HNC_TRACE_PATH")
    previous_bus = os.environ.get("AUREON_BUS_TRACE_DIR")
    directory = Path(tempfile.mkdtemp(prefix="aureon-public-field-"))
    trace = directory / "envelope.jsonl"
    bus_dir = directory / "bus"
    bus_dir.mkdir()
    try:
        payload = text if text.endswith("\n") else text + "\n"
        trace.write_text(payload, encoding="utf-8")
        os.environ["AUREON_HNC_TRACE_PATH"] = str(trace)
        os.environ["AUREON_BUS_TRACE_DIR"] = str(bus_dir)
        field = read_canonical_field(bus=object())
        if blend:
            body = blend_field(bus=object()).to_dict()
        else:
            body = field.to_dict()
    finally:
        if previous_trace is None:
            os.environ.pop("AUREON_HNC_TRACE_PATH", None)
        else:
            os.environ["AUREON_HNC_TRACE_PATH"] = previous_trace
        if previous_bus is None:
            os.environ.pop("AUREON_BUS_TRACE_DIR", None)
        else:
            os.environ["AUREON_BUS_TRACE_DIR"] = previous_bus
        trace.unlink(missing_ok=True)
        for child in bus_dir.glob("*"):
            child.unlink(missing_ok=True)
        bus_dir.rmdir()
        directory.rmdir()
    body["label"] = "inferred. Read from the envelope supplied to this process."
    body["status"] = "inferred" if body.get("available") is True else "unavailable"
    return body


@quiet
def lambda_engine_step(
    volatility: float | None = None,
    readings: list[dict[str, Any]] | None = None,
) -> str:
    """Run LambdaEngine.step, or return status unavailable.

    This is not HarmonicRealityField and it is not the committed brain replay. The committed replay ships no readings. A missing or short reading list returns status unavailable and does not fill lambda or coherence with 0. Auris-to-Lambda link: HOLD.

    Args:
        volatility: Finite volatility. Omitted is unavailable, not 0. Label: cited, LambdaEngine.step.
        readings: Objects with name, value, confidence, and state. Fewer than two returns status unavailable. Label: cited, huggingface/hnc-field/app.py. Auris-to-Lambda link: HOLD.
    """

    parsed, reason = _parse_readings(readings)
    vol = _finite(volatility)
    if parsed is None or vol is None:
        why = reason or "volatility is missing"
        return _dumps(
            {
                "auris_to_lambda": "HOLD",
                "label": (
                    "cited. The committed brain replay ships no LambdaEngine readings. "
                    "This is not HarmonicRealityField. Auris-to-Lambda link: HOLD."
                ),
                "lambda_t": None,
                "reason": why,
                "status": "unavailable",
            }
        )
    fd, name = tempfile.mkstemp(prefix="aureon-public-lambda-", suffix=".json")
    os.close(fd)
    path = Path(name)
    try:
        from aureon.core.aureon_lambda_engine import LambdaEngine, SubsystemReading

        engine = LambdaEngine(state_path=path)
        state = engine.step(parsed_readings(parsed, SubsystemReading), volatility=vol, auto_persist=False)
        body = state.to_dict()
    finally:
        path.unlink(missing_ok=True)
    body["auris_to_lambda"] = "HOLD"
    body["label"] = (
        "inferred. LambdaEngine.step on the supplied readings. "
        "Not HarmonicRealityField. Not the committed brain replay. "
        "Field names are the keys LambdaState.to_dict already returns. "
        "Auris-to-Lambda link: HOLD."
    )
    body["status"] = "inferred"
    return _dumps(body)


def parsed_readings(rows: list[dict[str, Any]], reading_type: Any) -> list[Any]:
    return [
        reading_type(
            name=row["name"],
            value=row["value"],
            confidence=row["confidence"],
            state=row["state"],
        )
        for row in rows
    ]


def _parse_readings(readings: list[dict[str, Any]] | None) -> tuple[list[dict[str, Any]] | None, str | None]:
    if readings is None:
        return None, "LambdaEngine path: unavailable. No readings were supplied."
    if not isinstance(readings, list) or len(readings) < 2:
        return None, "LambdaEngine path: unavailable. At least two readings are required."
    parsed: list[dict[str, Any]] = []
    for row in readings:
        if not isinstance(row, dict):
            return None, "LambdaEngine path: unavailable. A reading is missing fields."
        name = row.get("name")
        value = _finite(row.get("value"))
        confidence = _finite(row.get("confidence"))
        state = row.get("state")
        if not isinstance(name, str) or not name.strip() or value is None or confidence is None:
            return None, "LambdaEngine path: unavailable. A reading is missing fields."
        if not isinstance(state, str) or not state.strip():
            return None, "LambdaEngine path: unavailable. A reading is missing fields."
        parsed.append(
            {
                "name": name.strip(),
                "value": value,
                "confidence": confidence,
                "state": state.strip(),
            }
        )
    return parsed, None


def _texture(
    volatility: float | None,
    momentum: float | None,
    volume: float | None,
    spread: float | None,
) -> dict[str, float] | None:
    supplied: dict[str, float] = {}
    for key, raw in (
        ("volatility", volatility),
        ("momentum", momentum),
        ("volume", volume),
        ("spread", spread),
    ):
        if raw is None:
            continue
        number = _finite(raw)
        if number is None:
            continue
        supplied[key] = number
    return supplied or None


def _queen() -> Any:
    from aureon.utils.aureon_queen_hive_mind import QueenHiveMind

    return QueenHiveMind.__new__(QueenHiveMind)


@quiet
def auris_nodes(
    volatility: float | None = None,
    momentum: float | None = None,
    volume: float | None = None,
    spread: float | None = None,
) -> str:
    """Nine nodes. Real function: QueenHiveMind.read_auris_nodes.

    This tool is the nine nodes. It is not the conjecture (not called), not the persona (not scored), and not the coherence evaluator. The coherence evaluator is auris_coherence. Only the nine nodes and get_auris_coherence are real functions exposed here.

    A missing field is omitted. Nothing is filled with zero. Label: inferred.

    Args:
        volatility: Optional Tiger and related input. Omitted stays omitted. Label: cited, _auris_input.
        momentum: Optional Falcon and Dolphin input. Omitted stays omitted. Label: cited, _auris_input.
        volume: Optional Falcon and CargoShip input. Omitted stays omitted. Label: cited, _auris_input.
        spread: Optional Deer input. Omitted stays omitted. Label: cited, _auris_input.
    """

    market = _texture(volatility, momentum, volume, spread)
    nodes = _queen().read_auris_nodes(market)
    missing = sorted(name for name, row in nodes.items() if row.get("value") is None)
    return _dumps(
        {
            "auris": "nine nodes",
            "label": "inferred. QueenHiveMind.read_auris_nodes. A missing field is not filled.",
            "missing_nodes": missing,
            "nodes": nodes,
            "which_auris": AURIS_FOUR,
        }
    )


@quiet
def auris_coherence(
    volatility: float | None = None,
    momentum: float | None = None,
    volume: float | None = None,
    spread: float | None = None,
) -> str:
    """Coherence evaluator. Real function: QueenHiveMind.get_auris_coherence.

    This tool is the coherence evaluator. It is not the conjecture (not called), not the nine nodes (those are read_auris_nodes and AURIS_NODES on auris_nodes), and not the persona (not scored). Only the nine nodes and get_auris_coherence are real functions exposed here.

    Whenever any of the nine nodes has no reading, status is no_data and coherence is null. The missing node names are listed. Nothing is filled with zero. Auris-to-Lambda link: HOLD. Trade readiness: HOLD.

    Args:
        volatility: Optional. Omitted is not filled with zero. Label: cited, _auris_input.
        momentum: Optional. Omitted is not filled with zero. Label: cited, _auris_input.
        volume: Optional. Omitted is not filled with zero. Label: cited, _auris_input.
        spread: Optional. Omitted is not filled with zero. Label: cited, _auris_input.
    """

    market = _texture(volatility, momentum, volume, spread)
    queen = _queen()
    nodes = queen.read_auris_nodes(market)
    coherence, status = queen.get_auris_coherence(market)
    missing = sorted(name for name, row in nodes.items() if row.get("value") is None)
    if missing or coherence is None:
        return _dumps(
            {
                "auris": "coherence evaluator",
                "auris_to_lambda": "HOLD",
                "coherence": None,
                "label": "inferred. get_auris_coherence returned no complete nine-node reading. Auris-to-Lambda link: HOLD.",
                "missing_nodes": missing,
                "status": "no_data",
                "trade_readiness": "HOLD",
                "which_auris": AURIS_FOUR,
            }
        )
    return _dumps(
        {
            "auris": "coherence evaluator",
            "auris_to_lambda": "HOLD",
            "coherence": coherence,
            "label": "inferred. This is the evaluator return, not a track record. Auris-to-Lambda link: HOLD.",
            "missing_nodes": missing,
            "status": status,
            "trade_readiness": "HOLD",
            "which_auris": AURIS_FOUR,
        }
    )


def _lambda_column() -> list[float]:
    path = paths.qgita_series()
    values: list[float] = []
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or "Lambda" not in reader.fieldnames:
            return []
        for row in reader:
            try:
                values.append(float(row["Lambda"]))
            except (TypeError, ValueError):
                continue
    return values


def _event_record(item: Any, kind: str) -> dict[str, Any]:
    if kind == "ftcp":
        return {
            "adapter": "QGITAMarketAnalyzer.analyze",
            "curvature": float(item.curvature),
            "is_valid": bool(item.is_valid),
            "kind": "FTCP",
            "knot_index": int(item.knot_index),
            "timestamp": float(item.timestamp),
        }
    return {
        "adapter": "QGITAMarketAnalyzer.analyze",
        "event_type": str(item.event_type.value),
        "kind": "lighthouse",
        "lighthouse_intensity": float(item.lighthouse_intensity),
        "timestamp": float(item.timestamp),
    }


@quiet
def qgita_analyze(
    values: list[float] | None = None,
    timestamps: list[float] | None = None,
) -> str:
    """Run QGITAMarketAnalyzer.analyze and drop the signals object.

    Events are the adapter return, not a detection rate. Detection rate: HOLD. False-alarm rate: HOLD. The bundled series is cited-unverified and is not public market data.

    Args:
        values: Optional series. Omitted loads the vendored de440 Lambda column. A supplied series is inferred and is not the committed replay. Length must be at least 10. Label: cited for the file, inferred for a pasted series.
        timestamps: Optional clocks, one per value. Omitted uses the sample index. Label: cited, the Space clock.
    """

    supplied = values is not None
    series = list(values) if supplied else _lambda_column()
    if supplied:
        cleaned: list[float] = []
        for item in series:
            number = _finite(item)
            if number is None:
                return _dumps(
                    {
                        "detection_rate": "HOLD",
                        "false_alarm_rate": "HOLD",
                        "label": "inferred",
                        "reason": "A value is missing.",
                        "status": "unavailable",
                    }
                )
            cleaned.append(number)
        series = cleaned
    if len(series) < 10:
        return _dumps(
            {
                "detection_rate": "HOLD",
                "false_alarm_rate": "HOLD",
                "label": "cited. analyze returns insufficient_data below 10 samples.",
                "reason": "At least ten values are required.",
                "status": "unavailable",
            }
        )
    if timestamps is None:
        clocks = [float(index) for index in range(len(series))]
        clock_label = "cited. Sample index, the Space clock."
    else:
        if len(timestamps) != len(series):
            return _dumps(
                {
                    "detection_rate": "HOLD",
                    "false_alarm_rate": "HOLD",
                    "label": "inferred",
                    "reason": "timestamps and values differ in length.",
                    "status": "unavailable",
                }
            )
        clocks = []
        for item in timestamps:
            number = _finite(item)
            if number is None:
                return _dumps(
                    {
                        "detection_rate": "HOLD",
                        "false_alarm_rate": "HOLD",
                        "label": "inferred",
                        "reason": "A timestamp is missing.",
                        "status": "unavailable",
                    }
                )
            clocks.append(number)
        clock_label = "inferred. Caller-supplied clocks."
    from aureon.wisdom.aureon_qgita_framework import QGITAMarketAnalyzer

    analyzer = QGITAMarketAnalyzer()
    for index, value in enumerate(series):
        analyzer.feed_price(float(value), timestamp=clocks[index])
    raw = analyzer.analyze()
    stage1 = raw.get("stage1") if isinstance(raw.get("stage1"), dict) else {}
    stage2 = raw.get("stage2") if isinstance(raw.get("stage2"), dict) else {}
    valid = list(stage1.get("valid_ftcps") or [])
    events = list(stage2.get("lighthouse_events") or [])
    body: dict[str, Any] = {
        "clock": clock_label,
        "coherence": raw.get("coherence"),
        "detection_rate": "HOLD",
        "false_alarm_rate": "HOLD",
        "ftcp_count": stage1.get("ftcp_count"),
        "ftcps": [_event_record(item, "ftcp") for item in valid],
        "label": (
            "cited-unverified bundled series. Not public market data."
            if not supplied
            else "inferred. Adapter run on the supplied series. Not the committed replay."
        ),
        "lhe_count": stage2.get("lhe_count"),
        "lighthouse_events": [_event_record(item, "lhe") for item in events],
        "regime": raw.get("regime"),
        "samples_fed": len(series),
        "status": raw.get("status", "unavailable"),
    }
    return _dumps(body)


@quiet
def organism_replay_read() -> str:
    """Read the committed circulation replay file. This does not start a seat.

    Connectivity figures are cited from the file. The fault block is seeded synthetic input, not telemetry. A claim that those faults are recorded seat faults is HOLD.

    Args:
        none: This tool takes no inputs. Label: cited, huggingface/organism-replay/replay/organism.json.
    """

    record = _load(paths.organism_json())
    connectivity = record.get("connectivity") if isinstance(record.get("connectivity"), dict) else {}
    self_model = record.get("self_model") if isinstance(record.get("self_model"), dict) else {}
    prediction = self_model.get("prediction") if isinstance(self_model.get("prediction"), dict) else {}
    fault = self_model.get("fault") if isinstance(self_model.get("fault"), dict) else {}
    seats = connectivity.get("seats") if isinstance(connectivity.get("seats"), dict) else {}
    isolated = connectivity.get("isolated")
    topics = _dashboard_topics()
    return _dumps(
        {
            "cited": {
                "connected": connectivity.get("connected"),
                "connectivity_score": connectivity.get("score"),
                "http_seat_bound": connectivity.get("http_seat_bound"),
                "isolated": isolated,
                "label": "cited, huggingface/organism-replay/replay/organism.json",
                "prediction_accuracy": prediction.get("accuracy"),
                "prediction_baseline_accuracy": prediction.get("baseline_accuracy"),
                "roster": connectivity.get("roster"),
                "seats": seats,
                "verdict": connectivity.get("verdict"),
            },
            "dashboard_topics": topics,
            "label": "cited replay file. Circulation was not started.",
            "seeded_synthetic_fault": {
                "detection_rate_in_file": fault.get("detection_rate"),
                "false_alarm_rate_in_file": fault.get("false_alarm_rate"),
                "hold": (
                    "A claim that these are recorded seat faults is HOLD. "
                    "These figures are not a QGITA detection rate and not telemetry."
                ),
                "label": "Seeded synthetic input, not telemetry.",
                "origin": fault.get("origin"),
                "seed": fault.get("seed"),
            },
        }
    )


def _dashboard_topics() -> list[str]:
    topics = (
        "ics.body.state",
        "ics.mind.state",
        "ics.source.state",
        "ics.soul.state",
        "ics.hnc.state",
        "ics.monologue",
    )
    try:
        from aureon.core.aureon_thought_bus import ThoughtBus
        from aureon.core.cognitive_dashboard import CognitiveDashboard

        bus = ThoughtBus(persist_path=None)
        CognitiveDashboard(thought_bus=bus)
    except Exception:
        return [f"Dashboard topic {topic}: unavailable" for topic in topics]
    lines = []
    for topic in topics:
        found = bus.recall(topic, limit=1)
        if found:
            lines.append(f"Dashboard topic {topic}: present in the replay")
        else:
            lines.append(f"Dashboard topic {topic}: unavailable")
    return lines


@quiet
def organism_catalog() -> str:
    """List circulation seats, algorithmic nodes, and deterministic systems.

    These are names in source. This tool does not start circulation, self-repair, or self-code. Label: cited.

    Args:
        none: This tool takes no inputs. Label: cited, circulation_seats, list_nodes, and list_systems.
    """

    from aureon.core.algorithmic_nodes import list_nodes
    from aureon.core.deterministic_systems import list_systems
    from aureon.core.organism_circulation import circulation_seats

    return _dumps(
        {
            "label": "cited. Names in source. Seats are not running.",
            "nodes": list_nodes(),
            "seats": list(circulation_seats()),
            "systems": list_systems(),
        }
    )
