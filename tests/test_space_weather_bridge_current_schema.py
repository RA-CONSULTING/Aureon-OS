from __future__ import annotations

from datetime import datetime, timezone
from email.utils import format_datetime

from aureon.data_feeds import aureon_space_weather_bridge as sw


class FakeResponse:
    def __init__(self, payload, *, provider_time=None):
        self._payload = payload
        self.headers = {}
        if provider_time is not None:
            self.headers["Date"] = format_datetime(provider_time, usegmt=True)

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def test_space_weather_bridge_parses_current_swpc_kp_schema(monkeypatch):
    bridge = sw.SpaceWeatherBridge()
    provider_time = datetime.now(timezone.utc).replace(microsecond=0)

    monkeypatch.setattr(
        sw.requests,
        "get",
        lambda *args, **kwargs: FakeResponse(
            [{"time_tag": provider_time.isoformat(), "Kp": 3.67}]
        ),
    )

    assert bridge._fetch_kp_index() == {
        "current_kp": 3.67,
        "source_timestamp": provider_time.isoformat(),
    }


def test_space_weather_bridge_parses_current_swpc_wind_and_mag_schema(monkeypatch):
    bridge = sw.SpaceWeatherBridge()
    provider_time = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    def fake_get(url, *args, **kwargs):
        if "rtsw_wind" in url:
            return FakeResponse(
                [
                    {
                        "time_tag": provider_time,
                        "proton_speed": 423.51,
                        "proton_density": 2.64,
                    }
                ]
            )
        if "rtsw_mag" in url:
            return FakeResponse(
                [{"time_tag": provider_time, "bz_gsm": 2.15}]
            )
        raise AssertionError(url)

    monkeypatch.setattr(sw.requests, "get", fake_get)

    assert bridge._fetch_solar_wind() == {
        "density": 2.64,
        "speed": 423.51,
        "bz": 2.15,
        "source_timestamp": provider_time,
    }


def test_space_weather_bridge_parses_current_swpc_forecast_schema(monkeypatch):
    bridge = sw.SpaceWeatherBridge()
    provider_time = datetime.now(timezone.utc).replace(microsecond=0)

    monkeypatch.setattr(
        sw.requests,
        "get",
        lambda *args, **kwargs: FakeResponse(
            [
                {"time_tag": "2026-07-14T00:00:00", "kp": 1.67},
                {"time_tag": "2026-07-14T03:00:00", "kp": 5.0},
            ],
            provider_time=provider_time,
        ),
    )

    assert bridge._fetch_3day_forecast() == {
        "highest_kp_category": "Active",
        "source_timestamp": format_datetime(provider_time, usegmt=True),
    }


def test_space_weather_forecast_without_provider_issue_time_is_no_data(monkeypatch):
    bridge = sw.SpaceWeatherBridge()
    monkeypatch.setattr(
        sw.requests,
        "get",
        lambda *args, **kwargs: FakeResponse(
            [{"time_tag": "2099-01-01T00:00:00Z", "kp": 9.0}]
        ),
    )

    assert bridge._fetch_3day_forecast() is None
