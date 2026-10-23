#!/usr/bin/env python3
"""
Kraken trading adapter — Aureon radar (organism-controlled).

Pattern follows the repo's existing exchange clients (alpaca_client.py,
binance_client.py) and ports the production Kraken mechanics from the
read-only upstream client (aureon-os-upstream/aureon/exchanges/kraken_client.py):

- Keys: KRAKEN_API_KEY / KRAKEN_API_SECRET, read from the environment AT CALL
  TIME (re-read on every operation, so .env can be energized without restart).
  Secret values are NEVER logged, printed, journaled, or returned.
- No keys (or KRAKEN_DRY_RUN=true) -> honest PAPER mode: orders are computed
  against REAL prices from Kraken's live public feed and journaled as
  paper_dry_run entries. Nothing is fabricated; paper entries are labeled.
- Keys present -> authenticate() validates against /0/private/Balance (read-only).
  Live order placement is additionally gated behind KRAKEN_LIVE_ENABLED=true
  (fail-closed by default): proving mechanics never forces a live trade —
  live firing follows the organism's own auto-arm doctrine.
- Kraken signature: HMAC-SHA512 of (url_path + SHA256(nonce + postdata)) keyed
  with the base64-decoded API secret — identical to upstream's _kraken_sign.

Import has no side effects. Network happens only inside methods.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import math
import os
import threading
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

KRAKEN_BASE = "https://api.kraken.com"
KRAKEN_PUBLIC = KRAKEN_BASE + "/0/public"
KRAKEN_PRIVATE = KRAKEN_BASE + "/0/private"

# Journaled paper orders live beside the repo's other ledgers.
JOURNAL_PATH = Path(__file__).resolve().parents[1] / "paper_journal" / "kraken_paper_journal.jsonl"

# Kraken spot minimum notional (USD-ish) — order refused below this.
DEFAULT_MIN_NOTIONAL = 5.0

# ──────────────────────────────────────────────────────────────────────────
# .env loading (mirrors alpaca_client.py: explicit candidates, no override)
# ──────────────────────────────────────────────────────────────────────────
try:
    from dotenv import load_dotenv

    _candidates = []
    _explicit = os.getenv("DOTENV_PATH")
    if _explicit:
        _candidates.append(Path(_explicit))
    _candidates.append(Path.cwd() / ".env")
    _candidates.append(Path(__file__).resolve().parents[1] / ".env")

    _loaded = False
    for _cand in _candidates:
        try:
            if _cand.exists():
                load_dotenv(dotenv_path=str(_cand), override=False)
                _loaded = True
                break
        except Exception:
            continue
    if not _loaded:
        load_dotenv(override=False)
except ImportError:
    pass


def _canonical_asset(value: Any) -> str:
    asset = str(value or "").strip().upper()
    aliases = {
        "XBT": "BTC", "XXBT": "BTC", "XDG": "DOGE", "XXDG": "DOGE",
        "XETH": "ETH", "XXETH": "ETH", "ZUSD": "USD", "ZEUR": "EUR",
        "ZGBP": "GBP", "ZCAD": "CAD", "ZJPY": "JPY", "ZAUD": "AUD",
    }
    if asset in aliases:
        return aliases[asset]
    if asset.startswith(("X", "Z")) and len(asset) > 3:
        return asset[1:]
    return asset


def _pair_assets(value: Any) -> tuple:
    pair = str(value or "").strip().upper().replace("/", "").replace("-", "")
    for quote in ("USDT", "USDC", "ZUSD", "ZEUR", "ZGBP", "ZCAD", "ZJPY",
                  "ZAUD", "USD", "EUR", "GBP", "CAD", "JPY", "AUD"):
        if pair.endswith(quote) and len(pair) > len(quote):
            return _canonical_asset(pair[: -len(quote)]), _canonical_asset(quote)
    return "", ""


def _kraken_pair(value: Any) -> str:
    """'BTC/USD', 'BTCUSD', 'XBTUSD' -> Kraken altname 'XBTUSD'."""
    base, quote = _pair_assets(value)
    if not base or not quote:
        raise ValueError(f"unparseable pair: {value!r}")
    base = "XBT" if base == "BTC" else ("XDG" if base == "DOGE" else base)
    return base + quote


def _finite(value: Any, *, positive: bool = False) -> Optional[float]:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    if positive and number <= 0.0:
        return None
    return number


class KrakenAdapter:
    """Organism-controlled Kraken spot adapter. Paper without keys, live with."""

    def __init__(self, timeout: float = 10.0):
        self.base = KRAKEN_BASE
        self.timeout = timeout
        self.min_notional = float(os.getenv("KRAKEN_MIN_NOTIONAL", str(DEFAULT_MIN_NOTIONAL)) or DEFAULT_MIN_NOTIONAL)
        self._nonce_lock = threading.Lock()
        self._last_nonce = 0
        # Host rate budget (per-host GlobalRateBudget; graceful absence keeps
        # the adapter usable but unbudgeted — logged once).
        self._rate_budget = None
        self._RequestPriority = None
        self._budget_wait = None
        try:
            from aureon.core.global_rate_budget import (
                RequestPriority,
                get_host_rate_budget,
                wait_for_slot_deferred,
            )
            self._rate_budget = get_host_rate_budget("api.kraken.com")
            self._RequestPriority = RequestPriority
            self._budget_wait = wait_for_slot_deferred
        except Exception as exc:
            logger.debug("kraken GlobalRateBudget unavailable (%s) - running unbudgeted", type(exc).__name__)

    # ── rate budget discipline (defer reads, fail-closed writes) ──────────
    def _budget_acquire(self, priority, *, is_trading: bool = False,
                        write: bool = False, max_wait_s: float = 15.0) -> bool:
        """Queue for a host budget slot. Reads defer and never crash; writes
        raise (fail-closed) if the slot stays deferred past max_wait_s."""
        if self._rate_budget is None:
            return True
        granted = self._budget_wait(
            self._rate_budget, priority, is_trading=is_trading, max_wait_s=max_wait_s
        )
        if not granted:
            if write:
                raise RuntimeError(
                    f"kraken rate budget deferred {priority.name} call beyond "
                    f"{max_wait_s}s - NOT sent (fail-closed)"
                )
            logger.warning(
                "kraken rate budget deferred %s read beyond %ss - proceeding anyway",
                priority.name, max_wait_s,
            )
        return granted

    def _budget_on_429(self, priority) -> None:
        if self._rate_budget is not None:
            try:
                self._rate_budget.on_429_error(priority)
            except Exception:
                pass

    @staticmethod
    def _path_priority(path: str):
        """EXECUTION for order placement, POSITIONS for account reads,
        QUOTES for public market data. Returns the RequestPriority enum."""
        from aureon.core.global_rate_budget import RequestPriority
        lowered = str(path or "").lower()
        if "addorder" in lowered or "cancelorder" in lowered or "trade" in lowered:
            return RequestPriority.EXECUTION
        if "private" in lowered:
            return RequestPriority.POSITIONS
        return RequestPriority.QUOTES

    # ── key handling: read at CALL time, names only, never values ─────────
    def _keys(self) -> tuple:
        key = (os.getenv("KRAKEN_API_KEY") or "").strip()
        secret = (os.getenv("KRAKEN_API_SECRET") or os.getenv("KRAKEN_SECRET") or "").strip()
        return key, secret

    @property
    def has_keys(self) -> bool:
        key, secret = self._keys()
        return bool(key) and bool(secret)

    @property
    def paper_mode(self) -> bool:
        forced = (os.getenv("KRAKEN_DRY_RUN", "false").strip().lower() == "true")
        return forced or not self.has_keys

    @property
    def live_enabled(self) -> bool:
        return os.getenv("KRAKEN_LIVE_ENABLED", "false").strip().lower() == "true"

    # ── public REST (real market data, no auth) ───────────────────────────
    def _public_get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        self._budget_acquire(self._RequestPriority.QUOTES, max_wait_s=10.0)
        url = f"{KRAKEN_PUBLIC}/{endpoint}"
        if params:
            url += "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers={"User-Agent": "AureonKrakenAdapter/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:  # nosec B310 - public market-data endpoint
                payload = json.loads(resp.read().decode("utf-8", errors="replace"))
        except urllib.error.HTTPError as exc:
            if exc.code == 429 and self._rate_budget is not None:
                self._budget_on_429(self._RequestPriority.QUOTES)
            raise
        if isinstance(payload, dict) and payload.get("error"):
            errors = payload["error"]
            if self._rate_budget is not None and any("limit" in str(e).lower() or "throttle" in str(e).lower() for e in (errors if isinstance(errors, list) else [errors])):
                self._budget_on_429(self._RequestPriority.QUOTES)
            raise RuntimeError(f"kraken public {endpoint} error: {payload['error']}")
        result = payload.get("result", {}) if isinstance(payload, dict) else {}
        return result if isinstance(result, dict) else {}

    def get_ticker(self, pair: str) -> Dict[str, float]:
        """Real last/bid/ask for a pair from the live public feed."""
        kp = _kraken_pair(pair)
        result = self._public_get("Ticker", {"pair": kp})
        item = None
        for key, val in result.items():
            if isinstance(val, dict):
                item = val
                break
        if item is None:
            raise RuntimeError(f"no ticker data for {kp}")
        return {
            "pair": kp,
            "last": float((item.get("c") or [0])[0]),
            "bid": float((item.get("b") or [0])[0]),
            "ask": float((item.get("a") or [0])[0]),
            "volume_24h": float((item.get("v") or [0, 0])[-1]),
            "source": "kraken_public_ticker_live",
            "fetched_at": time.time(),
        }

    # ── private signing (identical to upstream kraken_client._kraken_sign) ─
    def _next_nonce(self) -> str:
        # Nanosecond-scale nonce SHARED with upstream's persisted nonce file.
        # Bug-hunt 2026-09-06: hive modules using aureon.exchanges.kraken_client
        # (ns nonces, persisted to NONCE_FILE) pushed Kraken's server-side
        # last-nonce to ~1.78e18; this adapter's µs nonces (~1.78e15) were then
        # permanently below it -> EAPI:Invalid nonce on every order. All
        # processes on this host must climb the SAME nonce ladder.
        with self._nonce_lock:
            try:
                from aureon.exchanges.kraken_client import NONCE_FILE
            except Exception:
                NONCE_FILE = os.path.join(os.path.dirname(__file__), ".kraken_nonce")
            current_ns = time.time_ns()
            last = 0
            try:
                if os.path.exists(NONCE_FILE):
                    with open(NONCE_FILE, "r", encoding="utf-8") as fh:
                        last = int(fh.read().strip() or 0)
            except Exception:
                last = 0
            floor = max(current_ns, self._last_nonce + 1, last + 1)
            self._last_nonce = floor
            try:
                with open(NONCE_FILE, "w", encoding="utf-8") as fh:
                    fh.write(str(floor))
            except Exception:
                pass
            return str(floor)

    def _sign(self, url_path: str, data: Dict[str, Any], api_secret: str) -> str:
        """Kraken signature: HMAC-SHA512(url_path + SHA256(nonce+postdata))
        keyed with base64-decoded secret. api_secret is a parameter so the
        caller's env read stays inside this module; never logged."""
        postdata = "".join([f"{k}={data[k]}&" for k in data]).rstrip("&")
        nonce = str(data.get("nonce", ""))
        sha256_hash = hashlib.sha256((nonce + postdata).encode()).digest()
        mac = hmac.new(base64.b64decode(api_secret), url_path.encode() + sha256_hash, hashlib.sha512)
        return base64.b64encode(mac.digest()).decode()

    def _private(self, path: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Signed private POST. Raises on missing keys — never fabricates."""
        key, secret = self._keys()
        if not key or not secret:
            raise RuntimeError("kraken private call without KRAKEN_API_KEY/KRAKEN_API_SECRET")
        import urllib.request as _ur

        priority = self._path_priority(path)
        # Writes (order placement) are fail-closed: if the budget keeps
        # deferring, the order is NOT sent. Account reads defer but proceed.
        self._budget_acquire(
            priority,
            is_trading=priority.name == "EXECUTION",
            write=priority.name == "EXECUTION",
            max_wait_s=15.0,
        )

        body = dict(data or {})
        body["nonce"] = self._next_nonce()
        postdata = urllib.parse.urlencode(body)
        sign = self._sign(path, body, secret)
        req = _ur.Request(
            self.base + path,
            data=postdata.encode(),
            headers={
                "API-Key": key,
                "API-Sign": sign,
                "User-Agent": "AureonKrakenAdapter/1.0",
            },
        )
        try:
            with _ur.urlopen(req, timeout=self.timeout) as resp:  # nosec B310 - signed exchange endpoint
                payload = json.loads(resp.read().decode("utf-8", errors="replace"))
        except urllib.error.HTTPError as exc:
            if exc.code == 429:
                self._budget_on_429(priority)
            raise
        if isinstance(payload, dict) and payload.get("error"):
            errors = payload["error"]
            if any("nonce" not in str(e).lower() and ("limit" in str(e).lower() or "throttle" in str(e).lower()) for e in (errors if isinstance(errors, list) else [errors])):
                self._budget_on_429(priority)
            raise RuntimeError(f"kraken private {path} error: {payload['error']}")
        result = payload.get("result", {}) if isinstance(payload, dict) else {}
        return result if isinstance(result, dict) else {}

    # ── authentication probe (read-only) ─────────────────────────────────
    def authenticate(self) -> Dict[str, Any]:
        """Validate keys against /0/private/Balance. Returns names/status only."""
        if not self.has_keys:
            return {"authenticated": False, "mode": "paper", "reason": "kraken_keys_absent"}
        try:
            balance = self._private("/0/private/Balance", {})
            return {
                "authenticated": True,
                "mode": "live_keyed",
                "balance_assets": sorted(balance.keys()),
                "checked_at": time.time(),
            }
        except RuntimeError as exc:
            msg = str(exc)
            # Kraken's own rejection proves the signed transport reached them.
            return {"authenticated": False, "mode": "live_keyed", "reason": msg[:200]}
        except Exception as exc:  # network etc.
            return {"authenticated": False, "mode": "live_keyed", "reason": f"{type(exc).__name__}: {exc}"[:200]}

    # ── account read (real balance, keyed only) ──────────────────────────
    def get_balance(self) -> Dict[str, float]:
        """Return non-zero balances from /0/private/Balance."""
        if not self.has_keys:
            return {}
        try:
            balance = self._private("/0/private/Balance", {})
            return {
                _canonical_asset(asset): float(amount)
                for asset, amount in balance.items()
                if float(amount) > 0
            }
        except Exception as exc:
            logger.warning("kraken balance fetch failed: %s", exc)
            return {}

    # ── order construction (real prices, both modes) ─────────────────────
    def build_order(self, pair: str, side: str, volume: float,
                    ordertype: str = "market", price: Optional[float] = None) -> Dict[str, Any]:
        """Compute the exact order object that would be sent (real ticker prices)."""
        side = side.lower().strip()
        if side not in {"buy", "sell"}:
            raise ValueError("side must be 'buy' or 'sell'")
        ordertype = ordertype.lower().strip()
        if ordertype not in {"market", "limit"}:
            raise ValueError("ordertype must be 'market' or 'limit'")
        volume = _finite(volume, positive=True)
        if volume is None:
            raise ValueError("volume must be a positive finite number")

        ticker = self.get_ticker(pair)
        if ordertype == "market":
            ref_price = ticker["ask"] if side == "buy" else ticker["bid"]
        else:
            ref_price = _finite(price, positive=True)
            if ref_price is None:
                raise ValueError("limit order requires a positive price")

        notional = volume * ref_price
        kp = _kraken_pair(pair)
        return {
            "pair": kp,
            "type": side,
            "ordertype": ordertype,
            "volume": f"{volume:.8f}".rstrip("0").rstrip("."),
            "price": f"{ref_price:.5f}".rstrip("0").rstrip(".") if ordertype == "limit" else None,
            "notional_quote": round(notional, 2),
            "reference_price": ref_price,
            "reference_source": ticker["source"],
            "reference_fetched_at": ticker["fetched_at"],
        }

    # ── journaling (paper entries labeled; secrets never written) ─────────
    def _journal(self, entry: Dict[str, Any]) -> None:
        JOURNAL_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(JOURNAL_PATH, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, sort_keys=True, default=str) + "\n")

    # ── order placement ───────────────────────────────────────────────────
    def place_order(self, pair: str, side: str, volume: float,
                    ordertype: str = "market", price: Optional[float] = None,
                    reason: str = "") -> Dict[str, Any]:
        """Route an order: paper journal when unkeyed/dry-run, signed AddOrder
        when keyed AND KRAKEN_LIVE_ENABLED=true (fail-closed otherwise)."""
        order = self.build_order(pair, side, volume, ordertype, price)
        if order["notional_quote"] < self.min_notional:
            raise ValueError(
                f"notional {order['notional_quote']} below kraken minimum {self.min_notional}"
            )

        if self.paper_mode:
            entry = {
                "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "mode": "paper_dry_run",
                "simulated": True,
                "exchange": "kraken",
                "order": order,
                "keys_present": self.has_keys,
                "dry_run_forced": os.getenv("KRAKEN_DRY_RUN", "").lower() == "true",
                "reason": reason or "paper_mode_no_keys",
            }
            self._journal(entry)
            logger.info("kraken PAPER order journaled: %s %s %s @ %s",
                        side, order["volume"], order["pair"], order["reference_price"])
            return {"status": "paper", "simulated": True, "journal": str(JOURNAL_PATH), "order": order}

        if not self.live_enabled:
            raise RuntimeError(
                "keys present but KRAKEN_LIVE_ENABLED is not 'true' — live spot "
                "firing stays fail-closed until the organism's auto-arm doctrine "
                "energizes it. Order NOT sent."
            )

        body: Dict[str, Any] = {
            "pair": order["pair"],
            "type": order["type"],
            "ordertype": order["ordertype"],
            "volume": order["volume"],
        }
        if order["price"]:
            body["price"] = order["price"]
        result = self._private("/0/private/AddOrder", body)
        txids = result.get("txid") or []
        receipt = {
            "status": "live",
            "simulated": False,
            "txids": txids,
            "descr": result.get("descr", {}),
            "order": order,
            "placed_at": time.time(),
        }
        logger.info("kraken LIVE order placed: %s %s %s (txids=%d)",
                    side, order["volume"], order["pair"], len(txids))
        return receipt

    def status(self) -> Dict[str, Any]:
        key, _secret = self._keys()
        return {
            "exchange": "kraken",
            "mode": "paper" if self.paper_mode else "live_keyed",
            "key_configured": bool(key),
            "secret_configured": bool(_secret),
            "dry_run_forced": os.getenv("KRAKEN_DRY_RUN", "").lower() == "true",
            "live_enabled": self.live_enabled,
            "journal": str(JOURNAL_PATH),
            "base": self.base,
        }


_ADAPTER: Optional[KrakenAdapter] = None
_ADAPTER_LOCK = threading.Lock()


def get_kraken_adapter() -> KrakenAdapter:
    global _ADAPTER
    with _ADAPTER_LOCK:
        if _ADAPTER is None:
            _ADAPTER = KrakenAdapter()
        return _ADAPTER


if __name__ == "__main__":
    print(json.dumps(get_kraken_adapter().status(), indent=2, sort_keys=True))
