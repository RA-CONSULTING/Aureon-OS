"""Connectivity of the circulation bus, and a self-model scored on held-out questions.

The run is in-process. It publishes real circulation pulses on a ThoughtBus and
reads them back. It does not bind a port, start a seat process, place an
order, or call an external model.

The self-model's next-step rule is fixed before the score is read:

1. If every value is a number and the step is constant, add that step.
2. Otherwise the smallest period ``p`` with ``value[i] == value[i % p]``.
3. Otherwise the last value (persistence).

The baseline is persistence only.

A fault trial withholds a pulse (silent), or publishes that seat's own
payload with ``loop`` set to ``fault`` and ``error`` set to ``injected``.
The self-model flags a missing pulse, a loop other than the loop it saw on
its own healthy pulses, or an error field. The baseline flags a missing
pulse only. The label is the injection.

Figures from this module are connectivity, self-prediction accuracy, and
fault-detection rate. They are not a claim that the system is conscious or
alive.
"""

from __future__ import annotations

import os
import random
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

SEED = 20261024
TICKS = 8
FAULT_TRIALS = 48
_NOTE = (
    "These figures are connectivity, self-prediction accuracy, and fault-detection rate. "
    "They are not a claim that the system is conscious or alive."
)
_MODES = ("clean", "silent", "error")


def predict_next(values: list[Any]) -> Any:
    """Pre-registered next-step rule. See the module docstring."""

    if not values:
        return None
    if len(values) == 1:
        return values[0]
    if all(isinstance(value, (int, float)) and not isinstance(value, bool) for value in values):
        deltas = [values[index] - values[index - 1] for index in range(1, len(values))]
        if all(delta == deltas[0] for delta in deltas):
            return values[-1] + deltas[0]
    for period in range(1, len(values)):
        if all(values[index] == values[index % period] for index in range(len(values))):
            return values[len(values) % period]
    return values[-1]


def _persist(values: list[Any]) -> Any:
    if not values:
        return None
    return values[-1]


def _mode(values: list[str]) -> str | None:
    if not values:
        return None
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return sorted(counts, key=lambda key: (-counts[key], key))[0]


def _rates(called: list[bool], labels: list[int]) -> dict[str, float | int | None]:
    tp = fp = tn = fn = 0
    for flag, label in zip(called, labels):
        if flag and label == 1:
            tp += 1
        elif flag and label == 0:
            fp += 1
        elif label == 0:
            tn += 1
        else:
            fn += 1
    detection = tp / (tp + fn) if (tp + fn) else None
    false_alarm = fp / (fp + tn) if (fp + tn) else None
    return {
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "detection_rate": detection,
        "false_alarm_rate": false_alarm,
    }


@contextmanager
def _isolated_circulation() -> Iterator[Any]:
    """Point the process bus and connector file at a temp dir, then put them back."""

    import aureon.core.aureon_thought_bus as busmod
    import aureon.core.organism_circulation as circ

    tmp = tempfile.TemporaryDirectory()
    previous_bus_path = os.environ.get("AUREON_THOUGHT_BUS_PATH")
    previous_state = os.environ.get("AUREON_ORGANISM_STATE")
    previous_instance = busmod._thought_bus_instance
    previous_subscribed = circ._SUBSCRIBED
    previous_wired = circ._AUDIT_WIRED
    previous_audit_bus = circ._AUDIT_BUS
    with circ._LOCK:
        previous_inbox = circ._STATE["inbox"]
        previous_loops = circ._STATE["loops"]
        previous_seen = circ._STATE.get("self_model_seen")
        previous_counts = circ._STATE.get("consume_count")
        previous_samples = circ._STATE.get("latency_samples")
        circ._STATE["inbox"] = {}
        circ._STATE["loops"] = {}
        circ._STATE["self_model_seen"] = {}
        circ._STATE["consume_count"] = {}
        circ._STATE["latency_samples"] = []
    os.environ["AUREON_THOUGHT_BUS_PATH"] = str(Path(tmp.name) / "thoughts.jsonl")
    os.environ["AUREON_ORGANISM_STATE"] = str(Path(tmp.name) / "state")
    with busmod._bus_lock:
        busmod._thought_bus_instance = None
    circ._SUBSCRIBED = False
    circ._AUDIT_WIRED = False
    circ._AUDIT_BUS = None
    try:
        yield circ
    finally:
        with busmod._bus_lock:
            busmod._thought_bus_instance = previous_instance
        circ._SUBSCRIBED = previous_subscribed
        circ._AUDIT_WIRED = previous_wired
        circ._AUDIT_BUS = previous_audit_bus
        with circ._LOCK:
            circ._STATE["inbox"] = previous_inbox
            circ._STATE["loops"] = previous_loops
            if previous_seen is None:
                circ._STATE.pop("self_model_seen", None)
            else:
                circ._STATE["self_model_seen"] = previous_seen
            if previous_counts is None:
                circ._STATE.pop("consume_count", None)
            else:
                circ._STATE["consume_count"] = previous_counts
            if previous_samples is None:
                circ._STATE.pop("latency_samples", None)
            else:
                circ._STATE["latency_samples"] = previous_samples
        if previous_bus_path is None:
            os.environ.pop("AUREON_THOUGHT_BUS_PATH", None)
        else:
            os.environ["AUREON_THOUGHT_BUS_PATH"] = previous_bus_path
        if previous_state is None:
            os.environ.pop("AUREON_ORGANISM_STATE", None)
        else:
            os.environ["AUREON_ORGANISM_STATE"] = previous_state
        tmp.cleanup()


def _finite(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value == value and value not in (float("inf"), float("-inf"))


def _latency_stats(samples: list[float]) -> dict[str, float | int | None]:
    if not samples:
        return {"count": 0, "min": None, "mean": None, "max": None}
    return {
        "count": len(samples),
        "min": min(samples),
        "mean": sum(samples) / len(samples),
        "max": max(samples),
    }


def _field_series(pulses: list[dict[str, Any]], field: str) -> list[Any]:
    return [pulse[field] for pulse in pulses if field in pulse]


def _score_prediction(by_seat: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    questions: list[dict[str, Any]] = []
    held_out = None
    for name in sorted(by_seat):
        pulses = sorted(by_seat[name], key=lambda pulse: (pulse.get("tick") is None, pulse.get("tick")))
        if not pulses:
            continue
        last = pulses[-1]
        history = pulses[:-1]
        if held_out is None:
            held_out = last.get("tick")
        fields = ["tick", "loop"]
        if any("stage" in pulse for pulse in pulses):
            fields.append("stage")
        for field in fields:
            past = _field_series(history, field)
            actual = last.get(field)
            predicted = predict_next(past)
            baseline = _persist(past)
            questions.append(
                {
                    "seat": name,
                    "field": field,
                    "held_out_tick": last.get("tick"),
                    "predicted": predicted,
                    "baseline": baseline,
                    "actual": actual,
                    "correct": predicted == actual,
                    "baseline_correct": baseline == actual,
                }
            )
    total = len(questions)
    correct = sum(1 for row in questions if row["correct"])
    baseline_correct = sum(1 for row in questions if row["baseline_correct"])
    return {
        "rule": "constant numeric step, else smallest repeating period, else persistence",
        "baseline": "persistence",
        "held_out": "last pulse of each seat",
        "held_out_tick": held_out,
        "questions": total,
        "correct": correct,
        "accuracy": (correct / total) if total else None,
        "baseline_correct": baseline_correct,
        "baseline_accuracy": (baseline_correct / total) if total else None,
        "per_question": questions,
    }


def _self_flags(payload: dict[str, Any] | None, expected_loop: str | None) -> bool:
    if payload is None:
        return True
    if payload.get("error"):
        return True
    if expected_loop is not None and payload.get("loop") != expected_loop:
        return True
    return False


def _fault_trials(circ: Any, bus: Any, seats: list[dict[str, str]], expected_loop: str | None, seed: int, trials: int) -> dict[str, Any]:
    rng = random.Random(seed)
    rows: list[dict[str, Any]] = []
    self_called: list[bool] = []
    baseline_called: list[bool] = []
    labels: list[int] = []
    for index in range(trials):
        seat = rng.choice(seats)
        mode = rng.choice(_MODES)
        label = 0 if mode == "clean" else 1
        payload = None
        if mode != "silent":
            payload = circ._payload_for(seat, index)
            payload["kind"] = "fault_probe"
            payload["probe_id"] = index
            if mode == "error":
                payload["loop"] = "fault"
                payload["error"] = "injected"
            from aureon.core.aureon_thought_bus import Thought

            bus.publish(Thought(source=seat["name"], topic=circ._CIRCULATION, payload=payload))
        seen = _probe_payload(bus, seat["name"], index)
        self_flag = _self_flags(seen, expected_loop)
        baseline_flag = seen is None
        self_called.append(self_flag)
        baseline_called.append(baseline_flag)
        labels.append(label)
        rows.append(
            {
                "trial": index,
                "seat": seat["name"],
                "mode": mode,
                "label": label,
                "self_model_flagged": self_flag,
                "baseline_flagged": baseline_flag,
            }
        )
    self_rates = _rates(self_called, labels)
    baseline_rates = _rates(baseline_called, labels)
    return {
        "seed": seed,
        "trials": trials,
        "modes": list(_MODES),
        "self_model_rule": "missing pulse, loop other than the loop observed on healthy pulses, or an error field",
        "baseline_rule": "missing pulse only",
        "expected_loop": expected_loop,
        "self_model": self_rates,
        "baseline": baseline_rates,
        "detection_rate": self_rates["detection_rate"],
        "false_alarm_rate": self_rates["false_alarm_rate"],
        "baseline_detection_rate": baseline_rates["detection_rate"],
        "baseline_false_alarm_rate": baseline_rates["false_alarm_rate"],
        "trials_raw": rows,
    }


def _probe_payload(bus: Any, seat: str, probe_id: int) -> dict[str, Any] | None:
    found = None
    for item in bus.recall(topic_prefix="organism.circulation", limit=5000):
        payload = item.get("payload")
        if not isinstance(payload, dict):
            continue
        if item.get("source") == seat and payload.get("probe_id") == probe_id:
            found = payload
    return found


def evaluate_organism(
    *,
    ticks: int = TICKS,
    fault_trials: int = FAULT_TRIALS,
    seed: int = SEED,
    disabled: tuple[str, ...] = (),
) -> dict[str, Any]:
    """Run the circulation seats and score connectivity plus the self-model."""

    with _isolated_circulation() as circ:
        for name in disabled:
            circ.switch_connector(name, False)
        circ.ensure_audit_subscribers()
        from aureon.core.aureon_thought_bus import get_thought_bus

        bus = get_thought_bus()
        started = time.perf_counter()
        for tick in range(ticks):
            circ._publish_tick(tick)
        elapsed = time.perf_counter() - started
        roster = list(circ.circulation_seats())
        names = [seat["name"] for seat in roster]
        thoughts = bus.recall(topic_prefix="organism.", limit=5000)
        pulses = [
            item
            for item in thoughts
            if item.get("topic") == circ._CIRCULATION and isinstance(item.get("payload"), dict) and item["payload"].get("kind") == "pulse"
        ]
        self_model_messages = [item for item in thoughts if item.get("topic") == "organism.self_model"]
        by_seat: dict[str, list[dict[str, Any]]] = {name: [] for name in names}
        published = {name: 0 for name in names}
        for item in pulses:
            source = str(item.get("source") or "")
            if source not in published:
                continue
            published[source] += 1
            by_seat[source].append(item["payload"])
        with circ._LOCK:
            consumed = {name: int((circ._STATE.get("consume_count") or {}).get(name, 0)) for name in names}
            samples = [float(value) for value in (circ._STATE.get("latency_samples") or []) if _finite(value)]
        seats: dict[str, Any] = {}
        isolated: list[str] = []
        for seat in roster:
            name = seat["name"]
            is_isolated = published[name] == 0 or consumed[name] == 0
            if is_isolated:
                isolated.append(name)
            last = by_seat[name][-1] if by_seat[name] else {}
            seats[name] = {
                "role": seat["role"],
                "module": seat["module"],
                "publishes": published[name] > 0,
                "consumes": consumed[name] > 0,
                "published": published[name],
                "consumed": consumed[name],
                "isolated": is_isolated,
                "last_tick": last.get("tick"),
                "last_loop": last.get("loop"),
            }
        http_bound = False
        http_rows = by_seat.get("http_seat") or []
        if http_rows:
            http_bound = bool(http_rows[-1].get("http_seat_bound"))
        connected = len(roster) - len(isolated)
        score = (connected / len(roster)) if roster else None
        prediction = _score_prediction({name: rows for name, rows in by_seat.items() if rows})
        observed_loops = [pulse.get("loop") for rows in by_seat.values() for pulse in rows if isinstance(pulse.get("loop"), str)]
        expected_loop = _mode([loop for loop in observed_loops if isinstance(loop, str)])
        faults = _fault_trials(circ, bus, roster, expected_loop, seed, fault_trials)
        errors = [
            {"seat": name, "tick": pulse.get("tick"), "error": pulse.get("error")}
            for name, rows in by_seat.items()
            for pulse in rows
            if pulse.get("error")
        ]
        recent_actions = [
            {
                "seat": name,
                "tick": (by_seat[name][-1].get("tick") if by_seat[name] else None),
                "loop": (by_seat[name][-1].get("loop") if by_seat[name] else None),
                "stage": (by_seat[name][-1].get("stage") if by_seat[name] else None),
            }
            for name in names
        ]
        circulation_messages = len(pulses)
        rate = (circulation_messages / elapsed) if elapsed > 0 else None
        return {
            "schema": "aureon.organism-proof.v1",
            "live_trading": False,
            "orders_placed": False,
            "external_llm": False,
            "ollama": False,
            "cognition": "internal",
            "note": _NOTE,
            "seed": seed,
            "scope": {
                "bus": "aureon.core.aureon_thought_bus.ThoughtBus",
                "topic": "organism.circulation",
                "self_model_topic": "organism.self_model",
                "http_listener_started": False,
                "process_seats_not_started": [
                    "market-status",
                    "orca",
                    "fusion",
                    "gateway",
                    "live-bridge",
                    "error-sink",
                ],
            },
            "connectivity": {
                "verdict": "fail" if isolated else "pass",
                "score": score,
                "roster": len(roster),
                "connected": connected,
                "isolated": isolated,
                "ticks": ticks,
                "circulation_messages": circulation_messages,
                "self_model_messages": len(self_model_messages),
                "latency_samples": len(samples),
                "http_seat_bound": http_bound,
                "disabled": list(disabled),
                "seats": seats,
                "timing": {
                    "elapsed_s": elapsed,
                    "messages_per_second": rate,
                    "latency_s": _latency_stats(samples),
                },
            },
            "self_model": {
                "external_llm": False,
                "ollama": False,
                "cognition": "internal",
                "health": {name: (not row["isolated"]) for name, row in seats.items()},
                "capabilities": [{"name": seat["name"], "role": seat["role"], "module": seat["module"]} for seat in roster],
                "recent_actions": recent_actions,
                "errors": errors,
                "prediction": prediction,
                "fault": faults,
            },
        }


def render_organism_markdown(report: dict[str, Any]) -> str:
    connectivity = report["connectivity"]
    prediction = report["self_model"]["prediction"]
    fault = report["self_model"]["fault"]
    isolated = connectivity["isolated"]
    isolated_text = ", ".join(isolated) if isolated else "none"
    lines = [
        "# Circulation connectivity and self-model",
        "",
        report["note"],
        "",
        "Internal cognition only. No external model was called. Live trading stayed off. No order was placed.",
        f"Connectivity verdict: **{connectivity['verdict']}**. Score `{connectivity['score']}`.",
        f"Roster `{connectivity['roster']}`, connected `{connectivity['connected']}`, isolated: {isolated_text}.",
        (
            f"Circulation messages `{connectivity['circulation_messages']}` over `{connectivity['ticks']}` ticks. "
            f"Self-model readings on the bus: `{connectivity['self_model_messages']}`."
        ),
        (
            f"Latency samples `{connectivity['latency_samples']}`. "
            f"Messages per second and latency min/mean/max are in the raw `timing` object from this run."
        ),
        f"HTTP seat bound during this run: `{connectivity['http_seat_bound']}`.",
        (
            f"Self-prediction accuracy `{prediction['accuracy']}` "
            f"({prediction['correct']}/{prediction['questions']}). "
            f"Persistence baseline `{prediction['baseline_accuracy']}` "
            f"({prediction['baseline_correct']}/{prediction['questions']})."
        ),
        (
            f"Fault detection rate `{fault['detection_rate']}`, false-alarm rate `{fault['false_alarm_rate']}`. "
            f"Baseline detection `{fault['baseline_detection_rate']}`, "
            f"baseline false-alarm `{fault['baseline_false_alarm_rate']}`."
        ),
        f"Fault trials `{fault['trials']}`, seed `{fault['seed']}`.",
        "",
    ]
    return "\n".join(lines)
