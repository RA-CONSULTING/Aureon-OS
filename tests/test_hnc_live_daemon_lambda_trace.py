"""Real Lambda trace publication is distinct from audit and unavailable readings."""

from __future__ import annotations

import asyncio
import json
import math
from pathlib import Path

import pytest

from aureon.core import aureon_lambda_engine as lambda_module
from aureon.core.aureon_lambda_engine import LambdaEngine, SubsystemReading
from aureon.core.hnc_live_daemon import HNCLiveDaemon, SourceReceipt, SourceState, _finite_reading

NOW = 1_786_400_000.0


def _source(name: str, value: float, source_timestamp: float) -> SourceState:
    receipt = SourceReceipt(
        source_id=f"provider.{name}", source_timestamp=source_timestamp,
        received_at=NOW - 1.0, receipt_id=f"provider:{name}:receipt-1",
        receipt_type="provider_measurement", truth_status="real_observed",
        generated_values=False,
    )
    return SourceState(
        name=name, interval_s=5.0,
        last_reading=SubsystemReading(name=name, value=value, confidence=0.8, state="live"),
        last_receipt=receipt, last_fetch_ts=receipt.received_at, max_age_s=120.0,
    )


def _daemon(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, live: bool, audit: bool) -> tuple[HNCLiveDaemon, Path, Path]:
    state_path = tmp_path / "lambda_history.json"
    trace_path = tmp_path / "hnc_live_trace.jsonl"
    monkeypatch.setattr(lambda_module, "DEFAULT_HISTORY_STATE_PATH", state_path)
    monkeypatch.setenv("AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS", "1")
    if live:
        monkeypatch.setenv(lambda_module.LIVE_DAEMON_ENV, "1")
    else:
        monkeypatch.delenv(lambda_module.LIVE_DAEMON_ENV, raising=False)
    if audit:
        monkeypatch.setenv("AUREON_AUDIT_MODE", "1")
    else:
        monkeypatch.delenv("AUREON_AUDIT_MODE", raising=False)
    daemon = object.__new__(HNCLiveDaemon)
    daemon.engine = LambdaEngine()
    daemon._sources = {
        "a": _source("a", 0.55, NOW - 5.0),
        "b": _source("b", 0.65, NOW - 2.0),
    }
    daemon._step_lock = asyncio.Lock()
    daemon._trace_path = trace_path
    daemon._publish_pulse = lambda _envelope: None
    return daemon, state_path, trace_path


def _rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()] if path.exists() else []


def test_live_daemon_with_import_suppression_publishes_real_lambda(tmp_path, monkeypatch):
    daemon, state_path, trace_path = _daemon(tmp_path, monkeypatch, live=True, audit=False)
    state, envelope, _ = asyncio.run(daemon.publish_heartbeat(NOW))
    assert state is not None
    disk = json.loads(state_path.read_text(encoding="utf-8"))
    row = _rows(trace_path)[0]
    assert row["truth_status"] == "real_derived"
    assert row["data_status"] == "live"
    assert row["lambda_t"] == disk["history"][-1] == envelope["lambda_t"]
    assert math.isfinite(row["lambda_t"])


def test_audit_mode_writes_nothing(tmp_path, monkeypatch):
    daemon, state_path, trace_path = _daemon(tmp_path, monkeypatch, live=True, audit=True)
    state, envelope, _ = asyncio.run(daemon.publish_heartbeat(NOW))
    assert state is None
    assert envelope["truth_status"] == "no_data"
    assert not state_path.exists()
    assert _rows(trace_path) == []


def test_suppressed_non_daemon_has_no_lambda(tmp_path, monkeypatch):
    daemon, state_path, trace_path = _daemon(tmp_path, monkeypatch, live=False, audit=False)
    state, envelope, _ = asyncio.run(daemon.publish_heartbeat(NOW))
    assert state is None
    assert envelope["truth_status"] == "no_data"
    assert "lambda_t" not in envelope
    assert not state_path.exists()
    assert "lambda_t" not in _rows(trace_path)[0]


def test_no_data_transaction_is_not_republished_as_live(tmp_path):
    daemon = object.__new__(HNCLiveDaemon)
    daemon._trace_path = tmp_path / "trace.jsonl"
    daemon._sources = {}
    daemon._append_trace({"data_status": "no_data", "truth_status": "no_data"}, [])
    row = _rows(daemon._trace_path)[0]
    assert row["truth_status"] == "no_data"
    assert "lambda_t" not in row


@pytest.mark.parametrize("value", [None, True, False, float("nan"), float("inf"), "-"])
def test_invalid_lambda_is_not_a_trace_reading(tmp_path, value):
    daemon = object.__new__(HNCLiveDaemon)
    daemon._trace_path = tmp_path / "trace.jsonl"
    daemon._sources = {}
    daemon._append_trace({"data_status": "live", "truth_status": "real_derived", "lambda_t": value}, [])
    row = _rows(daemon._trace_path)[0]
    assert row["truth_status"] == row["data_status"] == "no_data"
    assert row["reason"] == "lambda_reading_missing"
    assert "lambda_t" not in row


def test_zero_and_missing_metrics_remain_distinct(tmp_path):
    daemon = object.__new__(HNCLiveDaemon)
    daemon._trace_path = tmp_path / "trace.jsonl"
    daemon._sources = {}
    daemon._append_trace({"data_status": "live", "lambda_t": 0.0, "coherence_gamma": 0.0}, [])
    row = _rows(daemon._trace_path)[0]
    assert row["lambda_t"] == row["coherence_gamma"] == 0.0
    assert row["consciousness_psi"] is None
    assert row["symbolic_life_score"] is None
    assert _finite_reading(0) == 0.0
