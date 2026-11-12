"""The restored Sero planetary monitor is the real one, and the launcher seat runs it."""

import importlib.util
import signal
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def _load(tmp_path, monkeypatch):
    monkeypatch.setenv("SERO_WORKSPACE", str(tmp_path))
    sys.modules.pop("aureon_fusion.paths", None)
    old_int = signal.getsignal(signal.SIGINT)
    old_term = signal.getsignal(signal.SIGTERM)
    try:
        spec = importlib.util.spec_from_file_location("pmd_under_test", REPO / "planetary_monitor_daemon.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    finally:
        signal.signal(signal.SIGINT, old_int)
        signal.signal(signal.SIGTERM, old_term)
        sys.modules.pop("aureon_fusion.paths", None)
    return mod


def test_real_module_replaces_placeholder(tmp_path, monkeypatch):
    mod = _load(tmp_path, monkeypatch)
    assert (tmp_path / "planetary_monitor").is_dir()
    assert mod.DATA_DIR == str(tmp_path / "planetary_monitor")
    text = (REPO / "planetary_monitor_daemon.py").read_text(encoding="utf-8")
    assert "checkout_daemons" not in text
    assert "services.swpc.noaa.gov" in text
    for word in ("place_order", "create_order", "close_position"):
        assert word not in text


def test_kp_reading_comes_from_the_noaa_payload(tmp_path, monkeypatch):
    mod = _load(tmp_path, monkeypatch)
    payload = [
        {"time_tag": "2026-11-12 09:00:00", "kp": 3.33, "observed": "observed", "noaa_scale": None},
        {"time_tag": "2026-11-12 12:00:00", "kp": 4.0, "observed": "predicted", "noaa_scale": None},
    ]
    monkeypatch.setattr(mod, "communion_get_json", lambda url, **kw: payload)
    reading = mod.fetch_noaa_kp()
    assert reading["kp"] == 3.33 and reading["status"] == "observed"
    assert reading["time_tag"] == "2026-11-12 09:00:00"


def test_feed_failure_is_reported_not_invented(tmp_path, monkeypatch):
    mod = _load(tmp_path, monkeypatch)

    def boom(url, **kw):
        raise OSError("offline")

    monkeypatch.setattr(mod, "communion_get_json", boom)
    reading = mod.fetch_noaa_kp()
    assert "error" in reading and "kp" not in reading


def test_launcher_seat_delegates_to_real_module():
    text = (REPO / "aureon" / "launch" / "daemons" / "planetary_monitor_daemon.py").read_text(encoding="utf-8")
    assert '"planetary_monitor_daemon.py"' in text and "_load_real().main()" in text
    assert "checkout_daemons" not in text
