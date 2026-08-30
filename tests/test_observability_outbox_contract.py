from __future__ import annotations

import json
import multiprocessing
import threading
import time
from pathlib import Path
from typing import Any

import pytest

import aureon.observability.outbox as outbox_module
from aureon.observability import (
    RECEIPT_SCHEMA,
    DurableObservabilityOutbox,
    OutboxBusyError,
    OutboxCapacityError,
    OutboxCorruptionError,
    OutboxIdempotencyConflictError,
    OutboxReceiptError,
    OutboxUnavailableError,
)


def _canonical(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    ).encode()


def _receipt(item: dict[str, Any], *, receipt_id: str = "delivery-12345678") -> dict[str, Any]:
    return {
        "schema": RECEIPT_SCHEMA,
        "event_id": item["event_id"],
        "payload_sha256": item["payload_sha256"],
        "receipt_id": receipt_id,
        "delivered_at_unix_ns": item["created_at_unix_ns"] + 1,
    }


def _diagnostic_keys(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        for key, item in value.items():
            normalized = key.replace("-", "_").lower()
            if normalized in {
                "message",
                "messages",
                "stack",
                "stack_trace",
                "stacktrace",
                "traceback",
                "locals",
                "local_variables",
                "exception_message",
                "error_message",
                "exc_info",
            }:
                found.add(normalized)
            found.update(_diagnostic_keys(item))
    elif isinstance(value, list):
        for item in value:
            found.update(_diagnostic_keys(item))
    return found


def _hold_process_lock(lock_path: str, ready: Any, release: Any) -> None:
    with outbox_module._writer_lease(Path(lock_path)):
        ready.set()
        release.wait(10)


def test_outbox_is_canonical_redacted_and_restart_idempotent(tmp_path: Path) -> None:
    state_path = tmp_path / "observability-outbox.json"
    now = 10_000_000_000
    outbox = DurableObservabilityOutbox(state_path, clock_ns=lambda: now)
    try:
        raise RuntimeError("Bearer provider-secret must not persist")
    except RuntimeError as exception:
        item = outbox.enqueue(
            "provider_failure",
            idempotency_key="stable-source-event-1",
            fields={
                "authorization": "Bearer top-secret",
                "message": "raw provider response",
                "nested": {
                    "apiKey": "sk-proj-private-value",
                    "clientSecretValue": "unprefixed-client-secret",
                    "providerAuthHeader": "unprefixed-auth-secret",
                    "stackTrace": "secret stack",
                    "locals": {"password": "hunter2"},
                    "status": "held",
                },
                "not_finite": float("nan"),
            },
            exception=exception,
        )

        restarted = DurableObservabilityOutbox(state_path, clock_ns=lambda: now + 999)
        replay = restarted.enqueue(
            "provider_failure",
            idempotency_key="stable-source-event-1",
            fields={
                "authorization": "Bearer top-secret",
                "message": "raw provider response",
                "nested": {
                    "apiKey": "sk-proj-private-value",
                    "clientSecretValue": "unprefixed-client-secret",
                    "providerAuthHeader": "unprefixed-auth-secret",
                    "stackTrace": "secret stack",
                    "locals": {"password": "hunter2"},
                    "status": "held",
                },
                "not_finite": float("nan"),
            },
            exception=exception,
        )

    raw = state_path.read_bytes()
    parsed = json.loads(raw)
    assert raw == _canonical(parsed)
    assert replay == item
    assert len(restarted.pending()) == 1
    assert restarted.health().generation == 1
    assert item["payload"]["authorization"] == "[REDACTED]"
    assert item["payload"]["nested"]["apiKey"] == "[REDACTED]"
    assert item["payload"]["nested"]["clientSecretValue"] == "[REDACTED]"
    assert item["payload"]["nested"]["providerAuthHeader"] == "[REDACTED]"
    assert item["payload"]["nested"]["status"] == "held"
    assert item["payload"]["not_finite"] == "[NON_FINITE]"
    assert item["payload"]["exception_type"] == "RuntimeError"
    assert _diagnostic_keys(item["payload"]) == set()

    encoded = raw.decode()
    for forbidden in (
        "provider-secret",
        "top-secret",
        "raw provider response",
        "sk-proj-private-value",
        "unprefixed-client-secret",
        "unprefixed-auth-secret",
        "secret stack",
        "hunter2",
    ):
        assert forbidden not in encoded


def test_idempotency_conflict_and_failed_replace_preserve_prior_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    state_path = tmp_path / "outbox.json"
    outbox = DurableObservabilityOutbox(state_path, clock_ns=lambda: 20_000_000_000)
    outbox.enqueue("first", idempotency_key="one", fields={"status": "pending"})
    before = state_path.read_bytes()

    with pytest.raises(OutboxIdempotencyConflictError):
        outbox.enqueue("first", idempotency_key="one", fields={"status": "changed"})
    assert state_path.read_bytes() == before

    def fail_replace(_source: Path, _destination: Path) -> None:
        raise OSError("simulated local filesystem failure")

    monkeypatch.setattr(outbox_module.os, "replace", fail_replace)
    with pytest.raises(OutboxUnavailableError):
        outbox.enqueue("second", idempotency_key="two")

    assert state_path.read_bytes() == before
    assert list(tmp_path.glob(".outbox.json.*.tmp")) == []


def test_delivery_requires_one_exact_matching_receipt(tmp_path: Path) -> None:
    state_path = tmp_path / "outbox.json"
    outbox = DurableObservabilityOutbox(state_path, clock_ns=lambda: 30_000_000_000)
    item = outbox.enqueue("alert_ready", idempotency_key="alert-1")
    receipt = _receipt(item)

    wrong_hash = {**receipt, "payload_sha256": "0" * 64}
    with pytest.raises(OutboxReceiptError):
        outbox.mark_delivered(wrong_hash)
    with pytest.raises(OutboxReceiptError):
        outbox.mark_delivered({**receipt, "extra": "not-accepted"})
    with pytest.raises(OutboxReceiptError):
        outbox.mark_delivered({**receipt, "event_id": "f" * 64})
    assert len(outbox.pending()) == 1

    delivered = outbox.mark_delivered(receipt)
    generation = outbox.health().generation
    assert delivered["delivery"] == receipt
    assert outbox.pending() == ()
    assert outbox.mark_delivered(receipt) == delivered
    assert outbox.health().generation == generation
    with pytest.raises(OutboxReceiptError):
        outbox.mark_delivered({**receipt, "receipt_id": "delivery-different"})


def test_sink_failure_or_invalid_receipt_leaves_event_pending(tmp_path: Path) -> None:
    outbox = DurableObservabilityOutbox(
        tmp_path / "outbox.json", clock_ns=lambda: 40_000_000_000
    )
    item = outbox.enqueue("alert_ready", idempotency_key="alert-for-sink")
    initial_generation = outbox.health().generation

    def failed_sink(_envelope: dict[str, Any]) -> dict[str, Any]:
        raise RuntimeError("provider failure with Bearer sink-secret")

    with pytest.raises(RuntimeError):
        outbox.deliver(item["event_id"], failed_sink)
    assert [pending["event_id"] for pending in outbox.pending()] == [item["event_id"]]
    assert outbox.health().generation == initial_generation

    with pytest.raises(OutboxReceiptError):
        outbox.deliver(item["event_id"], lambda _envelope: {"status": "accepted"})
    assert [pending["event_id"] for pending in outbox.pending()] == [item["event_id"]]
    assert outbox.health().generation == initial_generation

    delivered = outbox.deliver(item["event_id"], lambda envelope: _receipt(envelope))
    assert delivered["delivery"] == _receipt(item)
    assert outbox.pending() == ()


def test_thread_writer_lease_is_nonblocking(tmp_path: Path) -> None:
    outbox = DurableObservabilityOutbox(tmp_path / "outbox.json")
    entered = threading.Event()
    release = threading.Event()

    def hold_lock() -> None:
        with outbox._exclusive_writer():
            entered.set()
            release.wait(10)

    thread = threading.Thread(target=hold_lock, daemon=True)
    thread.start()
    assert entered.wait(5)
    started = time.perf_counter()
    try:
        with pytest.raises(OutboxBusyError):
            outbox.enqueue("thread_contended", idempotency_key="thread-lock")
        assert time.perf_counter() - started < 1.0
    finally:
        release.set()
        thread.join(5)
    assert not thread.is_alive()


def test_process_writer_lease_is_nonblocking_and_restart_safe(tmp_path: Path) -> None:
    outbox = DurableObservabilityOutbox(tmp_path / "outbox.json")
    context = multiprocessing.get_context("spawn")
    ready = context.Event()
    release = context.Event()
    process = context.Process(
        target=_hold_process_lock,
        args=(str(outbox.lock_path), ready, release),
    )
    process.start()
    try:
        assert ready.wait(10)
        started = time.perf_counter()
        with pytest.raises(OutboxBusyError):
            outbox.enqueue("process_contended", idempotency_key="process-lock")
        assert time.perf_counter() - started < 1.0
    finally:
        release.set()
        process.join(10)
        if process.is_alive():
            process.terminate()
            process.join(5)
    assert process.exitcode == 0

    item = outbox.enqueue("after_restart", idempotency_key="released-process-lock")
    assert outbox.pending()[0]["event_id"] == item["event_id"]


def test_count_age_and_byte_retention_are_bounded_and_reported(tmp_path: Path) -> None:
    clock = {"now": 100_000_000_000}
    counted = DurableObservabilityOutbox(
        tmp_path / "counted.json",
        max_events=2,
        max_age_seconds=5,
        clock_ns=lambda: clock["now"],
    )
    first = counted.enqueue("sample", idempotency_key="count-1")
    clock["now"] += 1
    second = counted.enqueue("sample", idempotency_key="count-2")
    clock["now"] += 1
    third = counted.enqueue("sample", idempotency_key="count-3")
    assert [item["event_id"] for item in counted.items()] == [
        second["event_id"],
        third["event_id"],
    ]
    assert first["event_id"] not in {item["event_id"] for item in counted.items()}
    assert counted.health().dropped_count == 1

    clock["now"] += 10_000_000_000
    age_health = counted.prune()
    assert counted.items() == ()
    assert age_health.dropped_age == 2
    assert age_health.healthy

    calibration = DurableObservabilityOutbox(
        tmp_path / "calibration.json", clock_ns=lambda: 200_000_000_000
    )
    calibration.enqueue("sample", idempotency_key="calibrate", fields={"blob": "x" * 700})
    one_item_bytes = calibration.health().state_bytes
    byte_bounded = DurableObservabilityOutbox(
        tmp_path / "byte-bounded.json",
        max_bytes=max(512, one_item_bytes + 100),
        clock_ns=lambda: 200_000_000_000,
    )
    byte_bounded.enqueue("sample", idempotency_key="bytes-1", fields={"blob": "x" * 700})
    newest = byte_bounded.enqueue(
        "sample", idempotency_key="bytes-2", fields={"blob": "y" * 700}
    )
    byte_health = byte_bounded.health()
    assert [item["event_id"] for item in byte_bounded.items()] == [newest["event_id"]]
    assert byte_health.dropped_bytes == 1
    assert byte_health.state_bytes <= byte_bounded.max_bytes


def test_oversize_event_is_rejected_without_creating_state(tmp_path: Path) -> None:
    state_path = tmp_path / "outbox.json"
    outbox = DurableObservabilityOutbox(
        state_path, max_bytes=512, clock_ns=lambda: 300_000_000_000
    )
    with pytest.raises(OutboxCapacityError):
        outbox.enqueue("oversize", idempotency_key="too-large", fields={"blob": "x" * 2_048})
    assert not state_path.exists()
    assert outbox.health().code == "ok"


def test_corruption_is_health_reportable_and_never_overwritten(tmp_path: Path) -> None:
    state_path = tmp_path / "outbox.json"
    outbox = DurableObservabilityOutbox(state_path, clock_ns=lambda: 400_000_000_000)
    outbox.enqueue("sample", idempotency_key="original", fields={"status": "pending"})
    tampered = json.loads(state_path.read_bytes())
    tampered["items"][0]["payload"]["status"] = "tampered-without-new-checksum"
    corrupt_bytes = _canonical(tampered)
    state_path.write_bytes(corrupt_bytes)

    health = outbox.health()
    assert not health.healthy
    assert health.code == "corrupt_state"
    assert health.generation is None
    with pytest.raises(OutboxCorruptionError):
        outbox.pending()
    with pytest.raises(OutboxCorruptionError):
        outbox.enqueue("later", idempotency_key="must-not-overwrite")
    assert state_path.read_bytes() == corrupt_bytes
