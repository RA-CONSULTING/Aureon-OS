"""Missing soul readings must be no data, not a healthy stand-in.

_scan_soul_state no longer fills GARY_SIGNATURE / coherence 1.0 / phase_lock
True / distortion 0.0 when a field is missing or the reader fails. The
constructor does not seed those healthy values. QueenSoulReader clock maths
such as sin(time.time()/3600) run only behind the dev simulation gate, and
even then the reading is not marked live.
No network and no randomness.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def _load_daemon(tmp_path, monkeypatch):
    monkeypatch.setenv("SERO_WORKSPACE", str(tmp_path))
    monkeypatch.delenv("AUREON_ALLOW_SIM_FALLBACK", raising=False)
    monkeypatch.chdir(tmp_path)
    sys.modules.pop("aureon_fusion.paths", None)
    spec = importlib.util.spec_from_file_location("spd_no_standin", REPO / "soul_protection_daemon.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    sys.modules.pop("aureon_fusion.paths", None)
    return mod


def test_missing_key_is_none(tmp_path, monkeypatch):
    mod = _load_daemon(tmp_path, monkeypatch)
    daemon = mod.SoulProtectionDaemon()

    class Reader:
        def read_soul(self):
            return {"coherence": 0.4}

    daemon._soul_reader = Reader()
    soul = daemon._scan_soul_state()
    assert soul["coherence"] == 0.4
    assert soul["frequency"] is None
    assert soul["phase_lock"] is None
    assert soul["distortion"] is None
    assert soul["status"] == "partial"
    assert soul["error"] is None


def test_exception_is_no_reading_not_healthy(tmp_path, monkeypatch):
    mod = _load_daemon(tmp_path, monkeypatch)
    daemon = mod.SoulProtectionDaemon()

    class Reader:
        def read_soul(self):
            raise OSError("offline")

    daemon._soul_reader = Reader()
    soul = daemon._scan_soul_state()
    assert soul["frequency"] is None
    assert soul["coherence"] is None
    assert soul["phase_lock"] is None
    assert soul["distortion"] is None
    assert soul["status"] == "no_reading"
    assert "OSError" in soul["error"] and "offline" in soul["error"]
    assert soul["coherence"] != 1.0
    assert soul["phase_lock"] is not True


def test_constructor_does_not_seed_healthy_values(tmp_path, monkeypatch):
    mod = _load_daemon(tmp_path, monkeypatch)
    daemon = mod.SoulProtectionDaemon()
    state = daemon.soul_state
    assert state["frequency"] is None
    assert state["coherence"] is None
    assert state["phase_lock"] is None
    assert state["distortion"] is None
    assert state["status"] == "no_reading"
    assert state["frequency"] != 528.422
    assert state["coherence"] != 1.0
    assert state["phase_lock"] is not True


def test_reader_clock_values_gated_off_by_default(monkeypatch):
    monkeypatch.delenv("AUREON_ALLOW_SIM_FALLBACK", raising=False)
    from aureon.queen.queen_soul_reader import QueenSoulReader

    reader = QueenSoulReader()
    schumann = reader._read_schumann_alignment()
    assert schumann["current_schumann"] is None
    assert schumann["phase_lock"] is None
    assert schumann["status"] == "no_reading"
    assert schumann.get("is_live") is not True

    reading = reader.read_soul()
    assert reading["schumann"]["phase_lock"] is None
    assert reading["soul"]["coherence"] is None
    assert reading["queen_verdict"]["queen_message"]
    assert "no reading" in reading["queen_verdict"]["queen_message"].lower() or any(
        "no reading" in str(item).lower() for item in reading["queen_verdict"]["verdicts"]
    )


def test_dev_clock_values_are_not_marked_live(monkeypatch):
    monkeypatch.setenv("AUREON_ALLOW_SIM_FALLBACK", "1")
    from aureon.queen.queen_soul_reader import QueenSoulReader

    reader = QueenSoulReader()
    schumann = reader._read_schumann_alignment()
    assert schumann["phase_lock"] is not None
    assert schumann.get("is_live") is False


def test_shield_total_blocks_missing_is_none_real_zero_kept(tmp_path, monkeypatch):
    mod = _load_daemon(tmp_path, monkeypatch)
    assert mod._load_shield_total_blocks(None) is None
    mod.SHIELD_STATS_FILE.write_text(json.dumps({"other": 1}), encoding="utf-8")
    assert mod._load_shield_total_blocks(None) is None
    mod.SHIELD_STATS_FILE.write_text(json.dumps({"total_blocks": 0}), encoding="utf-8")
    assert mod._load_shield_total_blocks(None) == 0
    mod.SHIELD_STATS_FILE.write_text(json.dumps({"total_blocks": 12}), encoding="utf-8")
    assert mod._load_shield_total_blocks(None) == 12
    mod.SHIELD_STATS_FILE.write_text("{", encoding="utf-8")
    assert mod._load_shield_total_blocks(None) is None


def test_none_coherence_formats_without_crashing(tmp_path, monkeypatch):
    mod = _load_daemon(tmp_path, monkeypatch)
    assert mod._format_optional_ratio(None, ".1%") == "no_reading"
    assert mod._format_optional_ratio(0.4, ".1%") == "40.0%"
    daemon = mod.SoulProtectionDaemon()
    daemon._last_summary = 0.0
    daemon._scan_soul_state = lambda: {
        "frequency": None,
        "coherence": None,
        "phase_lock": None,
        "distortion": None,
        "status": "no_reading",
        "error": None,
    }
    daemon._detect_hostile_injection = lambda: None
    daemon._validate_timeline_anchor = lambda: {"anchor_valid": False, "warning": "unvalidated"}
    daemon._protection_cycle()
