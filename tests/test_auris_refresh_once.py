from __future__ import annotations

import json
from pathlib import Path

import pytest

from aureon.intelligence.dr_auris_throne import CosmicState, DrAurisThrone


def _bare_throne(state: CosmicState):
    throne = object.__new__(DrAurisThrone)
    throne._cycle_count = 0
    throne._state = CosmicState()
    published: list[CosmicState] = []
    alerted: list[CosmicState] = []
    throne._analyze_cosmos = lambda: state
    throne._publish_state = published.append
    throne._publish_alert = alerted.append
    return throne, published, alerted


def test_refresh_once_uses_same_state_publication_without_worker() -> None:
    state = CosmicState(data_status="live", coherence_gamma=0.95, gate_open=True)
    throne, published, alerted = _bare_throne(state)

    result = throne.refresh_once()

    assert result is state
    assert throne.get_state() is state
    assert throne._cycle_count == 1
    assert published == [state]
    assert alerted == []
    assert getattr(throne, "_thread", None) is None


def test_refresh_once_preserves_existing_extreme_condition_alert() -> None:
    state = CosmicState(kp_index=6.0, earth_disturbance=0.8, bz_component=-11.0)
    throne, published, alerted = _bare_throne(state)

    throne.refresh_once()

    assert published == [state]
    assert alerted == [state]


def test_publish_state_persists_cross_process_trace_without_thought_bus(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("AUREON_BUS_TRACE_DIR", str(tmp_path))
    throne = object.__new__(DrAurisThrone)
    throne._thought_bus = None
    throne._cycle_count = 1
    state = CosmicState(data_status="no_data", receipt_id="auris:no_data:test")

    throne._publish_state(state)

    trace_path = tmp_path / "auris_cosmic_state.jsonl"
    rows = [json.loads(line) for line in trace_path.read_text(encoding="utf-8").splitlines()]
    assert rows[-1]["receipt_id"] == "auris:no_data:test"
    assert rows[-1]["_ts"] == state.received_at


def test_read_latest_hnc_receipt_falls_back_to_cross_process_trace(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("AUREON_BUS_TRACE_DIR", str(tmp_path))
    hnc_receipt = {
        "data_status": "live",
        "receipt_id": "hnc:live_field:test-cross-process",
        "receipt_type": "hnc_live_field",
        "source_timestamp": 1_786_435_000.0,
        "received_at": 1_786_435_000.1,
        "truth_status": "real_derived",
        "generated_values": False,
        "input_receipt_ids": ["provider:test:1"],
        "coherence_gamma": 0.91,
    }
    (tmp_path / "hnc_live_trace.jsonl").write_text(
        json.dumps(hnc_receipt) + "\n",
        encoding="utf-8",
    )
    throne = object.__new__(DrAurisThrone)
    throne._thought_bus = None

    assert throne._read_latest_hnc_receipt() == hnc_receipt
