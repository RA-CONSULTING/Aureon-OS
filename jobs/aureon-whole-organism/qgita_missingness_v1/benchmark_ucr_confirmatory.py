"""Prospectively frozen UCR second-corpus benchmark for QGITA v2.

Implements QGITA_V2_UCR_CONFIRMATORY_PROTOCOL_v1.md.  The UCR archive is read
through HTTP byte ranges and is never retained or extracted on local disk.
Labels encoded in member filenames are parsed only after every member has been
selected by the frozen inclusion rule.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import re
import sys
import urllib.request
import zipfile
from collections import OrderedDict, defaultdict
from pathlib import Path
from typing import Iterable

import numpy as np


PROTOCOL_FILE = "QGITA_V2_UCR_CONFIRMATORY_PROTOCOL_v1.md"
PROTOCOL_SHA256 = "576395DB0DC651E291894312FC724A4469AD84507316D5F5340A11F4F4EA6E1B"
PROTOCOL_AMENDMENT_FILE = "QGITA_V2_UCR_CONFIRMATORY_PROTOCOL_AMENDMENT_v2.md"
PROTOCOL_AMENDMENT_SHA256 = (
    "5E823835D5A9DAA6CD33AB818EEAA7C67E99EBD53A38A31668CA019700BC32C6"
)
ARCHIVE_URL = (
    "https://www.cs.ucr.edu/~eamonn/time_series_data_2018/"
    "UCR_TimeSeriesAnomalyDatasets2021.zip"
)
EXPECTED_RAW_MEMBER_COUNT = 251
EXPECTED_UNIQUE_MEMBER_COUNT = 250
EXPECTED_DUPLICATE_BASENAME = (
    "170_UCR_Anomaly_gaitHunt1_18500_33070_33180.txt"
)
SEED = 20260728
BOOTSTRAP_REPLICATES = 10_000
SIGN_FLIP_REPLICATES = 99_999
SURROGATE_REPLICATES = 999
CURVATURE_QUANTILE = 0.99
MIN_CALIBRATION_OBSERVATIONS = 100
FLOOR_MULTIPLIER = 1e-12
EWMA_ALPHA = 2.0 / (377.0 + 1.0)
FIBONACCI_LATTICE = np.asarray(
    [0, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377],
    dtype=np.int64,
)
EQUAL_STEP_LATTICE = np.asarray(
    [0, 29, 58, 87, 116, 145, 174, 203, 232, 261, 290, 319, 348, 377],
    dtype=np.int64,
)
METHODS = (
    "qgita_fibonacci_scale_normalized",
    "equal_step_scale_normalized",
    "absolute_first_difference",
    "robust_level_deviation",
    "causal_ewma_residual",
)
PRIMARY_METHOD = METHODS[0]
COMPARATORS = METHODS[1:]
MEMBER_PATTERN = re.compile(
    r"^(?P<dataset_id>\d{3})_UCR_Anomaly_(?P<name>.+)_"
    r"(?P<train_end>\d+)_(?P<anomaly_start>\d+)_(?P<anomaly_end>\d+)\.txt$",
    re.IGNORECASE,
)


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def scale_floor(values: np.ndarray) -> float:
    finite = np.asarray(values, dtype=np.float64)
    if finite.size == 0 or not np.all(np.isfinite(finite)):
        raise ValueError("scale-floor input must be non-empty and finite")
    return FLOOR_MULTIPLIER * max(1.0, float(np.median(np.abs(finite))))


def parse_member_basename(name: str) -> dict:
    match = MEMBER_PATTERN.fullmatch(Path(name).name)
    if match is None:
        raise ValueError("member basename does not match the frozen UCR rule")
    parsed = match.groupdict()
    return {
        "dataset_id": parsed["dataset_id"],
        "name": parsed["name"],
        "train_end_1based": int(parsed["train_end"]),
        "anomaly_start_1based": int(parsed["anomaly_start"]),
        "anomaly_end_1based": int(parsed["anomaly_end"]),
    }


def boundary_conversion(parsed: dict, row_count: int) -> tuple[int, int, int]:
    train_end = int(parsed["train_end_1based"])
    anomaly_start = int(parsed["anomaly_start_1based"]) - 1
    anomaly_end = int(parsed["anomaly_end_1based"]) - 1
    if not 0 < train_end < anomaly_start + 1 <= anomaly_end + 1 <= row_count:
        raise ValueError(
            "encoded boundaries violate "
            "0 < TRAINEND < ANOMALYSTART <= ANOMALYEND <= n"
        )
    return train_end, anomaly_start, anomaly_end


def family_key(name: str) -> str:
    normalized = name.casefold()
    prefix = re.match(r"^(distorted|noise)(\d*)", normalized)
    if prefix is not None:
        normalized = normalized[prefix.end() :]
    normalized = re.sub(r"\d+$", "", normalized)
    normalized = re.sub(r"[^a-z0-9]+", "_", normalized).strip("_")
    return normalized or "empty_family"


class HTTPRangeReader(io.RawIOBase):
    """Small seekable HTTP range reader suitable for Python's zipfile."""

    def __init__(
        self,
        url: str,
        *,
        chunk_size: int = 4 * 1024 * 1024,
        cache_chunks: int = 12,
    ) -> None:
        self.url = url
        self.chunk_size = int(chunk_size)
        self.cache_chunks = int(cache_chunks)
        request = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(request, timeout=60) as response:
            headers = response.headers
            self.length = int(headers["Content-Length"])
            self.etag = headers.get("ETag")
            self.last_modified = headers.get("Last-Modified")
            self.accept_ranges = headers.get("Accept-Ranges")
        if self.length <= 0:
            raise OSError("source returned no positive Content-Length")
        if (self.accept_ranges or "").casefold() != "bytes":
            raise OSError("source does not declare HTTP byte-range support")
        self.position = 0
        self.cache: OrderedDict[int, bytes] = OrderedDict()

    def readable(self) -> bool:
        return True

    def seekable(self) -> bool:
        return True

    def tell(self) -> int:
        return self.position

    def seek(self, offset: int, whence: int = io.SEEK_SET) -> int:
        if whence == io.SEEK_SET:
            position = offset
        elif whence == io.SEEK_CUR:
            position = self.position + offset
        elif whence == io.SEEK_END:
            position = self.length + offset
        else:
            raise ValueError("unsupported seek mode")
        if position < 0:
            raise ValueError("negative seek position")
        self.position = min(int(position), self.length)
        return self.position

    def _chunk(self, chunk_index: int) -> bytes:
        if chunk_index in self.cache:
            payload = self.cache.pop(chunk_index)
            self.cache[chunk_index] = payload
            return payload
        start = chunk_index * self.chunk_size
        end = min(start + self.chunk_size, self.length) - 1
        request = urllib.request.Request(
            self.url,
            headers={
                "Range": f"bytes={start}-{end}",
                "User-Agent": "QGITA-UCR-reproducibility-audit/1.0",
            },
        )
        with urllib.request.urlopen(request, timeout=120) as response:
            if response.status != 206:
                raise OSError(f"range request returned HTTP {response.status}")
            payload = response.read()
            content_range = response.headers.get("Content-Range", "")
        expected = end - start + 1
        if len(payload) != expected:
            raise OSError(
                f"range returned {len(payload)} bytes; expected {expected}"
            )
        if not content_range.startswith(f"bytes {start}-{end}/"):
            raise OSError(f"unexpected Content-Range: {content_range!r}")
        self.cache[chunk_index] = payload
        while len(self.cache) > self.cache_chunks:
            self.cache.popitem(last=False)
        return payload

    def read(self, size: int = -1) -> bytes:
        if self.position >= self.length:
            return b""
        if size is None or size < 0:
            size = self.length - self.position
        size = min(int(size), self.length - self.position)
        pieces: list[bytes] = []
        remaining = size
        while remaining:
            chunk_index = self.position // self.chunk_size
            within = self.position % self.chunk_size
            payload = self._chunk(chunk_index)
            take = min(remaining, len(payload) - within)
            if take <= 0:
                raise OSError("HTTP range cache made no forward progress")
            pieces.append(payload[within : within + take])
            self.position += take
            remaining -= take
        return b"".join(pieces)


def hash_remote_archive(url: str, expected_length: int) -> str:
    digest = hashlib.sha256()
    count = 0
    request = urllib.request.Request(
        url, headers={"User-Agent": "QGITA-UCR-reproducibility-audit/1.0"}
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
            count += len(chunk)
            if count % (32 * 1024 * 1024) < len(chunk):
                print(
                    f"archive hash progress: {count}/{expected_length} bytes",
                    file=sys.stderr,
                    flush=True,
                )
    if count != expected_length:
        raise OSError(f"archive GET returned {count}; expected {expected_length}")
    return digest.hexdigest().upper()


def curvature_bank(
    values: np.ndarray, train_end: int, lattice: np.ndarray
) -> tuple[np.ndarray, list[dict]]:
    if lattice.shape != (14,) or np.any(np.diff(lattice) <= 0):
        raise ValueError("lattice must contain 14 strictly increasing positions")
    n = len(values)
    timeline = np.full(n, -np.inf, dtype=np.float64)
    raw: list[tuple[int, int, np.ndarray, np.ndarray]] = []
    training_values: list[np.ndarray] = []
    for k in range(1, len(lattice) - 1):
        predecessor = int(lattice[k - 1])
        centre = int(lattice[k])
        successor = int(lattice[k + 1])
        count = n - successor
        if count <= 0:
            raise ValueError("series is shorter than a required lattice successor")
        starts = np.arange(count, dtype=np.int64)
        h_minus = float(centre - predecessor)
        h_plus = float(successor - centre)
        with np.errstate(over="raise", invalid="raise", divide="raise"):
            curvature = (
                2.0
                / (h_minus + h_plus)
                * (
                    (values[starts + successor] - values[starts + centre]) / h_plus
                    - (values[starts + centre] - values[starts + predecessor])
                    / h_minus
                )
            )
        decision = starts + successor
        train_mask = decision < train_end
        calibration = np.abs(curvature[train_mask])
        if len(calibration) < MIN_CALIBRATION_OBSERVATIONS:
            raise ValueError(
                f"interior index {k} has only {len(calibration)} "
                "calibration observations"
            )
        if not np.all(np.isfinite(calibration)):
            raise ValueError("non-finite calibration curvature")
        training_values.append(calibration)
        raw.append((k, successor, decision, np.abs(curvature)))

    pooled_training = np.concatenate(training_values)
    floor = scale_floor(pooled_training)
    diagnostics: list[dict] = []
    for k, successor, decision, absolute_curvature in raw:
        calibration = absolute_curvature[decision < train_end]
        q99 = float(np.quantile(calibration, CURVATURE_QUANTILE))
        denominator = max(q99, floor)
        normalized = absolute_curvature / denominator
        if not np.all(np.isfinite(normalized)):
            raise ValueError("non-finite normalized curvature")
        np.maximum.at(timeline, decision, normalized)
        diagnostics.append(
            {
                "interior_index": k,
                "successor_position": successor,
                "calibration_count": int(len(calibration)),
                "calibration_abs_curvature_q99": q99,
                "normalization_denominator": denominator,
            }
        )
    timeline[timeline == -np.inf] = np.nan
    return timeline, diagnostics


def first_difference_scores(
    values: np.ndarray, train_end: int
) -> tuple[np.ndarray, dict]:
    differences = np.abs(np.diff(values))
    decisions = np.arange(1, len(values), dtype=np.int64)
    calibration = differences[decisions < train_end]
    if len(calibration) < MIN_CALIBRATION_OBSERVATIONS:
        raise ValueError("insufficient first-difference calibration")
    q99 = float(np.quantile(calibration, CURVATURE_QUANTILE))
    denominator = max(q99, scale_floor(calibration))
    scores = np.full(len(values), np.nan, dtype=np.float64)
    scores[1:] = differences / denominator
    return scores, {
        "calibration_count": int(len(calibration)),
        "calibration_abs_difference_q99": q99,
        "normalization_denominator": denominator,
    }


def robust_level_scores(
    values: np.ndarray, train_end: int
) -> tuple[np.ndarray, dict]:
    training = values[:train_end]
    if len(training) < MIN_CALIBRATION_OBSERVATIONS:
        raise ValueError("insufficient robust-level calibration")
    median = float(np.median(training))
    mad = float(np.median(np.abs(training - median)))
    denominator = max(
        1.4826 * mad,
        FLOOR_MULTIPLIER * max(1.0, float(np.median(np.abs(training)))),
    )
    scores = np.abs(values - median) / denominator
    if not np.all(np.isfinite(scores)):
        raise ValueError("non-finite robust-level score")
    return scores, {
        "calibration_count": int(len(training)),
        "training_median": median,
        "training_mad": mad,
        "normalization_denominator": denominator,
    }


def ewma_scores(values: np.ndarray, train_end: int) -> tuple[np.ndarray, dict]:
    if train_end < MIN_CALIBRATION_OBSERVATIONS:
        raise ValueError("insufficient EWMA calibration")
    training = values[:train_end]
    floor = FLOOR_MULTIPLIER * max(
        1.0, float(np.median(np.abs(training)))
    )
    floor_squared = floor * floor
    scores = np.full(len(values), np.nan, dtype=np.float64)
    mean = float(values[0])
    variance = 0.0
    for index in range(1, len(values)):
        residual = float(values[index]) - mean
        scores[index] = abs(residual) / math.sqrt(variance + floor_squared)
        variance = (1.0 - EWMA_ALPHA) * variance + EWMA_ALPHA * residual * residual
        mean = (1.0 - EWMA_ALPHA) * mean + EWMA_ALPHA * float(values[index])
    if not np.all(np.isfinite(scores[1:])):
        raise ValueError("non-finite EWMA score")
    return scores, {
        "alpha": EWMA_ALPHA,
        "initial_mean": float(values[0]),
        "initial_variance": 0.0,
        "scale_floor": floor,
        "variance_update": (
            "v_t=(1-alpha)*v_(t-1)+alpha*(x_t-mu_(t-1))^2"
        ),
    }


def select_peak(
    scores: np.ndarray,
    train_end: int,
    anomaly_start: int,
    anomaly_end: int,
) -> dict:
    test = np.asarray(scores[train_end:], dtype=np.float64)
    if len(test) <= 1:
        raise ValueError("test region must contain at least two samples")
    finite = np.isfinite(test)
    if not np.any(finite):
        raise ValueError("method has no finite test score")
    maximum = float(np.nanmax(test))
    maxima = np.flatnonzero(test == maximum)
    selected = train_end + int(maxima[0])
    anomaly_length = anomaly_end - anomaly_start + 1
    margin = max(anomaly_length, 100)
    tolerance_start = max(train_end, anomaly_start - margin)
    tolerance_end = min(len(scores) - 1, anomaly_end + margin)
    if selected < anomaly_start:
        signed_distance = selected - anomaly_start
    elif selected > anomaly_end:
        signed_distance = selected - anomaly_end
    else:
        signed_distance = 0
    return {
        "selected_index_zero_based": selected,
        "selected_index_one_based": selected + 1,
        "selected_score": maximum,
        "maximum_tie_count": int(len(maxima)),
        "maximum_tie": bool(len(maxima) > 1),
        "strict_localisation": bool(anomaly_start <= selected <= anomaly_end),
        "ucr_localisation": bool(tolerance_start <= selected <= tolerance_end),
        "signed_distance_from_anomaly": int(signed_distance),
        "absolute_distance_from_anomaly": int(abs(signed_distance)),
        "ucr_tolerance_start_zero_based": int(tolerance_start),
        "ucr_tolerance_end_zero_based": int(tolerance_end),
    }


def score_series(values: np.ndarray, metadata: dict) -> dict:
    train_end, anomaly_start, anomaly_end = boundary_conversion(
        metadata, len(values)
    )
    fibonacci, fibonacci_diagnostics = curvature_bank(
        values, train_end, FIBONACCI_LATTICE
    )
    equal_step, equal_diagnostics = curvature_bank(
        values, train_end, EQUAL_STEP_LATTICE
    )
    first_difference, first_diagnostics = first_difference_scores(values, train_end)
    robust_level, robust_diagnostics = robust_level_scores(values, train_end)
    ewma, ewma_diagnostics = ewma_scores(values, train_end)
    timelines = {
        METHODS[0]: fibonacci,
        METHODS[1]: equal_step,
        METHODS[2]: first_difference,
        METHODS[3]: robust_level,
        METHODS[4]: ewma,
    }
    method_diagnostics = {
        METHODS[0]: {"per_index": fibonacci_diagnostics},
        METHODS[1]: {"per_index": equal_diagnostics},
        METHODS[2]: first_diagnostics,
        METHODS[3]: robust_diagnostics,
        METHODS[4]: ewma_diagnostics,
    }
    outcomes = {
        method: select_peak(scores, train_end, anomaly_start, anomaly_end)
        for method, scores in timelines.items()
    }
    return {
        "row_count": int(len(values)),
        "train_end_zero_based_exclusive": train_end,
        "test_start_zero_based": train_end,
        "test_length": int(len(values) - train_end),
        "anomaly_start_zero_based": anomaly_start,
        "anomaly_end_zero_based": anomaly_end,
        "anomaly_length": anomaly_end - anomaly_start + 1,
        "methods": outcomes,
        "method_calibration": method_diagnostics,
    }


def aggregate_records(series: list[dict]) -> tuple[dict, dict, list[str], np.ndarray]:
    families: dict[str, list[dict]] = defaultdict(list)
    for record in series:
        families[record["family_key"]].append(record)
    family_keys = sorted(families)
    family_matrix = np.zeros((len(family_keys), len(METHODS)), dtype=np.float64)
    family_detail: dict[str, dict] = {}
    for row, key in enumerate(family_keys):
        members = families[key]
        method_values = {}
        for column, method in enumerate(METHODS):
            values = [
                float(item["methods"][method]["ucr_localisation"])
                for item in members
            ]
            family_matrix[row, column] = float(np.mean(values))
            method_values[method] = family_matrix[row, column]
        family_detail[key] = {
            "member_count": len(members),
            "dataset_ids": sorted(item["dataset_id"] for item in members),
            "method_ucr_success_means": method_values,
        }

    method_aggregate: dict[str, dict] = {}
    for column, method in enumerate(METHODS):
        strict = [
            int(item["methods"][method]["strict_localisation"]) for item in series
        ]
        ucr = [int(item["methods"][method]["ucr_localisation"]) for item in series]
        distances = [
            item["methods"][method]["absolute_distance_from_anomaly"]
            for item in series
        ]
        method_aggregate[method] = {
            "strict_success_count": int(sum(strict)),
            "strict_series_macro_fraction": float(np.mean(strict)),
            "ucr_success_count": int(sum(ucr)),
            "ucr_series_macro_fraction": float(np.mean(ucr)),
            "ucr_family_macro_fraction": float(np.mean(family_matrix[:, column])),
            "median_absolute_distance": float(np.median(distances)),
        }
    return method_aggregate, family_detail, family_keys, family_matrix


def percentile_interval(values: np.ndarray) -> list[float]:
    lower, upper = np.quantile(values, [0.025, 0.975])
    return [float(lower), float(upper)]


def cluster_bootstrap(
    family_keys: list[str], family_matrix: np.ndarray
) -> tuple[dict, dict]:
    rng = np.random.default_rng(np.random.SeedSequence([SEED, 1]))
    family_count = len(family_keys)
    sampled = rng.integers(
        0, family_count, size=(BOOTSTRAP_REPLICATES, family_count)
    )
    replicate_values = family_matrix[sampled].mean(axis=1)
    method_intervals = {
        method: {
            "estimate": float(np.mean(family_matrix[:, column])),
            "percentile_95_interval": percentile_interval(
                replicate_values[:, column]
            ),
        }
        for column, method in enumerate(METHODS)
    }
    primary = replicate_values[:, 0]
    difference_intervals = {}
    for column, comparator in enumerate(COMPARATORS, start=1):
        observed = float(np.mean(family_matrix[:, 0] - family_matrix[:, column]))
        differences = primary - replicate_values[:, column]
        difference_intervals[comparator] = {
            "primary_minus_comparator_estimate": observed,
            "percentile_95_interval": percentile_interval(differences),
        }
    metadata = {
        "seed_sequence": [SEED, 1],
        "replicates": BOOTSTRAP_REPLICATES,
        "sampling_unit": "provenance family",
        "family_count": family_count,
    }
    return {
        "methods": method_intervals,
        "primary_differences": difference_intervals,
    }, metadata


def holm_adjust(raw: dict[str, float]) -> dict[str, float]:
    ordered = sorted(raw, key=raw.get)
    count = len(ordered)
    adjusted: dict[str, float] = {}
    running = 0.0
    for rank, key in enumerate(ordered):
        candidate = (count - rank) * raw[key]
        running = max(running, candidate)
        adjusted[key] = min(1.0, running)
    return adjusted


def paired_sign_flip(family_matrix: np.ndarray) -> tuple[dict, dict]:
    differences = family_matrix[:, [0]] - family_matrix[:, 1:]
    observed = differences.mean(axis=0)
    exceed = np.zeros(len(COMPARATORS), dtype=np.int64)
    rng = np.random.default_rng(np.random.SeedSequence([SEED, 2]))
    remaining = SIGN_FLIP_REPLICATES
    chunk_size = 10_000
    while remaining:
        count = min(chunk_size, remaining)
        signs = rng.choice(
            np.asarray([-1.0, 1.0]),
            size=(count, differences.shape[0]),
            replace=True,
        )
        permuted = signs @ differences / differences.shape[0]
        exceed += np.sum(
            np.abs(permuted) >= np.abs(observed)[None, :], axis=0
        )
        remaining -= count
    raw = {
        comparator: float((1 + exceed[index]) / (SIGN_FLIP_REPLICATES + 1))
        for index, comparator in enumerate(COMPARATORS)
    }
    adjusted = holm_adjust(raw)
    result = {
        comparator: {
            "primary_minus_comparator_family_mean": float(observed[index]),
            "two_sided_plus_one_p_value": raw[comparator],
            "holm_adjusted_p_value": adjusted[comparator],
        }
        for index, comparator in enumerate(COMPARATORS)
    }
    metadata = {
        "seed_sequence": [SEED, 2],
        "replicates": SIGN_FLIP_REPLICATES,
        "exchangeability_unit": "provenance family",
        "statistic": "absolute mean family success difference",
        "multiplicity": "Holm across four comparisons",
    }
    return result, metadata


def alignment_surrogate(
    series: list[dict],
    family_keys: list[str],
    observed_family_macro: float,
) -> tuple[dict, dict]:
    family_index = {key: index for index, key in enumerate(family_keys)}
    family_sizes = np.zeros(len(family_keys), dtype=np.int64)
    successes = np.zeros(
        (SURROGATE_REPLICATES, len(family_keys)), dtype=np.float64
    )
    rng = np.random.default_rng(np.random.SeedSequence([SEED, 3]))
    for record in series:
        index = family_index[record["family_key"]]
        family_sizes[index] += 1
        primary = record["methods"][PRIMARY_METHOD]
        test_length = int(record["test_length"])
        peak_relative = (
            int(primary["selected_index_zero_based"])
            - int(record["test_start_zero_based"])
        )
        low = (
            int(primary["ucr_tolerance_start_zero_based"])
            - int(record["test_start_zero_based"])
        )
        high = (
            int(primary["ucr_tolerance_end_zero_based"])
            - int(record["test_start_zero_based"])
        )
        shifts = rng.integers(1, test_length, size=SURROGATE_REPLICATES)
        shifted = (peak_relative + shifts) % test_length
        successes[:, index] += ((shifted >= low) & (shifted <= high)).astype(
            np.float64
        )
    family_rates = successes / family_sizes[None, :]
    aggregates = family_rates.mean(axis=1)
    exceed = int(np.count_nonzero(aggregates >= observed_family_macro))
    result = {
        "observed_primary_family_macro_ucr_success": observed_family_macro,
        "surrogate_mean": float(np.mean(aggregates)),
        "surrogate_percentile_95_interval": percentile_interval(aggregates),
        "one_sided_plus_one_p_value": float(
            (1 + exceed) / (SURROGATE_REPLICATES + 1)
        ),
        "surrogate_aggregates_at_least_observed": exceed,
    }
    metadata = {
        "seed_sequence": [SEED, 3],
        "replicates": SURROGATE_REPLICATES,
        "shift": "independent uniformly sampled non-zero circular peak shift",
        "aggregation": "provenance-family macro",
    }
    return result, metadata


def acquisition_manifest(
    reader: HTTPRangeReader,
    archive_sha256: str,
    raw_members: list[dict],
    canonical_members: list[dict],
    duplicate_groups: list[dict],
) -> dict:
    return {
        "archive_url": reader.url,
        "content_length": reader.length,
        "etag": reader.etag,
        "last_modified": reader.last_modified,
        "accept_ranges": reader.accept_ranges,
        "archive_sha256": archive_sha256,
        "raw_matching_member_count": len(raw_members),
        "unique_matching_basename_count": len(canonical_members),
        "exact_duplicate_groups": duplicate_groups,
        "members": [
            {
                "dataset_id": item["dataset_id"],
                "member_path": item["member_path"],
                "uncompressed_bytes": item["uncompressed_bytes"],
                "uncompressed_sha256": item["uncompressed_sha256"],
            }
            for item in raw_members
        ],
        "canonical_series": [
            {
                "dataset_id": item["dataset_id"],
                "canonical_member_path": item["member_path"],
                "duplicate_source_paths": item["duplicate_source_paths"],
            }
            for item in canonical_members
        ],
        "storage_policy": (
            "streamed over HTTP ranges; full ZIP and extracted raw members "
            "not retained locally"
        ),
    }


def render_manifest_markdown(manifest: dict) -> str:
    lines = [
        "# QGITA v2 UCR acquisition manifest",
        "",
        f"- Archive URL: `{manifest['archive_url']}`",
        f"- Content length: `{manifest['content_length']}` bytes",
        f"- ETag: `{manifest['etag']}`",
        f"- Last-Modified: `{manifest['last_modified']}`",
        f"- Whole-archive SHA-256: `{manifest['archive_sha256']}`",
        f"- Raw matching members: `{manifest['raw_matching_member_count']}`",
        "- Unique matching basenames: "
        f"`{manifest['unique_matching_basename_count']}`",
        f"- Exact duplicate groups: `{len(manifest['exact_duplicate_groups'])}`",
        "- Storage: streamed over HTTP ranges; no full ZIP or extracted raw "
        "corpus retained locally.",
        "",
        "## Member fingerprints",
        "",
        "| ID | Bytes | SHA-256 | Member path |",
        "|---:|---:|---|---|",
    ]
    for member in manifest["members"]:
        lines.append(
            f"| {member['dataset_id']} | {member['uncompressed_bytes']} | "
            f"`{member['uncompressed_sha256']}` | "
            f"`{member['member_path']}` |"
        )
    return "\n".join(lines) + "\n"


def build_result() -> tuple[dict, dict]:
    reader = HTTPRangeReader(ARCHIVE_URL)
    archive_sha256 = hash_remote_archive(ARCHIVE_URL, reader.length)
    series: list[dict] = []
    exclusions: list[dict] = []
    member_records: list[dict] = []
    raw_member_records: list[dict] = []
    duplicate_groups: list[dict] = []
    with zipfile.ZipFile(reader) as archive:
        candidates = [
            info
            for info in archive.infolist()
            if not info.is_dir() and MEMBER_PATTERN.fullmatch(Path(info.filename).name)
        ]
        if len(candidates) != EXPECTED_RAW_MEMBER_COUNT:
            raise RuntimeError(
                f"frozen member rule selected {len(candidates)} members; "
                f"expected {EXPECTED_RAW_MEMBER_COUNT}"
            )
        grouped: dict[str, list[zipfile.ZipInfo]] = defaultdict(list)
        for info in candidates:
            grouped[Path(info.filename).name].append(info)
        if len(grouped) != EXPECTED_UNIQUE_MEMBER_COUNT:
            raise RuntimeError(
                f"found {len(grouped)} unique matching basenames; "
                f"expected {EXPECTED_UNIQUE_MEMBER_COUNT}"
            )
        repeated = {name: infos for name, infos in grouped.items() if len(infos) > 1}
        if set(repeated) != {EXPECTED_DUPLICATE_BASENAME}:
            raise RuntimeError(
                "archive duplicate set does not match the frozen amendment"
            )
        if len(repeated[EXPECTED_DUPLICATE_BASENAME]) != 2:
            raise RuntimeError("expected duplicate basename does not occur twice")

        # Validate the packaging duplicate before parsing any member or scoring
        # any detector, as required by amendment 2.
        duplicate_payload_by_path: dict[str, bytes] = {}
        duplicate_fingerprints: list[dict] = []
        for info in sorted(
            repeated[EXPECTED_DUPLICATE_BASENAME],
            key=lambda item: item.filename,
        ):
            payload = archive.read(info)
            duplicate_payload_by_path[info.filename] = payload
            duplicate_fingerprints.append(
                {
                    "member_path": info.filename,
                    "uncompressed_bytes": len(payload),
                    "uncompressed_sha256": sha256_bytes(payload),
                    "crc32": f"{info.CRC:08X}",
                }
            )
        if len(
            {
                (
                    item["uncompressed_bytes"],
                    item["uncompressed_sha256"],
                    item["crc32"],
                )
                for item in duplicate_fingerprints
            }
        ) != 1:
            raise RuntimeError("the repeated UCR basename is not byte-identical")
        duplicate_groups.append(
            {
                "basename": EXPECTED_DUPLICATE_BASENAME,
                "resolution": (
                    "byte-identical; UCR_Anomaly_FullData path parsed once"
                ),
                "entries": duplicate_fingerprints,
            }
        )

        for ordinal, basename in enumerate(sorted(grouped), start=1):
            infos = grouped[basename]
            if len(infos) == 1:
                info = infos[0]
                payload = archive.read(info)
                duplicate_source_paths: list[str] = []
                raw_member_records.append(
                    {
                        **parse_member_basename(info.filename),
                        "member_path": info.filename,
                        "uncompressed_bytes": len(payload),
                        "uncompressed_sha256": sha256_bytes(payload),
                    }
                )
            else:
                canonical = [
                    item
                    for item in infos
                    if "/UCR_Anomaly_FullData/" in item.filename.replace("\\", "/")
                ]
                if len(canonical) != 1:
                    raise RuntimeError(
                        "exact duplicate has no unique UCR_Anomaly_FullData path"
                    )
                info = canonical[0]
                payload = duplicate_payload_by_path[info.filename]
                duplicate_source_paths = sorted(
                    item.filename for item in infos if item.filename != info.filename
                )
                for item in sorted(infos, key=lambda value: value.filename):
                    raw_payload = duplicate_payload_by_path[item.filename]
                    raw_member_records.append(
                        {
                            **parse_member_basename(item.filename),
                            "member_path": item.filename,
                            "uncompressed_bytes": len(raw_payload),
                            "uncompressed_sha256": sha256_bytes(raw_payload),
                        }
                    )
            print(
                f"scoring UCR series {ordinal}/{len(grouped)}: {basename}",
                file=sys.stderr,
                flush=True,
            )
            parsed = parse_member_basename(info.filename)
            member_record = {
                **parsed,
                "member_path": info.filename,
                "uncompressed_bytes": len(payload),
                "uncompressed_sha256": sha256_bytes(payload),
                "duplicate_source_paths": duplicate_source_paths,
            }
            member_records.append(member_record)
            try:
                text = payload.decode("ascii")
                values = np.fromstring(text, sep=" ", dtype=np.float64)
                if values.size == 0:
                    raise ValueError("member contains no numeric values")
                if not np.all(np.isfinite(values)):
                    raise ValueError("member contains non-finite values")
                # np.fromstring can stop at malformed text; verify token count.
                tokens = text.split()
                if len(tokens) != len(values):
                    raise ValueError("member contains a non-numeric token")
                scored = score_series(values, parsed)
                series.append(
                    {
                        "dataset_id": parsed["dataset_id"],
                        "name": parsed["name"],
                        "family_key": family_key(parsed["name"]),
                        "member_path": info.filename,
                        "uncompressed_bytes": len(payload),
                        "uncompressed_sha256": member_record[
                            "uncompressed_sha256"
                        ],
                        "duplicate_source_paths": duplicate_source_paths,
                        **scored,
                    }
                )
            except (ValueError, FloatingPointError, OverflowError) as error:
                exclusions.append(
                    {
                        "dataset_id": parsed["dataset_id"],
                        "member_path": info.filename,
                        "reason": str(error),
                    }
                )

    if not series:
        raise RuntimeError("no UCR series was evaluable")
    aggregate, family_detail, family_keys, family_matrix = aggregate_records(series)
    bootstrap, bootstrap_meta = cluster_bootstrap(family_keys, family_matrix)
    paired, paired_meta = paired_sign_flip(family_matrix)
    surrogate, surrogate_meta = alignment_surrogate(
        series,
        family_keys,
        aggregate[PRIMARY_METHOD]["ucr_family_macro_fraction"],
    )
    manifest = acquisition_manifest(
        reader,
        archive_sha256,
        raw_member_records,
        member_records,
        duplicate_groups,
    )
    result = {
        "benchmark_identity": {
            "protocol_file": PROTOCOL_FILE,
            "protocol_sha256": PROTOCOL_SHA256,
            "protocol_amendment_file": PROTOCOL_AMENDMENT_FILE,
            "protocol_amendment_sha256": PROTOCOL_AMENDMENT_SHA256,
            "evidence_class": (
                "researcher-run prospectively frozen second-corpus benchmark"
            ),
            "independent_replication": False,
            "physical_validation": False,
            "primary_method": PRIMARY_METHOD,
        },
        "frozen_design": {
            "methods": list(METHODS),
            "fibonacci_lattice": FIBONACCI_LATTICE.tolist(),
            "equal_step_lattice": EQUAL_STEP_LATTICE.tolist(),
            "curvature_quantile": CURVATURE_QUANTILE,
            "minimum_calibration_observations": MIN_CALIBRATION_OBSERVATIONS,
            "ewma_alpha": EWMA_ALPHA,
            "seed": SEED,
            "bootstrap_replicates": BOOTSTRAP_REPLICATES,
            "sign_flip_replicates": SIGN_FLIP_REPLICATES,
            "surrogate_replicates": SURROGATE_REPLICATES,
            "indexing": "archive one-based; result decision indices zero-based and one-based",
            "primary_endpoint": "UCR peak localisation",
        },
        "acquisition": {
            key: value
            for key, value in manifest.items()
            if key not in {"members", "canonical_series"}
        },
        "evaluation": {
            "raw_matching_member_count": len(raw_member_records),
            "unique_matching_basename_count": len(member_records),
            "exact_duplicate_group_count": len(duplicate_groups),
            "evaluable_series_count": len(series),
            "excluded_series_count": len(exclusions),
            "provenance_family_count": len(family_keys),
        },
        "aggregate": aggregate,
        "family_cluster_bootstrap": bootstrap,
        "family_cluster_bootstrap_metadata": bootstrap_meta,
        "paired_family_sign_flip_tests": paired,
        "paired_family_sign_flip_metadata": paired_meta,
        "primary_alignment_surrogate": surrogate,
        "primary_alignment_surrogate_metadata": surrogate_meta,
        "family_detail": family_detail,
        "series": series,
        "exclusions": exclusions,
        "interpretation_boundary": (
            "second-corpus anomaly-localisation evidence only; not an "
            "independent replication, causal-physics test, Stage-2 test, "
            "peer review, publication, or validation of quantum gravity"
        ),
    }
    return result, manifest


def write_new(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(payload)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Run the frozen QGITA UCR second-corpus benchmark."
    )
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--manifest-output", required=True, type=Path)
    args = parser.parse_args(argv)
    if args.output.exists() or args.manifest_output.exists():
        raise FileExistsError("refusing to overwrite an existing output")
    result, manifest = build_result()
    result_payload = (
        json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n"
    ).encode("utf-8")
    manifest_payload = render_manifest_markdown(manifest).encode("utf-8")
    write_new(args.output, result_payload)
    write_new(args.manifest_output, manifest_payload)
    sys.stdout.buffer.write(result_payload)


if __name__ == "__main__":
    main()
