"""Keep ORCA's hands off Alpaca, Binance and Kraken holdings Aureon did not fill.

Companion to ``orca_capital_ownership`` (the CN50 guard). Owner rule, 9 Nov 2026:
Aureon must not close or manage positions Gary opened himself.

A balance alone says nothing about who bought it, and neither does a row in
``cost_basis_history.json`` (exchange trade history) or a paper/shadow book
(``aureon_radar/state/shadow_book_<venue>.json`` holds simulated fills only).
ORCA may exit a spot holding only up to Aureon's **recorded net real fill**:

* entries: ``orca_executions.json`` lines written by
  ``aureon_radar/bots/orca_unified_kill_chain.UnifiedKillChain._execute_trade``
  whose ``result.status`` is ``FILLED`` *and* whose broker receipt
  (``result.order``) shows a positive ``executedQty``/``filled_qty`` with no
  dry-run, paper, shadow or not-submitted marker. ``BALANCE_DRY_RUN``,
  ``SKIPPED``, ``NO_FUNDS`` and every other status are not fills. The
  requested ``volume`` is never used as a fill;
* exits subtracted: ``orca_executions.json`` lines with ``"kind": "exit"``
  (kill-chain spot sells) and SELL lines in ``aureon_radar/orca_live_journal.jsonl``
  (``orca_live_monitor.submit_exit_order``). Every exit attempt is subtracted
  unless it was refused before reaching the venue, so a failed or unknown
  exit only ever lowers what is sellable;
* ``AUREON_ORCA_ADOPT_POSITIONS`` (``venue:ASSET`` or ``venue:ASSET:QTY``,
  comma-separated) is the operator's explicit manual adopt list, mirroring
  ``AUREON_ORCA_CAPITAL_ADOPT_DEALS``. ``venue:ASSET:QTY`` adds QTY to the cap.
  ``venue:ASSET`` with no QTY adopts the whole holding: the cap is the venue
  balance, exactly as an adopted Capital deal is closed whole.

Fail closed: a missing executions file gives no entries; any unparseable or
non-object line in either record file makes that venue's sellable qty 0 (only
an explicit QTY-less adoption still applies). Nothing here closes, changes or
contacts anything; it only computes a cap.
"""

from __future__ import annotations

import json
import math
import os
from collections.abc import Iterable
from pathlib import Path
from typing import Any

ADOPT_ENV = "AUREON_ORCA_ADOPT_POSITIONS"
ROOT_ENV = "AUREON_ORCA_RECORDS_ROOT"
SPOT_VENUES = ("alpaca", "binance", "kraken")
EXECUTIONS_FILE = "orca_executions.json"
LIVE_JOURNAL_FILE = Path("aureon_radar") / "orca_live_journal.jsonl"
WHOLE = math.inf

_QUOTES = ("USDT", "USDC", "BUSD", "ZUSD", "ZGBP", "ZEUR", "USD", "GBP", "EUR")
_ALIASES = {"XBT": "BTC", "XXBT": "BTC", "XETH": "ETH", "XXRP": "XRP", "XLTC": "LTC", "XXDG": "DOGE", "XDG": "DOGE"}
_NOT_SENT = {"refused", "blocked_freshness"}
_DRY_FLAGS = ("dryRun", "dry_run", "simulated", "paper", "shadow")
_DRY_WORDS = ("dry", "paper", "shadow", "simulat", "not_submitted", "skip")


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


def records_root(env: dict[str, str] | None = None) -> Path:
    env = os.environ if env is None else env
    if env.get(ROOT_ENV):
        return Path(env[ROOT_ENV])
    return Path(env.get("SERO_WORKSPACE") or Path(__file__).resolve().parents[2])


def executions_path(env: dict[str, str] | None = None) -> Path:
    """Where the kill chain writes, and this module reads, ORCA execution records."""
    return records_root(env) / EXECUTIONS_FILE


def _positive(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) and number > 0 else None


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


def _looks_dry(blob: Any) -> bool:
    if not isinstance(blob, dict):
        return True
    if any(bool(blob.get(flag)) for flag in _DRY_FLAGS):
        return True
    if blob.get("submitted") is False:
        return True
    for key in ("status", "mode", "data_status", "truth_status", "reason"):
        value = str(blob.get(key) or "").lower()
        if any(word in value for word in _DRY_WORDS):
            return True
    return False


def real_fill(row: dict[str, Any]) -> tuple[str, str, float] | None:
    """(venue, asset, filled_qty) for a real ORCA entry fill, else None."""
    if row.get("kind") == "exit":
        return None
    result = row.get("result")
    opportunity = row.get("opportunity") if isinstance(row.get("opportunity"), dict) else {}
    if not isinstance(result, dict) or str(result.get("status") or "").upper() != "FILLED":
        return None
    venue = str(result.get("exchange") or opportunity.get("exchange") or "").lower()
    if venue not in SPOT_VENUES or _looks_dry(result):
        return None
    order = result.get("order")
    if _looks_dry(order):
        return None
    qty = _positive(order.get("executedQty")) or _positive(order.get("filled_qty"))
    asset = base_asset(result.get("pair") or opportunity.get("symbol"))
    if qty is None or not asset:
        return None
    return venue, asset, qty


def _exit_of_execution(row: dict[str, Any]) -> tuple[str, str, float] | None:
    if row.get("kind") != "exit":
        return None
    if str(row.get("status") or "").lower() in _NOT_SENT:
        return None
    venue = str(row.get("exchange") or "").lower()
    qty = _positive(row.get("qty"))
    asset = base_asset(row.get("asset") or row.get("symbol"))
    if venue not in SPOT_VENUES or qty is None or not asset:
        return None
    return venue, asset, qty


def _exit_of_journal(row: dict[str, Any]) -> tuple[str, str, float] | None:
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


def _adoptions(venue: str, env: dict[str, str]) -> dict[str, float]:
    """asset -> extra cap (WHOLE when no QTY was given)."""
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


def recorded_net_fills(venue: str, env: dict[str, str] | None = None) -> dict[str, float]:
    """asset -> Aureon's net real filled qty on this venue (fills minus exits), > 0 only."""
    venue = str(venue or "").strip().lower()
    if venue not in SPOT_VENUES:
        return {}
    env = dict(os.environ if env is None else env)
    root = records_root(env)
    try:
        executions = _lines(root / EXECUTIONS_FILE)
        journal = _lines(root / LIVE_JOURNAL_FILE)
    except _Unreadable:
        return {}
    net: dict[str, float] = {}
    for row in executions:
        fill = real_fill(row)
        if fill and fill[0] == venue:
            net[fill[1]] = net.get(fill[1], 0.0) + fill[2]
    exits = [_exit_of_execution(r) for r in executions] + [_exit_of_journal(r) for r in journal]
    for item in exits:
        if item and item[0] == venue:
            net[item[1]] = net.get(item[1], 0.0) - item[2]
    return {asset: qty for asset, qty in net.items() if qty > 1e-12}


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
    return recorded_net_fills(venue, env).get(asset, 0.0) + adopted


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
