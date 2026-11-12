"""Restored sero_space_weather: no stand-in values, real 24 h CME window."""

import importlib.util
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]


@pytest.fixture()
def sw(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("sero_sw_test", REPO / "sero_space_weather.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["sero_sw_test"] = mod
    spec.loader.exec_module(mod)
    monkeypatch.setattr(mod, "SW_STATE_FILE", tmp_path / "state.json")
    monkeypatch.setattr(mod, "SW_LOG", tmp_path / "log.jsonl")
    monkeypatch.setattr(mod, "FEEDER_ALERTS_PATH", tmp_path / "real_time_data.json")
    yield mod
    sys.modules.pop("sero_sw_test", None)


NOW = datetime(2026, 11, 12, 14, 0, tzinfo=timezone.utc)


def _alert(hours_ago, text="CME"):
    t = (NOW - timedelta(hours=hours_ago)).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    return {"product_id": "X", "issue_datetime": t, "message": text}


def test_unreachable_noaa_gives_none_not_minus_one(sw, monkeypatch):
    monkeypatch.setattr(sw, "communion_get_json", lambda *a, **k: None)
    snap = sw.fetch_space_weather()
    assert snap.kp_index is None
    assert snap.cme_count_24h is None
    assert snap.source_reachable is False
    b = sw.SpaceWeatherBridge()
    b.latest = snap
    assert b.is_storm_perturbed() is False
    assert b.get_stats()["cme_count_24h"] is None


def test_cme_count_is_last_24_hours_only(sw, monkeypatch):
    alerts = [_alert(2), _alert(23), _alert(30), _alert(24 * 20), _alert(1, "geomagnetic K-index 4")]
    monkeypatch.setattr(sw, "communion_get_json", lambda *a, **k: alerts)
    got = sw.fetch_cme_alerts(now=NOW)
    assert len(got) == 2


def test_failed_alerts_are_unknown_not_zero(sw, monkeypatch):
    monkeypatch.setattr(sw, "communion_get_json", lambda *a, **k: {"_error": "x"})
    assert sw.fetch_cme_alerts(now=NOW) is None


def test_feeder_snapshot_used_and_error_falls_back(sw, monkeypatch):
    sw.FEEDER_ALERTS_PATH.write_text(json.dumps(
        {"endpoints": {"alerts": {"_raw": [_alert(1)]}}}))
    monkeypatch.setattr(sw, "communion_get_json", lambda *a, **k: pytest.fail("no fetch"))
    assert len(sw.fetch_cme_alerts(now=NOW)) == 1
    sw.FEEDER_ALERTS_PATH.write_text(json.dumps(
        {"endpoints": {"alerts": {"_raw": {"_error": "down"}}}}))
    monkeypatch.setattr(sw, "communion_get_json", lambda *a, **k: [])
    assert sw.fetch_cme_alerts(now=NOW) == []


def test_kp_takes_newest_by_time_tag(sw, monkeypatch):
    rows = [{"time_tag": "2026-11-12T14:12:00", "kp_index": 5},
            {"time_tag": "2026-11-12T08:14:00", "kp_index": 1}]
    monkeypatch.setattr(sw, "communion_get_json", lambda *a, **k: rows)
    assert sw.fetch_kp_index() == 5.0


def test_fallback_url_is_the_live_products_feed(sw):
    assert sw.CME_FALLBACK_URL.endswith("/products/alerts.json")


def test_seat_runs_root_file_as_main():
    text = (REPO / "aureon/launch/daemons/sero_space_weather.py").read_text()
    assert "runpy.run_path" in text and 'run_name="__main__"' in text
    assert "checkout_daemons" not in text
