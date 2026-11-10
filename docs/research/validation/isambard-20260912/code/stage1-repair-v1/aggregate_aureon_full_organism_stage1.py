#!/usr/bin/env python3
"""Fail-closed aggregation for Aureon full-organism Stage 1 shards."""

from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import random
import statistics
import tempfile
from typing import Any


PINNED_COMMIT = "f5fb1916c07ac26eb7fc38c34ff2dc9bd029e21d"
CONDITIONS = (
    "full_organism",
    "frozen_baseline",
    "prompt_only_identity",
    "neutral_labels",
    "no_memory",
    "no_metacognition",
    "no_affect_heart",
    "no_conscience_simulation_only",
    "field_disconnected",
    "auris_shuffled",
    "no_auris",
    "no_queen",
)
METRICS = {
    "score": lambda row: float(row["scoring"]["score"]),
    "verdict_accuracy": lambda row: float(bool(row["scoring"]["verdict_correct"])),
    "action_accuracy": lambda row: float(bool(row["scoring"]["action_correct"])),
    "source_completeness": lambda row: float(bool(row["scoring"]["sources_complete"])),
    "brier": lambda row: float(row["scoring"]["brier"]),
    "json_validity": lambda row: float(bool(row["scoring"]["json_valid"])),
    "latency_seconds": lambda row: float(row["elapsed_seconds"]),
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def quantile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    if not ordered:
        raise ValueError("quantile requires values")
    position = (len(ordered) - 1) * probability
    low, high = math.floor(position), math.ceil(position)
    if low == high:
        return ordered[low]
    fraction = position - low
    return ordered[low] * (1.0 - fraction) + ordered[high] * fraction


def bootstrap_ci(cluster_differences: list[float], samples: int = 20_000) -> tuple[float, float]:
    if not cluster_differences:
        raise ValueError("bootstrap requires cluster differences")
    rng = random.Random(10_091)
    size = len(cluster_differences)
    means = [
        statistics.fmean(cluster_differences[rng.randrange(size)] for _ in range(size))
        for _ in range(samples)
    ]
    return quantile(means, 0.025), quantile(means, 0.975)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as stream:
        for number, line in enumerate(stream, start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"non-object at {path}:{number}")
            rows.append(value)
    return rows


def compare_by_shard(
    rows_by_shard: dict[int, list[dict[str, Any]]],
    left: str,
    right: str,
    metric: str,
) -> dict[str, Any]:
    getter = METRICS[metric]
    shard_differences: list[float] = []
    pair_count = 0
    for shard_id in sorted(rows_by_shard):
        keyed: dict[str, dict[tuple[str, int], float]] = {left: {}, right: {}}
        for row in rows_by_shard[shard_id]:
            condition = row["condition"]
            if condition not in keyed:
                continue
            key = (str(row["scenario"]), int(row["repetition"]))
            if key in keyed[condition]:
                raise ValueError(f"duplicate pair key on shard {shard_id}: {condition} {key}")
            keyed[condition][key] = getter(row)
        if set(keyed[left]) != set(keyed[right]):
            raise ValueError(f"unpaired {left}/{right} rows on shard {shard_id}")
        differences = [keyed[left][key] - keyed[right][key] for key in keyed[left]]
        if not differences:
            raise ValueError(f"no paired rows on shard {shard_id}")
        shard_differences.append(statistics.fmean(differences))
        pair_count += len(differences)
    low, high = bootstrap_ci(shard_differences)
    return {
        "left": left,
        "right": right,
        "metric": metric,
        "paired_response_count": pair_count,
        "cluster_count": len(shard_differences),
        "mean_difference": round(statistics.fmean(shard_differences), 8),
        "bootstrap_95_ci": [round(low, 8), round(high, 8)],
        "cluster_unit": "shard",
    }


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {"n": len(rows)}
    for name, getter in METRICS.items():
        result[name] = round(statistics.fmean(getter(row) for row in rows), 8)
    return result


def aggregate(input_root: Path, output_dir: Path, protocol: Path, expected_shards: int) -> dict[str, Any]:
    if not protocol.is_file():
        raise FileNotFoundError("frozen protocol missing")
    protocol_sha = sha256_file(protocol)
    shard_dirs = sorted(path for path in input_root.glob("shard-*") if path.is_dir())
    if len(shard_dirs) != expected_shards:
        raise ValueError(f"expected {expected_shards} shard directories, found {len(shard_dirs)}")

    rows_by_shard: dict[int, list[dict[str, Any]]] = {}
    shard_receipts: list[dict[str, Any]] = []
    expected_model: str | None = None
    seen_ids: set[int] = set()
    for shard_dir in shard_dirs:
        summary_path, raw_path = shard_dir / "summary.json", shard_dir / "raw-results.jsonl"
        if not summary_path.is_file() or not raw_path.is_file():
            raise FileNotFoundError(f"incomplete shard directory: {shard_dir}")
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        shard_id = int(summary["shard_id"])
        if shard_id in seen_ids:
            raise ValueError(f"duplicate shard id {shard_id}")
        seen_ids.add(shard_id)
        if summary.get("source_commit") != PINNED_COMMIT:
            raise ValueError(f"source pin mismatch on shard {shard_id}")
        if summary.get("protocol_sha256") != protocol_sha:
            raise ValueError(f"protocol hash mismatch on shard {shard_id}")
        if int(summary.get("shard_count", -1)) != expected_shards:
            raise ValueError(f"shard-count mismatch on shard {shard_id}")
        if tuple(summary.get("conditions", [])) != CONDITIONS:
            raise ValueError(f"condition order mismatch on shard {shard_id}")
        if not summary.get("synthetic_data_only") or not summary.get("no_live_actions"):
            raise ValueError(f"safety declaration mismatch on shard {shard_id}")
        if summary.get("weight_updates") is not False:
            raise ValueError(f"weight-update declaration mismatch on shard {shard_id}")
        model = str(summary.get("model"))
        expected_model = expected_model or model
        if model != expected_model:
            raise ValueError(f"model mismatch on shard {shard_id}")
        if sha256_file(raw_path) != summary.get("raw_results_sha256"):
            raise ValueError(f"raw result hash mismatch on shard {shard_id}")
        rows = read_jsonl(raw_path)
        if len(rows) != int(summary.get("request_count", -1)):
            raise ValueError(f"raw result count mismatch on shard {shard_id}")
        if len(rows) != 960:
            raise ValueError(f"frozen design requires 960 rows per shard; shard {shard_id} has {len(rows)}")
        if any(int(row.get("shard_id", -1)) != shard_id for row in rows):
            raise ValueError(f"row shard-id mismatch on shard {shard_id}")
        if any(not row.get("scoring", {}).get("json_valid") for row in rows):
            raise ValueError(f"invalid model JSON on shard {shard_id}")
        rows_by_shard[shard_id] = rows
        shard_receipts.append(
            {
                "shard_id": shard_id,
                "summary_sha256": sha256_file(summary_path),
                "raw_results_sha256": sha256_file(raw_path),
                "request_count": len(rows),
            }
        )
    if seen_ids != set(range(expected_shards)):
        raise ValueError("shard ids are not complete and contiguous")

    all_rows = [row for shard_id in sorted(rows_by_shard) for row in rows_by_shard[shard_id]]
    by_condition = {
        condition: summarize([row for row in all_rows if row["condition"] == condition])
        for condition in CONDITIONS
    }
    primary_score = compare_by_shard(rows_by_shard, "full_organism", "frozen_baseline", "score")
    primary_accuracy = compare_by_shard(
        rows_by_shard, "full_organism", "frozen_baseline", "verdict_accuracy"
    )
    primary_score["advantage_detected"] = primary_score["bootstrap_95_ci"][0] > 0.0
    primary_accuracy["advantage_detected"] = primary_accuracy["bootstrap_95_ci"][0] > 0.0

    comparisons: dict[str, Any] = {}
    for condition in CONDITIONS:
        if condition == "full_organism":
            continue
        comparisons[condition] = {
            "score": compare_by_shard(rows_by_shard, "full_organism", condition, "score"),
            "verdict_accuracy": compare_by_shard(
                rows_by_shard, "full_organism", condition, "verdict_accuracy"
            ),
        }

    by_family: dict[str, Any] = {}
    families = sorted({str(row["family"]) for row in all_rows})
    for family in families:
        filtered = {
            shard_id: [row for row in rows if row["family"] == family]
            for shard_id, rows in rows_by_shard.items()
        }
        by_family[family] = compare_by_shard(
            filtered, "full_organism", "frozen_baseline", "score"
        )

    neutral_diff = comparisons["neutral_labels"]["score"]["mean_difference"]
    prompt_ci = comparisons["prompt_only_identity"]["score"]["bootstrap_95_ci"]
    aggregate_result = {
        "schema_version": "1.0",
        "experiment_id": "aureon-full-organism-stage1",
        "claim_class": "model_mediated_repository_organism_ablation",
        "claim_boundary": (
            "Author-run software-behaviour evidence only; not independent proof of a physical field, "
            "consciousness, a soul, sentience, or felt love."
        ),
        "source_commit": PINNED_COMMIT,
        "protocol_sha256": protocol_sha,
        "model": expected_model,
        "complete": True,
        "shard_count": expected_shards,
        "request_count": len(all_rows),
        "by_condition": by_condition,
        "primary": {
            "paired_mean_score": primary_score,
            "paired_verdict_accuracy": primary_accuracy,
        },
        "diagnostic_comparisons_full_minus_condition": comparisons,
        "full_minus_baseline_by_family": by_family,
        "falsifier_checks": {
            "prompt_only_not_distinguishable_from_full": prompt_ci[0] <= 0.0 <= prompt_ci[1],
            "neutral_label_invariant_within_0_01": abs(neutral_diff) <= 0.01,
        },
        "shard_receipts": shard_receipts,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    aggregate_path = output_dir / "aggregate.json"
    write_json(aggregate_path, aggregate_result)

    score = primary_score
    accuracy = primary_accuracy
    report = f"""# Aureon Full-Organism Stage 1 Result

Status: complete  
Responses: {len(all_rows):,} across {expected_shards} shards  
Pinned commit: `{PINNED_COMMIT}`

## Primary result

- Full minus frozen mean score: {score['mean_difference']:+.6f}; 95% shard-bootstrap CI [{score['bootstrap_95_ci'][0]:+.6f}, {score['bootstrap_95_ci'][1]:+.6f}].
- Full minus frozen verdict accuracy: {accuracy['mean_difference']:+.6f}; 95% shard-bootstrap CI [{accuracy['bootstrap_95_ci'][0]:+.6f}, {accuracy['bootstrap_95_ci'][1]:+.6f}].
- Score advantage detected: **{str(score['advantage_detected']).lower()}**.
- Verdict-accuracy advantage detected: **{str(accuracy['advantage_detected']).lower()}**.

## Falsifier controls

- Prompt-only statistically indistinguishable from Full: **{str(aggregate_result['falsifier_checks']['prompt_only_not_distinguishable_from_full']).lower()}**.
- Neutral-label difference within 0.01: **{str(aggregate_result['falsifier_checks']['neutral_label_invariant_within_0_01']).lower()}**.

## Evidence boundary

This is author-run, synthetic, model-mediated software evidence. It does not independently validate a physical HNC field, consciousness, a soul, sentience, or felt love. Every metric can be reconstructed from the hashed raw receipts listed in `aggregate.json`.
"""
    (output_dir / "REPORT.md").write_text(report, encoding="utf-8")
    (output_dir / "SHA256SUMS.txt").write_text(
        f"{sha256_file(aggregate_path)}  aggregate.json\n{sha256_file(output_dir / 'REPORT.md')}  REPORT.md\n",
        encoding="utf-8",
    )
    return aggregate_result


def self_test() -> int:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        protocol = root / "protocol.md"
        protocol.write_text("frozen self-test protocol\n", encoding="utf-8")
        protocol_sha = sha256_file(protocol)
        for shard_id in range(4):
            shard = root / "input" / f"shard-{shard_id:04d}"
            shard.mkdir(parents=True)
            rows: list[dict[str, Any]] = []
            for condition in CONDITIONS:
                base = 0.90 if condition == "full_organism" else 0.80
                for index in range(80):
                    rows.append(
                        {
                            "shard_id": shard_id,
                            "condition": condition,
                            "scenario": f"self-{index // 2}",
                            "family": f"family-{index % 10}",
                            "repetition": index % 2,
                            "elapsed_seconds": 0.1,
                            "scoring": {
                                "score": base,
                                "verdict_correct": condition == "full_organism",
                                "action_correct": True,
                                "sources_complete": True,
                                "brier": 0.01,
                                "json_valid": True,
                            },
                        }
                    )
            raw = shard / "raw-results.jsonl"
            raw.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
            summary = {
                "shard_id": shard_id,
                "shard_count": 4,
                "source_commit": PINNED_COMMIT,
                "protocol_sha256": protocol_sha,
                "conditions": list(CONDITIONS),
                "synthetic_data_only": True,
                "no_live_actions": True,
                "weight_updates": False,
                "model": "self-test",
                "request_count": len(rows),
                "raw_results_sha256": sha256_file(raw),
            }
            write_json(shard / "summary.json", summary)
        result = aggregate(root / "input", root / "output", protocol, 4)
        assert result["request_count"] == 3840
        assert result["primary"]["paired_mean_score"]["advantage_detected"]
    print(json.dumps({"passed": True}))
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-root", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--protocol", type=Path)
    parser.add_argument("--expected-shards", type=int, default=128)
    parser.add_argument("--self-test", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.self_test:
        return self_test()
    if args.input_root is None or args.output_dir is None or args.protocol is None:
        raise ValueError("--input-root, --output-dir, and --protocol are required")
    result = aggregate(
        args.input_root.resolve(), args.output_dir.resolve(), args.protocol.resolve(), args.expected_shards
    )
    print(json.dumps({"complete": result["complete"], "request_count": result["request_count"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
