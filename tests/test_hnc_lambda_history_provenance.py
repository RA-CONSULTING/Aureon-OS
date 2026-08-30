"""Temp-only provenance and transaction tests for HNC Lambda session memory."""

from __future__ import annotations

import asyncio
import hashlib
import json
import math
import os
from pathlib import Path
from typing import Any

import pytest

from aureon.core import aureon_lambda_engine as lambda_module
from aureon.core.aureon_lambda_engine import (
    DEFAULT_HISTORY_STATE_PATH,
    LambdaEngine,
    SubsystemReading,
    validate_history_receipt,
)
from aureon.core.hnc_live_daemon import (
    HNCLiveDaemon,
    SourceReceipt,
    SourceState,
)

NOW = 1_786_400_000.0
SHARED_STATE_PATH = DEFAULT_HISTORY_STATE_PATH


def _file_identity(path: Path) -> tuple[int, int, str] | None:
    if not path.exists():
        return None
    stat = path.stat()
    return (
        stat.st_size,
        stat.st_mtime_ns,
        hashlib.sha256(path.read_bytes()).hexdigest(),
    )


@pytest.fixture(scope="module", autouse=True)
def _shared_history_is_read_only():
    before = _file_identity(SHARED_STATE_PATH)
    yield
    assert _file_identity(SHARED_STATE_PATH) == before


def _reading(name: str = "x", value: float = 0.6) -> SubsystemReading:
    return SubsystemReading(
        name=name,
        value=value,
        confidence=0.8,
        state="live",
    )


def _source_receipt(
    name: str = "x",
    *,
    source_timestamp: float = NOW - 2.0,
    received_at: float = NOW - 1.0,
) -> SourceReceipt:
    return SourceReceipt(
        source_id=f"provider.{name}",
        source_timestamp=source_timestamp,
        received_at=received_at,
        receipt_id=f"provider:{name}:receipt-1",
        receipt_type="provider_measurement",
        truth_status="real_observed",
        generated_values=False,
    )


def _source_state(
    name: str,
    *,
    source_timestamp: float,
    value: float,
) -> SourceState:
    receipt = _source_receipt(name, source_timestamp=source_timestamp)
    return SourceState(
        name=name,
        interval_s=5.0,
        last_reading=_reading(name, value),
        last_receipt=receipt,
        last_fetch_ts=receipt.received_at,
        max_age_s=120.0,
    )


def _step_and_commit(
    path: Path,
    *,
    provider_id: str = "provider:x:receipt-1",
    value: float = 0.6,
) -> tuple[LambdaEngine, dict[str, Any], dict[str, Any]]:
    engine = LambdaEngine(state_path=path)
    state = engine.step(
        [_reading(value=value)],
        source_receipt_ids=[provider_id],
        auto_persist=False,
    )
    receipt = engine.save_history(source_receipt_ids=[provider_id])
    assert receipt is not None
    return engine, state.to_dict(), receipt


def _daemon_shell(tmp_path: Path) -> HNCLiveDaemon:
    daemon = object.__new__(HNCLiveDaemon)
    daemon.engine = LambdaEngine(state_path=tmp_path / "lambda_history.json")
    daemon._sources = {
        "a": _source_state("a", source_timestamp=NOW - 5.0, value=0.55),
        "b": _source_state("b", source_timestamp=NOW - 2.0, value=0.65),
    }
    daemon._step_lock = asyncio.Lock()
    daemon._trace_path = tmp_path / "hnc_trace.jsonl"
    daemon._observer = None
    daemon._wave_predictor = None
    return daemon


@pytest.mark.parametrize(
    "raw_bytes",
    [
        b'{"version":2,"history":[0.1],"psi_history":[0.2],"step_count":1}',
        b'{"version":3,"history":',
        (
            b'{"version":3,"receipt_type":"hnc_lambda_history",'
            b'"source_id":"aureon:hnc:lambda_engine","data_status":"live",'
            b'"truth_status":"real_derived","generated_values":false,'
            b'"history":[NaN],"psi_history":[0.2],"step_count":1,'
            b'"beta":1.0,"source_receipt_ids":["provider:x:1"],'
            b'"input_receipt_ids":["provider:x:1"],'
            b'"previous_receipt_id":null,"previous_canonical_hash":null,'
            b'"canonical_hash":"bad","receipt_id":"bad"}'
        ),
    ],
    ids=["legacy_v2", "invalid_json", "nonfinite_v3"],
)
def test_untrusted_history_is_zero_and_logically_quarantined_until_commit(
    tmp_path: Path,
    raw_bytes: bytes,
) -> None:
    state_path = tmp_path / "lambda_history.json"
    state_path.write_bytes(raw_bytes)
    before = _file_identity(state_path)

    engine = LambdaEngine(state_path=state_path)

    assert engine.get_step() == 0
    assert engine.get_history() == []
    assert list(engine._psi_history) == []
    assert _file_identity(state_path) == before
    quarantine_path = engine.history_quarantine_path
    assert quarantine_path is not None
    assert hashlib.sha256(raw_bytes).hexdigest() in quarantine_path.name
    assert not quarantine_path.exists()

    assert engine.save_history() is None
    assert _file_identity(state_path) == before
    assert not quarantine_path.exists()

    engine.step(
        [_reading()],
        source_receipt_ids=["provider:x:receipt-1"],
        auto_persist=False,
    )
    receipt = engine.save_history(["provider:x:receipt-1"])
    assert receipt is not None
    assert quarantine_path.read_bytes() == raw_bytes
    assert validate_history_receipt(
        json.loads(state_path.read_text(encoding="utf-8"))
    ) == receipt


def test_tampered_v3_receipt_loads_no_values_and_preserves_exact_bytes(
    tmp_path: Path,
) -> None:
    state_path = tmp_path / "lambda_history.json"
    _engine, _state, _receipt = _step_and_commit(state_path)
    tampered = json.loads(state_path.read_text(encoding="utf-8"))
    tampered["history"][-1] += 0.25
    tampered_bytes = json.dumps(
        tampered,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    state_path.write_bytes(tampered_bytes)

    loaded = LambdaEngine(state_path=state_path)

    assert loaded.get_step() == 0
    assert loaded.get_history() == []
    assert state_path.read_bytes() == tampered_bytes
    assert loaded.history_load_status == "invalid_logically_quarantined"
    assert loaded.history_quarantine_path is not None
    assert not loaded.history_quarantine_path.exists()


def test_unreceipted_auto_or_explicit_save_never_writes(tmp_path: Path) -> None:
    state_path = tmp_path / "lambda_history.json"
    engine = LambdaEngine(state_path=state_path)
    for _ in range(max(1, lambda_module.PERSIST_EVERY)):
        engine.step([_reading()])
    assert not state_path.exists()
    assert engine.save_history() is None
    assert not state_path.exists()


def test_v3_receipt_is_deterministic_finite_and_hash_chained(
    tmp_path: Path,
) -> None:
    first_path = tmp_path / "first.json"
    second_path = tmp_path / "second.json"
    first_engine, _first_state, first = _step_and_commit(first_path)
    _second_engine, _second_state, independent = _step_and_commit(second_path)
    assert first == independent
    assert first["source_receipt_ids"] == ["provider:x:receipt-1"]
    assert first["input_receipt_ids"] == ["provider:x:receipt-1"]

    material = {
        key: value
        for key, value in first.items()
        if key not in {"canonical_hash", "receipt_id"}
    }
    expected_hash = hashlib.sha256(json.dumps(
        material,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")).hexdigest()
    assert first["canonical_hash"] == expected_hash
    assert first["receipt_id"] == f"hnc:lambda_history:{expected_hash}"
    assert all(math.isfinite(value) for value in first["history"])
    assert all(math.isfinite(value) for value in first["psi_history"])

    first_engine.step(
        [_reading(value=0.7)],
        source_receipt_ids=["provider:x:receipt-2"],
        auto_persist=False,
    )
    chained = first_engine.save_history(["provider:x:receipt-2"])
    assert chained is not None
    assert chained["previous_receipt_id"] == first["receipt_id"]
    assert chained["previous_canonical_hash"] == first["canonical_hash"]
    assert chained["source_receipt_ids"] == ["provider:x:receipt-2"]
    assert chained["input_receipt_ids"] == sorted([
        "provider:x:receipt-2",
        first["receipt_id"],
    ])


@pytest.mark.parametrize(
    "flag",
    ["AUREON_AUDIT_MODE", "AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS"],
)
def test_default_audit_or_suppress_neither_loads_nor_writes_shared_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    flag: str,
) -> None:
    state_path = tmp_path / "default" / "lambda_history.json"
    _seed, _state, _receipt = _step_and_commit(state_path)
    before = _file_identity(state_path)
    monkeypatch.setattr(lambda_module, "DEFAULT_HISTORY_STATE_PATH", state_path)
    monkeypatch.setenv("AUREON_AUDIT_MODE", "0")
    monkeypatch.setenv("AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS", "0")
    monkeypatch.setenv(flag, "1")

    engine = lambda_module.LambdaEngine()

    assert engine.history_load_status == "shared_state_suppressed"
    assert engine.get_step() == 0
    assert engine.get_history() == []
    engine.step(
        [_reading()],
        source_receipt_ids=["provider:x:receipt-2"],
        auto_persist=False,
    )
    assert engine.save_history(["provider:x:receipt-2"]) is None
    assert _file_identity(state_path) == before


def test_nonfinite_active_history_fails_closed_without_writing(
    tmp_path: Path,
) -> None:
    state_path = tmp_path / "lambda_history.json"
    engine = LambdaEngine(state_path=state_path)
    engine._history.append(float("inf"))
    assert engine.save_history(["provider:x:receipt-1"]) is None
    assert engine.last_history_commit_error == "nonfinite_or_invalid_history"
    assert not state_path.exists()


def test_concurrent_history_writer_conflict_preserves_winner(
    tmp_path: Path,
) -> None:
    state_path = tmp_path / "lambda_history.json"
    _seed, _state, _receipt = _step_and_commit(state_path)
    first = LambdaEngine(state_path=state_path)
    stale = LambdaEngine(state_path=state_path)
    first.step(
        [_reading(value=0.7)],
        source_receipt_ids=["provider:x:first"],
        auto_persist=False,
    )
    stale.step(
        [_reading(value=0.8)],
        source_receipt_ids=["provider:x:stale"],
        auto_persist=False,
    )
    winner = first.save_history(["provider:x:first"])
    assert winner is not None
    winner_bytes = state_path.read_bytes()

    assert stale.save_history(["provider:x:stale"]) is None
    assert stale.last_history_commit_error == "history_lineage_conflict"
    assert state_path.read_bytes() == winner_bytes


def test_advisory_lock_is_os_released_after_handle_close(tmp_path: Path) -> None:
    state_path = tmp_path / "lambda_history.json"
    engine = LambdaEngine(state_path=state_path)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = state_path.with_name(state_path.name + ".lock")
    abandoned = engine._acquire_advisory_lock(lock_path)
    assert abandoned is not None
    abandoned.close()
    engine.step(
        [_reading()],
        source_receipt_ids=["provider:x:receipt-1"],
        auto_persist=False,
    )
    assert engine.save_history(["provider:x:receipt-1"]) is not None
    assert lock_path.exists()
    assert lock_path.stat().st_size == 1


def test_advisory_lock_conflict_fails_before_state_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state_path = tmp_path / "lambda_history.json"
    engine = LambdaEngine(state_path=state_path)
    engine.step(
        [_reading()],
        source_receipt_ids=["provider:x:receipt-1"],
        auto_persist=False,
    )
    monkeypatch.setattr(engine, "_acquire_advisory_lock", lambda _path: None)

    assert engine.save_history(["provider:x:receipt-1"]) is None
    assert engine.last_history_commit_error == "history_advisory_lock_conflict"
    assert not state_path.exists()


def test_replace_failure_is_falsey_and_retry_commits(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state_path = tmp_path / "lambda_history.json"
    engine = LambdaEngine(state_path=state_path)
    engine.step(
        [_reading()],
        source_receipt_ids=["provider:x:receipt-1"],
        auto_persist=False,
    )
    real_replace = lambda_module.os.replace

    def fail_target_replace(source: Any, destination: Any) -> None:
        if Path(destination) == state_path:
            raise OSError("injected replace failure")
        real_replace(source, destination)

    with monkeypatch.context() as scoped:
        scoped.setattr(lambda_module.os, "replace", fail_target_replace)
        assert engine.save_history(["provider:x:receipt-1"]) is None
        assert engine.last_history_commit_error == "history_commit_failed:OSError"
        assert not state_path.exists()
    assert engine.save_history(["provider:x:receipt-1"]) is not None


def test_post_replace_readback_is_required(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state_path = tmp_path / "lambda_history.json"
    engine = LambdaEngine(state_path=state_path)
    engine.step(
        [_reading()],
        source_receipt_ids=["provider:x:receipt-1"],
        auto_persist=False,
    )
    monkeypatch.setattr(engine, "_disk_history_receipt", lambda: None)
    assert engine.save_history(["provider:x:receipt-1"]) is None
    assert engine.last_history_commit_error == "history_readback_failed"


def test_daemon_commits_memory_before_live_envelope_and_preserves_provider_time(
    tmp_path: Path,
) -> None:
    daemon = _daemon_shell(tmp_path)
    state, envelope, readings = asyncio.run(daemon._compute_transaction(NOW))

    assert state is not None
    assert envelope["data_status"] == "live"
    assert envelope["source_timestamp"] == NOW - 2.0
    memory = daemon.engine.last_history_receipt
    assert memory is not None
    provider_ids = [
        "provider:a:receipt-1",
        "provider:b:receipt-1",
    ]
    assert memory["source_receipt_ids"] == provider_ids
    assert envelope["memory_receipt_id"] == memory["receipt_id"]
    assert envelope["memory_canonical_hash"] == memory["canonical_hash"]
    assert envelope["input_receipt_ids"] == sorted(
        provider_ids + [memory["receipt_id"]]
    )
    assert envelope["step"] == memory["step_count"]
    assert envelope["lambda_t"] == memory["history"][-1]
    assert envelope["consciousness_psi"] == memory["psi_history"][-1]
    assert len(readings) == 2
    disk = json.loads(
        (tmp_path / "lambda_history.json").read_text(encoding="utf-8")
    )
    assert disk["receipt_id"] == memory["receipt_id"]


def test_daemon_failed_commit_rolls_back_and_emits_numeric_free_no_data(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    daemon = _daemon_shell(tmp_path)
    before = daemon.engine.checkpoint_history()
    monkeypatch.setattr(
        daemon.engine,
        "save_history",
        lambda source_receipt_ids=None: None,
    )

    state, envelope, readings = asyncio.run(daemon._compute_transaction(NOW))

    assert state is None
    assert readings == []
    assert daemon.engine.checkpoint_history() == before
    assert envelope["data_status"] == "no_data"
    assert envelope["reason"] == "lambda_history_commit_failed_rollback"
    for metric in (
        "step",
        "lambda_t",
        "consciousness_psi",
        "coherence_gamma",
        "symbolic_life_score",
        "source_count",
    ):
        assert metric not in envelope
    assert not (tmp_path / "lambda_history.json").exists()


def test_direct_live_envelope_requires_exact_memory_and_rejects_tampered_state(
    tmp_path: Path,
) -> None:
    daemon = _daemon_shell(tmp_path)
    state, envelope, readings = asyncio.run(daemon._compute_transaction(NOW))
    assert state is not None
    receipts = [daemon._sources[reading.name].last_receipt for reading in readings]
    memory = daemon.engine.last_history_receipt
    assert memory is not None

    with pytest.raises(TypeError):
        daemon._derived_envelope(state.to_dict(), readings, received_at=NOW)

    tampered_state = state.to_dict()
    tampered_state["lambda_t"] += 0.01
    with pytest.raises(ValueError, match="does not match emitted state"):
        daemon._derived_envelope(
            tampered_state,
            readings,
            received_at=NOW,
            source_receipts=receipts,
            memory_receipt=memory,
        )
    assert envelope["data_status"] == "live"


def test_memory_lineage_survives_bus_and_trace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    daemon = _daemon_shell(tmp_path)
    state, envelope, readings = asyncio.run(daemon._compute_transaction(NOW))
    assert state is not None
    daemon._append_trace(envelope, readings)
    trace = json.loads(daemon._trace_path.read_text(encoding="utf-8"))

    published = []

    class _Bus:
        def publish(self, thought: Any) -> None:
            published.append(thought)

    from aureon.core import aureon_thought_bus

    monkeypatch.setattr(aureon_thought_bus, "get_thought_bus", lambda: _Bus())
    daemon._publish_pulse(envelope)
    assert len(published) == 1
    payload = published[0].payload
    for key in (
        "memory_receipt_id",
        "memory_canonical_hash",
        "memory_previous_receipt_id",
        "step",
    ):
        assert key in trace
        assert trace[key] == envelope[key]
        assert key in payload
        assert payload[key] == envelope[key]
