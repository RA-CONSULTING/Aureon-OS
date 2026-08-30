"""Hermetic coverage for the six-tradition rune oracle."""

from __future__ import annotations

from typing import Any

from aureon.intelligence.aureon_seer import OracleOfRunes


def test_unified_oracle_reads_all_six_local_catalogues_without_market_data(
    monkeypatch: Any,
) -> None:
    oracle = OracleOfRunes()
    fixed_longitudes = dict(OracleOfRunes._EPOCH_LONGITUDES)
    monkeypatch.setattr(oracle, "_get_all_longitudes", lambda _now: fixed_longitudes)

    reading = oracle.read()

    assert reading.oracle == "RUNES"
    assert set(oracle._catalogues) == set(OracleOfRunes._TRADITIONS)
    assert reading.details["total_symbols"] == sum(
        len(symbols) for symbols in oracle._catalogues.values()
    )
    assert reading.details["total_symbols"] > 0
    assert set(reading.details["planetary_longitudes"]) == set(fixed_longitudes)
    assert 0.0 <= reading.score <= 1.0
    assert 0.0 <= reading.confidence <= 1.0
    assert reading.phase in {
        "ANCIENT_FIRE",
        "ANCIENT_LIGHT",
        "ANCIENT_FLUX",
        "ANCIENT_SHADOW",
        "ANCIENT_VOID",
    }
