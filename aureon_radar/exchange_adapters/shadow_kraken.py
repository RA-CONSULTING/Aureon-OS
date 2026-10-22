#!/usr/bin/env python3
"""Kraken venue shadow wiring — Aureon radar (organism-controlled).

Thin wrapper around shadow_executor.ShadowEngine fed by kraken_adapter's
LIVE PUBLIC ticker. Conforms to the binding schema in shadow_executor.py.

- Symbols: XBTUSD and ETHUSD (Kraken altnames; "BTC/USD"/"BTCUSD"-style
  inputs are canonicalized via kraken_adapter._kraken_pair). Anything else is
  journaled as refused_invalid_order before any network call.
- Quotes come from get_kraken_adapter().get_ticker() — real bid/ask/last with
  fetched_at stamped at receipt. Stale (>30 s) or unreachable feeds are
  refused by the engine (refused_feed_stale / refused_feed_unavailable);
  nothing is ever fabricated.
- propose_signal(symbol, side, qty, signal_source, signal_confidence) opens
  (or adds to / reverses) a shadow position and journals the result.
- mark_all() marks open positions to market and closes any that hit the
  engine's stop (-2 %) or take-profit (+3 %) on the live quote.
- live_place() is the FAIL-CLOSED live path: KRAKEN_API_KEY and
  KRAKEN_API_SECRET are re-read at CALL TIME from aureon_radar/.env AND the
  process environment (key VALUES are never logged, journaled, or returned —
  key names only). Without both, it journals the refusal and returns
  {"status": "refused_not_authorized", ...}. With keys it delegates to
  KrakenAdapter.place_order, which is itself fail-closed behind
  KRAKEN_LIVE_ENABLED=true.

IMPORT NOTE: unified_hub.py loads this file BY PATH via importlib with no
package context, so package-relative and bare sibling imports fail there.
Siblings are therefore loaded by file path and shared through sys.modules.

Import has no side effects beyond the adapter's own dotenv load.
"""

from __future__ import annotations

import importlib.util
import logging
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def _load_sibling(mod_name: str, file_name: str):
    """Load a sibling module by file path; share it via sys.modules so all
    shadow venue wrappers use ONE shadow_executor / adapter instance.
    A failed exec must NOT leave a partial module in sys.modules — a poisoned
    'shadow_executor' entry made binance/alpaca fail with misleading
    "cannot import name 'ShadowEngine'" errors (2026-09-07 incident)."""
    for name, mod in list(sys.modules.items()):
        if name == mod_name or name.endswith("." + mod_name):
            return mod
    path = Path(__file__).resolve().parent / file_name
    spec = importlib.util.spec_from_file_location(mod_name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = mod
    try:
        spec.loader.exec_module(mod)
    except BaseException:
        sys.modules.pop(mod_name, None)
        raise
    return mod


_shadow_executor = _load_sibling("shadow_executor", "shadow_executor.py")
_expectancy_gate = _load_sibling("expectancy_gate", "expectancy_gate.py")
_kraken_adapter = _load_sibling("kraken_adapter", "kraken_adapter.py")

ShadowEngine = _shadow_executor.ShadowEngine
ShadowOrder = _shadow_executor.ShadowOrder
ShadowPosition = _shadow_executor.ShadowPosition
env_has_keys = _shadow_executor.env_has_keys
utc_now_iso = _shadow_executor.utc_now_iso
get_kraken_adapter = _kraken_adapter.get_kraken_adapter
_kraken_pair = _kraken_adapter._kraken_pair

VENUE = "kraken"
SUPPORTED_SYMBOLS = ("XBTUSD", "ETHUSD")
LIVE_KEY_NAMES = ("KRAKEN_API_KEY", "KRAKEN_API_SECRET")

_ENGINE: Optional[ShadowEngine] = None


def get_engine() -> ShadowEngine:
    """Process-wide shadow book for kraken (positions survive across calls)."""
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = ShadowEngine(VENUE)
    return _ENGINE


def normalize_symbol(symbol: Any) -> str:
    """'BTC/USD', 'BTCUSD', 'XBTUSD' -> 'XBTUSD' (Kraken altname)."""
    return _kraken_pair(symbol)


def _quote_fn(symbol: str) -> Optional[Dict[str, Any]]:
    """Executor quote contract: bid/ask/last + source + fetched_at epoch.
    Returns None on any failure -> engine refuses as refused_feed_unavailable."""
    try:
        ticker = get_kraken_adapter().get_ticker(symbol)
        return {
            "bid": ticker.get("bid"),
            "ask": ticker.get("ask"),
            "last": ticker.get("last"),
            "source": ticker.get("source") or "kraken_public_ticker_live",
            "fetched_at": ticker.get("fetched_at") or time.time(),
        }
    except Exception as exc:
        logger.debug("kraken shadow quote failed for %s: %s", symbol, exc)
        return None


def propose_signal(symbol: Any, side: str, qty: float,
                   signal_source: str, signal_confidence: float) -> Dict[str, Any]:
    """Shadow-intent entry point (hub-facing). Returns the journaled result."""
    engine = get_engine()
    raw = str(symbol).strip()
    try:
        sym = normalize_symbol(raw)
    except Exception as exc:
        order = ShadowOrder(VENUE, raw, side, qty, signal_source, signal_confidence)
        return engine._refuse(order, "refused_invalid_order", str(exc))
    if sym not in SUPPORTED_SYMBOLS:
        order = ShadowOrder(VENUE, sym, side, qty, signal_source, signal_confidence)
        return engine._refuse(
            order, "refused_invalid_order",
            f"symbol {sym!r} not in supported {SUPPORTED_SYMBOLS}")
    order = ShadowOrder(VENUE, sym, side, qty, signal_source, signal_confidence)
    result = engine.propose(order, _quote_fn)
    if result.get("status") == "refused":
        logger.debug("kraken shadow refused: %s %s %s — %s",
                     side, qty, sym, result.get("reason"))
    return result


def mark_all() -> Dict[str, Any]:
    """MTM all open kraken shadow positions; close stop/TP hits on live quotes."""
    return get_engine().mark_all(_quote_fn)


def close_position(symbol: Any, reason: str = "manual_close") -> Dict[str, Any]:
    """Explicitly close an open shadow position at the live quote."""
    try:
        sym = normalize_symbol(symbol)
    except Exception:
        sym = str(symbol).strip()
    return get_engine().close_position(sym, reason, _quote_fn)


def positions() -> Dict[str, Any]:
    return get_engine().summary()


def live_place(symbol: Any, side: str, qty: float, ordertype: str = "market",
               price: Optional[float] = None, reason: str = "",
               confidence: Optional[float] = None) -> Dict[str, Any]:
    """FAIL-CLOSED live order path. Keys re-read at CALL TIME; never logged.

    Without KRAKEN_API_KEY + KRAKEN_API_SECRET (aureon_radar/.env or env)
    this journals a refused line and returns
    status="refused_not_authorized"; nothing is sent. With keys, the
    expectancy gate runs first (Gary's decree): the confidence-scaled
    expected move must clear 1.25x the venue's real round-trip cost
    (kraken ~0.9% — per-venue VENUE_FEES, not a flat fee); otherwise the
    order is journaled as refused_edge_below_cost and nothing is sent.
    confidence defaults to the hub promotion threshold (0.55) when the
    caller doesn't supply one. Authorized + gated -> delegates to
    KrakenAdapter.place_order (which additionally requires
    KRAKEN_LIVE_ENABLED=true to actually fire).
    """
    ok, present = env_has_keys(LIVE_KEY_NAMES)
    if not ok:
        result = {
            "status": "refused_not_authorized",
            "venue": VENUE,
            "symbol": str(symbol).strip().upper(),
            "side": str(side).strip().lower(),
            "qty": qty,
            "missing_key_names": [n for n, p in present.items() if not p],
            "ts_utc": utc_now_iso(),
        }
        engine = get_engine()
        engine._journal({
            "event": "refused", "venue": VENUE,
            "symbol": result["symbol"], "side": result["side"], "qty": qty,
            "price": None, "fee": None,
            "signal_source": "live_place", "signal_confidence": 1.0,
            "reason": "refused_not_authorized",
            "detail": "KRAKEN_API_KEY/KRAKEN_API_SECRET absent at call time",
        })
        logger.info("kraken live_place REFUSED (not authorized): %s",
                    result["symbol"])
        return result
    # Expectancy gate — fail-closed, before any live order reaches the adapter.
    try:
        verdict = _expectancy_gate.check(
            venue=VENUE, symbol=str(symbol).strip().upper(), side=side,
            qty=qty, price=price,
            confidence=_expectancy_gate.PROMOTION_CONFIDENCE
            if confidence is None else confidence)
    except Exception as exc:
        verdict = {"allowed": False, "reason": f"gate_error: {exc}"}
    if not verdict.get("allowed"):
        result = {
            "status": "refused",
            "reason": verdict.get("reason", "refused_edge_below_cost"),
            "venue": VENUE,
            "symbol": str(symbol).strip().upper(),
            "side": str(side).strip().lower(),
            "qty": qty,
            "expected_move_pct": verdict.get("expected_move_pct"),
            "round_trip_cost_pct": verdict.get("round_trip_cost_pct"),
            "margin_pct": verdict.get("margin_pct"),
            "ts_utc": utc_now_iso(),
        }
        get_engine()._journal({
            "event": "refused", "venue": VENUE,
            "symbol": result["symbol"], "side": result["side"], "qty": qty,
            "price": None, "fee": None,
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
        logger.info("kraken live_place REFUSED (%s): %s",
                    result["reason"], result["symbol"])
        return result
    try:
        sym = normalize_symbol(symbol)
    except Exception as exc:
        return {"status": "refused_invalid_order", "venue": VENUE,
                "symbol": str(symbol).strip().upper(), "detail": str(exc),
                "ts_utc": utc_now_iso()}
    try:
        receipt = get_kraken_adapter().place_order(
            sym, side, qty, ordertype=ordertype, price=price,
            reason=reason or "shadow_live_place")
        return receipt
    except Exception as exc:
        return {"status": "error", "venue": VENUE, "symbol": sym,
                "side": str(side).strip().lower(), "qty": qty,
                "error": f"{type(exc).__name__}: {exc}"[:300],
                "ts_utc": utc_now_iso()}


# ═══════════════════════════════════════════════════════════════════════════
# SELF-TEST — LIVE public data: one 0.001 XBTUSD shadow BUY, journal check,
# MTM pass, then close and verify the pnl line. Also verifies the fail-closed
# live_place gate. Appends real lines to the real journal (state/).
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import json
    import tempfile

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    # Self-test hygiene (2026-09-07): throwaway journal/ledger/book in
    # tempdir — this open/immediate-close round-trip used to write a
    # "selftest_close" close seconds after open into the REAL shadow ledger
    # (the 3-second-exit poison in time-to-capture stats). min_hold is
    # zeroed: the self-test closes by design.
    _tmpdir = Path(tempfile.mkdtemp(prefix="shadow_kraken_selftest_"))
    _ENGINE = ShadowEngine(
        VENUE,
        journal_path=_tmpdir / "shadow_trades.jsonl",
        ledger_path=_tmpdir / "shadow_ledger_summary.json",
        book_path=_tmpdir / f"shadow_book_{VENUE}.json",
    )
    _ENGINE.min_hold_seconds = 0.0
    print(f"self-test state dir (throwaway): {_tmpdir}")

    engine = get_engine()
    journal_path = engine.journal_path
    before = 0
    try:
        before = sum(1 for _ in open(journal_path, encoding="utf-8"))
    except OSError:
        pass
    print(f"journal: {journal_path} ({before} lines before)")

    print("== live_place gate (keys absent -> must refuse, journaled) ==")
    gate = live_place("XBTUSD", "buy", 0.001)
    print(json.dumps(gate, indent=2, sort_keys=True))
    assert gate["status"] == "refused_not_authorized", gate

    print("== shadow BUY 0.001 XBTUSD on live public ticker ==")
    res = propose_signal("XBTUSD", "buy", 0.001, "kraken_shadow_selftest", 0.80)
    print(json.dumps({k: v for k, v in res.items() if k != "position"},
                     indent=2, sort_keys=True, default=str))
    assert res["status"] == "opened", res
    print(f"FILLED at {res['fill_price']}  fee={res['fee']:.6f}  "
          f"provenance={res['provenance']}")

    print("== MTM pass ==")
    marks = mark_all()
    print(json.dumps(marks, indent=2, sort_keys=True, default=str))

    if "XBTUSD" in engine.positions:
        print("== close position (reason=selftest_close) ==")
        close = close_position("XBTUSD", "selftest_close")
        print(json.dumps(close, indent=2, sort_keys=True, default=str))
        assert close["status"] == "closed", close
        print(f"CLOSED at {close['price']}  net_pnl={close['net_pnl']}  "
              f"reason={close['exit_reason']}")
    else:
        print("NOTE: position already closed by protective level during mark_all")

    after = sum(1 for _ in open(journal_path, encoding="utf-8"))
    new_lines = [json.loads(l) for l in
                 open(journal_path, encoding="utf-8").read().splitlines()[before:]]
    print(f"journal: {after} lines after (+{after - before} new)")
    for line in new_lines:
        print("  JOURNAL:", json.dumps(line, sort_keys=True))

    opened = [l for l in new_lines if l.get("event") == "opened"]
    assert opened, "no opened line journaled"
    assert opened[0]["venue"] == "kraken" and opened[0]["symbol"] == "XBTUSD"
    assert opened[0]["provenance"].startswith("kraken_public_ticker_live@"), opened[0]
    closes = [l for l in new_lines if l.get("event") == "closed"]
    if closes:
        assert "net_pnl" in closes[-1] and "pnl_pct" in closes[-1], closes[-1]
    print("SELF-TEST PASSED")
