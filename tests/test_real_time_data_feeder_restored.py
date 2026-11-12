"""Restored real_time_data_feeder: newest real reading only, no stand-ins.

No network: fetch_json is replaced with recorded-shape payloads (row
shapes copied from the live NOAA RTSW / GOES / USGS feeds on 12 Nov 2026).
"""

import importlib.util
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]


@pytest.fixture()
def feeder(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location(
        "real_time_data_feeder_under_test", REPO / "real_time_data_feeder.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "DATA_FILE", str(tmp_path / "real_time_data.json"))
    return module


WIND = [  # newest first, two spacecraft per minute, like RTSW
    {"time_tag": "2026-11-12T13:58:00", "active": False, "proton_speed": 483.4,
     "proton_density": 1.49, "source": "ACE"},
    {"time_tag": "2026-11-12T13:58:00", "active": True, "proton_speed": 470.1,
     "proton_density": 1.6, "source": "DSCOVR"},
    {"time_tag": "2026-11-11T14:01:00", "active": True, "proton_speed": 390.0,
     "proton_density": 4.0, "source": "DSCOVR"},
]

XRAY = [
    {"time_tag": "2026-11-12T13:59:00Z", "flux": 7.1e-07, "energy": "0.1-0.8nm"},
    {"time_tag": "2026-11-12T14:00:00Z", "flux": 1.46e-08, "energy": "0.05-0.4nm"},
    {"time_tag": "2026-11-12T14:00:00Z", "flux": 7.25e-07, "energy": "0.1-0.8nm"},
    {"time_tag": "2026-11-12T13:58:00Z", "flux": 9.9e-09, "energy": "0.05-0.4nm"},
]


def test_solar_wind_takes_newest_active_row_not_list_end(feeder):
    s = feeder.extract_solar_wind_summary(WIND)
    assert s["time_tag"] == "2026-11-12T13:58:00"
    assert s["speed"] == 470.1 and s["source"] == "DSCOVR"


def test_xray_takes_newest_long_band(feeder):
    x = feeder.extract_xray_summary(list(reversed(XRAY)))
    assert x == {"time_tag": "2026-11-12T14:00:00Z", "flux": 7.25e-07, "energy": "0.1-0.8nm"}


def _fake_fetch(all_hour):
    def fetch(url, timeout=15, ttl_s=45):
        if "significant_hour" in url:
            return {"features": []}
        if "all_hour" in url:
            return all_hour
        if "alerts" in url:
            return {"_error": "Fetch failed (no cache)", "_url": url}
        if "rtsw_wind" in url:
            return WIND
        if "xrays" in url:
            return XRAY
        return {"_error": "Fetch failed (no cache)", "_url": url}
    return fetch


def test_zero_significant_quakes_still_counts_all_hour(feeder, monkeypatch):
    quakes = {"features": [{"properties": {"mag": 1.2, "place": "x", "time": 1}}] * 8}
    monkeypatch.setattr(feeder, "fetch_json", _fake_fetch(quakes))
    out = feeder.collect_all()
    assert out["summary"]["quakes"]["count"] == 8
    assert out["endpoints"]["quakes"]["_significant_count"] == 0


def test_failed_all_hour_is_no_count_not_zero(feeder, monkeypatch):
    monkeypatch.setattr(feeder, "fetch_json", _fake_fetch({"_error": "Fetch failed (no cache)"}))
    out = feeder.collect_all()
    assert out["summary"]["quakes"] is None


def test_failed_alerts_fetch_is_none_not_zero(feeder, monkeypatch):
    monkeypatch.setattr(feeder, "fetch_json", _fake_fetch({"features": []}))
    out = feeder.collect_all()
    assert out["summary"]["alerts_count"] is None
    assert out["summary"]["kp"] is None  # failed fetch, no stand-in
    assert out["data_policy"] == "REAL_ONLY_NO_SYNTHETIC"
