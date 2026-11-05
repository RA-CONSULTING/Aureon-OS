"""Auris node readings on synthetic inputs, checked against input guards.

Numeric values are whatever `read_auris_nodes` and `get_auris_coherence` return.
The ground-truth labels are the input guards in those methods: which roles have
a value when a field is present, missing, non-finite, or a bool. The numeric
formula is not reimplemented here.

Baselines are the null call, the all-zero input, and the same numbers moved
onto different keys.
"""

from __future__ import annotations

import math
import random
from typing import Any

from aureon.evidence.serialize import csv_text

FIELDS = ("volatility", "momentum", "volume", "spread")
LEVELS = (0.0, 0.25, 0.5, 0.75, 1.0)
RANDOM_SEED = 20261105
RANDOM_CASES = 16
# new key <- source key. Same four numbers, different roles.
KEY_PERMUTATION = {
    "volatility": "spread",
    "momentum": "volatility",
    "volume": "momentum",
    "spread": "volume",
}
# Transcribed from QueenHiveMind._auris_role_value. Empty means the role has
# no market input in that method. This is the guard, not the numeric expression.
ROLE_REQUIRED_INPUTS = {
    "volatility": ("volatility",),
    "momentum": ("momentum", "volume"),
    "stability": ("volatility",),
    "emotion": ("momentum",),
    "sensing": ("spread",),
    "love": ("volatility",),
    "infrastructure": ("volume",),
    "memory": (),
    "symbiosis": (),
}


def _reader():
    from aureon.utils.aureon_queen_hive_mind import AURIS_NODES, QueenHiveMind

    return QueenHiveMind.__new__(QueenHiveMind), AURIS_NODES


def _finite_input(raw: Any) -> bool:
    if isinstance(raw, bool) or raw is None:
        return False
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return False
    return math.isfinite(value)


def expects_value(role: str, market: Any) -> bool:
    required = ROLE_REQUIRED_INPUTS[role]
    if not required or not isinstance(market, dict):
        return False
    return all(key in market and _finite_input(market[key]) for key in required)


def _record_input(raw: Any) -> str:
    if isinstance(raw, bool):
        return "true" if raw else "false"
    if isinstance(raw, float) and raw != raw:
        return "nan"
    if isinstance(raw, str):
        return f"str:{raw}"
    if raw is None:
        return ""
    return repr(raw)


def _label_market(market: Any) -> dict[str, str]:
    if not isinstance(market, dict):
        return dict.fromkeys(FIELDS, "")
    return {key: _record_input(market[key]) if key in market else "" for key in FIELDS}


def _zeros() -> dict[str, float]:
    return dict.fromkeys(FIELDS, 0.0)


def _cases() -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = [
        {"case_id": "null", "kind": "null", "market": None},
        {"case_id": "empty", "kind": "null", "market": {}},
        {"case_id": "zeros", "kind": "zero", "market": _zeros()},
        {"case_id": "ones", "kind": "full", "market": dict.fromkeys(FIELDS, 1.0)},
    ]
    for field in FIELDS:
        for level in LEVELS:
            market = _zeros()
            market[field] = level
            cases.append(
                {
                    "case_id": f"sweep_{field}_{str(level).replace('.', 'p')}",
                    "kind": "sweep",
                    "sweep_field": field,
                    "market": market,
                }
            )
        market = dict.fromkeys(FIELDS, 0.5)
        del market[field]
        cases.append(
            {
                "case_id": f"missing_{field}",
                "kind": "ablation",
                "market": market,
            }
        )
    cases.append(
        {
            "case_id": "bool_volatility",
            "kind": "edge",
            "market": {**_zeros(), "volatility": True},
        }
    )
    cases.append(
        {
            "case_id": "nan_volatility",
            "kind": "edge",
            "market": {**_zeros(), "volatility": float("nan")},
        }
    )
    cases.append(
        {
            "case_id": "numeric_string_spread",
            "kind": "edge",
            "market": {**_zeros(), "spread": "0.2"},
        }
    )
    rng = random.Random(RANDOM_SEED)
    for index in range(RANDOM_CASES):
        market = {key: rng.random() for key in FIELDS}
        cases.append(
            {
                "case_id": f"random_{index:02d}",
                "kind": "seeded_random",
                "market": market,
            }
        )
        shuffled = {key: market[KEY_PERMUTATION[key]] for key in FIELDS}
        cases.append(
            {
                "case_id": f"random_{index:02d}_shuffled_keys",
                "kind": "shuffled_keys",
                "twin": f"random_{index:02d}",
                "market": shuffled,
            }
        )
    return cases


def _distance(left: dict[str, Any], right: dict[str, Any]) -> float:
    """Mean absolute gap. A missing-versus-present node counts as 1."""

    names = sorted(set(left) | set(right))
    gaps: list[float] = []
    for name in names:
        a = left[name]
        b = right[name]
        if a is None and b is None:
            continue
        if a is None or b is None:
            gaps.append(1.0)
        else:
            gaps.append(abs(float(a) - float(b)))
    if not gaps:
        return 0.0
    return sum(gaps) / len(gaps)


def _median(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2.0


def run_auris() -> dict[str, Any]:
    reader, nodes = _reader()
    role_by_name = {name: spec["role"] for name, spec in nodes.items()}
    unknown = sorted(set(role_by_name.values()) - set(ROLE_REQUIRED_INPUTS))
    if unknown:
        raise RuntimeError(f"AURIS roles without a transcribed guard: {unknown}")

    rows: list[dict[str, Any]] = []
    by_case: dict[str, dict[str, Any]] = {}
    coherence_status: dict[str, str] = {}
    checks = 0
    mismatches = 0
    numeric_coherence = 0

    for case in _cases():
        market = case["market"]
        coherence, status = reader.get_auris_coherence(market)
        readings = reader.read_auris_nodes(market)
        if coherence is not None:
            numeric_coherence += 1
            coherence = float(coherence)
        coherence_status[case["case_id"]] = str(status)
        values: dict[str, float | None] = {}
        labels = _label_market(market)
        for name in sorted(readings):
            item = readings[name]
            role = role_by_name[name]
            expected = expects_value(role, market)
            present = item.get("value") is not None
            checks += 1
            match = present is expected
            if not match:
                mismatches += 1
            value = None if item.get("value") is None else float(item["value"])
            weighted = None if item.get("weighted_value") is None else float(item["weighted_value"])
            values[name] = value
            rows.append(
                {
                    "case_id": case["case_id"],
                    "kind": case["kind"],
                    "twin": case.get("twin", ""),
                    "volatility": labels["volatility"],
                    "momentum": labels["momentum"],
                    "volume": labels["volume"],
                    "spread": labels["spread"],
                    "node": name,
                    "role": role,
                    "value": value,
                    "weighted_value": weighted,
                    "data_status": item.get("data_status"),
                    "freq": float(item["freq"]),
                    "weight": float(item["weight"]),
                    "coherence": coherence,
                    "coherence_status": status,
                    "dependency_expects_value": expected,
                    "dependency_match": match,
                }
            )
        by_case[case["case_id"]] = values

    zero_values = by_case["zeros"]
    null_status = coherence_status["null"]
    status_agreement = sum(1 for status in coherence_status.values() if status == null_status)
    random_ids = [f"random_{index:02d}" for index in range(RANDOM_CASES)]
    zero_distances = [_distance(by_case[case_id], zero_values) for case_id in random_ids]
    shuffle_distances = [
        _distance(by_case[case_id], by_case[f"{case_id}_shuffled_keys"]) for case_id in random_ids
    ]
    per_node = []
    for name in sorted(role_by_name):
        node_rows = [row for row in rows if row["node"] == name]
        per_node.append(
            {
                "node": name,
                "role": role_by_name[name],
                "required_inputs": list(ROLE_REQUIRED_INPUTS[role_by_name[name]]),
                "readings": sum(1 for row in node_rows if row["value"] is not None),
                "missing": sum(1 for row in node_rows if row["value"] is None),
                "cases": len(node_rows),
                "value_on_zeros": zero_values[name],
                "value_on_ones": by_case["ones"][name],
                "value_on_null": by_case["null"][name],
            }
        )
    always_missing = [item["node"] for item in per_node if item["readings"] == 0]

    summary = {
        "schema": "aureon.evidence.auris.v1",
        "live_trading": False,
        "external_llm": False,
        "source": "aureon.utils.aureon_queen_hive_mind.QueenHiveMind.get_auris_coherence",
        "node_source": "aureon.utils.aureon_queen_hive_mind.QueenHiveMind.read_auris_nodes",
        "reader": "QueenHiveMind.__new__, so the constructor's runtime wiring is not started",
        "ground_truth": (
            "Input guards transcribed from _auris_role_value and _auris_input. "
            "A role is expected to have a value only when every required field is present and finite. "
            "Memory and symbiosis have no required field. Numeric formulas are not reimplemented."
        ),
        "distance_rule": (
            "Mean absolute difference over nodes. A node missing on one side and present on the other counts as 1. "
            "Nodes missing on both sides are skipped."
        ),
        "key_permutation_new_from_source": KEY_PERMUTATION,
        "random_seed": RANDOM_SEED,
        "random_cases": RANDOM_CASES,
        "cases": len(by_case),
        "dependency_checks": checks,
        "dependency_mismatches": mismatches,
        "numeric_coherence_cases": numeric_coherence,
        "null_coherence_status": null_status,
        "coherence_status_matches_null": status_agreement,
        "coherence_status_cases": len(coherence_status),
        "nodes_without_any_reading": always_missing,
        "median_distance_from_zero_input": _median(zero_distances),
        "median_distance_from_key_shuffle": _median(shuffle_distances),
        "zero_input_distances": zero_distances,
        "key_shuffle_distances": shuffle_distances,
        "nodes": per_node,
        "orders_placed": False,
    }
    fieldnames = [
        "case_id",
        "kind",
        "twin",
        "volatility",
        "momentum",
        "volume",
        "spread",
        "node",
        "role",
        "value",
        "weighted_value",
        "data_status",
        "freq",
        "weight",
        "coherence",
        "coherence_status",
        "dependency_expects_value",
        "dependency_match",
    ]
    return {"summary": summary, "csv": csv_text(fieldnames, rows)}
