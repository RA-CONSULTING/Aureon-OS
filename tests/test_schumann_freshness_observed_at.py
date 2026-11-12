"""Schumann freshness is two checks: daemon alive and reading recent.

The write timestamp must sit inside the reader's existing window
(600 / 300 / 300 / 120 / 300 s). If observed_at is present it must parse
and be at most SCHUMANN_OBSERVED_MAX_AGE_SEC (default 7200 s) old —
Tomsk publishes hourly, so a live reading is often 1–2 hours old. A
present observed_at without a write timestamp is refused. Ages more
than 60 s in the future are refused. Files with no observed_at still
age by the write timestamp.
Time is frozen with monkeypatch; no network and no randomness.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

NOW = datetime(2026, 11, 12, 14, 0, 0, tzinfo=timezone.utc)
OLD = NOW - timedelta(days=5)
STALE_WRITE = NOW - timedelta(hours=1)  # 3600 s, past every write window
FRESH = NOW - timedelta(seconds=30)
JUST_WRITTEN = NOW
OBS_70MIN = NOW - timedelta(minutes=70)  # 4200 s: inside 7200, outside 600
OBS_3H = NOW - timedelta(hours=3)  # 10800 s, past the 7200 s cap
OBS_FUTURE = NOW + timedelta(minutes=10)
WRITE_FUTURE = NOW + timedelta(minutes=10)


def _freeze_datetime(monkeypatch, module):
    if getattr(module, "datetime", None) is None:
        return

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


def _freeze_readers(monkeypatch):
    import aureon_radar.planetary_switchboard as ps
    from aureon_fusion import heartbeat_exec as hb
    import aureon_radar.harmonic.live_field_coherence as lfc

    try:
        import aureon_fusion.schumann_freshness as sf
    except ImportError:
        sf = None
    if sf is not None:
        _freeze_datetime(monkeypatch, sf)
    _freeze_datetime(monkeypatch, ps)
    _freeze_datetime(monkeypatch, hb)
    _freeze_datetime(monkeypatch, lfc)
    return ps, hb, lfc


def _switchboard(tmp_path, monkeypatch, **overrides):
    import aureon_radar.planetary_switchboard as ps

    path = _write(tmp_path / "schumann_state.json", **overrides)
    monkeypatch.setenv("AUREON_SCHUMANN_STATE", str(path))
    monkeypatch.delenv("AUREON_ALLOW_SIM_FALLBACK", raising=False)
    _freeze_readers(monkeypatch)
    return ps.SchumannFeed().get_schumann()


def _heartbeat_cache(tmp_path, monkeypatch, **overrides):
    from aureon_fusion import heartbeat_exec as hb

    path = _write(tmp_path / "schumann_state.json", **overrides)
    monkeypatch.setattr(hb, "SCHUMANN_STATE", path)
    monkeypatch.delenv("AUREON_ALLOW_SIM_FALLBACK", raising=False)
    _freeze_readers(monkeypatch)
    return hb._load_schumann_cache()


def _live_field(tmp_path, monkeypatch, **overrides):
    import aureon_radar.harmonic.live_field_coherence as lfc

    path = _write(tmp_path / "schumann_state.json", **overrides)
    _freeze_readers(monkeypatch)
    if hasattr(lfc, "_read_schumann_state"):
        return lfc._read_schumann_state(str(path), lfc._SCHUMANN_MAX_AGE)
    # main ages this file by mtime via _read_json, not observed_at.
    return lfc._read_json(str(path), lfc._SCHUMANN_MAX_AGE)


def _all_readers(tmp_path, monkeypatch, **overrides):
    return (
        _switchboard(tmp_path, monkeypatch, **overrides),
        _heartbeat_cache(tmp_path, monkeypatch, **overrides),
        _live_field(tmp_path, monkeypatch, **overrides),
    )


def test_live_shaped_70min_observed_at_is_accepted(tmp_path, monkeypatch):
    sch, cache, field = _all_readers(
        tmp_path, monkeypatch,
        timestamp=JUST_WRITTEN.isoformat(),
        observed_at=OBS_70MIN.isoformat(),
    )
    assert sch is not None
    assert sch.fundamental_hz == 7.91
    assert cache is not None
    assert cache["frequency_hz"] == 7.91
    assert field is not None
    assert field["frequency_hz"] == 7.91


def test_observed_at_three_hours_old_is_refused(tmp_path, monkeypatch):
    sch, cache, field = _all_readers(
        tmp_path, monkeypatch,
        timestamp=FRESH.isoformat(),
        observed_at=OBS_3H.isoformat(),
    )
    assert sch is None
    assert cache is None
    assert field is None


def test_observed_at_ten_minutes_in_the_future_is_refused(tmp_path, monkeypatch):
    sch, cache, field = _all_readers(
        tmp_path, monkeypatch,
        timestamp=JUST_WRITTEN.isoformat(),
        observed_at=OBS_FUTURE.isoformat(),
    )
    assert sch is None
    assert cache is None
    assert field is None


def test_timestamp_in_the_future_is_refused(tmp_path, monkeypatch):
    sch, cache, field = _all_readers(
        tmp_path, monkeypatch,
        timestamp=WRITE_FUTURE.isoformat(),
        observed_at=OBS_70MIN.isoformat(),
    )
    assert sch is None
    assert cache is None
    assert field is None
    sch, cache, field = _all_readers(
        tmp_path, monkeypatch,
        timestamp=WRITE_FUTURE.isoformat(),
    )
    assert sch is None
    assert cache is None
    assert field is None


def test_fresh_observed_at_with_stale_timestamp_is_refused(tmp_path, monkeypatch):
    sch, cache, field = _all_readers(
        tmp_path, monkeypatch,
        timestamp=STALE_WRITE.isoformat(),
        observed_at=FRESH.isoformat(),
    )
    assert sch is None
    assert cache is None
    assert field is None


def test_written_now_with_old_observed_at_is_refused(tmp_path, monkeypatch):
    # Days-old observed_at is well past the 7200 s cap even if the
    # daemon just wrote the file. Fails on main, which ages by write time.
    sch, cache, field = _all_readers(
        tmp_path, monkeypatch,
        timestamp=NOW.isoformat(),
        observed_at=OLD.isoformat(),
    )
    assert sch is None
    assert cache is None
    assert field is None


def test_missing_observed_at_falls_back_to_timestamp(tmp_path, monkeypatch):
    sch, cache, field = _all_readers(
        tmp_path, monkeypatch, timestamp=FRESH.isoformat(),
    )
    assert sch is not None
    assert sch.fundamental_hz == 7.91
    assert cache is not None
    assert cache["frequency_hz"] == 7.91
    assert field is not None
    sch, cache, field = _all_readers(
        tmp_path, monkeypatch, timestamp=OLD.isoformat(),
    )
    assert sch is None
    assert cache is None
    assert field is None


def test_heartbeat_cache_refuses_stale(tmp_path, monkeypatch):
    assert _heartbeat_cache(tmp_path, monkeypatch, timestamp=NOW.isoformat(),
                            observed_at=OLD.isoformat()) is None
    assert _heartbeat_cache(tmp_path, monkeypatch, timestamp=OLD.isoformat()) is None
    assert _heartbeat_cache(tmp_path, monkeypatch, timestamp=FRESH.isoformat()) is not None


def test_unparseable_observed_at_fails_closed(tmp_path, monkeypatch):
    sch, cache, field = _all_readers(
        tmp_path, monkeypatch,
        timestamp=FRESH.isoformat(),
        observed_at="not-a-clock",
    )
    assert sch is None
    assert cache is None
    assert field is None


def test_observed_at_without_write_timestamp_is_refused(tmp_path, monkeypatch):
    sch, cache, field = _all_readers(
        tmp_path, monkeypatch,
        timestamp="",
        observed_at=OBS_70MIN.isoformat(),
    )
    assert sch is None
    assert cache is None
    assert field is None
