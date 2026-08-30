#!/usr/bin/env python3
"""Market signal adapter — scan a market-derived series through the engine.

Points the *same* phenolic engine (φ logic unchanged) at a market series: a price
series (folded via log-returns), a returns series, or any scalar timeseries (e.g.
momentum). The scan runs through the identical governed pipeline every other adapter
uses (``score_signal``: controls → Test A / Test B → separability at ``ALPHA``), and
reports whatever the pre-registered test returns.

This is the repository's headline thread — φ²-scaled coherence in market dynamics —
tested the honest way. The scan looks for statistical structure in a *derived*
series and reports exactly what the engine returns. It is **not** a trading signal,
a forecast, or financial advice, and it makes no profit or efficacy claim
(:data:`aureon.bio.market_reference.MARKET_BOUNDARY`).

Real local price data ships with it (``market_reference``): the per-symbol
``price_at_prediction`` series in ``data/probability_predictions.jsonl`` and the
dry-run ``entry_price`` log in ``data/queen_trades.jsonl``. Nothing about the engine
is modified; this module only feeds it a market series and reports the result.

Pure stdlib + numpy + the engine. Reuses the timeseries→Hz FFT seam already built for
the UPE adapter. No market/exchange dependency — a list of prices is enough.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

import phenolic_fingerprint as engine
from aureon.bio import market_reference as market
from aureon.bio.human_harmonic_proxy import (
    HumanSignal,
    ProxyResult,
    fold_to_band,
    score_signal,
)
from aureon.bio.upe_signal_adapter import _dominant_timeseries_hz

__all__ = [
    "MarketSignalAdapter",
    "score_market",
    "score_symbol",
    "main",
]


class MarketSignalAdapter:
    """Extract a derived signal from a market series (prices / returns / timeseries).

    Implements the :class:`aureon.bio.human_harmonic_proxy.SignalAdapter` seam.
    Consent + provenance are required arguments (never fabricated); for local market
    logs, consent is simply the operator affirming the scan.
    """

    modality: str = "market"

    def extract(
        self,
        spec: Any,
        *,
        consent: bool,
        provenance: str,
        kind: str = "prices",
        sample_rate_hz: float = 1.0,
        max_peaks: int = 24,
    ) -> HumanSignal:
        """Return a :class:`HumanSignal` (modality='market') of folded modulation tones.

        ``kind='prices'``    : ``spec`` is a price series (converted to log-returns).
        ``kind='returns'``   : ``spec`` is already a returns/change series.
        ``kind='timeseries'``: ``spec`` is any scalar series (e.g. momentum), used raw.
        """
        if kind == "prices":
            series = market.prices_to_returns(spec)
            note = "price series (log-returns)"
        elif kind in ("returns", "timeseries"):
            series = np.asarray(spec, dtype=float).ravel()
            note = "returns series" if kind == "returns" else "scalar series"
        else:  # pragma: no cover - guarded by callers
            raise ValueError(f"unknown kind {kind!r}; expected 'prices', 'returns', or 'timeseries'")

        raw_hz = _dominant_timeseries_hz(series, sample_rate_hz=sample_rate_hz, max_peaks=max_peaks)
        tones = tuple(sorted(f for f in (fold_to_band(v) for v in raw_hz) if f is not None))
        return HumanSignal(
            label=f"market:{kind}",
            frequencies_hz=tones,
            provenance=provenance,
            consent=consent,
            modality=self.modality,
            notes=f"{len(raw_hz)} dominant market cycle(s) from a {note}; "
            "derived-signal structure only, not a trading signal",
        )


def score_market(
    spec: Any,
    *,
    consent: bool,
    provenance: str,
    kind: str = "prices",
    sample_rate_hz: float = 1.0,
    nulls: int = engine.DEFAULT_NULLS,
    seed: int = 0,
) -> ProxyResult:
    """Scan a market series and score it through the governed pipeline."""
    signal = MarketSignalAdapter().extract(
        spec, consent=consent, provenance=provenance, kind=kind, sample_rate_hz=sample_rate_hz
    )
    return score_signal(signal, nulls=nulls, seed=seed)


def score_symbol(
    symbol: str,
    *,
    path: str | Path = "data/probability_predictions.jsonl",
    consent: bool = True,
    provenance: str | None = None,
    nulls: int = engine.DEFAULT_NULLS,
    seed: int = 0,
) -> ProxyResult:
    """Scan one symbol's real local price series through the engine."""
    prices = market.load_prediction_prices(symbol, path=path)
    prov = provenance or f"local prediction log: {symbol} ({market.MARKET_CITATION})"
    return score_market(prices, consent=consent, provenance=prov, kind="prices", nulls=nulls, seed=seed)


def main(argv: list[str] | None = None) -> int:
    """CLI: scan a real symbol series, or run the control self-test."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Scan a market-derived series through the phenolic engine (φ logic unchanged)."
    )
    parser.add_argument("--symbol", help="scan one symbol from the local prediction log")
    parser.add_argument("--path", default="data/probability_predictions.jsonl")
    parser.add_argument("--list", action="store_true", help="list available symbols and exit")
    parser.add_argument("--nulls", type=int, default=engine.DEFAULT_NULLS)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--self-test", action="store_true",
                        help="control self-test: efficient-market null + planted-structure reference")
    args = parser.parse_args(argv)

    print("Market signal adapter — scanning a market-derived series")
    print(f"  boundary: {market.MARKET_BOUNDARY}")
    print(f"  data:     {market.MARKET_CITATION}")

    if args.list:
        for sym, n in market.available_symbols(args.path).most_common(20):
            print(f"  {sym:12s} {n:4d} points")
        return 0

    if args.self_test:
        prov = "market control self-test"
        null = score_market(market.efficient_market_returns(1024, seed=args.seed), consent=True,
                            provenance=prov, kind="returns", nulls=args.nulls, seed=args.seed)
        planted = score_market(market.structured_returns(), consent=True, provenance=prov,
                              kind="returns", sample_rate_hz=8192.0, nulls=args.nulls, seed=args.seed)
        checks = [
            (null.valid and not null.structure_present,
             "efficient-market null -> negative control does NOT over-fire"),
            (planted.valid and planted.structure_present,
             "planted coherence     -> positive control detected"),
        ]
        ok = True
        for passed, label in checks:
            ok = ok and passed
            print(f"  {'✅' if passed else '❌'} {label}")
        print(f"  null:    A_p={null.test_A_p} B_p={null.test_B_p}")
        print(f"  planted: A_p={planted.test_A_p} B_p={planted.test_B_p}")
        return 0 if ok else 1

    if not args.symbol:
        parser.error("provide --symbol SYM, or --list, or --self-test")

    result = score_symbol(args.symbol, path=args.path, nulls=args.nulls, seed=args.seed)
    d = result.to_dict()
    print(f"  scan             : {args.symbol}")
    print(f"  n_tones          : {d['n_tones']}")
    print(f"  valid / blocked  : {d['valid']} / {d['blocked']}")
    print(f"  structure_present: {d['structure_present']}")
    print(f"  test_A_p/test_B_p: {d['test_A_p']} / {d['test_B_p']}")
    return 0


if __name__ == "__main__":  # pragma: no cover - manual entry point
    raise SystemExit(main())
