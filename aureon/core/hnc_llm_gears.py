"""HNC gears on one Aureon reply.

Three gears turn for every completion. None of them calls another model.

- parse: the same JSON-object extract the HNC-5000 worker uses
- field: the canonical HNC field, read and not invented
- auris: the nine-node vote over that parse and that field

A gear has turned when it finished. It is engaged when it found a real
signal: a JSON object, a fresh field, or nine votes.
"""

from __future__ import annotations

import json
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


class _GearVault:
    """The slices Auris reads. Values come from the parse and the field."""

    def __init__(self, parsed: dict[str, Any] | None, field_available: bool, lambda_reading: Any) -> None:
        engaged = parsed is not None
        self.love_amplitude = 1.0 if engaged else 0.0
        self.gratitude_score = 1.0 if engaged else 0.0
        # lambda_reading is the CoherenceDecision from assess_coherence. An
        # accepted reading, including a real 0.0, reaches Auris. A held or
        # absent reading is None, so it is not the same input as zero.
        accepted = lambda_reading is not None and getattr(lambda_reading, "accepted", False)
        self.last_lambda_t = float(lambda_reading.value) if accepted else None
        self.cortex_snapshot = (
            {"delta": 0.0, "alpha": 0.0, "gamma": 1.0}
            if engaged
            else {"delta": 1.0, "alpha": 0.0, "gamma": 0.0}
        )
        self.dominant_chakra = "love" if engaged else "foundation"
        self.max_size = 10000
        self._field_available = field_available

    def __len__(self) -> int:
        return 1 if self._field_available else 0


def turn_gears(text: str, bus: Any = None) -> dict[str, Any]:
    """Run parse, the HNC field, and Auris on one reply."""
    parsed = parse_hnc_object(text)
    gears: list[dict[str, Any]] = [{
        "name": "parse",
        "turned": True,
        "engaged": parsed is not None,
    }]

    field_available = False
    lambda_reading = None
    field_gear: dict[str, Any] = {"name": "field", "turned": False, "engaged": False}
    try:
        from aureon.core.hnc_field import assess_coherence, read_canonical_field

        field = read_canonical_field(bus)
        field_available = bool(field.available)
        # The one shared coherence check: bool, NaN, inf and values outside
        # [0, 1] are HOLD, not a reading.
        lambda_reading = assess_coherence(getattr(field, "coherence_gamma", None))
        field_gear["coherence"] = lambda_reading.value if lambda_reading.accepted else None
        field_gear["coherence_verdict"] = lambda_reading.verdict
        field_gear["turned"] = True
        field_gear["engaged"] = field_available
        field_gear["available"] = field_available
    except Exception as exc:  # noqa: BLE001 — a failed gear is reported, not hidden
        field_gear["error"] = f"{type(exc).__name__}: {exc}"
    gears.append(field_gear)

    auris_gear: dict[str, Any] = {"name": "auris", "turned": False, "engaged": False}
    try:
        from aureon.vault.auris_metacognition import AurisMetacognition

        vote = AurisMetacognition().vote(_GearVault(parsed, field_available, lambda_reading))
        auris_gear["turned"] = True
        auris_gear["engaged"] = vote.total == 9
        auris_gear["consensus"] = vote.consensus
        auris_gear["agreeing"] = vote.agreeing
        auris_gear["total"] = vote.total
    except Exception as exc:  # noqa: BLE001
        auris_gear["error"] = f"{type(exc).__name__}: {exc}"
    gears.append(auris_gear)

    return {
        "gears": gears,
        "all_turned": all(gear["turned"] for gear in gears),
        "parsed": parsed is not None,
    }


def attach_gears(body: dict[str, Any], text: str, bus: Any = None) -> dict[str, Any]:
    """Add the gear receipt beside the reply. The reply text stays unchanged."""
    out = dict(body)
    out["hnc_gears"] = turn_gears(text, bus=bus)
    return out
