"""A gap in a NOAA feed must not read as a calm 0 in solar_system_collector.
Missing core fields mean no reading (None); optional fields stay None.
Parsers are called directly on hand-made rows, so no network."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _collector(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    spec = importlib.util.spec_from_file_location("_ssc_nozero", ROOT / "solar_system_collector.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.DATA_DIR = tmp_path / "solar_system_data"
    c = mod.SolarSystemCollector.__new__(mod.SolarSystemCollector)
    return c


def test_missing_f107_is_no_reading(tmp_path, monkeypatch):
    c = _collector(tmp_path, monkeypatch)
    assert c._parse_sunspot_cycle([{"ssn": 120, "time_tag": "2026-11"}]) is None


def test_missing_ssn_stays_none(tmp_path, monkeypatch):
    c = _collector(tmp_path, monkeypatch)
    r = c._parse_sunspot_cycle([{"f10.7": 150.0, "time_tag": "2026-11"}])
    assert r["sunspot_number"] is None and r["f10.7_flux"] == 150.0
    assert r["cycle_phase"] == "unknown"


def test_missing_wind_speed_is_no_reading(tmp_path, monkeypatch):
    c = _collector(tmp_path, monkeypatch)
    assert c._parse_solar_wind([{"proton_density": 5.0}]) is None
    r = c._parse_solar_wind([{"proton_speed": 420.0, "proton_density": 5.0}])
    assert r["speed"] == 420.0 and r["temperature"] is None


def test_missing_bz_is_no_reading(tmp_path, monkeypatch):
    c = _collector(tmp_path, monkeypatch)
    assert c._parse_mag_field([{"bt": 6.0}], 400.0) is None
    r = c._parse_mag_field([{"bt": 6.0, "bz_gsm": -4.0}], 400.0)
    assert r["bz"] == -4.0 and r["by"] is None and r["clock_angle"] is None


def test_real_zero_is_kept(tmp_path, monkeypatch):
    c = _collector(tmp_path, monkeypatch)
    r = c._parse_mag_field([{"bt": 5.0, "bz_gsm": 0.0, "by_gsm": 0.0, "bx_gsm": 0.0}], 400.0)
    assert r["bz"] == 0.0 and r["bx"] == 0.0
