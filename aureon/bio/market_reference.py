#!/usr/bin/env python3
"""Market reference — real local price series + control references for the scan.

"Same song, different singer": the *same* phenolic engine — φ (golden-ratio) logic
used exactly as-is — is pointed at a market-derived series instead of molecules,
light, or a photon-count. This module supplies the real, locally-committed price
data the market adapter scans, plus the two control references every governed scan
uses. The engine's logic is unchanged; this module only loads market data and the
scan reports whatever the pre-registered test returns.

The market thread is the repository's headline claim (φ²-scaled coherence in market
dynamics). This adapter tests it the honest way: it looks for statistical structure
in a *derived* series and reports exactly what the test returns — nothing about the
scan is a trading signal, a forecast, or financial advice, and it makes no profit or
efficacy claim (:data:`MARKET_BOUNDARY`).

Real local data (committed in the repo, offline):
* ``data/probability_predictions.jsonl`` — per-symbol ``price_at_prediction`` series
  (hundreds of points for the liquid symbols).
* ``data/queen_trades.jsonl`` — a short dry-run ``entry_price`` log.

Two control references (mirror the engine's own control arms, not a claim either way):
* ``efficient_market_returns`` — i.i.d. returns, the efficient-market null (the
  negative-control reference: a memoryless walk must not over-fire the scan).
* ``structured_returns`` — planted clustered + φ-spaced cycles (the positive-control
  demonstration: the scan detects real coherence when it is genuinely present).

Pure stdlib + numpy + engine constants; no network, no astro/market dependency.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Final

import numpy as np

import phenolic_fingerprint as engine

__all__ = [
    "MARKET_BOUNDARY",
    "MARKET_CITATION",
    "load_prediction_prices",
    "load_trade_prices",
    "available_symbols",
    "prices_to_returns",
    "efficient_market_returns",
    "structured_returns",
]

PHI: float = float(engine.PHI)

#: The honest boundary for the market lane — carried alongside the engine's shared
#: SCIENTIFIC_BOUNDARY. Statistical structure only; never a signal to act on.
MARKET_BOUNDARY: Final[str] = (
    "Statistical structure in a derived market series only - NOT a trading signal, "
    "forecast, or financial advice; no profit or efficacy claim."
)

MARKET_CITATION: Final[str] = (
    "Local Aureon dry-run/prediction logs (data/probability_predictions.jsonl, "
    "data/queen_trades.jsonl). Derived series only."
)

_DEFAULT_PREDICTIONS: Final[str] = "data/probability_predictions.jsonl"
_DEFAULT_TRADES: Final[str] = "data/queen_trades.jsonl"


def _iter_jsonl(path: str | Path):
    with Path(path).open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def available_symbols(path: str | Path = _DEFAULT_PREDICTIONS) -> Counter:
    """Count usable (numeric-price) rows per symbol in a prediction log."""
    counts: Counter = Counter()
    for row in _iter_jsonl(path):
        sym = row.get("symbol")
        price = row.get("price_at_prediction")
        if sym and isinstance(price, (int, float)):
            counts[sym] += 1
    return counts


def load_prediction_prices(
    symbol: str, path: str | Path = _DEFAULT_PREDICTIONS
) -> list[float]:
    """Ordered ``price_at_prediction`` series for one symbol (by timestamp)."""
    rows = [
        r for r in _iter_jsonl(path)
        if r.get("symbol") == symbol and isinstance(r.get("price_at_prediction"), (int, float))
    ]
    rows.sort(key=lambda r: str(r.get("timestamp", "")))
    return [float(r["price_at_prediction"]) for r in rows]


def load_trade_prices(path: str | Path = _DEFAULT_TRADES) -> list[float]:
    """Ordered ``entry_price`` series from a dry-run trade log (by timestamp)."""
    rows = [r for r in _iter_jsonl(path) if isinstance(r.get("entry_price"), (int, float))]
    rows.sort(key=lambda r: str(r.get("timestamp", "")))
    return [float(r["entry_price"]) for r in rows]


def prices_to_returns(prices) -> np.ndarray:
    """Log-returns of a price series (the standard detrending transform)."""
    p = np.asarray(prices, dtype=float)
    p = p[np.isfinite(p) & (p > 0)]
    if p.size < 2:
        return np.array([])
    return np.diff(np.log(p))


def efficient_market_returns(n: int = 1024, seed: int = 0) -> np.ndarray:
    """i.i.d. Gaussian returns — the efficient-market (memoryless) null.

    Negative-control reference: a random walk has no periodic structure, so the scan
    must not over-fire on it.
    """
    if n < 4:
        raise ValueError("n must be >= 4")
    rng = np.random.default_rng(seed)
    return rng.standard_normal(n)


def structured_returns(n: int = 8192, sample_rate_hz: float = 8192.0) -> np.ndarray:
    """Returns series with planted cycles whose FFT tones form a clustered + φ set.

    Positive-control demonstration: two tight clusters one golden ratio apart in the
    modulation band, planted as pure cycles, so the scan is shown to detect real
    coherence when it is present. With ``sample_rate_hz == n`` the rfft bin index
    equals the frequency in Hz, so the target band tones land on exact bins.
    """
    centers = 1100.0 * np.array([1.0, PHI])
    offsets = np.array([-8.0, 0.0, 8.0])
    target_hz = (centers[:, None] + offsets[None, :]).ravel()
    t = np.arange(n, dtype=float)
    y = np.zeros(n, dtype=float)
    for f in target_hz:
        k = round(float(f) * n / sample_rate_hz)  # nearest rfft bin
        y = y + np.sin(2.0 * np.pi * k * t / n)
    return y
