"""Offline market-series pack. The live fetch is the module command, not this file."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "market_series"
PIN = "0646146c53e59dbcab41363a613d5651c9c9d50f"
_PUBLIC_PREFIXES = (
    "https://api.binance.com/api/v3/",
    "https://api.kraken.com/0/public/",
)


def _read(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def _kraken_transport(url: str) -> tuple[int, bytes]:
    if "binance.com" in url:
        return 451, b"<html>super-secret-value-xyz</html>"
    if "OHLC" in url:
        return 200, _read("kraken_ohlc.json")
    if "Spread" in url:
        return 200, _read("kraken_spread.json")
    raise AssertionError(url)


def _binance_transport(url: str) -> tuple[int, bytes]:
    if "klines" in url:
        return 200, _read("binance_klines.json")
    if "bookTicker" in url:
        return 200, _read("binance_book.json")
    raise AssertionError(url)


def test_kraken_fixture_derives_measured_inputs_and_drops_the_open_bar() -> None:
    from aureon.evaluation.market_series import fetch_public_pack, verify_pack

    pack = fetch_public_pack(_kraken_transport, fetched_at="2026-11-05T00:00:00Z")
    assert pack["verdict"] == "loaded"
    assert pack["key_group"] == "public:kraken"
    assert pack["symbol"] == "XBTUSD"
    assert pack["authenticated"] is False
    assert pack["key_material"] == "none"
    assert pack["orders_placed"] is False
    assert pack["live_trading"] is False
    assert pack["bar_count"] == 12
    assert pack["bars"][-1]["close"] == 112
    assert pack["bars"][0]["close"] == 100
    assert "return" not in pack["bars"][0]
    assert pack["auris_inputs"]["momentum"] == pytest.approx(0.12)
    assert pack["auris_inputs"]["volume"] == pytest.approx(0.625)
    assert pack["auris_inputs"]["spread"] == pytest.approx(0.5 / 112.25)
    ranges = [2.0 / close for close in (100, 102, 101, 103, 104, 106, 105, 107, 108, 110, 109, 112)]
    assert pack["auris_inputs"]["volatility"] == pytest.approx(sum(ranges) / len(ranges))
    for field in pack["fields"].values():
        assert field["evidence_tag"] == "measured"
    assert pack["time_range"]["start"] == "2023-11-14T22:13:20Z"
    assert pack["spread_time_range"]["prints"] == 2
    assert pack["attempts"][0]["venue"] == "binance"
    assert pack["attempts"][0]["http_status"] == 451
    assert pack["attempts"][0]["used"] is False
    blob = json.dumps(pack)
    assert "super-secret-value-xyz" not in blob
    assert verify_pack(pack) == []


def test_binance_fixture_is_labeled_public_binance(monkeypatch: pytest.MonkeyPatch) -> None:
    from aureon.evaluation.market_series import fetch_public_pack

    monkeypatch.setenv("BINANCE_API_SECRET", "another-secret-value")
    pack = fetch_public_pack(_binance_transport, fetched_at="2026-11-05T00:00:00Z")
    assert pack["key_group"] == "public:binance"
    assert pack["symbol"] == "BTCUSDT"
    assert pack["parser"] == "binance-klines-v1"
    assert pack["bar_count"] == 10
    assert pack["auris_inputs"]["spread"] == pytest.approx(0.5 / 100.25)
    assert "another-secret-value" not in json.dumps(pack)
    assert pack["provenance"]["key_material"] == "none"


def test_fetch_stays_on_public_urls_and_writes_no_secret(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from aureon.evaluation.market_series import fetch_public_pack, write_pack

    seen: list[str] = []

    def transport(url: str) -> tuple[int, bytes]:
        seen.append(url)
        return _kraken_transport(url)

    monkeypatch.setenv("KRAKEN_API_KEY", "super-secret-value-xyz")
    pack = fetch_public_pack(transport, fetched_at="2026-11-05T00:00:00Z")
    assert seen
    assert all(url.startswith(_PUBLIC_PREFIXES) for url in seen)
    assert all("private" not in url and "order" not in url.casefold() for url in seen)
    written = write_pack(tmp_path, pack)
    text = (tmp_path / "market_series.json").read_text(encoding="utf-8")
    assert "super-secret-value-xyz" not in text
    assert written["verdict"] == "loaded"
    rows = list(csv.DictReader((tmp_path / "market_series.csv").open(encoding="utf-8")))
    assert len(rows) == 12
    assert rows[0]["return"] == ""
    assert float(rows[-1]["close"]) == 112
    spread_rows = list(csv.DictReader((tmp_path / "market_spread.csv").open(encoding="utf-8")))
    assert len(spread_rows) == 2
    assert "AUREON_DISABLE_REAL_ORDERS=1" in (tmp_path / "market_series.md").read_text(encoding="utf-8")


def test_both_venues_down_writes_a_hold_receipt_without_prices(tmp_path: Path) -> None:
    from aureon.evaluation.market_series import fetch_public_pack, write_pack

    def transport(url: str) -> tuple[int, bytes]:
        if not url.startswith(_PUBLIC_PREFIXES):
            raise AssertionError(url)
        return 503, b"upstream"

    pack = fetch_public_pack(transport, fetched_at="2026-11-05T00:00:00Z")
    assert pack["verdict"] == "HOLD"
    assert pack["bars"] == []
    assert pack["auris_inputs"] == {}
    assert pack["key_group"] is None
    assert "invented" in pack["reason"]
    write_pack(tmp_path, pack)
    assert not (tmp_path / "market_series.csv").exists()
    saved = json.loads((tmp_path / "market_series.json").read_text(encoding="utf-8"))
    assert saved["verdict"] == "HOLD"
    assert saved["orders_placed"] is False


def test_brain_proof_consumes_a_pack_and_names_deer_when_spread_is_absent(tmp_path: Path) -> None:
    from aureon.evaluation.brain_proof import _market_qgita, _run_auris
    from aureon.evaluation.market_series import (
        fetch_public_pack,
        load_market_series,
        write_pack,
    )

    pack = fetch_public_pack(_kraken_transport, fetched_at="2026-11-05T00:00:00Z")
    pack["spread_prints"] = []
    pack["fields"].pop("spread", None)
    pack["auris_inputs"].pop("spread", None)
    pack["spread_source"] = None
    pack["spread_time_range"] = None
    write_pack(tmp_path / "reports" / "measured", pack)
    loaded = load_market_series(tmp_path)
    assert loaded["verdict"] == "loaded"
    report = _run_auris(loaded)
    assert report["market_data"] is not None
    assert "spread" not in report["market_data"]
    assert report["market_data"]["volatility"] == pack["auris_inputs"]["volatility"]
    assert report["market_nodes_without_reading"] == ["Deer"]
    assert "Clownfish" not in report["market_nodes_without_reading"]
    assert "Owl" not in report["market_nodes_without_reading"]
    assert report["coherence"] is None
    assert report["coherence_status"] == "no_data"
    reason = report["trade_readiness"]["reason"].casefold()
    assert "no market series" not in reason
    assert "no trade-outcome labels" not in reason
    assert "deer" in reason
    assert "no spread prints" in reason
    diagnosis = report["trade_readiness"]["diagnosis"]
    assert diagnosis["spread_clock"]["prints"] == 0
    assert diagnosis["orders_placed"] is False
    assert diagnosis["live_trading"] is False
    assert diagnosis["formula_ceiling"]["ready_marks"] == 0
    assert report["trade_readiness"]["verdict"] == "fail"
    assert report["trade_readiness"]["evidence_tag"] == "measured"
    assert report["trade_readiness"]["outcome_labels"] == "paper"
    assert report["trade_readiness"]["filled_outcomes"] == 0
    assert report["trade_readiness"]["release_boundary"] == "HOLD"
    assert report["trade_readiness"]["orders_placed"] is False
    assert report["trade_readiness"]["clownfish_readings"] == report["trade_readiness"]["paper_labels"]
    assert report["trade_readiness"]["owl_readings"] == report["trade_readiness"]["paper_labels"]
    assert report["orders_placed"] is False
    assert report["omitted_call"]["status"] == "no_data"
    qgita = _market_qgita(loaded)
    assert qgita["evidence_tag"] == "measured"
    assert qgita["rates_verdict"] == "HOLD"
    assert qgita["detection_rate"] is None
    assert qgita["false_alarm_rate"] is None
    assert "synthetic_planted" in qgita["rates_reason"]
    assert qgita.get("tag") != "synthetic_planted"
    assert "signal_in_noise" not in qgita
    assert qgita["orders_placed"] is False
    assert qgita["samples_fed"] == 12


def test_missing_pack_still_says_there_is_no_market_series(tmp_path: Path) -> None:
    from aureon.evaluation.brain_proof import _market_qgita, _run_auris
    from aureon.evaluation.market_series import load_market_series

    pack = load_market_series(tmp_path)
    assert pack["verdict"] == "absent"
    report = _run_auris(pack)
    assert report["market_data"] is None
    assert report["nodes"] is None
    assert report["market_nodes_without_reading"] is None
    assert "no market series" in report["trade_readiness"]["reason"]
    assert report["trade_readiness"]["verdict"] == "HOLD"
    qgita = _market_qgita(pack)
    assert qgita["verdict"] == "HOLD"
    assert qgita["evidence_tag"] == "hold"


def test_full_fixture_gives_clownfish_and_owl_a_reading() -> None:
    from aureon.evaluation.brain_proof import _run_auris
    from aureon.evaluation.market_series import fetch_public_pack

    pack = fetch_public_pack(_kraken_transport, fetched_at="2026-11-05T00:00:00Z")
    report = _run_auris(pack)
    assert report["market_nodes_without_reading"] == []
    assert isinstance(report["coherence"], float)
    assert report["coherence_evidence"] == "measured"
    nodes = report["nodes"]
    assert nodes["Clownfish"]["data_status"] == "reading"
    assert nodes["Owl"]["data_status"] == "reading"
    assert nodes["Deer"]["value"] == pytest.approx(pack["auris_inputs"]["spread"])
    trade = report["trade_readiness"]
    reason = trade["reason"].casefold()
    assert "no market series" not in reason
    assert "no trade-outcome labels" not in reason
    assert trade["verdict"] in {"pass", "fail"}
    assert trade["evidence_tag"] == "measured"
    assert trade["outcome_labels"] == "paper"
    assert trade["filled_outcomes"] == 0
    assert trade["release_boundary"] == "HOLD"
    assert trade["orders_placed"] is False
    assert trade["paper_labels"] > 0
    assert trade["clownfish_readings"] == trade["paper_labels"]
    assert trade["owl_readings"] == trade["paper_labels"]
    assert all(row["filled"] is False and row["outcome_kind"] == "paper" for row in trade["labels"])
    assert all(row["return_evidence"] == "measured" for row in trade["labels"])


def test_committed_pack_is_public_and_the_pin_stays() -> None:
    from aureon.evaluation.brain_proof import _run_auris
    from aureon.evaluation.market_series import load_market_series, verify_pack

    pack = load_market_series(ROOT)
    assert pack["verdict"] == "loaded"
    assert pack["key_group"] in {"public:kraken", "public:binance"}
    assert pack["authenticated"] is False
    assert pack["orders_placed"] is False
    assert pack["key_material"] == "none"
    assert pack["live_autonomy"] is False
    assert verify_pack(pack) == []
    assert pack["time_range"]["start"]
    assert pack["time_range"]["end"]
    assert pack["bar_count"] >= 10
    blob = json.dumps(pack).casefold()
    for token in ("api_key", "api_secret", "passphrase", "private_key"):
        assert token not in blob
    rows = list(csv.DictReader((ROOT / "reports/measured/market_series.csv").open(encoding="utf-8")))
    assert len(rows) == pack["bar_count"]
    assert float(rows[0]["close"]) == pytest.approx(pack["bars"][0]["close"])
    assert float(rows[-1]["open_time"]) == pytest.approx(pack["bars"][-1]["open_time"])
    report = _run_auris(pack)
    assert report["market_data"] is not None
    trade = report["trade_readiness"]
    reason = trade["reason"].casefold()
    assert "no market series" not in reason
    assert "no trade-outcome labels" not in reason
    assert trade["verdict"] in {"pass", "fail"}
    assert trade["evidence_tag"] == "measured"
    assert trade["outcome_labels"] == "paper"
    assert trade["filled_outcomes"] == 0
    assert trade["release_boundary"] == "HOLD"
    assert trade["orders_placed"] is False
    assert trade["real_orders"] == "AUREON_DISABLE_REAL_ORDERS=1"
    assert trade["clownfish_readings"] == trade["paper_labels"]
    assert trade["owl_readings"] == trade["paper_labels"]
    assert "Clownfish" not in trade["nodes_without_reading_on_a_label"]
    assert "Owl" not in trade["nodes_without_reading_on_a_label"]
    if "volatility" in report["market_data"]:
        assert "Clownfish" not in report["market_nodes_without_reading"]
    if "momentum" in report["market_data"]:
        assert "Owl" not in report["market_nodes_without_reading"]
    if "spread" not in report["market_data"]:
        assert "Deer" in report["market_nodes_without_reading"]
    diagnosis = trade["diagnosis"]
    clock = diagnosis["spread_clock"]
    ceiling = diagnosis["formula_ceiling"]
    ladder = diagnosis["status_ladder"]
    assert trade["verdict"] == "fail"
    assert "Deer" in trade["nodes_without_reading_on_a_label"]
    assert clock["prints"] > 0
    assert clock["prints_at_or_before_last_labelled_close"] == 0
    assert clock["labels_with_spread_known"] == 0
    assert clock["first_print_minus_last_labelled_close_seconds"] > 0
    assert diagnosis["labelled_bars_with_coherence"] == 0
    assert diagnosis["labelled_bars_no_data"] == trade["paper_labels"]
    assert diagnosis["window_matches_final_else"] is True
    assert diagnosis["ready_mark_below_sweep"] is True
    assert diagnosis["orders_placed"] is False
    assert diagnosis["live_trading"] is False
    assert ceiling["ready_marks"] == 0
    assert ceiling["highest_coherence"] < ladder["ready_threshold"]
    assert ceiling["confirmation_grid_exceeded_corner"] is False
    assert "Ready to trade" not in ceiling["highest_status"]
    assert "does not change the node formulas" in diagnosis["next_stage"]
    assert "does not invent outcome labels" in diagnosis["next_stage"]
    assert "later spread print" in diagnosis["next_stage"]
    ready = next(item for item in ladder["compares"] if item["ready_mark"])
    buried = next(item for item in ladder["compares"] if item["op"] == ">" and item["threshold"] > 0.9)
    assert ready["threshold"] > buried["threshold"]
    assert ladder["compares"].index(ready) < ladder["compares"].index(buried)
    assert PIN in (ROOT / "mcp" / "pyproject.toml").read_text(encoding="utf-8")
    assert PIN in (ROOT / "mcp" / "aureon_public" / "guard_loader.py").read_text(encoding="utf-8")


def test_check_command_does_not_fetch(monkeypatch: pytest.MonkeyPatch) -> None:
    from aureon.evaluation import market_series

    def boom(url: str, timeout: float = 20.0) -> tuple[int, bytes]:
        raise AssertionError(url)

    monkeypatch.setattr(market_series, "http_get", boom)
    assert market_series.main(["--check", "--out", str(ROOT / "reports" / "measured")]) == 0
