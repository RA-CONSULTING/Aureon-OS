from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

from aureon.core.hnc_live_daemon import _get_macro_snapshot_quietly
from aureon.harmonic import aureon_schumann_resonance_bridge as schumann


def test_macro_snapshot_suppresses_legacy_status_output(capsys):
    class MacroFeed:
        def get_snapshot(self):
            print("world status: \U0001f30d")
            return {"vix": 19.5}

    assert _get_macro_snapshot_quietly(MacroFeed()) == {"vix": 19.5}
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


def test_schumann_reuses_complete_shared_space_weather_reading(monkeypatch):
    source_timestamp = datetime.now(UTC).isoformat()

    class SharedBridge:
        calls = 0

        def get_live_data(self):
            type(self).calls += 1
            return SimpleNamespace(
                kp_index=4.0,
                active_sources=["NOAA-KP", "NOAA-SolarWind"],
                source_timestamps={"NOAA-KP": source_timestamp},
            )

    shared = SharedBridge()
    monkeypatch.setattr(
        "aureon.data_feeds.aureon_space_weather_bridge.SpaceWeatherBridge",
        SharedBridge,
    )
    monkeypatch.setattr(
        "aureon.data_feeds.aureon_space_weather_bridge.get_space_weather_bridge",
        lambda: shared,
    )
    monkeypatch.setattr(
        schumann.SchumannResonanceBridge,
        "_fetch_barcelona_data",
        lambda self: None,
    )
    monkeypatch.setattr(
        schumann.SchumannResonanceBridge,
        "_fetch_usgs_magnetometer",
        lambda self: None,
    )
    monkeypatch.setenv("AUREON_ALLOW_SIM_FALLBACK", "0")

    reading = schumann.SchumannResonanceBridge().get_live_data(force_refresh=True)

    assert SharedBridge.calls == 1
    assert reading.active_sources == ["NOAA-Kp-Derived"]
    assert reading.source_timestamp == source_timestamp
    assert 7.7 < reading.fundamental_hz < 8.0
