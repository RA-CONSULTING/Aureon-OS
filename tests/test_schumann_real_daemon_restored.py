"""The restored Sero Schumann daemon writes only measured, provider-live readings."""

import importlib.util
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

# Shape of the real ResonanceOne /api/now response on 12 Nov 2026 while the
# Tomsk feed was paused: a 7.83 placeholder with schumann_unavailable = true.
PAUSED = {
    "activity_index": None, "activity_index_label": None,
    "schumann_frequency_hz": 7.83, "kp_index": 1, "solar_flare_class": "C4.9",
    "geomagnetic_status": "quiet", "schumann_unavailable": True,
    "last_schumann_at": "2026-11-07T19:00:27.030312+00:00", "data_quality": "stale",
}


def _load(tmp_path, monkeypatch):
    monkeypatch.setenv("SERO_WORKSPACE", str(tmp_path))
    sys.modules.pop("aureon_fusion.paths", None)
    spec = importlib.util.spec_from_file_location("srd_under_test", REPO / "schumann_real_daemon.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    sys.modules.pop("aureon_fusion.paths", None)
    return mod


def test_paths_and_no_orders(tmp_path, monkeypatch):
    mod = _load(tmp_path, monkeypatch)
    assert mod.STATE_FILE == tmp_path / "schumann_state.json"
    text = (REPO / "schumann_real_daemon.py").read_text(encoding="utf-8")
    assert "checkout_daemons" not in text and "resonanceone.app/api/now" in text
    for word in ("place_order", "create_order", "close_position", "random"):
        assert word not in text


def test_provider_placeholder_is_not_written_as_real(tmp_path, monkeypatch):
    mod = _load(tmp_path, monkeypatch)
    state, why = mod.build_state(PAUSED)
    assert state is None and "unavailable" in why
    stale_only = dict(PAUSED, schumann_unavailable=False)
    state, why = mod.build_state(stale_only)
    assert state is None and "stale" in why


def test_missing_frequency_is_refused(tmp_path, monkeypatch):
    mod = _load(tmp_path, monkeypatch)
    for bad in ({}, {"schumann_frequency_hz": None}, {"schumann_frequency_hz": 0}, {"schumann_frequency_hz": True}, []):
        assert mod.build_state(bad)[0] is None


def test_live_reading_kept_and_missing_fields_stay_none(tmp_path, monkeypatch):
    mod = _load(tmp_path, monkeypatch)
    live = {"schumann_frequency_hz": 7.91, "schumann_unavailable": False, "data_quality": "live",
            "last_schumann_at": "2026-11-12T12:00:00+00:00"}
    state, why = mod.build_state(live)
    assert why is None
    assert state["frequency_hz"] == 7.91 and state["real_data"] is True
    assert state["activity_index"] is None and state["kp_index"] is None
    assert state["solar_flare_class"] is None
    assert state["observed_at"] == "2026-11-12T12:00:00+00:00"
    json.dumps(state)


def test_launcher_seat_delegates_to_real_module():
    text = (REPO / "aureon" / "launch" / "daemons" / "schumann_real_daemon.py").read_text(encoding="utf-8")
    assert '"schumann_real_daemon.py"' in text and "_load_real().main()" in text
    assert "checkout_daemons" not in text
