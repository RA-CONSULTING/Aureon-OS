from __future__ import annotations

import inspect

from aureon.plumber.breaker import (
    SYNTHETIC_BREAKER_SCOPE,
    run_synthetic_offline_breaker_lab,
)


def test_breaker_is_argument_free_synthetic_offline_lab() -> None:
    assert not inspect.signature(run_synthetic_offline_breaker_lab).parameters
    report = run_synthetic_offline_breaker_lab()
    assert report.lab_scope == SYNTHETIC_BREAKER_SCOPE
    assert report.all_tamper_rejected
    assert len(report.cases) >= 7
    assert all(case.tamper_rejected for case in report.cases)
    assert not report.plaintext_exposed
    assert not report.production_validation


def test_breaker_public_report_suppresses_material_and_decoder_details() -> None:
    summary = run_synthetic_offline_breaker_lab().public_summary()
    rendered = repr(summary).casefold()
    for forbidden in (
        "synthetic-offline-breaker-fixture",
        "ciphertext_b64",
        "master_key",
        "attacker_key",
        "packet_contract_failed",
    ):
        assert forbidden not in rendered
    assert summary["production_validation"] is False
