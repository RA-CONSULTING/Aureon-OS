"""Volatility Sentinel (P2): every number is measured, never invented.

Covers: the EWMA estimator against hand-computed values, warm-up honesty
(None, not a placeholder), volatility-expansion detection, fusion weight
renormalization + escalation, the zero-input no_data contract with named
blockers, the conservative portfolio roll-up, and the publish/read freshness
contract (stale and unstamped rows refused).
"""

import math
import random

import pytest

from aureon.intelligence.volatility_sentinel import (
    ESCALATION_RISK,
    WARMUP_FAST,
    WARMUP_SLOW,
    EwmaVolEstimator,
    FactorReading,
    VolatilityAssessment,
    VolatilitySentinel,
    read_latest_assessment,
)

# ── EwmaVolEstimator ─────────────────────────────────────────────────


def test_ewma_matches_hand_computation():
    """σ² recursions reproduce the formula to 1e-9 on a deterministic series."""
    est = EwmaVolEstimator(lambda_fast=0.94, lambda_slow=0.997)
    prices = [100.0, 101.0, 100.5, 102.0, 101.2]
    for p in prices:
        est.update(p)

    s2f = s2s = None
    last = None
    for p in prices:
        if last is None:
            last = p
            continue
        r2 = math.log(p / last) ** 2
        last = p
        if s2f is None:
            s2f = s2s = r2
        else:
            s2f = 0.94 * s2f + 0.06 * r2
            s2s = 0.997 * s2s + 0.003 * r2

    got_f, got_s = est.sigmas()
    assert got_f == pytest.approx(math.sqrt(s2f), abs=1e-9)
    assert got_s == pytest.approx(math.sqrt(s2s), abs=1e-9)


def test_ewma_warmup_returns_none_not_a_placeholder():
    est = EwmaVolEstimator()
    price = 100.0
    for _ in range(WARMUP_FAST - 1):
        price *= 1.001
        est.update(price)
    assert est.risk() is None, "an unmeasured risk must be None, never a default"


def test_ewma_detects_volatility_expansion():
    """Flat baseline then a 10x-vol regime pushes risk decisively up."""
    rng = random.Random(11)
    est = EwmaVolEstimator()
    price = 100.0
    for _ in range(WARMUP_SLOW + 50):
        price *= 1.0 + rng.gauss(0.0, 0.001)
        est.update(price)
    calm = est.risk()
    assert calm is not None and calm < 0.4

    for _ in range(40):
        price *= 1.0 + rng.gauss(0.0, 0.010)
        est.update(price)
    stressed = est.risk()
    assert stressed is not None
    assert stressed > 0.6
    assert stressed > calm


def test_ewma_flat_series_risk_zero():
    est = EwmaVolEstimator()
    for _ in range(WARMUP_SLOW + 10):
        est.update(100.0)
    assert est.risk() == pytest.approx(0.0)


# ── fusion ───────────────────────────────────────────────────────────


def _sentinel_with_factors(monkeypatch, readings):
    """A sentinel whose four factor methods return the given FactorReadings."""
    s = VolatilitySentinel(symbols=["BTC/USD"])
    names = ["_factor_ewma", "_factor_phase", "_factor_qgita", "_factor_surge"]
    for name, reading in zip(names, readings, strict=True):
        monkeypatch.setattr(s, name, lambda symbol, _r=reading: _r)
    return s


def test_fusion_renormalizes_over_available_factors(monkeypatch):
    readings = [
        FactorReading("ewma_vol", 0.6, 0.35, "ok", ""),
        FactorReading("phase_transition", None, 0.25, "no_data", "phase: warm-up"),
        FactorReading("qgita_regime", 0.2, 0.20, "ok", ""),
        FactorReading("spectral_surge", None, 0.20, "no_data", "surge: buffer 0/64"),
    ]
    s = _sentinel_with_factors(monkeypatch, readings)
    a = s.assess("BTC/USD")
    expected = (0.6 * 0.35 + 0.2 * 0.20) / (0.35 + 0.20)
    assert a.status == "ok"
    assert a.volatility_risk == pytest.approx(expected)
    assert a.confidence == pytest.approx(0.55)
    assert len(a.blockers) == 2 and any("warm-up" in b for b in a.blockers)


def test_fusion_escalates_on_single_screaming_factor(monkeypatch):
    readings = [
        FactorReading("ewma_vol", 0.05, 0.35, "ok", ""),
        FactorReading("phase_transition", 0.95, 0.25, "ok", ""),
        FactorReading("qgita_regime", 0.05, 0.20, "ok", ""),
        FactorReading("spectral_surge", 0.05, 0.20, "ok", ""),
    ]
    s = _sentinel_with_factors(monkeypatch, readings)
    a = s.assess("BTC/USD")
    assert a.volatility_risk == pytest.approx(0.95), (
        "a factor >= ESCALATION_RISK must not be averaged away (max is tighten-only)"
    )
    assert ESCALATION_RISK <= 0.95


def test_no_inputs_is_honest_no_data():
    s = VolatilitySentinel(symbols=["BTC/USD"])
    a = s.assess("BTC/USD")
    assert a.status == "no_data"
    assert a.volatility_risk is None
    assert a.confidence == 0.0
    assert len(a.blockers) == 4, "every missing factor must be named"
    for name in ("ewma_vol", "phase_transition", "qgita_regime", "spectral_surge"):
        assert any(name in b for b in a.blockers)


def test_portfolio_rollup_takes_max_risk(monkeypatch):
    s = VolatilitySentinel(symbols=["A", "B"])
    per_symbol = {
        "A": VolatilityAssessment("ok", 0.30, 1.0, (), (), "A", 1.0),
        "B": VolatilityAssessment("ok", 0.70, 1.0, (), (), "B", 1.0),
    }
    monkeypatch.setattr(s, "assess", lambda sym, ts=None: per_symbol[sym])
    a = s.assess_portfolio()
    assert a.volatility_risk == pytest.approx(0.70)
    assert a.symbol is None


def test_portfolio_rollup_no_data_when_all_symbols_dark():
    s = VolatilitySentinel(symbols=["A", "B"])
    a = s.assess_portfolio()
    assert a.status == "no_data" and a.volatility_risk is None
    assert a.blockers


# ── real-factor integration (ewma only, others honestly dark) ────────


def test_assess_with_only_prices_uses_ewma_and_names_the_rest():
    rng = random.Random(3)
    s = VolatilitySentinel(symbols=["BTC/USD"])
    price = 100.0
    for i in range(WARMUP_SLOW + 20):
        price *= 1.0 + rng.gauss(0.0, 0.002)
        s.ingest_price("BTC/USD", price, ts=float(i))
    a = s.assess("BTC/USD")
    assert a.status == "ok"
    assert a.confidence == pytest.approx(0.35), "only the ewma weight measured"
    ok = [f for f in a.factors if f.status == "ok"]
    assert [f.name for f in ok] == ["ewma_vol"]
    assert len(a.blockers) == 3


# ── publish / read freshness contract ────────────────────────────────


@pytest.fixture()
def isolated_trace(tmp_path, monkeypatch):
    monkeypatch.setenv("AUREON_BUS_TRACE_DIR", str(tmp_path))
    return tmp_path


def test_publish_then_read_roundtrip(isolated_trace):
    import time as _time

    s = VolatilitySentinel(symbols=["BTC/USD"])
    a = VolatilityAssessment(
        status="ok", volatility_risk=0.42, confidence=0.55,
        factors=(FactorReading("ewma_vol", 0.42, 0.35, "ok", "ratio=1.7"),),
        blockers=("phase_transition: warm-up",),
        symbol=None, ts=_time.time(),
    )
    s.publish(a)
    got = read_latest_assessment(max_age_s=120.0, bus=False)
    # bus=False is not a bus object; recall path fails closed and the trace
    # fallback must carry the row.
    assert got is not None
    assert got.volatility_risk == pytest.approx(0.42)
    assert got.confidence == pytest.approx(0.55)
    assert got.blockers == ("phase_transition: warm-up",)


def test_read_refuses_stale_rows(isolated_trace):
    s = VolatilitySentinel(symbols=["BTC/USD"])
    old = VolatilityAssessment(
        status="ok", volatility_risk=0.9, confidence=1.0, factors=(),
        blockers=(), symbol=None, ts=1000.0,  # 2001-vintage: unquestionably stale
    )
    s.publish(old)
    assert read_latest_assessment(max_age_s=120.0, bus=False) is None


def test_read_refuses_unstamped_rows(isolated_trace):
    from aureon.core.bus_trace import append_trace
    from aureon.intelligence.volatility_sentinel import VOL_TRACE_NAME

    append_trace(VOL_TRACE_NAME, {"status": "ok", "volatility_risk": 0.9,
                                  "confidence": 1.0})  # no ts on purpose
    assert read_latest_assessment(max_age_s=120.0, bus=False) is None


def test_read_returns_none_when_nothing_published(isolated_trace):
    assert read_latest_assessment(max_age_s=120.0, bus=False) is None
