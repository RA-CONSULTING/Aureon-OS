"""Non-finite Schumann freshness limits fail closed.

A nan/inf AUREON_SCHUMANN_OBSERVED_MAX_AGE_SEC falls back to 7200 s, and a
nan/inf/non-positive write window refuses the reading. No network.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from aureon_fusion import schumann_freshness as sf

NOW = datetime(2026, 11, 12, 14, 0, tzinfo=timezone.utc)


def _state(observed_age_s, write_age_s=30):
    return {
        "timestamp": (NOW - timedelta(seconds=write_age_s)).isoformat(),
        "observed_at": (NOW - timedelta(seconds=observed_age_s)).isoformat(),
        "real_data": True,
    }


@pytest.mark.parametrize("raw", ["nan", "NaN", "inf", "-inf", "Infinity"])
def test_nonfinite_env_falls_back_to_default(monkeypatch, raw):
    monkeypatch.setenv(sf.ENV_SCHUMANN_OBSERVED_MAX_AGE_SEC, raw)
    assert sf.schumann_observed_max_age_sec() == sf.SCHUMANN_OBSERVED_MAX_AGE_SEC


@pytest.mark.parametrize("raw", ["nan", "inf"])
def test_nonfinite_env_still_refuses_30_day_old_reading(monkeypatch, raw):
    monkeypatch.setenv(sf.ENV_SCHUMANN_OBSERVED_MAX_AGE_SEC, raw)
    result = sf.evaluate_schumann_freshness(_state(30 * 86400), 300, NOW)
    assert result.accepted is False


def test_live_shaped_70_minute_reading_still_accepted(monkeypatch):
    monkeypatch.delenv(sf.ENV_SCHUMANN_OBSERVED_MAX_AGE_SEC, raising=False)
    assert sf.evaluate_schumann_freshness(_state(70 * 60), 300, NOW).accepted is True


@pytest.mark.parametrize("window", [float("nan"), float("inf"), 0, -5, None, "x"])
def test_bad_write_window_fails_closed(monkeypatch, window):
    monkeypatch.delenv(sf.ENV_SCHUMANN_OBSERVED_MAX_AGE_SEC, raising=False)
    result = sf.evaluate_schumann_freshness(_state(60), window, NOW)
    assert result.accepted is False
    assert "invalid write window" in result.reason


def test_bad_write_window_without_observed_at_fails_closed():
    data = {"timestamp": (NOW - timedelta(days=30)).isoformat(), "real_data": True}
    assert sf.evaluate_schumann_freshness(data, float("nan"), NOW).accepted is False
