"""Offline receipt-contract tests for the UPE source -> HNC -> Auris route."""

from __future__ import annotations

import ast
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from aureon.bio import upe_signal_adapter as upe
from aureon.bio import human_harmonic_proxy as proxy
from scripts.validation.validate_real_data_contract import scan_text_file


NOW = 10_000.0


def _spectrum() -> np.ndarray:
    nm = np.linspace(200.0, 800.0, 2000)
    intensity = (
        np.ones_like(nm)
        + 0.9 * np.exp(-((nm - 400.0) ** 2) / (2.0 * 0.5**2))
        + 0.9 * np.exp(-((nm - 600.0) ** 2) / (2.0 * 0.5**2))
    )
    return np.column_stack([nm, intensity])


def _receipt_chain(
    values: np.ndarray,
) -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
    common: dict[str, object] = {
        "source_timestamp": NOW - 10.0,
        "received_at": NOW - 9.0,
        "freshness_ttl_sec": 60.0,
        "generated_values": False,
        "eligible_for_action": True,
        "eligible_for_accounting": False,
        "eligible_for_learning": True,
    }
    measurement = {
        **common,
        "receipt_id": "upe-measurement-1",
        "source_id": "lab.pmt.alpha",
        "receipt_type": "upe_measurement",
        "truth_status": "real_observed",
        "kind": "spectrum",
        "data_sha256": upe.upe_data_sha256(values),
    }
    hnc = {
        **common,
        "receipt_id": "hnc-gate-1",
        "source_id": "aureon.hnc",
        "receipt_type": "hnc_coherence",
        "truth_status": "real_derived",
        "source_timestamp": NOW - 8.0,
        "received_at": NOW - 7.0,
        "input_receipt_ids": [measurement["receipt_id"]],
        "coherence": 0.8,
        "gate_open": True,
    }
    auris = {
        **common,
        "receipt_id": "auris-gate-1",
        "source_id": "aureon.auris",
        "receipt_type": "auris_coherence",
        "truth_status": "real_derived",
        "source_timestamp": NOW - 6.0,
        "received_at": NOW - 5.0,
        "input_receipt_ids": [measurement["receipt_id"], hnc["receipt_id"]],
        "coherence": 0.9,
        "gate_open": True,
    }
    return measurement, hnc, auris


def test_generated_controls_are_frozen_non_operational_and_not_relabelable() -> None:
    control = upe.control_upe("structured")
    assert control.provenance == "bio.control.upe.structured"
    assert control.data_origin == "derived_statistical_control"
    assert control.truth_status == "statistical_control"
    assert control.generated_values is True
    assert control.control_only is True
    assert control.live_data is False
    assert control.provider_observation is False
    assert control.operational_eligible is False
    assert control.action_eligible is False
    assert control.actionable is False
    assert control.accounting_eligible is False
    assert control.learning_eligible is False
    assert control.provider_eligible is False
    assert control.receipt_ids == ()

    with pytest.raises(TypeError):
        control.samples[0][0] = 999.0  # type: ignore[index]
    readonly = control.as_array()
    assert readonly.flags.writeable is False
    with pytest.raises(ValueError):
        readonly[0, 0] = 999.0

    signal = upe.UPESignalAdapter().extract(
        control,
        consent=True,
        provenance="caller cannot relabel this provider-live",
    )
    assert signal.provenance == control.provenance
    assert signal.control_only is True
    assert signal.operational_eligible is False
    assert signal.actionable is False

    relabelled = replace(
        control,
        provenance="lab.pmt.alpha#invented",
        control_only=False,
        generated_values=False,
        live_data=True,
        provider_observation=True,
        operational_eligible=True,
        action_eligible=True,
        actionable=True,
        learning_eligible=True,
        provider_eligible=True,
    )
    with pytest.raises(ValueError, match="live UPE input requires"):
        upe.UPESignalAdapter().extract(
            relabelled,
            consent=True,
            provenance="attempted relabel",
        )


def test_unreceipted_arrays_remain_control_only_regardless_of_claimed_provenance() -> None:
    signal = upe.UPESignalAdapter().extract(
        _spectrum(),
        consent=True,
        provenance="claimed provider observation",
    )
    assert signal.provenance == "bio.control.upe.unverified_input"
    assert signal.truth_status == "statistical_control"
    assert signal.generated_values is True
    assert signal.control_only is True
    assert signal.live_data is False
    assert signal.operational_eligible is False
    assert signal.actionable is False
    assert signal.learning_eligible is False


def test_complete_fresh_linked_receipts_open_the_live_hnc_auris_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    values = _spectrum()
    measurement, hnc, auris = _receipt_chain(values)
    signal = upe.UPESignalAdapter().extract(
        values,
        consent=True,
        provenance="operator consented laboratory observation",
        measurement_receipt=measurement,
        hnc_receipt=hnc,
        auris_receipt=auris,
        now=NOW,
    )
    assert signal.frequencies_hz
    assert signal.provenance == "lab.pmt.alpha#upe-measurement-1;hnc#hnc-gate-1;auris#auris-gate-1"
    assert signal.receipt_ids == (
        "upe-measurement-1",
        "hnc-gate-1",
        "auris-gate-1",
    )
    assert signal.truth_status == "real_observed"
    assert signal.generated_values is False
    assert signal.control_only is False
    assert signal.live_data is True
    assert signal.provider_observation is True
    assert signal.operational_eligible is True
    assert signal.action_eligible is True
    assert signal.actionable is True
    assert signal.learning_eligible is True
    assert signal.provider_eligible is True
    assert signal.accounting_eligible is False

    monkeypatch.setattr(
        proxy,
        "_get_conscience",
        lambda: SimpleNamespace(
            ask_why=lambda *_args, **_kwargs: SimpleNamespace(
                verdict=SimpleNamespace(name="APPROVED")
            )
        ),
    )
    scored = upe.score_upe(
        values,
        consent=True,
        provenance="operator consented laboratory observation",
        measurement_receipt=measurement,
        hnc_receipt=hnc,
        auris_receipt=auris,
        now=NOW,
        nulls=120,
    )
    payload = scored.to_dict()
    assert payload["truth_status"] == "real_derived"
    assert payload["generated_values"] is False
    assert payload["operational_eligible"] is True
    assert payload["learning_eligible"] is True
    assert payload["provider_eligible"] is True
    assert payload["accounting_eligible"] is False
    assert payload["actionable"] is scored.structure_present
    assert payload["input_receipt_ids"] == [
        "upe-measurement-1",
        "hnc-gate-1",
        "auris-gate-1",
    ]


@pytest.mark.parametrize(
    ("target", "field", "value", "message"),
    [
        ("measurement", "generated_values", True, "generated_values=false"),
        ("measurement", "data_sha256", "0" * 64, "does not bind"),
        ("measurement", "source_timestamp", NOW - 1_000.0, "stale"),
        ("hnc", "input_receipt_ids", ["another-input"], "link exactly"),
        ("auris", "gate_open", False, "explicitly pass"),
        ("auris", "received_at", float("nan"), "finite"),
    ],
)
def test_incomplete_generated_stale_or_unlinked_receipts_fail_closed(
    target: str,
    field: str,
    value: object,
    message: str,
) -> None:
    values = _spectrum()
    measurement, hnc, auris = _receipt_chain(values)
    receipts = {
        "measurement": deepcopy(measurement),
        "hnc": deepcopy(hnc),
        "auris": deepcopy(auris),
    }
    receipts[target][field] = value
    with pytest.raises(ValueError, match=message):
        upe.build_live_upe_input(
            values,
            measurement_receipt=receipts["measurement"],
            hnc_receipt=receipts["hnc"],
            auris_receipt=receipts["auris"],
            now=NOW,
        )


def test_timeseries_receipt_binds_exact_sample_rate_and_nonnegative_counts() -> None:
    counts = np.arange(32, dtype=float)
    sample_rate = 8.0
    common: dict[str, object] = {
        "source_timestamp": NOW - 3.0,
        "received_at": NOW - 2.0,
        "freshness_ttl_sec": 30.0,
        "generated_values": False,
        "eligible_for_action": True,
        "eligible_for_accounting": False,
        "eligible_for_learning": True,
    }
    measurement = {
        **common,
        "receipt_id": "counts-1",
        "source_id": "lab.pmt.counter",
        "receipt_type": "upe_measurement",
        "truth_status": "real_observed",
        "kind": "timeseries",
        "sample_rate_hz": sample_rate,
        "data_sha256": upe.upe_data_sha256(counts, kind="timeseries"),
    }
    hnc = {
        **common,
        "receipt_id": "hnc-counts-1",
        "source_id": "aureon.hnc",
        "receipt_type": "hnc_coherence",
        "truth_status": "real_derived",
        "source_timestamp": NOW - 1.5,
        "received_at": NOW - 1.0,
        "input_receipt_ids": ["counts-1"],
        "coherence": 0.8,
        "gate_open": True,
    }
    auris = {
        **common,
        "receipt_id": "auris-counts-1",
        "source_id": "aureon.auris",
        "receipt_type": "auris_coherence",
        "truth_status": "real_derived",
        "source_timestamp": NOW - 0.8,
        "received_at": NOW - 0.5,
        "input_receipt_ids": ["counts-1", "hnc-counts-1"],
        "coherence": 0.9,
        "gate_open": True,
    }
    live = upe.build_live_upe_input(
        counts,
        measurement_receipt=measurement,
        hnc_receipt=hnc,
        auris_receipt=auris,
        kind="timeseries",
        sample_rate_hz=sample_rate,
        now=NOW,
    )
    with pytest.raises(ValueError, match="does not match"):
        upe.UPESignalAdapter().extract(
            live,
            consent=True,
            provenance="consented counts",
            kind="timeseries",
            sample_rate_hz=sample_rate * 2.0,
            now=NOW,
        )

    with pytest.raises(ValueError, match="non-negative"):
        upe.build_live_upe_input(
            -counts,
            measurement_receipt=measurement,
            hnc_receipt=hnc,
            auris_receipt=auris,
            kind="timeseries",
            sample_rate_hz=sample_rate,
            now=NOW,
        )


def test_module_is_inert_and_exact_hardened_validator_is_clean() -> None:
    target = Path(upe.__file__).resolve()
    tree = ast.parse(target.read_text(encoding="utf-8"))
    assert not any(
        isinstance(node, ast.FunctionDef) and node.name == "main"
        for node in tree.body
    )
    assert not any(
        isinstance(node, ast.If)
        and isinstance(node.test, ast.Compare)
        and isinstance(node.test.left, ast.Name)
        and node.test.left.id == "__name__"
        for node in tree.body
    )
    root = Path(__file__).resolve().parents[1]
    assert scan_text_file(target, root) == []
