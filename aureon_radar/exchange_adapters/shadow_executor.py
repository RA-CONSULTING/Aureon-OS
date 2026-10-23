"""Shadow execution engine — Aureon radar (organism-controlled).

BINDING SCHEMA (decided here; venue agents and the hub must conform):

- A "shadow order" is a labeled simulation of intent filled against a REAL,
  FRESH public quote. It never leaves the machine and never touches keys.
- Data-freshness doctrine is ABSOLUTE. If the injected quote function is
  unreachable, returns no usable price, or returns a quote older than
  STALE_AFTER_SEC (30 s), the order is REFUSED with event="refused" and a
  `reason` of:
      refused_feed_unavailable  — quote function raised / returned nothing
      refused_feed_stale        — quote timestamp older than 30 s, or its
                                  timestamp is missing/unparseable (cannot
                                  prove freshness => not fresh)
      refused_invalid_order     — bad side/qty/symbol
  A refused order is journaled and NEVER filled. No price is ever fabricated.

- QUOTE CONTRACT (venue quote functions must return a mapping with):
      bid, ask, last   : floats (any may be absent, not all)
      source           : str provenance label (e.g. "kraken_public_ticker_live")
      fetched_at       : epoch seconds (float/int) OR ISO-8601 str
      ts_utc           : ISO-8601 str (alternative to fetched_at)
  The venue wrappers in shadow_{kraken,alpaca,binance}.py adapt the native
  adapter payloads to this contract. `provenance` in the journal is
  "<source>@<ISO-8601 of the quote's own timestamp>". A quote function that
  fails must return None or raise — the engine converts that into
  refused_feed_unavailable.

- FILL MODEL: reference = ask for BUY, bid for SELL (taker realism);
  fallbacks: last, then mid=(bid+ask)/2. Adverse slippage SLIPPAGE (0.05 %)
  is applied against the direction: buy_fill = ref*(1+SLIPPAGE),
  sell_fill = ref*(1-SLIPPAGE). Taker fee is charged on fill notional:
  kraken 0.40 %, binance 0.10 %, alpaca 0.0 % (VENUE_FEES below).

- FEE JOURNALING (2026-09-07): a close's journaled `fees` is the
  CONSERVATIVE MAX of the modeled entry+exit taker fees and the venue cost
  model's round-trip floor: notional * round_trip_cost_pct, venue+symbol
  specific from state/hunting_grounds.json when the schedule is fresh
  (< 24 h), else a labeled 0.2 % estimate (matches dreamt_plays cost_model).
  This closes the old hole where e.g. alpaca closes journaled fees 0.0 while
  the cost model says 0.2-0.54 % round trip. net_pnl = gross - fees. The
  close entry carries fee_basis / fee_is_estimate / round_trip_cost_pct /
  round_trip_fee_floor / taker_fees for audit; the ledger adds
  total_estimated_fees per pair and in totals.

- MINIMUM HOLD (2026-09-07): no close of any kind (stop, TP, reversal, or
  manual) within MIN_HOLD_SECONDS (default 60 s, env SHADOW_MIN_HOLD_SECS)
  of the open. The journal had 14/25 closes exiting <3 s after open — mark
  noise and open/close self-test round-trips, not signal outcomes. A blocked
  close returns {"status": "held_min_hold"} and journals a throttled
  event="held_min_hold" line; the position stays open and is re-evaluated on
  the next mark cycle. Same pattern as CAPITAL_FAST_PROFIT_MIN_HOLD_SECS in
  capital_cfd_trader.py.

- POSITIONS: one open position per (venue, symbol). An opposite-side propose
  on an open position closes it first (reason="reversal"), then opens the new
  one. Same-side propose on an open position adds to it at a volume-weighted
  average entry and journals event="filled". Protective levels from entry:
  stop-loss -2 %, take-profit +3 % (STOP_PCT / TAKE_PROFIT_PCT) — the TP is
  clamped UPWARD to the owner capture floor at call time (see
  effective_take_profit_pct; owner decree 2026-09-06, ≥ 1.0%).

- JOURNAL: aureon_radar/state/shadow_trades.jsonl — one JSON line per event:
  event in {"opened","filled","closed","refused","mark"} with fields
  ts_utc, event, venue, symbol, side, qty, price, fee, signal_source,
  signal_confidence, provenance (omitted when unavailable); closes add
  entry_price, exit_reason, gross_pnl, fees, net_pnl, pnl_pct, hold_seconds,
  plus the fee-audit fields above; blocked min-hold closes add
  event="held_min_hold" with exit_reason, hold_seconds, min_hold_seconds.
  `mark` events (MTM heartbeat) are throttled to one per position per
  MARK_JOURNAL_THROTTLE_SEC (default 300 s) to keep the journal honest but
  bounded; MTM itself updates in memory every call.

- LEDGER: aureon_radar/state/shadow_ledger_summary.json — rewritten after
  every close, keyed "<venue>:<symbol>", with closed_trades, wins, losses,
  win_rate, total gross/net pnl, total fees, plus a "totals" block.

- BOOK: state/shadow_book_<venue>.json (next to the journal) — the open
  position book is persisted atomically after every open/fill/close and
  reloaded at engine construction. Gap fix 2026-09-07: the book used to be
  in-memory only, so any hub restart orphaned every open position — the
  journal said "opened" but no live process would ever mark or close it
  again (shadow_trades.jsonl closes/marks stopped ~18:49Z on 2026-09-06,
  one minute after the hub restarted). A missing/corrupt book file fails
  closed to an empty book, never to fabricated positions.

- LIVE GATE: live_place() in the venue wrappers is FAIL-CLOSED. It re-reads
  aureon_radar/.env AND os.environ at CALL TIME (values are never logged,
  returned, or journaled — key NAMES only) and returns
  {"status": "refused_not_authorized", ...} unless both required key
  variables are non-empty. When keys are present it delegates to the venue
  adapter's existing order path.

Import has no side effects. Network happens only inside venue quote functions.
"""

from __future__ import annotations

import json
import logging
import math
import os
import tempfile
import threading
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

RADAR_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_JOURNAL_PATH = RADAR_ROOT / "state" / "shadow_trades.jsonl"
DEFAULT_LEDGER_PATH = RADAR_ROOT / "state" / "shadow_ledger_summary.json"
ENV_PATH = RADAR_ROOT / ".env"

# ── binding constants (see module docstring) ─────────────────────────────
STALE_AFTER_SEC = 30.0
SLIPPAGE = 0.0005          # 0.05 % adverse, applied to fill price
MARK_JOURNAL_THROTTLE_SEC = 300.0
STOP_PCT = -0.02           # -2 % from entry fill
TAKE_PROFIT_PCT = 0.03     # +3 % from entry fill
VENUE_FEES: Dict[str, float] = {
    # Taker fees (all organism orders are market orders = takers).
    # Kraken tier 0 (<$10k 30d volume): 0.40% taker / 0.25% maker — corrected
    # 2026-09-06 from 0.26% (bug-hunt: fee math understated real cost).
    "kraken": 0.0040,
    "binance": 0.0010,   # VIP0 spot taker
    "alpaca": 0.0,       # crypto: commission-free, cost lives in spread
    # Capital.com CFD: no flat taker fee — the round-trip cost IS the spread,
    # and the spread is already embedded in the quoted/fill price, so adding
    # a fee here would double-count. Round-trip cost for the expectancy gate
    # is therefore slippage-only (2 * 0.05% via round_trip_cost()).
    "capital": 0.0,
}
DEFAULT_FEE = 0.0

# ── round-trip cost model (fee journaling, 2026-09-07) ────────────────────
HUNTING_GROUNDS_PATH = RADAR_ROOT / "state" / "hunting_grounds.json"
# A cost SCHEDULE (not a tick quote) is "fresh" within a day. Older, missing,
# or unparseable => we cannot trust the venue mapping and fall back.
HG_FRESH_MAX_AGE_SEC = 24.0 * 3600.0
# Conservative labeled fallback; matches state/dreamt_plays.json cost_model
# (round_trip_pct 0.2, source venue_cost_fallback, label "estimate").
ROUND_TRIP_FALLBACK_PCT = 0.002
ROUND_TRIP_FALLBACK_LABEL = "estimate_0.2pct_fallback"
# Minimum hold before ANY close (protective, reversal, manual). The shadow
# journal showed 14/25 closes exiting <3 s after open (mark noise plus
# open/close self-test round-trips), poisoning time-to-capture stats. Same
# pattern as CAPITAL_FAST_PROFIT_MIN_HOLD_SECS in capital_cfd_trader.py.
MIN_HOLD_SECONDS = float(os.environ.get("SHADOW_MIN_HOLD_SECS", "60"))
HELD_JOURNAL_THROTTLE_SEC = 300.0

QuoteFn = Callable[[str], Optional[Dict[str, Any]]]

# Owner capture floor (Gary Leckey, 2026-09-06): TP targets never sit below
# the floor (state/capture_floor.json, default 1.0%). Read at call time; an
# absent/corrupt file means the floor is absent (TAKE_PROFIT_PCT stands) —
# that is capture_floor's own fail-closed contract and we preserve it exactly
# even when the capture_floor MODULE itself cannot be imported: unified_hub
# loads this module by file path with exchange_adapters/ NOT on sys.path
# (2026-09-07 incident: "No module named 'capture_floor'" made every shadow
# venue inert in the live hub), so this import must never be load-bearing.
try:
    from .capture_floor import load_capture_floor, apply_floor_to_tp_pct
except ImportError:  # pragma: no cover - direct-script / path-loaded fallback
    try:
        from capture_floor import load_capture_floor, apply_floor_to_tp_pct
    except ImportError:  # pragma: no cover - capture_floor module unavailable
        load_capture_floor = None  # type: ignore[assignment]

        def apply_floor_to_tp_pct(tp_pct: float, floor: Optional[float]) -> float:
            return tp_pct if floor is None else max(tp_pct, floor)


def effective_take_profit_pct() -> float:
    """TP pct from entry, clamped UPWARD to the owner capture floor.

    TAKE_PROFIT_PCT is +3%; the floor (1.0% by decree) only binds when it
    exceeds that, and never pulls a higher target down. Absent/corrupt
    decree file — or an unavailable capture_floor module — means the floor
    is absent: plain TAKE_PROFIT_PCT (prior behavior), never weakened.
    """
    floor = load_capture_floor() if load_capture_floor is not None else None
    return apply_floor_to_tp_pct(TAKE_PROFIT_PCT, floor)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _iso_from_epoch(epoch: float) -> str:
    return datetime.fromtimestamp(epoch, tz=timezone.utc).isoformat()


def _parse_ts_epoch(value: Any) -> Optional[float]:
    """Epoch seconds from an epoch number or an ISO-8601 string; None if bad."""
    if value is None:
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value) if math.isfinite(float(value)) else None
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


@dataclass
class ShadowOrder:
    venue: str
    symbol: str
    side: str            # "buy" | "sell"
    qty: float
    signal_source: str
    signal_confidence: float
    ts_utc: str = field(default_factory=utc_now_iso)


@dataclass
class ShadowPosition:
    venue: str
    symbol: str
    side: str
    qty: float
    entry_price: float
    entry_fee: float
    entry_ts_utc: str
    signal_source: str
    signal_confidence: float
    fees_paid: float = 0.0
    last_mark: float = 0.0
    last_mark_ts_utc: str = ""
    last_mark_journal_ts: float = 0.0
    last_held_journal_ts: float = 0.0

    @property
    def direction_sign(self) -> int:
        return 1 if self.side == "buy" else -1

    def unrealized(self, mark_price: float) -> float:
        return (mark_price - self.entry_price) * self.qty * self.direction_sign


def normalize_quote(raw: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Validate a venue quote payload against the contract. Raises ValueError.

    Returns {bid, ask, last, mid, ref candidates..., ts_epoch, provenance}.
    """
    if not isinstance(raw, dict):
        raise ValueError("quote function returned no payload")
    bid = _finite(raw.get("bid"))
    ask = _finite(raw.get("ask"))
    last = _finite(raw.get("last"))
    price = _finite(raw.get("price"))          # binance-style {price: ...}
    if last is None:
        last = price
    if bid is None and ask is None and last is None:
        raise ValueError(f"quote has no usable price fields: {sorted(raw.keys())}")
    mid = (bid + ask) / 2.0 if (bid is not None and ask is not None) else None
    ts_epoch = _parse_ts_epoch(raw.get("fetched_at"))
    if ts_epoch is None:
        ts_epoch = _parse_ts_epoch(raw.get("ts_utc"))
    if ts_epoch is None:
        raise ValueError("quote has no parseable timestamp — freshness unprovable")
    source = str(raw.get("source") or raw.get("provenance") or "unknown_feed")
    return {
        "bid": bid, "ask": ask, "last": last, "mid": mid,
        "ts_epoch": ts_epoch, "source": source,
        "provenance": f"{source}@{_iso_from_epoch(ts_epoch)}",
    }


def _finite(value: Any) -> Optional[float]:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def check_quote_fresh(quote: Dict[str, Any], now: Optional[float] = None) -> Tuple[bool, str]:
    """(is_fresh, refusal_reason_if_not). Age > STALE_AFTER_SEC => stale."""
    now = time.time() if now is None else now
    age = now - quote["ts_epoch"]
    if age > STALE_AFTER_SEC:
        return False, "refused_feed_stale"
    return True, ""


def reference_price(quote: Dict[str, Any], side: str) -> float:
    """Taker reference: ask for buy, bid for sell; fallback last, then mid."""
    primary = quote["ask"] if side == "buy" else quote["bid"]
    for candidate in (primary, quote["last"], quote["mid"]):
        if candidate is not None and candidate > 0:
            return candidate
    raise ValueError("no positive reference price in quote")


def apply_fill(price: float, side: str, fee_rate: float, qty: float) -> Dict[str, float]:
    """Adverse slippage on price + taker fee on notional. Never fabricates."""
    slipped = price * (1 + SLIPPAGE) if side == "buy" else price * (1 - SLIPPAGE)
    notional = slipped * qty
    fee = notional * fee_rate
    return {"fill_price": slipped, "notional": notional, "fee": fee}


def _norm_cost_symbol(symbol: Any) -> str:
    """Cost-schedule symbol key: uppercase, separators stripped, venue
    aliases unified (XBT->BTC, USDT->USD) so engine symbols (XBTUSD,
    BTCUSDT, BTC/USD) match hunting-grounds rows (BTC/USD)."""
    s = str(symbol or "").upper().replace("/", "").replace("-", "").replace("_", "")
    if s.startswith("XBT"):
        s = "BTC" + s[3:]
    if s.endswith("USDT"):
        s = s[:-4] + "USD"
    return s


def round_trip_cost_pct(venue: str, symbol: str,
                        now: Optional[float] = None) -> Tuple[float, bool, str]:
    """(pct, is_estimate, source) for a venue+symbol round trip. Fail-closed:
    any doubt (missing/stale schedule, no symbol match) yields the
    conservative labeled 0.2% estimate — never zero, never fabricated.
    Fresh hunting-grounds rows win, real observations over journaled
    estimates. Mirrors juice_gate.spread_for conventions."""
    fallback = (ROUND_TRIP_FALLBACK_PCT, True, ROUND_TRIP_FALLBACK_LABEL)
    try:
        raw = json.loads(HUNTING_GROUNDS_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return fallback
    if not isinstance(raw, dict):
        return fallback
    ts_epoch = _parse_ts_epoch(raw.get("timestamp"))
    now = time.time() if now is None else now
    if ts_epoch is None or now - ts_epoch > HG_FRESH_MAX_AGE_SEC:
        return fallback  # stale or freshness unprovable: cannot trust mapping
    grounds = raw.get("grounds")
    if not isinstance(grounds, list):
        return fallback
    key = str(venue or "").lower()
    sym = _norm_cost_symbol(symbol)
    best_est: Optional[float] = None
    for g in grounds:
        if not isinstance(g, dict):
            continue
        if str(g.get("exchange", "")).lower() != key:
            continue
        if _norm_cost_symbol(g.get("symbol")) != sym:
            continue
        pct = _finite(g.get("round_trip_cost_pct"))
        if pct is None or pct <= 0:
            continue
        if not g.get("spread_is_estimate", True):
            return pct, False, "hunting_grounds_real"
        if best_est is None:
            best_est = pct
    if best_est is not None:
        return best_est, True, "hunting_grounds_estimate"
    return fallback


def env_has_keys(key_names: Tuple[str, ...], env_path: Path = ENV_PATH) -> Tuple[bool, Dict[str, bool]]:
    """CALL-TIME, fail-closed key presence check. Never reads values into
    logs: returns (all_present, {name: present_bool}) only."""
    present: Dict[str, bool] = {}
    file_vals: Dict[str, str] = {}
    try:
        for line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            name, _, value = line.partition("=")
            file_vals[name.strip()] = value.strip().strip('"').strip("'")
    except OSError:
        pass
    for name in key_names:
        from_env = bool((os.environ.get(name) or "").strip())
        from_file = bool(file_vals.get(name, ""))
        present[name] = from_env or from_file
    return all(present.values()), present


def _atomic_write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(obj, fh, indent=2, sort_keys=True, default=str)
            fh.write("\n")
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


class ShadowLedger:
    """Per (venue:symbol) closed-trade stats, exported after every close."""

    def __init__(self, path: Path = DEFAULT_LEDGER_PATH):
        self.path = Path(path)
        self._lock = threading.Lock()

    def record_close(self, close: Dict[str, Any]) -> Dict[str, Any]:
        key = f"{close['venue']}:{close['symbol']}"
        with self._lock:
            try:
                summary = json.loads(self.path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                summary = {"by_pair": {}, "totals": {}}
            by_pair = summary.setdefault("by_pair", {})
            entry = by_pair.setdefault(key, {
                "venue": close["venue"], "symbol": close["symbol"],
                "closed_trades": 0, "wins": 0, "losses": 0, "win_rate": 0.0,
                "total_gross_pnl": 0.0, "total_net_pnl": 0.0, "total_fees": 0.0,
                "total_estimated_fees": 0.0,
                "last_close_ts_utc": "", "updated_ts_utc": "",
            })
            entry.setdefault("total_estimated_fees", 0.0)
            net = float(close.get("net_pnl", 0.0))
            gross = float(close.get("gross_pnl", 0.0))
            fees = float(close.get("fees", 0.0))
            entry["closed_trades"] += 1
            if net > 0:
                entry["wins"] += 1
            elif net < 0:
                entry["losses"] += 1
            entry["total_gross_pnl"] += gross
            entry["total_net_pnl"] += net
            entry["total_fees"] += fees
            if close.get("fee_is_estimate"):
                entry["total_estimated_fees"] += fees
            decided = entry["wins"] + entry["losses"]
            entry["win_rate"] = round(entry["wins"] / decided, 4) if decided else 0.0
            entry["last_close_ts_utc"] = close.get("ts_utc", "")
            entry["updated_ts_utc"] = utc_now_iso()
            totals = summary.setdefault("totals", {})
            for k, v in (("closed_trades", 0), ("wins", 0), ("losses", 0),
                         ("win_rate", 0.0), ("total_gross_pnl", 0.0),
                         ("total_net_pnl", 0.0), ("total_fees", 0.0),
                         ("total_estimated_fees", 0.0)):
                totals.setdefault(k, v)
            totals["closed_trades"] += 1
            if net > 0:
                totals["wins"] += 1
            elif net < 0:
                totals["losses"] += 1
            totals["total_gross_pnl"] += gross
            totals["total_net_pnl"] += net
            totals["total_fees"] += fees
            if close.get("fee_is_estimate"):
                totals["total_estimated_fees"] += fees
            t_decided = totals["wins"] + totals["losses"]
            totals["win_rate"] = round(totals["wins"] / t_decided, 4) if t_decided else 0.0
            summary["ts_utc"] = utc_now_iso()
            _atomic_write_json(self.path, summary)
            return summary


class ShadowEngine:
    """Venue-scoped shadow book: proposals -> fills -> positions -> closes.

    quote_fn(symbol) -> quote-contract mapping, or None/raise on failure.
    """

    def __init__(self, venue: str,
                 journal_path: Path = DEFAULT_JOURNAL_PATH,
                 ledger_path: Path = DEFAULT_LEDGER_PATH,
                 book_path: Optional[Path] = None):
        self.venue = venue.lower().strip()
        self.journal_path = Path(journal_path)
        self.ledger = ShadowLedger(ledger_path)
        self.fee_rate = VENUE_FEES.get(self.venue, DEFAULT_FEE)
        self.min_hold_seconds = MIN_HOLD_SECONDS
        self.book_path = Path(book_path) if book_path is not None else \
            self.journal_path.with_name(f"shadow_book_{self.venue}.json")
        self.positions: Dict[str, ShadowPosition] = {}
        self._lock = threading.Lock()
        self._load_book()

    # ── journal ──────────────────────────────────────────────────────────
    def _journal(self, entry: Dict[str, Any]) -> None:
        entry.setdefault("ts_utc", utc_now_iso())
        self.journal_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.journal_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, sort_keys=True, default=str) + "\n")
        logger.debug("shadow journal: %s", {k: entry.get(k) for k in
                                            ("event", "venue", "symbol", "reason")})

    def _refuse(self, order: ShadowOrder, reason: str, detail: str = "") -> Dict[str, Any]:
        entry = {
            "event": "refused", "venue": self.venue, "symbol": order.symbol,
            "side": order.side, "qty": order.qty, "price": None, "fee": None,
            "signal_source": order.signal_source,
            "signal_confidence": order.signal_confidence,
            "reason": reason,
        }
        if detail:
            entry["detail"] = detail[:300]
        self._journal(entry)
        return {"status": "refused", "reason": reason, "detail": detail,
                "journal": str(self.journal_path)}

    # ── open-book persistence (survives process restart) ─────────────────
    def _save_book(self) -> None:
        """Atomically persist the open position book. Callers hold _lock."""
        try:
            payload = {
                "venue": self.venue,
                "saved_ts_utc": utc_now_iso(),
                "positions": {sym: asdict(pos) for sym, pos in self.positions.items()},
            }
            _atomic_write_json(self.book_path, payload)
        except Exception as exc:  # persistence must never break the trade path
            logger.warning("shadow book save failed (%s): %s", self.venue, exc)

    def _load_book(self) -> None:
        """Reload open positions written by a previous process. Fail-closed:
        a missing or corrupt book yields an empty book, never fabricated
        positions."""
        try:
            if not self.book_path.exists():
                return
            raw = json.loads(self.book_path.read_text(encoding="utf-8"))
            rows = raw.get("positions")
            if not isinstance(rows, dict):
                raise ValueError("book has no positions mapping")
            loaded: Dict[str, ShadowPosition] = {}
            for sym, row in rows.items():
                if not isinstance(row, dict):
                    raise ValueError(f"book row for {sym!r} is not a mapping")
                pos = ShadowPosition(
                    venue=str(row.get("venue") or self.venue),
                    symbol=str(row.get("symbol") or sym),
                    side=str(row.get("side") or ""),
                    qty=float(row["qty"]),
                    entry_price=float(row["entry_price"]),
                    entry_fee=float(row.get("entry_fee") or 0.0),
                    entry_ts_utc=str(row.get("entry_ts_utc") or utc_now_iso()),
                    signal_source=str(row.get("signal_source") or "unknown"),
                    signal_confidence=float(row.get("signal_confidence") or 0.0),
                    fees_paid=float(row.get("fees_paid") or 0.0),
                    last_mark=float(row.get("last_mark") or 0.0),
                    last_mark_ts_utc=str(row.get("last_mark_ts_utc") or ""),
                    last_mark_journal_ts=0.0,  # re-arm the mark journal throttle
                )
                if pos.side not in {"buy", "sell"}:
                    raise ValueError(f"book row for {sym!r} has invalid side")
                if not (math.isfinite(pos.qty) and pos.qty > 0):
                    raise ValueError(f"book row for {sym!r} has invalid qty")
                if not (math.isfinite(pos.entry_price) and pos.entry_price > 0):
                    raise ValueError(f"book row for {sym!r} has invalid entry_price")
                loaded[pos.symbol] = pos
            self.positions = loaded
            if loaded:
                logger.info("shadow book restored: %s %d open position(s) from %s",
                            self.venue, len(loaded), self.book_path)
        except FileNotFoundError:
            pass
        except Exception as exc:
            # Fail closed: start empty rather than trust a corrupt book.
            logger.warning("shadow book load failed (%s), starting empty: %s",
                           self.venue, exc)
            self.positions = {}

    # ── quote acquisition (absolute freshness doctrine) ──────────────────
    def _fresh_quote(self, symbol: str, quote_fn: QuoteFn) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """Returns (quote, refusal_reason). quote is None on any failure."""
        try:
            raw = quote_fn(symbol)
            quote = normalize_quote(raw)
        except Exception as exc:
            return None, "refused_feed_unavailable",  # type: ignore[return-value]
        fresh, reason = check_quote_fresh(quote)
        if not fresh:
            return None, reason
        return quote, None

    # ── order path ───────────────────────────────────────────────────────
    def propose(self, order: ShadowOrder, quote_fn: QuoteFn) -> Dict[str, Any]:
        order.venue = self.venue
        order.side = str(order.side).strip().lower()
        if order.side not in {"buy", "sell"}:
            return self._refuse(order, "refused_invalid_order", f"side={order.side!r}")
        qty = _finite(order.qty)
        if qty is None or qty <= 0:
            return self._refuse(order, "refused_invalid_order", f"qty={order.qty!r}")
        order.qty = qty
        if not str(order.symbol).strip():
            return self._refuse(order, "refused_invalid_order", "empty symbol")

        quote, refusal = self._fresh_quote(order.symbol, quote_fn)
        if quote is None:
            return self._refuse(order, refusal or "refused_feed_unavailable")

        with self._lock:
            open_pos = self.positions.get(order.symbol)
            if open_pos and open_pos.side != order.side:
                close = self._close_locked(open_pos, quote, reason="reversal")
                if close.get("status") != "closed":
                    return close
            return self._fill_locked(order, quote)

    def _fill_locked(self, order: ShadowOrder, quote: Dict[str, Any]) -> Dict[str, Any]:
        ref = reference_price(quote, order.side)
        fill = apply_fill(ref, order.side, self.fee_rate, order.qty)
        existing = self.positions.get(order.symbol)
        if existing and existing.side == order.side:
            total_qty = existing.qty + order.qty
            existing.entry_price = (
                existing.entry_price * existing.qty + fill["fill_price"] * order.qty
            ) / total_qty
            existing.qty = total_qty
            existing.fees_paid += fill["fee"]
            existing.signal_source = order.signal_source
            existing.signal_confidence = order.signal_confidence
            event = "filled"
            position = existing
        else:
            position = ShadowPosition(
                venue=self.venue, symbol=order.symbol, side=order.side,
                qty=order.qty, entry_price=fill["fill_price"], entry_fee=fill["fee"],
                entry_ts_utc=order.ts_utc,
                signal_source=order.signal_source,
                signal_confidence=order.signal_confidence,
                fees_paid=fill["fee"],
            )
            self.positions[order.symbol] = position
            event = "opened"
        position.last_mark = fill["fill_price"]
        position.last_mark_ts_utc = utc_now_iso()
        entry = {
            "event": event, "venue": self.venue, "symbol": order.symbol,
            "side": order.side, "qty": order.qty, "price": fill["fill_price"],
            "fee": round(fill["fee"], 10), "signal_source": order.signal_source,
            "signal_confidence": order.signal_confidence,
            "provenance": quote["provenance"],
            "position_qty": position.qty,
            "position_entry_price": position.entry_price,
        }
        self._journal(entry)
        self._save_book()
        return {"status": event, "fill_price": fill["fill_price"],
                "fee": fill["fee"], "position": position,
                "provenance": quote["provenance"], "journal": str(self.journal_path)}

    # ── close path ───────────────────────────────────────────────────────
    def _journal_held_locked(self, pos: "ShadowPosition", reason: str,
                             hold: float) -> None:
        """Throttled journal of a min-hold-blocked close (one line per
        HELD_JOURNAL_THROTTLE_SEC per position; mark noise must not spam)."""
        now = time.time()
        if now - pos.last_held_journal_ts < HELD_JOURNAL_THROTTLE_SEC:
            return
        pos.last_held_journal_ts = now
        self._journal({
            "event": "held_min_hold", "venue": self.venue, "symbol": pos.symbol,
            "side": pos.side, "qty": pos.qty, "price": None, "fee": None,
            "signal_source": pos.signal_source,
            "signal_confidence": pos.signal_confidence,
            "exit_reason": reason, "hold_seconds": round(hold, 3),
            "min_hold_seconds": self.min_hold_seconds,
        })

    def _close_locked(self, pos: ShadowPosition, quote: Dict[str, Any],
                      reason: str) -> Dict[str, Any]:
        exit_side = "sell" if pos.side == "buy" else "buy"
        entry_epoch = _parse_ts_epoch(pos.entry_ts_utc)
        hold = max(0.0, time.time() - entry_epoch) if entry_epoch else 0.0
        if hold < self.min_hold_seconds:
            # Minimum-hold doctrine: no close (protective, reversal, or
            # manual) within min_hold_seconds of open — sub-minute exits are
            # mark noise / test round-trips, not signal outcomes.
            self._journal_held_locked(pos, reason, hold)
            return {"status": "held_min_hold", "venue": self.venue,
                    "symbol": pos.symbol, "exit_reason": reason,
                    "hold_seconds": round(hold, 3),
                    "min_hold_seconds": self.min_hold_seconds}
        ref = reference_price(quote, exit_side)
        fill = apply_fill(ref, exit_side, self.fee_rate, pos.qty)
        gross = (fill["fill_price"] - pos.entry_price) * pos.qty * pos.direction_sign
        # Fee journaling (2026-09-07): the journaled fee is the CONSERVATIVE
        # MAX of the modeled entry+exit taker fees and the venue cost model's
        # round-trip floor (notional * round_trip_cost_pct from fresh
        # hunting_grounds, else labeled 0.2% estimate). Never zero, never
        # double-counted. net = gross - fees.
        taker_fees = pos.fees_paid + fill["fee"]
        notional = pos.entry_price * pos.qty
        rt_pct, rt_is_estimate, rt_source = round_trip_cost_pct(self.venue, pos.symbol)
        rt_floor = notional * rt_pct
        if rt_floor > taker_fees:
            fees = rt_floor
            fee_basis = rt_source
        else:
            fees = taker_fees
            fee_basis = "venue_taker"
        fee_is_estimate = bool(fee_basis != "venue_taker" and rt_is_estimate)
        net = gross - fees                  # gross minus journaled round-trip cost
        pnl_pct = (net / notional) if notional else 0.0
        entry = {
            "event": "closed", "venue": self.venue, "symbol": pos.symbol,
            "side": exit_side, "qty": pos.qty, "price": fill["fill_price"],
            "fee": round(fill["fee"], 10),
            "signal_source": pos.signal_source,
            "signal_confidence": pos.signal_confidence,
            "provenance": quote["provenance"],
            "entry_price": pos.entry_price, "exit_reason": reason,
            "gross_pnl": round(gross, 10), "fees": round(fees, 10),
            "net_pnl": round(net, 10), "pnl_pct": round(pnl_pct, 8),
            "hold_seconds": round(hold, 3),
            "taker_fees": round(taker_fees, 10),
            "round_trip_cost_pct": rt_pct,
            "round_trip_fee_floor": round(rt_floor, 10),
            "fee_basis": fee_basis, "fee_is_estimate": fee_is_estimate,
        }
        self._journal(entry)
        self.ledger.record_close(entry)
        del self.positions[pos.symbol]
        self._save_book()
        result = dict(entry)
        result.update({"status": "closed", "journal": str(self.journal_path)})
        return result

    def close_position(self, symbol: str, reason: str, quote_fn: QuoteFn) -> Dict[str, Any]:
        symbol = str(symbol).strip()
        with self._lock:
            pos = self.positions.get(symbol)
            if pos is None:
                return {"status": "no_position", "venue": self.venue, "symbol": symbol}
            quote, refusal = self._fresh_quote(symbol, quote_fn)
            if quote is None:
                order = ShadowOrder(self.venue, symbol, "sell", pos.qty,
                                    pos.signal_source, pos.signal_confidence)
                return self._refuse(order, refusal or "refused_feed_unavailable")
            return self._close_locked(pos, quote, reason)

    # ── mark-to-market + protective levels ───────────────────────────────
    def _check_protective(self, pos: ShadowPosition, mark_price: float) -> Optional[str]:
        # TP distance honors the owner capture floor (max with TAKE_PROFIT_PCT,
        # read at call time); the stop-loss is untouched by the decree.
        tp_pct = effective_take_profit_pct()
        if pos.side == "buy":
            if mark_price <= pos.entry_price * (1 + STOP_PCT):
                return "stop_loss"
            if mark_price >= pos.entry_price * (1 + tp_pct):
                return "take_profit"
        else:
            if mark_price >= pos.entry_price * (1 - STOP_PCT):
                return "stop_loss"
            if mark_price <= pos.entry_price * (1 - tp_pct):
                return "take_profit"
        return None

    def mark_all(self, quote_fn: QuoteFn, journal_marks: bool = True,
                 throttle_sec: float = MARK_JOURNAL_THROTTLE_SEC) -> Dict[str, Any]:
        """MTM every open position; close any that hit stop (-2%) or TP (+3%)."""
        results = {"marked": [], "closed": [], "refused": [], "held": []}
        with self._lock:
            symbols = list(self.positions.keys())
        for symbol in symbols:
            with self._lock:
                pos = self.positions.get(symbol)
            if pos is None:
                continue
            quote, refusal = self._fresh_quote(symbol, quote_fn)
            if quote is None:
                results["refused"].append({"symbol": symbol, "reason": refusal})
                continue
            mark = quote["last"] or quote["mid"] or reference_price(quote, pos.side)
            with self._lock:
                pos = self.positions.get(symbol)
                if pos is None:
                    continue
                pos.last_mark = mark
                pos.last_mark_ts_utc = utc_now_iso()
                hit = self._check_protective(pos, mark)
                if hit:
                    close_res = self._close_locked(pos, quote, hit)
                    if close_res.get("status") == "closed":
                        results["closed"].append(close_res)
                    else:  # held_min_hold: position stays open, retried next cycle
                        results["held"].append(close_res)
                    continue
            unreal = pos.unrealized(mark)
            results["marked"].append({
                "venue": self.venue, "symbol": symbol, "mark": mark,
                "unrealized_pnl": round(unreal, 10),
                "provenance": quote["provenance"],
            })
            now = time.time()
            if journal_marks and (now - pos.last_mark_journal_ts) >= throttle_sec:
                pos.last_mark_journal_ts = now
                self._journal({
                    "event": "mark", "venue": self.venue, "symbol": symbol,
                    "side": pos.side, "qty": pos.qty, "price": mark,
                    "fee": None, "signal_source": pos.signal_source,
                    "signal_confidence": pos.signal_confidence,
                    "provenance": quote["provenance"],
                    "unrealized_pnl": round(unreal, 10),
                    "entry_price": pos.entry_price,
                })
        return results

    def summary(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "venue": self.venue,
                "open_positions": {
                    sym: {
                        "side": p.side, "qty": p.qty, "entry_price": p.entry_price,
                        "last_mark": p.last_mark,
                        "unrealized_pnl": round(p.unrealized(p.last_mark), 10)
                        if p.last_mark else None,
                        "signal_source": p.signal_source,
                    } for sym, p in self.positions.items()
                },
            }


# ═══════════════════════════════════════════════════════════════════════════
# SELF-TEST — stub quote function only; no network, real files untouched.
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import tempfile

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    tmpdir = Path(tempfile.mkdtemp(prefix="shadow_selftest_"))
    journal = tmpdir / "shadow_trades.jsonl"
    ledger_path = tmpdir / "shadow_ledger_summary.json"

    _price = 100.0

    def stub_quote(symbol: str) -> Dict[str, Any]:
        return {
            "symbol": symbol, "bid": _price - 0.1, "ask": _price + 0.1,
            "last": _price, "source": "stub_feed_SIMULATED_SELFTEST",
            "fetched_at": time.time(),
        }

    engine = ShadowEngine("kraken", journal_path=journal, ledger_path=ledger_path)

    order = ShadowOrder("kraken", "TESTUSD", "buy", 2.0, "selftest", 0.9)
    res = engine.propose(order, stub_quote)
    assert res["status"] == "opened", res
    fill = res["fill_price"]
    assert abs(fill - 100.1 * 1.0005) < 1e-9, fill          # ask + slippage
    kraken_fee_rate = VENUE_FEES["kraken"]  # tracks the fee table (0.40% taker)
    assert abs(res["fee"] - fill * 2.0 * kraken_fee_rate) < 1e-9, res["fee"]
    print(f"OK opened: fill={fill} fee={res['fee']:.6f} provenance={res['provenance']}")

    # minimum-hold: an immediate close of any kind must be HELD, not closed
    held = engine.close_position("TESTUSD", "manual", stub_quote)
    assert held["status"] == "held_min_hold" and held["hold_seconds"] < MIN_HOLD_SECONDS, held
    assert "TESTUSD" in engine.positions, "held close must keep the position open"
    print(f"OK min-hold: immediate close held ({held['hold_seconds']:.3f}s < "
          f"{held['min_hold_seconds']:.0f}s), position kept")
    engine.min_hold_seconds = 0.0  # self-test closes by design

    # stale feed must refuse
    def stale_quote(symbol: str) -> Dict[str, Any]:
        q = stub_quote(symbol)
        q["fetched_at"] = time.time() - 60
        return q

    res2 = engine.propose(ShadowOrder("kraken", "TESTUSD", "buy", 1.0, "selftest", 0.9), stale_quote)
    assert res2["status"] == "refused" and res2["reason"] == "refused_feed_stale", res2
    print("OK stale quote refused:", res2["reason"])

    def dead_quote(symbol: str) -> None:
        return None

    res3 = engine.propose(ShadowOrder("kraken", "TESTUSD", "buy", 1.0, "selftest", 0.9), dead_quote)
    assert res3["reason"] == "refused_feed_unavailable", res3
    print("OK dead feed refused:", res3["reason"])

    # move price +3.1% -> mark should trigger take_profit on mark_all
    _price = 103.2
    marks = engine.mark_all(stub_quote, journal_marks=True, throttle_sec=0)
    assert marks["closed"] and marks["closed"][0]["exit_reason"] == "take_profit", marks
    closed = marks["closed"][0]
    print(f"OK TP close: exit={closed['price']} gross={closed['gross_pnl']:.4f} "
          f"net={closed['net_pnl']:.4f} pnl_pct={closed['pnl_pct']:.5f}")
    # fee audit fields: kraken taker model (0.40% x 2 legs = 0.80%) must win
    # over the cost-model floor (0.2% fallback for unknown TESTUSD; even the
    # 0.72% kraken BTC/USD estimate would lose to 0.80% taker).
    assert closed["fee_basis"] == "venue_taker" and not closed["fee_is_estimate"], closed
    assert closed["round_trip_cost_pct"] == ROUND_TRIP_FALLBACK_PCT or \
           closed["round_trip_cost_pct"] >= ROUND_TRIP_FALLBACK_PCT, closed
    assert abs(closed["fees"] - closed["taker_fees"]) < 1e-9, closed
    assert abs(closed["net_pnl"] - (closed["gross_pnl"] - closed["fees"])) < 1e-9, closed
    print(f"OK fee audit: basis={closed['fee_basis']} fees={closed['fees']:.4f} "
          f"rt_floor={closed['round_trip_fee_floor']:.4f} "
          f"rt_pct={closed['round_trip_cost_pct']}")

    # cost-model lookup: venue+symbol matching with aliases, freshness, fallback
    rt = round_trip_cost_pct("kraken", "XBTUSD")   # aliases to kraken BTC/USD row
    assert rt[0] > 0, rt
    print(f"OK rt lookup kraken XBTUSD: pct={rt[0]} estimate={rt[1]} src={rt[2]}")
    rt2 = round_trip_cost_pct("alpaca", "AAPL")    # no grounds row -> fallback
    assert rt2 == (ROUND_TRIP_FALLBACK_PCT, True, ROUND_TRIP_FALLBACK_LABEL), rt2
    print("OK rt lookup alpaca AAPL -> labeled 0.2% fallback:", rt2)
    rt3 = round_trip_cost_pct("alpaca", "BTC/USD", now=time.time() + 10 * 24 * 3600)
    assert rt3 == (ROUND_TRIP_FALLBACK_PCT, True, ROUND_TRIP_FALLBACK_LABEL), rt3
    print("OK rt lookup stale schedule -> labeled 0.2% fallback:", rt3)

    # zero-taker venue: alpaca close must journal the cost-model floor as fees
    engine2 = ShadowEngine("alpaca", journal_path=journal, ledger_path=ledger_path)
    engine2.min_hold_seconds = 0.0
    res_a = engine2.propose(ShadowOrder("alpaca", "TESTUSD2", "buy", 1.0, "selftest", 0.9),
                            stub_quote)
    assert res_a["status"] == "opened" and res_a["fee"] == 0.0, res_a
    close_a = engine2.close_position("TESTUSD2", "selftest_close", stub_quote)
    assert close_a["status"] == "closed", close_a
    notional = close_a["entry_price"] * 1.0
    expect_floor = notional * ROUND_TRIP_FALLBACK_PCT
    assert close_a["fee_basis"] == ROUND_TRIP_FALLBACK_LABEL and close_a["fee_is_estimate"], close_a
    assert abs(close_a["fees"] - expect_floor) < 1e-6, close_a
    assert abs(close_a["net_pnl"] - (close_a["gross_pnl"] - expect_floor)) < 1e-9, close_a
    print(f"OK alpaca fee floor: fees={close_a['fees']:.6f} (0.2% of notional, "
          f"labeled estimate) net={close_a['net_pnl']:.6f}")

    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    pair = ledger["by_pair"]["kraken:TESTUSD"]
    assert pair["closed_trades"] == 1 and pair["wins"] == 1 and pair["win_rate"] == 1.0, pair
    assert pair["total_fees"] > 0 and pair["total_estimated_fees"] == 0.0, pair
    pair_a = ledger["by_pair"]["alpaca:TESTUSD2"]
    assert pair_a["total_fees"] > 0 and pair_a["total_estimated_fees"] == pair_a["total_fees"], pair_a
    print("OK ledger:", json.dumps(pair, sort_keys=True))
    print("OK ledger (alpaca fee floor):", json.dumps(pair_a, sort_keys=True))

    lines = [json.loads(l) for l in journal.read_text(encoding="utf-8").splitlines()]
    events = [l["event"] for l in lines]
    print("OK journal events:", events)
    assert events[0] == "opened" and events.count("held_min_hold") == 1, events
    assert "closed" in events, events
    print(f"SELF-TEST PASSED — journal at {journal}")
