"""Stage 3 and 4 read gate. No live order. No key value."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PIN = "bb04503119681adcf832f3c3e9b0cbf09fc7a938"

pytestmark = pytest.mark.timeout(180)


def _load(text: str) -> dict:
    return json.loads(text)


def test_read_gate_counts_leave_zero_and_trading_stays_closed() -> None:
    from aureon_public.body import OPEN_PLAN_THROUGH, package_depth
    from aureon_public.coverage_plan import plan_rows
    from aureon_public.guard_loader import PINNED_COMMIT

    assert PINNED_COMMIT == PIN
    assert OPEN_PLAN_THROUGH == 2
    rows = {row["package"]: row for row in plan_rows()}
    assert rows["miner"]["stage"] == 3
    assert rows["miner"]["reachable"] == 1
    assert rows["miner"]["tested"] == 1
    assert rows["queen"]["stage"] == 4
    assert rows["queen"]["reachable"] == 1
    assert rows["queen"]["tested"] == 1
    assert rows["exchanges"]["stage"] == 4
    assert rows["exchanges"]["reachable"] == 0
    assert rows["exchanges"]["tested"] == 0
    assert rows["accounting"]["reachable"] == 0
    assert rows["trading"]["reachable"] == 0
    depth = package_depth()
    assert depth["miner"]["reachable"] == 1
    assert depth["queen"]["reachable"] == 1
    assert depth["exchanges"]["reachable"] == 0
    stage3 = sum(row["reachable"] for row in rows.values() if row["stage"] == 3)
    stage4 = sum(row["reachable"] for row in rows.values() if row["stage"] == 4)
    assert stage3 == 1
    assert stage4 == 1


def test_tools_call_the_read_gate_and_do_not_place_orders(monkeypatch: pytest.MonkeyPatch) -> None:
    from aureon_public.body import body_call
    from aureon_public.stage34_gate import contains_env_secret
    from aureon_public.stage34_layer import (
        stage34_key_groups,
        stage34_miner_insight,
        stage34_queen_ground,
    )

    secret = "stage34-planted-secret-value"
    monkeypatch.setenv("KRAKEN_API_KEY", secret)
    monkeypatch.setenv("KRAKEN_API_SECRET", secret + "-other")
    monkeypatch.setenv("BINANCE_API_KEY", "")

    miner = _load(stage34_miner_insight())
    assert miner["called"] is True
    assert miner["status"] == "cited"
    assert miner["result"]["verdict"] == "NEUTRAL"
    assert miner["result"]["category"] == ""
    assert "bridge" not in json.dumps(miner["result"]).lower()

    queen = _load(stage34_queen_ground())
    assert queen["called"] is True
    assert queen["result"]["lambda_t"] == 1.0
    assert queen["result"]["grounded"] is True
    assert queen["result"]["correction_pulse"] == 0.0
    assert queen["result"]["lambda_zp"] == pytest.approx(0.16133)

    labels = _load(stage34_key_groups())
    assert labels["live_orders"] == "refused"
    assert labels["key_material"] == "not read"
    assert labels["trade_readiness"] == "HOLD"
    groups = {item["key_group"]: item["present"] for item in labels["key_groups"]}
    assert groups["redacted:kraken"] is True
    assert groups["absent:binance"] is False
    blob = json.dumps(labels)
    assert secret not in blob
    assert contains_env_secret(blob) is None
    assert os.environ["KRAKEN_API_KEY"] not in blob

    order = _load(body_call("trading/__init__.py", "__init__"))
    assert order.get("called") is not True
    assert order.get("live_orders") == "refused"
    equity = _load(
        body_call("exchanges/single_currency_equity.py", "gbp_equity_from_balances")
    )
    assert equity.get("called") is not True
    assert equity["reason"] == "operator entry point is not on aureon-public"
    bridge = _load(body_call("miner/miner_inhouse_ai_bridge.py", "get_miner_ai_bridge"))
    assert bridge.get("called") is not True
    assert bridge["status"] == "unavailable"


def test_stage34_sweep_record_blocks_network_and_names_the_pin() -> None:
    record = json.loads(
        (ROOT / "measured" / "aureon_public_stage34_call_sweep.json").read_text(encoding="utf-8")
    )
    assert record["schema"] == "aureon.public.stage34-call-sweep.v1"
    assert record["pin"] == PIN
    assert record["sockets"] == "blocked"
    assert record["processes"] == "blocked"
    assert record["live_orders"] == "refused"
    assert record["key_material"] == "not read"
    assert record["writes"] == "outside sandbox blocked"
    entries = {(row["module"], row["symbol"]): row for row in record["entries"]}
    assert len(entries) == 2
    for row in entries.values():
        assert row["refused"] is False
        assert row["called"] is True
        assert row["socket"] == []
        assert row["bad"] == []
        assert row["process"] == []
        real = row["attempts"][-1]
        assert real["label"] == "read_gate"
        assert real["called"] is True
        assert real["refusal"] is None
    labels = {item["key_group"] for item in record["key_groups"]}
    assert labels <= {f"redacted:{name}" for name in ("kraken", "capital", "alpaca", "binance")} | {
        f"absent:{name}" for name in ("kraken", "capital", "alpaca", "binance")
    }
    text = json.dumps(record)
    assert "api_key" not in text.lower()
    assert "secret" not in text.lower()
    for item in record["key_groups"]:
        assert item["key_group"].startswith(("redacted:", "absent:"))
        assert set(item) == {"key_group", "present"}
