"""Canonical exchange brain presented to Queen/ORCA processes.

The Queen is allowed to observe through the underlying provider client, but it
cannot use that client as authority.  Every supported mutation is routed
through :class:`GovernedMultiExchangeClient`, which obtains an exact strategy
plan and then enters the existing HNC -> Auris -> Council/Crown boundary.
Missing composition is a numeric-free HOLD, not a legacy live fallback.
"""

from __future__ import annotations

from collections.abc import Callable, Collection, Mapping
from threading import Lock
from typing import Any

from aureon.governance.legacy_economic_unity import (
    LegacyEconomicInvocation,
)
from aureon.governance.legacy_unity_composition import LegacyUnityIntentPlan
from aureon.trading.unified_exchange_client import (
    GovernedMultiExchangeClient,
    MultiExchangeClient,
    TrustedUnifiedEcosystemPlanSupplier,
)

_SUPPORTED_EXCHANGES = frozenset({"alpaca", "binance", "capital", "kraken"})
_BLOCKED_MUTATION_PREFIXES = (
    "cancel_",
    "create_order",
    "edit_order",
    "place_",
    "replace_order",
    "submit_order",
)
_BLOCKED_MUTATION_NAMES = frozenset(
    {
        "allocate",
        "borrow",
        "close_margin_position",
        "close_position",
        "convert_crypto",
        "deallocate",
        "repay",
        "stake",
        "transfer",
        "unstake",
        "withdraw",
    }
)


def _hold(exchange: str, symbol: str, reason: str) -> dict[str, Any]:
    return {
        "status": "no_data",
        "decision": "HOLD",
        "reason": reason,
        "exchange": exchange,
        "symbol": symbol,
        "truth_status": "no_data",
        "generated_values": False,
        "action_eligible": False,
        "accounting_eligible": False,
        "learning_eligible": False,
        "economic_mutation": False,
    }


class QueenGovernedExchangeBrain:
    """Read-through provider view with one canonical economic mutation door."""

    def __init__(
        self,
        *,
        exchange: str,
        read_client: Any,
        governed_client: GovernedMultiExchangeClient | None,
        outcome_observer: Callable[[str, Mapping[str, Any]], Any] | None = None,
    ) -> None:
        normalized = str(exchange or "").strip().lower()
        if normalized not in _SUPPORTED_EXCHANGES:
            raise ValueError("supported_queen_exchange_required")
        if governed_client is not None and not isinstance(
            governed_client,
            GovernedMultiExchangeClient,
        ):
            raise TypeError("governed_multi_exchange_client_required")
        if governed_client is not None and normalized not in governed_client.clients:
            raise ValueError("queen_exchange_missing_from_unity_composition")
        self.exchange = normalized
        self._read_client = read_client
        self._governed_client = governed_client
        self._outcome_observer = outcome_observer
        self._read_lock = Lock()

    @property
    def read_client(self) -> Any:
        with self._read_lock:
            return self._read_client

    @property
    def unity_ready(self) -> bool:
        return self._governed_client is not None

    @property
    def dry_run(self) -> bool:
        if self._governed_client is not None:
            return bool(self._governed_client.dry_run)
        client = self.read_client
        return bool(getattr(client, "dry_run", True)) if client is not None else True

    def bind_read_client(self, client: Any) -> None:
        """Bind a lazy read client once without changing mutation authority."""

        if client is None:
            raise ValueError("queen_read_client_required")
        with self._read_lock:
            if self._read_client is not None and self._read_client is not client:
                raise RuntimeError("queen_read_client_already_bound")
            self._read_client = client

    def place_market_order(
        self,
        symbol: str,
        side: str,
        quantity: Any = None,
        quote_qty: Any = None,
        *,
        unity_invocation: LegacyEconomicInvocation | None = None,
        unity_plan: LegacyUnityIntentPlan | None = None,
        unity_purpose: str | None = None,
        **provider_kwargs: Any,
    ) -> dict[str, Any]:
        symbol_text = str(symbol or "").strip().upper()
        if unity_invocation is not None or unity_plan is not None:
            return self._observe(
                "place_market_order",
                _hold(
                    self.exchange,
                    symbol_text,
                    "caller_supplied_unity_authority_forbidden",
                ),
            )
        if provider_kwargs:
            return self._observe(
                "place_market_order",
                _hold(
                    self.exchange,
                    symbol_text,
                    "provider_specific_mutation_arguments_require_exact_unity_route",
                ),
            )
        if self._governed_client is None:
            return self._observe(
                "place_market_order",
                _hold(
                    self.exchange,
                    symbol_text,
                    "canonical_queen_unity_composition_required",
                ),
            )
        result = self._governed_client.place_market_order(
            self.exchange,
            symbol_text,
            side,
            quantity=quantity,
            quote_qty=quote_qty,
            unity_purpose=unity_purpose,
        )
        if not isinstance(result, Mapping):
            return self._observe(
                "place_market_order",
                _hold(
                    self.exchange,
                    symbol_text,
                    "queen_unity_dispatch_receipt_required",
                ),
            )
        return self._observe("place_market_order", result)

    def _observe(
        self,
        operation: str,
        result: Mapping[str, Any],
    ) -> dict[str, Any]:
        receipt = dict(result)
        if self._outcome_observer is not None:
            try:
                self._outcome_observer(operation, dict(receipt))
            except Exception:
                # Observation is feedback-only. It can never alter or retry a
                # provider outcome that may already have happened.
                pass
        return receipt

    def place_margin_order(
        self,
        symbol: str,
        side: str,
        quantity: Any,
        leverage: int = 2,
        order_type: str = "market",
        price: Any = None,
        take_profit: Any = None,
        stop_loss: Any = None,
        post_only: bool = False,
        *,
        unity_invocation: LegacyEconomicInvocation | None = None,
        unity_plan: LegacyUnityIntentPlan | None = None,
        unity_purpose: str = "ENTRY",
        unity_reduce_only: bool = False,
        **provider_kwargs: Any,
    ) -> dict[str, Any]:
        symbol_text = str(symbol or "").strip().upper()
        if unity_invocation is not None or unity_plan is not None:
            return self._observe(
                "place_margin_order",
                _hold(
                    self.exchange,
                    symbol_text,
                    "caller_supplied_unity_authority_forbidden",
                ),
            )
        if provider_kwargs:
            return self._observe(
                "place_margin_order",
                _hold(
                    self.exchange,
                    symbol_text,
                    "provider_specific_mutation_arguments_require_exact_unity_route",
                ),
            )
        if self._governed_client is None:
            return self._observe(
                "place_margin_order",
                _hold(
                    self.exchange,
                    symbol_text,
                    "canonical_queen_unity_composition_required",
                ),
            )
        result = self._governed_client.place_margin_order(
            self.exchange,
            symbol_text,
            side,
            quantity,
            leverage,
            order_type=order_type,
            price=price,
            take_profit=take_profit,
            stop_loss=stop_loss,
            post_only=post_only,
            unity_purpose=unity_purpose,
            unity_reduce_only=unity_reduce_only,
        )
        if not isinstance(result, Mapping):
            result = _hold(
                self.exchange,
                symbol_text,
                "queen_unity_dispatch_receipt_required",
            )
        return self._observe("place_margin_order", result)

    def close_margin_position(
        self,
        symbol: str,
        side: str,
        volume: Any = None,
        order_type: str = "market",
        price: Any = None,
        leverage: Any = None,
        *,
        unity_invocation: LegacyEconomicInvocation | None = None,
        unity_plan: LegacyUnityIntentPlan | None = None,
        **provider_kwargs: Any,
    ) -> dict[str, Any]:
        symbol_text = str(symbol or "").strip().upper()
        if unity_invocation is not None or unity_plan is not None:
            return self._observe(
                "close_margin_position",
                _hold(
                    self.exchange,
                    symbol_text,
                    "caller_supplied_unity_authority_forbidden",
                ),
            )
        if provider_kwargs:
            return self._observe(
                "close_margin_position",
                _hold(
                    self.exchange,
                    symbol_text,
                    "provider_specific_mutation_arguments_require_exact_unity_route",
                ),
            )
        if self._governed_client is None:
            return self._observe(
                "close_margin_position",
                _hold(
                    self.exchange,
                    symbol_text,
                    "canonical_queen_unity_composition_required",
                ),
            )
        result = self._governed_client.close_margin_position(
            self.exchange,
            symbol_text,
            side,
            volume=volume,
            order_type=order_type,
            price=price,
            leverage=leverage,
        )
        if not isinstance(result, Mapping):
            result = _hold(
                self.exchange,
                symbol_text,
                "queen_unity_dispatch_receipt_required",
            )
        return self._observe("close_margin_position", result)

    def place_take_profit_order(
        self,
        symbol: str,
        side: str,
        quantity: Any,
        take_profit_price: Any,
        limit_price: Any = None,
        *,
        unity_invocation: LegacyEconomicInvocation | None = None,
        unity_plan: LegacyUnityIntentPlan | None = None,
        **provider_kwargs: Any,
    ) -> dict[str, Any]:
        symbol_text = str(symbol or "").strip().upper()
        if unity_invocation is not None or unity_plan is not None:
            return self._observe(
                "place_take_profit_order",
                _hold(
                    self.exchange,
                    symbol_text,
                    "caller_supplied_unity_authority_forbidden",
                ),
            )
        if provider_kwargs:
            return self._observe(
                "place_take_profit_order",
                _hold(
                    self.exchange,
                    symbol_text,
                    "provider_specific_mutation_arguments_require_exact_unity_route",
                ),
            )
        if self._governed_client is None:
            return self._observe(
                "place_take_profit_order",
                _hold(
                    self.exchange,
                    symbol_text,
                    "canonical_queen_unity_composition_required",
                ),
            )
        result = self._governed_client.place_take_profit_order(
            self.exchange,
            symbol_text,
            side,
            quantity,
            take_profit_price,
            limit_price,
        )
        if not isinstance(result, Mapping):
            result = _hold(
                self.exchange,
                symbol_text,
                "queen_unity_dispatch_receipt_required",
            )
        return self._observe("place_take_profit_order", result)

    def place_trailing_stop_order(
        self,
        symbol: str,
        side: str,
        quantity: Any,
        trailing_offset: Any,
        offset_type: str = "percent",
        *,
        unity_invocation: LegacyEconomicInvocation | None = None,
        unity_plan: LegacyUnityIntentPlan | None = None,
        **provider_kwargs: Any,
    ) -> dict[str, Any]:
        symbol_text = str(symbol or "").strip().upper()
        if unity_invocation is not None or unity_plan is not None:
            return self._observe(
                "place_trailing_stop_order",
                _hold(
                    self.exchange,
                    symbol_text,
                    "caller_supplied_unity_authority_forbidden",
                ),
            )
        if provider_kwargs:
            return self._observe(
                "place_trailing_stop_order",
                _hold(
                    self.exchange,
                    symbol_text,
                    "provider_specific_mutation_arguments_require_exact_unity_route",
                ),
            )
        if self._governed_client is None:
            return self._observe(
                "place_trailing_stop_order",
                _hold(
                    self.exchange,
                    symbol_text,
                    "canonical_queen_unity_composition_required",
                ),
            )
        result = self._governed_client.place_trailing_stop_order(
            self.exchange,
            symbol_text,
            side,
            quantity,
            trailing_offset,
            offset_type,
        )
        if not isinstance(result, Mapping):
            result = _hold(
                self.exchange,
                symbol_text,
                "queen_unity_dispatch_receipt_required",
            )
        return self._observe("place_trailing_stop_order", result)

    def _blocked_mutation(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        symbol = kwargs.get("symbol")
        if symbol is None and args:
            symbol = args[0]
        return self._observe(
            "blocked_mutation",
            _hold(
                self.exchange,
                str(symbol or "UNKNOWN").strip().upper(),
                "queen_mutation_route_not_yet_unified",
            ),
        )

    def __getattr__(self, name: str) -> Any:
        if name in _BLOCKED_MUTATION_NAMES or name.startswith(
            _BLOCKED_MUTATION_PREFIXES
        ):
            return self._blocked_mutation
        client = self.read_client
        if client is None:
            raise AttributeError(name)
        return getattr(client, name)


def build_queen_exchange_brains(
    *,
    unity_composition: Any = None,
    unity_plan_supplier: TrustedUnifiedEcosystemPlanSupplier | None = None,
    trusted_unity_plan_supplier_ids: Collection[str] = (),
    fallback_read_clients: Mapping[str, Any] | None = None,
    outcome_observer: Callable[[str, Mapping[str, Any]], Any] | None = None,
) -> tuple[
    dict[str, QueenGovernedExchangeBrain],
    GovernedMultiExchangeClient | None,
    dict[str, Any],
]:
    """Compose every Queen exchange brain under the same immutable authority."""

    trusted_ids = frozenset(
        str(item or "").strip()
        for item in trusted_unity_plan_supplier_ids
        if str(item or "").strip()
    )
    fallback = dict(fallback_read_clients or {})
    unknown = set(fallback) - _SUPPORTED_EXCHANGES
    if unknown:
        raise ValueError("unsupported_queen_read_client")

    governed: GovernedMultiExchangeClient | None
    if unity_composition is None:
        if unity_plan_supplier is not None or trusted_ids:
            raise ValueError(
                "queen_unity_composition_plan_supplier_and_allowlist_required_together"
            )
        governed = None
        read_clients = fallback
        status = {
            "status": "HOLD",
            "reason": "canonical_queen_unity_composition_required",
            "economic_mutation": False,
        }
    else:
        if unity_plan_supplier is None or not trusted_ids or fallback:
            raise ValueError(
                "queen_unity_composition_plan_supplier_and_allowlist_required_together"
            )
        base_client = getattr(unity_composition, "client", None)
        if not isinstance(base_client, MultiExchangeClient):
            raise TypeError("canonical_multi_exchange_client_required")
        governed = GovernedMultiExchangeClient(
            base_client=base_client,
            plan_supplier=unity_plan_supplier,
            trusted_plan_supplier_ids=trusted_ids,
        )
        # Queen analytics use provider-specific read surfaces (order books,
        # snapshots, positions).  Expose that read view while the adapter
        # intercepts every mutation name before it can reach the provider.
        read_clients = {
            exchange: getattr(client, "client", client)
            for exchange, client in governed.clients.items()
        }
        status = {
            "status": "READY",
            "reason": "queen_hnc_auris_council_crown_unity_composed",
            "economic_mutation": False,
        }

    brains = {
        exchange: QueenGovernedExchangeBrain(
            exchange=exchange,
            read_client=read_clients.get(exchange),
            governed_client=governed,
            outcome_observer=outcome_observer,
        )
        for exchange in sorted(_SUPPORTED_EXCHANGES)
    }
    return brains, governed, status
