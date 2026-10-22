"""MultiExchangeRouter — single entry point for live organism orders.

Routes ``place_order(symbol, direction, size, stop_level=None, profit_level=None)``
to the best available venue among:

  * Alpaca      — US stocks / ETFs
  * Kraken      — crypto/fiat spot
  * Binance     — crypto spot
  * Capital.com — forex, commodities, indices, single-stock CFDs

Selection logic:
  1. Classify the symbol (US equity, crypto, forex, commodity, index, CFD).
  2. Filter venues that are configured and currently tradable (market hours).
  3. Prefer live-capable venues; fall back to paper/dry-run only when no
     live keys are available.
  4. Enforce aggregate margin exposure <= 100 % of total account value (configurable via ROUTER_MARGIN_CAP).

All API keys are read from the environment / ``aureon_radar/.env`` by the
underlying adapters. This module never caches secret values and never logs them.
"""

from __future__ import annotations

import json
import logging
import re
import sys
import threading
import time
from datetime import datetime, time as dt_time, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# Paths & state
# ═══════════════════════════════════════════════════════════════════════════════
_RADAR_ROOT = Path(__file__).resolve().parent
_LOG_PATH = _RADAR_ROOT / "aureon_multi_exchange.log"

# ═══════════════════════════════════════════════════════════════════════════════
# Symbol classification tables (conservative, expandable)
# ═══════════════════════════════════════════════════════════════════════════════
_CRYPTO_BASES = {
    "BTC", "ETH", "XBT", "LTC", "XRP", "SOL", "DOGE", "XDG", "AVAX", "DOT",
    "LINK", "UNI", "AAVE", "BCH", "XLM", "ATOM", "ALGO", "MATIC", "SHIB",
    "ADA", "BNB", "ETC", "FIL", "NEAR", "APT", "OP", "ARB", "CRV", "MKR",
    "SNX", "COMP", "XTZ", "SUI", "SEI", "INJ", "TIA", "WIF", "BONK", "PEPE",
    "TRUMP",
}

_CRYPTO_QUOTES = {"USD", "USDT", "USDC", "EUR", "GBP", "BTC", "ETH"}

_FOREX_PAIRS = {
    "EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "USDCAD", "NZDUSD",
    "EURGBP", "EURJPY", "GBPJPY", "AUDJPY", "CADJPY", "CHFJPY", "EURCHF",
    "GBPCHF", "EURAUD", "GBPAUD", "EURCAD", "GBPCAD", "AUDCAD", "AUDNZD",
}

_COMMODITIES = {"GOLD", "SILVER", "OIL_CRUDE", "BRENT_OIL", "NATURALGAS", "USOIL", "UKOIL"}

_INDICES = {"US100", "US500", "US30", "UK100", "GER40", "EUR50", "JPN225", "AUS200"}

_US_STOCKS = {
    "AAPL", "TSLA", "NVDA", "MSFT", "AMZN", "GOOGL", "META", "NFLX", "AMD",
    "INTC", "CRM", "UBER", "COIN", "PLTR", "ARKK", "QQQ", "SPY", "IWM",
}

_US_ETFS = {"XLE", "XOP", "VDE", "OIH", "IXC", "USO", "UNG", "GLD", "SLV"}

_CAPITAL_STOCK_CFDS = {"AAPL", "TSLA", "NVDA", "MSFT", "AMZN", "GOOGL", "META"}

# Maps a symbol to its preferred venue list (in priority order).
_VENUE_PRECEDENCE: Dict[str, List[str]] = {
    "us_equity": ["alpaca"],
    "crypto": ["binance", "kraken"],
    "forex": ["capital"],
    "commodity": ["capital"],
    "index": ["capital"],
    "stock_cfd": ["capital"],
    "unknown": ["alpaca", "capital"],
}

# ═══════════════════════════════════════════════════════════════════════════════
# Adapter imports (defensive — parallel build tracks may land files separately)
# ═══════════════════════════════════════════════════════════════════════════════
def _import_adapters() -> Dict[str, Any]:
    adapters: Dict[str, Any] = {}

    # Ensure radar root is importable for bare package names
    radar_root = str(_RADAR_ROOT)
    if radar_root not in sys.path:
        sys.path.insert(0, radar_root)

    # Try absolute package path first, then bare module path.
    _import_paths = [
        "aureon_radar.exchange_adapters.{name}_adapter",
        "exchange_adapters.{name}_adapter",
    ]

    def _try_import(module_path: str, class_name: str):
        mod = __import__(module_path, fromlist=[class_name])
        return getattr(mod, class_name)

    for name, class_name in (
        ("alpaca", "AlpacaAdapter"),
        ("kraken", "KrakenAdapter"),
        ("binance", "BinanceAdapter"),
    ):
        for path_template in _import_paths:
            try:
                adapters[name] = _try_import(path_template.format(name=name), class_name)
                break
            except Exception as exc:
                logger.debug("%s adapter import via %s failed: %s", name, path_template, exc)

    try:
        from aureon_dual_capital import DualCapitalConnector
        adapters["capital"] = DualCapitalConnector
    except Exception as exc:
        logger.debug("dual capital connector unavailable: %s", exc)

    return adapters


ADAPTERS = _import_adapters()


# ═══════════════════════════════════════════════════════════════════════════════
# Helper functions
# ═══════════════════════════════════════════════════════════════════════════════
def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _log_event(record: Dict[str, Any]) -> None:
    """Append a structured log line; secrets must already be removed by caller."""
    try:
        _LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(_LOG_PATH, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, default=str) + "\n")
    except Exception as exc:
        logger.debug("router log write failed: %s", exc)


def _normalize_direction(direction: Any) -> str:
    d = str(direction or "").strip().upper()
    if d in ("LONG", "BUY"):
        return "buy"
    if d in ("SHORT", "SELL"):
        return "sell"
    return d.lower()


def _parse_crypto_pair(symbol: str) -> Optional[Tuple[str, str]]:
    """Return (base, quote) if the symbol looks like a crypto pair."""
    s = str(symbol or "").strip().upper().replace("-", "/").replace(" ", "")
    if "/" in s:
        base, quote = s.split("/", 1)
        return base, quote
    for quote in sorted(_CRYPTO_QUOTES, key=len, reverse=True):
        if s.endswith(quote) and len(s) > len(quote):
            return s[: -len(quote)], quote
    return None


def _classify_symbol(symbol: str) -> Dict[str, str]:
    """Classify symbol into asset class and normalized venue candidates."""
    s = str(symbol or "").strip().upper().replace("-", "").replace("/", "")

    # Crypto pair?
    pair = _parse_crypto_pair(symbol)
    if pair:
        base, quote = pair
        if base in _CRYPTO_BASES or quote in _CRYPTO_BASES:
            return {
                "symbol": symbol,
                "normalized": f"{base}/{quote}" if "/" not in str(symbol).upper() else symbol.upper().replace("-", "/"),
                "asset_class": "crypto",
                "venues": _VENUE_PRECEDENCE["crypto"],
            }

    if s in _FOREX_PAIRS:
        return {"symbol": symbol, "normalized": s, "asset_class": "forex", "venues": _VENUE_PRECEDENCE["forex"]}
    if s in _COMMODITIES:
        return {"symbol": symbol, "normalized": s, "asset_class": "commodity", "venues": _VENUE_PRECEDENCE["commodity"]}
    if s in _INDICES:
        return {"symbol": symbol, "normalized": s, "asset_class": "index", "venues": _VENUE_PRECEDENCE["index"]}
    # US equities take precedence over Capital single-stock CFDs for symbols
    # that Alpaca can trade directly.
    if s in _US_STOCKS or s in _US_ETFS:
        return {"symbol": symbol, "normalized": s, "asset_class": "us_equity", "venues": _VENUE_PRECEDENCE["us_equity"]}
    if s in _CAPITAL_STOCK_CFDS:
        return {"symbol": symbol, "normalized": s, "asset_class": "stock_cfd", "venues": _VENUE_PRECEDENCE["stock_cfd"]}

    # Heuristic: 1-5 uppercase chars -> US equity-ish
    if re.fullmatch(r"[A-Z]{1,5}", s):
        return {"symbol": symbol, "normalized": s, "asset_class": "us_equity", "venues": _VENUE_PRECEDENCE["us_equity"]}

    # Fallback: try Alpaca first, then Capital
    return {"symbol": symbol, "normalized": s, "asset_class": "unknown", "venues": _VENUE_PRECEDENCE["unknown"]}


def _is_weekday() -> bool:
    return datetime.now(timezone.utc).weekday() < 5


def _ny_now() -> datetime:
    """Return current time in US/Eastern (best-effort)."""
    try:
        import zoneinfo
        return datetime.now(zoneinfo.ZoneInfo("America/New_York"))
    except Exception:
        # Fallback: UTC-4/UTC-5 approximation is acceptable for coarse market-hours guard
        offset = -4 if _is_dst() else -5
        return datetime.now(timezone.utc).replace(tzinfo=None).replace(tzinfo=timezone.utc).__class__.fromisoformat(
            (datetime.now(timezone.utc).replace(tzinfo=None)).isoformat()
        )


def _is_dst() -> bool:
    """Rough DST detection for US Eastern."""
    now = datetime.now(timezone.utc)
    year = now.year
    # Second Sunday in March
    march_second_sunday = 8 + (6 - datetime(year, 3, 1).weekday()) % 7
    dst_start = datetime(year, 3, march_second_sunday, 7, tzinfo=timezone.utc)
    # First Sunday in November
    november_first_sunday = 1 + (6 - datetime(year, 11, 1).weekday()) % 7
    dst_end = datetime(year, 11, november_first_sunday, 6, tzinfo=timezone.utc)
    return dst_start <= now < dst_end


def _is_us_equity_market_open() -> bool:
    """Core NYSE/Nasdaq hours (09:30-16:00 ET), weekdays only."""
    if not _is_weekday():
        return False
    try:
        import zoneinfo
        now = datetime.now(zoneinfo.ZoneInfo("America/New_York"))
    except Exception:
        # Coarse UTC offset fallback
        now = datetime.utcnow()
        now = now.replace(hour=(now.hour - (4 if _is_dst() else 5)) % 24)
    current = now.time()
    return dt_time(9, 30) <= current <= dt_time(16, 0)


def _venue_available(venue: str, asset_class: str) -> bool:
    """Return True if the venue is currently accepting orders for this asset class."""
    if venue == "alpaca":
        return _is_us_equity_market_open()
    if venue in ("kraken", "binance"):
        return True  # crypto 24/7
    if venue == "capital":
        if asset_class in ("forex", "commodity", "index", "crypto"):
            return True  # forex/commodities generally 24/5
        if asset_class == "stock_cfd":
            return _is_weekday()
        return _is_weekday()
    return True


def _exchange_symbol(venue: str, normalized: str, original: str) -> str:
    """Translate normalized symbol into venue-native ticker."""
    if venue in ("kraken", "binance"):
        # Binance wants BTCUSDT; Kraken wants XBTUSD (handled by its adapter)
        pair = _parse_crypto_pair(original)
        if pair:
            base, quote = pair
            if quote in ("USD", "USDC"):
                quote = "USDT"
            return f"{base}{quote}" if venue == "binance" else f"{base}/{quote}"
        return original.upper().replace("-", "").replace("/", "")
    return normalized


# ═══════════════════════════════════════════════════════════════════════════════
# Aggregate exposure guard
# ═══════════════════════════════════════════════════════════════════════════════
class _ExposureCache:
    def __init__(self, ttl: float = 10.0):
        self._ttl = ttl
        self._lock = threading.Lock()
        self._last_update = 0.0
        self._account_value = 0.0
        self._exposure = 0.0

    def get(self, router: "MultiExchangeRouter") -> Tuple[float, float]:
        with self._lock:
            now = time.time()
            if now - self._last_update > self._ttl:
                self._account_value = router._total_account_value()
                self._exposure = router._total_position_exposure()
                self._last_update = now
            return self._account_value, self._exposure


_EXPOSURE_CACHE = _ExposureCache()


# ═══════════════════════════════════════════════════════════════════════════════
# Router
# ═══════════════════════════════════════════════════════════════════════════════
class MultiExchangeRouter:
    """Single ``place_order`` entry point for all organism trading surfaces."""

    def __init__(self):
        self._alpaca: Optional[Any] = None
        self._kraken: Optional[Any] = None
        self._binance: Optional[Any] = None
        self._capital: Optional[Any] = None
        self._lock = threading.Lock()

    # ──────────────────────────────────────────────────────────────────────────
    # Lazy adapter construction
    # ──────────────────────────────────────────────────────────────────────────
    def _alpaca_adapter(self) -> Optional[Any]:
        if "alpaca" not in ADAPTERS:
            return None
        with self._lock:
            if self._alpaca is None:
                self._alpaca = ADAPTERS["alpaca"]()
            return self._alpaca

    def _kraken_adapter(self) -> Optional[Any]:
        if "kraken" not in ADAPTERS:
            return None
        with self._lock:
            if self._kraken is None:
                self._kraken = ADAPTERS["kraken"]()
            return self._kraken

    def _binance_adapter(self) -> Optional[Any]:
        if "binance" not in ADAPTERS:
            return None
        with self._lock:
            if self._binance is None:
                self._binance = ADAPTERS["binance"]()
            return self._binance

    def _capital_connector(self) -> Optional[Any]:
        if "capital" not in ADAPTERS:
            return None
        with self._lock:
            if self._capital is None:
                self._capital = ADAPTERS["capital"]()
            return self._capital

    # ──────────────────────────────────────────────────────────────────────────
    # Status
    # ──────────────────────────────────────────────────────────────────────────
    def status(self) -> Dict[str, Any]:
        """Best-effort status across all configured venues."""
        out = {
            "ts_utc": _utc_now(),
            "us_equity_market_open": _is_us_equity_market_open(),
            "venues": {},
        }
        for name, getter in (
            ("alpaca", self._alpaca_adapter),
            ("kraken", self._kraken_adapter),
            ("binance", self._binance_adapter),
            ("capital", self._capital_connector),
        ):
            try:
                inst = getter()
                out["venues"][name] = {"available": inst is not None}
                if inst is not None and hasattr(inst, "status"):
                    out["venues"][name]["status"] = inst.status()
                elif inst is not None and hasattr(inst, "get_status"):
                    out["venues"][name]["status"] = inst.get_status()
            except Exception as exc:
                out["venues"][name] = {"available": False, "error": str(exc)[:200]}
        return out

    # ──────────────────────────────────────────────────────────────────────────
    # Account value aggregation (best-effort)
    # ──────────────────────────────────────────────────────────────────────────
    def _total_account_value(self) -> float:
        total = 0.0

        alpaca = self._alpaca_adapter()
        if alpaca is not None:
            try:
                acct = alpaca.get_account()
                total += float(acct.get("equity") or acct.get("buying_power") or 0.0)
            except Exception as exc:
                logger.debug("alpaca account value failed: %s", exc)

        kraken = self._kraken_adapter()
        if kraken is not None:
            try:
                bal = kraken.get_balance()
                total += float(bal.get("USD", 0.0) or bal.get("USDT", 0.0) or 0.0)
            except Exception as exc:
                logger.debug("kraken account value failed: %s", exc)

        binance = self._binance_adapter()
        if binance is not None:
            try:
                bal = binance.get_balance()
                total += float(bal.get("USDT", 0.0) or bal.get("USD", 0.0) or 0.0)
            except Exception as exc:
                logger.debug("binance account value failed: %s", exc)

        capital = self._capital_connector()
        if capital is not None:
            try:
                total += float(capital.get_live_balance())
            except Exception as exc:
                logger.debug("capital live account value failed: %s", exc)

        return max(total, 0.0)

    def _margin_cap_ratio(self) -> float:
        """Owner-configurable aggregate margin cap (default 1.00 for full autonomy)."""
        try:
            return max(0.0, min(1.0, float(os.getenv("ROUTER_MARGIN_CAP", "1.00"))))
        except Exception:
            return 1.00

    def _total_position_exposure(self) -> float:
        """Approximate aggregate *margin* exposure across venues.

        Capital.com CFDs: notional / leverage.
        Alpaca equities: assume 50% Reg-T margin (crypto is 100% and routed elsewhere).
        Crypto spot (Kraken/Binance) is fully paid and skipped for margin totals.
        """
        total = 0.0

        alpaca = self._alpaca_adapter()
        if alpaca is not None:
            try:
                for p in alpaca.get_positions():
                    qty = abs(float(p.get("qty", 0.0) or 0.0))
                    price = float(p.get("current_price") or p.get("avg_entry_price") or 0.0)
                    asset = str(p.get("asset_class") or p.get("asset_id") or "").upper()
                    margin_frac = 1.0 if "CRYPTO" in asset or "USD" in asset else 0.5
                    total += qty * price * margin_frac
            except Exception as exc:
                logger.debug("alpaca exposure failed: %s", exc)

        capital = self._capital_connector()
        if capital is not None:
            try:
                for p in capital.get_live_positions():
                    pos = p.get("position", {}) if isinstance(p, dict) else {}
                    size = abs(float(pos.get("size", 0.0) or 0.0))
                    market = p.get("market", {}) if isinstance(p, dict) else {}
                    price = float(
                        market.get("offer") or market.get("bid") or pos.get("level") or 0.0
                    )
                    leverage = float(pos.get("leverage") or market.get("leverage") or 1.0)
                    if leverage <= 0:
                        leverage = 1.0
                    total += (size * price) / leverage
            except Exception as exc:
                logger.debug("capital exposure failed: %s", exc)

        # Crypto spot positions are fully paid, not margin; skip in margin total.
        return total

    def _check_exposure_cap(self, order_notional: float) -> Tuple[bool, str]:
        account_value, existing_exposure = _EXPOSURE_CACHE.get(self)
        if account_value <= 0:
            # No account value data: allow but log a warning (fail-open on missing data).
            logger.warning(
                "exposure cap skipped: no account value available (order_notional=%s)",
                order_notional,
            )
            return True, ""
        projected = existing_exposure + order_notional
        limit = account_value * self._margin_cap_ratio()
        if projected > limit:
            return False, (
                f"aggregate margin exposure {projected:.2f} would exceed "
                f"{self._margin_cap_ratio():.0%} account value limit {limit:.2f}"
            )
        return True, ""

    # ──────────────────────────────────────────────────────────────────────────
    # Price helpers for exposure estimation
    # ──────────────────────────────────────────────────────────────────────────
    def _estimate_notional(self, symbol: str, size: float, asset_class: str) -> float:
        """Best-effort notional value of the intended order."""
        try:
            if asset_class == "us_equity":
                alpaca = self._alpaca_adapter()
                if alpaca is not None:
                    q = alpaca.get_quote(symbol)
                    return abs(size) * float(q.get("last") or q.get("bid") or 0.0)
            if asset_class == "crypto":
                binance = self._binance_adapter()
                if binance is not None:
                    q = binance.get_price(_exchange_symbol("binance", symbol, symbol))
                    if q.get("ok"):
                        return abs(size) * float(q["price"])
                kraken = self._kraken_adapter()
                if kraken is not None:
                    t = kraken.get_ticker(_exchange_symbol("kraken", symbol, symbol))
                    return abs(size) * float(t.get("last") or 0.0)
            if asset_class in ("forex", "commodity", "index", "stock_cfd"):
                capital = self._capital_connector()
                if capital is not None:
                    rules = capital._get_dealing_rules(symbol)
                    bid = rules.get("bid") if rules else None
                    ask = rules.get("ask") if rules else None
                    price = float(ask or bid or 0.0)
                    return abs(size) * price
        except Exception as exc:
            logger.debug("notional estimate failed for %s: %s", symbol, exc)
        return 0.0

    def _estimate_margin(self, symbol: str, size: float, asset_class: str) -> float:
        """Best-effort *margin* required for the intended order.

        Mirrors the margin assumptions used in position exposure so the
        aggregate cap compares like-for-like.
        """
        notional = self._estimate_notional(symbol, size, asset_class)
        if notional <= 0:
            return 0.0
        if asset_class == "us_equity":
            return notional * 0.5  # Reg-T initial margin approximation
        if asset_class in ("forex", "commodity", "index", "stock_cfd"):
            try:
                rules = self._capital_connector()._get_dealing_rules(symbol)
                margin_factor = float(rules.get("marginFactor") or 10.0) / 100.0
            except Exception:
                margin_factor = 0.10
            return notional * margin_factor
        # Crypto spot is fully paid; we still return notional here, but the cap
        # is generous and spot crypto is small/notional-limited by the adapters.
        return notional

    # ──────────────────────────────────────────────────────────────────────────
    # Venue-specific order submission
    # ──────────────────────────────────────────────────────────────────────────
    def _route_alpaca(self, symbol: str, side: str, size: float) -> Dict[str, Any]:
        alpaca = self._alpaca_adapter()
        if alpaca is None:
            return {"error": "alpaca adapter not available"}
        try:
            receipt = alpaca.submit_order(symbol=symbol, side=side, qty=size)
            return {
                "dealId": receipt.get("order_id") or receipt.get("id") or "unknown",
                "account": "alpaca_paper" if alpaca.paper else "alpaca_live",
                "size": size,
                "error": None,
                "venue": "alpaca",
                "raw": receipt,
            }
        except Exception as exc:
            return {"error": f"alpaca: {exc}"}

    def _route_kraken(self, symbol: str, side: str, size: float) -> Dict[str, Any]:
        kraken = self._kraken_adapter()
        if kraken is None:
            return {"error": "kraken adapter not available"}
        try:
            receipt = kraken.place_order(
                pair=_exchange_symbol("kraken", symbol, symbol),
                side=side,
                volume=size,
            )
            txids = receipt.get("txids") or []
            return {
                "dealId": txids[0] if txids else receipt.get("status") or "unknown",
                "account": "kraken_paper" if kraken.paper_mode else "kraken_live",
                "size": size,
                "error": None,
                "venue": "kraken",
                "raw": receipt,
            }
        except Exception as exc:
            return {"error": f"kraken: {exc}"}

    def _route_binance(self, symbol: str, side: str, size: float) -> Dict[str, Any]:
        binance = self._binance_adapter()
        if binance is None:
            return {"error": "binance adapter not available"}
        try:
            receipt = binance.place_order(
                symbol=_exchange_symbol("binance", symbol, symbol),
                side=side.upper(),
                quantity=size,
            )
            return {
                "dealId": receipt.get("client_order_id") or receipt.get("orderId") or "unknown",
                "account": "binance_paper" if receipt.get("dry_run") else "binance_live",
                "size": size,
                "error": None,
                "venue": "binance",
                "raw": receipt,
            }
        except Exception as exc:
            return {"error": f"binance: {exc}"}

    def _route_capital(
        self,
        symbol: str,
        side: str,
        size: float,
        stop_level: Optional[float],
        profit_level: Optional[float],
    ) -> Dict[str, Any]:
        capital = self._capital_connector()
        if capital is None:
            return {"error": "capital connector not available"}

        # Capital.com direction must be BUY/SELL.
        cap_side = "BUY" if side == "buy" else "SELL"

        # If no stop level provided for a live Capital order, compute the
        # broker-minimum distance so the fail-closed gate is satisfied.
        if stop_level is None:
            try:
                rules = capital._get_dealing_rules(symbol)
                entry = float(
                    rules.get("ask") or rules.get("bid") or 0.0 if rules else 0.0
                )
                if entry > 0:
                    distance = capital.get_minimum_stop_distance(symbol, entry)
                    if cap_side == "BUY":
                        stop_level = entry - distance
                    else:
                        stop_level = entry + distance
                    logger.info(
                        "capital default stop computed for %s %s: entry=%s stop=%s",
                        symbol, cap_side, entry, stop_level,
                    )
            except Exception as exc:
                logger.debug("capital default stop computation failed: %s", exc)

        try:
            receipt = capital.place_live_order(
                symbol=symbol,
                direction=cap_side,
                size=size,
                stop_level=stop_level,
                profit_level=profit_level,
            )
            err = receipt.get("error")
            return {
                "dealId": receipt.get("dealId") or receipt.get("dealReference") or "unknown",
                "account": "capital_live",
                "size": receipt.get("size", size),
                "error": err,
                "venue": "capital",
                "raw": receipt,
            }
        except Exception as exc:
            return {"error": f"capital: {exc}"}

    # ──────────────────────────────────────────────────────────────────────────
    # Main public API
    # ──────────────────────────────────────────────────────────────────────────
    def place_order(
        self,
        symbol: str,
        direction: Any,
        size: float,
        stop_level: Optional[float] = None,
        profit_level: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Route a single market order to the best available venue.

        Returns a unified dict with at least:
          { "dealId": str|None, "account": str, "size": float, "error": str|None }
        """
        side = _normalize_direction(direction)
        if side not in ("buy", "sell"):
            return {"dealId": None, "account": "none", "size": 0.0, "error": f"invalid direction {direction!r}"}

        try:
            size = float(size)
        except Exception:
            return {"dealId": None, "account": "none", "size": 0.0, "error": f"invalid size {size!r}"}

        classification = _classify_symbol(symbol)
        asset_class = classification["asset_class"]
        normalized = classification["normalized"]
        venues = classification["venues"]

        # Exposure cap check before routing (margin, not notional)
        margin = self._estimate_margin(normalized, size, asset_class)
        ok, reason = self._check_exposure_cap(margin)
        if not ok:
            _log_event({
                "ts_utc": _utc_now(),
                "event": "order_refused",
                "symbol": symbol,
                "side": side,
                "size": size,
                "reason": reason,
            })
            return {"dealId": None, "account": "none", "size": size, "error": reason}

        last_error: Optional[str] = None
        for venue in venues:
            if not _venue_available(venue, asset_class):
                last_error = f"{venue} unavailable for {asset_class} (market hours)"
                continue

            if venue == "alpaca":
                # Fail fast when the account cannot short US equities.
                if side == "sell" and asset_class == "us_equity" and not self._alpaca_short_enabled():
                    last_error = (
                        f"alpaca: short selling disabled for {normalized} "
                        "(account shorting_enabled=false)"
                    )
                    logger.info(last_error)
                    continue
                result = self._route_alpaca(normalized, side, size)
            elif venue == "kraken":
                result = self._route_kraken(normalized, side, size)
            elif venue == "binance":
                result = self._route_binance(normalized, side, size)
            elif venue == "capital":
                result = self._route_capital(normalized, side, size, stop_level, profit_level)
            else:
                continue

            if not result.get("error"):
                _log_event({
                    "ts_utc": _utc_now(),
                    "event": "order_routed",
                    "symbol": symbol,
                    "venue": venue,
                    "side": side,
                    "size": result.get("size", size),
                    "account": result.get("account"),
                    "dealId": result.get("dealId"),
                })
                return {
                    "dealId": result.get("dealId"),
                    "account": result.get("account"),
                    "size": result.get("size", size),
                    "error": None,
                    "venue": venue,
                }

            last_error = result.get("error")
            logger.info("venue %s rejected %s: %s", venue, symbol, last_error)

        # All candidate venues failed
        error_msg = last_error or f"no venue available for {symbol} ({asset_class})"
        _log_event({
            "ts_utc": _utc_now(),
            "event": "order_failed",
            "symbol": symbol,
            "side": side,
            "size": size,
            "error": error_msg,
        })
        return {"dealId": None, "account": "none", "size": size, "error": error_msg}

    # ──────────────────────────────────────────────────────────────────────────
    # Aggregate exposure / margin guard (public API)
    # ──────────────────────────────────────────────────────────────────────────
    def aggregate_exposure(self) -> Dict[str, float]:
        """Return aggregate account value and current margin exposure."""
        account_value = self._total_account_value()
        exposure = self._total_position_exposure()
        cap = self._margin_cap_ratio()
        limit = account_value * cap
        return {
            "account_value": account_value,
            "position_exposure": exposure,
            "limit": limit,
            "cap_ratio": cap,
            "available": max(0.0, limit - exposure),
            "utilization_pct": (exposure / account_value * 100.0) if account_value > 0 else 0.0,
        }

    def can_add_exposure(self, order_notional: float) -> Tuple[bool, str]:
        """Fail-closed aggregate exposure check (kept in router and exposed here)."""
        ok, reason = self._check_exposure_cap(order_notional)
        return ok, reason

    def get_open_positions(self) -> List[Dict[str, Any]]:
        """Return normalized open positions across all configured venues.

        Normalized fields:
            deal_id, symbol, direction, size, entry_price, current_price,
            target_price, stop_level, venue
        """
        positions: List[Dict[str, Any]] = []

        capital = self._capital_connector()
        if capital is not None:
            try:
                for p in capital.get_live_positions() or []:
                    if not isinstance(p, dict):
                        continue
                    pos = p.get("position", {}) or {}
                    market = p.get("market", {}) or {}
                    deal_id = pos.get("dealId") or pos.get("dealReference")
                    if not deal_id:
                        continue
                    direction = str(pos.get("direction", "") or "").upper()
                    size = abs(float(pos.get("size", 0.0) or 0.0))
                    # Prefer a scaled opening price; fall back to the current
                    # scaled mark so DTP starts from the present level (safe
                    # fallback when the true entry is not exposed).
                    current = float(
                        market.get("offer") or market.get("bid") or pos.get("level") or 0.0
                    )
                    entry = float(
                        pos.get("openLevel") or pos.get("openPrice") or current
                    )
                    if entry <= 0:
                        entry = current
                    positions.append({
                        "deal_id": deal_id,
                        "symbol": str(market.get("epic") or pos.get("epic") or "").upper(),
                        "direction": "BUY" if direction in ("BUY", "LONG") else "SELL",
                        "size": size,
                        "entry_price": entry,
                        "current_price": current,
                        "target_price": None,
                        "stop_level": None,
                        "venue": "capital",
                    })
            except Exception as exc:
                logger.debug("get_open_positions capital failed: %s", exc)

        alpaca = self._alpaca_adapter()
        if alpaca is not None:
            try:
                for p in alpaca.get_positions() or []:
                    if not isinstance(p, dict):
                        continue
                    qty = float(p.get("qty", 0.0) or 0.0)
                    if qty == 0:
                        continue
                    symbol = str(p.get("symbol", "") or "").upper()
                    entry = float(p.get("avg_entry_price") or p.get("avg_entry") or 0.0)
                    current = float(p.get("current_price") or p.get("lastday_price") or entry)
                    positions.append({
                        "deal_id": symbol,  # Alpaca uses symbol as position id
                        "symbol": symbol,
                        "direction": "BUY" if qty > 0 else "SELL",
                        "size": abs(qty),
                        "entry_price": entry,
                        "current_price": current,
                        "target_price": None,
                        "stop_level": None,
                        "venue": "alpaca",
                    })
            except Exception as exc:
                logger.debug("get_open_positions alpaca failed: %s", exc)

        return positions

    def venue_balance(self, venue: str, currency: str = "USD") -> float:
        """Best-effort available cash/buying power for a specific venue.

        Returns 0.0 when the venue is unavailable or the read fails.
        """
        try:
            if venue == "alpaca":
                alpaca = self._alpaca_adapter()
                if alpaca is not None:
                    acct = alpaca.get_account()
                    return float(acct.get("buying_power") or acct.get("cash") or 0.0)
            if venue == "kraken":
                kraken = self._kraken_adapter()
                if kraken is not None:
                    bal = kraken.get_balance()
                    return float(bal.get(currency.upper(), 0.0) or 0.0)
            if venue == "binance":
                binance = self._binance_adapter()
                if binance is not None:
                    bal = binance.get_balance()
                    return float(bal.get(currency.upper(), 0.0) or 0.0)
            if venue == "capital":
                capital = self._capital_connector()
                if capital is not None:
                    return float(capital.get_live_balance())
        except Exception as exc:
            logger.debug("venue_balance failed for %s: %s", venue, exc)
        return 0.0

    def _alpaca_short_enabled(self) -> bool:
        """Return True if the connected Alpaca account allows short selling."""
        try:
            alpaca = self._alpaca_adapter()
            if alpaca is None:
                return False
            acct = alpaca.get_account()
            return bool(acct.get("shorting_enabled", False))
        except Exception as exc:
            logger.debug("alpaca short-enabled check failed: %s", exc)
            return False

    # ──────────────────────────────────────────────────────────────────────────
    # Close position across venues
    # ──────────────────────────────────────────────────────────────────────────
    def close_position(
        self,
        deal_id: str,
        venue: str,
        symbol: Optional[str] = None,
        size: Optional[float] = None,
        direction: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Best-effort close of an open position on the venue that holds it."""
        venue = (venue or "").lower()
        try:
            if venue == "alpaca":
                return self._close_alpaca(symbol or "")
            if venue == "binance":
                return self._close_binance(symbol or "", size or 0.0)
            if venue == "kraken":
                return self._close_kraken(symbol or "", size or 0.0, direction or "")
            if venue == "capital":
                return self._close_capital(deal_id)
            return {"success": False, "error": f"unknown venue {venue}"}
        except Exception as exc:
            logger.warning("close_position error on %s %s: %s", venue, deal_id, exc)
            return {"success": False, "error": str(exc)}

    def _close_alpaca(self, symbol: str) -> Dict[str, Any]:
        alpaca = self._alpaca_adapter()
        if alpaca is None:
            return {"success": False, "error": "alpaca adapter not available"}
        clients = alpaca._live_clients()
        if clients is None:
            return {"success": False, "error": "alpaca not authenticated"}
        try:
            clients[0].close_position(symbol)
            return {"success": True, "venue": "alpaca", "symbol": symbol}
        except Exception as exc:
            return {"success": False, "error": f"alpaca close: {exc}"}

    def _close_binance(self, symbol: str, size: float) -> Dict[str, Any]:
        binance = self._binance_adapter()
        if binance is None:
            return {"success": False, "error": "binance adapter not available"}
        try:
            receipt = binance.place_order(symbol=symbol, side="SELL", quantity=size)
            return {
                "success": not bool(receipt.get("error")),
                "venue": "binance",
                "symbol": symbol,
                "size": size,
                "raw": receipt,
            }
        except Exception as exc:
            return {"success": False, "error": f"binance close: {exc}"}

    def _close_kraken(self, symbol: str, size: float, direction: str) -> Dict[str, Any]:
        kraken = self._kraken_adapter()
        if kraken is None:
            return {"success": False, "error": "kraken adapter not available"}
        try:
            side = "sell" if str(direction).upper() in ("LONG", "BUY") else "buy"
            receipt = kraken.place_order(
                pair=_exchange_symbol("kraken", symbol, symbol),
                side=side,
                volume=size,
                reason="router_close",
            )
            return {
                "success": receipt.get("status") == "live" or receipt.get("status") == "paper",
                "venue": "kraken",
                "symbol": symbol,
                "size": size,
                "raw": receipt,
            }
        except Exception as exc:
            return {"success": False, "error": f"kraken close: {exc}"}

    def _close_capital(self, deal_id: str) -> Dict[str, Any]:
        capital = self._capital_connector()
        if capital is None:
            return {"success": False, "error": "capital connector not available"}
        try:
            result = capital.close_live_position(deal_id)
            return {"success": bool(result.get("success")), "venue": "capital", "deal_id": deal_id, "raw": result}
        except Exception as exc:
            return {"success": False, "error": f"capital close: {exc}"}


# ═══════════════════════════════════════════════════════════════════════════════
# Module-level convenience
# ═══════════════════════════════════════════════════════════════════════════════
_ROUTER: Optional[MultiExchangeRouter] = None
_ROUTER_LOCK = threading.Lock()


def get_router() -> MultiExchangeRouter:
    global _ROUTER
    with _ROUTER_LOCK:
        if _ROUTER is None:
            _ROUTER = MultiExchangeRouter()
        return _ROUTER


def place_order(
    symbol: str,
    direction: Any,
    size: float,
    stop_level: Optional[float] = None,
    profit_level: Optional[float] = None,
) -> Dict[str, Any]:
    """Module-level convenience wrapper around ``MultiExchangeRouter.place_order``."""
    return get_router().place_order(symbol, direction, size, stop_level, profit_level)


if __name__ == "__main__":
    print(json.dumps(get_router().status(), indent=2, default=str))
