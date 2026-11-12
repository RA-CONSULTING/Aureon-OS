"""The restored Sero soul protection daemon is the real one, and the launcher seat runs it."""

import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def _load(tmp_path, monkeypatch):
    monkeypatch.setenv("SERO_WORKSPACE", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    sys.modules.pop("aureon_fusion.paths", None)
    spec = importlib.util.spec_from_file_location("spd_under_test", REPO / "soul_protection_daemon.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    sys.modules.pop("aureon_fusion.paths", None)
    return mod


def test_real_module_replaces_placeholder(tmp_path, monkeypatch):
    mod = _load(tmp_path, monkeypatch)
    assert (tmp_path / "soul_shield_logs").is_dir()
    assert mod.LOG_DIR == tmp_path / "soul_shield_logs"
    assert mod.PID_FILE == tmp_path / "soul_protection.pid"
    assert mod.SHIELD_STATS_FILE == tmp_path / "queen_shield_stats.json"
    text = (REPO / "soul_protection_daemon.py").read_text(encoding="utf-8")
    assert "checkout_daemons" not in text
    assert "SoulProtectionDaemon" in text
    for word in ("place_order", "create_order", "close_position"):
        assert word not in text


def test_hostile_injection_comes_from_the_log_payload(tmp_path, monkeypatch):
    mod = _load(tmp_path, monkeypatch)
    (tmp_path / "hnc_superposition.out").write_text(
        "idle field line\nphoton emission E=440.0\n",
        encoding="utf-8",
    )
    reading = mod.SoulProtectionDaemon()._detect_hostile_injection()
    assert reading["frequency"] == 440.0
    assert reading["hostile_freq"] == 440.0
    assert reading["name"] == "440 Hz Parasite"
    assert reading["source"] == "hnc_field_injection"
    assert reading["line"] == "photon emission E=440.0"


def test_feed_failure_is_reported_not_invented(tmp_path, monkeypatch):
    mod = _load(tmp_path, monkeypatch)
    daemon = mod.SoulProtectionDaemon()
    assert not (tmp_path / "hnc_superposition.out").exists()
    assert daemon._detect_hostile_injection() is None
    (tmp_path / "hnc_superposition.out").write_text("no frequency field here\n", encoding="utf-8")
    assert daemon._detect_hostile_injection() is None
    attack_logs = list((tmp_path / "soul_shield_logs").glob("attacks_*.jsonl"))
    assert attack_logs == []


def test_launcher_seat_delegates_to_real_module():
    text = (REPO / "aureon" / "launch" / "daemons" / "soul_protection_daemon.py").read_text(encoding="utf-8")
    assert '"soul_protection_daemon.py"' in text and "_load_real().main()" in text
    assert "checkout_daemons" not in text
