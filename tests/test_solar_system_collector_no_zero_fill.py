"""A missing provider field stays missing; it never becomes a calm 0 reading."""

import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def _collector(tmp_path, monkeypatch):
    monkeypatch.setenv("SERO_WORKSPACE", str(tmp_path))
    sys.modules.pop("aureon_fusion.paths", None)
    spec = importlib.util.spec_from_file_location("ssc_nozero", REPO / "solar_system_collector.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    sys.modules.pop("aureon_fusion.paths", None)
    return mod, mod.SolarSystemCollector()


def test_sunspot_missing_fields_are_none(tmp_path, monkeypatch):
    _, c = _collector(tmp_path, monkeypatch)
    r = c._parse_sunspot_cycle([{"time_tag": "2026-08", "ssn": 80}])
    assert r["sunspot_number"] == 80
    assert r["f10.7_flux"] is None
    assert r["activity_level"] is None and r["cycle_phase"] is None
    assert c._parse_sunspot_cycle([{"time_tag": "2026-08"}]) is None


def test_solar_wind_without_speed_is_no_reading(tmp_path, monkeypatch):
    _, c = _collector(tmp_path, monkeypatch)
    assert c._parse_solar_wind([{"time_tag": "t", "proton_density": 5}]) is None
    r = c._parse_solar_wind([{"time_tag": "t", "proton_speed": 420}])
    assert r["speed"] == 420
    assert r["density"] is None and r["temperature"] is None
    assert r["dynamic_pressure"] is None


def test_mag_field_missing_components_are_none(tmp_path, monkeypatch):
    _, c = _collector(tmp_path, monkeypatch)
    assert c._parse_mag_field([{"time_tag": "t", "bx_gsm": 1.0}], 400) is None
    r = c._parse_mag_field([{"time_tag": "t", "bt": 6.0}], 400)
    assert r["bt"] == 6.0
    assert r["bz"] is None and r["by"] is None and r["bx"] is None
    assert r["clock_angle"] is None and r["coupling_efficiency"] is None


def test_real_values_still_flow(tmp_path, monkeypatch):
    _, c = _collector(tmp_path, monkeypatch)
    wind = c._parse_solar_wind([{"time_tag": "t", "proton_speed": 650, "proton_density": 10, "proton_temperature": 1e5}])
    mag = c._parse_mag_field([{"time_tag": "t", "bx_gsm": 1, "by_gsm": -2, "bz_gsm": -12, "bt": 12.2}], wind["speed"])
    assert wind["regime"] == "high_speed_stream"
    assert abs(wind["dynamic_pressure"] - 10 * 650 ** 2 * 1.67e-6) < 1e-9
    assert mag["bz"] == -12.0 and mag["coupling_efficiency"] > 0
    health = c._calculate_health({"solar_wind": {"speed": None, "dynamic_pressure": None},
                                  "magnetic_field": {"bz": None}})
    assert health["concerns"] == []
    health = c._calculate_health({"solar_wind": {"speed": wind["speed"]}, "magnetic_field": {"bz": mag["bz"]}})
    assert len(health["concerns"]) == 2
