"""Faculty refresh uses measured inputs and blocks the rest."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone

from aureon_fusion import faculty_refresh
from aureon_fusion.faculty_refresh import GDELT, HN, NOAA_KP, NOAA_XRAY, SCHUMANN_STATION, USGS_QUAKES, refresh
from aureon_fusion.flight_recorder import FACULTY_FILES


def _fetch(url: str):
    if url == NOAA_KP:
        return [{"time_tag": "2026-10-22T15:25:00", "kp_index": 1, "estimated_kp": 1.33, "kp": "1P"}]
    if url == NOAA_XRAY:
        return [{"time_tag": "2026-10-22T15:28:00Z", "flux": 8.1e-8, "energy": "0.1-0.8nm"}]
    if url == USGS_QUAKES:
        return {"features": [{"properties": {"mag": 2.1, "place": "fixture", "time": 1}}]}
    if url == HN:
        return {"hits": [{"title": "Markets fixture headline"}]}
    if url in {GDELT, SCHUMANN_STATION}:
        return {"_error": "HTTP 429", "_url": url}
    raise AssertionError(url)


def test_refresh_keeps_measured_values_and_blocks_the_unfed(tmp_path, monkeypatch):
    paths = {name: tmp_path / f"{name}.json" for name in faculty_refresh.PATHS}
    monkeypatch.setattr(faculty_refresh, "PATHS", paths)
    monkeypatch.setattr(
        "aureon_fusion.flight_recorder.FACULTY_FILES",
        [{**item, "path": paths[item["name"]]} for item in FACULTY_FILES],
    )
    monkeypatch.setattr("aureon_fusion.flight_recorder.FUSION_STATE", tmp_path)
    monkeypatch.setattr("aureon_fusion.flight_recorder.FLIGHT_LOG", tmp_path / "flight.jsonl")
    monkeypatch.setattr("aureon_fusion.flight_recorder.FLIGHT_HEALTH", tmp_path / "health.json")

    report = refresh(
        _fetch,
        organ_pids={"supervisor": os.getpid()},
        hnc_step=lambda kp: {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": "hnc_core",
            "truth_status": "real_derived",
            "input_kp_index": kp,
            "step": 1,
            "coherence_gamma": 0.5,
            "consciousness_psi": 0.2,
            "consciousness_level": "STIRRING",
            "simulation": False,
        },
        pulse=lambda: {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": "internal_telemetry",
            "truth_status": "real_derived",
            "pulse": 0.0,
            "components": {},
            "simulation": False,
        },
    )
    by_name = {row["faculty"]: row for row in report["rows"]}
    assert by_name["real_time_data"]["status"] == "fresh"
    assert by_name["hnc_core"]["status"] == "fresh"
    assert by_name["news_geo_digest"]["status"] == "fresh"
    assert by_name["schumann"]["status"] == "blocked"
    assert "not substituted" in by_name["schumann"]["blocked_reason"]
    assert by_name["real_portfolio"]["status"] == "blocked"
    assert by_name["prophecy_summary"]["status"] == "blocked"
    assert by_name["organ_registry"]["status"] == "fresh"
    measured = json.loads(paths["real_time_data"].read_text(encoding="utf-8"))
    assert measured["summary"]["kp"]["kp_index"] == 1
    assert measured["summary"]["xray"]["flux"] == 8.1e-8
    hnc = json.loads(paths["hnc_core"].read_text(encoding="utf-8"))
    assert hnc["input_kp_index"] == 1.0
    schumann = json.loads(paths["schumann"].read_text(encoding="utf-8"))
    assert "frequency_hz" not in schumann
    assert report["health"]["simulated_detected"] == []


def test_neutral_baseline_pulse_is_blocked(tmp_path, monkeypatch):
    paths = {name: tmp_path / f"{name}.json" for name in faculty_refresh.PATHS}
    monkeypatch.setattr(faculty_refresh, "PATHS", paths)
    monkeypatch.setattr(
        "aureon_fusion.flight_recorder.FACULTY_FILES",
        [{**item, "path": paths[item["name"]]} for item in FACULTY_FILES],
    )
    monkeypatch.setattr("aureon_fusion.flight_recorder.FUSION_STATE", tmp_path)
    monkeypatch.setattr("aureon_fusion.flight_recorder.FLIGHT_LOG", tmp_path / "flight.jsonl")
    monkeypatch.setattr("aureon_fusion.flight_recorder.FLIGHT_HEALTH", tmp_path / "health.json")
    monkeypatch.setattr(
        "aureon_fusion.knowledge_pulse_feeder.compute_pulse",
        lambda now=None: (
            0.5,
            {
                "research_activity": {
                    "available": True,
                    "baseline_established": True,
                    "value": 0.5,
                    "db_rows": 0,
                    "subsignals": {"db_growth": 0.5, "fragments": None},
                }
            },
        ),
    )

    def _down(_url: str):
        return {"_error": "offline"}

    report = refresh(_down, organ_pids=None)
    by_name = {row["faculty"]: row for row in report["rows"]}
    assert by_name["knowledge_pulse"]["status"] == "blocked"
    assert "0.5" in by_name["knowledge_pulse"]["blocked_reason"]
    written = json.loads(paths["knowledge_pulse"].read_text(encoding="utf-8"))
    assert "pulse" not in written
