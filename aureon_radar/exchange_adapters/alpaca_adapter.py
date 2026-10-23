"""Alpaca trading adapter — paper-first, organism-controlled.

Decree scope: the Aureon organism MUST be able to trade on Alpaca.
This adapter is the canonical Alpaca entry point for the organism:

- Paper-first: defaults to the Alpaca paper environment
  (https://paper-api.alpaca.markets). Live trading requires an explicit
  ``APCA_LIVE=true`` environment flag AND live keys.
- Credentials are read at CALL TIME from the environment, never at import
  time and never cached. Accepted names (official alpaca-py names first):
  ``APCA_API_KEY_ID`` / ``APCA_API_SECRET_KEY``, with repo-legacy fallback
  ``ALPACA_API_KEY`` / ``ALPACA_SECRET_KEY``.
- Keys absent -> honest dry-run: no order ever leaves the machine. Intended
  orders are journaled with REAL market prices pulled from labeled public
  feeds (Yahoo Finance for stocks/ETFs, Binance public API for crypto),
  each entry stamped ``mode: DRY_RUN`` and ``exchange: ALPACA_PAPER``.
- Secret values are never logged or returned; key NAMES only.

No fabricated data: every price carries its ``source`` and retrieval
timestamp; dry-run artifacts are labeled as simulations of intent, never
as fills.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ALPACA_LIVE_BASE = "https://api.alpaca.markets"
ALPACA_PAPER_BASE = "https://paper-api.alpaca.markets"

_KEY_ID_NAMES = ("APCA_API_KEY_ID", "ALPACA_API_KEY")
_KEY_SECRET_NAMES = ("APCA_API_SECRET_KEY", "ALPACA_SECRET_KEY", "ALPACA_API_SECRET")

_CRYPTO_BASES = {
    "BTC", "ETH", "LTC", "XRP", "SOL", "DOGE", "AVAX", "DOT", "LINK", "UNI",
    "AAVE", "BCH", "XLM", "ATOM", "ALGO", "MATIC", "SHIB", "ADA", "BNB",
    "ETC", "FIL", "NEAR", "APT", "OP", "ARB", "CRV", "MKR", "SNX", "COMP",
    "XTZ", "SUI", "SEI", "INJ", "TIA", "WIF", "BONK", "PEPE", "TRUMP",
}

_JOURNAL_DIR = Path(__file__).resolve().parent / "journals"
_DRY_RUN_JOURNAL = _JOURNAL_DIR / "alpaca_dry_run_journal.jsonl"

_MODULE_DIR = Path(__file__).resolve().parent
for _dotenv_candidate in (
    _MODULE_DIR.parent / ".env",
    Path.cwd() / ".env",
):
    if _dotenv_candidate.exists():
        try:
            from dotenv import load_dotenv

            load_dotenv(dotenv_path=str(_dotenv_candidate), override=False)
        except Exception:
            # dotenv missing or unreadable: os.environ still honored.
            pass
        break


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _is_crypto_symbol(symbol: str) -> bool:
    cleaned = str(symbol or "").strip().upper().replace("-", "/")
    base = cleaned.split("/")[0]
    return "/" in cleaned or base in _CRYPTO_BASES or cleaned.endswith("USD")


def _to_alpaca_symbol(symbol: str) -> str:
    """BTC / BTCUSD / BTC-USD -> BTC/USD ; AAPL -> AAPL."""
    cleaned = str(symbol or "").strip().upper().replace("-", "/").replace(" ", "")
    if "/" in cleaned:
        return cleaned
    for quote in ("USDT", "USDC", "USD"):
        if cleaned.endswith(quote) and len(cleaned) > len(quote):
            return f"{cleaned[:-len(quote)]}/{quote}"
    if cleaned in _CRYPTO_BASES:
        return f"{cleaned}/USD"
    return cleaned


def _to_binance_symbol(symbol: str) -> Optional[str]:
    cleaned = str(symbol or "").strip().upper().replace("-", "/").replace(" ", "")
    if "/" in cleaned:
        base, quote = cleaned.split("/", 1)
    elif cleaned.endswith("USDT"):
        return cleaned
    elif cleaned in _CRYPTO_BASES:
        base, quote = cleaned, "USDT"
    elif cleaned.endswith("USD"):
        base, quote = cleaned[:-3], "USDT"
    else:
        return None
    if quote in ("USD", "USDC"):
        quote = "USDT"
    return f"{base}{quote}" if base in _CRYPTO_BASES else None


def _yahoo_symbol(symbol: str) -> str:
    return str(symbol or "").strip().upper().replace("-", ".").replace("/", ".")


class AlpacaAdapter:
    """Paper-first Alpaca adapter with honest dry-run fallback.

    ``paper`` defaults to True unless the environment sets ``APCA_LIVE=true``
    (explicit owner opt-in for the live environment).
    """

    def __init__(self, paper: Optional[bool] = None):
        if paper is None:
            paper = os.getenv("APCA_LIVE", "false").strip().lower() != "true"
        self.paper = bool(paper)
        self.base_url = ALPACA_PAPER_BASE if self.paper else ALPACA_LIVE_BASE
        self._trading_client = None
        self._data_client = None

    # ------------------------------------------------------------------
    # Credentials (call-time, names only)
    # ------------------------------------------------------------------
    @staticmethod
    def _credentials() -> Tuple[Optional[str], Optional[str], Dict[str, str]]:
        key_id = next((os.getenv(n) for n in _KEY_ID_NAMES if os.getenv(n)), None)
        secret = next((os.getenv(n) for n in _KEY_SECRET_NAMES if os.getenv(n)), None)
        present = {
            "key_id_env": next((n for n in _KEY_ID_NAMES if os.getenv(n)), None),
            "secret_env": next((n for n in _KEY_SECRET_NAMES if os.getenv(n)), None),
        }
        return key_id, secret, present

    def _live_clients(self):
        """Build (or reuse) alpaca-py clients from call-time credentials."""
        key_id, secret, _ = self._credentials()
        if not key_id or not secret:
            return None
        from alpaca.data.historical import CryptoHistoricalDataClient, StockHistoricalDataClient
        from alpaca.trading.client import TradingClient

        if self._trading_client is None or self._data_client is None:
            self._trading_client = TradingClient(key_id, secret, paper=self.paper)
            self._data_client = (StockHistoricalDataClient(key_id, secret),
                                 CryptoHistoricalDataClient(key_id, secret))
        return self._trading_client, self._data_client[0], self._data_client[1]

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------
    def status(self) -> Dict[str, Any]:
        key_id, secret, names = self._credentials()
        keys_present = bool(key_id and secret)
        return {
            "exchange": "alpaca",
            "environment": "paper" if self.paper else "LIVE",
            "base_url": self.base_url,
            "keys_present": keys_present,
            "key_names": names,
            "mode": "paper_live" if keys_present else "dry_run",
            "dry_run": not keys_present,
            "live_opt_in_env": "APCA_LIVE",
            "note": (
                "dry_run: orders journaled locally with real public-feed prices; "
                "nothing is sent to Alpaca until APCA_API_KEY_ID/APCA_API_SECRET_KEY are set"
                if not keys_present
                else "paper keys active; orders route to Alpaca paper environment"
            ),
            "ts_utc": _utc_now(),
        }

    # ------------------------------------------------------------------
    # Market data — real prices from labeled sources
    # ------------------------------------------------------------------
    def get_quote(self, symbol: str) -> Dict[str, Any]:
        """Real last price for ``symbol``.

        With keys: Alpaca data API. Without keys: Binance public (crypto) or
        Yahoo Finance public (stocks/ETFs). Every result is source-labeled.
        """
        key_id, secret, _ = self._credentials()
        if key_id and secret:
            return self._quote_alpaca(symbol, key_id, secret)

        if _is_crypto_symbol(symbol):
            return self._quote_binance_public(symbol)
        return self._quote_yahoo_public(symbol)

    def _quote_alpaca(self, symbol: str, key_id: str, secret: str) -> Dict[str, Any]:
        from alpaca.data.historical import CryptoHistoricalDataClient, StockHistoricalDataClient
        from alpaca.data.requests import CryptoLatestQuoteRequest, StockLatestQuoteRequest

        alpaca_sym = _to_alpaca_symbol(symbol)
        try:
            if "/" in alpaca_sym:
                client = CryptoHistoricalDataClient(key_id, secret)
                req = CryptoLatestQuoteRequest(symbol_or_symbols=[alpaca_sym])
                quote = client.get_crypto_latest_quote(req)[alpaca_sym]
            else:
                client = StockHistoricalDataClient(key_id, secret)
                req = StockLatestQuoteRequest(symbol_or_symbols=[alpaca_sym])
                quote = client.get_stock_latest_quote(req)[alpaca_sym]
            return {
                "symbol": alpaca_sym,
                "bid": float(quote.bid_price),
                "ask": float(quote.ask_price),
                "last": (float(quote.bid_price) + float(quote.ask_price)) / 2.0,
                "source": "alpaca_data_api",
                "environment": "paper" if self.paper else "LIVE",
                "ts_utc": _utc_now(),
            }
        except Exception as exc:  # fall through to public feed, honestly labeled
            fallback = (self._quote_binance_public(symbol) if _is_crypto_symbol(symbol)
                        else self._quote_yahoo_public(symbol))
            fallback["alpaca_error"] = f"{type(exc).__name__}: {exc}"[:200]
            return fallback

    def _quote_binance_public(self, symbol: str) -> Dict[str, Any]:
        import requests

        binance_sym = _to_binance_symbol(symbol)
        if not binance_sym:
            raise ValueError(f"{symbol!r} is not a crypto pair this feed can quote")
        resp = requests.get(
            "https://api.binance.com/api/v3/ticker/price",
            params={"symbol": binance_sym},
            timeout=10,
        )
        resp.raise_for_status()
        payload = resp.json()
        price = float(payload["price"])
        return {
            "symbol": _to_alpaca_symbol(symbol),
            "binance_symbol": binance_sym,
            "bid": price,
            "ask": price,
            "last": price,
            "source": "binance_public",
            "environment": "public_feed",
            "ts_utc": _utc_now(),
        }

    def _quote_yahoo_public(self, symbol: str) -> Dict[str, Any]:
        import requests

        ysym = _yahoo_symbol(symbol)
        resp = requests.get(
            f"https://query1.finance.yahoo.com/v8/finance/chart/{ysym}",
            params={"interval": "1m", "range": "1d"},
            headers={"User-Agent": "Mozilla/5.0 (Aureon dry-run quote)"},
            timeout=10,
        )
        resp.raise_for_status()
        result = resp.json()["chart"]["result"][0]
        meta = result["meta"]
        closes = [c for c in (result.get("indicators", {}).get("quote", [{}])[0].get("close") or []) if c]
        if not closes:
            raise ValueError(f"Yahoo returned no price data for {ysym}")
        price = float(closes[-1])
        return {
            "symbol": meta.get("symbol", ysym),
            "bid": price,
            "ask": price,
            "last": price,
            "currency": meta.get("currency"),
            "exchange": meta.get("fullExchangeName"),
            "source": "yahoo_finance_public",
            "environment": "public_feed",
            "ts_utc": _utc_now(),
        }

    # ------------------------------------------------------------------
    # Orders — paper route, or honest dry-run journal
    # ------------------------------------------------------------------
    def submit_order(
        self,
        symbol: str,
        side: str,
        qty: Optional[float] = None,
        notional: Optional[float] = None,
        order_type: str = "market",
        time_in_force: str = "day",
    ) -> Dict[str, Any]:
        """Submit an order to Alpaca paper, or journal it in dry-run.

        Exactly one of ``qty`` / ``notional`` must be given. In dry-run the
        intended order is appended to ``journals/alpaca_dry_run_journal.jsonl``
        with a real public-feed price; nothing is transmitted.
        """
        if bool(qty) == bool(notional):
            raise ValueError("exactly one of qty or notional must be provided")
        side = str(side).strip().lower()
        if side not in {"buy", "sell"}:
            raise ValueError(f"side must be 'buy' or 'sell', got {side!r}")
        # Crypto symbols only accept IOC time-in-force at Alpaca; equities
        # accept DAY. Bug-hunt 2026-09-06 (live fire test): BTC/USD market
        # order with DAY was rejected 42210000 "invalid crypto time_in_force".
        if _is_crypto_symbol(symbol) and time_in_force.lower() == "day":
            time_in_force = "ioc"

        clients = self._live_clients()
        if clients is not None:
            trading_client, _, _ = clients
            from alpaca.trading.requests import MarketOrderRequest
            from alpaca.trading.enums import OrderSide, TimeInForce

            request = MarketOrderRequest(
                symbol=_to_alpaca_symbol(symbol),
                qty=qty,
                notional=notional,
                side=OrderSide.BUY if side == "buy" else OrderSide.SELL,
                time_in_force=getattr(TimeInForce, time_in_force.upper()),
            )
            order = trading_client.submit_order(order_data=request)
            return {
                "mode": "paper_live",
                "exchange": "ALPACA_PAPER" if self.paper else "ALPACA_LIVE",
                "order_id": str(order.id),
                "status": str(order.status),
                "submitted": True,
                "ts_utc": _utc_now(),
            }

        return self._journal_dry_run(
            symbol=symbol, side=side, qty=qty, notional=notional,
            order_type=order_type, time_in_force=time_in_force,
        )

    def _journal_dry_run(self, *, symbol, side, qty, notional, order_type, time_in_force) -> Dict[str, Any]:
        quote = self.get_quote(symbol)  # real price, labeled source
        entry = {
            "ts_utc": _utc_now(),
            "mode": "DRY_RUN",
            "simulated": True,
            "exchange": "ALPACA_PAPER",
            "would_submit_to": ALPACA_PAPER_BASE,
            "order_intent": {
                "symbol": _to_alpaca_symbol(symbol),
                "side": side,
                "qty": qty,
                "notional": notional,
                "type": order_type,
                "time_in_force": time_in_force,
            },
            "reference_price": quote,
            "blocking_reason": "APCA_API_KEY_ID/APCA_API_SECRET_KEY absent from environment",
            "note": "No order was sent anywhere. This is a labeled simulation of intent against a real market price.",
        }
        _JOURNAL_DIR.mkdir(parents=True, exist_ok=True)
        with open(_DRY_RUN_JOURNAL, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return entry

    # ------------------------------------------------------------------
    # Positions
    # ------------------------------------------------------------------
    def get_positions(self) -> List[Dict[str, Any]]:
        """Return open positions."""
        clients = self._live_clients()
        if clients is not None:
            positions = clients[0].get_all_positions()
            return [
                {
                    "symbol": str(p.symbol),
                    "qty": float(p.qty),
                    "qty_available": float(getattr(p, "qty_available", p.qty) or p.qty),
                    "avg_entry_price": float(p.avg_entry_price),
                    "current_price": float(getattr(p, "current_price", 0.0) or 0.0),
                    "market_value": float(getattr(p, "market_value", 0.0) or 0.0),
                    "unrealized_pl": float(getattr(p, "unrealized_pl", 0.0) or 0.0),
                    "unrealized_plpc": float(getattr(p, "unrealized_plpc", 0.0) or 0.0),
                    "side": "long" if float(p.qty) > 0 else "short",
                }
                for p in positions
            ]
        return []

    # ------------------------------------------------------------------
    # Account
    # ------------------------------------------------------------------
    def get_account(self) -> Dict[str, Any]:
        clients = self._live_clients()
        if clients is not None:
            acct = clients[0].get_account()
            return {
                "mode": "paper_live",
                "account_number": str(acct.account_number),
                "status": str(acct.status),
                "currency": str(acct.currency),
                "buying_power": float(acct.buying_power),
                "cash": float(acct.cash),
                "equity": float(acct.equity),
                "shorting_enabled": bool(getattr(acct, "shorting_enabled", False)),
                "ts_utc": _utc_now(),
            }
        return {
            "mode": "dry_run",
            "keys_present": False,
            "note": "account requires APCA_API_KEY_ID/APCA_API_SECRET_KEY",
            "ts_utc": _utc_now(),
        }
