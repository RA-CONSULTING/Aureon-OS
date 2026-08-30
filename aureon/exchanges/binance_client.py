import os, time, hmac, hashlib, requests, json, logging, math, threading
from pathlib import Path
from decimal import Decimal, InvalidOperation, ROUND_DOWN
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:
    pass

try:
    from aureon.core.aureon_env import load_aureon_environment

    load_aureon_environment(Path(__file__).resolve().parents[2], override=False)
except Exception:
    pass
from typing import Dict, Any, Set, List, Optional

from aureon.governance.economic_boundary import (
    EconomicGovernanceBlocked,
    _claim_economic_transport_context,
    _economic_transport_body_digest,
)

# Rate limiting utilities (TokenBucket, TTLCache)
try:
    from aureon.core.rate_limiter import TokenBucket, TTLCache
except Exception:
    TokenBucket = None
    TTLCache = None

BINANCE_MAINNET = "https://api.binance.com"
BINANCE_TESTNET = "https://testnet.binance.vision"
_BINANCE_SIGNING_CONTROL_FIELDS = frozenset(
    {"recvWindow", "signature", "timestamp"}
)

# 🇬🇧 UK Binance Restrictions (FCA regulated)
# These are tokens/features restricted for UK retail accounts
UK_RESTRICTED_TOKENS = {
    # Derivatives/Leveraged tokens (banned for UK retail)
    "BTCDOWN", "BTCUP", "ETHDOWN", "ETHUP", "BNBDOWN", "BNBUP",
    "XRPDOWN", "XRPUP", "DOTDOWN", "DOTUP", "EOSDOWN", "EOSUP",
    "TRXDOWN", "TRXUP", "LINKDOWN", "LINKUP", "ADAUP", "ADADOWN",
    "SXPDOWN", "SXPUP", "UNIDOWN", "UNIUP", "FILDOWN", "FILUP",
    "AAVEDOWN", "AAVEUP", "SUSHIDOWN", "SUSHIUP", "1INCHDOWN", "1INCHUP",
    # Stock tokens (delisted for UK)
    "TSLA", "COIN", "AAPL", "MSFT", "GOOGL", "AMZN", "MSTR",
    # Some stablecoins have restrictions
    "BUSD",  # Deprecated
}

# Features not available for UK accounts
UK_RESTRICTED_FEATURES = {
    "margin",      # No margin trading
    "futures",     # No derivatives
    "options",     # No options
    "leveraged",   # No leveraged tokens
}

class BinanceClient:
    def __init__(self):
        self.init_error = ""
        self.last_error = ""
        # Support common env var aliases from TS/Node side as well
        self.api_key = os.getenv("BINANCE_API_KEY") or os.getenv("BINANCE_KEY") or ""
        self.api_secret = os.getenv("BINANCE_API_SECRET") or os.getenv("BINANCE_SECRET") or ""
        self.use_testnet = (os.getenv("BINANCE_USE_TESTNET") or os.getenv("BINANCE_TESTNET") or "false").lower() == "true"
        self.dry_run = os.getenv("BINANCE_DRY_RUN", "false").lower() == "true"
        
        # 🇬🇧 UK Mode - Enable restrictions for FCA-regulated accounts
        self.uk_mode = os.getenv("BINANCE_UK_MODE", "true").lower() == "true"
        
        # Only require API keys if NOT in dry-run mode
        if not self.dry_run and (not self.api_key or not self.api_secret):
            raise ValueError("Missing BINANCE_API_KEY or BINANCE_API_SECRET in environment")
        
        self.base = BINANCE_TESTNET if self.use_testnet else BINANCE_MAINNET
        self.session = requests.Session()
        
        # Configure HTTPAdapter with connection pooling and SSL/TLS stability improvements
        retry_strategy = Retry(
            total=3,
            status_forcelist=[429, 500, 502, 503, 504],
            # Order mutations are not transport-idempotent unless the caller
            # supplies and persists a client order id.  Never let urllib3
            # replay a POST behind the receipt/latch layer.
            allowed_methods=["GET"],
            backoff_factor=1
        )
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=10,
            pool_maxsize=10,
            pool_block=False
        )
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        
        if self.api_key:
            self.session.headers.update({"X-MBX-APIKEY": self.api_key})
        
        # Cache allowed pairs for UK mode
        self._allowed_pairs_cache: Set[str] = set()
        self._cache_timestamp: float = 0
        self._symbol_filters_cache: dict[str, dict[str, float]] = {}
        
        # 🇬🇧 Cache UK restricted symbols to skip known-bad symbols proactively
        self._uk_restricted_symbols_cache: Set[str] = set()
        self._uk_restriction_cache_timestamp: float = 0
        
        # Server time offset for clock sync (fixes Windows clock drift)
        self._time_offset_ms: int = 0
        self._time_sync_timestamp: float = 0
        # Construction stays inert.  The first signed request performs the
        # provider-clock sync; importing or instantiating this adapter must not
        # create an undeclared network request.

        # Token bucket rate limiter for Binance and request/quote caching
        try:
            rate = float(os.getenv('BINANCE_RATE_PER_SECOND', '0.2'))  # Even more conservative: 0.2 req/sec
        except Exception:
            rate = 0.2  # Very conservative default to avoid bans
        try:
            burst = float(os.getenv('BINANCE_BURST_CAPACITY', str(max(1, int(rate)))))
        except Exception:
            burst = max(1, rate)
        self._rate_limiter = TokenBucket(rate=rate, capacity=burst) if TokenBucket else None
        self._request_cache = TTLCache(default_ttl=float(os.getenv('BINANCE_EXCHANGE_CACHE_TTL', '1.0'))) if TTLCache else None
        self.max_retries = int(os.getenv('BINANCE_RETRY_COUNT', '2'))
        # Submission acknowledgements that have not been proven by a complete
        # terminal provider fill block duplicate submissions in this process.
        self._pending_orders: Dict[tuple[str, str, bool], Dict[str, Any]] = {}
        self._pending_conversions: Dict[tuple[str, str], Dict[str, Any]] = {}
        # A per-call opaque capability closes direct request-helper bypasses.
        # Each capability is bound to the exact query/body digests and is
        # removed before the session sees the mutation.
        self._economic_dispatch_lock = threading.RLock()
        self._economic_dispatches: dict[
            object,
            tuple[str, str, str, str],
        ] = {}

    @staticmethod
    def _norm(symbol: str) -> str:
        """Normalize symbol for Binance API: strip '/' separators.
        E.g. 'XRP/USDC' -> 'XRPUSDC', 'BTCUSDT' -> 'BTCUSDT'.
        """
        return symbol.replace('/', '') if symbol else symbol

    @staticmethod
    def _finite_number(value: Any, *, positive: bool = False) -> Optional[float]:
        """Parse a provider number without manufacturing a missing value."""
        try:
            parsed = float(value)
        except (TypeError, ValueError):
            return None
        if not math.isfinite(parsed):
            return None
        if positive and parsed <= 0:
            return None
        return parsed

    @staticmethod
    def _timestamp_seconds(value: Any) -> Optional[float]:
        parsed = BinanceClient._finite_number(value, positive=True)
        if parsed is None:
            return None
        if parsed > 10_000_000_000:
            parsed /= 1000.0
        return parsed

    @classmethod
    def _fresh_provider_timestamp(
        cls,
        value: Any,
        *,
        max_age_seconds: Optional[float] = None,
    ) -> Optional[float]:
        source_timestamp = cls._timestamp_seconds(value)
        if source_timestamp is None:
            return None
        now = time.time()
        max_age = max_age_seconds
        if max_age is None:
            try:
                max_age = float(os.getenv("BINANCE_RECEIPT_MAX_AGE_SECONDS", "300"))
            except (TypeError, ValueError):
                max_age = 300.0
        if source_timestamp > now + 5.0 or now - source_timestamp > max_age:
            return None
        return source_timestamp

    @staticmethod
    def _valid_provider_identifier(value: Any) -> Optional[str]:
        if value is None or isinstance(value, bool):
            return None
        identifier = str(value).strip()
        if identifier.lower() in {"", "none", "null", "unknown", "n/a", "0", "-1"}:
            return None
        return identifier

    @staticmethod
    def _valid_client_order_id(value: Any) -> Optional[str]:
        """Accept only the conservative Binance client-order-id subset."""
        identifier = BinanceClient._valid_provider_identifier(value)
        if identifier is None or len(identifier) > 36:
            return None
        allowed = frozenset(
            "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-"
        )
        if any(character not in allowed for character in identifier):
            return None
        return identifier

    @classmethod
    def _order_key(cls, symbol: str, side: str, margin: bool) -> tuple[str, str, bool]:
        return (cls._norm(symbol).upper(), str(side).strip().upper(), bool(margin))

    def _order_receipt_shell(
        self,
        *,
        symbol: str,
        side: str,
        order_id: Optional[str],
        status: str,
        data_status: str,
        truth_status: str,
        reason: str,
        submitted: bool,
        margin: bool,
        client_order_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        received_at = time.time()
        normalized_client_order_id = self._valid_client_order_id(client_order_id)
        return {
            "symbol": self._norm(symbol).upper(),
            "side": str(side).strip().upper(),
            "orderId": order_id,
            "provider_order_id": order_id,
            "clientOrderId": normalized_client_order_id,
            "provider_client_order_id": normalized_client_order_id,
            "status": status,
            "provider_status": None,
            "data_status": data_status,
            "truth_status": truth_status,
            "reason": reason,
            "submitted": bool(submitted),
            "submission_acknowledged": bool(order_id),
            "reconciliation_required": bool(submitted),
            "source_id": (
                f"binance:order:{order_id}"
                if order_id else (
                    f"binance:client_order:{normalized_client_order_id}"
                    if normalized_client_order_id else None
                )
            ),
            "source_timestamp": None,
            "provider_timestamp": None,
            "received_at": received_at,
            "receipt_id": None,
            "fills": [],
            "fill_receipt_complete": False,
            "eligible_for_action": False,
            "eligible_for_accounting": False,
            "eligible_for_learning": False,
            "generated_values": False,
            "action": False,
            "accounting": False,
            "learning": False,
            "margin": bool(margin),
            "exchange": "binance",
        }

    def _not_submitted_order_receipt(
        self,
        reason: str,
        *,
        symbol: str,
        side: str,
        margin: bool = False,
        **observed_request: Any,
    ) -> Dict[str, Any]:
        receipt = self._order_receipt_shell(
            symbol=symbol,
            side=side,
            order_id=None,
            status="not_submitted",
            data_status="not_submitted",
            truth_status="no_data",
            reason=reason,
            submitted=False,
            margin=margin,
        )
        receipt.update(observed_request)
        receipt["reconciliation_required"] = False
        return receipt

    def _pending_order_receipt(
        self,
        reason: str,
        *,
        symbol: str,
        side: str,
        order_id: Optional[str],
        margin: bool,
        provider_status: Optional[str] = None,
        readback_performed: bool = False,
        client_order_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        receipt = self._order_receipt_shell(
            symbol=symbol,
            side=side,
            order_id=order_id,
            status="pending_reconciliation",
            data_status="pending_reconciliation",
            truth_status="real_observed" if order_id else "no_data",
            reason=reason,
            submitted=True,
            margin=margin,
            client_order_id=client_order_id,
        )
        receipt["provider_status"] = provider_status
        receipt["readback_performed"] = bool(readback_performed)
        return receipt

    def _normalize_order_receipt(
        self,
        order: Any,
        *,
        symbol: str,
        side: str,
        margin: bool,
        expected_order_id: Optional[str] = None,
        expected_client_order_id: Optional[str] = None,
        now: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Normalize provider order evidence without creating fill or fee values."""
        expected_symbol = self._norm(symbol).upper()
        expected_side = str(side).strip().upper()
        if not isinstance(order, dict):
            return self._pending_order_receipt(
                "provider_submission_outcome_unproven",
                symbol=expected_symbol,
                side=expected_side,
                order_id=expected_order_id,
                margin=margin,
            )

        order_id = self._valid_provider_identifier(order.get("orderId"))
        observed_client_order_id = self._valid_client_order_id(
            order.get("clientOrderId")
        )
        provider_status = str(order.get("status") or "").strip().upper()
        observed_symbol = self._norm(str(order.get("symbol") or "")).upper()
        observed_side = str(order.get("side") or "").strip().upper()
        if order_id is None:
            return self._pending_order_receipt(
                "non_sentinel_provider_order_id_required",
                symbol=expected_symbol,
                side=expected_side,
                order_id=expected_order_id,
                margin=margin,
                provider_status=provider_status or None,
                client_order_id=expected_client_order_id,
            )
        if expected_order_id is not None and order_id != expected_order_id:
            return self._pending_order_receipt(
                "provider_order_id_mismatch",
                symbol=expected_symbol,
                side=expected_side,
                order_id=expected_order_id,
                margin=margin,
                provider_status=provider_status or None,
                client_order_id=expected_client_order_id,
            )
        if (
            expected_client_order_id is not None
            and observed_client_order_id != expected_client_order_id
        ):
            return self._pending_order_receipt(
                "provider_client_order_id_mismatch",
                symbol=expected_symbol,
                side=expected_side,
                order_id=order_id,
                margin=margin,
                provider_status=provider_status or None,
                client_order_id=expected_client_order_id,
            )
        if observed_symbol != expected_symbol or observed_side != expected_side:
            return self._pending_order_receipt(
                "provider_symbol_and_side_must_match_submission",
                symbol=expected_symbol,
                side=expected_side,
                order_id=order_id,
                margin=margin,
                provider_status=provider_status or None,
                client_order_id=expected_client_order_id,
            )

        nonterminal_statuses = {"NEW", "PENDING_NEW", "PARTIALLY_FILLED"}
        terminal_statuses = {"FILLED", "CANCELED", "CANCELLED", "EXPIRED", "REJECTED"}
        if provider_status in nonterminal_statuses or provider_status not in terminal_statuses:
            return self._pending_order_receipt(
                "terminal_provider_fill_receipt_required",
                symbol=expected_symbol,
                side=expected_side,
                order_id=order_id,
                margin=margin,
                provider_status=provider_status or None,
                client_order_id=expected_client_order_id,
            )

        source_timestamp_raw = (
            order.get("updateTime")
            or order.get("transactTime")
            or order.get("workingTime")
            or order.get("time")
        )
        source_timestamp = self._fresh_provider_timestamp(source_timestamp_raw, max_age_seconds=300.0)
        executed_qty = self._finite_number(order.get("executedQty"))
        if source_timestamp is None or executed_qty is None or executed_qty < 0:
            return self._pending_order_receipt(
                "fresh_provider_timestamp_and_executed_quantity_required",
                symbol=expected_symbol,
                side=expected_side,
                order_id=order_id,
                margin=margin,
                provider_status=provider_status,
                client_order_id=expected_client_order_id,
            )

        if provider_status != "FILLED" and executed_qty == 0:
            receipt = self._order_receipt_shell(
                symbol=expected_symbol,
                side=expected_side,
                order_id=order_id,
                status="CANCELED" if provider_status == "CANCELLED" else provider_status,
                data_status="live",
                truth_status="real_observed",
                reason="terminal_provider_receipt_without_fill",
                submitted=True,
                margin=margin,
                client_order_id=observed_client_order_id,
            )
            receipt.update({
                "provider_status": provider_status,
                "source_timestamp": source_timestamp,
                "provider_timestamp": source_timestamp,
                "reconciliation_required": False,
                "receipt_id": f"binance:order:{order_id}:{provider_status.lower()}",
            })
            return receipt

        if executed_qty <= 0:
            return self._pending_order_receipt(
                "positive_provider_fill_quantity_required",
                symbol=expected_symbol,
                side=expected_side,
                order_id=order_id,
                margin=margin,
                provider_status=provider_status,
                client_order_id=expected_client_order_id,
            )

        filled_notional = self._finite_number(
            order.get("cummulativeQuoteQty")
            if "cummulativeQuoteQty" in order
            else order.get("cumulativeQuoteQty"),
            positive=True,
        )
        raw_fills = order.get("fills")
        normalized_fills: List[Dict[str, Any]] = []
        if isinstance(raw_fills, list):
            for raw_fill in raw_fills:
                if not isinstance(raw_fill, dict):
                    normalized_fills = []
                    break
                fill_order_id_raw = raw_fill.get("orderId")
                fill_order_id = self._valid_provider_identifier(fill_order_id_raw) if fill_order_id_raw is not None else order_id
                trade_id = self._valid_provider_identifier(
                    raw_fill.get("tradeId") if "tradeId" in raw_fill else raw_fill.get("id")
                )
                qty = self._finite_number(raw_fill.get("qty"), positive=True)
                price = self._finite_number(raw_fill.get("price"), positive=True)
                commission = self._finite_number(raw_fill.get("commission"))
                commission_asset = str(raw_fill.get("commissionAsset") or "").strip().upper()
                fill_timestamp_raw = raw_fill.get("time") or raw_fill.get("transactTime") or source_timestamp_raw
                fill_timestamp = self._fresh_provider_timestamp(fill_timestamp_raw, max_age_seconds=300.0)
                if (
                    fill_order_id != order_id
                    or trade_id is None
                    or qty is None
                    or price is None
                    or commission is None
                    or commission < 0
                    or not commission_asset
                    or fill_timestamp is None
                ):
                    normalized_fills = []
                    break
                normalized_fills.append({
                    "orderId": order_id,
                    "tradeId": trade_id,
                    "qty": qty,
                    "price": price,
                    "commission": commission,
                    "commissionAsset": commission_asset,
                    "source_timestamp": fill_timestamp,
                    "provider_timestamp": fill_timestamp,
                    "truth_status": "real_observed",
                    "generated_values": False,
                })

        trade_ids = [str(fill["tradeId"]) for fill in normalized_fills]
        fee_assets = {str(fill["commissionAsset"]) for fill in normalized_fills}
        if not normalized_fills or len(trade_ids) != len(set(trade_ids)) or len(fee_assets) != 1:
            return self._pending_order_receipt(
                "complete_unique_provider_trades_and_single_fee_asset_required",
                symbol=expected_symbol,
                side=expected_side,
                order_id=order_id,
                margin=margin,
                provider_status=provider_status,
                client_order_id=expected_client_order_id,
            )
        if filled_notional is None:
            return self._pending_order_receipt(
                "provider_executed_quote_notional_required",
                symbol=expected_symbol,
                side=expected_side,
                order_id=order_id,
                margin=margin,
                provider_status=provider_status,
                client_order_id=expected_client_order_id,
            )

        trades_qty = sum(float(fill["qty"]) for fill in normalized_fills)
        trades_notional = sum(float(fill["qty"]) * float(fill["price"]) for fill in normalized_fills)
        qty_tolerance = max(1e-12, executed_qty * 1e-8)
        notional_tolerance = max(1e-8, filled_notional * 0.001)
        if (
            abs(trades_qty - executed_qty) > qty_tolerance
            or abs(trades_notional - filled_notional) > notional_tolerance
        ):
            return self._pending_order_receipt(
                "provider_order_and_trade_fill_totals_inconsistent",
                symbol=expected_symbol,
                side=expected_side,
                order_id=order_id,
                margin=margin,
                provider_status=provider_status,
                client_order_id=expected_client_order_id,
            )

        average_price = filled_notional / executed_qty
        fee_asset = next(iter(fee_assets))
        observed_fee = sum(float(fill["commission"]) for fill in normalized_fills)
        latest_source_timestamp = max(
            source_timestamp,
            *(float(fill["source_timestamp"]) for fill in normalized_fills),
        )
        received_at = time.time() if now is None else float(now)
        if latest_source_timestamp > received_at + 5.0:
            return self._pending_order_receipt(
                "provider_fill_timestamp_is_ahead_of_receipt_clock",
                symbol=expected_symbol,
                side=expected_side,
                order_id=order_id,
                margin=margin,
                provider_status=provider_status,
                client_order_id=expected_client_order_id,
            )
        digest_source = f"{order_id}|{expected_symbol}|{expected_side}|{','.join(trade_ids)}|{latest_source_timestamp}"
        receipt_id = "binance:fill:" + hashlib.sha256(digest_source.encode("utf-8")).hexdigest()
        normalized_status = "FILLED" if provider_status == "FILLED" else "PARTIALLY_FILLED"
        return {
            "symbol": expected_symbol,
            "side": expected_side,
            "orderId": order_id,
            "provider_order_id": order_id,
            "clientOrderId": observed_client_order_id,
            "provider_client_order_id": observed_client_order_id,
            "status": normalized_status,
            "provider_status": provider_status,
            "data_status": "live",
            "truth_status": "real_observed",
            "reason": "complete_fresh_terminal_provider_fill_receipt",
            "submitted": True,
            "submission_acknowledged": True,
            "reconciliation_required": False,
            "source_id": f"binance:order:{order_id}:trades",
            "source_timestamp": latest_source_timestamp,
            "provider_timestamp": latest_source_timestamp,
            "received_at": received_at,
            "receipt_id": receipt_id,
            "fills": normalized_fills,
            "executedQty": executed_qty,
            "filled_qty": executed_qty,
            "cummulativeQuoteQty": filled_notional,
            "filled_notional": filled_notional,
            "avgPrice": average_price,
            "avg_fill_price": average_price,
            "filled_avg_price": average_price,
            "fee": observed_fee,
            "fees": observed_fee,
            "fee_asset": fee_asset,
            "fee_currency": fee_asset,
            "fill_receipt_complete": True,
            "eligible_for_action": False,
            "eligible_for_accounting": True,
            "eligible_for_learning": True,
            "generated_values": False,
            "action": False,
            "accounting": True,
            "learning": True,
            "margin": bool(margin),
            "exchange": "binance",
            "provider_receipt_type": "BinanceFullOrderAndTrades",
        }

    def _reconcile_pending_order(self, key: tuple[str, str, bool]) -> Dict[str, Any]:
        """Perform no more than one provider readback for a latched submission."""
        pending = self._pending_orders.get(key)
        if not isinstance(pending, dict):
            return self._pending_order_receipt(
                "pending_submission_state_unavailable",
                symbol=key[0],
                side=key[1],
                order_id=None,
                margin=key[2],
            )
        order_id = self._valid_provider_identifier(pending.get("order_id"))
        client_order_id = self._valid_client_order_id(
            pending.get("client_order_id")
        )
        if order_id is None and client_order_id is None:
            return self._pending_order_receipt(
                "ambiguous_submission_requires_external_reconciliation",
                symbol=key[0],
                side=key[1],
                order_id=None,
                margin=key[2],
                client_order_id=None,
            )

        observed = dict(pending.get("order") or {})
        provider_status = str(observed.get("status") or "").strip().upper()
        executed_qty = self._finite_number(observed.get("executedQty"))
        needs_trades = (
            order_id is not None
            and provider_status
            in {"FILLED", "CANCELED", "CANCELLED", "EXPIRED", "REJECTED"}
            and executed_qty is not None
            and executed_qty > 0
        )
        if needs_trades:
            endpoint = "/sapi/v1/margin/myTrades" if key[2] else "/api/v3/myTrades"
            params: Dict[str, Any] = {"symbol": key[0], "orderId": order_id}
            if key[2]:
                params["isIsolated"] = pending.get("is_isolated", "FALSE")
            try:
                readback = self._signed_request("GET", endpoint, params)
            except Exception:
                return self._pending_order_receipt(
                    "provider_trade_readback_unavailable",
                    symbol=key[0],
                    side=key[1],
                    order_id=order_id,
                    margin=key[2],
                    provider_status=provider_status or None,
                    readback_performed=True,
                    client_order_id=client_order_id,
                )
            rows = readback if isinstance(readback, list) else readback.get("trades") if isinstance(readback, dict) else None
            matching_rows = [
                row for row in rows
                if isinstance(row, dict)
                and self._valid_provider_identifier(row.get("orderId")) == order_id
            ] if isinstance(rows, list) else []
            observed["fills"] = matching_rows
            trade_timestamps = [
                self._timestamp_seconds(row.get("time"))
                for row in matching_rows
                if isinstance(row, dict)
            ]
            valid_trade_timestamps = [stamp for stamp in trade_timestamps if stamp is not None]
            if valid_trade_timestamps:
                observed["updateTime"] = max(valid_trade_timestamps)
        else:
            endpoint = "/sapi/v1/margin/order" if key[2] else "/api/v3/order"
            params = {"symbol": key[0]}
            if order_id is not None:
                params["orderId"] = order_id
            else:
                params["origClientOrderId"] = client_order_id
            if key[2]:
                params["isIsolated"] = pending.get("is_isolated", "FALSE")
            try:
                readback = self._signed_request("GET", endpoint, params)
            except Exception:
                return self._pending_order_receipt(
                    "provider_order_readback_unavailable",
                    symbol=key[0],
                    side=key[1],
                    order_id=order_id,
                    margin=key[2],
                    provider_status=provider_status or None,
                    readback_performed=True,
                    client_order_id=client_order_id,
                )
            if isinstance(readback, dict):
                observed.update(readback)
                observed_order_id = self._valid_provider_identifier(
                    observed.get("orderId")
                )
                if order_id is None and observed_order_id is not None:
                    order_id = observed_order_id
                    pending["order_id"] = observed_order_id

        pending["order"] = observed
        normalized = self._normalize_order_receipt(
            observed,
            symbol=key[0],
            side=key[1],
            margin=key[2],
            expected_order_id=order_id,
            expected_client_order_id=client_order_id,
        )
        metadata = pending.get("metadata")
        if isinstance(metadata, dict):
            normalized.update(metadata)
        normalized["readback_performed"] = True
        if normalized.get("reconciliation_required") is False:
            self._pending_orders.pop(key, None)
        return normalized

    def get_order_status(
        self,
        order_id: Optional[str] = None,
        client_order_id: Optional[str] = None,
        *,
        symbol: Optional[str] = None,
        side: Optional[str] = None,
        margin: bool = False,
    ) -> Dict[str, Any]:
        """Reconcile one known order without permitting a duplicate submission."""
        expected = self._valid_provider_identifier(order_id)
        expected_client = self._valid_client_order_id(client_order_id)
        for key, pending in list(self._pending_orders.items()):
            if not isinstance(pending, dict):
                continue
            pending_order_id = self._valid_provider_identifier(
                pending.get("order_id")
            )
            pending_client_id = self._valid_client_order_id(
                pending.get("client_order_id")
            )
            if (
                (expected is not None and pending_order_id == expected)
                or (
                    expected_client is not None
                    and pending_client_id == expected_client
                )
            ):
                if self.dry_run:
                    return self._pending_order_receipt(
                        "readback_disabled_in_dry_run",
                        symbol=key[0],
                        side=key[1],
                        order_id=expected,
                        margin=key[2],
                        client_order_id=expected_client,
                    )
                return self._reconcile_pending_order(key)
        normalized_symbol = self._norm(symbol or "").upper()
        normalized_side = str(side or "").strip().upper()
        if (
            not self.dry_run
            and normalized_symbol
            and normalized_side in {"BUY", "SELL"}
            and (expected is not None or expected_client is not None)
        ):
            key = self._order_key(normalized_symbol, normalized_side, margin)
            self._pending_orders[key] = {
                "order_id": expected,
                "client_order_id": expected_client,
                "order": {},
                "params": {
                    "symbol": normalized_symbol,
                    "side": normalized_side,
                },
                "is_isolated": "FALSE",
            }
            return self._reconcile_pending_order(key)
        return self._order_receipt_shell(
            symbol="",
            side="",
            order_id=expected,
            status="no_data",
            data_status="no_data",
            truth_status="no_data",
            reason="known_latched_order_context_required_for_readback",
            submitted=expected is not None,
            margin=False,
            client_order_id=expected_client,
        )

    def get_order_with_fees(
        self,
        order_id: Optional[str] = None,
        client_order_id: Optional[str] = None,
        **context: Any,
    ) -> Dict[str, Any]:
        return self.get_order_status(
            order_id,
            client_order_id,
            **context,
        )
    
    def _sync_server_time(self) -> None:
        """Sync with Binance server time to handle local clock drift."""
        try:
            local_time_before = int(time.time() * 1000)
            r = self.session.get(f"{self.base}/api/v3/time", timeout=5)
            local_time_after = int(time.time() * 1000)
            
            if r.status_code == 200:
                server_time = r.json().get('serverTime', local_time_before)
                # Account for network latency (use midpoint)
                local_time_mid = (local_time_before + local_time_after) // 2
                self._time_offset_ms = server_time - local_time_mid
                self._time_sync_timestamp = time.time()
                
                if abs(self._time_offset_ms) > 1000:
                    print(f"   [Binance] Clock offset detected: {self._time_offset_ms}ms - auto-correcting")
        except Exception as e:
            self.last_error = f"time_sync_failed: {e}"
            print(f"   [Binance] Time sync failed: {e} - using local time")
            self._time_offset_ms = 0
    
    def _get_server_timestamp(self) -> int:
        """Get current timestamp adjusted for server time offset."""
        # Re-sync every 5 minutes to handle drift
        if time.time() - self._time_sync_timestamp > 300:
            self._sync_server_time()
        return int(time.time() * 1000) + self._time_offset_ms

    def _sign(self, params: Dict[str, Any]) -> str:
        query = "&".join(f"{k}={params[k]}" for k in params)
        signature = hmac.new(self.api_secret.encode(), query.encode(), hashlib.sha256).hexdigest()
        return signature

    def is_uk_restricted_symbol(self, symbol: str) -> bool:
        """Check if a symbol contains UK-restricted tokens."""
        if not self.uk_mode:
            return False
        symbol_upper = symbol.upper()
        for token in UK_RESTRICTED_TOKENS:
            if token in symbol_upper:
                return True
        return False

    def get_allowed_pairs_uk(self, force_refresh: bool = False) -> Set[str]:
        """Get list of pairs allowed for UK accounts based on Trade Groups.
        
        Caches results for 1 hour to avoid repeated API calls.
        """
        if not self.uk_mode:
            return set()  # No filtering needed
        
        # Return cache if fresh (< 1 hour)
        if not force_refresh and self._allowed_pairs_cache and (time.time() - self._cache_timestamp) < 3600:
            return self._allowed_pairs_cache
        
        try:
            # Get account trade groups
            account = self.account()
            permissions = account.get('permissions', [])
            trade_groups = {p for p in permissions if p.startswith('TRD_GRP_')}
            
            if not trade_groups:
                print("⚠️  UK Account: No TRD_GRP permissions found - trading may be restricted")
                return set()
            
            # Get exchange info and filter by trade groups
            info = self.exchange_info()
            symbols = info.get('symbols', [])
            
            allowed = set()
            for sym in symbols:
                if sym.get('status') != 'TRADING':
                    continue
                if not sym.get('isSpotTradingAllowed', False):
                    continue
                
                # Check if symbol's permission sets match our trade groups
                permission_sets = sym.get('permissionSets') or []
                for perm_set in permission_sets:
                    if trade_groups.intersection({p for p in perm_set if p.startswith('TRD_GRP_')}):
                        symbol_name = sym.get('symbol', '')
                        # Also filter out known restricted tokens
                        if not self.is_uk_restricted_symbol(symbol_name):
                            allowed.add(symbol_name)
                        break
            
            self._allowed_pairs_cache = allowed
            self._cache_timestamp = time.time()
            print(f"🇬🇧 UK Mode: {len(allowed)} tradeable pairs loaded")
            return allowed
            
        except Exception as e:
            print(f"⚠️  Failed to load UK allowed pairs: {e}")
            return set()

    def can_trade_symbol(self, symbol: str) -> tuple[bool, str]:
        """Check if a symbol can be traded (considering UK restrictions).
        
        Returns (can_trade: bool, reason: str)
        """
        if not self.uk_mode:
            return True, "OK"
        
        # Check static blacklist first
        if self.is_uk_restricted_symbol(symbol):
            return False, f"🇬🇧 UK Restricted: Contains banned token"
        
        # Check dynamic allowed list (based on account's trade groups)
        allowed = self.get_allowed_pairs_uk()
        if allowed and symbol.upper() not in allowed:
            return False, f"🇬🇧 UK Restricted: Not in account's permitted trade groups"
        
        return True, "OK"

    def _register_economic_dispatch(
        self,
        *,
        method: str,
        path: str,
        query_digest: str,
    ) -> object:
        dispatch = object()
        state = (
            method,
            path,
            query_digest,
            _economic_transport_body_digest({}),
        )
        with self._economic_dispatch_lock:
            self._economic_dispatches[dispatch] = state
        return dispatch

    def _discard_economic_dispatch(self, dispatch: object | None) -> None:
        if dispatch is None:
            return
        with self._economic_dispatch_lock:
            self._economic_dispatches.pop(dispatch, None)

    def _consume_economic_dispatch(
        self,
        dispatch: object | None,
        *,
        method: str,
        path: str,
        params: Dict[str, Any] | None,
        data: Dict[str, Any] | None,
    ) -> None:
        with self._economic_dispatch_lock:
            state = self._economic_dispatches.pop(dispatch, None)
        if state is None:
            raise EconomicGovernanceBlocked(
                "signed_binance_mutation_dispatch_capability_required"
            )
        if params is not None and not isinstance(params, dict):
            raise EconomicGovernanceBlocked(
                "exact_binance_mutation_query_and_body_required"
            )
        if data is not None and not isinstance(data, dict):
            raise EconomicGovernanceBlocked(
                "exact_binance_mutation_query_and_body_required"
            )
        economic_query = dict(params or {})
        for field in _BINANCE_SIGNING_CONTROL_FIELDS:
            economic_query.pop(field, None)
        try:
            observed = (
                method,
                path,
                _economic_transport_body_digest(economic_query),
                _economic_transport_body_digest(dict(data or {})),
            )
        except (TypeError, ValueError) as exc:
            raise EconomicGovernanceBlocked(
                "exact_binance_mutation_query_and_body_required"
            ) from exc
        if observed != state:
            raise EconomicGovernanceBlocked(
                "exact_binance_mutation_query_and_body_required"
            )

    def _do_request(
        self,
        method: str,
        path: str,
        params: Dict[str, Any] = None,
        data: Dict[str, Any] = None,
        timeout: int = 15,
        *,
        _economic_dispatch: object | None = None,
    ):
        """Internal request helper: respects rate limiter, handles 429 Retry-After and retries."""
        normalized_method = str(method).strip().upper()
        if normalized_method != "GET" or _economic_dispatch is not None:
            self._consume_economic_dispatch(
                _economic_dispatch,
                method=normalized_method,
                path=path,
                params=params,
                data=data,
            )
        url = f"{self.base}{path}"
        # Respect rate limiter
        if getattr(self, '_rate_limiter', None):
            try:
                self._rate_limiter.wait()
            except Exception:
                pass

        for attempt in range(self.max_retries + 1):
            # For signed POST requests, params go in query string, not body
            try:
                resp = self.session.request(
                    normalized_method,
                    url,
                    params=params,
                    data=data,
                    timeout=timeout,
                )
            except Exception as e:
                self.last_error = str(e)
                if "[WinError 10013]" in self.last_error:
                    self.init_error = "socket_blocked"
                raise
            if resp.status_code == 429:
                # Metric: API 429
                try:
                    from aureon.core.metrics import api_429_counter
                    api_429_counter.inc(1, exchange='binance', endpoint=path)
                except Exception:
                    pass

                retry_after = resp.headers.get('Retry-After')
                try:
                    wait_time = float(retry_after) if retry_after else 2 ** attempt
                except Exception:
                    wait_time = 2 ** attempt
                time.sleep(min(max(wait_time, 0.1), 10))
                if method.upper() == "GET" and attempt < self.max_retries:
                    continue
            if resp.status_code != 200:
                self.last_error = f"Binance error {resp.status_code}: {resp.text}"
                # 🇬🇧 UK Mode: Cache ONLY genuine "not permitted" errors
                # -2010 can mean "insufficient balance" OR "not permitted" — check message text
                if self.uk_mode and resp.status_code == 400:
                    try:
                        error_data = resp.json()
                        error_msg = str(error_data.get('msg', '')).lower()
                        if error_data.get('code') == -2010 and 'not permitted' in error_msg:
                            # Genuine UK restriction — cache it
                            symbol = params.get('symbol') if params else None
                            if symbol:
                                self._uk_restricted_symbols_cache.add(symbol)
                                self._uk_restriction_cache_timestamp = time.time()
                                print(f"   🇬🇧 Cached UK restricted symbol: {symbol}")
                        # Don't cache insufficient balance as UK restricted
                    except Exception:
                        pass
                raise RuntimeError(f"Binance error {resp.status_code}: {resp.text}")
            self.last_error = ""
            return resp.json()
        raise RuntimeError("Binance request failed after retries")

    def _signed_request(self, method: str, path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        normalized_method = str(method).strip().upper()
        dispatch: object | None = None
        if normalized_method != "GET":
            if self.dry_run:
                raise EconomicGovernanceBlocked(
                    "dry_run_binance_provider_mutation_forbidden"
                )
            if self.use_testnet:
                if self.base != BINANCE_TESTNET:
                    raise EconomicGovernanceBlocked(
                        "explicit_binance_testnet_endpoint_required"
                    )
                try:
                    body_digest = _economic_transport_body_digest(params)
                except (TypeError, ValueError) as exc:
                    raise EconomicGovernanceBlocked(
                        "exact_binance_mutation_query_required"
                    ) from exc
            else:
                body_digest = _claim_economic_transport_context(
                    method=normalized_method,
                    path=path,
                    body=params,
                )
                if self.base != BINANCE_MAINNET:
                    raise EconomicGovernanceBlocked(
                        "canonical_binance_live_endpoint_required"
                    )
            wire_params = dict(params)
            if _BINANCE_SIGNING_CONTROL_FIELDS.intersection(wire_params):
                raise EconomicGovernanceBlocked(
                    "binance_signing_control_fields_are_transport_owned"
                )
            dispatch = self._register_economic_dispatch(
                method=normalized_method,
                path=path,
                query_digest=body_digest,
            )
        else:
            wire_params = dict(params)
        try:
            wire_params["timestamp"] = self._get_server_timestamp()
            wire_params["recvWindow"] = 60000
            signature = self._sign(wire_params)
            wire_params["signature"] = signature
            return self._do_request(
                normalized_method,
                path,
                params=wire_params,
                _economic_dispatch=dispatch,
            )
        finally:
            self._discard_economic_dispatch(dispatch)

    def ping(self) -> bool:
        try:
            r = self.session.get(f"{self.base}/api/v3/ping", timeout=5)
            if r.status_code != 200:
                self.last_error = f"ping_failed_http_{r.status_code}"
            return r.status_code == 200
        except Exception as e:
            self.last_error = str(e)
            if "[WinError 10013]" in self.last_error:
                self.init_error = "socket_blocked"
            return False

    def diagnose_ready(self) -> Dict[str, Any]:
        network_ok = self.ping()
        account_ok = False
        account_error = ""
        if network_ok:
            try:
                self.account()
                account_ok = True
                self.init_error = ""
            except Exception as e:
                account_error = str(e)
                self.last_error = account_error
                self.init_error = "account_unavailable"
        elif not self.init_error:
            self.init_error = "network_unavailable"

        return {
            "dry_run": self.dry_run,
            "testnet": self.use_testnet,
            "uk_mode": self.uk_mode,
            "base": self.base,
            "network_ok": network_ok,
            "account_ok": account_ok,
            "margin_available": (not self.uk_mode) and self._margin_enabled(),
            "init_error": self.init_error,
            "last_error": self.last_error,
            "account_error": account_error,
        }

    def server_time(self) -> Dict[str, Any]:
        r = self.session.get(f"{self.base}/api/v3/time")
        return r.json()

    def exchange_info(self, symbol: str = None) -> Dict[str, Any]:
        params = {}
        key = f"exchange_info::{symbol or 'all'}"
        if self._request_cache:
            cached = self._request_cache.get(key)
            if cached is not None:
                return cached
        if symbol:
            params["symbol"] = symbol
        # Use _do_request to respect rate limits
        r = self._do_request("GET", "/api/v3/exchangeInfo", params=params)
        if self._request_cache:
            try:
                self._request_cache.set(key, r)
            except Exception:
                pass
        return r

    # Compatibility alias for callers expecting get_exchange_info
    def get_exchange_info(self, symbol: str = None) -> Dict[str, Any]:
        return self.exchange_info(symbol)

    def account(self) -> Dict[str, Any]:
        return self._signed_request("GET", "/api/v3/account", {})

    def api_restrictions(self) -> Dict[str, Any]:
        """Return the provider API-key restriction document."""
        return self._signed_request(
            "GET", "/sapi/v1/account/apiRestrictions", {},
        )

    def api_trading_status(self) -> Dict[str, Any]:
        """Return the provider account trading-lock document."""
        return self._signed_request(
            "GET", "/sapi/v1/account/apiTradingStatus", {},
        )

    def get_account_permission_receipt(self) -> Dict[str, Any]:
        """Return a sanitized, fail-closed receipt for bounded spot BUYs."""
        account_data: Any = None
        restriction_data: Any = None
        trading_status_data: Any = None
        provider_clock: Any = None
        try:
            account_data = self.account()
            restriction_data = self.api_restrictions()
            trading_status_data = self.api_trading_status()
            provider_clock = self.server_time()
        except Exception:
            # Provider errors can contain account metadata.  Do not copy them
            # into this receipt; an incomplete four-source read is NO_DATA.
            account_data = None
            restriction_data = None
            trading_status_data = None
            provider_clock = None
        received_at = time.time()

        account = account_data if isinstance(account_data, dict) else {}
        restrictions = (
            restriction_data if isinstance(restriction_data, dict) else {}
        )
        trading_status = (
            trading_status_data
            if isinstance(trading_status_data, dict) else {}
        )
        trading_status_body = trading_status.get("data")
        if not isinstance(trading_status_body, dict):
            trading_status_body = {}

        account_type = str(account.get("accountType") or "").strip().upper()
        raw_permissions = account.get("permissions")
        permissions_are_strings = (
            isinstance(raw_permissions, list)
            and bool(raw_permissions)
            and all(
                isinstance(value, str) and bool(value.strip())
                for value in raw_permissions
            )
        )
        permissions = (
            sorted({
                value.strip().upper()
                for value in raw_permissions
                if isinstance(value, str) and value.strip()
            })
            if isinstance(raw_permissions, list) else []
        )
        permissions_are_spot_only = (
            permissions_are_strings
            and "SPOT" in permissions
            and all(
                permission == "SPOT"
                or (
                    permission.startswith("TRD_GRP_")
                    and len(permission) > len("TRD_GRP_")
                )
                for permission in permissions
            )
        )

        raw_server_time = (
            provider_clock.get("serverTime")
            if isinstance(provider_clock, dict) else None
        )
        numeric_server_time = self._finite_number(
            raw_server_time, positive=True,
        )
        server_time = (
            int(numeric_server_time)
            if numeric_server_time is not None
            and numeric_server_time.is_integer()
            else None
        )
        source_timestamp = self._fresh_provider_timestamp(
            server_time, max_age_seconds=60.0,
        )

        safety_flags = {
            "account_type_is_spot": account_type == "SPOT",
            "account_permissions_are_spot_only": permissions_are_spot_only,
            "account_can_trade": account.get("canTrade") is True,
            "api_reading_enabled": (
                restrictions.get("enableReading") is True
            ),
            "api_spot_trading_enabled": (
                restrictions.get("enableSpotAndMarginTrading") is True
            ),
            "api_trading_unlocked": (
                trading_status_body.get("isLocked") is False
            ),
            "api_ip_restricted": restrictions.get("ipRestrict") is True,
            "api_withdrawals_disabled": (
                restrictions.get("enableWithdrawals") is False
            ),
            "api_internal_transfer_disabled": (
                restrictions.get("enableInternalTransfer") is False
            ),
            "api_universal_transfer_disabled": (
                restrictions.get("permitsUniversalTransfer") is False
            ),
            "api_margin_disabled": restrictions.get("enableMargin") is False,
            "api_futures_disabled": (
                restrictions.get("enableFutures") is False
            ),
            "api_options_disabled": (
                restrictions.get("enableVanillaOptions") is False
            ),
            "api_portfolio_margin_disabled": (
                restrictions.get("enablePortfolioMarginTrading") is False
            ),
            "client_is_mainnet": self.use_testnet is False,
            "client_is_live": self.dry_run is False,
            "uk_guard_enabled": self.uk_mode is True,
        }
        eligible = (
            source_timestamp is not None
            and all(value is True for value in safety_flags.values())
        )
        receipt_material = {
            "account_type": account_type,
            "permissions": permissions,
            "server_time": server_time,
            **safety_flags,
        }
        receipt_id = (
            "binance:account_permission:"
            + hashlib.sha256(json.dumps(
                receipt_material,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            ).encode("utf-8")).hexdigest()
            if eligible else None
        )
        return {
            "account_type": account_type,
            "permissions": permissions,
            "server_time": server_time,
            **safety_flags,
            "safe_for_bounded_spot_buy": eligible,
            "source_id": (
                "binance:/api/v3/account"
                "+/sapi/v1/account/apiRestrictions"
                "+/sapi/v1/account/apiTradingStatus"
                "+/api/v3/time"
            ),
            "source_timestamp": source_timestamp if eligible else None,
            "received_at": received_at,
            "receipt_id": receipt_id,
            "provider_receipt_type": (
                "Account+ApiRestrictions+ApiTradingStatus+Time"
            ),
            "truth_status": "real_provider" if eligible else "no_data",
            "data_status": "live" if eligible else "no_data",
            "reason": (
                "safe_spot_only_account_permissions_confirmed"
                if eligible
                else "complete_safe_spot_only_account_permission_receipt_required"
            ),
            "generated_values": False,
            "eligible_for_action": eligible,
            "eligible_for_accounting": False,
            "eligible_for_learning": False,
            "action": False,
            "accounting": False,
            "learning": False,
        }

    def get_asset_balance(self, asset: str) -> Optional[Dict[str, Any]]:
        """Return an exact, timestamped account balance receipt for one asset."""
        acct = self.account()
        try:
            provider_clock = self.server_time()
        except Exception:
            provider_clock = None
        received_at = time.time()
        if not isinstance(acct, dict) or not isinstance(acct.get("balances"), list):
            return None
        account_update_time = acct.get("updateTime")
        server_time = (
            provider_clock.get("serverTime")
            if isinstance(provider_clock, dict) else None
        )
        source_timestamp = self._fresh_provider_timestamp(
            server_time,
            max_age_seconds=60.0,
        )
        requested_asset = str(asset).upper()
        for bal in acct["balances"]:
            if not isinstance(bal, dict) or str(bal.get("asset", "")).upper() != requested_asset:
                continue
            free = self._finite_number(bal.get("free"))
            locked = self._finite_number(bal.get("locked"))
            if free is None or locked is None or free < 0 or locked < 0:
                return None
            eligible = source_timestamp is not None
            receipt_material = json.dumps(
                {
                    "asset": requested_asset,
                    "free": free,
                    "locked": locked,
                    "updateTime": account_update_time,
                    "serverTime": server_time,
                },
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
            receipt_id = (
                f"binance:account:{requested_asset}:"
                + hashlib.sha256(
                    receipt_material.encode("utf-8")
                ).hexdigest()
                if source_timestamp is not None
                else None
            )
            return {
                "asset": requested_asset,
                "free": free,
                "locked": locked,
                "total": free + locked,
                "account_update_time": account_update_time,
                "account_update_timestamp": self._timestamp_seconds(
                    account_update_time
                ),
                "server_time": server_time,
                "source_id": (
                    "binance:/api/v3/account+/api/v3/time"
                ),
                "source_timestamp": source_timestamp,
                "received_at": received_at,
                "receipt_id": receipt_id,
                "provider_receipt_type": "Account+Time",
                "truth_status": "real_provider" if eligible else "no_data",
                "data_status": "live" if eligible else "no_data",
                "generated_values": False,
                "eligible_for_action": eligible,
            }
        return None

    def get_free_balance(self, asset: str) -> float:
        receipt = self.get_asset_balance(asset)
        if not receipt or receipt.get("eligible_for_action") is not True:
            raise RuntimeError(f"NO_DATA: fresh Binance balance unavailable for {asset}")
        return float(receipt["free"])

    def get_balance(self) -> Dict[str, float]:
        """Compatibility: return total balances (free + locked) as {asset: amount}."""
        balances: Dict[str, float] = {}
        try:
            acct = self.account()
            if not isinstance(acct, dict) or self._fresh_provider_timestamp(acct.get("updateTime")) is None:
                return {}
            raw_balances = acct.get("balances")
            if not isinstance(raw_balances, list):
                return {}
            for bal in raw_balances:
                if not isinstance(bal, dict):
                    return {}
                asset = bal.get("asset")
                if not asset:
                    return {}
                free_amt = self._finite_number(bal.get("free"))
                locked_amt = self._finite_number(bal.get("locked"))
                if free_amt is None or locked_amt is None or free_amt < 0 or locked_amt < 0:
                    return {}
                total_amt = free_amt + locked_amt
                if total_amt > 0:
                    balances[asset] = total_amt
        except Exception:
            return {}
        return balances

    def _format_order_value(self, value: float | str | Decimal | None) -> str | None:
        if value is None:
            return None
        if isinstance(value, str):
            return value
        try:
            dec_value = Decimal(str(value))
        except (InvalidOperation, ValueError, TypeError) as exc:
            raise ValueError(f"Invalid order value: {value}") from exc
        
        # Use high precision to avoid rounding errors from default 'f' (6 decimals)
        formatted = "{:.20f}".format(dec_value)
        if '.' in formatted:
            formatted = formatted.rstrip('0').rstrip('.')
        return formatted

    def _place_market_order_receipt_gated(
        self,
        symbol: str,
        side: str,
        quantity: float | str | Decimal | None,
        quote_qty: float | str | Decimal | None,
        client_order_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        symbol = self._norm(symbol).upper()
        normalized_side = str(side or "").strip().upper()
        normalized_client_order_id = self._valid_client_order_id(
            client_order_id
        )
        if (
            client_order_id is not None
            and normalized_client_order_id is None
        ):
            return self._not_submitted_order_receipt(
                "valid_client_order_id_required",
                symbol=symbol,
                side=normalized_side,
                requested_client_order_id=client_order_id,
            )
        quantity_value = self._finite_number(quantity, positive=True) if quantity is not None else None
        quote_value = self._finite_number(quote_qty, positive=True) if quote_qty is not None else None
        if (
            not symbol
            or normalized_side not in {"BUY", "SELL"}
            or (quantity_value is None) == (quote_value is None)
            or (normalized_side == "SELL" and quote_value is not None)
        ):
            return self._not_submitted_order_receipt(
                "exactly_one_positive_quantity_is_required",
                symbol=symbol,
                side=normalized_side,
                requested_quantity=quantity,
                requested_quote_quantity=quote_qty,
            )

        key = self._order_key(symbol, normalized_side, False)
        if key in self._pending_orders:
            pending = self._pending_orders[key]
            pending_client_order_id = (
                self._valid_client_order_id(pending.get("client_order_id"))
                if isinstance(pending, dict) else None
            )
            if (
                normalized_client_order_id is not None
                and pending_client_order_id is not None
                and normalized_client_order_id != pending_client_order_id
            ):
                return self._pending_order_receipt(
                    "different_pending_client_order_id_blocks_submission",
                    symbol=symbol,
                    side=normalized_side,
                    order_id=self._valid_provider_identifier(
                        pending.get("order_id")
                    ) if isinstance(pending, dict) else None,
                    margin=False,
                    client_order_id=pending_client_order_id,
                )
            if self.dry_run:
                return self._pending_order_receipt(
                    "readback_disabled_in_dry_run",
                    symbol=symbol,
                    side=normalized_side,
                    order_id=self._valid_provider_identifier(pending.get("order_id")),
                    margin=False,
                    client_order_id=pending_client_order_id,
                )
            return self._reconcile_pending_order(key)

        if self.dry_run:
            return self._not_submitted_order_receipt(
                "dry_run",
                symbol=symbol,
                side=normalized_side,
                requested_quantity=quantity_value,
                requested_quote_quantity=quote_value,
            )

        if self.uk_mode:
            if symbol in self._uk_restricted_symbols_cache and normalized_side != "SELL":
                receipt = self._not_submitted_order_receipt(
                    "symbol_not_permitted_for_account",
                    symbol=symbol,
                    side=normalized_side,
                )
                receipt["uk_restricted"] = True
                return receipt
            if normalized_side != "SELL":
                can_trade, reason = self.can_trade_symbol(symbol)
                if not can_trade:
                    self._uk_restricted_symbols_cache.add(symbol)
                    self._uk_restriction_cache_timestamp = time.time()
                    receipt = self._not_submitted_order_receipt(
                        str(reason),
                        symbol=symbol,
                        side=normalized_side,
                    )
                    receipt["uk_restricted"] = True
                    return receipt

        if normalized_side == "SELL":
            base_asset = None
            for quote_asset in ("USDT", "USDC", "BUSD", "FDUSD", "TUSD", "USD", "EUR", "GBP", "BTC", "BNB", "ETH"):
                if symbol.endswith(quote_asset) and len(symbol) > len(quote_asset):
                    base_asset = symbol[:-len(quote_asset)]
                    break
            if not base_asset:
                return self._not_submitted_order_receipt(
                    "provider_symbol_metadata_required_for_balance_check",
                    symbol=symbol,
                    side=normalized_side,
                    requested_quantity=quantity_value,
                )
            balance_receipt = self.get_asset_balance(base_asset)
            actual_balance = self._finite_number(
                balance_receipt.get("free") if isinstance(balance_receipt, dict) else None
            )
            if (
                not isinstance(balance_receipt, dict)
                or balance_receipt.get("eligible_for_action") is not True
                or balance_receipt.get("truth_status") != "real_provider"
                or balance_receipt.get("generated_values") is not False
                or actual_balance is None
                or actual_balance < 0
            ):
                return self._not_submitted_order_receipt(
                    "fresh_provider_balance_receipt_required",
                    symbol=symbol,
                    side=normalized_side,
                    requested_quantity=quantity_value,
                )
            if quantity_value is None or actual_balance < quantity_value:
                return self._not_submitted_order_receipt(
                    "insufficient_observed_free_balance",
                    symbol=symbol,
                    side=normalized_side,
                    requested_quantity=quantity_value,
                    observed_free_balance=actual_balance,
                    balance_receipt_id=balance_receipt.get("receipt_id"),
                )

        try:
            filters = self.get_symbol_filters(symbol)
        except Exception:
            filters = None
        min_notional = self._finite_number(
            filters.get("min_notional") if isinstance(filters, dict) else None,
            positive=True,
        )
        if min_notional is None:
            return self._not_submitted_order_receipt(
                "provider_symbol_filters_and_minimum_notional_required",
                symbol=symbol,
                side=normalized_side,
            )

        params: Dict[str, Any] = {
            "symbol": symbol,
            "side": normalized_side,
            "type": "MARKET",
            "newOrderRespType": "FULL",
        }
        if normalized_client_order_id is not None:
            params["newClientOrderId"] = normalized_client_order_id
        if quantity_value is not None:
            try:
                adjusted_qty = self.adjust_quantity(symbol, quantity_value)
            except Exception:
                adjusted_qty = None
            if adjusted_qty is None or adjusted_qty <= 0:
                return self._not_submitted_order_receipt(
                    "provider_quantity_filter_rejected_request",
                    symbol=symbol,
                    side=normalized_side,
                    requested_quantity=quantity_value,
                )
            ticker = self.get_ticker(symbol)
            observed_price = self._finite_number(
                ticker.get("price") if isinstance(ticker, dict) else None,
                positive=True,
            )
            if (
                not isinstance(ticker, dict)
                or ticker.get("data_status") != "live"
                or ticker.get("truth_status") != "real_observed"
                or ticker.get("generated_values") is not False
                or observed_price is None
            ):
                return self._not_submitted_order_receipt(
                    "fresh_provider_quote_required_for_notional_check",
                    symbol=symbol,
                    side=normalized_side,
                    requested_quantity=quantity_value,
                )
            notional = adjusted_qty * observed_price
            if notional < min_notional:
                return self._not_submitted_order_receipt(
                    "order_below_provider_minimum_notional",
                    symbol=symbol,
                    side=normalized_side,
                    requested_quantity=quantity_value,
                    observed_notional=notional,
                    provider_minimum_notional=min_notional,
                    quote_receipt_id=ticker.get("receipt_id"),
                )
            params["quantity"] = self._format_order_value(adjusted_qty)
        else:
            try:
                adjusted_quote = self.adjust_quote_qty(symbol, quote_value)
            except Exception:
                adjusted_quote = None
            if adjusted_quote is None or adjusted_quote <= 0 or adjusted_quote < min_notional:
                return self._not_submitted_order_receipt(
                    "quote_quantity_below_provider_minimum_notional",
                    symbol=symbol,
                    side=normalized_side,
                    requested_quote_quantity=quote_value,
                    provider_minimum_notional=min_notional,
                )
            params["quoteOrderQty"] = self._format_order_value(adjusted_quote)

        try:
            response = self._signed_request("POST", "/api/v3/order", params)
        except EconomicGovernanceBlocked:
            raise
        except Exception:
            self._pending_orders[key] = {
                "order_id": None,
                "client_order_id": normalized_client_order_id,
                "order": {},
                "params": dict(params),
                "is_isolated": "FALSE",
            }
            receipt = self._pending_order_receipt(
                "ambiguous_submission_requires_external_reconciliation",
                symbol=symbol,
                side=normalized_side,
                order_id=None,
                margin=False,
                client_order_id=normalized_client_order_id,
            )
            # The POST left this process, but provider acceptance is unknown.
            # Preserve the reconciliation latch without inventing acceptance.
            receipt["submitted"] = None
            return receipt

        order_id = self._valid_provider_identifier(response.get("orderId")) if isinstance(response, dict) else None
        normalized = self._normalize_order_receipt(
            response,
            symbol=symbol,
            side=normalized_side,
            margin=False,
            expected_order_id=order_id,
            expected_client_order_id=normalized_client_order_id,
        )
        if normalized.get("reconciliation_required") is False:
            return normalized
        self._pending_orders[key] = {
            "order_id": order_id,
            "client_order_id": normalized_client_order_id,
            "order": dict(response) if isinstance(response, dict) else {},
            "params": dict(params),
            "is_isolated": "FALSE",
        }
        return normalized

    def place_market_order(
        self,
        symbol: str,
        side: str,
        quantity: float | str | Decimal | None = None,
        quote_qty: float | str | Decimal | None = None,
        client_order_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        return self._place_market_order_receipt_gated(
            symbol,
            side,
            quantity,
            quote_qty,
            client_order_id,
        )

    def get_symbol_filters(
        self,
        symbol: str,
        force_refresh: bool = False,
    ) -> Dict[str, Any]:
        symbol = symbol.upper()
        if symbol in self._symbol_filters_cache and not force_refresh:
            cached = self._symbol_filters_cache[symbol]
            if self._fresh_provider_timestamp(
                cached.get("source_timestamp"),
                max_age_seconds=300.0,
            ) is not None:
                return cached

        info = self.exchange_info(symbol=symbol)
        provider_clock = self.server_time()
        received_at = time.time()
        source_timestamp = self._fresh_provider_timestamp(
            provider_clock.get("serverTime")
            if isinstance(provider_clock, dict) else None,
            max_age_seconds=60.0,
        )
        if source_timestamp is None:
            raise RuntimeError(
                f"Fresh provider clock required for {symbol} filters"
            )
        entry = None
        if isinstance(info, dict):
            symbols = info.get('symbols', [])
            if symbols:
                entry = symbols[0]
        if entry is None:
            raise RuntimeError(f"Failed to load symbol info for {symbol}")

        filters = entry.get('filters')
        if not isinstance(filters, list):
            raise RuntimeError(f"Provider symbol filters unavailable for {symbol}")
        def _find(filter_type: str) -> Dict[str, Any]:
            for f in filters:
                if f.get('filterType') == filter_type:
                    return f
            return {}

        lot = _find('LOT_SIZE')
        market_lot = _find('MARKET_LOT_SIZE')
        min_notional = _find('MIN_NOTIONAL') or _find('NOTIONAL')

        step_size = self._finite_number(market_lot.get("stepSize"), positive=True) if market_lot else None
        if step_size is None:
            step_size = self._finite_number(lot.get("stepSize") if lot else None, positive=True)
        min_qty = self._finite_number(market_lot.get("minQty"), positive=True) if market_lot else None
        if min_qty is None:
            min_qty = self._finite_number(lot.get("minQty") if lot else None, positive=True)
        max_qty = self._finite_number(market_lot.get("maxQty"), positive=True) if market_lot else None
        if max_qty is None:
            max_qty = self._finite_number(lot.get("maxQty") if lot else None, positive=True)
        min_notional_val = self._finite_number((min_notional or {}).get("minNotional"), positive=True)
        if step_size is None or min_qty is None or max_qty is None or min_notional_val is None:
            raise RuntimeError(f"Complete provider quantity and notional filters required for {symbol}")

        base_precision_raw = entry.get("baseAssetPrecision")
        quote_precision_raw = entry.get("quoteAssetPrecision")
        if quote_precision_raw is None:
            quote_precision_raw = entry.get("quotePrecision")
        if base_precision_raw is None or quote_precision_raw is None:
            raise RuntimeError(f"Provider asset precision unavailable for {symbol}")
        base_precision = int(base_precision_raw)
        quote_precision = int(quote_precision_raw)
        if not 0 <= base_precision <= 20 or not 0 <= quote_precision <= 20:
            raise RuntimeError(f"Provider asset precision invalid for {symbol}")

        data = {
            'step_size': step_size,
            'min_qty': min_qty,
            'max_qty': max_qty,
            'min_notional': min_notional_val,
            'base_precision': base_precision,
            'quote_precision': quote_precision,
            'base_asset': entry.get('baseAsset'),
            'quote_asset': entry.get('quoteAsset'),
        }
        filter_material = json.dumps(
            {
                "symbol": symbol,
                "step_size": step_size,
                "min_qty": min_qty,
                "max_qty": max_qty,
                "min_notional": min_notional_val,
                "base_precision": base_precision,
                "quote_precision": quote_precision,
                "base_asset": entry.get("baseAsset"),
                "quote_asset": entry.get("quoteAsset"),
                "source_timestamp": source_timestamp,
            },
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        data.update({
            "source_id": "binance:/api/v3/exchangeInfo+/api/v3/time",
            "source_timestamp": source_timestamp,
            "received_at": received_at,
            "receipt_id": "binance:filters:" + hashlib.sha256(
                filter_material.encode("utf-8")
            ).hexdigest(),
            "provider_receipt_type": "ExchangeInfo+Time",
            "truth_status": "real_observed",
            "data_status": "live",
            "generated_values": False,
            "eligible_for_action": True,
            "action": False,
            "accounting": False,
            "learning": False,
        })
        self._symbol_filters_cache[symbol] = data
        return data

    def get_trade_fee_receipt(self, symbol: str) -> Dict[str, Any]:
        """Return exact account-specific spot fee rates plus provider time."""
        normalized_symbol = self._norm(symbol).upper()
        received_at = time.time()
        try:
            raw = self._signed_request(
                "GET",
                "/sapi/v1/asset/tradeFee",
                {"symbol": normalized_symbol},
            )
            provider_clock = self.server_time()
        except Exception:
            raw = None
            provider_clock = None
        rows = (
            raw
            if isinstance(raw, list)
            else raw.get("tradeFee")
            if isinstance(raw, dict)
            else None
        )
        matching = [
            row for row in rows
            if isinstance(row, dict)
            and self._norm(str(row.get("symbol") or "")).upper()
            == normalized_symbol
        ] if isinstance(rows, list) else []
        source_timestamp = self._fresh_provider_timestamp(
            provider_clock.get("serverTime")
            if isinstance(provider_clock, dict) else None,
            max_age_seconds=60.0,
        )
        if len(matching) != 1 or source_timestamp is None:
            return {
                "symbol": normalized_symbol,
                "data_status": "no_data",
                "truth_status": "no_data",
                "generated_values": False,
                "eligible_for_action": False,
                "source_timestamp": None,
                "received_at": received_at,
                "receipt_id": None,
                "reason": "complete_account_trade_fee_and_provider_time_required",
            }
        row = matching[0]
        maker = self._finite_number(row.get("makerCommission"))
        taker = self._finite_number(row.get("takerCommission"))
        if (
            maker is None
            or taker is None
            or maker < 0
            or taker < 0
            or maker >= 1
            or taker >= 1
        ):
            return {
                "symbol": normalized_symbol,
                "data_status": "no_data",
                "truth_status": "no_data",
                "generated_values": False,
                "eligible_for_action": False,
                "source_timestamp": None,
                "received_at": received_at,
                "receipt_id": None,
                "reason": "finite_provider_fee_rates_required",
            }
        material = json.dumps(
            {
                "symbol": normalized_symbol,
                "maker_commission": maker,
                "taker_commission": taker,
                "source_timestamp": source_timestamp,
            },
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        return {
            "symbol": normalized_symbol,
            "maker_commission": maker,
            "taker_commission": taker,
            "fee_currency_policy": "provider_fill_determines_asset",
            "source_id": (
                "binance:/sapi/v1/asset/tradeFee+/api/v3/time"
            ),
            "source_timestamp": source_timestamp,
            "received_at": received_at,
            "receipt_id": "binance:trade_fee:" + hashlib.sha256(
                material.encode("utf-8")
            ).hexdigest(),
            "provider_receipt_type": "TradeFee+Time",
            "truth_status": "real_provider",
            "data_status": "live",
            "generated_values": False,
            "eligible_for_action": True,
            "action": False,
            "accounting": False,
            "learning": False,
        }

    def adjust_quantity(self, symbol: str, quantity: float) -> float:
        filters = self.get_symbol_filters(symbol)
        qty_dec = Decimal(str(quantity))
        step_value = self._finite_number(filters.get("step_size"), positive=True)
        min_qty_value = self._finite_number(filters.get("min_qty"), positive=True)
        max_qty_value = self._finite_number(filters.get("max_qty"), positive=True)
        if step_value is None or min_qty_value is None or max_qty_value is None:
            raise RuntimeError(f"Complete provider quantity filters required for {symbol}")
        step = Decimal(str(step_value))
        qty_dec = (qty_dec // step) * step

        if filters.get("base_precision") is None:
            raise RuntimeError(f"Provider base precision unavailable for {symbol}")
        precision = int(filters["base_precision"])
        try:
            scale = Decimal(1).scaleb(-precision)
            qty_dec = qty_dec.quantize(scale, rounding=ROUND_DOWN)
        except (InvalidOperation, ValueError):
            pass

        min_qty = Decimal(str(min_qty_value))
        if qty_dec < min_qty:
            return 0.0

        max_qty = Decimal(str(max_qty_value))
        if qty_dec > max_qty:
            qty_dec = max_qty

        return float(qty_dec)

    def adjust_quote_qty(self, symbol: str, quote_qty: float) -> float:
        """Adjust quoteOrderQty to match the symbol's quote precision for Binance."""
        filters = self.get_symbol_filters(symbol)
        if filters.get("quote_precision") is None:
            raise RuntimeError(f"Provider quote precision unavailable for {symbol}")
        precision = int(filters["quote_precision"])
        if not 0 <= precision <= 20:
            raise RuntimeError(f"Provider quote precision invalid for {symbol}")
        qty_dec = Decimal(str(quote_qty))
        scale = Decimal(1).scaleb(-precision)
        qty_dec = qty_dec.quantize(scale, rounding=ROUND_DOWN)
        return float(qty_dec)

    def best_price(self, symbol: str, timeout: float = 3.0) -> Dict[str, Any]:
        try:
            r = self.session.get(f"{self.base}/api/v3/ticker/price", params={"symbol": symbol}, timeout=timeout)
            return r.json()
        except Exception:
            return {}
    
    def convert_to_quote(self, asset: str, amount: float, quote: str) -> float:
        """Convert an asset amount into quote using spot ticker price if available.
        
        Supports multi-hop conversion via USDT for pairs without direct trading pairs.
        """
        asset = asset.upper()
        quote = quote.upper()
        
        if asset == quote:
            return amount
        
        # Skip conversion for dust amounts (< $0.01 worth)
        if amount < 0.00001:
            return 0.0
        
        # Try direct pair first
        pair = f"{asset}{quote}"
        inv_pair = f"{quote}{asset}"
        try:
            price_info = self.best_price(pair, timeout=2.0)
            price = float(price_info.get("price", 0))
            if price > 0:
                return amount * price
        except Exception:
            pass
        try:
            price_info = self.best_price(inv_pair, timeout=2.0)
            price = float(price_info.get("price", 0))
            if price > 0:
                return amount / price
        except Exception:
            pass
        
        # Multi-hop conversion via USDT or USDC
        for pivot in ['USDT', 'USDC', 'BTC']:
            if pivot in (asset, quote):
                continue
            
            # asset -> pivot
            asset_to_pivot = 0.0
            try:
                pair1 = f"{asset}{pivot}"
                price_info = self.best_price(pair1, timeout=2.0)
                price = float(price_info.get("price", 0))
                if price > 0:
                    asset_to_pivot = amount * price
            except Exception:
                pass
            if asset_to_pivot <= 0:
                try:
                    pair1_inv = f"{pivot}{asset}"
                    price_info = self.best_price(pair1_inv, timeout=2.0)
                    price = float(price_info.get("price", 0))
                    if price > 0:
                        asset_to_pivot = amount / price
                except Exception:
                    pass
            
            if asset_to_pivot <= 0:
                continue
            
            # pivot -> quote
            pivot_to_quote = 0.0
            try:
                pair2 = f"{pivot}{quote}"
                price_info = self.best_price(pair2, timeout=2.0)
                price = float(price_info.get("price", 0))
                if price > 0:
                    pivot_to_quote = asset_to_pivot * price
            except Exception:
                pass
            if pivot_to_quote <= 0:
                try:
                    pair2_inv = f"{quote}{pivot}"
                    price_info = self.best_price(pair2_inv, timeout=2.0)
                    price = float(price_info.get("price", 0))
                    if price > 0:
                        pivot_to_quote = asset_to_pivot / price
                except Exception:
                    pass
            
            if pivot_to_quote > 0:
                return pivot_to_quote
        
        return 0.0

    def compute_order_fees_in_quote(self, order: Dict[str, Any], primary_quote: str) -> Optional[float]:
        """Return an observed fee only when its provider asset is the requested quote."""
        if (
            not isinstance(order, dict)
            or order.get("fill_receipt_complete") is not True
            or order.get("eligible_for_accounting") is not True
            or order.get("eligible_for_learning") is not True
            or order.get("generated_values") is not False
            or order.get("reconciliation_required") is not False
        ):
            return None
        fee = self._finite_number(order.get("fee"))
        fee_asset = str(order.get("fee_asset") or order.get("fee_currency") or "").strip().upper()
        quote_asset = str(primary_quote or "").strip().upper()
        if fee is None or fee < 0 or not fee_asset or fee_asset != quote_asset:
            return None
        return fee
    
    def get_ticker_price(self, symbol: str) -> Optional[Dict[str, str]]:
        """Get current price for a symbol."""
        symbol = self._norm(symbol)
        try:
            r = self.session.get(f"{self.base}/api/v3/ticker/price", params={"symbol": symbol}, timeout=5)
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
        return None

    def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """Return only complete, fresh observed Binance 24-hour quote evidence."""
        symbol = self._norm(symbol)
        received_at = time.time()
        try:
            raw = self.get_24h_ticker(symbol)
        except Exception:
            raw = None
        if not isinstance(raw, dict):
            return {"symbol": symbol, "source_timestamp": None, "received_at": received_at, "truth_status": "no_data", "generated_values": False, "data_status": "no_data"}
        source_timestamp = self._fresh_provider_timestamp(raw.get("closeTime"), max_age_seconds=300.0)
        bid = self._finite_number(raw.get("bidPrice"), positive=True)
        ask = self._finite_number(raw.get("askPrice"), positive=True)
        last = self._finite_number(raw.get("lastPrice"), positive=True)
        if source_timestamp is None or bid is None or ask is None or last is None or ask < bid:
            return {"symbol": symbol, "source_timestamp": None, "received_at": received_at, "truth_status": "no_data", "generated_values": False, "data_status": "no_data"}
        return {"symbol": symbol, "price": last, "last": last, "bid": bid, "ask": ask, "source_id": "binance:/api/v3/ticker/24hr", "source_timestamp": source_timestamp, "received_at": received_at, "receipt_id": str(raw["closeTime"]), "truth_status": "real_observed", "generated_values": False, "data_status": "live", "action_enabled": False, "accounting_enabled": False, "learning_enabled": False}

    def get_24h_tickers(self) -> list:
        """Get all 24h ticker stats for commando scanning 🦆⚔️
        
        In dry-run mode, fallback to mainnet public API if testnet fails.
        """
        # Try configured endpoint first
        try:
            r = self.session.get(f"{self.base}/api/v3/ticker/24hr", timeout=10)
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
        
        # In dry-run mode, fallback to mainnet public API (no auth needed)
        if self.dry_run:
            try:
                import requests as req
                r = req.get(f"{BINANCE_MAINNET}/api/v3/ticker/24hr", timeout=10)
                if r.status_code == 200:
                    return r.json()
            except Exception as e:
                raise RuntimeError(f"Failed to get 24h tickers (dry-run fallback failed): {e}")
        
        raise RuntimeError(f"Failed to get 24h tickers: {r.status_code if 'r' in dir() else 'no response'}")
    
    def get_24h_ticker(self, symbol: str) -> Dict[str, Any]:
        """Get 24h ticker stats for specific symbol
        
        In dry-run mode, fallback to mainnet public API if testnet fails.
        """
        symbol = self._norm(symbol)
        # Try configured endpoint first
        try:
            r = self.session.get(f"{self.base}/api/v3/ticker/24hr", params={"symbol": symbol}, timeout=10)
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
        
        # In dry-run mode, fallback to mainnet public API
        if self.dry_run:
            try:
                import requests as req
                r = req.get(f"{BINANCE_MAINNET}/api/v3/ticker/24hr", params={"symbol": symbol}, timeout=10)
                if r.status_code == 200:
                    return r.json()
            except Exception as e:
                raise RuntimeError(f"Failed to get ticker for {symbol} (dry-run fallback failed): {e}")
        
        raise RuntimeError(f"Failed to get ticker for {symbol}: {r.status_code if 'r' in dir() else 'no response'}")

    def get_klines(self, symbol: str, interval: str = "15m", limit: int = 100) -> List[Dict]:
        """Get historical klines/candlestick data for market context.
        
        Returns list of OHLCV candles for technical analysis.
        Essential for 24h historical context on startup.
        
        Args:
            symbol: Trading pair (e.g., BTCUSDC)
            interval: Candle interval (1m, 5m, 15m, 1h, 4h, 1d)
            limit: Number of candles (max 1000)
            
        Returns:
            List of dicts with open, high, low, close, volume, timestamp
        """
        try:
            params = {"symbol": symbol, "interval": interval, "limit": min(limit, 1000)}
            r = self.session.get(f"{self.base}/api/v3/klines", params=params, timeout=10)
            if r.status_code == 200:
                raw = r.json()
                # Parse Binance kline format into dict
                return [{
                    'timestamp': k[0],
                    'open': float(k[1]),
                    'high': float(k[2]),
                    'low': float(k[3]),
                    'close': float(k[4]),
                    'volume': float(k[5]),
                    'close_time': k[6],
                    'quote_volume': float(k[7]),
                    'trades': int(k[8]),
                    'taker_buy_base': float(k[9]),
                    'taker_buy_quote': float(k[10])
                } for k in raw]
        except Exception:
            pass
        
        # Fallback to mainnet for dry-run
        if self.dry_run:
            try:
                params = {"symbol": symbol, "interval": interval, "limit": min(limit, 1000)}
                r = requests.get(f"{BINANCE_MAINNET}/api/v3/klines", params=params, timeout=10)
                if r.status_code == 200:
                    raw = r.json()
                    return [{
                        'timestamp': k[0],
                        'open': float(k[1]),
                        'high': float(k[2]),
                        'low': float(k[3]),
                        'close': float(k[4]),
                        'volume': float(k[5]),
                        'close_time': k[6],
                        'quote_volume': float(k[7]),
                        'trades': int(k[8]),
                        'taker_buy_base': float(k[9]),
                        'taker_buy_quote': float(k[10])
                    } for k in raw]
            except Exception as e:
                print(f"⚠️ Failed to get klines for {symbol}: {e}")
        return []
    
    def get_24h_historical(self, symbols: List[str] = None, interval: str = "1h") -> Dict[str, List[Dict]]:
        """Bootstrap 24h historical data for multiple symbols.
        
        Fetches 24 hours of historical candles for each symbol to establish
        market context before live trading begins.
        
        Args:
            symbols: List of symbols to fetch (default: top volume pairs)
            interval: Candle interval (default 1h = 24 candles per day)
            
        Returns:
            Dict mapping symbol -> list of OHLCV candles
        """
        if symbols is None:
            # Get top volume USDC pairs
            try:
                tickers = self.get_24h_tickers()
                usdc_pairs = [t for t in tickers if t['symbol'].endswith('USDC')]
                usdc_pairs.sort(key=lambda x: float(x.get('quoteVolume', 0)), reverse=True)
                symbols = [t['symbol'] for t in usdc_pairs[:20]]
            except Exception:
                symbols = ['BTCUSDC', 'ETHUSDC', 'SOLUSDC', 'BNBUSDC', 'XRPUSDC']
        
        historical_data = {}
        limit = 24 if interval == "1h" else 96  # 24h of 1h candles or 24h of 15m candles
        
        print(f"📊 Bootstrapping 24h historical data for {len(symbols)} symbols...")
        for symbol in symbols:
            try:
                klines = self.get_klines(symbol, interval, limit)
                if klines:
                    historical_data[symbol] = klines
            except Exception as e:
                print(f"   ⚠️ {symbol}: {e}")
        
        print(f"   ✅ Loaded {len(historical_data)} symbol histories")
        return historical_data

    def get_deposit_address(self, coin: str, network: str | None = None) -> Dict[str, Any]:
        """Retrieve deposit address for a given coin (and optional network).

        Note: Not available on testnet. Will raise if testnet flag is set.
        """
        if self.use_testnet:
            raise RuntimeError("Deposit addresses are not provided by Binance testnet; switch BINANCE_USE_TESTNET=false only after validation.")
        params: Dict[str, Any] = {"coin": coin}
        if network:
            params["network"] = network
        return self._signed_request("GET", "/sapi/v1/capital/deposit/address", params)

    def withdraw(self, coin: str, address: str, amount: float,
                 network: str | None = None, address_tag: str | None = None) -> Dict[str, Any]:
        """Initiate a withdrawal from Binance spot wallet to an external address.

        Args:
            coin:        Asset ticker, e.g. 'USDT'.
            address:     Destination wallet address.
            amount:      Amount to withdraw (must exceed Binance's minimum and network fee).
            network:     Network override, e.g. 'TRX' for TRC20 (low fee), 'ETH' for ERC20.
                         If omitted Binance picks the default network for the coin.
            address_tag: Memo/tag required by some networks (XRP, XLM, etc.).

        Returns:
            Dict containing 'id' (withdrawal ID) on success, or an error dict.
        """
        if self.use_testnet:
            raise RuntimeError("Withdrawals are not supported on Binance testnet.")
        params: Dict[str, Any] = {
            "coin": coin,
            "address": address,
            "amount": str(amount),
        }
        if network:
            params["network"] = network
        if address_tag:
            params["addressTag"] = address_tag
        return self._signed_request("POST", "/sapi/v1/capital/withdraw/apply", params)

    # ── Simple Earn (Flexible) ──────────────────────────────────────────────
    def get_flexible_positions(self, asset: str = None) -> Dict[str, Any]:
        """Get Simple Earn flexible product positions."""
        params: Dict[str, Any] = {"size": 100}
        if asset:
            params["asset"] = asset
        return self._signed_request("GET", "/sapi/v1/simple-earn/flexible/position", params)

    def redeem_flexible(self, product_id: str, amount: float = None, redeem_all: bool = False) -> Dict[str, Any]:
        """Redeem from Simple Earn flexible product back to spot wallet.
        
        Args:
            product_id: The product ID from get_flexible_positions()
            amount: Amount to redeem (None = all)
            redeem_all: If True, redeem entire position
        """
        params: Dict[str, Any] = {"productId": product_id}
        if redeem_all:
            params["redeemAll"] = True
        elif amount is not None:
            params["amount"] = str(amount)
        else:
            params["redeemAll"] = True
        return self._signed_request("POST", "/sapi/v1/simple-earn/flexible/redeem", params)

    def get_my_trades(self, symbol: str, limit: int = 500, silent: bool = False) -> list:
        """Get trade history for a symbol.
        
        Returns list of trades with entry prices, quantities, fees etc.
        Used to calculate real cost basis for positions.
        
        Args:
            symbol: Trading pair symbol
            limit: Max trades to return
            silent: If True, suppress error messages for invalid symbols
        """
        params = {"symbol": symbol, "limit": limit}
        try:
            return self._signed_request("GET", "/api/v3/myTrades", params)
        except Exception as e:
            # Only print errors if not silent and not an "Invalid symbol" error
            if not silent and 'Invalid symbol' not in str(e):
                print(f"⚠️ Failed to get trade history for {symbol}: {e}")
            return []
    
    def get_all_my_trades(self, symbols: list = None, limit_per_symbol: int = 100) -> Dict[str, list]:
        """Get trade history for multiple symbols.
        
        Returns dict: {symbol: [trades]}
        """
        # 🔧 BINANCE VALID PAIRS: Only try quote currencies that Binance actually supports
        # Binance has very limited EUR/GBP support - only major pairs
        BINANCE_EUR_SUPPORTED = {'BTC', 'ETH', 'BNB', 'XRP', 'ADA', 'SOL', 'DOT', 'DOGE', 'SHIB', 'MATIC', 'LTC', 'AVAX', 'LINK', 'ATOM'}
        BINANCE_GBP_SUPPORTED = {'BTC', 'ETH', 'BNB', 'XRP', 'ADA', 'SOL', 'DOT', 'DOGE', 'LTC'}
        
        # Assets that should NEVER be used as base (stablecoins, earn products, etc.)
        SKIP_AS_BASE = {'USDC', 'USDT', 'BUSD', 'TUSD', 'FDUSD', 'EUR', 'GBP', 'USD', 
                        'LDUSDC', 'LDUSDT', 'LDBUSD', 'LDBNB', 'LDBTC', 'LDETH'}
        
        if not symbols:
            # Get symbols from current balances
            account = self.account()
            balances = account.get('balances', [])
            symbols = []
            for b in balances:
                if float(b.get('free', 0)) > 0 or float(b.get('locked', 0)) > 0:
                    asset = b['asset'].upper()
                    
                    # Skip stablecoins and special assets as base
                    if asset in SKIP_AS_BASE or asset.startswith('LD'):
                        continue
                    
                    # Clean up Binance Earn prefix if present
                    clean_asset = asset[2:] if asset.startswith('LD') else asset
                    
                    # Only try quote currencies that this asset actually supports on Binance
                    # USDC and USDT are widely supported
                    symbols.append(f"{clean_asset}USDC")
                    symbols.append(f"{clean_asset}USDT")
                    
                    # EUR only for major coins
                    if clean_asset in BINANCE_EUR_SUPPORTED:
                        symbols.append(f"{clean_asset}EUR")
                    
                    # GBP only for top coins
                    if clean_asset in BINANCE_GBP_SUPPORTED:
                        symbols.append(f"{clean_asset}GBP")
        
        all_trades = {}
        for symbol in symbols:
            try:
                trades = self.get_my_trades(symbol, limit_per_symbol, silent=True)
                if trades:
                    all_trades[symbol] = trades
            except:
                continue
        return all_trades
    
    def calculate_cost_basis(self, symbol: str) -> Dict[str, Any]:
        """Calculate average cost basis for a symbol from trade history.
        
        Returns:
            {
                'symbol': str,
                'avg_entry_price': float,
                'total_quantity': float,
                'total_cost': float,
                'total_fees': float,
                'trade_count': int,
                'first_trade': timestamp,
                'last_trade': timestamp
            }
        """
        trades = self.get_my_trades(symbol)
        if not trades:
            return None
        
        total_qty = 0.0
        total_cost = 0.0
        total_fees = 0.0
        buy_trades = 0
        first_trade = None
        last_trade = None
        
        for trade in trades:
            is_buyer = trade.get('isBuyer', False)
            qty = float(trade.get('qty', 0))
            price = float(trade.get('price', 0))
            commission = float(trade.get('commission', 0))
            timestamp = trade.get('time', 0)
            
            if is_buyer:
                total_qty += qty
                total_cost += qty * price
                total_fees += commission
                buy_trades += 1
            else:
                # Sell reduces position
                total_qty -= qty
                # Proportionally reduce cost basis
                if total_qty > 0:
                    avg_price = total_cost / (total_qty + qty) if (total_qty + qty) > 0 else 0
                    total_cost = total_qty * avg_price
            
            if first_trade is None or timestamp < first_trade:
                first_trade = timestamp
            if last_trade is None or timestamp > last_trade:
                last_trade = timestamp
        
        avg_entry = total_cost / total_qty if total_qty > 0 else 0
        
        return {
            'symbol': symbol,
            'avg_entry_price': avg_entry,
            'total_quantity': total_qty,
            'total_cost': total_cost,
            'total_fees': total_fees,
            'trade_count': buy_trades,
            'first_trade': first_trade,
            'last_trade': last_trade
        }

    # ══════════════════════════════════════════════════════════════════════
    # CRYPTO CONVERSION - Convert between crypto assets internally
    # ══════════════════════════════════════════════════════════════════════

    _pairs_cache = None
    _pairs_cache_time = 0
    _PAIRS_CACHE_TTL = 300  # 5 minutes

    def get_available_pairs(self, base: str = None, quote: str = None) -> List[Dict[str, Any]]:
        """
        Get available trading pairs, optionally filtered by base or quote asset.
        Uses caching to avoid repeated API calls (5 min TTL).
        """
        import time as _time
        current_time = _time.time()
        
        # Check cache
        if BinanceClient._pairs_cache is None or (current_time - BinanceClient._pairs_cache_time) > BinanceClient._PAIRS_CACHE_TTL:
            try:
                info = self.exchange_info()
                symbols = info.get("symbols", [])
                all_pairs = []
                
                for sym in symbols:
                    if sym.get("status") != "TRADING":
                        continue
                    
                    all_pairs.append({
                        "pair": sym.get("symbol"),
                        "base": sym.get("baseAsset", ""),
                        "quote": sym.get("quoteAsset", "")
                    })
                
                BinanceClient._pairs_cache = all_pairs
                BinanceClient._pairs_cache_time = current_time
            except Exception as e:
                print(f"Error getting pairs: {e}")
                return BinanceClient._pairs_cache or []
        
        # Filter from cache
        results = []
        for p in (BinanceClient._pairs_cache or []):
            if base and p["base"].upper() != base.upper():
                continue
            if quote and p["quote"].upper() != quote.upper():
                continue
            results.append(p)
        
        return results

    def find_conversion_path(self, from_asset: str, to_asset: str) -> List[Dict[str, Any]]:
        """Resolve a provider-listed one- or two-hop spot conversion route."""
        source_asset = str(from_asset or "").strip().upper()
        target_asset = str(to_asset or "").strip().upper()
        if not source_asset or not target_asset or source_asset == target_asset:
            return []
        pair_map = {
            str(row.get("pair") or "").strip().upper(): row
            for row in self.get_available_pairs()
            if isinstance(row, dict) and str(row.get("pair") or "").strip()
        }
        direct_pair = f"{source_asset}{target_asset}"
        if direct_pair in pair_map:
            return [{
                "pair": direct_pair,
                "side": "SELL",
                "from": source_asset,
                "to": target_asset,
                "description": f"Sell {source_asset} for {target_asset}",
            }]
        inverse_pair = f"{target_asset}{source_asset}"
        if inverse_pair in pair_map:
            return [{
                "pair": inverse_pair,
                "side": "BUY",
                "from": source_asset,
                "to": target_asset,
                "description": f"Buy {target_asset} with {source_asset}",
            }]

        for intermediate in ("USDT", "USDC", "BTC", "BNB", "EUR"):
            if intermediate in {source_asset, target_asset}:
                continue
            if self.uk_mode and (intermediate in UK_RESTRICTED_TOKENS or intermediate == "USDC"):
                continue
            first = None
            first_direct = f"{source_asset}{intermediate}"
            first_inverse = f"{intermediate}{source_asset}"
            if first_direct in pair_map:
                first = {
                    "pair": first_direct,
                    "side": "SELL",
                    "from": source_asset,
                    "to": intermediate,
                    "description": f"Sell {source_asset} for {intermediate}",
                }
            elif first_inverse in pair_map:
                first = {
                    "pair": first_inverse,
                    "side": "BUY",
                    "from": source_asset,
                    "to": intermediate,
                    "description": f"Buy {intermediate} with {source_asset}",
                }
            if first is None:
                continue

            second = None
            second_direct = f"{intermediate}{target_asset}"
            second_inverse = f"{target_asset}{intermediate}"
            if second_direct in pair_map:
                second = {
                    "pair": second_direct,
                    "side": "SELL",
                    "from": intermediate,
                    "to": target_asset,
                    "description": f"Sell {intermediate} for {target_asset}",
                }
            elif second_inverse in pair_map:
                second = {
                    "pair": second_inverse,
                    "side": "BUY",
                    "from": intermediate,
                    "to": target_asset,
                    "description": f"Buy {target_asset} with {intermediate}",
                }
            if second is not None:
                return [first, second]
        return []

    def _complete_conversion_hop_receipt(
        self,
        receipt: Any,
        *,
        trade: Dict[str, Any],
    ) -> bool:
        if not isinstance(receipt, dict):
            return False
        quantity = self._finite_number(receipt.get("filled_qty"), positive=True)
        notional = self._finite_number(receipt.get("filled_notional"), positive=True)
        average_price = self._finite_number(receipt.get("filled_avg_price"), positive=True)
        fee = self._finite_number(receipt.get("fee"))
        source_timestamp = self._timestamp_seconds(receipt.get("source_timestamp"))
        received_at = self._timestamp_seconds(receipt.get("received_at"))
        now = time.time()
        expected_notional = quantity * average_price if quantity is not None and average_price is not None else None
        fills = receipt.get("fills")
        trade_ids = [
            self._valid_provider_identifier(row.get("tradeId"))
            for row in fills
            if isinstance(row, dict)
        ] if isinstance(fills, list) else []
        return bool(
            receipt.get("status") in {"FILLED", "PARTIALLY_FILLED"}
            and receipt.get("data_status") == "live"
            and receipt.get("truth_status") == "real_observed"
            and receipt.get("generated_values") is False
            and receipt.get("fill_receipt_complete") is True
            and receipt.get("eligible_for_accounting") is True
            and receipt.get("eligible_for_learning") is True
            and receipt.get("reconciliation_required") is False
            and self._norm(str(receipt.get("symbol") or "")).upper() == str(trade["pair"]).upper()
            and str(receipt.get("side") or "").strip().upper() == str(trade["side"]).upper()
            and self._valid_provider_identifier(receipt.get("orderId")) is not None
            and self._valid_provider_identifier(receipt.get("receipt_id")) is not None
            and quantity is not None
            and notional is not None
            and average_price is not None
            and fee is not None
            and fee >= 0
            and bool(str(receipt.get("fee_asset") or "").strip())
            and bool(trade_ids)
            and all(trade_id is not None for trade_id in trade_ids)
            and len(trade_ids) == len(set(trade_ids))
            and expected_notional is not None
            and math.isclose(notional, expected_notional, rel_tol=0.001, abs_tol=1e-8)
            and source_timestamp is not None
            and received_at is not None
            and source_timestamp <= received_at + 5.0
            and received_at <= now + 5.0
            and now - source_timestamp <= 300.0
            and now - received_at <= 300.0
        )

    @staticmethod
    def _conversion_controls() -> Dict[str, bool]:
        return {
            "eligible_for_action": False,
            "eligible_for_accounting": False,
            "eligible_for_learning": False,
            "generated_values": False,
            "action": False,
            "accounting": False,
            "learning": False,
        }

    def convert_crypto(
        self,
        from_asset: str,
        to_asset: str,
        amount: float,
        use_quote_amount: bool = False,
    ) -> Dict[str, Any]:
        """Advance at most one receipt-gated conversion hop per invocation."""
        source_asset = str(from_asset or "").strip().upper()
        target_asset = str(to_asset or "").strip().upper()
        requested_amount = self._finite_number(amount, positive=True)
        controls = self._conversion_controls()
        if not source_asset or not target_asset or source_asset == target_asset or requested_amount is None:
            return {
                "success": False,
                "status": "no_data",
                "data_status": "no_data",
                "truth_status": "no_data",
                "reason": "distinct_assets_and_positive_finite_amount_required",
                "from_asset": source_asset,
                "to_asset": target_asset,
                **controls,
            }
        if self.dry_run:
            return {
                "success": False,
                "status": "not_submitted",
                "data_status": "not_submitted",
                "truth_status": "no_data",
                "reason": "dry_run",
                "from_asset": source_asset,
                "to_asset": target_asset,
                "original_amount": requested_amount,
                **controls,
            }

        conversion_key = (source_asset, target_asset)
        state = self._pending_conversions.get(conversion_key)
        if isinstance(state, dict):
            terminal_failure = state.get("terminal_failure")
            if isinstance(terminal_failure, dict):
                return {
                    "success": False,
                    "status": "no_data",
                    "data_status": "no_data",
                    "truth_status": "real_observed",
                    "reason": str(terminal_failure.get("reason") or "terminal_conversion_failure_latched"),
                    "from_asset": source_asset,
                    "to_asset": target_asset,
                    "original_amount": requested_amount,
                    "terminal_receipt": terminal_failure.get("receipt"),
                    **controls,
                }
            same_amount = math.isclose(
                float(state["requested_amount"]),
                requested_amount,
                rel_tol=1e-12,
                abs_tol=1e-12,
            )
            if same_amount is False or bool(state.get("use_quote_amount")) != bool(use_quote_amount):
                return {
                    "success": False,
                    "status": "pending_reconciliation",
                    "data_status": "pending_reconciliation",
                    "truth_status": "real_observed",
                    "reason": "existing_conversion_must_reconcile_before_new_request",
                    "from_asset": source_asset,
                    "to_asset": target_asset,
                    "original_amount": requested_amount,
                    "pending_original_amount": state.get("requested_amount"),
                    **controls,
                }
        else:
            submitted_amount = requested_amount
            balance_receipt_id = None
            if not use_quote_amount:
                balance_receipt = self.get_asset_balance(source_asset)
                available = self._finite_number(
                    balance_receipt.get("free") if isinstance(balance_receipt, dict) else None
                )
                if (
                    not isinstance(balance_receipt, dict)
                    or balance_receipt.get("eligible_for_action") is not True
                    or balance_receipt.get("truth_status") != "real_provider"
                    or balance_receipt.get("generated_values") is not False
                    or available is None
                    or available <= 0
                ):
                    return {
                        "success": False,
                        "status": "no_data",
                        "data_status": "no_data",
                        "truth_status": "no_data",
                        "reason": "fresh_positive_source_balance_receipt_required",
                        "from_asset": source_asset,
                        "to_asset": target_asset,
                        "original_amount": requested_amount,
                        **controls,
                    }
                balance_receipt_id = balance_receipt.get("receipt_id")
                if submitted_amount > available * 0.99:
                    submitted_amount = available * 0.999
                if not math.isfinite(submitted_amount) or submitted_amount <= 0:
                    return {
                        "success": False,
                        "status": "no_data",
                        "data_status": "no_data",
                        "truth_status": "no_data",
                        "reason": "positive_balance_clamped_amount_required",
                        "from_asset": source_asset,
                        "to_asset": target_asset,
                        "original_amount": requested_amount,
                        **controls,
                    }

            path = self.find_conversion_path(source_asset, target_asset)
            if not path:
                return {
                    "success": False,
                    "status": "no_data",
                    "data_status": "no_data",
                    "truth_status": "no_data",
                    "reason": "provider_listed_conversion_path_unavailable",
                    "from_asset": source_asset,
                    "to_asset": target_asset,
                    "original_amount": requested_amount,
                    **controls,
                }
            state = {
                "requested_amount": requested_amount,
                "submitted_amount": submitted_amount,
                "remaining_amount": submitted_amount,
                "use_quote_amount": bool(use_quote_amount),
                "path": path,
                "next_hop": 0,
                "terminal_receipts": [],
                "balance_receipt_id": balance_receipt_id,
            }
            self._pending_conversions[conversion_key] = state

        path = state.get("path")
        next_hop = state.get("next_hop")
        remaining_amount = self._finite_number(state.get("remaining_amount"), positive=True)
        if (
            not isinstance(path, list)
            or not isinstance(next_hop, int)
            or next_hop < 0
            or next_hop >= len(path)
            or remaining_amount is None
            or not isinstance(path[next_hop], dict)
        ):
            self._pending_conversions.pop(conversion_key, None)
            return {
                "success": False,
                "status": "no_data",
                "data_status": "no_data",
                "truth_status": "no_data",
                "reason": "conversion_state_incomplete",
                "from_asset": source_asset,
                "to_asset": target_asset,
                **controls,
            }

        trade = path[next_hop]
        pair = str(trade.get("pair") or "").strip().upper()
        side = str(trade.get("side") or "").strip().upper()
        if not pair or side not in {"BUY", "SELL"}:
            self._pending_conversions.pop(conversion_key, None)
            return {
                "success": False,
                "status": "no_data",
                "data_status": "no_data",
                "truth_status": "no_data",
                "reason": "conversion_hop_pair_and_side_required",
                "from_asset": source_asset,
                "to_asset": target_asset,
                **controls,
            }

        receipt = (
            self.place_market_order(pair, side, quantity=remaining_amount)
            if side == "SELL"
            else self.place_market_order(pair, side, quote_qty=remaining_amount)
        )
        prior_receipts = list(state.get("terminal_receipts") or [])
        if not self._complete_conversion_hop_receipt(receipt, trade=trade):
            receipt_data_status = receipt.get("data_status") if isinstance(receipt, dict) else None
            receipt_status = receipt.get("status") if isinstance(receipt, dict) else None
            reconciliation_required = receipt.get("reconciliation_required") if isinstance(receipt, dict) else None
            if receipt_data_status != "pending_reconciliation":
                self._pending_conversions.pop(conversion_key, None)
            return {
                "success": False,
                "status": "pending_reconciliation" if receipt_data_status == "pending_reconciliation" else "no_data",
                "data_status": "pending_reconciliation" if receipt_data_status == "pending_reconciliation" else "no_data",
                "truth_status": "real_observed" if receipt_data_status == "pending_reconciliation" else "no_data",
                "reason": (
                    str(receipt.get("reason") or "terminal_provider_fill_receipt_required")
                    if isinstance(receipt, dict)
                    else "terminal_provider_fill_receipt_required"
                ),
                "from_asset": source_asset,
                "to_asset": target_asset,
                "original_amount": requested_amount,
                "submitted_amount": state.get("submitted_amount"),
                "current_hop": next_hop,
                "current_order_status": receipt_status,
                "reconciliation_required": reconciliation_required is not False,
                "partial_results": prior_receipts,
                "current_receipt": receipt if isinstance(receipt, dict) else None,
                **controls,
            }

        output_amount = self._finite_number(
            receipt.get("filled_notional") if side == "SELL" else receipt.get("filled_qty"),
            positive=True,
        )
        fee = self._finite_number(receipt.get("fee"))
        fee_asset = str(receipt.get("fee_asset") or "").strip().upper()
        received_asset = str(trade.get("to") or "").strip().upper()
        if output_amount is None or fee is None or fee < 0 or not fee_asset or not received_asset:
            state["terminal_failure"] = {
                "reason": "terminal_hop_output_and_fee_evidence_required",
                "receipt": dict(receipt),
            }
            return {
                "success": False,
                "status": "no_data",
                "data_status": "no_data",
                "truth_status": "no_data",
                "reason": "terminal_hop_output_and_fee_evidence_required",
                "from_asset": source_asset,
                "to_asset": target_asset,
                "current_receipt": receipt,
                **controls,
            }
        if fee_asset == received_asset:
            output_amount -= fee
        if not math.isfinite(output_amount) or output_amount <= 0:
            state["terminal_failure"] = {
                "reason": "positive_post_fee_hop_output_required",
                "receipt": dict(receipt),
            }
            return {
                "success": False,
                "status": "no_data",
                "data_status": "no_data",
                "truth_status": "no_data",
                "reason": "positive_post_fee_hop_output_required",
                "from_asset": source_asset,
                "to_asset": target_asset,
                **controls,
            }

        prior_receipts.append({"trade": dict(trade), "result": dict(receipt), "status": "terminal"})
        state["terminal_receipts"] = prior_receipts
        state["remaining_amount"] = output_amount
        state["next_hop"] = next_hop + 1
        if state["next_hop"] < len(path):
            return {
                "success": False,
                "status": "pending_reconciliation",
                "data_status": "pending_reconciliation",
                "truth_status": "real_derived",
                "reason": "next_conversion_hop_not_submitted",
                "from_asset": source_asset,
                "to_asset": target_asset,
                "original_amount": requested_amount,
                "intermediate_amount": output_amount,
                "completed_hops": len(prior_receipts),
                "trades": prior_receipts,
                **controls,
            }

        self._pending_conversions.pop(conversion_key, None)
        source_timestamp = max(float(row["result"]["source_timestamp"]) for row in prior_receipts)
        receipt_ids = [str(row["result"]["receipt_id"]) for row in prior_receipts]
        conversion_receipt_id = "binance:conversion:" + hashlib.sha256("|".join(receipt_ids).encode("utf-8")).hexdigest()
        return {
            "success": True,
            "status": "FILLED",
            "data_status": "live",
            "truth_status": "real_derived",
            "reason": "all_conversion_hops_have_terminal_provider_receipts",
            "from_asset": source_asset,
            "to_asset": target_asset,
            "original_amount": requested_amount,
            "submitted_amount": state.get("submitted_amount"),
            "final_amount": output_amount,
            "path": path,
            "trades": prior_receipts,
            "trade_count": len(prior_receipts),
            "source_id": "binance:conversion:terminal_hops",
            "source_timestamp": source_timestamp,
            "received_at": time.time(),
            "receipt_id": conversion_receipt_id,
            "terminal_receipt_ids": receipt_ids,
            "eligible_for_action": False,
            "eligible_for_accounting": True,
            "eligible_for_learning": True,
            "generated_values": False,
            "action": False,
            "accounting": True,
            "learning": True,
        }

    # CROSS MARGIN TRADING  —  Binance SAPI /sapi/v1/margin
    # ═══════════════════════════════════════════════════════════════════════
    #
    # Mirrors the Kraken margin API so OrcaKillCycle can use either exchange
    # transparently via duck-typing (hasattr(client, 'place_margin_order')).
    #
    # Binance Cross Margin uses sideEffectType to auto-borrow / auto-repay:
    #   MARGIN_BUY   → borrow quote asset, buy base (open LONG)
    #   AUTO_REPAY   → sell base, repay borrowed quote (close LONG)
    #   NO_SIDE_EFFECT → move funds within margin account (no borrow/repay)
    #
    # UK NOTE: Binance margin is restricted for FCA-regulated UK accounts.
    # place_margin_order() returns a rejection dict when uk_mode=True so the
    # Orca loop degrades to spot trading without crashing.
    #
    # ENV VARS (add to .env to enable Binance margin):
    #   BINANCE_MARGIN_ENABLED=true        — master switch (default: false)
    #   BINANCE_MARGIN_MAX_LEVERAGE=3      — cap leverage (default: 3)
    #   BINANCE_MARGIN_ISOLATED=false      — cross (default) vs isolated margin
    # ═══════════════════════════════════════════════════════════════════════

    def _margin_enabled(self) -> bool:
        """True if Binance margin trading is enabled and account is non-UK."""
        if self.uk_mode:
            return False
        return os.getenv("BINANCE_MARGIN_ENABLED", "false").lower() in ("1", "true", "yes")

    def _margin_isolated(self) -> bool:
        """True = use Isolated margin; False (default) = Cross margin."""
        return os.getenv("BINANCE_MARGIN_ISOLATED", "false").lower() in ("1", "true", "yes")

    def get_margin_account(self) -> Dict[str, Any]:
        """
        GET /sapi/v1/margin/account

        Returns the cross-margin account summary:
          marginLevel           — safety score (>1.5 = healthy, <1.1 = liquidation risk)
          totalAssetOfBtc       — total value in BTC
          totalLiabilityOfBtc   — total borrowed in BTC
          totalNetAssetOfBtc    — equity in BTC
          userAssets[]          — per-asset balances, borrowed, free, interest
        """
        if self.dry_run:
            return {
                "status": "not_submitted",
                "data_status": "not_submitted",
                "truth_status": "no_data",
                "reason": "dry_run_provider_account_readback_disabled",
                "generated_values": False,
                "eligible_for_action": False,
                "eligible_for_accounting": False,
                "eligible_for_learning": False,
            }
        return self._signed_request("GET", "/sapi/v1/margin/account", {})

    def get_margin_pairs(self) -> List[Dict[str, Any]]:
        """
        GET /sapi/v1/margin/allPairs

        Returns all cross-margin eligible trading pairs, normalised to match
        the Kraken margin pairs format used by OrcaKillCycle:

          [{"pair": "BTCUSDT", "base": "BTC", "quote": "USDT",
            "leverage_buy": [3], "leverage_sell": [3], "max_leverage": 3,
            "is_buy_allowed": True, "is_sell_allowed": True}]

        Binance cross-margin provides up to 3x leverage for most pairs
        (5x for BTC/ETH with a higher-tier account).
        """
        if self.dry_run:
            return []
        try:
            raw = self._signed_request("GET", "/sapi/v1/margin/allPairs", {})
            results = []
            max_lev = int(os.getenv("BINANCE_MARGIN_MAX_LEVERAGE", "3"))
            for p in (raw if isinstance(raw, list) else []):
                is_buy  = bool(p.get("isBuyAllowed",  True))
                is_sell = bool(p.get("isSellAllowed", True))
                sym     = str(p.get("symbol", p.get("base", "") + p.get("quote", "")))
                results.append({
                    "pair":          sym,
                    "base":          str(p.get("base",  "")),
                    "quote":         str(p.get("quote", "")),
                    "leverage_buy":  [max_lev] if is_buy  else [],
                    "leverage_sell": [max_lev] if is_sell else [],
                    "max_leverage":  max_lev,
                    "is_buy_allowed":  is_buy,
                    "is_sell_allowed": is_sell,
                })
            return results
        except Exception as e:
            import logging; logging.getLogger(__name__).warning(f"BinanceClient.get_margin_pairs error: {e}")
            return []

    def get_margin_pair_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        GET /sapi/v1/margin/pair?symbol=BTCUSDT

        Returns info for a single cross-margin pair, or None if not eligible.
        """
        sym = self._norm(symbol)
        if self.dry_run:
            return None
        try:
            return self._signed_request("GET", "/sapi/v1/margin/pair", {"symbol": sym})
        except Exception:
            return None

    def get_open_margin_positions(self, do_calcs: bool = True) -> List[Dict[str, Any]]:
        """
        Derive open margin positions from the cross-margin account's userAssets.

        Returns a normalised list matching the Kraken get_open_margin_positions()
        format used by OrcaKillCycle for position monitoring:

          [{"symbol": "BTCUSDT", "side": "buy", "pair": "BTCUSDT",
            "volume": 0.001, "cost": 65.0, "current_value": 65.5,
            "unrealized_pnl": 0.50, "leverage": 3, "margin": 21.67,
            "borrowed": 43.33, "interest": 0.01}]
        """
        if self.dry_run:
            return []
        try:
            acct = self.get_margin_account()
            assets = acct.get("userAssets") if isinstance(acct, dict) else None
            if not isinstance(assets, list):
                return []
            positions = []
            for asset in assets:
                if not isinstance(asset, dict):
                    continue
                borrowed = self._finite_number(asset.get("borrowed"))
                net_asset = self._finite_number(asset.get("netAsset"))
                free = self._finite_number(asset.get("free"))
                interest = self._finite_number(asset.get("interest"))
                if (
                    borrowed is None
                    or net_asset is None
                    or free is None
                    or interest is None
                    or borrowed < 0
                    or interest < 0
                ):
                    continue
                if borrowed > 0 or net_asset < 0:
                    a_sym = str(asset.get("asset", ""))
                    ticker = self.get_ticker(a_sym + "USDT")
                    price = self._finite_number(
                        ticker.get("price") if isinstance(ticker, dict) else None,
                        positive=True,
                    )
                    if (
                        not a_sym
                        or not isinstance(ticker, dict)
                        or ticker.get("data_status") != "live"
                        or ticker.get("truth_status") != "real_observed"
                        or ticker.get("generated_values") is not False
                        or price is None
                    ):
                        continue
                    current_value = (free + net_asset) * price
                    cost = borrowed * price
                    unrealized    = current_value - cost
                    max_lev = int(os.getenv("BINANCE_MARGIN_MAX_LEVERAGE", "3"))
                    if max_lev <= 0:
                        continue
                    positions.append({
                        "symbol":        a_sym + "USDT",
                        "pair":          a_sym + "USDT",
                        "side":          "buy" if net_asset > 0 else "sell",
                        "volume":        abs(free + net_asset),
                        "cost":          cost,
                        "current_value": current_value,
                        "unrealized_pnl": unrealized,
                        "leverage":      max_lev,
                        "margin":        current_value / max_lev,
                        "borrowed":      borrowed,
                        "interest":      interest,
                        "exchange":      "binance",
                        "source_id":     ticker.get("source_id"),
                        "source_timestamp": ticker.get("source_timestamp"),
                        "received_at":   ticker.get("received_at"),
                        "receipt_id":    ticker.get("receipt_id"),
                        "truth_status":  "real_derived",
                        "generated_values": False,
                    })
            return positions
        except Exception as e:
            import logging; logging.getLogger(__name__).warning(f"BinanceClient.get_open_margin_positions error: {e}")
            return []

    def _place_margin_order_receipt_gated(
        self,
        *,
        symbol: str,
        side: str,
        quantity: float,
        leverage: int,
        order_type: str,
        price: Optional[float],
        take_profit: Optional[float],
        stop_loss: Optional[float],
        post_only: bool,
        reduce_only: bool,
    ) -> Dict[str, Any]:
        sym = self._norm(symbol).upper()
        normalized_side = str(side or "").strip().upper()
        normalized_type = str(order_type or "").strip().upper()
        quantity_value = self._finite_number(quantity, positive=True)
        limit_price = self._finite_number(price, positive=True) if price is not None else None
        if (
            not sym
            or normalized_side not in {"BUY", "SELL"}
            or normalized_type not in {"MARKET", "LIMIT"}
            or quantity_value is None
            or (normalized_type == "LIMIT" and limit_price is None)
        ):
            return self._not_submitted_order_receipt(
                "finite_quantity_side_order_type_and_limit_price_required",
                symbol=sym,
                side=normalized_side,
                margin=True,
                requested_quantity=quantity,
                requested_price=price,
            )

        key = self._order_key(sym, normalized_side, True)
        if key in self._pending_orders:
            if self.dry_run:
                pending = self._pending_orders[key]
                return self._pending_order_receipt(
                    "readback_disabled_in_dry_run",
                    symbol=sym,
                    side=normalized_side,
                    order_id=self._valid_provider_identifier(pending.get("order_id")),
                    margin=True,
                )
            return self._reconcile_pending_order(key)
        if self.dry_run:
            return self._not_submitted_order_receipt(
                "dry_run",
                symbol=sym,
                side=normalized_side,
                margin=True,
                requested_quantity=quantity_value,
                requested_price=limit_price,
            )
        if self.uk_mode:
            receipt = self._not_submitted_order_receipt(
                "binance_margin_unavailable_for_uk_account",
                symbol=sym,
                side=normalized_side,
                margin=True,
            )
            receipt["uk_restricted"] = True
            return receipt
        if not self._margin_enabled():
            return self._not_submitted_order_receipt(
                "binance_margin_not_enabled",
                symbol=sym,
                side=normalized_side,
                margin=True,
            )

        try:
            adjusted_quantity = self.adjust_quantity(sym, quantity_value)
        except Exception:
            adjusted_quantity = None
        if adjusted_quantity is None or adjusted_quantity <= 0:
            return self._not_submitted_order_receipt(
                "provider_margin_quantity_filter_rejected_request",
                symbol=sym,
                side=normalized_side,
                margin=True,
                requested_quantity=quantity_value,
            )

        is_isolated = "TRUE" if self._margin_isolated() else "FALSE"
        side_effect = "AUTO_REPAY" if reduce_only else "MARGIN_BUY"
        receipt_metadata = {
            "leverage": str(leverage),
            "sideEffectType": side_effect,
            "isIsolated": is_isolated == "TRUE",
            "reduce_only": bool(reduce_only),
            "take_profit": take_profit,
            "stop_loss": stop_loss,
        }
        params: Dict[str, Any] = {
            "symbol": sym,
            "side": normalized_side,
            "type": normalized_type,
            "quantity": self._format_order_value(adjusted_quantity),
            "sideEffectType": side_effect,
            "isIsolated": is_isolated,
            "newOrderRespType": "FULL",
        }
        if normalized_type == "LIMIT":
            params["price"] = self._format_order_value(limit_price)
            params["timeInForce"] = "GTX" if post_only else "GTC"

        try:
            response = self._signed_request("POST", "/sapi/v1/margin/order", params)
        except EconomicGovernanceBlocked:
            raise
        except Exception:
            self._pending_orders[key] = {
                "order_id": None,
                "order": {},
                "params": dict(params),
                "is_isolated": is_isolated,
                "metadata": dict(receipt_metadata),
            }
            pending_receipt = self._pending_order_receipt(
                "ambiguous_submission_requires_external_reconciliation",
                symbol=sym,
                side=normalized_side,
                order_id=None,
                margin=True,
            )
            pending_receipt.update(receipt_metadata)
            return pending_receipt

        order_id = self._valid_provider_identifier(response.get("orderId")) if isinstance(response, dict) else None
        normalized = self._normalize_order_receipt(
            response,
            symbol=sym,
            side=normalized_side,
            margin=True,
            expected_order_id=order_id,
        )
        normalized.update(receipt_metadata)
        if normalized.get("reconciliation_required") is False:
            return normalized
        self._pending_orders[key] = {
            "order_id": order_id,
            "order": dict(response) if isinstance(response, dict) else {},
            "params": dict(params),
            "is_isolated": is_isolated,
            "metadata": dict(receipt_metadata),
        }
        return normalized

    def place_margin_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        leverage: int = 3,
        order_type: str = "market",
        price: Optional[float] = None,
        take_profit: Optional[float] = None,
        stop_loss: Optional[float] = None,
        post_only: bool = False,
        reduce_only: bool = False,
    ) -> Dict[str, Any]:
        """
        POST /sapi/v1/margin/order  —  Open a cross-margin position.

        Args:
            symbol      Binance symbol, e.g. 'BTCUSDT' or 'BTC/USDT'
            side        'buy'  → LONG (borrow quote, buy base)
                        'sell' → SHORT (borrow base, sell base)
            quantity    Base-asset quantity to trade
            leverage    Target leverage (stored as metadata; Binance cross
                        margin leverage is account-level, not per-order)
            order_type  'market' (default) or 'limit'
            price       Limit price (required when order_type='limit')
            take_profit Stored locally; attach a separate OCO order if needed
            stop_loss   Stored locally; attach a separate OCO order if needed
            reduce_only If True, uses AUTO_REPAY to close an existing position
                        rather than opening a new one

        Returns a Kraken-compatible dict for seamless OrcaKillCycle substitution:
            {symbol, orderId, type, side, leverage, margin, status, ...}

        UK accounts (uk_mode=True) receive a rejection dict; margin is FCA-restricted.
        BINANCE_MARGIN_ENABLED must be 'true' in .env to allow live orders.
        """
        return self._place_margin_order_receipt_gated(
            symbol=symbol,
            side=side,
            quantity=quantity,
            leverage=leverage,
            order_type=order_type,
            price=price,
            take_profit=take_profit,
            stop_loss=stop_loss,
            post_only=post_only,
            reduce_only=reduce_only,
        )

    def close_margin_position(
        self,
        symbol: str,
        side: str,
        volume: Optional[float] = None,
        order_type: str = "market",
        price: Optional[float] = None,
        leverage: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Close an open cross-margin position using AUTO_REPAY.

        Args:
            symbol      Binance symbol, e.g. 'BTCUSDT'
            side        'sell' to close a LONG; 'buy' to close a SHORT
            volume      Quantity to close.  If None, queries open positions
                        and closes the full volume automatically.
            order_type  'market' (default) or 'limit'
            price       Limit price (required when order_type='limit')
            leverage    Ignored (Binance auto-repay handles this internally)

        Returns a Kraken-compatible dict.
        """
        sym = self._norm(symbol)

        if self.uk_mode:
            return {
                "rejected": True, "symbol": sym,
                "reason": "Binance margin not available for UK accounts.",
                "uk_restricted": True, "margin": True,
            }

        if not self._margin_enabled():
            return {
                "rejected": True, "symbol": sym,
                "reason": "Binance margin not enabled (BINANCE_MARGIN_ENABLED).",
                "margin": True,
            }

        # Auto-detect volume from open positions if not supplied
        qty = self._finite_number(volume, positive=True) if volume is not None else None
        if qty is None:
            try:
                positions = self.get_open_margin_positions()
                for pos in positions:
                    if pos.get("symbol") == sym or pos.get("pair") == sym:
                        qty = self._finite_number(pos.get("volume"), positive=True)
                        break
            except Exception:
                qty = None

        if qty is None:
            return {
                **self._not_submitted_order_receipt(
                    "fresh_open_margin_position_volume_required",
                    symbol=sym,
                    side=side,
                    margin=True,
                ),
                "error": f"No proven open margin position found for {sym} to close.",
            }

        return self.place_margin_order(
            symbol=sym,
            side=side,
            quantity=qty,
            leverage=leverage or 3,
            order_type=order_type,
            price=price,
            reduce_only=True,   # → AUTO_REPAY sideEffectType
        )

    def get_margin_interest_rates(self, asset: str = "BTC") -> List[Dict[str, Any]]:
        """
        GET /sapi/v1/margin/interestRateHistory

        Returns recent borrow interest rates for an asset.
        Binance charges interest per hour on borrowed margin funds.
        """
        if self.dry_run:
            return [{"asset": asset, "dailyInterestRate": "0.0002",
                     "timestamp": int(time.time() * 1000)}]
        try:
            return self._signed_request(
                "GET", "/sapi/v1/margin/interestRateHistory",
                {"asset": asset, "limit": 24}
            )
        except Exception as e:
            import logging; logging.getLogger(__name__).warning(f"BinanceClient.get_margin_interest_rates error: {e}")
            return []

    def borrow_margin(self, asset: str, amount: float) -> Dict[str, Any]:
        """
        POST /sapi/v1/margin/loan  —  Explicit borrow from the margin pool.

        Usually NOT needed when using place_margin_order() with MARGIN_BUY,
        which auto-borrows.  Use this for manual collateral management.
        """
        if self.dry_run:
            return {"tranId": 0, "asset": asset, "amount": str(amount), "dry_run": True}
        if self.uk_mode:
            return {"rejected": True, "reason": "Margin not available for UK accounts."}
        params = {
            "asset":      asset,
            "amount":     str(round(amount, 8)),
            "isIsolated": "TRUE" if self._margin_isolated() else "FALSE",
        }
        return self._signed_request("POST", "/sapi/v1/margin/loan", params)

    def repay_margin(self, asset: str, amount: float) -> Dict[str, Any]:
        """
        POST /sapi/v1/margin/repay  —  Explicitly repay borrowed margin funds.

        Usually NOT needed when using close_margin_position() which uses
        AUTO_REPAY.  Use this for manual debt management.
        """
        if self.dry_run:
            return {"tranId": 0, "asset": asset, "amount": str(amount), "dry_run": True}
        if self.uk_mode:
            return {"rejected": True, "reason": "Margin not available for UK accounts."}
        params = {
            "asset":      asset,
            "amount":     str(round(amount, 8)),
            "isIsolated": "TRUE" if self._margin_isolated() else "FALSE",
        }
        return self._signed_request("POST", "/sapi/v1/margin/repay", params)


def position_size_from_balance(client: BinanceClient, symbol: str, fraction: float, max_usdt: float) -> float:
    # Assume quote asset is USDT for simplicity
    quote_free = client.get_free_balance("USDT")
    size = quote_free * fraction
    return min(size, max_usdt)


def load_risk_config() -> Dict[str, Any]:
    return {
        "fraction": float(os.getenv("BINANCE_RISK_FRACTION", "0.02")),
        "max_usdt": float(os.getenv("BINANCE_RISK_MAX_ORDER_USDT", "25"))
    }


# ═══════════════════════════════════════════════════════════════════════════
# BINANCE POOL MINING API
# ═══════════════════════════════════════════════════════════════════════════

class BinancePoolClient:
    """
    Binance Pool Mining API Client
    
    Endpoints for tracking mining earnings, hashrate, and payouts.
    https://binance-docs.github.io/apidocs/spot/en/#mining-endpoints
    """
    
    def __init__(self, client: BinanceClient = None):
        self.client = client or BinanceClient()
        self.base = self.client.base
        self.session = self.client.session
    
    def _signed_request(self, method: str, path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Signed request using parent client's auth"""
        return self.client._signed_request(method, path, params)
    
    # ═══════════════════════════════════════════════════════════════════════
    # MINING ACCOUNT INFO
    # ═══════════════════════════════════════════════════════════════════════
    
    def get_algo_list(self) -> Dict[str, Any]:
        """Get list of mining algorithms (SAPI)"""
        return self._signed_request("GET", "/sapi/v1/mining/pub/algoList", {})
    
    def get_coin_list(self) -> Dict[str, Any]:
        """Get list of mineable coins (SAPI)"""
        return self._signed_request("GET", "/sapi/v1/mining/pub/coinList", {})
    
    def get_miner_list(self, algo: str = "sha256", user_name: str = None) -> Dict[str, Any]:
        """Get list of miners for account
        
        Args:
            algo: Algorithm name (sha256, ethash, etc.)
            user_name: Mining account username
        """
        params = {"algo": algo}
        if user_name:
            params["userName"] = user_name
        return self._signed_request("GET", "/sapi/v1/mining/worker/list", params)
    
    def get_miner_detail(self, algo: str, worker_name: str, user_name: str = None) -> Dict[str, Any]:
        """Get detailed miner/worker stats
        
        Args:
            algo: Algorithm name
            worker_name: Worker name (e.g., 'aureon')
            user_name: Mining account username
        """
        params = {"algo": algo, "workerName": worker_name}
        if user_name:
            params["userName"] = user_name
        return self._signed_request("GET", "/sapi/v1/mining/worker/detail", params)
    
    # ═══════════════════════════════════════════════════════════════════════
    # EARNINGS & PAYOUTS
    # ═══════════════════════════════════════════════════════════════════════
    
    def get_earnings_list(self, algo: str = "sha256", user_name: str = None, 
                          coin: str = None, start_date: int = None, 
                          end_date: int = None, page: int = 1, 
                          page_size: int = 20) -> Dict[str, Any]:
        """Get mining earnings history
        
        Args:
            algo: Algorithm name
            user_name: Mining account username
            coin: Coin name (BTC, ETH, etc.)
            start_date: Start timestamp (ms)
            end_date: End timestamp (ms)
            page: Page number
            page_size: Results per page (max 200)
        """
        params = {"algo": algo, "page": page, "pageSize": min(page_size, 200)}
        if user_name:
            params["userName"] = user_name
        if coin:
            params["coin"] = coin
        if start_date:
            params["startDate"] = start_date
        if end_date:
            params["endDate"] = end_date
        return self._signed_request("GET", "/sapi/v1/mining/payment/list", params)
    
    def get_extra_bonus(self, algo: str = "sha256", user_name: str = None,
                        coin: str = None, start_date: int = None,
                        end_date: int = None, page: int = 1,
                        page_size: int = 20) -> Dict[str, Any]:
        """Get extra mining bonus (referral, events, etc.)"""
        params = {"algo": algo, "page": page, "pageSize": min(page_size, 200)}
        if user_name:
            params["userName"] = user_name
        if coin:
            params["coin"] = coin
        if start_date:
            params["startDate"] = start_date
        if end_date:
            params["endDate"] = end_date
        return self._signed_request("GET", "/sapi/v1/mining/payment/other", params)
    
    def get_hashrate_resale_list(self, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """Get hashrate resale list (if selling hashpower)"""
        params = {"page": page, "pageSize": min(page_size, 200)}
        return self._signed_request("GET", "/sapi/v1/mining/hash-transfer/config/details/list", params)
    
    # ═══════════════════════════════════════════════════════════════════════
    # STATISTICS
    # ═══════════════════════════════════════════════════════════════════════
    
    def get_statistic_list(self, algo: str = "sha256", user_name: str = None) -> Dict[str, Any]:
        """Get mining statistics (hashrate, earnings summary)
        
        Returns:
            {
                "code": 0,
                "data": {
                    "fifteenMinHashRate": "457.38",
                    "dayHashRate": "450.12",
                    "validNum": 5,
                    "invalidNum": 0,
                    "profitToday": {"BTC": "0.00012345"},
                    "profitYesterday": {"BTC": "0.00011234"},
                    "userName": "mining_account",
                    "unit": "TH/s",
                    "algo": "sha256"
                }
            }
        """
        params = {"algo": algo}
        # userName is required by Binance Pool API
        if user_name:
            params["userName"] = user_name
        else:
            # Try to get from environment
            params["userName"] = os.getenv("BINANCE_POOL_USERNAME", os.getenv("MINING_WORKER", "").split(".")[0])
        
        if not params["userName"]:
            return {"code": -1, "msg": "userName required - set BINANCE_POOL_USERNAME env var", "data": {}}
        
        return self._signed_request("GET", "/sapi/v1/mining/statistics/user/status", params)
    
    def get_account_list(self, algo: str = "sha256", user_name: str = None) -> Dict[str, Any]:
        """Get mining account earnings list"""
        params = {"algo": algo}
        if user_name:
            params["userName"] = user_name
        return self._signed_request("GET", "/sapi/v1/mining/statistics/user/list", params)
    
    # ═══════════════════════════════════════════════════════════════════════
    # CONVENIENCE METHODS
    # ═══════════════════════════════════════════════════════════════════════
    
    def get_total_earnings(self, algo: str = "sha256", coin: str = "BTC") -> Dict[str, float]:
        """Get total earnings summary
        
        Returns:
            {
                'today': float,
                'yesterday': float,
                'total_paid': float,
                'hashrate_15m': float,
                'hashrate_24h': float,
                'unit': str
            }
        """
        try:
            stats = self.get_statistic_list(algo)
            data = stats.get('data', {})
            
            today = 0.0
            yesterday = 0.0
            
            profit_today = data.get('profitToday', {})
            profit_yesterday = data.get('profitYesterday', {})
            
            if isinstance(profit_today, dict):
                today = float(profit_today.get(coin, 0))
            if isinstance(profit_yesterday, dict):
                yesterday = float(profit_yesterday.get(coin, 0))
            
            return {
                'today': today,
                'yesterday': yesterday,
                'hashrate_15m': float(data.get('fifteenMinHashRate', 0)),
                'hashrate_24h': float(data.get('dayHashRate', 0)),
                'valid_workers': int(data.get('validNum', 0)),
                'invalid_workers': int(data.get('invalidNum', 0)),
                'unit': data.get('unit', 'H/s'),
                'algo': algo,
                'coin': coin
            }
        except Exception as e:
            return {
                'error': str(e),
                'today': 0.0,
                'yesterday': 0.0,
                'hashrate_15m': 0.0,
                'hashrate_24h': 0.0,
                'valid_workers': 0,
                'invalid_workers': 0,
                'unit': 'H/s',
                'algo': algo,
                'coin': coin
            }
    
    def get_wallet_balance(self, asset: str = "BTC") -> float:
        """Get current wallet balance for mining payouts"""
        try:
            balance = self.client.get_free_balance(asset)
            return float(balance)
        except Exception:
            return 0.0
    
    def format_earnings_display(self, algo: str = "sha256", coin: str = "BTC") -> str:
        """Format earnings for display"""
        earnings = self.get_total_earnings(algo, coin)
        balance = self.get_wallet_balance(coin)
        
        if 'error' in earnings:
            return f"⚠️ Mining API Error: {earnings['error']}"
        
        return (
            f"💰 BINANCE POOL EARNINGS ({coin})\n"
            f"   Today:     {earnings['today']:.8f} {coin}\n"
            f"   Yesterday: {earnings['yesterday']:.8f} {coin}\n"
            f"   Hashrate:  {earnings['hashrate_15m']:.2f} {earnings['unit']} (15m)\n"
            f"   Workers:   {earnings['valid_workers']} active, {earnings['invalid_workers']} inactive\n"
            f"   Wallet:    {balance:.8f} {coin}"
        )

    # ══════════════════════════════════════════════════════════════════════
    # CRYPTO CONVERSION - Convert between crypto assets internally
    # ══════════════════════════════════════════════════════════════════════

    def get_available_pairs(self, base: str = None, quote: str = None) -> List[Dict[str, Any]]:
        """
        Get available trading pairs, optionally filtered by base or quote asset.
        
        Args:
            base: Filter by base asset (e.g., 'BTC', 'ETH')
            quote: Filter by quote asset (e.g., 'USDT', 'ETH')
            
        Returns:
            List of pairs with base, quote, and pair name
        """
        return self.client.get_available_pairs(base=base, quote=quote)

    def find_conversion_path(self, from_asset: str, to_asset: str) -> List[Dict[str, Any]]:
        """
        Find the best path to convert from one asset to another.
        
        Returns list of trades to execute:
        - Single trade if direct pair exists
        - Two trades via USDT/BTC if no direct pair
        
        Args:
            from_asset: Source asset (e.g., 'BTC')
            to_asset: Target asset (e.g., 'ETH')
            
        Returns:
            List of {pair, side, description} for each trade needed
        """
        return self.client.find_conversion_path(from_asset, to_asset)

    def convert_crypto(
        self,
        from_asset: str,
        to_asset: str,
        amount: float,
        use_quote_amount: bool = False
    ) -> Dict[str, Any]:
        """
        Convert one crypto asset to another within Binance.
        
        Automatically finds the best path:
        - Direct pair if available (e.g., ETHBTC)
        - Via USDT/BTC if no direct pair
        
        Args:
            from_asset: Source asset (e.g., 'BTC', 'ETH')
            to_asset: Target asset (e.g., 'ETH', 'SOL')
            amount: Amount of from_asset to convert
            use_quote_amount: If True, amount is in to_asset terms
            
        Returns:
            Conversion result with executed trades
        """
        return self.client.convert_crypto(
            from_asset,
            to_asset,
            amount,
            use_quote_amount=use_quote_amount,
        )

    def get_convertible_assets(self) -> Dict[str, List[str]]:
        """
        Get all assets that can be converted to/from.
        
        Returns:
            Dict mapping each asset to list of assets it can convert to
        """
        pairs = self.get_available_pairs()
        
        # Build conversion map
        conversions = {}
        
        for p in pairs:
            base = p["base"].upper()
            quote = p["quote"].upper()
            
            # Base can convert to quote (by selling)
            if base not in conversions:
                conversions[base] = set()
            conversions[base].add(quote)
            
            # Quote can convert to base (by buying)
            if quote not in conversions:
                conversions[quote] = set()
            conversions[quote].add(base)
        
        # Convert sets to sorted lists
        return {k: sorted(v) for k, v in conversions.items()}


# ═══════════════════════════════════════════════════════════════════════════════
# 🟡 SINGLETON PATTERN - Single Binance client instance across all modules
# ═══════════════════════════════════════════════════════════════════════════════
_binance_client_instance: Optional['BinanceClient'] = None
_binance_client_lock = None  # Lazy init to avoid import issues

def get_binance_client() -> Optional['BinanceClient']:
    """
    Get the singleton BinanceClient instance.
    
    This ensures only ONE BinanceClient exists across the entire application,
    preventing rate limit issues and connection pool exhaustion.
    
    Usage:
        from binance_client import get_binance_client
        client = get_binance_client()
        if client:
            balance = client.get_balance()
    
    Returns:
        BinanceClient instance, or None if credentials are missing
    """
    global _binance_client_instance, _binance_client_lock
    
    # Lazy init the lock
    if _binance_client_lock is None:
        import threading
        _binance_client_lock = threading.Lock()
    
    if _binance_client_instance is None:
        with _binance_client_lock:
            # Double-check locking pattern
            if _binance_client_instance is None:
                try:
                    _binance_client_instance = BinanceClient()
                    logging.getLogger(__name__).info("🟡 Binance singleton client initialized")
                except ValueError as e:
                    # Missing credentials
                    logging.getLogger(__name__).warning(f"⚠️ Binance client unavailable: {e}")
                    return None
                except Exception as e:
                    logging.getLogger(__name__).error(f"❌ Binance client init failed: {e}")
                    return None
    
    return _binance_client_instance


def safe_trade(symbol: str = None, side: str = "BUY") -> Dict[str, Any]:
    symbol = symbol or os.getenv("BINANCE_SYMBOL", "BTCUSDT")
    client = get_binance_client()
    if not client:
        return {"error": "Binance client not available"}
    if not client.ping():
        raise RuntimeError("Binance API not reachable")
    risk = load_risk_config()
    size = position_size_from_balance(client, symbol, risk["fraction"], risk["max_usdt"])
    if size < 5:  # require a minimal notional for meaningful trade
        return {"skipped": True, "reason": "Insufficient free USDT for minimum trade", "calculatedSize": size}
    order = client.place_market_order(symbol, side, round(size, 2))
    return {"orderResult": order, "risk": risk}

if __name__ == "__main__":
    try:
        result = safe_trade()
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"Error executing trade: {e}")
