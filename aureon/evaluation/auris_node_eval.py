"""Run the nine Auris nodes on a fixed labelled draw and score them.

The label is a pre-registered threshold on the input the node's role names.
It is not a trade outcome. A node whose output does not change has no
evidence, and its verdict is HOLD. A coherence figure is not a licence to
trade: there is no independent outcome label for that claim.
"""

from __future__ import annotations

import random
from typing import Any

SEED = 20261024
ROWS = 256
DECISION_AT = 0.5

# Positive class for the documented input. The baseline uses its own threshold.
# These constants are the task. They are not fitted to a hit rate.
RULES: dict[str, dict[str, Any]] = {
    "Tiger": {
        "feature": "volatility",
        "positive_when": "le",
        "threshold": 0.35,
        "baseline_positive_when": "le",
        "baseline_threshold": 0.50,
    },
    "Falcon": {
        "feature": "abs_momentum",
        "positive_when": "ge",
        "threshold": 0.45,
        "baseline_positive_when": "ge",
        "baseline_threshold": 0.50,
    },
    "Hummingbird": {
        "feature": "volatility",
        "positive_when": "le",
        "threshold": 0.35,
        "baseline_positive_when": "le",
        "baseline_threshold": 0.50,
    },
    "Dolphin": {
        "feature": "momentum",
        "positive_when": "gt",
        "threshold": 0.0,
        "baseline_positive_when": "ge",
        "baseline_threshold": 0.0,
    },
    "Deer": {
        "feature": "spread",
        "positive_when": "ge",
        "threshold": 0.55,
        "baseline_positive_when": "ge",
        "baseline_threshold": 0.50,
    },
    "Panda": {
        "feature": "volatility",
        "positive_when": "le",
        "threshold": 0.50,
        "baseline_positive_when": "le",
        "baseline_threshold": 0.50,
    },
    "CargoShip": {
        "feature": "volume",
        "positive_when": "ge",
        "threshold": 0.55,
        "baseline_positive_when": "ge",
        "baseline_threshold": 0.50,
    },
}


def _compare(value: float, op: str, threshold: float) -> bool:
    if op == "le":
        return value <= threshold
    if op == "lt":
        return value < threshold
    if op == "ge":
        return value >= threshold
    if op == "gt":
        return value > threshold
    raise ValueError(op)


def _features(seed: int, rows: int) -> list[dict[str, float]]:
    rng = random.Random(seed)
    drawn: list[dict[str, float]] = []
    for _ in range(rows):
        momentum = rng.uniform(-1.0, 1.0)
        drawn.append(
            {
                "volatility": rng.random(),
                "momentum": momentum,
                "abs_momentum": abs(momentum),
                "volume": rng.random(),
                "spread": rng.random(),
            }
        )
    return drawn


def _rate(hits: int, total: int) -> float | None:
    if total <= 0:
        return None
    return hits / total


def _reader():
    from aureon.utils.aureon_queen_hive_mind import QueenHiveMind

    return QueenHiveMind.__new__(QueenHiveMind)


def evaluate_auris_nodes(seed: int = SEED, rows: int = ROWS) -> dict[str, Any]:
    """One deterministic run of ``read_auris_nodes`` on the labelled draw."""

    queen = _reader()
    table = _features(seed, rows)
    outputs: list[dict[str, Any]] = []
    by_node: dict[str, list[float]] = {}
    coherences: list[float] = []
    for features in table:
        market = {
            "volatility": features["volatility"],
            "momentum": features["momentum"],
            "volume": features["volume"],
            "spread": features["spread"],
        }
        reading = queen.read_auris_nodes(market)
        coherence, status = queen.get_auris_coherence(market)
        node_values = {name: float(item["value"]) for name, item in reading.items()}
        for name, value in node_values.items():
            by_node.setdefault(name, []).append(value)
        outputs.append(
            {
                "features": features,
                "nodes": node_values,
                "coherence": float(coherence),
                "coherence_status": status,
            }
        )
        coherences.append(float(coherence))

    nodes: dict[str, Any] = {}
    for name, values in by_node.items():
        low = min(values)
        high = max(values)
        mean = sum(values) / len(values)
        varying = (high - low) > 1e-12
        rule = RULES.get(name)
        record: dict[str, Any] = {
            "n": len(values),
            "min": low,
            "max": high,
            "mean": mean,
            "output_varies": varying,
            "decision_at": DECISION_AT,
            "decision_positive_rate": _rate(sum(value >= DECISION_AT for value in values), len(values)),
        }
        if not varying or rule is None:
            record["verdict"] = "HOLD"
            record["reason"] = (
                "output does not change with the labelled inputs"
                if not varying
                else "no pre-registered label for this node"
            )
            record["hit_rate"] = None
            record["baseline_hit_rate"] = None
            record["hits"] = None
            record["baseline_hits"] = None
        else:
            hits = 0
            baseline_hits = 0
            positive = 0
            for row, value in zip(outputs, values):
                feature = float(row["features"][rule["feature"]])
                label = _compare(feature, rule["positive_when"], float(rule["threshold"]))
                if label:
                    positive += 1
                if (value >= DECISION_AT) == label:
                    hits += 1
                baseline = _compare(feature, rule["baseline_positive_when"], float(rule["baseline_threshold"]))
                if baseline == label:
                    baseline_hits += 1
            record.update(
                {
                    "verdict": "measured",
                    "reason": "hit rate is agreement with the pre-registered feature threshold",
                    "label": {
                        "feature": rule["feature"],
                        "positive_when": rule["positive_when"],
                        "threshold": rule["threshold"],
                    },
                    "baseline": {
                        "feature": rule["feature"],
                        "positive_when": rule["baseline_positive_when"],
                        "threshold": rule["baseline_threshold"],
                        "name": "threshold on the same input feature",
                    },
                    "positive_labels": positive,
                    "hits": hits,
                    "baseline_hits": baseline_hits,
                    "hit_rate": _rate(hits, len(values)),
                    "baseline_hit_rate": _rate(baseline_hits, len(values)),
                }
            )
        nodes[name] = record

    return {
        "schema": "aureon.auris-node-eval.v1",
        "seed": seed,
        "rows": rows,
        "source": "aureon.utils.aureon_queen_hive_mind.QueenHiveMind.read_auris_nodes",
        "live_trading": False,
        "nodes": nodes,
        "trade_readiness": {
            "verdict": "HOLD",
            "reason": "no independent trade-outcome labels; coherence is not evidence of a fill",
            "coherence_min": min(coherences) if coherences else None,
            "coherence_max": max(coherences) if coherences else None,
            "coherence_mean": (sum(coherences) / len(coherences)) if coherences else None,
        },
        "samples": outputs,
    }


def render_auris_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Auris node evaluation",
        "",
        f"Seed `{report['seed']}`, {report['rows']} labelled rows. Source `{report['source']}`.",
        "A hit is the node value at or above 0.5 agreeing with a pre-registered threshold on the named input.",
        "That is not a trade result. Live trading is off.",
        "",
        "| node | verdict | hit rate | baseline hit rate | output min | output max |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for name, node in report["nodes"].items():
        hit = "HOLD" if node["hit_rate"] is None else f"{node['hit_rate']:.4f}"
        base = "HOLD" if node["baseline_hit_rate"] is None else f"{node['baseline_hit_rate']:.4f}"
        lines.append(
            f"| {name} | {node['verdict']} | {hit} | {base} | {node['min']:.4f} | {node['max']:.4f} |"
        )
    trade = report["trade_readiness"]
    lines.extend(
        [
            "",
            f"Trade readiness: **{trade['verdict']}**. {trade['reason']}",
            "",
        ]
    )
    return "\n".join(lines)
