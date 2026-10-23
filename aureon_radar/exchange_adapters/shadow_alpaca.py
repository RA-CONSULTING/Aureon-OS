"""Alpaca shadow-trading wiring — thin wrapper over shadow_executor.

Quotes come from alpaca_adapter.py's get_quote(): without keys it uses
labeled public feeds (Binance public for BTC/USD and ETH/USD, Yahoo Finance
public for AAPL); with keys it uses the Alpaca data API. Every quote is
source-labeled by the adapter and freshness-checked by the engine. Fee 0.0 %
taker, slippage 0.05 % (binding constants in shadow_executor).

Public API (used by the hub and by Gary):
    propose_signal(symbol, side, qty, signal_source, signal_confidence) -> dict
    mark_all() -> dict   (MTM + stop -2% / TP +3% management on open positions)
    live_place(symbol, side, qty) -> dict   (FAIL-CLOSED, see below)
    get_engine() -> ShadowEngine

live_place() is the gated live path: it re-reads aureon_radar/.env AND
os.environ at CALL TIME for APCA_API_KEY_ID + APCA_API_SECRET_KEY (with the
adapter's legacy fallbacks; key NAMES only — values are never logged,
returned, or journaled). Absent -> {"status": "refused_not_authorized", ...}
and the refusal is journaled. Present -> delegates to
AlpacaAdapter.submit_order() (paper environment unless APCA_LIVE=true).

Import has no side effects beyond the adapter's own dotenv load.
"""

from __future__ import annotations

import json
import logging
import sys as _sys
from pathlib import Path as _Path
from typing import Any, Dict, Optional

# unified_hub.py loads this file BY PATH via importlib with no package context,
# so the relative import below fails there and the bare fallback needs our own
# directory on sys.path. Bootstrap it; idempotent and harmless otherwise.
_MODULE_DIR = _Path(__file__).resolve().parent
if str(_MODULE_DIR) not in _sys.path:
    _sys.path.insert(0, str(_MODULE_DIR))

try:
    from .shadow_executor import (
        ShadowEngine,
        ShadowOrder,
        env_has_keys,
        utc_now_iso,
    )
except ImportError:  # pragma: no cover - direct-script fallback
    from shadow_executor import (
        ShadowEngine,
        ShadowOrder,
        env_has_keys,
        utc_now_iso,
    )

try:
    from .alpaca_adapter import AlpacaAdapter
except ImportError:  # pragma: no cover - direct-script fallback
    from alpaca_adapter import AlpacaAdapter

try:
    from . import expectancy_gate as _expectancy_gate
except ImportError:  # pragma: no cover - direct-script fallback
    import expectancy_gate as _expectancy_gate

logger = logging.getLogger(__name__)

VENUE = "alpaca"
# ETH/USD added 2026-09-06 (bug-hunt): the hub routes ETH signals here
# (ShadowArm._ASSET_MAP) and both quote paths support it — with keys the
# Alpaca data API lists ETH/USD; without keys the Binance public feed quotes
# it (ETH->ETHUSDT). The old BTC-only whitelist refused every ETH dispatch
# with an identical reason every cycle (16x in state/shadow_trades.jsonl).
SUPPORTED_SYMBOLS = ("BTC/USD", "ETH/USD", "AAPL")
_LIVE_KEY_NAMES = ("APCA_API_KEY_ID", "APCA_API_SECRET_KEY")

_ADAPTER: Optional[AlpacaAdapter] = None
_ENGINE: Optional[ShadowEngine] = None


def get_engine() -> ShadowEngine:
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = ShadowEngine(VENUE)
    return _ENGINE


def _get_adapter() -> AlpacaAdapter:
    global _ADAPTER
    if _ADAPTER is None:
        _ADAPTER = AlpacaAdapter()
    return _ADAPTER


def _canonical_symbol(symbol: str) -> str:
    cleaned = str(symbol).strip().upper().replace("-", "/").replace(" ", "")
    if cleaned in ("BTC", "BTCUSD", "BTC/USD", "XBTUSD", "XBT/USD"):
        return "BTC/USD"
    if cleaned in ("ETH", "ETHUSD", "ETH/USD", "XETHUSD"):
        return "ETH/USD"
    if cleaned in ("AAPL",):
        return "AAPL"
    return cleaned


def _quote_fn(symbol: str) -> Optional[Dict[str, Any]]:
    """Live quote via the adapter; returns None on any failure."""
    try:
        return _get_adapter().get_quote(symbol)
    except Exception as exc:
        logger.debug("alpaca shadow quote failed for %s: %s", symbol, exc)
        return None


def propose_signal(symbol: str, side: str, qty: float,
                   signal_source: str, signal_confidence: float) -> Dict[str, Any]:
    symbol = _canonical_symbol(symbol)
    if symbol not in SUPPORTED_SYMBOLS:
        order = ShadowOrder(VENUE, symbol, side, qty, signal_source, signal_confidence)
        return get_engine()._refuse(
            order, "refused_invalid_order",
            f"{symbol!r} not in {SUPPORTED_SYMBOLS}")
    order = ShadowOrder(VENUE, symbol, side, qty, signal_source, signal_confidence)
    return get_engine().propose(order, _quote_fn)


def mark_all() -> Dict[str, Any]:
    return get_engine().mark_all(_quote_fn)


def close_position(symbol: str, reason: str = "manual") -> Dict[str, Any]:
    return get_engine().close_position(_canonical_symbol(symbol), reason, _quote_fn)


def live_place(symbol: str, side: str, qty: float,
               confidence: Optional[float] = None) -> Dict[str, Any]:
    """FAIL-CLOSED live order path. Call-time key check, names only.

    With keys present (or the legacy fallback names), the expectancy gate
    runs first (Gary's decree): the confidence-scaled expected move must
    clear 1.25x the venue's real round-trip cost (per-venue VENUE_FEES, not
    a flat fee); otherwise the order is journaled as
    refused_edge_below_cost and nothing is sent. confidence defaults to the
    hub promotion threshold (0.55) when the caller doesn't supply one.
    """
    symbol = _canonical_symbol(symbol)
    ok, present = env_has_keys(_LIVE_KEY_NAMES)
    if not ok:
        # Legacy fallback names also satisfy authorization.
        ok_legacy, present_legacy = env_has_keys(("ALPACA_API_KEY", "ALPACA_SECRET_KEY"))
        if ok_legacy:
            ok = True
        else:
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
                "detail": "APCA_API_KEY_ID/APCA_API_SECRET_KEY absent at call time",
            })
            logger.info("alpaca live_place REFUSED (not authorized): %s", symbol)
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
        logger.info("alpaca live_place REFUSED (%s): %s",
                    result["reason"], symbol)
        return result
    try:
        return _get_adapter().submit_order(symbol, side=side, qty=qty)
    except Exception as exc:
        return {"status": "error", "venue": VENUE,
                "error": f"{type(exc).__name__}: {exc}"[:300],
                "ts_utc": utc_now_iso()}


if __name__ == "__main__":
    import tempfile

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    # Self-test hygiene (2026-09-07): run against a THROWAWAY journal/ledger/
    # book in tempdir. These open/immediate-close round-trips used to write
    # "manual" closes <3 s after open into the REAL shadow ledger — that was
    # the 3-second-exit poison in time-to-capture stats. min_hold is zeroed
    # because the self-test closes by design.
    _tmpdir = _Path(tempfile.mkdtemp(prefix="shadow_alpaca_selftest_"))
    _ENGINE = ShadowEngine(
        VENUE,
        journal_path=_tmpdir / "shadow_trades.jsonl",
        ledger_path=_tmpdir / "shadow_ledger_summary.json",
        book_path=_tmpdir / f"shadow_book_{VENUE}.json",
    )
    _ENGINE.min_hold_seconds = 0.0
    print(f"self-test state dir (throwaway): {_tmpdir}")

    print("== live_place gate check (keys absent -> must refuse) ==")
    gate = live_place("BTC/USD", "buy", 0.001)
    print(json.dumps(gate, indent=2, sort_keys=True))
    assert gate["status"] == "refused_not_authorized", gate

    print("== shadow BUY 0.001 BTC/USD ==")
    res_btc = propose_signal("BTC/USD", "buy", 0.001, "alpaca_shadow_selftest", 0.75)
    print(json.dumps({k: v for k, v in res_btc.items() if k != "position"},
                     indent=2, sort_keys=True, default=str))
    assert res_btc["status"] == "opened", res_btc
    print(f"FILLED BTC at {res_btc['fill_price']}  provenance={res_btc['provenance']}")

    print("== shadow BUY 1 AAPL ==")
    res_aapl = propose_signal("AAPL", "buy", 1, "alpaca_shadow_selftest", 0.75)
    print(json.dumps({k: v for k, v in res_aapl.items() if k != "position"},
                     indent=2, sort_keys=True, default=str))
    assert res_aapl["status"] == "opened", res_aapl
    print(f"FILLED AAPL at {res_aapl['fill_price']}  provenance={res_aapl['provenance']}")

    print("== MTM pass ==")
    print(json.dumps(mark_all(), indent=2, sort_keys=True, default=str))

    print("== close both (reason=selftest_close) ==")
    close_btc = close_position("BTC/USD", "selftest_close")
    print(json.dumps(close_btc, indent=2, sort_keys=True, default=str))
    assert close_btc["status"] == "closed", close_btc
    close_aapl = close_position("AAPL", "selftest_close")
    print(json.dumps(close_aapl, indent=2, sort_keys=True, default=str))
    assert close_aapl["status"] == "closed", close_aapl
    print(f"CLOSED BTC at {close_btc['price']}  net_pnl={close_btc['net_pnl']}  "
          f"fees={close_btc.get('fees')}  fee_basis={close_btc.get('fee_basis')}")
    print(f"CLOSED AAPL at {close_aapl['price']}  net_pnl={close_aapl['net_pnl']}  "
          f"fees={close_aapl.get('fees')}  fee_basis={close_aapl.get('fee_basis')}")
    print(f"SELF-TEST PASSED (throwaway state in {_tmpdir}; real ledger untouched)")
