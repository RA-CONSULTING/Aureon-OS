import time

from aureon.bridges.validation_bridge import ValidationBridge


def test_protocol_blocks_missing_receipts_and_forwards_fresh_receipts_without_spawning(monkeypatch):
    bridge = ValidationBridge()
    calls = []
    monkeypatch.setattr(bridge, "send_auris_data", lambda *args, **kwargs: calls.append(("auris", kwargs)))
    monkeypatch.setattr(bridge, "send_aura_data", lambda *args, **kwargs: calls.append(("aura", kwargs)))

    blocked = bridge.run_validation_protocol([])

    assert blocked == {
        "truth_status": "no_data",
        "actionable": False,
        "generated_values": False,
        "blocker": "validators_not_started",
        "receipts": [],
    }
    assert calls == []
    assert bridge.auris_process is None
    assert bridge.aura_process is None

    now = time.time()
    receipt = {
        "source_id": "provider.test",
        "source_timestamp": now - 1,
        "received_at": now,
        "receipt_id": "receipt-1",
        "truth_status": "real_observed",
        "generated_values": False,
        "sample_data": [1.0, 2.0],
        "fund_hz": 7.83,
        "harmonics": [7.83],
        "gain": 1.0,
        "bands": {"alpha": 0.1},
        "hrv_rmssd": 1.0,
        "gsr_uS": 1.0,
        "resp_bpm": 1.0,
    }
    bridge.running = True

    stale = dict(receipt)
    stale["source_timestamp"] = now - 61
    stale_result = bridge.run_validation_protocol([stale], max_age_sec=60)

    assert stale_result["truth_status"] == "no_data"
    assert stale_result["actionable"] is False
    assert stale_result["blocker"] == "stale_receipt"
    assert calls == []

    forwarded = bridge.run_validation_protocol([receipt])

    assert forwarded["truth_status"] == "real_observed"
    assert forwarded["receipts"] == ["receipt-1"]
    assert [name for name, _ in calls] == ["auris", "aura"]
    assert calls[0][1]["receipt"]["source_timestamp"] != calls[0][1]["receipt"]["received_at"]
