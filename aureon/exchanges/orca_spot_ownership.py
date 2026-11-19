"""Keep ORCA's hands off Alpaca, Binance and Kraken holdings Aureon did not fill.

Companion to ``orca_capital_ownership`` (the CN50 guard). Owner rule, 9 Nov 2026:
Aureon must not close or manage positions Gary opened himself.

A balance alone says nothing about who bought it, and neither does a row in
``cost_basis_history.json`` (exchange trade history), a paper/shadow book
(``aureon_radar/state/shadow_book_<venue>.json`` holds simulated fills only)
or ``orca_executions.json`` (an attempt log: ERROR, NO_FUNDS, BUY_FAILED,
ARBITRAGE_LOGGED, BALANCE_DRY_RUN and not-submitted receipts sit beside real
orders). None of them is read here.

ORCA may exit a spot holding only up to its **sellable cap**:

* ``aureon_owned_qty(venue, symbol)`` from ``aureon.exchanges.orca_real_fills``
  (PR #382): the locked ledger ``state/aureon_real_fills.jsonl`` of the kill
  chain's exchange-confirmed fills, buys minus sells for that venue and exact
  symbol, ``0`` on a missing, unreadable or corrupt ledger. When that module is
  not installed (``#370`` merged first) the local fallback is ``0``: nothing is
  owned. The ledger keys fills by exact symbol (``ETHUSD`` on Kraken,
  ``ETHUSDT`` on Binance), so the cap sums the helper over the spellings of one
  base asset on that venue (``ETH``, ``ETHUSD``, ``ETH/USD``, ``XETHZUSD``,
  ``ETHUSDT``, ...). Each fill sits under exactly one spelling, so nothing is
  counted twice. Only the venue asked for counts;
* minus exits this branch records and the ledger does not: every spot sell
  attempt of ``execute_kill_chain`` (``state/orca_spot_exits.jsonl``, written by
  ``record_spot_exit``) and every SELL of ``orca_live_monitor.submit_exit_order``
  (``aureon_radar/orca_live_journal.jsonl``). Attempts refused before reaching
  the venue (``refused``, ``blocked_freshness``) are not subtracted; failed or
  unknown ones are, so they only ever lower the cap. If the ledger later also
  records one of these sells it is subtracted twice, which errs towards holding;
* plus ``AUREON_ORCA_ADOPT_POSITIONS`` (``venue:ASSET`` or ``venue:ASSET:QTY``,
  comma-separated), the operator's explicit manual adopt list, mirroring
  ``AUREON_ORCA_CAPITAL_ADOPT_DEALS``. An adoption counts only for its own
  venue. ``venue:ASSET:QTY`` adds QTY (a positive number; 0, negative or
  unparseable adopts nothing). ``venue:ASSET`` with no QTY adopts the whole
  holding: the cap is the venue balance, exactly as an adopted Capital deal is
  closed whole.

Fail closed: any helper error or a non-finite/negative/non-numeric owned qty
is 0; an unreadable exits record makes the owned part 0 (only an adoption
still applies). Nothing here places, closes or contacts anything.
"""

from __future__ import annotations

import importlib
import json
import math
import os
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ADOPT_ENV = "AUREON_ORCA_ADOPT_POSITIONS"
ROOT_ENV = "AUREON_ORCA_RECORDS_ROOT"
REAL_FILLS_MODULE = "aureon.exchanges.orca_real_fills"
SPOT_VENUES = ("alpaca", "binance", "kraken")
SPOT_EXITS_FILE = Path("state") / "orca_spot_exits.jsonl"
LIVE_JOURNAL_FILE = Path("aureon_radar") / "orca_live_journal.jsonl"
WHOLE = math.inf

_QUOTES = ("USDT", "USDC", "BUSD", "ZUSD", "ZGBP", "ZEUR", "USD", "GBP", "EUR")
_ALIASES = {"XBT": "BTC", "XXBT": "BTC", "XETH": "ETH", "XXRP": "XRP", "XLTC": "LTC", "XXDG": "DOGE", "XDG": "DOGE"}
_NOT_SENT = {"refused", "blocked_freshness"}


class _Unreadable(Exception):
    pass


def base_asset(symbol: Any) -> str:
    """``KNC``, ``KNC/USD``, ``KNCUSD`` and ``KNCUSDT`` all give ``KNC``. Empty when unknown."""
    text = str(symbol or "").strip().upper()
    for sep in ("/", "-", ":", " ", "_"):
        if sep in text:
            text = text.split(sep, 1)[0]
            break
    else:
        for quote in _QUOTES:
            if text.endswith(quote) and len(text) > len(quote):
                text = text[: -len(quote)]
                break
    return _ALIASES.get(text, text)


def symbol_spellings(symbol: Any) -> list[str]:
    """Every ledger spelling of ``symbol``'s base asset: bare, base+quote, base/quote, Kraken X..Z.."""
    asset = base_asset(symbol)
    if not asset:
        return []
    bases = [asset] + [code for code, alias in _ALIASES.items() if alias == asset]
    quotes = ("USDT", "USDC", "BUSD", "USD", "EUR", "GBP")
    found = [str(symbol or "").strip().upper()]
    for base in bases:
        found.append(base)
        for quote in quotes:
            found += [base + quote, f"{base}/{quote}", f"{base}-{quote}"]
            if quote in ("USD", "EUR", "GBP"):
                found += [base + "Z" + quote, "X" + base + "Z" + quote]
    seen: list[str] = []
    for item in found:
        if item and item not in seen and base_asset(item) == asset:
            seen.append(item)
    return seen


def _positive(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError, ArithmeticError):
        return None
    return number if math.isfinite(number) and number > 0 else None


def _ledger_helper():
    """``orca_real_fills.aureon_owned_qty`` when #382 is installed, else None."""
    try:
        return getattr(importlib.import_module(REAL_FILLS_MODULE), "aureon_owned_qty", None)
    except Exception:
        return None


def aureon_owned_qty(venue: str, symbol: str) -> float:
    """Aureon's confirmed real buys minus sells on ``venue`` for ``symbol``'s base asset.

    Same name and arguments as ``orca_real_fills.aureon_owned_qty`` (#382), which
    it delegates to for every spelling of the asset; 0.0 when that module is
    absent, on any error, or when the total is not a positive finite number.
    """
    venue_key = str(venue or "").strip().lower()
    helper = _ledger_helper()
    if helper is None or venue_key not in SPOT_VENUES:
        return 0.0
    total = 0.0
    try:
        for spelling in symbol_spellings(symbol):
            number = float(helper(venue_key, spelling))
            if not math.isfinite(number):
                return 0.0
            total += number
    except Exception:
        return 0.0
    return total if total > 0 else 0.0


def records_root(env: dict[str, str] | None = None) -> Path:
    env = os.environ if env is None else env
    if env.get(ROOT_ENV):
        return Path(env[ROOT_ENV])
    return Path(env.get("SERO_WORKSPACE") or Path(__file__).resolve().parents[2])


def spot_exits_path(env: dict[str, str] | None = None) -> Path:
    return records_root(env) / SPOT_EXITS_FILE


def record_spot_exit(exchange: str, symbol: str, qty: Any, status: str) -> None:
    """Append one kill-chain spot sell attempt so the cap subtracts it. Raises on I/O error."""
    path = spot_exits_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps({
            "timestamp": datetime.now(UTC).isoformat(),
            "venue": str(exchange or "").lower(),
            "symbol": str(symbol or ""),
            "side": "sell",
            "qty": qty,
            "status": status,
        }) + "\n")
        fh.flush()
        os.fsync(fh.fileno())


def _lines(path: Path) -> list[dict[str, Any]]:
    """Every line as an object. Missing file: []. Any bad line: _Unreadable."""
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return []
    except OSError as exc:
        raise _Unreadable(str(exc)) from exc
    rows = []
    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except ValueError as exc:
            raise _Unreadable(f"{path.name}: unparseable line") from exc
        if not isinstance(row, dict):
            raise _Unreadable(f"{path.name}: non-object line")
        rows.append(row)
    return rows


def _exit(row: dict[str, Any]) -> tuple[str, str, float] | None:
    if str(row.get("side") or "").lower() != "sell":
        return None
    if str(row.get("status") or "").lower() in _NOT_SENT:
        return None
    venue = str(row.get("venue") or "").lower()
    qty = _positive(row.get("qty"))
    asset = base_asset(row.get("symbol"))
    if venue not in SPOT_VENUES or qty is None or not asset:
        return None
    return venue, asset, qty


def recorded_exits(venue: str, env: dict[str, str] | None = None) -> dict[str, float] | None:
    """asset -> qty ORCA tried to sell on this venue outside the ledger; None if unreadable."""
    root = records_root(env)
    try:
        rows = _lines(root / SPOT_EXITS_FILE) + _lines(root / LIVE_JOURNAL_FILE)
    except _Unreadable:
        return None
    out: dict[str, float] = {}
    for row in rows:
        item = _exit(row)
        if item and item[0] == venue:
            out[item[1]] = out.get(item[1], 0.0) + item[2]
    return out


def _adoptions(venue: str, env: dict[str, str]) -> dict[str, float]:
    """asset -> extra cap on this venue only (WHOLE when no QTY was given)."""
    adopted: dict[str, float] = {}
    for part in (env.get(ADOPT_ENV, "") or "").split(","):
        bits = [b.strip() for b in part.split(":")]
        if len(bits) < 2 or bits[0].lower() != venue or not base_asset(bits[1]):
            continue
        asset = base_asset(bits[1])
        if len(bits) == 2:
            adopted[asset] = WHOLE
        else:
            qty = _positive(bits[2])
            if qty is not None and adopted.get(asset) != WHOLE:
                adopted[asset] = adopted.get(asset, 0.0) + qty
    return adopted


def _owned(venue: str, symbol: Any, env: dict[str, str]) -> float:
    owned = _positive(aureon_owned_qty(venue, symbol)) or 0.0
    if owned <= 0:
        return 0.0
    exits = recorded_exits(venue, env)
    if exits is None:
        return 0.0
    return max(0.0, owned - exits.get(base_asset(symbol), 0.0))


def sellable_cap(venue: str, symbol: Any, env: dict[str, str] | None = None) -> float:
    """Most ORCA may exit for this venue+asset: 0.0 (not ORCA's), a qty, or WHOLE."""
    venue = str(venue or "").strip().lower()
    asset = base_asset(symbol)
    if venue not in SPOT_VENUES or not asset:
        return 0.0
    env = dict(os.environ if env is None else env)
    adopted = _adoptions(venue, env).get(asset, 0.0)
    if adopted == WHOLE:
        return WHOLE
    return _owned(venue, symbol, env) + adopted


def is_owned(venue: str, symbol: Any, env: dict[str, str] | None = None) -> bool:
    return sellable_cap(venue, symbol, env=env) > 0


def capped_qty(venue: str, symbol: Any, qty: Any, env: dict[str, str] | None = None) -> float:
    """min(qty, cap); 0.0 when not ORCA's or qty is not a positive number."""
    held = _positive(qty)
    if held is None:
        return 0.0
    return min(held, sellable_cap(venue, symbol, env=env))


def split_owned_spot(
    venue: str,
    positions: Iterable[dict[str, Any]],
    env: dict[str, str] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return (owned, skipped). Owned rows are copies with ``qty`` capped; error rows pass through."""
    owned: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for row in positions or []:
        if isinstance(row, dict) and "error" in row:
            owned.append(row)
            continue
        if not isinstance(row, dict):
            skipped.append(row)
            continue
        qty = capped_qty(venue, row.get("symbol"), row.get("qty"), env=env)
        if qty > 0:
            capped = dict(row)
            if qty < float(row.get("qty") or 0):
                capped["qty_balance"] = row.get("qty")
            capped["qty"] = qty
            owned.append(capped)
        else:
            skipped.append(row)
    return owned, skipped
