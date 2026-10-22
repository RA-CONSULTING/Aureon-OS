"""Live trading progress feed builder — Aureon radar (monitoring only).

Assembles aureon_radar/state/trading_progress_state.json every INTERVAL seconds
so Queen Sero's battle-view shows, from REAL sources only:

  positions  — open shadow positions reconstructed by replaying opened/closed
               events from the shadow journals (state/shadow_trades.jsonl plus
               any *.jsonl in exchange_adapters/journals/), enriched with
               Capital.com CFD state when that trace is FRESH.
  capital    — free cash per venue from the last history entry of
               real_portfolio_state.json (written live by
               _portfolio_writer_loop.py); deployed = sum of open position
               notional per venue.
  horizons   — target_pct honours the owner capture floor
               (state/capture_floor.json, decree 2026-09-06, 1% minimum);
               eta_min is derived from REAL mark-to-market velocity observed
               in the journal (never invented); distance-to-target uses a
               current public price via aureon_price_feed (throttled/cached).
  criteria   — per position: stop-loss / take-profit levels, capture floor,
               expectancy fields (confidence + expected_move_pct from the
               shadow expectancy model), age.

HARD RULES (owner decree, shared contract):
  * NEVER invent numbers — a missing source field is null, not 0.
  * Fail-closed: any source read error marks that block error+null; stale
    sources are reported as stale, never presented as fresh.
  * No live orders. This file only reads journals/state and public prices.

Run (from aureon_radar/, with .env sourced for anything downstream):
    python trading_progress_monitor.py           # loop every 60 s
    python trading_progress_monitor.py --once    # single build + exit
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import os
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

RADAR_ROOT = Path(__file__).resolve().parent
STATE_DIR = RADAR_ROOT / "state"
OUT_PATH = STATE_DIR / "trading_progress_state.json"
PORTFOLIO_PATH = RADAR_ROOT / "real_portfolio_state.json"
SHADOW_JOURNAL_PATH = STATE_DIR / "shadow_trades.jsonl"
JOURNALS_DIR = RADAR_ROOT / "exchange_adapters" / "journals"
CAPITAL_TRACE_PATH = (
    RADAR_ROOT.parent / "aureon-os-upstream" / "state" / "capital_cfd_last_exchange_trace.json"
)

INTERVAL_SEC = float(os.getenv("TRADING_PROGRESS_INTERVAL", "60"))
PORTFOLIO_STALE_SEC = float(os.getenv("TRADING_PROGRESS_PORTFOLIO_STALE_SEC", "180"))
CAPITAL_TRACE_STALE_SEC = float(os.getenv("TRADING_PROGRESS_CAPITAL_STALE_SEC", "120"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("trading_progress_monitor")

# Repo modules (no new dependencies; stdlib + what's already imported here).
for _p in (str(RADAR_ROOT), str(RADAR_ROOT / "exchange_adapters")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

try:
    from aureon_price_feed import get_price  # throttled/cached public prices
    from capture_floor import load_capture_floor
    from expectancy_gate import expected_move_pct as _expected_move_pct
    from shadow_executor import STOP_PCT, effective_take_profit_pct
except Exception as exc:  # fail-closed: module-level import failure is fatal
    logger.error("progress monitor: repo module import failed: %s", exc)
    raise


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_ts(value: Any) -> Optional[float]:
    """Epoch seconds from an epoch number or ISO-8601 string; None if bad."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        v = float(value)
        return v if math.isfinite(v) else None
    text = str(value).strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        pass
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def _num(value: Any) -> Optional[float]:
    if value is None or isinstance(value, bool):
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


# ── symbol normalization (aliases only — prices always come from the feed) ──
_SYMBOL_ALIASES = {
    "BTCUSDT": "BTCUSD",
    "BTC/USD": "BTCUSD",
    "XBTUSD": "BTCUSD",
    "ETHUSDT": "ETHUSD",
    "ETH/USD": "ETHUSD",
    "XETHUSD": "ETHUSD",
}


def feed_symbol(symbol: str) -> str:
    """Map a venue-native symbol to the aureon_price_feed canonical symbol."""
    s = str(symbol or "").strip().upper()
    return _SYMBOL_ALIASES.get(s, s)


# ── position reconstruction from shadow journals ───────────────────────────
def _replay_journal(path: Path, opened: Dict[Tuple[str, str], Dict[str, Any]],
                    marks: Dict[Tuple[str, str], List[Dict[str, Any]]],
                    errors: List[str]) -> None:
    """Replay one journal into `opened` (venue,symbol -> open event) and
    `marks`. Corrupt lines are skipped; an unreadable file is a hard error
    for that source (fail-closed, recorded in `errors`)."""
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception as exc:
        errors.append(f"journal unreadable: {path.name}: {exc}")
        return
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            e = json.loads(line)
        except json.JSONDecodeError:
            continue  # torn/partial line — never crash the feed on it
        if not isinstance(e, dict):
            continue
        venue = str(e.get("venue") or "").strip().lower()
        symbol = str(e.get("symbol") or "").strip()
        event = str(e.get("event") or "").strip().lower()
        if not venue or not symbol:
            continue
        key = (venue, symbol)
        if event == "opened":
            prev = opened.get(key)
            # Same position re-opened after a torn journal: latest open wins.
            if prev is None or (_parse_ts(e.get("ts_utc")) or 0) >= (
                    _parse_ts(prev.get("ts_utc")) or 0):
                opened[key] = e
        elif event == "closed":
            opened.pop(key, None)
        elif event == "mark":
            marks.setdefault(key, []).append(e)


def collect_open_positions() -> Tuple[Dict[Tuple[str, str], Dict[str, Any]],
                                      Dict[Tuple[str, str], List[Dict[str, Any]]],
                                      List[str]]:
    """Reconstruct open shadow positions from ALL shadow journal sources."""
    opened: Dict[Tuple[str, str], Dict[str, Any]] = {}
    marks: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
    errors: List[str] = []

    sources = [SHADOW_JOURNAL_PATH]
    if JOURNALS_DIR.is_dir():
        sources.extend(sorted(JOURNALS_DIR.glob("*.jsonl")))
    for src in sources:
        if src.exists():
            _replay_journal(src, opened, marks, errors)

    # Dedup marks against the authoritative open set only; sort each list by ts
    # so velocity estimation sees a clean time series.
    for key in list(marks):
        if key not in opened:
            del marks[key]
        else:
            marks[key].sort(key=lambda e: _parse_ts(e.get("ts_utc")) or 0.0)
    return opened, marks, errors


# ── Capital.com CFD state (only when the trader's trace is FRESH) ──────────
def collect_capital_trace(now: float) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """Open Capital CFD exposure from capital_cfd_trader's exchange trace.

    The trader keeps live positions in memory; its on-disk trace is a
    point-in-time snapshot. If it is older than CAPITAL_TRACE_STALE_SEC we
    refuse to present it as fresh (fail-closed) and return no positions.
    """
    try:
        st = CAPITAL_TRACE_PATH.stat()
    except Exception as exc:
        return [], f"capital trace unavailable: {exc}"
    age = now - st.st_mtime
    if age > CAPITAL_TRACE_STALE_SEC:
        return [], (f"capital_cfd_trader trace stale "
                    f"({age:.0f}s > {CAPITAL_TRACE_STALE_SEC:.0f}s) — "
                    f"no fresh Capital position state on disk")
    try:
        trace = json.loads(CAPITAL_TRACE_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        return [], f"capital trace unreadable: {exc}"
    envelope = trace.get("capital_risk_envelope") if isinstance(trace, dict) else None
    if not isinstance(envelope, dict):
        return [], "capital trace has no capital_risk_envelope"
    gross = _num(envelope.get("existing_gross_notional_gbp"))
    if not gross or gross <= 0:
        return [], None  # truthfully: no open Capital exposure recorded
    symbol = str(trace.get("symbol") or "").strip().upper()
    direction = str(trace.get("direction") or "").strip().upper()
    size = _num(trace.get("size"))
    pos = {
        "venue": "capital",
        "symbol": symbol or None,
        "direction": direction.lower() if direction in ("BUY", "SELL") else None,
        "size": size,
        "entry_price": None,  # trace records candidate price, not a fill
        "entry_ts_utc": None,
        "signal_confidence": None,
        "_from_capital_trace": True,
    }
    return [pos], None


# ── per-venue capital from the portfolio writer's live file ────────────────
VENUE_BALANCE_KEYS = {
    "alpaca": "alpaca_usd",
    "kraken": "kraken_usd",
    "binance": "binance_usd",
    "capital": "capital_usd",
}


def collect_capital(now: float) -> Dict[str, Any]:
    """Free cash per venue from the LAST history entry of
    real_portfolio_state.json. Missing/corrupt/stale file => error+nulls."""
    block: Dict[str, Any] = {
        "deployed_usd": None, "free_usd": None, "by_venue": {}, "error": None,
        "source_age_sec": None,
    }
    try:
        raw = json.loads(PORTFOLIO_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        block["error"] = f"real_portfolio_state.json unreadable: {exc}"
        for venue in VENUE_BALANCE_KEYS:
            block["by_venue"][venue] = {"free_usd": None, "deployed_usd": None,
                                        "error": block["error"]}
        return block
    history = raw.get("history")
    if not isinstance(history, list) or not history:
        block["error"] = "real_portfolio_state.json has no history entries"
        for venue in VENUE_BALANCE_KEYS:
            block["by_venue"][venue] = {"free_usd": None, "deployed_usd": None,
                                        "error": block["error"]}
        return block
    last = history[-1] if isinstance(history[-1], dict) else {}
    ts = _parse_ts(last.get("timestamp"))
    if ts is None:
        block["error"] = "last portfolio history entry has no usable timestamp"
    else:
        age = now - ts
        block["source_age_sec"] = round(age, 1)
        if age > PORTFOLIO_STALE_SEC:
            block["error"] = (f"portfolio state stale ({age:.0f}s > "
                              f"{PORTFOLIO_STALE_SEC:.0f}s) — not fresh")

    free_total: Optional[float] = None
    for venue, key in VENUE_BALANCE_KEYS.items():
        v_block: Dict[str, Any] = {"free_usd": None, "deployed_usd": 0.0,
                                   "error": None}
        bal = _num(last.get(key))
        if bal is not None and block["error"] is None:
            v_block["free_usd"] = bal
            free_total = (free_total or 0.0) + bal
        else:
            v_block["error"] = block["error"] or f"venue balance field {key} missing"
        block["by_venue"][venue] = v_block

    if block["error"] is None:
        block["free_usd"] = free_total
    return block


# ── position enrichment ────────────────────────────────────────────────────
def _eta_from_marks(position_marks: List[Dict[str, Any]], entry: float,
                    sign: int, target_pct: float) -> Tuple[Optional[float], int]:
    """ETA (minutes) to the capture target from REAL mark-to-market velocity.

    Uses every journaled mark for this position: velocity of progress-pct
    vs time. Returns (eta_min, marks_used). eta is None when velocity is not
    positive (not converging) or fewer than 2 marks exist — never guessed.
    """
    pts: List[Tuple[float, float]] = []
    for e in position_marks:
        ts = _parse_ts(e.get("ts_utc"))
        price = _num(e.get("price"))
        if ts is None or price is None or not entry:
            continue
        pts.append((ts, ((price - entry) / entry) * 100.0 * sign))
    if len(pts) < 2:
        return None, len(pts)
    t0, p0 = pts[0]
    t1, p1 = pts[-1]
    dt = t1 - t0
    if dt <= 0:
        return None, len(pts)
    velocity = (p1 - p0) / dt  # progress-pct per second
    if velocity <= 0:
        return None, len(pts)
    remaining = max(0.0, target_pct - p1)
    return round((remaining / velocity) / 60.0, 1), len(pts)


def build_position_block(open_event: Dict[str, Any],
                         position_marks: List[Dict[str, Any]],
                         floor: Optional[float],
                         tp_pct: float) -> Dict[str, Any]:
    venue = str(open_event.get("venue") or "").strip().lower() or None
    symbol = str(open_event.get("symbol") or "").strip() or None
    side = str(open_event.get("side") or "").strip().lower()
    direction = side if side in ("buy", "sell") else None
    sign = 1 if direction == "buy" else (-1 if direction == "sell" else 0)

    qty = _num(open_event.get("position_qty")) or _num(open_event.get("qty"))
    entry = _num(open_event.get("position_entry_price")) or _num(open_event.get("price"))
    conf = _num(open_event.get("signal_confidence"))
    entry_ts = _parse_ts(open_event.get("ts_utc"))

    size_usd = round(qty * entry, 6) if (qty is not None and entry is not None) else None

    current: Optional[float] = None
    price_error: Optional[str] = None
    if symbol:
        try:
            current = get_price(feed_symbol(symbol))  # throttled/cached feed
        except Exception as exc:
            price_error = f"price feed error: {exc}"
        if current is not None and not (isinstance(current, float) and math.isfinite(current)):
            current = None
    if current is None and price_error is None:
        price_error = "price feed returned no live quote"

    pnl_usd: Optional[float] = None
    pct_to_target: Optional[float] = None
    close_ready: Optional[bool] = None
    if current is not None and entry and sign:
        pnl_usd = round((current - entry) * (qty or 0.0) * sign, 8) if qty is not None else None
        tp_price = entry * (1 + tp_pct * sign)
        dist = (tp_price - current) * sign
        pct_to_target = round((dist / current) * 100.0, 4) if current else None
        close_ready = bool(dist <= 0)

    eta_min, marks_used = (None, 0)
    if entry and sign:
        eta_min, marks_used = _eta_from_marks(position_marks, entry, sign, tp_pct * 100.0)

    # Take-profit/stop-loss levels actually enforced by shadow_executor.
    criteria: Dict[str, Any] = {
        "capture_floor_pct": round(floor * 100.0, 4) if floor is not None else None,
        "target_tp_pct": round(tp_pct * 100.0, 4),
        "stop_loss_pct": round(STOP_PCT * 100.0, 4),
        "take_profit_price": round(entry * (1 + tp_pct * sign), 8)
        if entry and sign else None,
        "stop_loss_price": round(entry * (1 + STOP_PCT * sign), 8)
        if entry and sign else None,
        "expectancy_confidence": conf,
        "expected_move_pct": round(_expected_move_pct(conf), 6)
        if conf is not None else None,
        "opened_ts_utc": open_event.get("ts_utc"),
        "marks_used_for_eta": marks_used,
        "size_native": qty,
    }

    block: Dict[str, Any] = {
        "venue": venue,
        "symbol": symbol,
        "direction": direction,
        "size_usd": size_usd,
        "entry": entry,
        "current": current,
        "pnl_usd": pnl_usd,
        "target_pct": round(tp_pct * 100.0, 4),
        "pct_to_target": pct_to_target,
        "eta_min": eta_min,
        "close_ready": close_ready,
        "criteria": criteria,
        "error": price_error if current is None else None,
        "provenance": open_event.get("provenance"),
    }
    return block


def build_state() -> Dict[str, Any]:
    now = time.time()
    ts = utc_now_iso()

    floor = load_capture_floor()            # fraction; None if decree file bad
    tp_pct = effective_take_profit_pct()    # TP honoring the capture floor

    opened, marks, journal_errors = collect_open_positions()
    capital_positions, capital_note = collect_capital_trace(now)

    positions: List[Dict[str, Any]] = []
    for key in sorted(opened):
        try:
            positions.append(build_position_block(opened[key], marks.get(key, []),
                                                  floor, tp_pct))
        except Exception as exc:  # one bad position must not kill the feed
            positions.append({"venue": key[0], "symbol": key[1], "error":
                              f"position build failed: {exc}"})
    for pos in capital_positions:
        block: Dict[str, Any] = {
            "venue": "capital", "symbol": pos.get("symbol"),
            "direction": pos.get("direction"),
            "size_usd": None, "entry": None, "current": None, "pnl_usd": None,
            "target_pct": round(tp_pct * 100.0, 4),
            "pct_to_target": None, "eta_min": None, "close_ready": None,
            "criteria": {"capture_floor_pct": round(floor * 100.0, 4)
                         if floor is not None else None,
                         "note": "gross notional only — trace has no fill price"},
            "error": "capital trace lacks entry fill — pnl/eta not computable",
        }
        positions.append(block)

    # Deployed notional per venue from the reconstructed position set.
    capital_block = collect_capital(now)
    deployed: Dict[str, float] = {}
    for p in positions:
        v = str(p.get("venue") or "").lower()
        s = p.get("size_usd")
        if v and isinstance(s, (int, float)):
            deployed[v] = deployed.get(v, 0.0) + float(s)
    for venue, v_block in capital_block["by_venue"].items():
        v_block["deployed_usd"] = round(deployed.get(venue, 0.0), 6)
    if capital_block["error"] is None:
        capital_block["deployed_usd"] = round(sum(deployed.values()), 6)

    actionable = [p for p in positions if p.get("close_ready")]
    awaiting = [p for p in positions if not p.get("close_ready")]
    known = [p for p in positions if p.get("current") is not None and p.get("error") is None]
    closest = None
    if known:
        closest = min(known, key=lambda p: p.get("pct_to_target")
                      if p.get("pct_to_target") is not None else 1e9)
    if actionable:
        hint = (f"{len(actionable)} position(s) AT/BEYOND take-profit — "
                f"close path should fire ({', '.join(sorted(p['venue'] + ':' + str(p['symbol']) for p in actionable))})")
    elif closest and closest.get("pct_to_target") is not None:
        hint = (f"{len(positions)} in play; closest to capture: "
                f"{closest['venue']}:{closest['symbol']} "
                f"{closest['pct_to_target']}% to target")
    elif positions:
        hint = f"{len(positions)} in play; no live prices yet — awaiting quotes"
    else:
        hint = "no open positions — awaiting next gated signal"

    return {
        "ts": ts,
        "positions": positions,
        "capital": capital_block,
        "summary": {
            "open_count": len(positions),
            "awaiting_count": len(awaiting),
            "close_ready_count": len(actionable),
            "next_action_hint": hint,
        },
        "meta": {
            "interval_sec": INTERVAL_SEC,
            "journal_errors": journal_errors or None,
            "capital_trace_note": capital_note,
            "capture_floor_present": floor is not None,
            "build": "trading_progress_monitor.py (read-only monitoring; no orders)",
        },
    }


def write_state(state: Dict[str, Any]) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(STATE_DIR), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(state, fh, indent=2, sort_keys=True, allow_nan=False)
        os.replace(tmp, OUT_PATH)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true",
                        help="build the state once and exit (no loop)")
    args = parser.parse_args()

    if args.once:
        state = build_state()
        write_state(state)
        print(f"trading_progress_state.json written: "
              f"{state['summary']['open_count']} open, "
              f"hint={state['summary']['next_action_hint']}", flush=True)
        return

    logger.info("progress feed online — interval %.0fs", INTERVAL_SEC)
    while True:
        try:
            write_state(build_state())
        except Exception as exc:
            # Never die silently: the file keeps its last good write.
            logger.error("cycle error: %s", exc)
        time.sleep(INTERVAL_SEC)


if __name__ == "__main__":
    main()
