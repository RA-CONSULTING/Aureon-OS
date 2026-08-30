"""The HNC + Auris stack fires on REAL open historical data — no API keys.

Replays the bundled provenance-stamped Kraken public OHLC datasets (real
exchange history) through the real components and pins the calibration
verdicts: signals observed, capital preserved in downtrends, honest
blockers when a dataset is missing, deterministic artifacts.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from aureon.analytics.historical_replay_validation import (
    ABLATION_GATES,
    DATA_DIR,
    INTERVALS,
    SYMBOLS,
    _equity_walk,
    _trade_stats,
    compute_replay_validation,
    load_ohlc,
    replay_symbol,
    validate_dataset,
)

_HAVE_DATA = all(
    (DATA_DIR / f"kraken_ohlc_{s}_{iv}m.json").exists()
    for s in SYMBOLS for iv in INTERVALS)

pytestmark = pytest.mark.skipif(
    not _HAVE_DATA,
    reason="bundled open datasets missing — refetch with "
           "`python -m aureon.analytics.historical_replay_validation --refresh`",
)


@pytest.fixture(scope="module")
def bundled_report():
    """One full 6-replay sweep, shared by every verdict test (deterministic)."""
    return compute_replay_validation()


def test_datasets_are_real_and_provenance_stamped():
    for sym in SYMBOLS:
        for interval in INTERVALS:
            payload = load_ohlc(sym, interval_minutes=interval)
            assert payload is not None
            prov = payload["provenance"]
            assert "Kraken public" in prov["source"]
            assert "not synthetic" in prov["kind"]
            assert prov["interval_minutes"] == interval
            assert len(payload["candles"]) >= 500, (
                "a real month of hourly candles / ~2 years of daily candles")


def test_replay_produces_real_hnc_and_auris_observables():
    payload = load_ohlc("BTCUSD")
    r = replay_symbol(payload)
    # the Auris nodes actually moved on the real data — not a constant
    assert r.auris_coherence_max > r.auris_coherence_min
    assert 0.0 < r.auris_coherence_mean < 1.0
    # the field computed a real Γ and the observer classified the timeline
    assert 0.0 < r.gamma_mean < 1.0
    assert sum(r.observer_regime_counts.values()) == r.candles
    assert r.vol_assessments_ok > 0, "the sentinel measured real expansion risk"
    # fee-inclusive accounting is self-consistent
    assert r.fees_paid_pct == pytest.approx(
        r.n_position_changes * 0.26, abs=1e-6)


def test_validation_verdicts_on_bundled_data(bundled_report):
    report = bundled_report
    assert not report.blockers
    assert report.total_candles >= 4000, "both real horizons replayed"
    assert report.any_symbol_produced_signals, (
        "the stack must fire at least one entry signal on this real history"
    )
    assert report.capital_preserved_in_downtrends, (
        "the gated strategy must never draw down MORE than buy-and-hold"
    )
    for s in report.symbols:
        assert s["max_drawdown_pct"] <= s["buy_hold_max_drawdown_pct"] + 1e-9


def test_profit_margin_benchmark_measured_on_both_horizons(bundled_report):
    report = bundled_report
    # round-trip margins exist and aggregate coherently
    assert report.total_round_trips > 0
    assert report.overall_win_rate is not None and 0.0 <= report.overall_win_rate <= 1.0
    assert set(report.margin_attribution) == {f"{iv}m" for iv in INTERVALS}
    for att in report.margin_attribution.values():
        # the full HNC gate stack must out-margin ungated momentum on this
        # real bundled history (measured +19.6% hourly / +39.0% daily at pin
        # time) and must cut mean max drawdown vs buy-and-hold
        assert att["hnc_edge_vs_momentum_only_pct"] > 0.0
        assert att["mean_max_dd_hnc_full_pct"] < att["mean_max_dd_buy_hold_pct"]
        # the walk-forward Γ tighten never costs margin on the bundled data
        # (measured +0.00% hourly / +10.23% daily at pin time)
        assert att["gamma_edge_vs_hnc_full_pct"] >= 0.0


def test_ablation_gate_ladder_is_structurally_monotone(bundled_report):
    """Each added gate can only REMOVE long candles (subset property)."""
    report = bundled_report
    for s in report.symbols:
        abl = s["ablations"]
        assert set(abl) == set(ABLATION_GATES)
        assert (abl["gamma_tightened"]["long_candles"]
                <= abl["hnc_full"]["long_candles"]
                <= abl["no_sentinel_veto"]["long_candles"]
                <= abl["probability_only"]["long_candles"]
                <= abl["buy_hold"]["long_candles"])
        assert abl["momentum_only"]["long_candles"] <= abl["buy_hold"]["long_candles"]
        # Γ-conditioned split covers every decided candle exactly once
        gc = s["gamma_conditioned"]
        assert gc["n_above"] + gc["n_below"] == s["candles"] - 1


def test_trade_stats_math_hand_computed():
    """Pure accounting check on a tiny labeled example (no market claim)."""
    closes = [100.0, 110.0, 110.0, 121.0]
    positions = [1, 0, 1]  # trade 1: 100→110; trade 2: 110→121 (held to end)
    stats = _trade_stats(closes, positions)
    per_trade = (1.1 * (1.0 - 0.0026) ** 2 - 1.0) * 100.0
    assert stats["n_round_trips"] == 2
    assert stats["win_rate"] == 1.0
    assert stats["avg_trade_net_pct"] == pytest.approx(per_trade, abs=1e-3)
    assert stats["avg_hold_candles"] == 1.0
    # compounding the round trips reproduces the equity walk exactly
    walk_ret, _dd, _ch, _fees = _equity_walk(closes, positions)
    compounded = ((1.0 + per_trade / 100.0) ** 2 - 1.0) * 100.0
    assert walk_ret == pytest.approx(compounded, abs=1e-9)


def test_missing_dataset_is_a_named_blocker(tmp_path):
    report = compute_replay_validation(data_dir=tmp_path)
    assert len(report.blockers) == len(SYMBOLS) * len(INTERVALS)
    assert all("refetch" in b for b in report.blockers)
    assert report.symbols == []
    assert report.any_symbol_produced_signals is False
    assert report.total_round_trips == 0 and report.overall_win_rate is None


def test_replay_is_deterministic():
    payload = load_ohlc("SOLUSD")
    assert replay_symbol(payload).to_dict() == replay_symbol(payload).to_dict()


def test_corrupt_dataset_refused(tmp_path):
    bad = tmp_path / "kraken_ohlc_BTCUSD_60m.json"
    bad.write_text("{not json", encoding="utf-8")
    assert load_ohlc("BTCUSD", data_dir=tmp_path) is None


def test_bundled_datasets_are_chronological_and_integral():
    """Every bundled dataset passes chronology + OHLC integrity with zero
    violations (measured: strictly ascending, zero gaps, invariants hold)."""
    for sym in SYMBOLS:
        for interval in INTERVALS:
            payload = load_ohlc(sym, interval_minutes=interval)
            assert payload is not None
            assert validate_dataset(payload) == []
            ts = [float(c["ts"]) for c in payload["candles"]]
            # contiguous real series: every step exactly one interval
            assert all(
                b - a == interval * 60 for a, b in zip(ts[:-1], ts[1:], strict=True))


def _tampered(payload, mutate):
    doc = json.loads(json.dumps(payload))  # deep copy
    mutate(doc["candles"])
    return doc


def test_tampered_chronology_or_ohlc_is_refused(tmp_path):
    base = load_ohlc("BTCUSD")
    assert base is not None

    def swap_ts(cs):  # backwards timestamp
        cs[5]["ts"], cs[6]["ts"] = cs[6]["ts"], cs[5]["ts"]

    def break_ohlc(cs):  # high below low
        cs[3]["high"] = cs[3]["low"] - 1.0

    def negative_volume(cs):
        cs[7]["volume"] = -1.0

    def misaligned_gap(cs):  # timestamp off the interval grid
        cs[9]["ts"] = float(cs[9]["ts"]) + 17.0

    for i, mutate in enumerate((swap_ts, break_ohlc, negative_volume, misaligned_gap)):
        doc = _tampered(base, mutate)
        assert validate_dataset(doc), f"mutation {i} must be caught"
        p = tmp_path / f"case{i}" / "kraken_ohlc_BTCUSD_60m.json"
        p.parent.mkdir(parents=True)
        p.write_text(json.dumps(doc), encoding="utf-8")
        assert load_ohlc("BTCUSD", data_dir=p.parent) is None, (
            f"mutation {i}: a tampered series must never replay")


def test_artifact_written_by_cli_matches_module(tmp_path, bundled_report):
    from aureon.analytics.historical_replay_validation import write_replay_report

    report = bundled_report
    out = write_replay_report(report, tmp_path / "replay.json")
    loaded = json.loads(Path(out.out_path).read_text(encoding="utf-8"))
    assert loaded["any_symbol_produced_signals"] == report.any_symbol_produced_signals
    assert loaded["boundary"] == report.boundary
