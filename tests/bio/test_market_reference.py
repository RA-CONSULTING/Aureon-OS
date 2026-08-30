"""Tests for market_reference — real local price series + market controls.

Pure data module. Asserts loaders return numeric series, the return transform behaves,
the control references (efficient-market null + planted structure) are well-formed, and
the boundary/citation are honest.
"""

from __future__ import annotations

import numpy as np

from aureon.bio import market_reference as market


def test_efficient_market_null_is_iid_like():
    r1 = market.efficient_market_returns(512, seed=0)
    r2 = market.efficient_market_returns(512, seed=0)
    assert r1.shape == (512,)
    assert np.allclose(r1, r2)  # deterministic given seed
    assert abs(float(np.mean(r1))) < 0.5  # roughly zero-mean noise


def test_structured_returns_has_planted_cycles():
    s = market.structured_returns()
    assert s.size > 100
    assert np.isfinite(s).all()
    assert float(np.std(s)) > 0


def test_prices_to_returns():
    rets = market.prices_to_returns([100.0, 101.0, 100.5, 102.0])
    assert rets.shape == (3,)
    assert np.isfinite(rets).all()
    assert market.prices_to_returns([1.0]).size == 0
    assert market.prices_to_returns([1.0, -5.0, 2.0]).size >= 1  # non-positive dropped


def test_loaders_return_numeric_series():
    prices = market.load_trade_prices()
    assert isinstance(prices, list)
    assert all(isinstance(p, float) for p in prices)
    syms = market.available_symbols()
    if syms:  # local prediction log present
        sym = syms.most_common(1)[0][0]
        series = market.load_prediction_prices(sym)
        assert all(isinstance(p, float) for p in series)


def test_boundary_and_citation_honest():
    low = market.MARKET_BOUNDARY.lower()
    assert "not a trading signal" in low
    assert "no profit" in low
    assert "derived" in market.MARKET_CITATION.lower()
