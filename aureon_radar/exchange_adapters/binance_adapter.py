"""Binance exchange adapter — organism-controlled connectivity + order path.

Scope: BINANCE connectivity + adapter (decree 2026-09-06).

Config (aureon_radar/.env or process env):
    BINANCE_API_KEY      — spot API key (key NAME only, never logged)
    BINANCE_API_SECRET   — spot API secret
    BINANCE_TESTNET=true — target spot testnet (testnet.binance.vision)
                           (BINANCE_USE_TESTNET=true also honored, matching
                           binance_client.py convention)
    BINANCE_DRY_RUN=true — force paper mode even when keys exist

Modes:
    keys present, dry_run false -> LIVE-CAPABLE (orders still route through
        BinanceClient's receipt/latch machinery; nothing here force-fires)
    keys absent  -> DRY-RUN journaling: paper orders are built against REAL
        market prices fetched live from the selected endpoint, labeled
        DRY_RUN, and appended to the dry-run journal. No fabricated prices.

Connectivity is reported honestly. Earlier tonight import-time Binance
connects hung on TCP SYN from this UK host; that is why every network path
here is bounded by socket.setdefaulttimeout(30) and short requests timeouts.
If a probe fails, the failure is returned — never smoothed over.
"""

import hashlib
import hmac
import json
import logging
import os
import socket
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import requests

# Import-time guard: every socket created after this import is bounded.
# Load-bearing doctrine (master_launcher.py / unified_hub.py precedent).
socket.setdefaulttimeout(30)

logger = logging.getLogger("aureon.binance_adapter")

# Spot endpoints. Futures testnet (testnet.binancefuture.com) probed tonight
# as reachable too, but spot is the adapter's scope; futures stays a
# binance_ws_client / futures-client concern.
MAINNET_BASE = "https://api.binance.com"
TESTNET_BASE = "https://testnet.binance.vision"

_RADAR_ROOT = Path(__file__).resolve().parents[1]          # aureon_radar/
_ENV_PATH = _RADAR_ROOT / ".env"
_JOURNAL_DIR = _RADAR_ROOT / "state" / "exchange_adapters"
_DRY_RUN_JOURNAL = _JOURNAL_DIR / "binance_dry_run_journal.jsonl"

_REQUEST_TIMEOUT = 15  # seconds, per call


def _load_dotenv_file(path: Path) -> Dict[str, str]:
    """Minimal .env reader (KEY=VALUE lines); returns found keys, no values escape."""
    found: Dict[str, str] = {}
    try:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            if key:
                found[key] = value.strip().strip('"').strip("'")
    except OSError:
        pass
    return found


class BinanceAdapterConfig:
    """Resolved adapter configuration. Never exposes secret values."""

    def __init__(self, env: Optional[Dict[str, str]] = None):
        src = dict(env) if env is not None else {}
        # Precedence: process env > explicit env dict > .env file
        # (matching dotenv override=False doctrine for the file layer).
        file_env = _load_dotenv_file(_ENV_PATH)
        merged = {**file_env, **src, **{k: v for k, v in os.environ.items() if k in (
            "BINANCE_API_KEY", "BINANCE_API_SECRET", "BINANCE_KEY", "BINANCE_SECRET",
            "BINANCE_TESTNET", "BINANCE_USE_TESTNET", "BINANCE_DRY_RUN")}}

        self.api_key = merged.get("BINANCE_API_KEY") or merged.get("BINANCE_KEY") or ""
        self.api_secret = merged.get("BINANCE_API_SECRET") or merged.get("BINANCE_SECRET") or ""
        self.testnet = (merged.get("BINANCE_TESTNET") or merged.get("BINANCE_USE_TESTNET") or "false").strip().lower() == "true"
        self.has_keys = bool(self.api_key and self.api_secret)
        # Dry-run when keys absent is mandatory honesty, not a preference.
        self.dry_run = (merged.get("BINANCE_DRY_RUN", "false").strip().lower() == "true") or not self.has_keys

    @property
    def base_url(self) -> str:
        return TESTNET_BASE if self.testnet else MAINNET_BASE

    def public_summary(self) -> Dict[str, Any]:
        """Config facts safe to log — key NAMES and booleans only."""
        return {
            "env_file": str(_ENV_PATH),
            "base_url": self.base_url,
            "testnet": self.testnet,
            "has_api_key": bool(self.api_key),
            "has_api_secret": bool(self.api_secret),
            "key_env_names": ["BINANCE_API_KEY", "BINANCE_API_SECRET"],
            "dry_run": self.dry_run,
        }


class BinanceAdapter:
    """Connectivity probe + order path for Binance spot.

    Public endpoints are probed directly. Signed/account calls delegate to
    the proven aureon_radar.binance_client.BinanceClient (lazy import) so
    there is exactly one signing/receipt implementation in the organism.
    """

    def __init__(self, config: Optional[BinanceAdapterConfig] = None):
        # Explicit config (tests, probes) is pinned. Otherwise config resolves
        # at CALL time (property below), so keys energized in .env mid-uptime
        # are honored without a restart — the shadow wrappers check keys at
        # call time (env_has_keys), and the adapter must not contradict that
        # check with a config snapshot from process start (bug-hunt 2026-09-06:
        # env_has_keys passed but the stale cached config still refused the
        # live order as "live_order without keys").
        self._explicit_config = config

    @property
    def config(self) -> BinanceAdapterConfig:
        return self._explicit_config if self._explicit_config is not None \
            else BinanceAdapterConfig()

    # ------------------------------------------------------------------ #
    # Connectivity — honest, bounded, no smoothing
    # ------------------------------------------------------------------ #
    def connectivity(self, timeout: int = _REQUEST_TIMEOUT) -> Dict[str, Any]:
        base = self.config.base_url
        result: Dict[str, Any] = {
            "endpoint": base,
            "testnet": self.config.testnet,
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "reachable": False,
        }
        # 1) TCP+TLS+HTTP reachability via /api/v3/ping
        try:
            t0 = time.monotonic()
            r = requests.get(f"{base}/api/v3/ping", timeout=timeout)
            latency_ms = round((time.monotonic() - t0) * 1000, 1)
            result["ping_http_status"] = r.status_code
            result["ping_latency_ms"] = latency_ms
            result["ping_ok"] = r.status_code == 200
        except requests.RequestException as exc:
            result["ping_ok"] = False
            result["ping_error"] = f"{type(exc).__name__}: {exc}"
            return result
        # 2) Server time (proves a real Binance payload, not a captive page)
        try:
            r = requests.get(f"{base}/api/v3/time", timeout=timeout)
            payload = r.json()
            server_ms = int(payload.get("serverTime", 0))
            local_ms = int(time.time() * 1000)
            result["server_time_ok"] = server_ms > 0
            result["clock_offset_ms"] = local_ms - server_ms
        except (requests.RequestException, ValueError, TypeError) as exc:
            result["server_time_ok"] = False
            result["server_time_error"] = f"{type(exc).__name__}: {exc}"
            return result
        result["reachable"] = bool(result.get("ping_ok") and result.get("server_time_ok"))
        return result

    def get_price(self, symbol: str = "BTCUSDT", timeout: int = _REQUEST_TIMEOUT) -> Dict[str, Any]:
        """REAL market price from the selected endpoint. Never synthesized."""
        base = self.config.base_url
        symbol = symbol.upper().strip()
        try:
            r = requests.get(
                f"{base}/api/v3/ticker/price",
                params={"symbol": symbol},
                timeout=timeout,
            )
            payload = r.json()
            if r.status_code != 200 or "price" not in payload:
                return {"ok": False, "symbol": symbol, "error": f"HTTP {r.status_code}: {payload}"}
            return {
                "ok": True,
                "symbol": symbol,
                "price": float(payload["price"]),
                "source": base,
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            }
        except (requests.RequestException, ValueError) as exc:
            return {"ok": False, "symbol": symbol, "error": f"{type(exc).__name__}: {exc}"}

    # ------------------------------------------------------------------ #
    # Account
    # ------------------------------------------------------------------ #
    def get_balance(self) -> Dict[str, float]:
        """Return non-zero balances via the signed BinanceClient account."""
        if not self.config.has_keys:
            return {}
        try:
            from binance_client import BinanceClient  # lazy import

            client = BinanceClient()
            return client.get_balance()
        except Exception as exc:
            logger.warning("binance adapter balance fetch failed: %s", exc)
            return {}

    # ------------------------------------------------------------------ #
    # Order path
    # ------------------------------------------------------------------ #
    def place_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        order_type: str = "MARKET",
        dry_run: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """Create-order path.

        dry_run=None -> config decides (keys absent => always dry-run).
        Dry-run receipts use REAL fetched prices and are journaled with an
        explicit DRY_RUN label. Live path delegates to BinanceClient.
        """
        paper = self.config.dry_run if dry_run is None else bool(dry_run)
        symbol = symbol.upper().strip()
        side = side.upper().strip()
        order_type = order_type.upper().strip()

        if paper:
            return self._dry_run_order(symbol, side, quantity, order_type)
        return self._live_order(symbol, side, quantity, order_type)

    def _dry_run_order(self, symbol: str, side: str, quantity: float, order_type: str) -> Dict[str, Any]:
        quote = self.get_price(symbol)
        receipt: Dict[str, Any] = {
            "mode": "DRY_RUN",
            "dry_run": True,
            "exchange": "binance",
            "testnet": self.config.testnet,
            "endpoint": self.config.base_url,
            "symbol": symbol,
            "side": side,
            "order_type": order_type,
            "quantity": quantity,
            "client_order_id": f"dry_{uuid.uuid4().hex[:24]}",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "live_order_sent": False,
            "reason_no_live": "keys absent -> mandatory dry-run" if not self.config.has_keys
                              else "BINANCE_DRY_RUN=true",
        }
        if quote.get("ok"):
            receipt["ref_price"] = quote["price"]
            receipt["ref_price_source"] = quote["source"]
            receipt["ref_price_at"] = quote["fetched_at"]
            receipt["notional_estimate"] = round(quote["price"] * float(quantity), 8)
        else:
            # Honest: no price available -> the paper order is NOT priced.
            receipt["ref_price"] = None
            receipt["ref_price_error"] = quote.get("error")
        self._journal(receipt)
        return receipt

    def _live_order(self, symbol: str, side: str, quantity: float, order_type: str) -> Dict[str, Any]:
        if not self.config.has_keys:
            # Fail closed, honestly.
            receipt = self._dry_run_order(symbol, side, quantity, order_type)
            receipt["live_attempt_refused"] = True
            self._journal({"mode": "REFUSAL", "reason": "live_order without keys", "symbol": symbol})
            return receipt
        # Delegate to the proven client (signing, receipts, UK restrictions,
        # rate limiting, clock sync all live there — one implementation).
        os.environ.setdefault("BINANCE_DRY_RUN", "false")
        if self.config.testnet:
            os.environ["BINANCE_USE_TESTNET"] = "true"
        from binance_client import BinanceClient  # lazy: heavy import chain

        client = BinanceClient()
        result = client.place_market_order(symbol=symbol, side=side, quantity=quantity)
        return {"mode": "LIVE", "dry_run": False, "result": result}

    def place_order_by_notional(
        self,
        symbol: str,
        side: str,
        notional_usd: float,
        order_type: str = "MARKET",
        dry_run: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """Place an order sized by notional USD value.

        Computes quantity = notional / current price and delegates to
        place_order. Quantity is rounded to 6 decimal places (safe for BTC
        and most altcoins); callers should verify lot-size filters for
        very low-priced tokens.
        """
        quote = self.get_price(symbol)
        if not quote.get("ok"):
            return {
                "mode": "ERROR",
                "error": "price_unavailable",
                "symbol": symbol,
                "reason": quote.get("error"),
            }
        price = float(quote["price"])
        if price <= 0:
            return {"mode": "ERROR", "error": "invalid_price", "symbol": symbol, "price": price}
        quantity = round(notional_usd / price, 6)
        receipt = self.place_order(symbol, side, quantity, order_type, dry_run=dry_run)
        receipt["requested_notional"] = notional_usd
        receipt["computed_quantity"] = quantity
        receipt["reference_price"] = quote["price"]
        return receipt

    # ------------------------------------------------------------------ #
    # Journaling
    # ------------------------------------------------------------------ #
    def _journal(self, record: Dict[str, Any]) -> Path:
        _JOURNAL_DIR.mkdir(parents=True, exist_ok=True)
        line = json.dumps(record, default=str)
        with open(_DRY_RUN_JOURNAL, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
        logger.info("binance adapter journal: mode=%s symbol=%s", record.get("mode"), record.get("symbol"))
        return _DRY_RUN_JOURNAL

    @staticmethod
    def journal_path() -> Path:
        return _DRY_RUN_JOURNAL


def probe() -> Dict[str, Any]:
    """One-shot honest status: config facts + connectivity + a paper order."""
    adapter = BinanceAdapter()
    return {
        "config": adapter.config.public_summary(),
        "connectivity": adapter.connectivity(),
    }


if __name__ == "__main__":
    print(json.dumps(probe(), indent=2, default=str))
