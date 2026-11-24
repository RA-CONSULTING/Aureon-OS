"""The live HNC daemon publishes real Lambda(t) under import suppression.

Guarded files:
- aureon/core/hnc_live_daemon.py
- aureon/core/aureon_lambda_engine.py


The organ registry (``aureon_fusion/organ_registry.py``) pins
``AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS=1`` on the ``hnc_live_daemon`` organ
via ``_launch_env``. ``aureon/launch/master.py`` ``child_env`` copies that
spec onto the child. ``aureon_radar/master_launcher.py`` does not launch
this organ, and the daemon does not set the flag itself. A normal organ
start therefore arrives with import suppression already set. The same
helper used to pin ``AUREON_AUDIT_MODE=1`` as well, which made every
shared-history commit roll back and every trace row ``no_data``.

Audit mode still writes nothing. A missing history is ``no_data``, never
``lambda_t`` 0.0. A real 0.0 stays 0.0.
"""

from __future__ import annotations

import asyncio
import importlib
import json
import logging
import math
import os
import time
from pathlib import Path
from unittest import mock

import pytest

from aureon.core import aureon_lambda_engine as lambda_module
from aureon.core.aureon_lambda_engine import LambdaEngine, SubsystemReading
from aureon.core.hnc_live_daemon import (
    HNCLiveDaemon,
    SourceReceipt,
    SourceState,
    _finite_reading,
)

NOW = 1_786_400_000.0
SUPPRESS = "AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS"
AUDIT = "AUREON_AUDIT_MODE"


def _identity(path: Path):
    if not path.exists():
        return None
    stat = path.stat()
    return (stat.st_size, stat.st_mtime_ns)


@pytest.fixture(autouse=True)
def _repo_lambda_history_untouched():
    path = Path(lambda_module.DEFAULT_HISTORY_STATE_PATH)
    before = _identity(path)
    yield
    assert _identity(path) == before


def _receipt(name: str) -> SourceReceipt:
    return SourceReceipt(
        source_id=f"provider.{name}",
        source_timestamp=NOW - 2.0,
        received_at=NOW - 1.0,
        receipt_id=f"provider:{name}:receipt-1",
        receipt_type="provider_measurement",
        truth_status="real_observed",
        generated_values=False,
    )


def _source(name: str, value: float, *, source_timestamp: float) -> SourceState:
    receipt = _receipt(name)
    receipt = SourceReceipt(
        source_id=receipt.source_id,
        source_timestamp=source_timestamp,
        received_at=receipt.received_at,
        receipt_id=receipt.receipt_id,
        receipt_type=receipt.receipt_type,
        truth_status=receipt.truth_status,
        generated_values=False,
    )
    return SourceState(
        name=name,
        interval_s=5.0,
        last_reading=SubsystemReading(
            name=name, value=value, confidence=0.8, state="live",
        ),
        last_receipt=receipt,
        last_fetch_ts=receipt.received_at,
        max_age_s=120.0,
    )


def _daemon(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    sources: bool,
    live: bool,
    audit: bool,
) -> tuple[HNCLiveDaemon, Path, Path]:
    state_path = tmp_path / "lambda_history.json"
    trace_path = tmp_path / "hnc_live_trace.jsonl"
    monkeypatch.setattr(lambda_module, "DEFAULT_HISTORY_STATE_PATH", state_path)
    monkeypatch.setenv(SUPPRESS, "1")
    if live:
        monkeypatch.setenv(lambda_module.LIVE_DAEMON_ENV, "1")
    else:
        monkeypatch.delenv(lambda_module.LIVE_DAEMON_ENV, raising=False)
    if audit:
        monkeypatch.setenv(AUDIT, "1")
    else:
        monkeypatch.delenv(AUDIT, raising=False)
    daemon = object.__new__(HNCLiveDaemon)
    daemon.engine = LambdaEngine()
    daemon._sources = {}
    if sources:
        daemon._sources = {
            "a": _source("a", 0.55, source_timestamp=NOW - 5.0),
            "b": _source("b", 0.65, source_timestamp=NOW - 2.0),
        }
    daemon._step_lock = asyncio.Lock()
    daemon._trace_path = trace_path
    daemon._publish_pulse = lambda _envelope: None
    return daemon, state_path, trace_path


def _rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_live_daemon_with_import_suppression_writes_real_lambda(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    daemon, state_path, trace_path = _daemon(
        tmp_path, monkeypatch, sources=True, live=True, audit=False,
    )

    state, envelope, _readings = asyncio.run(daemon.publish_heartbeat(NOW))

    assert state is not None
    disk = json.loads(state_path.read_text(encoding="utf-8"))
    rows = _rows(trace_path)
    assert len(rows) == 1
    assert rows[0]["truth_status"] == "real_derived"
    assert rows[0]["data_status"] == "live"
    assert rows[0]["generated_values"] is False
    assert rows[0]["lambda_t"] == disk["history"][-1]
    assert rows[0]["lambda_t"] == envelope["lambda_t"]
    assert math.isfinite(rows[0]["lambda_t"])
    assert disk["truth_status"] == "real_derived"


def test_audit_mode_writes_nothing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    daemon, state_path, trace_path = _daemon(
        tmp_path, monkeypatch, sources=True, live=True, audit=True,
    )
    with caplog.at_level(logging.WARNING, logger="aureon.core.hnc_live_daemon"):
        asyncio.run(daemon.publish_heartbeat(NOW))
        asyncio.run(daemon.publish_heartbeat(NOW))

    assert not state_path.exists()
    assert not trace_path.exists()
    warnings = [
        record for record in caplog.records
        if "shared_state_suppressed" in record.message
    ]
    assert len(warnings) == 1
    assert warnings[0].levelno == logging.WARNING


def test_missing_history_is_no_data_not_zero(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    daemon, state_path, trace_path = _daemon(
        tmp_path, monkeypatch, sources=False, live=True, audit=False,
    )
    assert not state_path.exists()

    _state, envelope, readings = asyncio.run(daemon.publish_heartbeat(NOW))

    assert readings == []
    assert envelope["truth_status"] == "no_data"
    assert envelope.get("lambda_t") is None
    rows = _rows(trace_path)
    assert len(rows) == 1
    assert rows[0]["truth_status"] == "no_data"
    assert "lambda_t" not in rows[0]
    assert rows[0].get("lambda_t") is None
    assert not state_path.exists()


def test_real_zero_lambda_is_committed_and_traced(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    daemon, state_path, trace_path = _daemon(
        tmp_path, monkeypatch, sources=False, live=True, audit=False,
    )
    daemon.engine._history.append(0.0)
    daemon.engine._psi_history.append(0.0)
    daemon.engine._step_count = 1
    receipt = daemon.engine.save_history(["provider:x:zero"])

    assert receipt is not None
    assert receipt["history"][-1] == 0.0
    disk = json.loads(state_path.read_text(encoding="utf-8"))
    assert disk["history"][-1] == 0.0
    assert disk["truth_status"] == "real_derived"

    daemon._append_trace(
        {
            "data_status": "live",
            "truth_status": "real_derived",
            "generated_values": False,
            "lambda_t": 0.0,
            "step": 1,
            "consciousness_psi": 0.0,
            "coherence_gamma": 0.0,
            "symbolic_life_score": 0.0,
            "source_count": 0,
        },
        [],
    )
    row = _rows(trace_path)[-1]
    assert row["truth_status"] == "real_derived"
    assert row["lambda_t"] == 0.0
    assert row["consciousness_psi"] == 0.0


def test_import_suppression_without_live_daemon_still_writes_nothing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    daemon, state_path, trace_path = _daemon(
        tmp_path, monkeypatch, sources=True, live=False, audit=False,
    )

    state, envelope, _readings = asyncio.run(daemon.publish_heartbeat(NOW))

    assert state is None
    assert envelope["truth_status"] == "no_data"
    assert "lambda_t" not in envelope
    assert not state_path.exists()
    rows = _rows(trace_path)
    assert rows[0]["truth_status"] == "no_data"
    assert "lambda_t" not in rows[0]


def test_trace_does_not_invent_zero_for_a_live_envelope_with_no_lambda(
    tmp_path: Path,
) -> None:
    daemon = object.__new__(HNCLiveDaemon)
    daemon._trace_path = tmp_path / "hnc_live_trace.jsonl"
    daemon._sources = {}
    daemon._append_trace(
        {
            "data_status": "live",
            "truth_status": "real_derived",
            "lambda_t": None,
        },
        [],
    )
    row = _rows(daemon._trace_path)[0]
    assert row["truth_status"] == "no_data"
    assert row["data_status"] == "no_data"
    assert "lambda_t" not in row


def test_main_marks_the_process_as_the_live_daemon_after_imports(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(lambda_module.LIVE_DAEMON_ENV, raising=False)
    monkeypatch.setenv("AUREON_PLUG_AND_PLAY", "1")
    seen: dict[str, str | None] = {}

    class _Daemon:
        def __init__(self, *args, **kwargs):
            seen["flag"] = os.environ.get(lambda_module.LIVE_DAEMON_ENV)

        async def run(self, duration_s=None):
            return None

    monkeypatch.setattr(
        "aureon.core.hnc_live_daemon.HNCLiveDaemon",
        _Daemon,
    )
    from aureon.core.hnc_live_daemon import main

    main()
    assert seen["flag"] == "1"


def _organ_envs(launcher_env: dict) -> tuple[dict, dict]:
    import aureon_fusion.organ_registry as registry

    with mock.patch.dict(os.environ, launcher_env, clear=True):
        reloaded = importlib.reload(registry)
        daemon_env = dict(reloaded.ORGANS["hnc_live_daemon"]["env"])
        supervisor_env = dict(reloaded.ORGANS["unity_supervisor"]["env"])
    return daemon_env, supervisor_env


@pytest.fixture
def restored_organ_registry():
    import aureon_fusion.organ_registry as registry

    yield
    importlib.reload(registry)


def test_normal_live_organ_pins_import_suppression_and_not_audit(
    restored_organ_registry,
    tmp_path: Path,
) -> None:
    daemon_env, _supervisor = _organ_envs({"SERO_WORKSPACE": str(tmp_path)})

    assert daemon_env[SUPPRESS] == "1"
    assert AUDIT not in daemon_env
    assert daemon_env["AUREON_DISABLE_REAL_ORDERS"] == "1"
    assert daemon_env["AUREON_LIVE_TRADING"] == "0"
    assert daemon_env["AUREON_DISABLE_EXCHANGE_MUTATIONS"] == "1"


def test_launcher_audit_mode_is_kept_on_the_live_daemon_organ(
    restored_organ_registry,
    tmp_path: Path,
) -> None:
    daemon_env, supervisor = _organ_envs({
        "SERO_WORKSPACE": str(tmp_path),
        AUDIT: "1",
    })
    assert daemon_env[AUDIT] == "1"
    assert daemon_env[SUPPRESS] == "1"

    respawn_env, _again = _organ_envs(supervisor)
    assert respawn_env[AUDIT] == "1"
    assert respawn_env[SUPPRESS] == "1"


def _engine(tmp_path: Path) -> LambdaEngine:
    return LambdaEngine(state_path=tmp_path / "lambda_history.json")


def test_one_reading_gamma_is_none_not_half(tmp_path: Path) -> None:
    state = _engine(tmp_path).step(
        [SubsystemReading(name="only", value=0.4, confidence=0.8, state="live")],
        source_receipt_ids=["provider:only:1"],
        auto_persist=False,
    )
    assert state.coherence_gamma is None
    assert state.coherence_gamma != 0.5


def test_zero_mean_gamma_is_none_not_half(tmp_path: Path) -> None:
    state = _engine(tmp_path).step(
        [
            SubsystemReading(name="a", value=0.0, confidence=1.0, state="live"),
            SubsystemReading(name="b", value=0.0, confidence=1.0, state="live"),
        ],
        source_receipt_ids=["provider:a:1", "provider:b:1"],
        auto_persist=False,
    )
    assert state.coherence_gamma is None
    assert state.coherence_gamma != 0.5


def test_warmup_psi_is_none_until_the_echo_window(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    state = engine.step(
        [
            SubsystemReading(name="a", value=0.55, confidence=0.8, state="live"),
            SubsystemReading(name="b", value=0.65, confidence=0.8, state="live"),
        ],
        source_receipt_ids=["provider:a:1", "provider:b:1"],
        auto_persist=False,
    )
    assert len(engine._history) < lambda_module.TAU
    assert state.consciousness_psi is None
    assert state.consciousness_psi != (1 / 30)
    assert list(engine._psi_history) == []


def test_bool_is_not_a_lambda_reading() -> None:
    assert _finite_reading(True) is None
    assert _finite_reading(False) is None
    assert _finite_reading(True) != 1.0
    assert _finite_reading(False) != 0.0
    assert _finite_reading(0.0) == 0.0
    assert _finite_reading(0) == 0.0


def test_non_finite_is_not_a_lambda_reading() -> None:
    assert _finite_reading(float("nan")) is None
    assert _finite_reading(float("inf")) is None
    assert _finite_reading(float("-inf")) is None
    assert _finite_reading(0.0) == 0.0


def _live_shell(tmp_path: Path) -> HNCLiveDaemon:
    daemon = object.__new__(HNCLiveDaemon)
    daemon._trace_path = tmp_path / "hnc_live_trace.jsonl"
    daemon._sources = {}
    return daemon


def test_missing_field_readings_are_none_not_zero(tmp_path: Path) -> None:
    daemon = _live_shell(tmp_path)
    daemon._append_trace(
        {
            "data_status": "live",
            "truth_status": "real_derived",
            "source": "hnc_live_daemon",
            "source_timestamp": NOW - 2.0,
            "received_at": NOW,
            "lambda_t": 0.2,
        },
        [],
    )
    row = _rows(daemon._trace_path)[0]
    assert row["consciousness_psi"] is None
    assert row["coherence_gamma"] is None
    assert row["symbolic_life_score"] is None
    assert row["consciousness_psi"] != 0.0
    assert row["coherence_gamma"] != 0.0
    assert row["symbolic_life_score"] != 0.0
    assert row["lambda_t"] == 0.2
    assert row["source"] == "hnc_live_daemon"
    assert row["source_timestamp"] == NOW - 2.0


def test_measured_zero_field_readings_stay_zero(tmp_path: Path) -> None:
    daemon = _live_shell(tmp_path)
    daemon._append_trace(
        {
            "data_status": "live",
            "truth_status": "real_derived",
            "lambda_t": 0.0,
            "consciousness_psi": 0.0,
            "coherence_gamma": 0.0,
            "symbolic_life_score": 0.0,
        },
        [],
    )
    row = _rows(daemon._trace_path)[0]
    assert row["lambda_t"] == 0.0
    assert row["consciousness_psi"] == 0.0
    assert row["coherence_gamma"] == 0.0
    assert row["symbolic_life_score"] == 0.0


def test_wakeup_psi_and_default_gamma_are_not_trace_readings(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    daemon, _state, trace_path = _daemon(
        tmp_path, monkeypatch, sources=True, live=True, audit=False,
    )
    _state_obj, envelope, _readings = asyncio.run(daemon.publish_heartbeat(NOW))
    row = _rows(trace_path)[0]
    assert row["consciousness_psi"] is None
    assert row["symbolic_life_score"] is None
    assert envelope["consciousness_psi"] is None
    assert row["lambda_t"] == envelope["lambda_t"]
    assert math.isfinite(row["lambda_t"])
    assert isinstance(row["coherence_gamma"], float)
    assert row["source"] == "hnc_live_daemon"
    assert row["source_timestamp"] is not None

    daemon._sources = {"a": daemon._sources["a"]}
    one_state, one_source, one_readings = asyncio.run(daemon.publish_heartbeat(NOW))
    one_row = _rows(trace_path)[-1]
    assert one_state is None
    assert one_readings == []
    assert one_source["truth_status"] == "no_data"
    assert one_source["reason"] == "insufficient_sources"
    assert one_source.get("lambda_t") is None
    assert one_row["truth_status"] == "no_data"
    assert one_row["reason"] == "insufficient_sources"
    assert "lambda_t" not in one_row


def test_stale_lambda_history_is_not_loaded(tmp_path: Path) -> None:
    path = tmp_path / "lambda_history.json"
    writer = LambdaEngine(state_path=path)
    writer._history.append(0.42)
    writer._psi_history.append(0.2)
    writer._step_count = 1
    assert writer.save_history(["provider:x:stale-check"]) is not None
    fresh = LambdaEngine(state_path=path)
    assert fresh.get_history() == [0.42]
    assert fresh.history_load_status == "loaded_v3"

    old = time.time() - (lambda_module.HISTORY_MAX_AGE_S + 60.0)
    os.utime(path, (old, old))
    stale = LambdaEngine(state_path=path)
    assert stale.get_history() == []
    assert stale.history_load_status == "stale"
    assert stale.get_history() != [0.42]


def test_supervisor_pin_does_not_force_audit_onto_a_live_daemon_respawn(
    restored_organ_registry,
    tmp_path: Path,
) -> None:
    _first, supervisor = _organ_envs({"SERO_WORKSPACE": str(tmp_path)})
    assert supervisor[AUDIT] == "1"
    assert supervisor[SUPPRESS] == "1"
    assert "AUREON_PARENT_" + AUDIT not in supervisor

    respawn_env, _supervisor = _organ_envs(supervisor)
    assert AUDIT not in respawn_env
    assert respawn_env[SUPPRESS] == "1"
