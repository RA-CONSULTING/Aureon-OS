"""The restored Sero solar system collector is the real one, and the launcher seat runs it."""

import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def _load(tmp_path, monkeypatch):
    monkeypatch.setenv("SERO_WORKSPACE", str(tmp_path))
    sys.modules.pop("aureon_fusion.paths", None)
    spec = importlib.util.spec_from_file_location("ssc_under_test", REPO / "solar_system_collector.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    sys.modules.pop("aureon_fusion.paths", None)
    return mod


def test_real_module_replaces_placeholder(tmp_path, monkeypatch):
    mod = _load(tmp_path, monkeypatch)
    collector = mod.SolarSystemCollector()
    assert (tmp_path / "solar_system_data").is_dir()
    assert mod.DATA_DIR == tmp_path / "solar_system_data"
    text = (REPO / "solar_system_collector.py").read_text(encoding="utf-8")
    assert "checkout_daemons" not in text
    assert "services.swpc.noaa.gov" in text
    for word in ("place_order", "create_order", "close_position"):
        assert word not in text
    assert collector.data_dir == mod.DATA_DIR


def test_sunspot_reading_comes_from_the_payload(tmp_path, monkeypatch):
    mod = _load(tmp_path, monkeypatch)
    payload = [
        {"time_tag": "2026-07", "ssn": 40, "f10.7": 90, "smoothed_ssn": 50},
        {"time_tag": "2026-08", "ssn": 80, "f10.7": 120, "smoothed_ssn": 90},
    ]
    reading = mod.SolarSystemCollector()._parse_sunspot_cycle(payload)
    assert reading["sunspot_number"] == 80
    assert reading["f10.7_flux"] == 120
    assert reading["smoothed_ssn"] == 90
    assert reading["time_tag"] == "2026-08"
    assert reading["cycle_phase"] == "approaching_max"
    assert reading["activity_level"] == "moderate"


def test_feed_failure_is_reported_not_invented(tmp_path, monkeypatch):
    mod = _load(tmp_path, monkeypatch)

    def boom(url, **kw):
        raise OSError("offline")

    monkeypatch.setattr(mod, "communion_get_json", boom)
    collector = mod.SolarSystemCollector()
    state = collector.collect()
    assert state is None
    assert collector.get_latest() is None
    assert not mod.STATE_FILE.exists()
    assert not mod.TIMESERIES_FILE.exists()


def test_launcher_seat_delegates_to_real_module():
    text = (REPO / "aureon" / "launch" / "daemons" / "solar_system_collector.py").read_text(encoding="utf-8")
    assert '"solar_system_collector.py"' in text and "runpy.run_path" in text
    assert "_REAL" in text and 'run_name="__main__"' in text
    assert "checkout_daemons" not in text
