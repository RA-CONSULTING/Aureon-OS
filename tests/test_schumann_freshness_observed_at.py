"""schumann_state.json must be judged fresh by when Tomsk measured it.

A file written just now with an observed_at days old is stale. A fresh
observed_at is accepted even if the write timestamp is old. If
observed_at is absent, freshness falls back to timestamp. The heartbeat
cache never serves a stale file as the current field.
Time is frozen with monkeypatch; no network and no randomness.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

NOW = datetime(2026, 11, 12, 14, 0, 0, tzinfo=timezone.utc)
OLD = NOW - timedelta(days=5)
FRESH = NOW - timedelta(seconds=30)


def _freeze_datetime(monkeypatch, module):
    class FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return NOW if tz is None else NOW.astimezone(tz)

    monkeypatch.setattr(module, "datetime", FrozenDateTime)


def _payload(**overrides):
    data = {
        "timestamp": NOW.isoformat(),
        "frequency_hz": 7.91,
        "activity_index": 20,
        "activity_label": "quiet",
        "kp_index": 1,
        "geomagnetic_status": "quiet",
        "real_data": True,
        "simulation": False,
        "source": "resonanceone_tomsk",
    }
    data.update(overrides)
    return data


def _write(path: Path, **overrides) -> Path:
    path.write_text(json.dumps(_payload(**overrides)), encoding="utf-8")
    return path


def _switchboard(tmp_path, monkeypatch, **overrides):
    import aureon_radar.planetary_switchboard as ps

    path = _write(tmp_path / "schumann_state.json", **overrides)
    monkeypatch.setenv("AUREON_SCHUMANN_STATE", str(path))
    monkeypatch.delenv("AUREON_ALLOW_SIM_FALLBACK", raising=False)
    _freeze_datetime(monkeypatch, ps)
    return ps.SchumannFeed().get_schumann()


def _heartbeat_cache(tmp_path, monkeypatch, **overrides):
    from aureon_fusion import heartbeat_exec as hb

    path = _write(tmp_path / "schumann_state.json", **overrides)
    monkeypatch.setattr(hb, "SCHUMANN_STATE", path)
    monkeypatch.delenv("AUREON_ALLOW_SIM_FALLBACK", raising=False)
    _freeze_datetime(monkeypatch, hb)
    return hb._load_schumann_cache()


def test_written_now_with_old_observed_at_is_refused(tmp_path, monkeypatch):
    assert _switchboard(tmp_path, monkeypatch, timestamp=NOW.isoformat(),
                        observed_at=OLD.isoformat()) is None
    assert _heartbeat_cache(tmp_path, monkeypatch, timestamp=NOW.isoformat(),
                            observed_at=OLD.isoformat()) is None


def test_fresh_observed_at_is_accepted(tmp_path, monkeypatch):
    sch = _switchboard(tmp_path, monkeypatch, timestamp=OLD.isoformat(),
                       observed_at=FRESH.isoformat())
    assert sch is not None
    assert sch.fundamental_hz == 7.91
    cache = _heartbeat_cache(tmp_path, monkeypatch, timestamp=OLD.isoformat(),
                             observed_at=FRESH.isoformat())
    assert cache is not None
    assert cache["frequency_hz"] == 7.91


def test_missing_observed_at_falls_back_to_timestamp(tmp_path, monkeypatch):
    sch = _switchboard(tmp_path, monkeypatch, timestamp=FRESH.isoformat())
    assert sch is not None
    assert sch.fundamental_hz == 7.91
    cache = _heartbeat_cache(tmp_path, monkeypatch, timestamp=FRESH.isoformat())
    assert cache is not None
    assert cache["frequency_hz"] == 7.91
    assert _switchboard(tmp_path, monkeypatch, timestamp=OLD.isoformat()) is None
    assert _heartbeat_cache(tmp_path, monkeypatch, timestamp=OLD.isoformat()) is None


def test_heartbeat_cache_refuses_stale(tmp_path, monkeypatch):
    assert _heartbeat_cache(tmp_path, monkeypatch, timestamp=NOW.isoformat(),
                            observed_at=OLD.isoformat()) is None
    assert _heartbeat_cache(tmp_path, monkeypatch, timestamp=OLD.isoformat()) is None
    assert _heartbeat_cache(tmp_path, monkeypatch, timestamp=FRESH.isoformat()) is not None


def test_unparseable_observed_at_fails_closed(tmp_path, monkeypatch):
    assert _switchboard(tmp_path, monkeypatch, timestamp=FRESH.isoformat(),
                        observed_at="not-a-clock") is None
    assert _heartbeat_cache(tmp_path, monkeypatch, timestamp=FRESH.isoformat(),
                            observed_at="not-a-clock") is None
