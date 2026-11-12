"""An all-clear needs a reading. No live readings is NO_READING, never CLEAR,
and the soul reader never tells Gary to trade. No network, no randomness."""
from __future__ import annotations

import json

import pytest

from aureon.queen import queen_soul_reader as qsr


@pytest.fixture()
def reader(tmp_path, monkeypatch):
    monkeypatch.delenv("AUREON_ALLOW_SIM_FALLBACK", raising=False)
    monkeypatch.chdir(tmp_path)
    r = qsr.QueenSoulReader()
    monkeypatch.setattr(r, "_read_schumann_alignment", lambda: {"phase_lock": None})
    return r


def test_nothing_read_is_no_reading_not_clear(reader):
    rep = reader.scan_for_threats()
    assert rep["threat_level"] == "NO_READING"
    assert rep["threat_score"] is None
    assert rep["protection_status"] == "NO_READING"
    assert "Trade with confidence" not in rep["queen_assessment"]
    assert "not a trading signal" in rep["queen_assessment"]
    assert "528.422" not in rep["queen_assessment"]


def test_missing_inputs_are_no_reading_scores(reader):
    assert reader._scan_market_predators()["score"] is None
    assert reader._scan_schumann_disruption()["score"] is None


def test_measured_quiet_field_is_clear_without_trade_advice(reader, monkeypatch):
    monkeypatch.setattr(reader, "_read_schumann_alignment", lambda: {"phase_lock": 0.9})
    rep = reader.scan_for_threats()
    assert rep["threat_level"] == "CLEAR"
    assert rep["threat_score"] == 0.0
    text = rep["queen_assessment"]
    assert "ALL CLEAR" in text
    assert "Trade with confidence" not in text
    assert "528.422" not in text
    assert "grounding to Earth is stable" not in text


def test_real_predator_file_still_raises_threat(reader, tmp_path):
    (tmp_path / "predator_detection_history.json").write_text(json.dumps(
        {"predators": {"f1": {"firm_id": "f1", "threat_level": "high"}}, "front_run_rate": 0.0}))
    rep = reader.scan_for_threats()
    assert rep["threat_level"] == "LOW"
    assert rep["threat_score"] == 0.3


def test_empty_predator_file_is_a_reading(reader, tmp_path):
    (tmp_path / "predator_detection_history.json").write_text(json.dumps({"predators": {}}))
    assert reader._scan_market_predators()["score"] == 0.0
    assert reader.scan_for_threats()["threat_level"] == "CLEAR"
