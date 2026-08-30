"""Tests for the market signal adapter — scan a market-derived series through the engine.

The engine's φ logic is unchanged. These tests assert the machinery: the control
references behave (an efficient-market null does not over-fire; planted coherence is
detected), a real local symbol series scans to a valid deterministic result, and the
governance holds. No assertion is made about what a real market "should" score, and
no field may leak a trading-signal / efficacy claim.
"""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from aureon.bio import human_harmonic_proxy as proxy
from aureon.bio import market_reference as market
from aureon.bio import market_signal_adapter as msa

NULLS = 300
# no health/aura/etc. AND no market-overclaim words may appear in any result field
_FORBIDDEN = (
    "health", "aura", "emotion", "spirit", "entity", "diagnos", "disease", "personality",
    "buy", "sell", "profit", "forecast", "guarantee", "advice",
)


class _StubConscience:
    def __init__(self, verdict):
        self._v = verdict

    def ask_why(self, action, context=None):
        return SimpleNamespace(verdict=SimpleNamespace(name=self._v), message="")


@pytest.fixture(autouse=True)
def _approved(monkeypatch):
    monkeypatch.setattr(proxy, "_get_conscience", lambda: _StubConscience("APPROVED"))


# ---------------------------------------------------------------------------
# control references (negative does not over-fire; positive is detected)
# ---------------------------------------------------------------------------


def test_efficient_market_null_does_not_overfire():
    r = msa.score_market(market.efficient_market_returns(1024, seed=0), consent=True,
                         provenance="ctrl", kind="returns", nulls=NULLS)
    assert r.valid is True
    assert r.structure_present is False


def test_planted_structure_positive_control_detected():
    r = msa.score_market(market.structured_returns(), consent=True, provenance="ctrl",
                         kind="returns", sample_rate_hz=8192.0, nulls=NULLS)
    assert r.valid is True
    assert r.structure_present is True
    assert r.test_A_p < proxy.engine.ALPHA and r.test_B_p < proxy.engine.ALPHA


# ---------------------------------------------------------------------------
# transforms + folding
# ---------------------------------------------------------------------------


def test_prices_to_returns():
    rets = market.prices_to_returns([100.0, 101.0, 100.5])
    assert rets.shape == (2,)
    assert np.isfinite(rets).all()
    assert market.prices_to_returns([1.0]).size == 0


def test_tones_fold_into_band():
    sig = msa.MarketSignalAdapter().extract(
        market.structured_returns(), consent=True, provenance="p",
        kind="returns", sample_rate_hz=8192.0)
    low, high = proxy.TARGET_BAND_HZ
    assert sig.frequencies_hz
    assert all(low <= f < high for f in sig.frequencies_hz)


# ---------------------------------------------------------------------------
# real local data (valid + deterministic)
# ---------------------------------------------------------------------------


def test_real_symbol_scan_is_valid_and_deterministic():
    syms = market.available_symbols()
    assert syms, "no symbols in local prediction log"
    symbol = syms.most_common(1)[0][0]
    r1 = msa.score_symbol(symbol, nulls=NULLS, seed=0)
    r2 = msa.score_symbol(symbol, nulls=NULLS, seed=0)
    assert r1.valid is True and r1.blocked is False
    assert r1.n_tones > 0
    assert (r1.test_A_p, r1.test_B_p) == (r2.test_A_p, r2.test_B_p)


def test_trade_log_loads_ordered_prices():
    prices = market.load_trade_prices()
    assert isinstance(prices, list)
    assert all(isinstance(p, float) for p in prices)


# ---------------------------------------------------------------------------
# governance
# ---------------------------------------------------------------------------


def test_consent_gate_blocks():
    r = msa.score_market(market.efficient_market_returns(256), consent=False,
                         provenance="x", kind="returns", nulls=100)
    assert r.blocked is True and r.valid is False
    assert r.to_dict()["structure_present"] is False


def test_missing_provenance_blocks():
    r = msa.score_market(market.efficient_market_returns(256), consent=True,
                         provenance="  ", kind="returns", nulls=100)
    assert r.blocked is True


def test_boundary_and_no_claim_words():
    r = msa.score_market(market.structured_returns(), consent=True, provenance="ctrl",
                         kind="returns", sample_rate_hz=8192.0, nulls=NULLS)
    d = r.to_dict()
    assert d["boundary"] == proxy.SCIENTIFIC_BOUNDARY
    for key, value in d.items():
        if key == "boundary" or not isinstance(value, str):
            continue
        low = value.lower()
        for w in _FORBIDDEN:
            assert w not in low, f"field {key!r} leaked {w!r}: {value!r}"


def test_market_boundary_present_and_clean():
    assert "not a trading signal" in market.MARKET_BOUNDARY.lower()
    assert "no profit" in market.MARKET_BOUNDARY.lower()


def test_module_has_no_person_reading_surface():
    names = [n.lower() for n in dir(msa)]
    for banned in ("face", "landmark", "detect", "emotion", "biometric", "recognize"):
        assert not any(banned in n for n in names), f"unexpected {banned!r} surface"


def test_symbol_helper_missing_provenance_blocks():
    # score_symbol defaults consent=True; a blank provenance must still block
    syms = market.available_symbols()
    if not syms:
        pytest.skip("no local prediction symbols")
    sym = syms.most_common(1)[0][0]
    r = msa.score_symbol(sym, provenance="  ", nulls=100)
    assert r.blocked is True
