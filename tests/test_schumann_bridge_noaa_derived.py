from __future__ import annotations

from datetime import datetime, timezone

from aureon.harmonic import aureon_schumann_resonance_bridge as schumann


def test_schumann_bridge_uses_labelled_noaa_kp_derived_path(monkeypatch):
    class FakeSpaceWeatherBridge:
        def _fetch_kp_index(self):
            return {
                "current_kp": 4.0,
                "source_timestamp": datetime.now(timezone.utc).isoformat(),
            }

    monkeypatch.setattr(
        "aureon.data_feeds.aureon_space_weather_bridge.SpaceWeatherBridge",
        FakeSpaceWeatherBridge,
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

    bridge = schumann.SchumannResonanceBridge()
    reading = bridge.get_live_data(force_refresh=True)

    assert reading.active_sources == ["NOAA-Kp-Derived"]
    assert 7.7 < reading.fundamental_hz < 8.0
    assert 0.0 <= reading.earth_disturbance_level <= 1.0
