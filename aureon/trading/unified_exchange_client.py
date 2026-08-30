import json
import logging
import math
import os
import time
from collections.abc import Collection, Mapping
from dataclasses import dataclass
from decimal import Decimal
from threading import Lock
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

from aureon.governance.legacy_economic_unity import (
    LegacyEconomicInvocation,
    LegacyEconomicUnityGateway,
)
from aureon.governance.legacy_unity_composition import (
    LegacyUnityCompositionHold,
    LegacyUnityIntentPlan,
    TrustedLegacyInvocationSupplier,
)

# Imports deferred to avoid circular dependencies
# from aureon.exchanges.kraken_client import KrakenClient, get_kraken_client
# from aureon.exchanges.binance_client import BinanceClient
# from aureon.exchanges.alpaca_client import AlpacaClient
# from aureon.exchanges.capital_client import CapitalClient

logger = logging.getLogger(__name__)
MAX_RECEIPT_AGE_SECONDS = 300.0


def _finite(value: Any, *, positive: bool = False, nonnegative: bool = False) -> Optional[float]:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    if positive and number <= 0.0:
        return None
    if nonnegative and number < 0.0:
        return None
    return number


def _no_data(exchange: str, symbol: str, reason: str) -> Dict[str, Any]:
    return {
        "exchange": str(exchange or "").lower(),
        "symbol": str(symbol or "").upper(),
        "status": "no_data",
        "data_status": "no_data",
        "truth_status": "no_data",
        "reason": reason,
        "source_id": None,
        "source_timestamp": None,
        "received_at": time.time(),
        "receipt_id": None,
        "generated_values": False,
        "actionable": False,
        "eligible_for_accounting": False,
        "eligible_for_learning": False,
    }


def _canonical_symbol(value: Any) -> str:
    symbol = str(value or "").upper().replace("/", "").replace("-", "")
    if symbol.startswith("XBT"):
        symbol = "BTC" + symbol[3:]
    if symbol.startswith("XDG"):
        symbol = "DOGE" + symbol[3:]
    return symbol


def _fresh_quote(receipt: Any, *, exchange: str, symbol: str) -> Optional[Dict[str, Any]]:
    if not isinstance(receipt, Mapping):
        return None
    now = time.time()
    price = _finite(receipt.get("price"), positive=True)
    bid = _finite(receipt.get("bid"), positive=True)
    ask = _finite(receipt.get("ask"), positive=True)
    source_timestamp = _finite(receipt.get("source_timestamp"), positive=True)
    received_at = _finite(receipt.get("received_at"), positive=True)
    source_id = str(receipt.get("source_id") or "").strip()
    receipt_id = str(receipt.get("receipt_id") or "").strip()
    if (
        receipt.get("data_status") != "live"
        or receipt.get("truth_status") not in {"real_observed", "real_derived"}
        or receipt.get("generated_values") is not False
        or not source_id.lower().startswith(str(exchange).lower())
        or not receipt_id
        or _canonical_symbol(receipt.get("symbol")) != _canonical_symbol(symbol)
        or price is None
        or bid is None
        or ask is None
        or ask < bid
        or source_timestamp is None
        or received_at is None
        or source_timestamp > received_at + 5.0
        or received_at > now + 5.0
        or now - source_timestamp > MAX_RECEIPT_AGE_SECONDS
        or now - received_at > MAX_RECEIPT_AGE_SECONDS
    ):
        return None
    return dict(receipt)


def _fresh_balance(receipt: Any, *, exchange: str, asset: str) -> Optional[float]:
    if not isinstance(receipt, Mapping):
        return None
    now = time.time()
    balances = receipt.get("balances")
    amount = _finite(
        balances.get(asset) if isinstance(balances, Mapping) else None,
        nonnegative=True,
    )
    source_timestamp = _finite(receipt.get("source_timestamp"), positive=True)
    received_at = _finite(receipt.get("received_at"), positive=True)
    source_id = str(receipt.get("source_id") or "").strip()
    receipt_id = str(receipt.get("receipt_id") or "").strip()
    if (
        receipt.get("data_status") != "live"
        or receipt.get("truth_status") not in {"real_observed", "real_derived"}
        or receipt.get("generated_values") is not False
        or receipt.get("action_eligible") is not True
        or not source_id.lower().startswith(str(exchange).lower())
        or not receipt_id
        or amount is None
        or source_timestamp is None
        or received_at is None
        or source_timestamp > received_at + 5.0
        or received_at > now + 5.0
        or now - source_timestamp > MAX_RECEIPT_AGE_SECONDS
        or now - received_at > MAX_RECEIPT_AGE_SECONDS
    ):
        return None
    return amount

class MultiExchangeClient:
    """
    Manages multiple exchange clients simultaneously.
    Aggregates data and routes orders.
    """
    def __init__(
        self,
        *,
        legacy_unity_gateway: LegacyEconomicUnityGateway | None = None,
        legacy_invocation_supplier: TrustedLegacyInvocationSupplier | None = None,
    ):
        if (legacy_unity_gateway is None) != (legacy_invocation_supplier is None):
            raise ValueError("legacy_unity_gateway_and_invocation_supplier_required_together")
        if legacy_unity_gateway is None:
            self.clients = {
                exchange: UnifiedExchangeClient(exchange)
                for exchange in ('kraken', 'binance', 'alpaca', 'capital')
            }
        else:
            self.clients = {
                exchange: UnifiedExchangeClient(
                    exchange,
                    legacy_unity_gateway=legacy_unity_gateway,
                    legacy_invocation_supplier=legacy_invocation_supplier,
                )
                for exchange in ('kraken', 'binance', 'alpaca', 'capital')
            }
        self.dry_run = any(c.dry_run for c in self.clients.values())
        logger.info(f"Initialized MultiExchangeClient with {list(self.clients.keys())}")

    def get_all_balances(self) -> Dict[str, Dict[str, float]]:
        """
        Get balances from all exchanges.
        Returns: {'kraken': {'BTC': 0.1}, 'binance': {'BTC': 0.2}}
        """
        return {
            name: client.get_all_balances()
            for name, client in self.clients.items()
        }

    def get_consolidated_equity(self, base_currency: str = 'USD') -> float:
        """Calculate total equity across all exchanges in base currency."""
        total = 0.0
        for name, client in self.clients.items():
            # This is an approximation. A real implementation would need
            # to convert each asset to base currency using that exchange's rates.
            # For now, we rely on the client's internal tracking or simple sum if possible.
            # But UnifiedExchangeClient doesn't have get_equity().
            # We'll iterate balances and convert.
            balances = client.get_all_balances()
            for asset, amount in balances.items():
                if asset == base_currency:
                    total += amount
                else:
                    total += client.convert_to_quote(asset, amount, base_currency)
        return total

    def get_24h_tickers(self) -> List[Dict[str, Any]]:
        """Get tickers from all exchanges, tagged with source."""
        all_tickers = []
        for name, client in self.clients.items():
            try:
                tickers = client.get_24h_tickers()
                for t in tickers:
                    t['source'] = name
                    # Ensure symbol is unique or tagged if needed, but 'source' handles it.
                all_tickers.extend(tickers)
            except Exception as e:
                # Log error but continue with other exchanges
                print(f"⚠️ Error getting tickers from {name}: {str(e)[:50]}")
        return all_tickers

    def normalize_symbol(self, exchange: str, symbol: str) -> str:
        """Normalize a canonical symbol to an exchange-specific one."""
        exchange = exchange.lower()
        s = symbol.upper().replace('/', '')
        base, quote = None, None
        # Split by common quotes
        for q in ["USDT", "USDC", "USD", "EUR", "GBP", "BTC", "XBT"]:
            if s.endswith(q):
                base = s[:-len(q)]
                quote = q
                break
        if not base or not quote:
            # Fallback try two-part with slash
            if '/' in symbol:
                base, quote = symbol.upper().split('/')
            else:
                return s

        if exchange == 'kraken':
            # BTC is XBT, prefer USD/USDC/USDT availability
            kbase = 'XBT' if base == 'BTC' else base
            kquote = quote
            if kquote == 'BTC': kquote = 'XBT'
            # Prefer USD first, then USDC, then USDT
            for q in [kquote, 'USD', 'USDC', 'USDT']:
                alt = f"{kbase}{q}"
                return alt
        if exchange == 'binance':
            # 🔧 Prefer a quote the user actually holds; UK accounts often hold GBP/EUR
            binance_client = self.clients.get('binance')
            usdc_bal = usdt_bal = gbp_bal = eur_bal = 0.0
            if binance_client:
                # Assign to real variables (locals() doesn't reliably set new names inside functions)
                try:
                    usdc_bal = float(binance_client.get_balance('USDC') or 0)
                except Exception:
                    usdc_bal = 0.0
                try:
                    usdt_bal = float(binance_client.get_balance('USDT') or 0)
                except Exception:
                    usdt_bal = 0.0
                try:
                    gbp_bal = float(binance_client.get_balance('GBP') or 0)
                except Exception:
                    gbp_bal = 0.0
                try:
                    eur_bal = float(binance_client.get_balance('EUR') or 0)
                except Exception:
                    eur_bal = 0.0

            if quote in ['USD', 'USDC', 'USDT', 'GBP', 'EUR']:
                # Priority: GBP (if held), EUR, USDC, USDT, fallback to original quote
                if gbp_bal > 1:
                    bquote = 'GBP'
                elif eur_bal > 1:
                    bquote = 'EUR'
                elif usdc_bal > usdt_bal and usdc_bal > 1:
                    bquote = 'USDC'
                elif usdt_bal > 1:
                    bquote = 'USDT'
                else:
                    bquote = quote if quote in ['GBP', 'EUR'] else 'USDT'
            else:
                bquote = quote
            return f"{base}{bquote}"
        if exchange == 'alpaca':
            return f"{base}/{quote}"
        if exchange == 'capital':
            # Capital uses simple epics like BTCUSD
            cquote = 'USD' if quote in ['USDT', 'USDC'] else quote
            return f"{base}{cquote}"
        return s

    def place_market_order(
        self,
        exchange: str,
        symbol: str,
        side: str,
        quantity=None,
        quote_qty=None,
        *,
        unity_invocation: LegacyEconomicInvocation | None = None,
        unity_plan: LegacyUnityIntentPlan | None = None,
    ) -> Dict[str, Any]:
        if exchange not in self.clients:
            logger.error(f"Unknown exchange: {exchange}")
            return {}
        return self.clients[exchange].place_market_order(
            symbol,
            side,
            quantity,
            quote_qty,
            unity_invocation=unity_invocation,
            unity_plan=unity_plan,
        )

    # ══════════════════════════════════════════════════════════════════════
    # ADVANCED ORDER TYPES - Limit, Stop-Loss, Take-Profit, Trailing Stop
    # ══════════════════════════════════════════════════════════════════════

    def place_limit_order(self, exchange: str, symbol: str, side: str, quantity, price, 
                          post_only: bool = False, time_in_force: str = "GTC", *,
                          unity_invocation: LegacyEconomicInvocation | None = None,
                          unity_plan: LegacyUnityIntentPlan | None = None) -> Dict[str, Any]:
        """Place a limit order on the specified exchange."""
        if exchange not in self.clients:
            logger.error(f"Unknown exchange: {exchange}")
            return {}
        return self.clients[exchange].place_limit_order(
            symbol, side, quantity, price, post_only, time_in_force,
            unity_invocation=unity_invocation,
            unity_plan=unity_plan,
        )

    def place_stop_loss_order(self, exchange: str, symbol: str, side: str, quantity, 
                              stop_price, limit_price=None, *,
                              unity_invocation: LegacyEconomicInvocation | None = None,
                              unity_plan: LegacyUnityIntentPlan | None = None) -> Dict[str, Any]:
        """Place a stop-loss order (server-side - executes even if bot offline)."""
        if exchange not in self.clients:
            logger.error(f"Unknown exchange: {exchange}")
            return {}
        return self.clients[exchange].place_stop_loss_order(
            symbol, side, quantity, stop_price, limit_price,
            unity_invocation=unity_invocation,
            unity_plan=unity_plan,
        )

    def place_take_profit_order(self, exchange: str, symbol: str, side: str, quantity,
                                take_profit_price, limit_price=None, *,
                                unity_invocation: LegacyEconomicInvocation | None = None,
                                unity_plan: LegacyUnityIntentPlan | None = None) -> Dict[str, Any]:
        """Place a take-profit order (server-side - executes even if bot offline)."""
        if exchange not in self.clients:
            logger.error(f"Unknown exchange: {exchange}")
            return {}
        return self.clients[exchange].place_take_profit_order(
            symbol, side, quantity, take_profit_price, limit_price,
            unity_invocation=unity_invocation,
            unity_plan=unity_plan,
        )

    def place_trailing_stop_order(self, exchange: str, symbol: str, side: str, quantity,
                                  trailing_offset, offset_type: str = "percent", *,
                                  unity_invocation: LegacyEconomicInvocation | None = None,
                                  unity_plan: LegacyUnityIntentPlan | None = None) -> Dict[str, Any]:
        """Place a trailing stop order (auto-adjusts as price moves)."""
        if exchange not in self.clients:
            logger.error(f"Unknown exchange: {exchange}")
            return {}
        return self.clients[exchange].place_trailing_stop_order(
            symbol, side, quantity, trailing_offset, offset_type,
            unity_invocation=unity_invocation,
            unity_plan=unity_plan,
        )

    def place_order_with_tp_sl(self, exchange: str, symbol: str, side: str, quantity,
                               order_type: str = "market", price=None,
                               take_profit=None, stop_loss=None, *,
                               unity_invocation: LegacyEconomicInvocation | None = None,
                               unity_plan: LegacyUnityIntentPlan | None = None) -> Dict[str, Any]:
        """Place an order with attached Take-Profit and/or Stop-Loss (conditional close)."""
        if exchange not in self.clients:
            logger.error(f"Unknown exchange: {exchange}")
            return {}
        return self.clients[exchange].place_order_with_tp_sl(
            symbol, side, quantity, order_type, price, take_profit, stop_loss,
            unity_invocation=unity_invocation,
            unity_plan=unity_plan,
        )

    def get_open_orders(self, exchange: str, symbol: str = None) -> List[Dict[str, Any]]:
        """Get all open orders on the specified exchange."""
        if exchange not in self.clients:
            return []
        return self.clients[exchange].get_open_orders(symbol)

    def cancel_order(
        self,
        exchange: str,
        order_id: str,
        *,
        unity_invocation: LegacyEconomicInvocation | None = None,
        unity_plan: LegacyUnityIntentPlan | None = None,
    ) -> Dict[str, Any]:
        """Cancel a specific order."""
        if exchange not in self.clients:
            return {}
        return self.clients[exchange].cancel_order(
            order_id,
            unity_invocation=unity_invocation,
            unity_plan=unity_plan,
        )

    def cancel_all_orders(
        self,
        exchange: str,
        symbol: str = None,
        *,
        unity_invocation: LegacyEconomicInvocation | None = None,
        unity_plan: LegacyUnityIntentPlan | None = None,
    ) -> Dict[str, Any]:
        """Cancel all open orders, optionally filtered by symbol."""
        if exchange not in self.clients:
            return {}
        return self.clients[exchange].cancel_all_orders(
            symbol,
            unity_invocation=unity_invocation,
            unity_plan=unity_plan,
        )

    def get_ticker(self, exchange: str, symbol: str) -> Dict[str, float]:
        if exchange not in self.clients:
            return {'price': 0.0, 'bid': 0.0, 'ask': 0.0}
        return self.clients[exchange].get_ticker(symbol)
    
    def convert_to_quote(self, exchange: str, asset: str, amount: float, quote: str) -> float:
        if exchange not in self.clients:
            return 0.0
        return self.clients[exchange].convert_to_quote(asset, amount, quote)

    # ══════════════════════════════════════════════════════════════════════
    # CRYPTO CONVERSION - Convert between assets on any exchange
    # ══════════════════════════════════════════════════════════════════════

    def get_available_pairs(self, exchange: str, base: str = None, quote: str = None) -> List[Dict[str, Any]]:
        """Get available trading pairs on an exchange."""
        if exchange not in self.clients:
            return []
        if hasattr(self.clients[exchange], 'get_available_pairs'):
            return self.clients[exchange].get_available_pairs(base, quote)
        return []

    def find_conversion_path(self, exchange: str, from_asset: str, to_asset: str) -> List[Dict[str, Any]]:
        """Find the conversion path between two assets."""
        if exchange not in self.clients:
            return []
        if hasattr(self.clients[exchange], 'find_conversion_path'):
            return self.clients[exchange].find_conversion_path(from_asset, to_asset)
        return []

    def convert_crypto(self, exchange: str, from_asset: str, to_asset: str, amount: float) -> Dict[str, Any]:
        """Convert one crypto asset to another on the specified exchange."""
        if exchange not in self.clients:
            return {"error": f"Unknown exchange: {exchange}"}
        if hasattr(self.clients[exchange], 'convert_crypto'):
            return self.clients[exchange].convert_crypto(from_asset, to_asset, amount)
        return {"error": f"Exchange {exchange} doesn't support crypto conversion"}

    def get_convertible_assets(self, exchange: str) -> Dict[str, List[str]]:
        """Get all assets that can be converted on an exchange."""
        if exchange not in self.clients:
            return {}
        if hasattr(self.clients[exchange], 'get_convertible_assets'):
            return self.clients[exchange].get_convertible_assets()
        return {}

    def get_all_convertible_assets(self) -> Dict[str, Dict[str, List[str]]]:
        """Get convertible assets across all exchanges."""
        result = {}
        for exchange in self.clients:
            assets = self.get_convertible_assets(exchange)
            if assets:
                result[exchange] = assets
        return result

    # ══════════════════════════════════════════════════════════════════════
    # MARGIN TRADING - Leveraged positions (Kraken supported)
    # ══════════════════════════════════════════════════════════════════════

    def get_trade_balance(self, exchange: str, asset: str = "ZUSD") -> Dict[str, Any]:
        """Get margin/trade balance from the specified exchange."""
        if exchange not in self.clients:
            return {}
        return self.clients[exchange].get_trade_balance(asset)

    def get_open_margin_positions(self, exchange: str, do_calcs: bool = True) -> List[Dict[str, Any]]:
        """Get all open margin positions on the specified exchange."""
        if exchange not in self.clients:
            return []
        return self.clients[exchange].get_open_margin_positions(do_calcs)

    def get_margin_pairs(self, exchange: str) -> List[Dict[str, Any]]:
        """Get pairs that support margin trading on the specified exchange."""
        if exchange not in self.clients:
            return []
        return self.clients[exchange].get_margin_pairs()

    def get_pair_leverage(self, exchange: str, symbol: str) -> Dict[str, Any]:
        """Get available leverage for a specific pair on the specified exchange."""
        if exchange not in self.clients:
            return {}
        return self.clients[exchange].get_pair_leverage(symbol)

    def place_margin_order(self, exchange: str, symbol: str, side: str, quantity,
                           leverage, order_type: str = "market", price=None,
                           take_profit=None, stop_loss=None,
                           post_only: bool = False, *,
                           unity_invocation: LegacyEconomicInvocation | None = None,
                           unity_plan: LegacyUnityIntentPlan | None = None) -> Dict[str, Any]:
        """Place a margin (leveraged) order on the specified exchange."""
        if exchange not in self.clients:
            logger.error(f"Unknown exchange: {exchange}")
            return {}
        return self.clients[exchange].place_margin_order(
            symbol, side, quantity, leverage,
            order_type=order_type, price=price,
            take_profit=take_profit, stop_loss=stop_loss,
            post_only=post_only,
            unity_invocation=unity_invocation,
            unity_plan=unity_plan,
        )

    def close_margin_position(self, exchange: str, symbol: str, side: str,
                               volume=None, order_type: str = "market",
                               price=None, leverage=None, *,
                               unity_invocation: LegacyEconomicInvocation | None = None,
                               unity_plan: LegacyUnityIntentPlan | None = None) -> Dict[str, Any]:
        """Close an open margin position on the specified exchange."""
        if exchange not in self.clients:
            return {}
        return self.clients[exchange].close_margin_position(
            symbol, side, volume=volume,
            order_type=order_type, price=price, leverage=leverage,
            unity_invocation=unity_invocation,
            unity_plan=unity_plan,
        )

        def normalize_symbol(self, exchange: str, symbol: str) -> str:
            """Normalize canonical symbols to exchange-specific formats.
            - Kraken: BTC→XBT, prefer USD/USDC/USDT variants
            - Binance: prefer USDT quote
            - Capital: use epic as-is (USD pairs)
            """
            s = symbol.upper()
            if exchange == 'kraken':
                # BTC/XBT and quote fallbacks
                if s.startswith('BTC'):
                    s = 'XBT' + s[3:]
                # Kraken commonly lists USD/USDT/USDC; try USD first
                for q in ['USD', 'USDC', 'USDT']:
                    if s.endswith(q):
                        base = s[:-len(q)]
                        s = base + q
                        break
                return s
            if exchange == 'binance':
                # Prefer USDT on Binance
                for q in ['USD', 'USDC']:
                    if s.endswith(q):
                        base = s[:-len(q)]
                        s = base + 'USDT'
                        break
                return s
            if exchange == 'capital':
                # Use epic (symbol) as is; Capital.com search expects names like BTCUSD
                return s
            return s


@runtime_checkable
class TrustedUnifiedEcosystemPlanSupplier(Protocol):
    """Composition-root supplier for exact legacy-unity order plans."""

    supplier_id: str

    def supply_unity_plan(
        self,
        request: "UnifiedEcosystemMutationRequest",
    ) -> LegacyUnityIntentPlan:
        """Return one provider-exact, evidence-addressed plan."""


def _canonical_amount(value: Any, label: str) -> str | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError(f"{label}_must_be_positive_finite_decimal")
    try:
        amount = Decimal(str(value))
    except Exception as exc:
        raise ValueError(f"{label}_must_be_positive_finite_decimal") from exc
    if not amount.is_finite() or amount <= 0:
        raise ValueError(f"{label}_must_be_positive_finite_decimal")
    result = format(amount, "f")
    if "." in result:
        result = result.rstrip("0").rstrip(".")
    return result


@dataclass(frozen=True, slots=True)
class UnifiedEcosystemMutationRequest:
    """Immutable high-level order shape presented to the trusted plan supplier."""

    exchange: str
    operation: str
    purpose: str
    symbol: str
    side: str
    order_type: str
    quantity: str | None
    quote_quantity: str | None
    limit_price: str | None
    stop_price: str | None
    take_profit: str | None
    reduce_only: bool
    provider_order_id: str | None = None

    def __post_init__(self) -> None:
        if self.exchange not in {"kraken", "binance", "alpaca", "capital"}:
            raise ValueError("supported_exchange_required")
        if not self.operation or self.operation != self.operation.upper():
            raise ValueError("canonical_mutation_operation_required")
        if not self.purpose or self.purpose != self.purpose.upper():
            raise ValueError("canonical_mutation_purpose_required")
        if not self.symbol.strip():
            raise ValueError("canonical_mutation_symbol_required")
        if not self.side or self.side != self.side.upper():
            raise ValueError("canonical_mutation_side_required")
        if not self.order_type or self.order_type != self.order_type.upper():
            raise ValueError("canonical_mutation_order_type_required")
        if type(self.reduce_only) is not bool:
            raise ValueError("reduce_only_must_be_boolean")
        for name in (
            "quantity",
            "quote_quantity",
            "limit_price",
            "stop_price",
            "take_profit",
        ):
            value = getattr(self, name)
            if value is not None and _canonical_amount(value, name) != value:
                raise ValueError(f"canonical_{name}_required")
        if self.provider_order_id is not None and not self.provider_order_id.strip():
            raise ValueError("provider_order_id_must_be_nonblank")

    @classmethod
    def build(
        cls,
        *,
        exchange: str,
        operation: str,
        purpose: str,
        symbol: str,
        side: str,
        order_type: str,
        quantity: Any = None,
        quote_quantity: Any = None,
        limit_price: Any = None,
        stop_price: Any = None,
        take_profit: Any = None,
        reduce_only: bool,
        provider_order_id: str | None = None,
    ) -> "UnifiedEcosystemMutationRequest":
        return cls(
            exchange=str(exchange or "").strip().lower(),
            operation=str(operation or "").strip().upper(),
            purpose=str(purpose or "").strip().upper(),
            symbol=str(symbol or "").strip().upper(),
            side=str(side or "").strip().upper(),
            order_type=str(order_type or "").strip().upper(),
            quantity=_canonical_amount(quantity, "quantity"),
            quote_quantity=_canonical_amount(quote_quantity, "quote_quantity"),
            limit_price=_canonical_amount(limit_price, "limit_price"),
            stop_price=_canonical_amount(stop_price, "stop_price"),
            take_profit=_canonical_amount(take_profit, "take_profit"),
            reduce_only=reduce_only,
            provider_order_id=(
                None
                if provider_order_id is None
                else str(provider_order_id).strip()
            ),
        )


_ORDER_PATHS = {
    "kraken": ("POST", "/0/private/AddOrder"),
    "binance": ("POST", "/api/v3/order"),
    "alpaca": ("POST", "/v2/orders"),
    "capital": ("POST", "/positions"),
}
_CANCEL_ALL_PATHS = {
    "kraken": ("POST", "/0/private/CancelAll"),
    "alpaca": ("DELETE", "/v2/orders"),
}


def _plan_route_matches(
    plan: LegacyUnityIntentPlan,
    request: UnifiedEcosystemMutationRequest,
) -> bool:
    if request.operation == "CANCEL_ORDER":
        if request.exchange == "kraken":
            expected_route = ("POST", "/0/private/CancelOrder")
        elif request.exchange == "alpaca" and request.provider_order_id:
            expected_route = (
                "DELETE",
                f"/v2/orders/{request.provider_order_id}",
            )
        else:
            return False
    elif request.operation == "CANCEL_ALL_ORDERS":
        expected_route = _CANCEL_ALL_PATHS.get(request.exchange)
    else:
        expected_route = _ORDER_PATHS.get(request.exchange)
    return expected_route is not None and (plan.method, plan.path) == expected_route


def _cancel_body_matches(
    plan: LegacyUnityIntentPlan,
    request: UnifiedEcosystemMutationRequest,
) -> bool:
    if request.operation != "CANCEL_ORDER":
        return True
    if request.exchange == "alpaca":
        return True
    try:
        body = json.loads(plan.body_json)
    except (TypeError, json.JSONDecodeError):
        return False
    return str(body.get("txid") or "") == request.provider_order_id


class GovernedMultiExchangeClient(MultiExchangeClient):
    """Preserve the legacy API while requiring one exact plan per mutation.

    The wrapped client must already contain the canonical unity gateway and the
    HNC/Auris invocation supplier.  This facade adds the missing strategy-level
    plan seat, validates it against the actual call, and burns the plan before
    dispatch so an ambiguous provider outcome can never be retried.
    """

    def __init__(
        self,
        *,
        base_client: MultiExchangeClient,
        plan_supplier: TrustedUnifiedEcosystemPlanSupplier,
        trusted_plan_supplier_ids: Collection[str],
    ) -> None:
        if not isinstance(base_client, MultiExchangeClient):
            raise TypeError("canonical_multi_exchange_client_required")
        if not isinstance(plan_supplier, TrustedUnifiedEcosystemPlanSupplier):
            raise TypeError("trusted_unified_ecosystem_plan_supplier_required")
        supplier_id = str(plan_supplier.supplier_id or "").strip()
        allowlist = {
            str(item or "").strip().casefold()
            for item in trusted_plan_supplier_ids
            if str(item or "").strip()
        }
        if not allowlist or supplier_id.casefold() not in allowlist:
            raise ValueError("unified_ecosystem_plan_supplier_not_allowlisted")
        clients = getattr(base_client, "clients", None)
        if not isinstance(clients, Mapping) or not clients:
            raise ValueError("canonical_unified_exchange_clients_required")
        gateway_ids = {
            id(getattr(client, "_legacy_unity_gateway", None))
            for client in clients.values()
        }
        invocation_supplier_ids = {
            id(getattr(client, "_legacy_invocation_supplier", None))
            for client in clients.values()
        }
        if (
            len(gateway_ids) != 1
            or len(invocation_supplier_ids) != 1
            or id(None) in gateway_ids
            or id(None) in invocation_supplier_ids
        ):
            raise ValueError("canonical_unified_exchange_unity_composition_required")
        self.clients = clients
        self.dry_run = bool(getattr(base_client, "dry_run", True))
        self._plan_supplier = plan_supplier
        self._consumed_plan_digests: set[str] = set()
        self._plan_lock = Lock()

    @staticmethod
    def _plan_matches(
        plan: LegacyUnityIntentPlan,
        request: UnifiedEcosystemMutationRequest,
    ) -> bool:
        return (
            plan.venue == request.exchange
            and plan.operation == request.operation
            and plan.purpose == request.purpose
            and plan.symbol == request.symbol
            and plan.side == request.side
            and plan.order_type == request.order_type
            and plan.quantity == request.quantity
            and plan.quote_quantity == request.quote_quantity
            and plan.limit_price == request.limit_price
            and plan.stop_price == request.stop_price
            and plan.take_profit == request.take_profit
            and plan.reduce_only is request.reduce_only
            and _plan_route_matches(plan, request)
            and _cancel_body_matches(plan, request)
        )

    def _execute_governed(
        self,
        request: UnifiedEcosystemMutationRequest,
        dispatch,
    ) -> Dict[str, Any]:
        try:
            plan = self._plan_supplier.supply_unity_plan(request)
        except Exception:
            return _no_data(
                request.exchange,
                request.symbol,
                "trusted_unified_ecosystem_plan_resolution_failed",
            )
        if not isinstance(plan, LegacyUnityIntentPlan) or not self._plan_matches(
            plan,
            request,
        ):
            return _no_data(
                request.exchange,
                request.symbol,
                "exact_unified_ecosystem_plan_required",
            )
        with self._plan_lock:
            if plan.plan_digest in self._consumed_plan_digests:
                return _no_data(
                    request.exchange,
                    request.symbol,
                    "unified_ecosystem_plan_replay_blocked",
                )
            self._consumed_plan_digests.add(plan.plan_digest)
        try:
            result = dispatch(plan)
        except Exception:
            return _no_data(
                request.exchange,
                request.symbol,
                "unified_ecosystem_dispatch_outcome_ambiguous",
            )
        if not isinstance(result, Mapping):
            return _no_data(
                request.exchange,
                request.symbol,
                "unified_ecosystem_dispatch_receipt_required",
            )
        return dict(result)

    @staticmethod
    def _reject_caller_authority(
        exchange: str,
        symbol: str,
        invocation: LegacyEconomicInvocation | None,
        plan: LegacyUnityIntentPlan | None,
    ) -> Dict[str, Any] | None:
        if invocation is None and plan is None:
            return None
        return _no_data(
            exchange,
            symbol,
            "caller_supplied_unity_authority_forbidden",
        )

    def place_market_order(
        self,
        exchange: str,
        symbol: str,
        side: str,
        quantity=None,
        quote_qty=None,
        *,
        unity_invocation: LegacyEconomicInvocation | None = None,
        unity_plan: LegacyUnityIntentPlan | None = None,
        unity_purpose: str | None = None,
    ) -> Dict[str, Any]:
        rejected = self._reject_caller_authority(
            exchange,
            symbol,
            unity_invocation,
            unity_plan,
        )
        if rejected is not None:
            return rejected
        side_upper = str(side or "").strip().upper()
        purpose = str(
            unity_purpose or ("ENTRY" if side_upper == "BUY" else "EXIT")
        ).strip().upper()
        try:
            request = UnifiedEcosystemMutationRequest.build(
                exchange=exchange,
                operation="MARKET_ORDER",
                purpose=purpose,
                symbol=symbol,
                side=side_upper,
                order_type="MARKET",
                quantity=quantity,
                quote_quantity=quote_qty,
                reduce_only=side_upper == "SELL",
            )
        except ValueError as exc:
            return _no_data(exchange, symbol, str(exc))
        if request.exchange in {"alpaca", "capital"} and (
            request.quantity is None or request.quote_quantity is not None
        ):
            return _no_data(
                exchange,
                symbol,
                "provider_exact_base_quantity_required_before_governance",
            )
        return self._execute_governed(
            request,
            lambda exact_plan: MultiExchangeClient.place_market_order(
                self,
                exchange,
                symbol,
                side,
                quantity=quantity,
                quote_qty=quote_qty,
                unity_plan=exact_plan,
            ),
        )

    def place_limit_order(
        self,
        exchange: str,
        symbol: str,
        side: str,
        quantity,
        price,
        post_only: bool = False,
        time_in_force: str = "GTC",
        *,
        unity_invocation: LegacyEconomicInvocation | None = None,
        unity_plan: LegacyUnityIntentPlan | None = None,
        unity_purpose: str | None = None,
    ) -> Dict[str, Any]:
        rejected = self._reject_caller_authority(
            exchange, symbol, unity_invocation, unity_plan
        )
        if rejected is not None:
            return rejected
        side_upper = str(side or "").strip().upper()
        purpose = str(
            unity_purpose or ("ENTRY" if side_upper == "BUY" else "EXIT")
        ).strip().upper()
        try:
            request = UnifiedEcosystemMutationRequest.build(
                exchange=exchange,
                operation="LIMIT_ORDER",
                purpose=purpose,
                symbol=symbol,
                side=side_upper,
                order_type="LIMIT",
                quantity=quantity,
                limit_price=price,
                reduce_only=side_upper == "SELL",
            )
        except ValueError as exc:
            return _no_data(exchange, symbol, str(exc))
        return self._execute_governed(
            request,
            lambda exact_plan: MultiExchangeClient.place_limit_order(
                self,
                exchange,
                symbol,
                side,
                quantity,
                price,
                post_only,
                time_in_force,
                unity_plan=exact_plan,
            ),
        )

    def place_stop_loss_order(
        self,
        exchange: str,
        symbol: str,
        side: str,
        quantity,
        stop_price,
        limit_price=None,
        *,
        unity_invocation: LegacyEconomicInvocation | None = None,
        unity_plan: LegacyUnityIntentPlan | None = None,
    ) -> Dict[str, Any]:
        rejected = self._reject_caller_authority(
            exchange, symbol, unity_invocation, unity_plan
        )
        if rejected is not None:
            return rejected
        try:
            request = UnifiedEcosystemMutationRequest.build(
                exchange=exchange,
                operation="STOP_ORDER",
                purpose="CONTAINMENT",
                symbol=symbol,
                side=side,
                order_type="STOP_LOSS",
                quantity=quantity,
                limit_price=limit_price,
                stop_price=stop_price,
                reduce_only=True,
            )
        except ValueError as exc:
            return _no_data(exchange, symbol, str(exc))
        return self._execute_governed(
            request,
            lambda exact_plan: MultiExchangeClient.place_stop_loss_order(
                self,
                exchange,
                symbol,
                side,
                quantity,
                stop_price,
                limit_price,
                unity_plan=exact_plan,
            ),
        )

    def place_take_profit_order(
        self,
        exchange: str,
        symbol: str,
        side: str,
        quantity,
        take_profit_price,
        limit_price=None,
        *,
        unity_invocation: LegacyEconomicInvocation | None = None,
        unity_plan: LegacyUnityIntentPlan | None = None,
    ) -> Dict[str, Any]:
        rejected = self._reject_caller_authority(
            exchange, symbol, unity_invocation, unity_plan
        )
        if rejected is not None:
            return rejected
        try:
            request = UnifiedEcosystemMutationRequest.build(
                exchange=exchange,
                operation="TAKE_PROFIT_ORDER",
                purpose="CONTAINMENT",
                symbol=symbol,
                side=side,
                order_type="TAKE_PROFIT",
                quantity=quantity,
                limit_price=limit_price,
                take_profit=take_profit_price,
                reduce_only=True,
            )
        except ValueError as exc:
            return _no_data(exchange, symbol, str(exc))
        return self._execute_governed(
            request,
            lambda exact_plan: MultiExchangeClient.place_take_profit_order(
                self,
                exchange,
                symbol,
                side,
                quantity,
                take_profit_price,
                limit_price,
                unity_plan=exact_plan,
            ),
        )

    def place_trailing_stop_order(
        self,
        exchange: str,
        symbol: str,
        side: str,
        quantity,
        trailing_offset,
        offset_type: str = "percent",
        *,
        unity_invocation: LegacyEconomicInvocation | None = None,
        unity_plan: LegacyUnityIntentPlan | None = None,
    ) -> Dict[str, Any]:
        rejected = self._reject_caller_authority(
            exchange, symbol, unity_invocation, unity_plan
        )
        if rejected is not None:
            return rejected
        try:
            request = UnifiedEcosystemMutationRequest.build(
                exchange=exchange,
                operation="TRAILING_STOP_ORDER",
                purpose="CONTAINMENT",
                symbol=symbol,
                side=side,
                order_type="TRAILING_STOP",
                quantity=quantity,
                stop_price=trailing_offset,
                reduce_only=True,
            )
        except ValueError as exc:
            return _no_data(exchange, symbol, str(exc))
        return self._execute_governed(
            request,
            lambda exact_plan: MultiExchangeClient.place_trailing_stop_order(
                self,
                exchange,
                symbol,
                side,
                quantity,
                trailing_offset,
                offset_type,
                unity_plan=exact_plan,
            ),
        )

    def place_order_with_tp_sl(
        self,
        exchange: str,
        symbol: str,
        side: str,
        quantity,
        order_type: str = "market",
        price=None,
        take_profit=None,
        stop_loss=None,
        *,
        unity_invocation: LegacyEconomicInvocation | None = None,
        unity_plan: LegacyUnityIntentPlan | None = None,
        unity_purpose: str | None = None,
    ) -> Dict[str, Any]:
        rejected = self._reject_caller_authority(
            exchange, symbol, unity_invocation, unity_plan
        )
        if rejected is not None:
            return rejected
        side_upper = str(side or "").strip().upper()
        purpose = str(
            unity_purpose or ("ENTRY" if side_upper == "BUY" else "EXIT")
        ).strip().upper()
        try:
            request = UnifiedEcosystemMutationRequest.build(
                exchange=exchange,
                operation="ATOMIC_TP_SL_ORDER",
                purpose=purpose,
                symbol=symbol,
                side=side_upper,
                order_type=order_type,
                quantity=quantity,
                limit_price=price,
                stop_price=stop_loss,
                take_profit=take_profit,
                reduce_only=side_upper == "SELL",
            )
        except ValueError as exc:
            return _no_data(exchange, symbol, str(exc))
        return self._execute_governed(
            request,
            lambda exact_plan: MultiExchangeClient.place_order_with_tp_sl(
                self,
                exchange,
                symbol,
                side,
                quantity,
                order_type,
                price,
                take_profit,
                stop_loss,
                unity_plan=exact_plan,
            ),
        )

    def cancel_order(
        self,
        exchange: str,
        order_id: str,
        *,
        unity_invocation: LegacyEconomicInvocation | None = None,
        unity_plan: LegacyUnityIntentPlan | None = None,
    ) -> Dict[str, Any]:
        rejected = self._reject_caller_authority(
            exchange, order_id, unity_invocation, unity_plan
        )
        if rejected is not None:
            return rejected
        try:
            request = UnifiedEcosystemMutationRequest.build(
                exchange=exchange,
                operation="CANCEL_ORDER",
                purpose="CANCEL_PROTECTION",
                symbol=order_id,
                side="CANCEL",
                order_type="CANCEL",
                reduce_only=True,
                provider_order_id=order_id,
            )
        except ValueError as exc:
            return _no_data(exchange, order_id, str(exc))
        return self._execute_governed(
            request,
            lambda exact_plan: MultiExchangeClient.cancel_order(
                self,
                exchange,
                order_id,
                unity_plan=exact_plan,
            ),
        )

    def cancel_all_orders(
        self,
        exchange: str,
        symbol: str | None = None,
        *,
        unity_invocation: LegacyEconomicInvocation | None = None,
        unity_plan: LegacyUnityIntentPlan | None = None,
    ) -> Dict[str, Any]:
        request_symbol = str(symbol or "ALL_OPEN_ORDERS").strip().upper()
        rejected = self._reject_caller_authority(
            exchange, request_symbol, unity_invocation, unity_plan
        )
        if rejected is not None:
            return rejected
        try:
            request = UnifiedEcosystemMutationRequest.build(
                exchange=exchange,
                operation="CANCEL_ALL_ORDERS",
                purpose="CANCEL_PROTECTION",
                symbol=request_symbol,
                side="CANCEL",
                order_type="CANCEL_ALL",
                reduce_only=True,
            )
        except ValueError as exc:
            return _no_data(exchange, request_symbol, str(exc))
        return self._execute_governed(
            request,
            lambda exact_plan: MultiExchangeClient.cancel_all_orders(
                self,
                exchange,
                symbol,
                unity_plan=exact_plan,
            ),
        )

    def place_margin_order(
        self,
        exchange: str,
        symbol: str,
        side: str,
        quantity,
        leverage: int = 2,
        order_type: str = "market",
        price=None,
        take_profit=None,
        stop_loss=None,
        post_only: bool = False,
        *,
        unity_invocation: LegacyEconomicInvocation | None = None,
        unity_plan: LegacyUnityIntentPlan | None = None,
        unity_purpose: str = "ENTRY",
        unity_reduce_only: bool = False,
    ) -> Dict[str, Any]:
        rejected = self._reject_caller_authority(
            exchange, symbol, unity_invocation, unity_plan
        )
        if rejected is not None:
            return rejected
        try:
            request = UnifiedEcosystemMutationRequest.build(
                exchange=exchange,
                operation="MARGIN_ORDER",
                purpose=unity_purpose,
                symbol=symbol,
                side=side,
                order_type=order_type,
                quantity=quantity,
                limit_price=price,
                stop_price=stop_loss,
                take_profit=take_profit,
                reduce_only=unity_reduce_only,
            )
        except ValueError as exc:
            return _no_data(exchange, symbol, str(exc))
        return self._execute_governed(
            request,
            lambda exact_plan: MultiExchangeClient.place_margin_order(
                self,
                exchange,
                symbol,
                side,
                quantity,
                leverage,
                order_type=order_type,
                price=price,
                take_profit=take_profit,
                stop_loss=stop_loss,
                post_only=post_only,
                unity_plan=exact_plan,
            ),
        )

    def close_margin_position(
        self,
        exchange: str,
        symbol: str,
        side: str,
        volume=None,
        order_type: str = "market",
        price=None,
        leverage=None,
        *,
        unity_invocation: LegacyEconomicInvocation | None = None,
        unity_plan: LegacyUnityIntentPlan | None = None,
    ) -> Dict[str, Any]:
        rejected = self._reject_caller_authority(
            exchange, symbol, unity_invocation, unity_plan
        )
        if rejected is not None:
            return rejected
        try:
            request = UnifiedEcosystemMutationRequest.build(
                exchange=exchange,
                operation="MARGIN_CLOSE",
                purpose="CONTAINMENT",
                symbol=symbol,
                side=side,
                order_type=order_type,
                quantity=volume,
                limit_price=price,
                reduce_only=True,
            )
        except ValueError as exc:
            return _no_data(exchange, symbol, str(exc))
        return self._execute_governed(
            request,
            lambda exact_plan: MultiExchangeClient.close_margin_position(
                self,
                exchange,
                symbol,
                side,
                volume=volume,
                order_type=order_type,
                price=price,
                leverage=leverage,
                unity_plan=exact_plan,
            ),
        )


class UnifiedExchangeClient:
    """
    Unified interface for Kraken and Binance exchanges.
    Allows the Aureon ecosystem to trade on either platform seamlessly.
    """
    
    def __init__(
        self,
        exchange_id: str = "kraken",
        *,
        legacy_unity_gateway: LegacyEconomicUnityGateway | None = None,
        legacy_invocation_supplier: TrustedLegacyInvocationSupplier | None = None,
    ):
        self.exchange_id = exchange_id.lower()
        self.client = None
        self.available = False
        self.dry_run = False
        if legacy_unity_gateway is not None and not isinstance(
            legacy_unity_gateway,
            LegacyEconomicUnityGateway,
        ):
            raise TypeError("legacy_economic_unity_gateway_required")
        if legacy_invocation_supplier is not None and not isinstance(
            legacy_invocation_supplier,
            TrustedLegacyInvocationSupplier,
        ):
            raise TypeError("trusted_legacy_invocation_supplier_required")
        if (legacy_unity_gateway is None) != (legacy_invocation_supplier is None):
            raise ValueError("legacy_unity_gateway_and_invocation_supplier_required_together")
        self._legacy_unity_gateway = legacy_unity_gateway
        self._legacy_invocation_supplier = legacy_invocation_supplier
        # Kraken has per-pair minimums; apply a conservative global floor to avoid spam errors
        self.kraken_min_notional = float(os.getenv("KRAKEN_MIN_NOTIONAL", "5"))

        if self.exchange_id not in {"kraken", "binance", "alpaca", "capital"}:
            raise ValueError(f"Unsupported exchange: {exchange_id}")

        try:
            if self.exchange_id == "kraken":
                from aureon.exchanges.kraken_client import KrakenClient, get_kraken_client
                self.client = get_kraken_client()
            elif self.exchange_id == "binance":
                from aureon.exchanges.binance_client import BinanceClient, get_binance_client
                self.client = get_binance_client()
            elif self.exchange_id == "alpaca":
                from aureon.exchanges.alpaca_client import AlpacaClient
                self.client = AlpacaClient()
            elif self.exchange_id == "capital":
                from aureon.exchanges.capital_client import CapitalClient
                self.client = CapitalClient()
        except Exception as exc:
            logger.warning(f"{self.exchange_id} client unavailable: {exc}")
            self.client = None

        if self.client is None:
            self.dry_run = True
            logger.warning(f"{self.exchange_id} client unavailable; using disabled dry-run wrapper")
        else:
            self.available = True
            self.dry_run = bool(getattr(self.client, "dry_run", False))
            
        logger.info(f"Initialized UnifiedExchangeClient for {self.exchange_id} (Dry Run: {self.dry_run})")

    def _execute_optional_legacy_unity(
        self,
        invocation: LegacyEconomicInvocation | None,
        *,
        plan: LegacyUnityIntentPlan | None = None,
        transport,
    ) -> Dict[str, Any]:
        """Use the unity gateway when installed; otherwise retain compatibility.

        Live provider clients independently enforce their raw transport guard,
        so the compatibility branch cannot bypass a guarded provider boundary.
        """

        gateway = self._legacy_unity_gateway
        supplier = self._legacy_invocation_supplier
        if invocation is not None and plan is not None:
            return _no_data(
                self.exchange_id,
                plan.symbol,
                "exactly_one_legacy_unity_invocation_or_plan_required",
            )
        if invocation is None and plan is not None:
            if supplier is None:
                return _no_data(
                    self.exchange_id,
                    plan.symbol,
                    "trusted_legacy_invocation_supplier_required",
                )
            try:
                invocation = supplier.supply_legacy_invocation(plan)
            except LegacyUnityCompositionHold as exc:
                return _no_data(self.exchange_id, plan.symbol, exc.reason_code)
            except Exception:
                return _no_data(
                    self.exchange_id,
                    plan.symbol,
                    "trusted_legacy_invocation_resolution_failed",
                )
        if gateway is None and invocation is None:
            return _no_data(
                self.exchange_id,
                plan.symbol if plan is not None else "",
                "canonical_legacy_unity_composition_required",
            )
        if gateway is None:
            return _no_data(
                self.exchange_id,
                invocation.intent.symbol if invocation is not None else "",
                "legacy_unity_gateway_required",
            )
        if invocation is None:
            return _no_data(
                self.exchange_id,
                "",
                "hnc_auris_legacy_unity_invocation_required",
            )
        outcome = gateway.execute(invocation, transport=transport)
        receipt = dict(outcome.receipt)
        if outcome.status == "EXECUTED":
            if isinstance(outcome.provider_result, Mapping):
                result = dict(outcome.provider_result)
                result["aureon_legacy_unity_receipt"] = receipt
                return result
            return {
                "status": "executed",
                "provider_result": outcome.provider_result,
                "aureon_legacy_unity_receipt": receipt,
            }
        if outcome.status == "AMBIGUOUS":
            return {
                "status": "pending_reconciliation",
                "reason": receipt["reason"],
                "aureon_legacy_unity_receipt": receipt,
            }
        return {
            "status": "not_submitted",
            "reason": receipt["reason"],
            "rejected": True,
            "aureon_legacy_unity_receipt": receipt,
        }

    def normalize(self, symbol: str) -> str:
        """Normalize a canonical symbol to this client's exchange format."""
        mec = MultiExchangeClient()
        return mec.normalize_symbol(self.exchange_id, symbol)

    def get_balance(self, asset: str) -> float:
        """Get free balance for a specific asset."""
        if self.client is None:
            return 0.0

        if self.exchange_id == "kraken":
            # KrakenClient doesn't have a direct get_free_balance method exposed publicly in the snippet I saw,
            # but it has _private('/0/private/Balance').
            # Let's implement a safe wrapper.
            try:
                if self.dry_run:
                    # Mock balance for dry run if needed, or rely on client's behavior
                    return 1000.0 # Default mock
                
                res = self.client._private('/0/private/Balance', {})
                # Kraken returns assets like 'ZUSD', 'XXBT'. Need to handle mapping if strictly needed,
                # but usually passing 'USD' or 'BTC' works if the client handles it or if we check keys.
                # For now, let's try direct access and some common mappings.
                
                # Map common assets to Kraken internal names if not found
                # Kraken uses XXBT for BTC, XXDG for DOGE, XETH for ETH, ZUSD for USD, etc.
                mappings = {'BTC': 'XXBT', 'DOGE': 'XXDG', 'ETH': 'XETH', 'USD': 'ZUSD', 'GBP': 'ZGBP', 'EUR': 'ZEUR'}
                search_keys = [asset, mappings.get(asset, asset)]
                
                for key in search_keys:
                    if key in res:
                        return float(res[key])
                return 0.0
            except Exception as e:
                logger.error(f"Error getting Kraken balance: {e}")
                return 0.0
                
        elif self.exchange_id == "binance":
            try:
                return float(self.client.get_free_balance(asset) or 0.0)
            except Exception as e:
                logger.error(f"Error getting Binance balance: {e}")
                return 0.0
            
        elif self.exchange_id == "alpaca":
            try:
                # Prefer the client's own Kraken-compatible balance helper.
                return float(self.client.get_free_balance(asset) or 0.0)
            except Exception as e:
                logger.error(f"Error getting Alpaca balance: {e}")
                return 0.0
                
        return 0.0

    def get_all_balances(self) -> Dict[str, float]:
        """Get all non-zero balances."""
        if self.client is None:
            return {}

        balances = {}
        
        if self.exchange_id == 'kraken':
            try:
                # Use KrakenClient's get_account_balance if available
                if hasattr(self.client, 'get_account_balance'):
                    raw_bals = self.client.get_account_balance()
                    for asset, amount in raw_bals.items():
                        try:
                            val = float(amount)
                            if val > 0:
                                balances[asset] = val
                        except:
                            pass
                    return balances
            except Exception as e:
                logger.error(f"Error getting Kraken balances: {e}")
                return {}
        
        if self.exchange_id == 'alpaca':
            try:
                # Use the client's Kraken-compatible balance map (qty_available aware).
                return self.client.get_account_balance() or {}
            except Exception as e:
                logger.error(f"Error getting Alpaca balances: {e}")
                return {}

        if self.exchange_id == 'capital':
            try:
                return self.client.get_account_balance()
            except Exception as e:
                logger.error(f"Error getting Capital.com balances: {e}")
                return {}

        try:
            acct = self.client.account()
            for bal in acct.get("balances", []):
                val = float(bal.get("free", 0))
                if val > 0:
                    balances[bal.get("asset")] = val
        except Exception as e:
            logger.error(f"Error getting balances: {e}")
        return balances

    def account(self) -> Dict[str, Any]:
        """Return account info in Binance format."""
        if self.client is None:
            return {}
        return self.client.account()

    def convert_to_quote(self, asset: str, amount: float, quote: str) -> float:
        """Convert amount of asset to quote currency value."""
        # Handle Binance Earn assets (LD prefix)
        if self.exchange_id == 'binance' and asset.startswith('LD'):
            asset = asset[2:]
            
        if hasattr(self.client, 'convert_to_quote'):
            return self.client.convert_to_quote(asset, amount, quote)
            
        if self.exchange_id == 'alpaca':
            if asset == quote: return amount
            try:
                # Try to get latest quote for asset/quote
                symbol = f"{asset}/{quote}"
                quotes = self.client.get_latest_crypto_quotes([symbol])
                if symbol in quotes:
                    # Use mid price
                    bid = float(quotes[symbol].get('bp', 0))
                    ask = float(quotes[symbol].get('ap', 0))
                    if bid > 0 and ask > 0:
                        price = (bid + ask) / 2
                        return amount * price
                
                # Try reverse
                symbol_rev = f"{quote}/{asset}"
                quotes = self.client.get_latest_crypto_quotes([symbol_rev])
                if symbol_rev in quotes:
                    bid = float(quotes[symbol_rev].get('bp', 0))
                    ask = float(quotes[symbol_rev].get('ap', 0))
                    if bid > 0 and ask > 0:
                        price = (bid + ask) / 2
                        return amount / price
            except:
                pass
            return 0.0

    def get_24h_tickers(self) -> List[Dict[str, Any]]:
        """Proxy to client, ensuring symbols are returned in canonical form when possible."""
        if hasattr(self.client, 'get_24h_tickers'):
            tks = self.client.get_24h_tickers()
            # Attempt minimal canonicalization: map XBT->BTC and wsname-derived quotes
            out = []
            for t in tks:
                sym = t.get('symbol') or t.get('wsname') or ''
                symu = str(sym).upper()
                if symu.startswith('XBT'):
                    symu = 'BTC' + symu[3:]
                t['symbol'] = symu
                out.append(t)
            return out
        return []

    def get_ticker(self, symbol: str) -> Dict[str, float]:
        """Get ticker with normalization applied for this exchange."""
        norm = self.normalize(symbol)
        if hasattr(self.client, 'get_ticker'):
            return self.client.get_ticker(norm)
        # Fallback using 24h ticker
        if hasattr(self.client, 'get_24h_ticker'):
            t = self.client.get_24h_ticker(norm)
            try:
                last = float(t.get('lastPrice', 0) or 0)
            except Exception:
                last = 0.0
            return {'price': last, 'bid': last, 'ask': last}
        return {'price': 0.0, 'bid': 0.0, 'ask': 0.0}

    def get_24h_tickers(self) -> List[Dict[str, Any]]:
        """Get 24h ticker statistics for all symbols."""
        if self.client is None:
            return []

        if self.exchange_id == 'capital':
            try:
                return self.client.get_24h_tickers()
            except Exception as e:
                logger.error(f"Capital.com get_24h_tickers error: {e}")
                return []

        if self.exchange_id == 'kraken':
            try:
                # Use the KrakenClient's get_24h_tickers which handles all pairs properly
                return self.client.get_24h_tickers()
            except Exception as e:
                logger.error(f"Kraken get_24h_tickers error: {e}")
                return []

        if self.exchange_id == 'alpaca':
            try:
                return self.client.get_24h_tickers()
            except Exception as e:
                logger.error(f"Alpaca get_24h_tickers error: {e}")
                return []

        if hasattr(self.client, 'get_24h_tickers'):
            tickers = self.client.get_24h_tickers()
            # Normalize Binance data (strings to floats)
            if self.exchange_id == 'binance':
                for t in tickers:
                    if 'priceChangePercent' in t:
                        try:
                            t['priceChangePercent'] = float(t['priceChangePercent'])
                        except:
                            t['priceChangePercent'] = 0.0
                    if 'lastPrice' in t:
                        try:
                            t['lastPrice'] = float(t['lastPrice'])
                        except:
                            t['lastPrice'] = 0.0
            return tickers
        return []

    def get_ticker(self, symbol: str) -> Dict[str, float]:
        """
        Get current ticker data (price, bid, ask).
        Returns dict with 'price', 'bid', 'ask'.
        """
        if self.client is None:
            return {'price': 0.0, 'bid': 0.0, 'ask': 0.0}

        if self.exchange_id == "kraken":
            # Kraken uses pairs like 'XBTUSD'
            try:
                # Normalize to Kraken altname (no slash, upper)
                alt = symbol.replace('/', '').upper()
                
                # 🔧 Kraken ticker normalization - they use weird names!
                # BTC→XBT, DOGE→XDG (Kraken's internal naming convention)
                kraken_alt = alt
                if alt.startswith('BTC'):
                    kraken_alt = 'XBT' + alt[3:]
                elif alt.startswith('DOGE'):
                    kraken_alt = 'XDG' + alt[4:]  # DOGEUSDC → XDGUSDC
                    
                # Kraken expects the internal pair name (e.g. XXBTZUSD). Map altname -> internal.
                self.client._load_asset_pairs()
                
                # Try Kraken-mapped version first (XBT for BTC, XDG for DOGE)
                pair = self.client._alt_to_int.get(kraken_alt) or self.client._alt_to_int.get(alt, alt)
                ticker_symbol = kraken_alt if kraken_alt in self.client._alt_to_int else alt

                # Use KrakenClient ticker helper so mapping/format stays consistent
                result = self.client._ticker([ticker_symbol])
                if not result:
                    # Fallback: try original if mapped version didn't work
                    if ticker_symbol != alt:
                        result = self.client._ticker([alt])
                    if not result:
                        logger.error(f"Kraken ticker empty result for {alt} (tried {ticker_symbol}, pair {pair})")
                        return {'price': 0.0, 'bid': 0.0, 'ask': 0.0}

                key, data = next(iter(result.items()))
                try:
                    price = float(data.get('c', [0])[0])
                    bid = float(data.get('b', [0])[0])
                    ask = float(data.get('a', [0])[0])
                except Exception as inner:
                    logger.error(f"Error parsing Kraken ticker for {alt} ({key}): {inner}")
                    return {'price': 0.0, 'bid': 0.0, 'ask': 0.0}

                return {'price': price, 'bid': bid, 'ask': ask}
            except Exception as e:
                logger.error(f"Error getting Kraken ticker: {e}")
                return {'price': 0.0, 'bid': 0.0, 'ask': 0.0}

        elif self.exchange_id == "binance":
            try:
                # Binance has /api/v3/ticker/price and /api/v3/ticker/bookTicker
                # Let's use bookTicker for bid/ask
                res = self.client.session.get(f"{self.client.base}/api/v3/ticker/bookTicker", params={"symbol": symbol}).json()
                # {'symbol': 'BTCUSDT', 'bidPrice': '...', 'askPrice': '...'}
                if isinstance(res, dict) and 'bidPrice' in res and 'askPrice' in res:
                    bid = float(res['bidPrice'])
                    ask = float(res['askPrice'])
                    price = (bid + ask) / 2.0  # Approximation
                    return {'price': price, 'bid': bid, 'ask': ask}

                # Fallback: try ticker/price if bookTicker failed or returned error payload
                price_res = self.client.session.get(f"{self.client.base}/api/v3/ticker/price", params={"symbol": symbol}).json()
                if isinstance(price_res, dict) and 'price' in price_res:
                    try:
                        price = float(price_res['price'])
                    except Exception:
                        price = 0.0
                    return {'price': price, 'bid': price, 'ask': price}

                # Handle "Invalid symbol" gracefully
                if isinstance(res, dict) and res.get('code') == -1121:
                    logger.debug(f"Binance symbol not found: {symbol}")
                    return {'price': 0.0, 'bid': 0.0, 'ask': 0.0}

                logger.error(f"Binance ticker unexpected payload for {symbol}: {res}")
                return {'price': 0.0, 'bid': 0.0, 'ask': 0.0}
            except Exception as e:
                logger.error(f"Error getting Binance ticker: {e}")
                return {'price': 0.0, 'bid': 0.0, 'ask': 0.0}
        
        elif self.exchange_id == "alpaca":
            try:
                quotes = self.client.get_latest_crypto_quotes([symbol])
                if symbol in quotes:
                    q = quotes[symbol]
                    bid = float(q.get('bp', 0))
                    ask = float(q.get('ap', 0))
                    price = (bid + ask) / 2
                    return {'price': price, 'bid': bid, 'ask': ask}
            except Exception as e:
                logger.error(f"Error getting Alpaca ticker: {e}")
                return {'price': 0.0, 'bid': 0.0, 'ask': 0.0}

        elif self.exchange_id == "capital":
            try:
                return self.client.get_ticker(symbol)
            except Exception as e:
                logger.error(f"Error getting Capital.com ticker: {e}")
                return {'price': 0.0, 'bid': 0.0, 'ask': 0.0}

        return {'price': 0.0, 'bid': 0.0, 'ask': 0.0}

    def place_market_order(
        self,
        symbol: str,
        side: str,
        quantity: float = None,
        quote_qty: float = None,
        *,
        unity_invocation: LegacyEconomicInvocation | None = None,
        unity_plan: LegacyUnityIntentPlan | None = None,
    ) -> Dict[str, Any]:
        """
        Place a market order.
        side: 'buy' or 'sell'
        quantity: amount of base asset (e.g. BTC)
        quote_qty: amount of quote asset (e.g. USD)
        """
        side = side.lower()

        # Prevent Kraken "volume minimum not met" by enforcing a notional floor
        if self.exchange_id == "kraken":
            # If quote_qty given, it's already notional
            if quote_qty is not None and quote_qty < self.kraken_min_notional:
                logger.warning(f"Kraken order blocked: notional {quote_qty:.2f} below min {self.kraken_min_notional:.2f}")
                return {'error': 'min_notional', 'exchange': self.exchange_id}
            # If only quantity provided, estimate notional using latest price
            if quote_qty is None and quantity is not None:
                ticker = self.get_ticker(symbol)
                price = _finite(ticker.get('price') if isinstance(ticker, Mapping) else None, positive=True)
                requested_quantity = _finite(quantity, positive=True)
                if price is None or requested_quantity is None:
                    receipt = _no_data(self.exchange_id, symbol, "fresh_price_receipt_required_for_order_preflight")
                    receipt["status"] = "not_submitted"
                    receipt["rejected"] = True
                    return receipt
                est_notional = price * requested_quantity
                if est_notional < self.kraken_min_notional:
                    logger.warning(f"Kraken order blocked: est notional {est_notional:.2f} below min {self.kraken_min_notional:.2f} for {symbol}")
                    return {'error': 'min_notional', 'exchange': self.exchange_id}
        
        if self.exchange_id == "kraken":
            # Use KrakenClient's place_market_order which returns Binance-compatible format
            try:
                return self._execute_optional_legacy_unity(
                    unity_invocation,
                    plan=unity_plan,
                    transport=lambda: self.client.place_market_order(
                        symbol,
                        side,
                        quantity=quantity,
                        quote_qty=quote_qty,
                    ),
                )
            except Exception as e:
                logger.error(f"Error placing Kraken order: {e}")
                return {
                    'rejected': True,
                    'error': 'exception',
                    'reason': str(e),
                    'exchange': self.exchange_id,
                    'symbol': symbol,
                    'side': side,
                    'quantity': quantity,
                    'quote_qty': quote_qty,
                }

        elif self.exchange_id == "binance":
            try:
                return self._execute_optional_legacy_unity(
                    unity_invocation,
                    plan=unity_plan,
                    transport=lambda: self.client.place_market_order(
                        symbol,
                        side,
                        quantity=quantity,
                        quote_qty=quote_qty,
                    ),
                )
            except Exception as e:
                logger.error(f"Error placing Binance order: {e}")
                return {
                    'rejected': True,
                    'error': 'exception',
                    'reason': str(e),
                    'exchange': self.exchange_id,
                    'symbol': symbol,
                    'side': side,
                    'quantity': quantity,
                    'quote_qty': quote_qty,
                }
            
        elif self.exchange_id == "alpaca":
            try:
                symbol = self.normalize(symbol)
                # Route through AlpacaClient's Kraken-compatible helper which:
                # - converts quote_qty -> qty
                # - clamps SELL qty to qty_available (fee-safe)
                return self._execute_optional_legacy_unity(
                    unity_invocation,
                    plan=unity_plan,
                    transport=lambda: self.client.place_market_order(
                        symbol,
                        side,
                        quantity=quantity,
                        quote_qty=quote_qty,
                    ),
                )
            except Exception as e:
                logger.error(f"Error placing Alpaca order: {e}")
                return {
                    'rejected': True,
                    'error': 'exception',
                    'reason': str(e),
                    'exchange': self.exchange_id,
                    'symbol': symbol,
                    'side': side,
                    'quantity': quantity,
                    'quote_qty': quote_qty,
                }

        elif self.exchange_id == "capital":
            try:
                # Capital.com uses 'size' (quantity)
                if quantity:
                    return self._execute_optional_legacy_unity(
                        unity_invocation,
                        plan=unity_plan,
                        transport=lambda: self.client.place_market_order(
                            symbol,
                            side,
                            quantity,
                        ),
                    )
                elif quote_qty:
                    ticker = self.get_ticker(symbol)
                    if ticker['price'] > 0:
                        qty = quote_qty / ticker['price']
                        return self._execute_optional_legacy_unity(
                            unity_invocation,
                            plan=unity_plan,
                            transport=lambda: self.client.place_market_order(
                                symbol,
                                side,
                                qty,
                            ),
                        )
            except Exception as e:
                logger.error(f"Error placing Capital.com order: {e}")
                return {
                    'rejected': True,
                    'error': 'exception',
                    'reason': str(e),
                    'exchange': self.exchange_id,
                    'symbol': symbol,
                    'side': side,
                    'quantity': quantity,
                    'quote_qty': quote_qty,
                }

        return {
            'rejected': True,
            'error': 'invalid_order',
            'reason': 'Must provide quantity or quote_qty',
            'exchange': self.exchange_id,
            'symbol': symbol,
            'side': side,
            'quantity': quantity,
            'quote_qty': quote_qty,
        }

    # ══════════════════════════════════════════════════════════════════════
    # ADVANCED ORDER TYPES - Limit, Stop-Loss, Take-Profit, Trailing Stop
    # ══════════════════════════════════════════════════════════════════════

    def place_limit_order(self, symbol: str, side: str, quantity, price,
                          post_only: bool = False, time_in_force: str = "GTC", *,
                          unity_invocation: LegacyEconomicInvocation | None = None,
                          unity_plan: LegacyUnityIntentPlan | None = None) -> Dict[str, Any]:
        """Place a limit order. Uses maker fees (0.16% on Kraken vs 0.26% taker)."""
        side = side.lower()

        # Apply the same notional floor for Kraken limit orders
        if self.exchange_id == "kraken":
            notional = (price or 0) * (quantity or 0)
            if notional < self.kraken_min_notional:
                logger.warning(f"Kraken limit order blocked: notional {notional:.2f} below min {self.kraken_min_notional:.2f} for {symbol}")
                return {'error': 'min_notional', 'exchange': self.exchange_id}
        
        if self.exchange_id == "kraken":
            if hasattr(self.client, 'place_limit_order'):
                try:
                    return self._execute_optional_legacy_unity(
                        unity_invocation,
                        plan=unity_plan,
                        transport=lambda: self.client.place_limit_order(
                            symbol, side, quantity, price, post_only, time_in_force
                        ),
                    )
                except Exception as e:
                    logger.error(f"Error placing Kraken limit order: {e}")
                    return {}
        elif self.exchange_id == "alpaca":
            if hasattr(self.client, 'place_limit_order'):
                try:
                    # Alpaca uses lowercase tif: 'gtc', 'day', 'ioc'
                    tif = time_in_force.lower() if time_in_force else 'gtc'
                    return self._execute_optional_legacy_unity(
                        unity_invocation,
                        plan=unity_plan,
                        transport=lambda: self.client.place_limit_order(
                            symbol, quantity, side, price, time_in_force=tif
                        ),
                    )
                except Exception as e:
                    logger.error(f"Error placing Alpaca limit order: {e}")
                    return {}
        
        # Fallback to market order for exchanges without limit order support
        logger.warning(f"{self.exchange_id} doesn't support limit orders, using market")
        return self.place_market_order(
            symbol,
            side,
            quantity=quantity,
            unity_invocation=unity_invocation,
            unity_plan=unity_plan,
        )

    def place_stop_loss_order(self, symbol: str, side: str, quantity,
                              stop_price, limit_price=None, *,
                              unity_invocation: LegacyEconomicInvocation | None = None,
                              unity_plan: LegacyUnityIntentPlan | None = None) -> Dict[str, Any]:
        """Place server-side stop-loss order (executes even if bot offline)."""
        side = side.lower()
        
        if self.exchange_id == "kraken":
            if hasattr(self.client, 'place_stop_loss_order'):
                try:
                    return self._execute_optional_legacy_unity(
                        unity_invocation,
                        plan=unity_plan,
                        transport=lambda: self.client.place_stop_loss_order(
                            symbol, side, quantity, stop_price, limit_price
                        ),
                    )
                except Exception as e:
                    logger.error(f"Error placing Kraken stop-loss: {e}")
                    return {}
        elif self.exchange_id == "alpaca":
            if hasattr(self.client, 'place_stop_loss_order'):
                try:
                    return self._execute_optional_legacy_unity(
                        unity_invocation,
                        plan=unity_plan,
                        transport=lambda: self.client.place_stop_loss_order(
                            symbol, side, quantity, stop_price, limit_price
                        ),
                    )
                except Exception as e:
                    logger.error(f"Error placing Alpaca stop-loss: {e}")
                    return {}
        
        logger.warning(f"{self.exchange_id} doesn't support native stop-loss orders")
        return {'error': 'Not supported', 'exchange': self.exchange_id}

    def place_take_profit_order(self, symbol: str, side: str, quantity,
                                take_profit_price, limit_price=None, *,
                                unity_invocation: LegacyEconomicInvocation | None = None,
                                unity_plan: LegacyUnityIntentPlan | None = None) -> Dict[str, Any]:
        """Place server-side take-profit order (executes even if bot offline)."""
        side = side.lower()
        
        if self.exchange_id == "kraken":
            if hasattr(self.client, 'place_take_profit_order'):
                try:
                    return self._execute_optional_legacy_unity(
                        unity_invocation,
                        plan=unity_plan,
                        transport=lambda: self.client.place_take_profit_order(
                            symbol, side, quantity, take_profit_price, limit_price
                        ),
                    )
                except Exception as e:
                    logger.error(f"Error placing Kraken take-profit: {e}")
                    return {}
        elif self.exchange_id == "alpaca":
            if hasattr(self.client, 'place_take_profit_order'):
                try:
                    return self._execute_optional_legacy_unity(
                        unity_invocation,
                        plan=unity_plan,
                        transport=lambda: self.client.place_take_profit_order(
                            symbol, side, quantity, take_profit_price, limit_price
                        ),
                    )
                except Exception as e:
                    logger.error(f"Error placing Alpaca take-profit: {e}")
                    return {}
        
        logger.warning(f"{self.exchange_id} doesn't support native take-profit orders")
        return {'error': 'Not supported', 'exchange': self.exchange_id}

    def place_trailing_stop_order(self, symbol: str, side: str, quantity,
                                  trailing_offset, offset_type: str = "percent", *,
                                  unity_invocation: LegacyEconomicInvocation | None = None,
                                  unity_plan: LegacyUnityIntentPlan | None = None) -> Dict[str, Any]:
        """Place trailing stop order (auto-adjusts as price moves)."""
        side = side.lower()
        
        if self.exchange_id == "kraken":
            if hasattr(self.client, 'place_trailing_stop_order'):
                try:
                    return self._execute_optional_legacy_unity(
                        unity_invocation,
                        plan=unity_plan,
                        transport=lambda: self.client.place_trailing_stop_order(
                            symbol, side, quantity, trailing_offset, offset_type
                        ),
                    )
                except Exception as e:
                    logger.error(f"Error placing Kraken trailing stop: {e}")
                    return {}
        elif self.exchange_id == "alpaca":
            if hasattr(self.client, 'place_trailing_stop_order'):
                try:
                    # Alpaca uses trail_percent or trail_price
                    if offset_type == '+%':
                        return self._execute_optional_legacy_unity(
                            unity_invocation,
                            plan=unity_plan,
                            transport=lambda: self.client.place_trailing_stop_order(
                                symbol,
                                quantity,
                                side,
                                trail_percent=trailing_offset,
                            ),
                        )
                    else:
                        return self._execute_optional_legacy_unity(
                            unity_invocation,
                            plan=unity_plan,
                            transport=lambda: self.client.place_trailing_stop_order(
                                symbol,
                                quantity,
                                side,
                                trail_price=trailing_offset,
                            ),
                        )
                except Exception as e:
                    logger.error(f"Error placing Alpaca trailing stop: {e}")
                    return {}
        
        logger.warning(f"{self.exchange_id} doesn't support trailing stop orders")
        return {'error': 'Not supported', 'exchange': self.exchange_id}

    def place_order_with_tp_sl(self, symbol: str, side: str, quantity,
                               order_type: str = "market", price=None,
                               take_profit=None, stop_loss=None, *,
                               unity_invocation: LegacyEconomicInvocation | None = None,
                               unity_plan: LegacyUnityIntentPlan | None = None) -> Dict[str, Any]:
        """Place order with attached Take-Profit and/or Stop-Loss (conditional close)."""
        side = side.lower()
        
        if self.exchange_id == "kraken":
            if hasattr(self.client, 'place_order_with_tp_sl'):
                try:
                    return self._execute_optional_legacy_unity(
                        unity_invocation,
                        plan=unity_plan,
                        transport=lambda: self.client.place_order_with_tp_sl(
                            symbol,
                            side,
                            quantity,
                            order_type,
                            price,
                            take_profit,
                            stop_loss,
                        ),
                    )
                except Exception as e:
                    logger.error(f"Error placing Kraken order with TP/SL: {e}")
                    return {}
        elif self.exchange_id == "alpaca":
            if hasattr(self.client, 'place_order_with_tp_sl'):
                try:
                    return self._execute_optional_legacy_unity(
                        unity_invocation,
                        plan=unity_plan,
                        transport=lambda: self.client.place_order_with_tp_sl(
                            symbol,
                            side,
                            quantity,
                            order_type,
                            price,
                            take_profit,
                            stop_loss,
                        ),
                    )
                except Exception as e:
                    logger.error(f"Error placing Alpaca order with TP/SL: {e}")
                    return {}
        
        if take_profit is not None or stop_loss is not None:
            return _no_data(
                self.exchange_id,
                symbol,
                "native_atomic_tp_sl_or_separate_governed_plans_required",
            )
        return self.place_market_order(
            symbol,
            side,
            quantity=quantity,
            unity_invocation=unity_invocation,
            unity_plan=unity_plan,
        )

    def get_open_orders(self, symbol: str = None) -> List[Dict[str, Any]]:
        """Get all open orders."""
        if self.exchange_id == "kraken":
            if hasattr(self.client, 'get_open_orders'):
                try:
                    return self.client.get_open_orders(symbol)
                except Exception as e:
                    logger.error(f"Error getting Kraken open orders: {e}")
                    return []
        elif self.exchange_id == "alpaca":
            if hasattr(self.client, 'get_open_orders'):
                try:
                    return self.client.get_open_orders(symbol)
                except Exception as e:
                    logger.error(f"Error getting Alpaca open orders: {e}")
                    return []
        return []

    def cancel_order(
        self,
        order_id: str,
        *,
        unity_invocation: LegacyEconomicInvocation | None = None,
        unity_plan: LegacyUnityIntentPlan | None = None,
    ) -> Dict[str, Any]:
        """Cancel a specific order."""
        if self.exchange_id == "kraken":
            if hasattr(self.client, 'cancel_order'):
                try:
                    return self._execute_optional_legacy_unity(
                        unity_invocation,
                        plan=unity_plan,
                        transport=lambda: self.client.cancel_order(order_id),
                    )
                except Exception as e:
                    logger.error(f"Error cancelling Kraken order: {e}")
                    return {}
        elif self.exchange_id == "alpaca":
            if hasattr(self.client, 'cancel_order'):
                try:
                    return self._execute_optional_legacy_unity(
                        unity_invocation,
                        plan=unity_plan,
                        transport=lambda: self.client.cancel_order(order_id),
                    )
                except Exception as e:
                    logger.error(f"Error cancelling Alpaca order: {e}")
                    return {}
        return {}

    def cancel_all_orders(
        self,
        symbol: str = None,
        *,
        unity_invocation: LegacyEconomicInvocation | None = None,
        unity_plan: LegacyUnityIntentPlan | None = None,
    ) -> Dict[str, Any]:
        """Cancel all open orders."""
        if self.exchange_id == "kraken":
            if hasattr(self.client, 'cancel_all_orders'):
                try:
                    return self._execute_optional_legacy_unity(
                        unity_invocation,
                        plan=unity_plan,
                        transport=lambda: self.client.cancel_all_orders(symbol),
                    )
                except Exception as e:
                    logger.error(f"Error cancelling all Kraken orders: {e}")
                    return {}
        elif self.exchange_id == "alpaca":
            if hasattr(self.client, 'cancel_all_orders'):
                try:
                    return self._execute_optional_legacy_unity(
                        unity_invocation,
                        plan=unity_plan,
                        transport=lambda: self.client.cancel_all_orders(),
                    )
                except Exception as e:
                    logger.error(f"Error cancelling all Alpaca orders: {e}")
                    return {}
        return {}
        return {}

    def get_standardized_pair(self, base: str, quote: str) -> str:
        """Return the symbol in the format expected by the exchange."""
        base = base.upper()
        quote = quote.upper()
        
        if self.exchange_id == "kraken":
            # Kraken often uses XBT instead of BTC, but the API accepts 'BTCUSD' usually and maps it.
            # However, for consistency:
            if base == 'BTC': base = 'XBT'
            # if quote == 'BTC': quote = 'XBT' # Sometimes
            return f"{base}{quote}"
        elif self.exchange_id == "binance":
            return f"{base}{quote}"
        elif self.exchange_id == "alpaca":
            return f"{base}/{quote}"
        return f"{base}{quote}"

    def get_symbol_filters(self, symbol: str) -> Dict[str, float]:
        if hasattr(self.client, 'get_symbol_filters'):
            try:
                return self.client.get_symbol_filters(symbol)
            except Exception:
                return {}
        return {}

    def adjust_quantity(self, symbol: str, quantity: float) -> float:
        if hasattr(self.client, 'adjust_quantity'):
            try:
                return self.client.adjust_quantity(symbol, quantity)
            except Exception:
                return quantity
        return quantity

    # ══════════════════════════════════════════════════════════════════════
    # MARGIN TRADING - Leveraged positions (Kraken only for now)
    # ══════════════════════════════════════════════════════════════════════

    def get_trade_balance(self, asset: str = "ZUSD") -> Dict[str, Any]:
        """Get margin/trade balance information (equity, free margin, margin level)."""
        if self.exchange_id == "kraken":
            if hasattr(self.client, 'get_trade_balance'):
                try:
                    return self.client.get_trade_balance(asset)
                except Exception as e:
                    logger.error(f"Error getting Kraken trade balance: {e}")
                    return {}
        logger.warning(f"{self.exchange_id} doesn't support margin trade balance queries")
        return {}

    def get_open_margin_positions(self, do_calcs: bool = True) -> List[Dict[str, Any]]:
        """Get all open margin positions."""
        if self.exchange_id == "kraken":
            if hasattr(self.client, 'get_open_margin_positions'):
                try:
                    return self.client.get_open_margin_positions(do_calcs)
                except Exception as e:
                    logger.error(f"Error getting Kraken margin positions: {e}")
                    return []
        logger.warning(f"{self.exchange_id} doesn't support margin positions")
        return []

    def get_margin_pairs(self) -> List[Dict[str, Any]]:
        """Get trading pairs that support margin trading with leverage limits."""
        if self.exchange_id == "kraken":
            if hasattr(self.client, 'get_margin_pairs'):
                try:
                    return self.client.get_margin_pairs()
                except Exception as e:
                    logger.error(f"Error getting Kraken margin pairs: {e}")
                    return []
        return []

    def get_pair_leverage(self, symbol: str) -> Dict[str, Any]:
        """Get available leverage options for a specific pair."""
        if self.exchange_id == "kraken":
            if hasattr(self.client, 'get_pair_leverage'):
                try:
                    return self.client.get_pair_leverage(symbol)
                except Exception as e:
                    logger.error(f"Error getting leverage for {symbol}: {e}")
                    return {}
        return {}

    def place_margin_order(self, symbol: str, side: str, quantity, leverage,
                           order_type: str = "market", price=None,
                           take_profit=None, stop_loss=None,
                           post_only: bool = False, *,
                           unity_invocation: LegacyEconomicInvocation | None = None,
                           unity_plan: LegacyUnityIntentPlan | None = None) -> Dict[str, Any]:
        """Place a margin (leveraged) order."""
        side = side.lower()

        if self.exchange_id == "kraken":
            # Notional floor check
            if order_type.lower() == "limit" and price:
                limit_price = _finite(price, positive=True)
                requested_quantity = _finite(quantity, positive=True)
                if limit_price is None or requested_quantity is None:
                    receipt = _no_data(self.exchange_id, symbol, "finite_limit_price_and_quantity_required")
                    receipt["status"] = "not_submitted"
                    receipt["rejected"] = True
                    return receipt
                notional = limit_price * requested_quantity
            else:
                ticker = self.get_ticker(symbol)
                market_price = _finite(ticker.get('price') if isinstance(ticker, Mapping) else None, positive=True)
                requested_quantity = _finite(quantity, positive=True)
                if market_price is None or requested_quantity is None:
                    receipt = _no_data(self.exchange_id, symbol, "fresh_price_receipt_required_for_margin_preflight")
                    receipt["status"] = "not_submitted"
                    receipt["rejected"] = True
                    return receipt
                notional = market_price * requested_quantity
            if notional < self.kraken_min_notional:
                logger.warning(f"Kraken margin order blocked: notional {notional:.2f} below min {self.kraken_min_notional:.2f}")
                return {'error': 'min_notional', 'exchange': self.exchange_id, 'margin': True}

            if hasattr(self.client, 'place_margin_order'):
                try:
                    return self._execute_optional_legacy_unity(
                        unity_invocation,
                        plan=unity_plan,
                        transport=lambda: self.client.place_margin_order(
                            symbol,
                            side,
                            quantity,
                            leverage,
                            order_type=order_type,
                            price=price,
                            take_profit=take_profit,
                            stop_loss=stop_loss,
                            post_only=post_only,
                        ),
                    )
                except Exception as e:
                    logger.error(f"Error placing Kraken margin order: {e}")
                    return {
                        'rejected': True, 'error': 'exception',
                        'reason': str(e), 'exchange': self.exchange_id,
                        'margin': True
                    }

        logger.warning(f"{self.exchange_id} doesn't support margin trading")
        return {'error': 'not_supported', 'exchange': self.exchange_id, 'margin': True}

    def close_margin_position(self, symbol: str, side: str, volume=None,
                               order_type: str = "market", price=None,
                               leverage=None, *,
                               unity_invocation: LegacyEconomicInvocation | None = None,
                               unity_plan: LegacyUnityIntentPlan | None = None) -> Dict[str, Any]:
        """Close an open margin position."""
        side = side.lower()

        if self.exchange_id == "kraken":
            if hasattr(self.client, 'close_margin_position'):
                try:
                    return self._execute_optional_legacy_unity(
                        unity_invocation,
                        plan=unity_plan,
                        transport=lambda: self.client.close_margin_position(
                            symbol,
                            side,
                            volume=volume,
                            order_type=order_type,
                            price=price,
                            leverage=leverage,
                        ),
                    )
                except Exception as e:
                    logger.error(f"Error closing Kraken margin position: {e}")
                    return {'error': 'exception', 'reason': str(e)}

        logger.warning(f"{self.exchange_id} doesn't support closing margin positions")
        return {'error': 'not_supported', 'exchange': self.exchange_id}
