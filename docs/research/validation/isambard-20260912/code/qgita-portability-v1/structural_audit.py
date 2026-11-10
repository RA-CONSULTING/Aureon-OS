"""Independent audit of the frozen QGITA UCR robustness result.

This verifier does not import the robustness runner.  It independently checks
the frozen-file identities, byte-identical rerun, ledger topology, deterministic
seeds, missing-data arithmetic, family bootstrap, and phase-surrogate summary.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path

import numpy as np


ROOT_SEED = 20260728
MISSING_REPLICATES = 5
PHASE_REPLICATES = 39
BOOTSTRAP_REPLICATES = 10_000
NONINFERIORITY_MARGIN = -0.05
SPECTRAL_RELATIVE_TOLERANCE = 1e-8
SCENARIOS = ("mcar_05", "mcar_10", "burst_05")
PRIMARY_METHOD = "qgita_fibonacci_scale_normalized"
EXPECTED_HASHES = {
    "QGITA_V2_UCR_POSTCONFIRMATORY_ROBUSTNESS_PROTOCOL_v1.md": (
        "F259A59A0678DB0EAD8AC0F955113581F3DDDF4A1176141E3DC0C8263BADB9F0"
    ),
    "QGITA_V2_UCR_POSTCONFIRMATORY_ROBUSTNESS_PROTOCOL_AMENDMENT_v2.md": (
        "F6A6AFCAEAE0CBAE5FDF979B0A599EE9C8E33AE65DE15FB86CAB711C057E8068"
    ),
    "audit_qgita_ucr_robustness.py": (
        "94403CD1F3A74072B9663978175B9CF02FCE91CB1C5058C8C3A33983CAC975AB"
    ),
    "test_qgita_ucr_robustness.py": (
        "CB2B3F57F17DA2E640D3DEE0944F2652AE318A602191256A7795A81C97077AEE"
    ),
    "QGITA_UCR_CONFIRMATORY_RESULT_v1.json": (
        "924411087C598C3F86632B6272CA3CAF3673CFF1F5AC277DB5888E0F93B27DDB"
    ),
}


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            hasher.update(chunk)
    return hasher.hexdigest().upper()


def expected_seed(dataset_id: str, scenario: str, replicate: int) -> int:
    payload = f"{ROOT_SEED}|{dataset_id}|{scenario}|{replicate}".encode("utf-8")
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big")


def assert_close(actual: float, expected: float, label: str) -> None:
    if not math.isclose(float(actual), float(expected), rel_tol=0.0, abs_tol=1e-15):
        raise AssertionError(f"{label}: {actual!r} != {expected!r}")


def assert_float_list(actual: list, expected: list, label: str) -> None:
    if len(actual) != len(expected):
        raise AssertionError(f"{label}: list length differs")
    for index, (left, right) in enumerate(zip(actual, expected)):
        assert_close(left, right, f"{label}[{index}]")


def audit(
    result_path: Path,
    rerun_path: Path,
    stdout_path: Path,
    canonical_path: Path,
) -> dict:
    here = result_path.resolve().parent
    for name, expected in EXPECTED_HASHES.items():
        actual = digest(here / name)
        if actual != expected:
            raise AssertionError(f"{name} hash mismatch: {actual}")

    # Supplemental v1: retain the frozen checks above; validate the rerun ledger.
    # Byte identity is reported explicitly and is never converted to PASS.
    reference_hash = digest(result_path)
    result_hash = digest(rerun_path)
    if digest(stdout_path) != result_hash:
        raise AssertionError("stdout must be byte-identical to the rerun")
    result = json.loads(rerun_path.read_text(encoding="utf-8"))
    canonical = json.loads(canonical_path.read_text(encoding="utf-8"))
    canonical_by_id = {row["dataset_id"]: row for row in canonical["series"]}
    if len(canonical_by_id) != 250:
        raise AssertionError("canonical ledger is not 250 unique dataset IDs")

    identity = result["identity"]
    if identity["protocol_sha256"] != EXPECTED_HASHES[
        "QGITA_V2_UCR_POSTCONFIRMATORY_ROBUSTNESS_PROTOCOL_v1.md"
    ]:
        raise AssertionError("result protocol identity differs from frozen protocol")
    if identity["canonical_result_sha256"] != EXPECTED_HASHES[
        "QGITA_UCR_CONFIRMATORY_RESULT_v1.json"
    ]:
        raise AssertionError("result canonical-result identity differs")

    evaluation = result["evaluation"]
    expected_evaluation = {
        "series_count": 250,
        "family_count": 46,
        "representative_count": 46,
        "clean_peak_identity": "PASS",
        "member_hash_identity": "PASS",
    }
    if evaluation != expected_evaluation:
        raise AssertionError(f"unexpected evaluation ledger: {evaluation}")

    design = result["design"]
    if (
        design["root_seed"] != ROOT_SEED
        or design["missing_replicates"] != MISSING_REPLICATES
        or design["phase_replicates"] != PHASE_REPLICATES
        or tuple(design["scenarios"]) != SCENARIOS
    ):
        raise AssertionError("result design differs from frozen design")
    assert_close(
        design["noninferiority_margin"],
        NONINFERIORITY_MARGIN,
        "noninferiority margin",
    )

    series = result["series"]
    if len(series) != 250 or len({row["dataset_id"] for row in series}) != 250:
        raise AssertionError("robustness series ledger is not 250 unique IDs")

    family_rows: dict[str, list[dict]] = defaultdict(list)
    for row in series:
        dataset_id = row["dataset_id"]
        source = canonical_by_id.get(dataset_id)
        if source is None:
            raise AssertionError(f"dataset absent from canonical ledger: {dataset_id}")
        if (
            row["family_key"] != source["family_key"]
            or row["member_path"] != source["member_path"]
            or row["member_sha256"] != source["uncompressed_sha256"]
            or row["test_length"] != source["test_length"]
        ):
            raise AssertionError(f"source identity mismatch: {dataset_id}")
        clean = row["clean"]
        canonical_clean = source["methods"][PRIMARY_METHOD]
        for key in (
            "selected_index_zero_based",
            "ucr_localisation",
            "strict_localisation",
        ):
            if clean[key] != canonical_clean[key]:
                raise AssertionError(f"clean result mismatch {dataset_id}: {key}")
        if tuple(sorted(row["missing"])) != tuple(sorted(SCENARIOS)):
            raise AssertionError(f"missing scenario set mismatch: {dataset_id}")
        for scenario in SCENARIOS:
            outcomes = row["missing"][scenario]
            if len(outcomes) != MISSING_REPLICATES:
                raise AssertionError(f"replicate count mismatch: {dataset_id}/{scenario}")
            for replicate, outcome in enumerate(outcomes):
                if outcome["replicate"] != replicate:
                    raise AssertionError("missing-data replicate order mismatch")
                seed = expected_seed(dataset_id, scenario, replicate)
                if outcome["seed"] != seed:
                    raise AssertionError(
                        f"missing-data seed mismatch: {dataset_id}/{scenario}/{replicate}"
                    )
                assert_close(
                    outcome["realized_missing_fraction"],
                    outcome["realized_missing_count"] / row["test_length"],
                    "realized missing fraction",
                )
                changed = (
                    outcome["ucr_localisation"] != clean["ucr_localisation"]
                )
                stable = (
                    abs(
                        outcome["selected_index_zero_based"]
                        - clean["selected_index_zero_based"]
                    )
                    <= 100
                )
                if outcome["ucr_outcome_changed_from_clean"] != changed:
                    raise AssertionError("changed-outcome flag mismatch")
                if outcome["peak_within_100_of_clean"] != stable:
                    raise AssertionError("peak-stability flag mismatch")
        family_rows[row["family_key"]].append(row)

    family_keys = sorted(family_rows)
    if len(family_keys) != 46:
        raise AssertionError(f"recomputed {len(family_keys)} families, expected 46")
    clean_family = np.asarray(
        [
            np.mean(
                [float(row["clean"]["ucr_localisation"]) for row in family_rows[key]]
            )
            for key in family_keys
        ],
        dtype=float,
    )
    missing_summary = result["missing_data"]
    assert_close(
        missing_summary["clean_family_macro_ucr_success"],
        float(np.mean(clean_family)),
        "clean family macro",
    )
    if (
        missing_summary["family_count"] != 46
        or missing_summary["bootstrap_replicates"] != BOOTSTRAP_REPLICATES
        or missing_summary["bootstrap_seed_sequence"] != [ROOT_SEED, 41]
    ):
        raise AssertionError("missing-data summary design mismatch")

    bootstrap_rng = np.random.default_rng(np.random.SeedSequence([ROOT_SEED, 41]))
    bootstrap_indices = bootstrap_rng.integers(
        0, 46, size=(BOOTSTRAP_REPLICATES, 46)
    )
    for scenario in SCENARIOS:
        replicate_series = []
        replicate_family = []
        stability = []
        changed = []
        missing_fractions = []
        family_perturbed = [[] for _ in family_keys]
        for replicate in range(MISSING_REPLICATES):
            all_outcomes = []
            for family_index, key in enumerate(family_keys):
                family_outcomes = [
                    row["missing"][scenario][replicate]
                    for row in family_rows[key]
                ]
                all_outcomes.extend(family_outcomes)
                family_perturbed[family_index].extend(
                    float(outcome["ucr_localisation"])
                    for outcome in family_outcomes
                )
            replicate_series.append(
                float(np.mean([row["ucr_localisation"] for row in all_outcomes]))
            )
            replicate_family.append(
                float(
                    np.mean(
                        [
                            np.mean(
                                [
                                    row["missing"][scenario][replicate][
                                        "ucr_localisation"
                                    ]
                                    for row in family_rows[key]
                                ]
                            )
                            for key in family_keys
                        ]
                    )
                )
            )
            stability.extend(
                float(row["peak_within_100_of_clean"]) for row in all_outcomes
            )
            changed.extend(
                float(row["ucr_outcome_changed_from_clean"])
                for row in all_outcomes
            )
            missing_fractions.extend(
                float(row["realized_missing_fraction"]) for row in all_outcomes
            )
        perturbed_family = np.asarray(
            [np.mean(values) for values in family_perturbed], dtype=float
        )
        differences = perturbed_family - clean_family
        bootstrap = differences[bootstrap_indices].mean(axis=1)
        interval = [float(value) for value in np.quantile(bootstrap, [0.025, 0.975])]
        actual = missing_summary["scenarios"][scenario]
        assert_float_list(
            actual["replicate_series_macro_ucr_success"],
            replicate_series,
            f"{scenario} series replicates",
        )
        assert_float_list(
            actual["replicate_family_macro_ucr_success"],
            replicate_family,
            f"{scenario} family replicates",
        )
        expected_scalars = {
            "mean_series_macro_ucr_success": np.mean(replicate_series),
            "mean_family_macro_ucr_success": np.mean(replicate_family),
            "mean_peak_within_100_stability": np.mean(stability),
            "mean_ucr_outcome_change_fraction": np.mean(changed),
            "mean_realized_missing_fraction": np.mean(missing_fractions),
            "perturbed_minus_clean_family_macro_estimate": np.mean(differences),
        }
        for key, expected in expected_scalars.items():
            assert_close(actual[key], expected, f"{scenario} {key}")
        assert_float_list(
            actual["replicate_series_macro_range"],
            [min(replicate_series), max(replicate_series)],
            f"{scenario} series range",
        )
        assert_float_list(
            actual["replicate_family_macro_range"],
            [min(replicate_family), max(replicate_family)],
            f"{scenario} family range",
        )
        assert_float_list(
            actual["cluster_bootstrap_95_interval"],
            interval,
            f"{scenario} bootstrap interval",
        )
        if (
            actual["noninferiority_margin"] != NONINFERIORITY_MARGIN
            or actual["noninferior"] != (interval[0] > NONINFERIORITY_MARGIN)
        ):
            raise AssertionError(f"{scenario} noninferiority decision mismatch")

    representative_ids = {
        min(rows, key=lambda item: int(item["dataset_id"]))["dataset_id"]
        for rows in family_rows.values()
    }
    phase_rows = result["phase_representatives"]
    if (
        len(phase_rows) != 46
        or {row["dataset_id"] for row in phase_rows} != representative_ids
    ):
        raise AssertionError("phase representative set differs from frozen rule")
    for row in phase_rows:
        series_row = next(
            item for item in series if item["dataset_id"] == row["dataset_id"]
        )
        if row["family_key"] != series_row["family_key"] or row["clean"] != series_row[
            "clean"
        ]:
            raise AssertionError("phase representative clean identity mismatch")
        if len(row["surrogates"]) != PHASE_REPLICATES:
            raise AssertionError("phase replicate count mismatch")
        for replicate, outcome in enumerate(row["surrogates"]):
            if (
                outcome["replicate"] != replicate
                or outcome["seed"]
                != expected_seed(row["dataset_id"], "phase_randomized", replicate)
            ):
                raise AssertionError("phase replicate identity mismatch")
            if outcome["spectral_relative_error"] > SPECTRAL_RELATIVE_TOLERANCE:
                raise AssertionError("phase spectral tolerance exceeded")

    phase_summary = result["phase_randomized_surrogate"]
    clean_ucr = float(np.mean([row["clean"]["ucr_localisation"] for row in phase_rows]))
    clean_strict = float(
        np.mean([row["clean"]["strict_localisation"] for row in phase_rows])
    )
    ucr_replicates = []
    strict_replicates = []
    errors = []
    for replicate in range(PHASE_REPLICATES):
        outcomes = [row["surrogates"][replicate] for row in phase_rows]
        ucr_replicates.append(
            float(np.mean([row["ucr_localisation"] for row in outcomes]))
        )
        strict_replicates.append(
            float(np.mean([row["strict_localisation"] for row in outcomes]))
        )
        errors.extend(float(row["spectral_relative_error"]) for row in outcomes)
    ucr_exceed = sum(value >= clean_ucr for value in ucr_replicates)
    strict_exceed = sum(value >= clean_strict for value in strict_replicates)
    scalar_expectations = {
        "clean_ucr_success_fraction": clean_ucr,
        "clean_strict_success_fraction": clean_strict,
        "surrogate_ucr_mean": np.mean(ucr_replicates),
        "surrogate_strict_mean": np.mean(strict_replicates),
        "ucr_one_sided_plus_one_p_value": (1 + ucr_exceed)
        / (PHASE_REPLICATES + 1),
        "strict_one_sided_plus_one_p_value": (1 + strict_exceed)
        / (PHASE_REPLICATES + 1),
        "maximum_spectral_relative_error": max(errors),
        "spectral_relative_tolerance": SPECTRAL_RELATIVE_TOLERANCE,
    }
    for key, expected in scalar_expectations.items():
        assert_close(phase_summary[key], expected, f"phase {key}")
    assert_float_list(
        phase_summary["surrogate_ucr_success_fractions"],
        ucr_replicates,
        "phase UCR replicates",
    )
    assert_float_list(
        phase_summary["surrogate_strict_success_fractions"],
        strict_replicates,
        "phase strict replicates",
    )
    assert_float_list(
        phase_summary["surrogate_ucr_range"],
        [min(ucr_replicates), max(ucr_replicates)],
        "phase UCR range",
    )
    assert_float_list(
        phase_summary["surrogate_strict_range"],
        [min(strict_replicates), max(strict_replicates)],
        "phase strict range",
    )
    if (
        phase_summary["representative_count"] != 46
        or phase_summary["replicates"] != PHASE_REPLICATES
        or phase_summary["surrogate_ucr_aggregates_at_least_clean"] != ucr_exceed
        or phase_summary["surrogate_strict_aggregates_at_least_clean"]
        != strict_exceed
    ):
        raise AssertionError("phase summary count mismatch")

    return {
        "status": "STRUCTURAL_PASS",
        "result_sha256": result_hash,
        "rerun_json_byte_identical": result_hash == reference_hash,
        "stdout_byte_identical_to_rerun": True,
        "frozen_reference_sha256": reference_hash,
        "frozen_input_hashes_verified": len(EXPECTED_HASHES),
        "series_ledgers_verified": len(series),
        "provenance_families_recomputed": len(family_keys),
        "missing_scenarios_recomputed": len(SCENARIOS),
        "missing_replicate_ledgers_verified": (
            len(series) * len(SCENARIOS) * MISSING_REPLICATES
        ),
        "phase_representatives_verified": len(phase_rows),
        "phase_replicate_ledgers_verified": len(phase_rows) * PHASE_REPLICATES,
        "maximum_spectral_relative_error": max(errors),
        "spectral_relative_tolerance": SPECTRAL_RELATIVE_TOLERANCE,
        "interpretation": (
            "independent structural and arithmetic audit of the produced files; "
            "not independent scientific replication, physical validation, peer "
            "review, publication, or evidence of a Fibonacci-specific mechanism"
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result", required=True, type=Path)
    parser.add_argument("--rerun", required=True, type=Path)
    parser.add_argument("--stdout", required=True, type=Path)
    parser.add_argument("--canonical", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f"refusing to overwrite {args.output}")
    report = audit(args.result, args.rerun, args.stdout, args.canonical)
    payload = (json.dumps(report, indent=2, sort_keys=True) + "\n").encode("utf-8")
    with args.output.open("xb") as handle:
        handle.write(payload)
    print(payload.decode("utf-8"), end="")


if __name__ == "__main__":
    main()
