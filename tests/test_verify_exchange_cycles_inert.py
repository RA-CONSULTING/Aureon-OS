from __future__ import annotations

import importlib.util
import json
import os
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validation" / "verify_exchange_cycles.py"


def _load_module():
    name = "_test_verify_exchange_cycles"
    sys.modules.pop(name, None)
    spec = importlib.util.spec_from_file_location(name, SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _complete_fill(now: float) -> dict:
    return {
        "data_status": "live",
        "truth_status": "real_observed",
        "generated_values": False,
        "status": "FILLED",
        "fill_receipt_complete": True,
        "eligible_for_accounting": True,
        "reconciliation_required": False,
        "source_id": "kraken:QueryOrders",
        "source_timestamp": now - 2.0,
        "received_at": now - 1.0,
        "receipt_id": "receipt-1",
        "provider_order_id": "order-1",
        "provider_trade_ids": ["trade-1"],
        "executed_quantity": 2.0,
        "average_price": 10.0,
        "quote_quantity": 20.0,
        "total_fee": 0.1,
        "fee_currency": "USD",
    }


def test_import_and_default_cli_are_provider_inert(tmp_path, monkeypatch, capsys):
    sentinels = {
        "DRY_RUN": "sentinel-dry",
        "LIVE": "sentinel-live",
        "KRAKEN_DRY_RUN": "sentinel-kraken",
        "BINANCE_DRY_RUN": "sentinel-binance",
        "ALPACA_DRY_RUN": "sentinel-alpaca",
    }
    for key, value in sentinels.items():
        monkeypatch.setenv(key, value)
    monkeypatch.chdir(tmp_path)

    module = _load_module()

    assert {key: os.environ[key] for key in sentinels} == sentinels
    assert module.main([]) == 2
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "no_data"
    assert report["reason"] == "receipt_file_required"
    assert report["actionable"] is False
    assert report["eligible_for_accounting"] is False
    assert report["eligible_for_learning"] is False
    assert not (tmp_path / "exchange_verification_results.json").exists()

    source = SCRIPT.read_text(encoding="utf-8")
    for forbidden in (
        "place_market_order",
        "convert_crypto",
        "get_kraken_client",
        "AlpacaClient",
        "BinanceClient",
    ):
        assert forbidden not in source


def test_terminal_receipt_contract_rejects_unproven_values():
    module = _load_module()
    now = 1_800_000_000.0
    complete = _complete_fill(now)
    assert module._terminal_fill(complete, now=now) is True

    pending = {**complete, "status": "pending_reconciliation"}
    assert module._terminal_fill(pending, now=now) is False

    generated = {**complete, "generated_values": True}
    assert module._terminal_fill(generated, now=now) is False

    stale = {
        **complete,
        "source_timestamp": now - 1_000.0,
        "received_at": now - 999.0,
    }
    assert module._terminal_fill(stale, now=now) is False

    mismatched_notional = {**complete, "quote_quantity": 25.0}
    assert module._terminal_fill(mismatched_notional, now=now) is False

    naive_timestamp = {
        **complete,
        "source_timestamp": "2027-01-15T12:00:00",
        "received_at": "2027-01-15T12:00:01",
    }
    assert module._terminal_fill(naive_timestamp, now=now) is False


def test_cli_verifies_only_complete_receipts_and_writes_only_when_requested(
    tmp_path, capsys
):
    module = _load_module()
    now = time.time()
    receipt_path = tmp_path / "provider_receipts.json"
    receipt_path.write_text(
        json.dumps({"receipts": [_complete_fill(now)]}),
        encoding="utf-8",
    )

    assert module.main(["--receipts", str(receipt_path)]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "verified"
    assert report["truth_status"] == "real_derived"
    assert report["source_id"] == "exchange_receipt_contract_audit"
    assert report["source_timestamp"] == now - 2.0
    assert report["input_receipt_ids"] == ["receipt-1"]
    assert report["receipt_id"].startswith("exchange-receipt-audit:")
    assert report["actionable"] is False
    assert report["eligible_for_accounting"] is False
    assert report["eligible_for_learning"] is False

    output_path = tmp_path / "explicit_audit.json"
    assert module.main(
        [
            "--receipts",
            str(receipt_path),
            "--output",
            str(output_path),
        ]
    ) == 0
    written = json.loads(output_path.read_text(encoding="utf-8"))
    assert written["status"] == "verified"
    assert written["input_receipt_ids"] == ["receipt-1"]
    capsys.readouterr()

    assert module.main(["--live"]) == 2
    live_report = json.loads(capsys.readouterr().out)
    assert live_report["status"] == "no_data"
    assert live_report["reason"] == "live_submission_disabled"
