"""Keep ORCA's hands off Alpaca, Binance and Kraken holdings Aureon did not enter.

Companion to ``orca_capital_ownership`` (the CN50 guard). Owner rule, 9 Nov 2026:
Aureon must not close or manage positions Gary opened himself, and skips any
position with no Aureon shadow trade, forecast or entry plan.

``orca_live_monitor`` and ``orca_unified_kill_chain`` read every non-stable
balance or position on these venues. A balance alone (or a row in
``cost_basis_history.json``, which comes from exchange trade history, not from
Aureon) says nothing about who opened it. A holding becomes an exit candidate
only when Aureon has a recorded entry for that venue and asset:

* an open BUY in the radar shadow book ``aureon_radar/state/shadow_book_<venue>.json``
  written by ``aureon_radar/exchange_adapters/shadow_executor.ShadowEngine``
  (Aureon's persisted shadow-trade entry, with entry price and qty); or
* ``venue:ASSET`` listed in ``AUREON_ORCA_ADOPT_POSITIONS``, a comma-separated
  list the operator sets on purpose, mirroring ``AUREON_ORCA_CAPITAL_ADOPT_DEALS``.

This fails closed: a missing, unreadable or malformed book adopts nothing for
that venue, and an unrecognised symbol is never owned. Nothing here closes,
changes or contacts anything; it only filters a list.
"""

from __future__ import annotations

import json
import os
from collections.abc import Iterable
from pathlib import Path
from typing import Any

ADOPT_ENV = "AUREON_ORCA_ADOPT_POSITIONS"
STATE_DIR_ENV = "AUREON_ORCA_SHADOW_STATE_DIR"
SPOT_VENUES = ("alpaca", "binance", "kraken")

_QUOTES = ("USDT", "USDC", "BUSD", "ZUSD", "ZGBP", "ZEUR", "USD", "GBP", "EUR")
_ALIASES = {"XBT": "BTC", "XXBT": "BTC", "XETH": "ETH", "XXRP": "XRP", "XLTC": "LTC", "XXDG": "DOGE", "XDG": "DOGE"}


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


def _state_dir(state_dir: Path | None, env: dict[str, str]) -> Path:
    if state_dir is not None:
        return Path(state_dir)
    if env.get(STATE_DIR_ENV):
        return Path(env[STATE_DIR_ENV])
    root = env.get("SERO_WORKSPACE") or str(Path(__file__).resolve().parents[2])
    return Path(root) / "aureon_radar" / "state"


def _adopted(venue: str, env: dict[str, str]) -> set[str]:
    owned: set[str] = set()
    for part in (env.get(ADOPT_ENV, "") or "").split(","):
        if ":" not in part:
            continue
        v, sym = part.split(":", 1)
        if v.strip().lower() == venue and base_asset(sym):
            owned.add(base_asset(sym))
    return owned


def _shadow_book_entries(venue: str, state_dir: Path) -> set[str]:
    """Assets with an open BUY in the venue's shadow book. Any doubt gives an empty set."""
    try:
        raw = json.loads((state_dir / f"shadow_book_{venue}.json").read_text(encoding="utf-8"))
        rows = raw.get("positions")
        if not isinstance(rows, dict):
            return set()
        found: set[str] = set()
        for sym, row in rows.items():
            if not isinstance(row, dict):
                return set()
            if str(row.get("venue") or venue).lower() != venue:
                continue
            if str(row.get("side") or "").lower() != "buy":
                continue
            if not float(row.get("qty") or 0) > 0:
                continue
            asset = base_asset(row.get("symbol") or sym)
            if asset:
                found.add(asset)
        return found
    except Exception:
        return set()


def recorded_entries(
    venue: str, env: dict[str, str] | None = None, state_dir: Path | None = None
) -> set[str]:
    venue = str(venue or "").strip().lower()
    if venue not in SPOT_VENUES:
        return set()
    env = dict(os.environ if env is None else env)
    return _adopted(venue, env) | _shadow_book_entries(venue, _state_dir(state_dir, env))


def is_owned(
    venue: str, symbol: Any, env: dict[str, str] | None = None, state_dir: Path | None = None
) -> bool:
    asset = base_asset(symbol)
    return bool(asset) and asset in recorded_entries(venue, env=env, state_dir=state_dir)


def split_owned_spot(
    venue: str,
    positions: Iterable[dict[str, Any]],
    env: dict[str, str] | None = None,
    state_dir: Path | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return (owned, skipped) by each row's ``symbol``. Error rows pass through as owned."""
    entries = recorded_entries(venue, env=env, state_dir=state_dir)
    owned: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for row in positions or []:
        if not isinstance(row, dict):
            skipped.append(row)
            continue
        asset = base_asset(row.get("symbol"))
        if "error" in row or (asset and asset in entries):
            owned.append(row)
        else:
            skipped.append(row)
    return owned, skipped
