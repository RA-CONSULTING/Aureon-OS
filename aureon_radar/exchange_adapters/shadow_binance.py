"""Binance shadow-trading wiring — thin wrapper over shadow_executor.

Quotes come from the Binance public REST /api/v3/ticker/bookTicker on the
adapter's configured base URL (mainnet, or testnet when BINANCE_TESTNET=true
— verified reachable from this host, ping HTTP 200). bookTicker carries
bid+ask, so taker fills reference the ask (buy) / bid (sell) per the binding
fill model in shadow_executor, with last=mid as the MTM mark; if the
bookTicker call fails the adapter's public get_price() (/api/v3/ticker/price,
last-only) is used as fallback and fills reference last — never fabricated.
Fee 0.10 % taker, slippage 0.05 % (both owned by shadow_executor).

Public API (used by the hub and by Gary):
    propose_signal(symbol, side, qty, signal_source, signal_confidence) -> dict
    mark_all() -> dict   (MTM + stop -2% / TP +3% management on open positions)
    live_place(symbol, side, qty) -> dict   (FAIL-CLOSED, see below)
    get_engine() -> ShadowEngine

live_place() is the gated live path: it re-reads aureon_radar/.env AND
os.environ at CALL TIME for BINANCE_API_KEY + BINANCE_API_SECRET (key NAMES
only — values are never logged, returned, or journaled). Absent -> it returns
{"status": "refused_not_authorized", ...} and journals the refusal. Present ->
it delegates to BinanceAdapter.place_order(dry_run=False), which routes to
the signed BinanceClient path (testnet when BINANCE_TESTNET=true, which the
current .env sets). Gary energizes real keys when the capital gate releases.

Import has no side effects beyond the adapter's own socket-timeout guard.
"""

from __future__ import annotations

import json
import logging
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

_MODULE_DIR = Path(__file__).resolve().parent
if str(_MODULE_DIR) not in sys.path:
    # Hub loads this file via importlib without the package context; the
    # sibling modules must be importable either way.
    sys.path.insert(0, str(_MODULE_DIR))

from shadow_executor import (
    ShadowEngine,
    ShadowOrder,
    env_has_keys,
    utc_now_iso,
)

try:
    from binance_adapter import BinanceAdapter
except ImportError:  # pragma: no cover - package-style import fallback
    from .binance_adapter import BinanceAdapter

try:
    import expectancy_gate as _expectancy_gate
except ImportError:  # pragma: no cover - package-style import fallback
    from . import expectancy_gate as _expectancy_gate

logger = logging.getLogger(__name__)

VENUE = "binance"
SUPPORTED_SYMBOLS = ("BTCUSDT", "ETHUSDT")
_SYMBOL_ALIASES = {
    "BTC": "BTCUSDT", "BTCUSD": "BTCUSDT", "BTC/USD": "BTCUSDT",
    "XBTUSD": "BTCUSDT", "XBT/USD": "BTCUSDT",
    "ETH": "ETHUSDT", "ETHUSD": "ETHUSDT", "ETH/USD": "ETHUSDT",
}
_LIVE_KEY_NAMES = ("BINANCE_API_KEY", "BINANCE_API_SECRET")

_ADAPTER: Optional[BinanceAdapter] = None
_ENGINE: Optional[ShadowEngine] = None


def get_engine() -> ShadowEngine:
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = ShadowEngine(VENUE)
    return _ENGINE


def _get_adapter() -> BinanceAdapter:
    global _ADAPTER
    if _ADAPTER is None:
        _ADAPTER = BinanceAdapter()
    return _ADAPTER


def _normalize_symbol(symbol: Any) -> str:
    sym = str(symbol or "").strip().upper()
    return _SYMBOL_ALIASES.get(sym, sym)


def _quote_fn(symbol: str) -> Optional[Dict[str, Any]]:
    """Live public quote; returns None on any failure (executor then refuses
    honestly — never fabricates). Primary: /api/v3/ticker/bookTicker on the
    adapter's configured base URL (bid+ask+last=mid, fresh timestamp taken
    at fetch). Fallback: the adapter's get_price() (last-only)."""
    import requests

    sym = _normalize_symbol(symbol)
    adapter = _get_adapter()
    try:
        r = requests.get(
            f"{adapter.config.base_url}/api/v3/ticker/bookTicker",
            params={"symbol": sym},
            timeout=15,
        )
        payload = r.json()
        if r.status_code == 200 and "bidPrice" in payload:
            bid = float(payload["bidPrice"])
            ask = float(payload["askPrice"])
            return {
                "symbol": sym,
                "bid": bid,
                "ask": ask,
                "last": (bid + ask) / 2.0,
                "source": "binance_public_bookTicker",
                "fetched_at": time.time(),
            }
        logger.debug("binance bookTicker not ok for %s: HTTP %s %s",
                     sym, r.status_code, payload)
    except Exception as exc:
        logger.debug("binance bookTicker failed for %s: %s", sym, exc)
    try:
        payload = adapter.get_price(sym)
        if not payload.get("ok"):
            logger.debug("binance shadow quote not ok for %s: %s",
                         sym, payload.get("error"))
            return None
        return payload
    except Exception as exc:
        logger.debug("binance shadow quote failed for %s: %s", sym, exc)
        return None


def propose_signal(symbol: str, side: str, qty: float,
                   signal_source: str, signal_confidence: float) -> Dict[str, Any]:
    sym = _normalize_symbol(symbol)
    if sym not in SUPPORTED_SYMBOLS:
        order = ShadowOrder(VENUE, sym or str(symbol), str(side).lower(),
                            qty, signal_source, signal_confidence)
        return get_engine()._refuse(
            order, "refused_unsupported_symbol",
            f"binance shadow venue supports {SUPPORTED_SYMBOLS}")
    order = ShadowOrder(VENUE, sym, side, qty, signal_source, signal_confidence)
    return get_engine().propose(order, _quote_fn)


def mark_all() -> Dict[str, Any]:
    return get_engine().mark_all(_quote_fn)


def close_position(symbol: str, reason: str = "manual") -> Dict[str, Any]:
    return get_engine().close_position(_normalize_symbol(symbol), reason, _quote_fn)


def live_place(symbol: str, side: str, qty: float,
               confidence: Optional[float] = None) -> Dict[str, Any]:
    """FAIL-CLOSED live order path. Call-time key check, names only.

    With keys present, the expectancy gate runs first (Gary's decree): the
    confidence-scaled expected move must clear 1.25x the venue's real
    round-trip cost (per-venue VENUE_FEES, not a flat fee); otherwise the
    order is journaled as refused_edge_below_cost and nothing is sent.
    confidence defaults to the hub promotion threshold (0.55) when the
    caller doesn't supply one.
    """
    symbol = _normalize_symbol(symbol)
    ok, present = env_has_keys(_LIVE_KEY_NAMES)
    if not ok:
        result = {
            "status": "refused_not_authorized",
            "venue": VENUE,
            "symbol": symbol,
            "side": str(side).strip().lower(),
            "qty": qty,
            "missing_key_names": [n for n, p in present.items() if not p],
            "ts_utc": utc_now_iso(),
        }
        get_engine()._journal({
            "event": "refused", "venue": VENUE, "symbol": symbol,
            "side": result["side"], "qty": qty, "price": None, "fee": None,
            "signal_source": "live_place", "signal_confidence": 1.0,
            "reason": "refused_not_authorized",
            "detail": "BINANCE_API_KEY/BINANCE_API_SECRET absent at call time",
        })
        logger.info("binance live_place REFUSED (not authorized): %s", symbol)
        return result
    # Expectancy gate — fail-closed, before any live order reaches the adapter.
    try:
        verdict = _expectancy_gate.check(
            venue=VENUE, symbol=symbol, side=side, qty=qty, price=None,
            confidence=_expectancy_gate.PROMOTION_CONFIDENCE
            if confidence is None else confidence)
    except Exception as exc:
        verdict = {"allowed": False, "reason": f"gate_error: {exc}"}
    if not verdict.get("allowed"):
        result = {
            "status": "refused",
            "reason": verdict.get("reason", "refused_edge_below_cost"),
            "venue": VENUE,
            "symbol": symbol,
            "side": str(side).strip().lower(),
            "qty": qty,
            "expected_move_pct": verdict.get("expected_move_pct"),
            "round_trip_cost_pct": verdict.get("round_trip_cost_pct"),
            "margin_pct": verdict.get("margin_pct"),
            "ts_utc": utc_now_iso(),
        }
        get_engine()._journal({
            "event": "refused", "venue": VENUE, "symbol": symbol,
            "side": result["side"], "qty": qty, "price": None, "fee": None,
            "signal_source": "live_place",
            "signal_confidence": 0.55 if confidence is None else confidence,
            "reason": result["reason"],
            "detail": (f"expectancy gate: expected={verdict.get('expected_move_pct')} "
                       f"cost={verdict.get('round_trip_cost_pct')} "
                       f"margin={verdict.get('margin_pct')} "
                       f"floor={verdict.get('capture_floor_pct')} "
                       f"required={verdict.get('required_move_pct')} "
                       f"{verdict.get('detail') or ''}")[:300],
        })
        logger.info("binance live_place REFUSED (%s): %s",
                    result["reason"], symbol)
        return result
    try:
        return _get_adapter().place_order(symbol, side, qty, dry_run=False)
    except Exception as exc:
        return {"status": "error", "venue": VENUE,
                "error": f"{type(exc).__name__}: {exc}"[:300],
                "ts_utc": utc_now_iso()}


if __name__ == "__main__":
    import tempfile

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    # Self-test hygiene (2026-09-07): throwaway journal/ledger/book in
    # tempdir — these open/immediate-close round-trips used to write "manual"
    # closes <3 s after open into the REAL shadow ledger (the 3-second-exit
    # poison in time-to-capture stats). min_hold is zeroed: self-test closes
    # by design.
    _tmpdir = Path(tempfile.mkdtemp(prefix="shadow_binance_selftest_"))
    _ENGINE = ShadowEngine(
        VENUE,
        journal_path=_tmpdir / "shadow_trades.jsonl",
        ledger_path=_tmpdir / "shadow_ledger_summary.json",
        book_path=_tmpdir / f"shadow_book_{VENUE}.json",
    )
    _ENGINE.min_hold_seconds = 0.0
    print(f"self-test state dir (throwaway): {_tmpdir}")

    print("== live_place gate check (keys absent -> must refuse) ==")
    gate = live_place("BTCUSDT", "buy", 0.001)
    print(json.dumps(gate, indent=2, sort_keys=True))
    assert gate["status"] == "refused_not_authorized", gate

    print("== live public quotes (evidence — no fabrication) ==")
    q_btc = _quote_fn("BTCUSDT")
    q_eth = _quote_fn("ETHUSDT")
    assert q_btc and q_eth, "live quote fetch failed"
    print(f"BTCUSDT bookTicker bid={q_btc['bid']} ask={q_btc['ask']} "
          f"({q_btc['source']})")
    print(f"ETHUSDT bookTicker bid={q_eth['bid']} ask={q_eth['ask']} "
          f"({q_eth['source']})")

    print("== unsupported symbol + alias normalization ==")
    bad = propose_signal("DOGEUSDT", "buy", 1.0, "binance_shadow_selftest", 0.5)
    print(json.dumps(bad, indent=2, sort_keys=True))
    assert bad["status"] == "refused" and bad["reason"] == "refused_unsupported_symbol", bad

    print("== shadow BUY 0.001 BTCUSDT on live public quote ==")
    res = propose_signal("BTC", "buy", 0.001, "binance_shadow_selftest", 0.85)
    print(json.dumps({k: v for k, v in res.items() if k != "position"},
                     indent=2, sort_keys=True, default=str))
    assert res["status"] == "opened", res
    # taker realism: BUY fills at ask * (1 + 0.05% slippage)
    expect = q_btc["ask"] * 1.0005
    assert abs(res["fill_price"] - expect) / expect < 0.001, \
        f"fill {res['fill_price']} not near ask+slippage {expect} (quote moved?)"
    print(f"FILLED at {res['fill_price']}  provenance={res['provenance']}")

    print("== MTM pass ==")
    print(json.dumps(mark_all(), indent=2, sort_keys=True, default=str))

    print("== close position (reason=selftest_close) ==")
    close = close_position("BTCUSDT", "selftest_close")
    print(json.dumps(close, indent=2, sort_keys=True, default=str))
    assert close["status"] == "closed", close
    print(f"CLOSED at {close['price']}  net_pnl={close['net_pnl']}  "
          f"fees={close.get('fees')}  fee_basis={close.get('fee_basis')}")
    print(f"SELF-TEST PASSED (throwaway state in {_tmpdir}; real ledger untouched)")
