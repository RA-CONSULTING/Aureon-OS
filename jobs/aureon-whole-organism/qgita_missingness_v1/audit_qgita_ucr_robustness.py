"""Post-confirmatory missing-data and phase-surrogate robustness audit."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import zipfile
from collections import defaultdict
from pathlib import Path

import numpy as np

import benchmark_ucr_confirmatory as canonical


PROTOCOL_FILE = "QGITA_V2_UCR_POSTCONFIRMATORY_ROBUSTNESS_PROTOCOL_v1.md"
PROTOCOL_SHA256 = "F259A59A0678DB0EAD8AC0F955113581F3DDDF4A1176141E3DC0C8263BADB9F0"
CANONICAL_RESULT_SHA256 = (
    "924411087C598C3F86632B6272CA3CAF3673CFF1F5AC277DB5888E0F93B27DDB"
)
ROOT_SEED = 20260728
MISSING_REPLICATES = 5
PHASE_REPLICATES = 39
BOOTSTRAP_REPLICATES = 10_000
NONINFERIORITY_MARGIN = -0.05
SPECTRAL_RELATIVE_TOLERANCE = 1e-8
SCENARIOS = ("mcar_05", "mcar_10", "burst_05")
LATTICE = canonical.FIBONACCI_LATTICE


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def deterministic_seed(dataset_id: str, scenario: str, replicate: int) -> int:
    token = f"{ROOT_SEED}|{dataset_id}|{scenario}|{replicate}".encode("utf-8")
    return int.from_bytes(hashlib.sha256(token).digest()[:8], "big")


def mcar_mask(
    length: int,
    test_start: int,
    fraction: float,
    rng: np.random.Generator,
) -> np.ndarray:
    if not 0.0 <= fraction <= 1.0:
        raise ValueError("missing fraction must be in [0,1]")
    test_length = length - test_start
    count = int(round(fraction * test_length))
    mask = np.zeros(length, dtype=bool)
    if count:
        selected = rng.choice(test_length, size=count, replace=False) + test_start
        mask[selected] = True
    return mask


def burst_mask(
    length: int,
    test_start: int,
    rng: np.random.Generator,
) -> np.ndarray:
    test_length = length - test_start
    block_length = int(math.ceil(0.01 * test_length))
    mask = np.zeros(length, dtype=bool)
    starts = rng.integers(test_start, length, size=5)
    for start in starts:
        mask[int(start) : min(length, int(start) + block_length)] = True
    return mask


def locf(values: np.ndarray, mask: np.ndarray) -> np.ndarray:
    if values.shape != mask.shape:
        raise ValueError("values and mask must have equal shape")
    if mask[0]:
        raise ValueError("the first value cannot be missing for LOCF")
    indices = np.arange(len(values), dtype=np.int64)
    indices[mask] = 0
    np.maximum.accumulate(indices, out=indices)
    return values[indices]


def curvature_components(
    values: np.ndarray, predecessor: int, centre: int, successor: int
) -> tuple[np.ndarray, np.ndarray]:
    count = len(values) - successor
    if count <= 0:
        raise ValueError("series is shorter than a required lattice successor")
    starts = np.arange(count, dtype=np.int64)
    h_minus = float(centre - predecessor)
    h_plus = float(successor - centre)
    curvature = (
        2.0
        / (h_minus + h_plus)
        * (
            (values[starts + successor] - values[starts + centre]) / h_plus
            - (values[starts + centre] - values[starts + predecessor])
            / h_minus
        )
    )
    return starts + successor, np.abs(curvature)


def training_scales(values: np.ndarray, train_end: int) -> np.ndarray:
    rows: list[np.ndarray] = []
    raw: list[np.ndarray] = []
    for k in range(1, len(LATTICE) - 1):
        decision, absolute = curvature_components(
            values,
            int(LATTICE[k - 1]),
            int(LATTICE[k]),
            int(LATTICE[k + 1]),
        )
        calibration = absolute[decision < train_end]
        if len(calibration) < canonical.MIN_CALIBRATION_OBSERVATIONS:
            raise ValueError("insufficient curvature calibration")
        rows.append(calibration)
        raw.append(absolute)
    floor = canonical.scale_floor(np.concatenate(rows))
    return np.asarray(
        [
            max(
                float(np.quantile(calibration, canonical.CURVATURE_QUANTILE)),
                floor,
            )
            for calibration in rows
        ],
        dtype=np.float64,
    )


def qgita_scores_with_scales(
    values: np.ndarray, train_end: int, scales: np.ndarray
) -> np.ndarray:
    if scales.shape != (len(LATTICE) - 2,):
        raise ValueError("one scale is required for each interior knot")
    test_scores = np.full(len(values) - train_end, -np.inf, dtype=np.float64)
    for offset, k in enumerate(range(1, len(LATTICE) - 1)):
        decision, absolute = curvature_components(
            values,
            int(LATTICE[k - 1]),
            int(LATTICE[k]),
            int(LATTICE[k + 1]),
        )
        keep = decision >= train_end
        target = decision[keep] - train_end
        np.maximum.at(test_scores, target, absolute[keep] / scales[offset])
    test_scores[test_scores == -np.inf] = np.nan
    return test_scores


def score_qgita(
    values: np.ndarray,
    train_end: int,
    anomaly_start: int,
    anomaly_end: int,
    scales: np.ndarray | None = None,
) -> tuple[dict, np.ndarray]:
    if scales is None:
        scales = training_scales(values, train_end)
    test_scores = qgita_scores_with_scales(values, train_end, scales)
    scores = np.full(len(values), np.nan, dtype=np.float64)
    scores[train_end:] = test_scores
    return (
        canonical.select_peak(
            scores, train_end, anomaly_start, anomaly_end
        ),
        scales,
    )


def phase_randomize(
    values: np.ndarray, rng: np.random.Generator
) -> tuple[np.ndarray, float]:
    spectrum = np.fft.rfft(values)
    magnitudes = np.abs(spectrum)
    randomized = np.empty_like(spectrum)
    randomized[0] = spectrum[0]
    stop = len(spectrum) - 1 if len(values) % 2 == 0 else len(spectrum)
    if stop > 1:
        phases = rng.uniform(0.0, 2.0 * np.pi, size=stop - 1)
        randomized[1:stop] = magnitudes[1:stop] * np.exp(1j * phases)
    if len(values) % 2 == 0:
        randomized[-1] = spectrum[-1]
    surrogate = np.fft.irfft(randomized, n=len(values))
    check = np.abs(np.fft.rfft(surrogate))
    denominator = np.maximum(
        magnitudes, np.finfo(float).eps * max(1.0, float(np.max(magnitudes)))
    )
    relative_error = float(np.max(np.abs(check - magnitudes) / denominator))
    if relative_error > SPECTRAL_RELATIVE_TOLERANCE:
        raise ValueError(
            f"phase surrogate spectral error {relative_error} exceeds tolerance"
        )
    return np.asarray(surrogate, dtype=np.float64), relative_error


def representative_ids(series: list[dict]) -> dict[str, str]:
    result: dict[str, str] = {}
    for record in series:
        key = record["family_key"]
        dataset_id = record["dataset_id"]
        if key not in result or int(dataset_id) < int(result[key]):
            result[key] = dataset_id
    return result


def percentile_interval(values: np.ndarray) -> list[float]:
    lower, upper = np.quantile(values, [0.025, 0.975])
    return [float(lower), float(upper)]


def missing_aggregate(series_ledger: list[dict]) -> dict:
    family_keys = sorted({item["family_key"] for item in series_ledger})
    family_index = {key: index for index, key in enumerate(family_keys)}
    clean_families: list[list[float]] = [[] for _ in family_keys]
    for record in series_ledger:
        clean_families[family_index[record["family_key"]]].append(
            float(record["clean"]["ucr_localisation"])
        )
    clean_means = np.asarray(
        [np.mean(values) for values in clean_families], dtype=float
    )
    output = {}
    rng = np.random.default_rng(np.random.SeedSequence([ROOT_SEED, 41]))
    bootstrap_indices = rng.integers(
        0,
        len(family_keys),
        size=(BOOTSTRAP_REPLICATES, len(family_keys)),
    )
    for scenario in SCENARIOS:
        replicate_series = []
        replicate_family = []
        stability = []
        changed = []
        missing_fractions = []
        family_values: list[list[float]] = [[] for _ in family_keys]
        for replicate in range(MISSING_REPLICATES):
            outcomes = [
                record["missing"][scenario][replicate]
                for record in series_ledger
            ]
            replicate_series.append(
                float(np.mean([row["ucr_localisation"] for row in outcomes]))
            )
            grouped: list[list[float]] = [[] for _ in family_keys]
            for record, row in zip(series_ledger, outcomes):
                index = family_index[record["family_key"]]
                value = float(row["ucr_localisation"])
                grouped[index].append(value)
                family_values[index].append(value)
                stability.append(float(row["peak_within_100_of_clean"]))
                changed.append(float(row["ucr_outcome_changed_from_clean"]))
                missing_fractions.append(float(row["realized_missing_fraction"]))
            replicate_family.append(
                float(np.mean([np.mean(values) for values in grouped]))
            )
        perturbed_means = np.asarray(
            [np.mean(values) for values in family_values], dtype=float
        )
        differences = perturbed_means - clean_means
        bootstrap = differences[bootstrap_indices].mean(axis=1)
        interval = percentile_interval(bootstrap)
        output[scenario] = {
            "replicate_series_macro_ucr_success": replicate_series,
            "replicate_family_macro_ucr_success": replicate_family,
            "mean_series_macro_ucr_success": float(np.mean(replicate_series)),
            "mean_family_macro_ucr_success": float(np.mean(replicate_family)),
            "replicate_series_macro_range": [
                float(np.min(replicate_series)),
                float(np.max(replicate_series)),
            ],
            "replicate_family_macro_range": [
                float(np.min(replicate_family)),
                float(np.max(replicate_family)),
            ],
            "mean_peak_within_100_stability": float(np.mean(stability)),
            "mean_ucr_outcome_change_fraction": float(np.mean(changed)),
            "mean_realized_missing_fraction": float(np.mean(missing_fractions)),
            "perturbed_minus_clean_family_macro_estimate": float(
                np.mean(differences)
            ),
            "cluster_bootstrap_95_interval": interval,
            "noninferiority_margin": NONINFERIORITY_MARGIN,
            "noninferior": bool(interval[0] > NONINFERIORITY_MARGIN),
        }
    return {
        "clean_family_macro_ucr_success": float(np.mean(clean_means)),
        "family_count": len(family_keys),
        "bootstrap_replicates": BOOTSTRAP_REPLICATES,
        "bootstrap_seed_sequence": [ROOT_SEED, 41],
        "scenarios": output,
    }


def surrogate_aggregate(surrogate_ledger: list[dict]) -> dict:
    if len(surrogate_ledger) != 46:
        raise ValueError("phase surrogate requires 46 representatives")
    clean_ucr = float(
        np.mean([row["clean"]["ucr_localisation"] for row in surrogate_ledger])
    )
    clean_strict = float(
        np.mean(
            [row["clean"]["strict_localisation"] for row in surrogate_ledger]
        )
    )
    ucr_replicates = []
    strict_replicates = []
    errors = []
    for replicate in range(PHASE_REPLICATES):
        outcomes = [row["surrogates"][replicate] for row in surrogate_ledger]
        ucr_replicates.append(
            float(np.mean([item["ucr_localisation"] for item in outcomes]))
        )
        strict_replicates.append(
            float(np.mean([item["strict_localisation"] for item in outcomes]))
        )
        errors.extend(item["spectral_relative_error"] for item in outcomes)
    ucr_exceed = int(np.count_nonzero(np.asarray(ucr_replicates) >= clean_ucr))
    strict_exceed = int(
        np.count_nonzero(np.asarray(strict_replicates) >= clean_strict)
    )
    return {
        "representative_count": len(surrogate_ledger),
        "replicates": PHASE_REPLICATES,
        "clean_ucr_success_fraction": clean_ucr,
        "clean_strict_success_fraction": clean_strict,
        "surrogate_ucr_success_fractions": ucr_replicates,
        "surrogate_strict_success_fractions": strict_replicates,
        "surrogate_ucr_mean": float(np.mean(ucr_replicates)),
        "surrogate_ucr_range": [
            float(np.min(ucr_replicates)),
            float(np.max(ucr_replicates)),
        ],
        "surrogate_strict_mean": float(np.mean(strict_replicates)),
        "surrogate_strict_range": [
            float(np.min(strict_replicates)),
            float(np.max(strict_replicates)),
        ],
        "ucr_one_sided_plus_one_p_value": float(
            (1 + ucr_exceed) / (PHASE_REPLICATES + 1)
        ),
        "strict_one_sided_plus_one_p_value": float(
            (1 + strict_exceed) / (PHASE_REPLICATES + 1)
        ),
        "surrogate_ucr_aggregates_at_least_clean": ucr_exceed,
        "surrogate_strict_aggregates_at_least_clean": strict_exceed,
        "maximum_spectral_relative_error": float(np.max(errors)),
        "spectral_relative_tolerance": SPECTRAL_RELATIVE_TOLERANCE,
    }


def build_result(canonical_result_path: Path) -> dict:
    actual_hash = sha256_file(canonical_result_path)
    if actual_hash != CANONICAL_RESULT_SHA256:
        raise ValueError(f"canonical result hash mismatch: {actual_hash}")
    canonical_result = json.loads(
        canonical_result_path.read_text(encoding="utf-8")
    )
    canonical_series = canonical_result["series"]
    if len(canonical_series) != 250:
        raise ValueError("expected 250 canonical UCR series")
    representatives = representative_ids(canonical_series)
    if len(representatives) != 46:
        raise ValueError("expected 46 frozen provenance families")
    representative_dataset_ids = set(representatives.values())

    reader = canonical.HTTPRangeReader(canonical.ARCHIVE_URL)
    series_ledger: list[dict] = []
    surrogate_ledger: list[dict] = []
    with zipfile.ZipFile(reader) as archive:
        for ordinal, record in enumerate(canonical_series, start=1):
            print(
                f"robustness series {ordinal}/250: {record['dataset_id']}",
                file=sys.stderr,
                flush=True,
            )
            payload = archive.read(record["member_path"])
            if sha256_bytes(payload) != record["uncompressed_sha256"]:
                raise ValueError(
                    f"member hash mismatch for {record['dataset_id']}"
                )
            text = payload.decode("ascii")
            values = np.fromstring(text, sep=" ", dtype=np.float64)
            if len(text.split()) != len(values) or not np.all(np.isfinite(values)):
                raise ValueError(f"invalid numeric payload {record['dataset_id']}")
            train_end = int(record["train_end_zero_based_exclusive"])
            anomaly_start = int(record["anomaly_start_zero_based"])
            anomaly_end = int(record["anomaly_end_zero_based"])
            clean, scales = score_qgita(
                values, train_end, anomaly_start, anomaly_end
            )
            canonical_clean = record["methods"][canonical.PRIMARY_METHOD]
            if (
                clean["selected_index_zero_based"]
                != canonical_clean["selected_index_zero_based"]
                or clean["ucr_localisation"]
                != canonical_clean["ucr_localisation"]
                or clean["strict_localisation"]
                != canonical_clean["strict_localisation"]
            ):
                raise ValueError(
                    f"clean peak mismatch for {record['dataset_id']}"
                )

            missing: dict[str, list[dict]] = {name: [] for name in SCENARIOS}
            for scenario in SCENARIOS:
                for replicate in range(MISSING_REPLICATES):
                    rng = np.random.default_rng(
                        deterministic_seed(
                            record["dataset_id"], scenario, replicate
                        )
                    )
                    if scenario == "mcar_05":
                        mask = mcar_mask(len(values), train_end, 0.05, rng)
                    elif scenario == "mcar_10":
                        mask = mcar_mask(len(values), train_end, 0.10, rng)
                    else:
                        mask = burst_mask(len(values), train_end, rng)
                    corrupted = locf(values, mask)
                    outcome, _ = score_qgita(
                        corrupted,
                        train_end,
                        anomaly_start,
                        anomaly_end,
                        scales,
                    )
                    missing_count = int(np.count_nonzero(mask))
                    missing[scenario].append(
                        {
                            **outcome,
                            "replicate": replicate,
                            "seed": deterministic_seed(
                                record["dataset_id"], scenario, replicate
                            ),
                            "realized_missing_count": missing_count,
                            "realized_missing_fraction": (
                                missing_count / int(record["test_length"])
                            ),
                            "ucr_outcome_changed_from_clean": bool(
                                outcome["ucr_localisation"]
                                != clean["ucr_localisation"]
                            ),
                            "peak_within_100_of_clean": bool(
                                abs(
                                    outcome["selected_index_zero_based"]
                                    - clean["selected_index_zero_based"]
                                )
                                <= 100
                            ),
                        }
                    )

            series_ledger.append(
                {
                    "dataset_id": record["dataset_id"],
                    "family_key": record["family_key"],
                    "member_path": record["member_path"],
                    "member_sha256": record["uncompressed_sha256"],
                    "test_length": record["test_length"],
                    "clean": clean,
                    "missing": missing,
                }
            )

            if record["dataset_id"] in representative_dataset_ids:
                surrogates = []
                for replicate in range(PHASE_REPLICATES):
                    print(
                        f"phase surrogate {record['dataset_id']} "
                        f"{replicate + 1}/{PHASE_REPLICATES}",
                        file=sys.stderr,
                        flush=True,
                    )
                    seed = deterministic_seed(
                        record["dataset_id"], "phase_randomized", replicate
                    )
                    surrogate, spectral_error = phase_randomize(
                        values, np.random.default_rng(seed)
                    )
                    outcome, _ = score_qgita(
                        surrogate, train_end, anomaly_start, anomaly_end
                    )
                    surrogates.append(
                        {
                            **outcome,
                            "replicate": replicate,
                            "seed": seed,
                            "spectral_relative_error": spectral_error,
                        }
                    )
                surrogate_ledger.append(
                    {
                        "dataset_id": record["dataset_id"],
                        "family_key": record["family_key"],
                        "clean": clean,
                        "surrogates": surrogates,
                    }
                )

    missing_summary = missing_aggregate(series_ledger)
    surrogate_summary = surrogate_aggregate(surrogate_ledger)
    return {
        "identity": {
            "protocol_file": PROTOCOL_FILE,
            "protocol_sha256": PROTOCOL_SHA256,
            "evidence_class": "post-confirmatory robustness audit",
            "canonical_result_file": canonical_result_path.name,
            "canonical_result_sha256": actual_hash,
            "archive_url": canonical.ARCHIVE_URL,
            "archive_content_length": reader.length,
            "archive_etag": reader.etag,
            "archive_last_modified": reader.last_modified,
        },
        "design": {
            "root_seed": ROOT_SEED,
            "missing_replicates": MISSING_REPLICATES,
            "phase_replicates": PHASE_REPLICATES,
            "scenarios": list(SCENARIOS),
            "missing_scope": "test region only",
            "imputation": "last observation carried forward",
            "phase_surrogate": (
                "Fourier magnitudes preserved; randomized positive-frequency "
                "phases; exact amplitude distribution not preserved"
            ),
            "noninferiority_margin": NONINFERIORITY_MARGIN,
        },
        "evaluation": {
            "series_count": len(series_ledger),
            "family_count": len(representatives),
            "representative_count": len(surrogate_ledger),
            "clean_peak_identity": "PASS",
            "member_hash_identity": "PASS",
        },
        "missing_data": missing_summary,
        "phase_randomized_surrogate": surrogate_summary,
        "series": series_ledger,
        "phase_representatives": surrogate_ledger,
        "interpretation_boundary": (
            "post-confirmatory robustness evidence only; not a new held-out "
            "benchmark, IAAFT, independent replication, physical validation, "
            "peer review, or publication"
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--canonical-result", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f"refusing to overwrite {args.output}")
    result = build_result(args.canonical_result)
    payload = (
        json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n"
    ).encode("utf-8")
    with args.output.open("xb") as handle:
        handle.write(payload)
    sys.stdout.buffer.write(payload)


if __name__ == "__main__":
    main()
