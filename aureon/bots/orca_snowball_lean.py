#!/usr/bin/env python3
"""Receipt-gated autonomous Snowball execution.

A live composition injects venue adapters that expose complete provider
receipts and an HNC/Auris supplier that links its cognition result to those
receipts. Missing or stale evidence returns no_data; it is never converted into
a price, balance, fee, position, profit, or learning event.

The autonomous path is opportunity receipt -> provider evidence -> HNC/Auris
gate -> durable intent -> provider acknowledgement -> one bounded read-back ->
terminal fill. Only a complete terminal provider fill is committed.
"""

from __future__ import annotations

import json
import math
import os
import time
from contextlib import contextmanager
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Mapping, Optional


PHI = (1.0 + math.sqrt(5.0)) / 2.0
MILLION = Decimal("1000000")
_TERMINAL_FILL_STATUS = "FILLED"
_NON_FILL_STATUSES = frozenset(
    {
        "ACK",
        "ACCEPTED",
        "CANCELED",
        "CANCELLED",
        "DRY_RUN",
        "EXPIRED",
        "INCOMPLETE",
        "NEW",
        "PARTIAL",
        "PARTIALLY_FILLED",
        "PENDING",
        "PENDING_RECONCILIATION",
        "REJECTED",
    }
)


class ReceiptContractError(ValueError):
    """An observation cannot authorize an action."""


class DurableStateError(RuntimeError):
    """The unresolved-intent ledger is unavailable."""


def _result(
    status: str,
    reason: str,
    *,
    action: bool = False,
    accounting: bool = False,
    learning: bool = False,
    **extra: Any,
) -> Dict[str, Any]:
    outcome: Dict[str, Any] = {
        "status": status,
        "reason": reason,
        "action": action,
        "accounting": accounting,
        "learning": learning,
    }
    outcome.update(extra)
    return outcome


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ReceiptContractError(f"{field}_required")
    return value.strip()


def _decimal(value: Any, field: str, *, allow_zero: bool = False) -> Decimal:
    if isinstance(value, bool) or value is None:
        raise ReceiptContractError(f"{field}_finite_required")
    try:
        number = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ReceiptContractError(f"{field}_finite_required") from exc
    if not number.is_finite():
        raise ReceiptContractError(f"{field}_finite_required")
    if number < 0 or (number == 0 and not allow_zero):
        raise ReceiptContractError(f"{field}_positive_required")
    return number


def _timestamp(value: Any, field: str) -> float:
    if isinstance(value, bool) or value is None:
        raise ReceiptContractError(f"{field}_finite_required")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ReceiptContractError(f"{field}_finite_required") from exc
    if not math.isfinite(number):
        raise ReceiptContractError(f"{field}_finite_required")
    return number


def _required(receipt: Mapping[str, Any], field: str) -> Any:
    if field not in receipt:
        raise ReceiptContractError(f"{field}_required")
    return receipt[field]


def _same_number(left: Decimal, right: Decimal) -> bool:
    scale = max(abs(left), abs(right), Decimal("1"))
    return abs(left - right) <= scale * Decimal("0.00000001")


def _fresh_header(
    receipt: Any,
    *,
    kind: str,
    clock: Callable[[], float],
    max_age_seconds: float,
    truth_status: str,
    venue: Optional[str] = None,
    symbol: Optional[str] = None,
) -> Dict[str, Any]:
    if not isinstance(receipt, Mapping):
        raise ReceiptContractError(f"{kind}_receipt_required")
    data = dict(receipt)
    data["receipt_id"] = _text(
        _required(data, "receipt_id"), f"{kind}_receipt_id"
    )
    data["source_id"] = _text(
        _required(data, "source_id"), f"{kind}_source_id"
    )
    if _required(data, "data_status") != "live":
        raise ReceiptContractError(f"{kind}_live_status_required")
    if _required(data, "truth_status") != truth_status:
        raise ReceiptContractError(f"{kind}_{truth_status}_required")
    if _required(data, "generated_values") is not False:
        raise ReceiptContractError(f"{kind}_generated_values_forbidden")
    source_time = _timestamp(
        _required(data, "source_timestamp"), f"{kind}_source_timestamp"
    )
    received_at = _timestamp(
        _required(data, "received_at"), f"{kind}_received_at"
    )
    now = _timestamp(clock(), "clock")
    if source_time > received_at or received_at > now + 1.0:
        raise ReceiptContractError(f"{kind}_timestamp_order_invalid")
    if now - source_time > max_age_seconds:
        raise ReceiptContractError(f"{kind}_receipt_stale")
    if venue is not None and _text(
        _required(data, "venue"), f"{kind}_venue"
    ).lower() != venue:
        raise ReceiptContractError(f"{kind}_venue_mismatch")
    if symbol is not None and _text(
        _required(data, "symbol"), f"{kind}_symbol"
    ).upper() != symbol:
        raise ReceiptContractError(f"{kind}_symbol_mismatch")
    data["source_timestamp"] = source_time
    data["received_at"] = received_at
    return data


class OrcaSnowballLean:
    """Autonomous, receipt-gated Snowball execution coordinator.

    Existing orchestrators may still pass clients, but a client is usable only
    when it implements the narrow receipt methods declared by _adapter. The
    constructor performs no network calls, credential reads, writes, or provider
    initialization.
    """

    def __init__(
        self,
        clients: Optional[Mapping[str, Any]] = None,
        *,
        receipt_adapters: Optional[Mapping[str, Any]] = None,
        hnc_auris_gate_supplier: Optional[
            Callable[[Mapping[str, Any]], Mapping[str, Any]]
        ] = None,
        opportunity_receipt_supplier: Optional[
            Callable[[], Mapping[str, Any]]
        ] = None,
        portfolio_receipt_supplier: Optional[
            Callable[[], Mapping[str, Any]]
        ] = None,
        clock: Callable[[], float] = time.time,
        sleeper: Callable[[float], None] = time.sleep,
        state_path: Optional[str | Path] = None,
        max_receipt_age_seconds: float = 30.0,
    ) -> None:
        adapters: Dict[str, Any] = {}
        if clients is not None:
            adapters.update(
                {
                    str(name).strip().lower(): client
                    for name, client in clients.items()
                    if client is not None
                }
            )
        if receipt_adapters is not None:
            adapters.update(
                {
                    str(name).strip().lower(): adapter
                    for name, adapter in receipt_adapters.items()
                    if adapter is not None
                }
            )
        self._adapters = adapters
        self._gate_supplier = hnc_auris_gate_supplier
        self._opportunity_supplier = opportunity_receipt_supplier
        self._portfolio_supplier = portfolio_receipt_supplier
        self._clock = clock
        self._sleeper = sleeper
        self._state_path = (
            Path(state_path).expanduser().resolve()
            if state_path is not None
            else None
        )
        age = _timestamp(max_receipt_age_seconds, "max_receipt_age_seconds")
        if age <= 0:
            raise ValueError("max_receipt_age_seconds_must_be_positive")
        self._max_age = age

    @property
    def trades_executed(self) -> Optional[int]:
        state = self._read_state_if_available()
        if state is None:
            return None
        return len(state["committed_receipt_ids"])

    @property
    def total_profit(self) -> Optional[Decimal]:
        state = self._read_state_if_available()
        if state is None or not state["realized"]:
            return None
        total = Decimal("0")
        currency: Optional[str] = None
        for item in state["realized"]:
            item_currency = _text(item["currency"], "realized_currency")
            if currency is None:
                currency = item_currency
            elif currency != item_currency:
                return None
            total += _decimal(
                item["net_profit"], "realized_net_profit", allow_zero=True
            )
        return total

    @staticmethod
    def _empty_state() -> Dict[str, Any]:
        return {
            "schema": "aureon.orca_snowball_lean.receipts.v1",
            "unresolved": None,
            "committed_receipt_ids": [],
            "fills": [],
            "realized": [],
        }

    @staticmethod
    def _validated_state(raw: Any) -> Dict[str, Any]:
        if not isinstance(raw, Mapping):
            raise DurableStateError("durable_state_mapping_required")
        state = dict(raw)
        if state.get("schema") != "aureon.orca_snowball_lean.receipts.v1":
            raise DurableStateError("durable_state_schema_invalid")
        if state.get("unresolved") is not None and not isinstance(
            state["unresolved"], Mapping
        ):
            raise DurableStateError("durable_unresolved_state_invalid")
        for field in ("committed_receipt_ids", "fills", "realized"):
            if not isinstance(state.get(field), list):
                raise DurableStateError(f"durable_{field}_invalid")
        return state

    def _read_state_if_available(self) -> Optional[Dict[str, Any]]:
        if self._state_path is None:
            return None
        if not self._state_path.exists():
            return self._empty_state()
        try:
            raw = json.loads(self._state_path.read_text(encoding="utf-8"))
            return self._validated_state(raw)
        except (OSError, json.JSONDecodeError, DurableStateError):
            return None

    def _load_state(self) -> Dict[str, Any]:
        if self._state_path is None:
            raise DurableStateError("durable_state_path_required")
        if not self._state_path.exists():
            return self._empty_state()
        try:
            raw = json.loads(self._state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise DurableStateError("durable_state_unreadable") from exc
        return self._validated_state(raw)

    def _save_state(self, state: Mapping[str, Any]) -> None:
        if self._state_path is None:
            raise DurableStateError("durable_state_path_required")
        path = self._state_path
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
        payload = json.dumps(state, indent=2, sort_keys=True) + "\n"
        try:
            with temporary.open("x", encoding="utf-8", newline="\n") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
        finally:
            if temporary.exists():
                temporary.unlink()

    @contextmanager
    def _state_lock(self) -> Iterator[None]:
        if self._state_path is None:
            raise DurableStateError("durable_state_path_required")
        lock_path = self._state_path.with_suffix(self._state_path.suffix + ".lock")
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        handle = lock_path.open("a+b")
        try:
            handle.seek(0, os.SEEK_END)
            if handle.tell() == 0:
                handle.write(b"0")
                handle.flush()
                os.fsync(handle.fileno())
            handle.seek(0)
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            handle.close()
            raise DurableStateError("durable_state_lock_busy") from exc
        try:
            yield
        finally:
            handle.seek(0)
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            handle.close()

    def _adapter(self, venue: str) -> Any:
        adapter = self._adapters.get(venue)
        if adapter is None:
            raise ReceiptContractError("venue_receipt_adapter_required")
        methods = (
            "get_quote_receipt",
            "get_account_receipt",
            "get_position_receipt",
            "get_fee_receipt",
            "submit_order_receipt",
            "read_order_receipt",
        )
        if any(not callable(getattr(adapter, name, None)) for name in methods):
            raise ReceiptContractError("complete_venue_receipt_protocol_required")
        return adapter

    def _quote(self, raw: Any, *, venue: str, symbol: str) -> Dict[str, Any]:
        quote = _fresh_header(
            raw,
            kind="quote",
            clock=self._clock,
            max_age_seconds=self._max_age,
            truth_status="real_observed",
            venue=venue,
            symbol=symbol,
        )
        bid = _decimal(_required(quote, "bid"), "quote_bid")
        ask = _decimal(_required(quote, "ask"), "quote_ask")
        if bid > ask:
            raise ReceiptContractError("two_sided_quote_crossed")
        quote_currency = _text(
            _required(quote, "quote_currency"), "quote_currency"
        ).upper()
        quote.update({"bid": bid, "ask": ask, "quote_currency": quote_currency})
        return quote

    def _account(
        self, raw: Any, *, venue: str, quote_currency: str
    ) -> Dict[str, Any]:
        account = _fresh_header(
            raw,
            kind="account",
            clock=self._clock,
            max_age_seconds=self._max_age,
            truth_status="real_observed",
            venue=venue,
        )
        if _required(account, "account_scope") != "complete":
            raise ReceiptContractError("complete_account_scope_required")
        balances = _required(account, "available_balances")
        if not isinstance(balances, Mapping) or quote_currency not in balances:
            raise ReceiptContractError("exact_quote_currency_balance_required")
        account["available_quote_balance"] = _decimal(
            balances[quote_currency],
            "available_quote_balance",
            allow_zero=True,
        )
        account["quote_currency"] = quote_currency
        return account

    def _position(
        self,
        raw: Any,
        *,
        venue: str,
        symbol: str,
        quote_currency: str,
    ) -> Dict[str, Any]:
        position = _fresh_header(
            raw,
            kind="position",
            clock=self._clock,
            max_age_seconds=self._max_age,
            truth_status="real_observed",
            venue=venue,
            symbol=symbol,
        )
        if _required(position, "position_scope") != "complete":
            raise ReceiptContractError("complete_position_scope_required")
        if _required(position, "cost_basis_complete") is not True:
            raise ReceiptContractError("complete_cost_basis_required")
        quantity = _decimal(
            _required(position, "quantity"),
            "position_quantity",
            allow_zero=True,
        )
        cost_basis = _decimal(
            _required(position, "cost_basis_total"),
            "position_cost_basis_total",
            allow_zero=True,
        )
        currency = _text(
            _required(position, "cost_basis_currency"),
            "position_cost_basis_currency",
        ).upper()
        if currency != quote_currency:
            raise ReceiptContractError("position_cost_basis_currency_mismatch")
        if (quantity == 0) != (cost_basis == 0):
            raise ReceiptContractError("position_cost_basis_inconsistent")
        position.update(
            {
                "quantity": quantity,
                "cost_basis_total": cost_basis,
                "cost_basis_currency": currency,
            }
        )
        return position

    def _fee(
        self,
        raw: Any,
        *,
        venue: str,
        symbol: str,
        side: str,
        quote_currency: str,
    ) -> Dict[str, Any]:
        fee = _fresh_header(
            raw,
            kind="fee",
            clock=self._clock,
            max_age_seconds=self._max_age,
            truth_status="real_observed",
            venue=venue,
            symbol=symbol,
        )
        if _required(fee, "fee_schedule_complete") is not True:
            raise ReceiptContractError("complete_fee_schedule_required")
        if _text(_required(fee, "side"), "fee_side").lower() != side:
            raise ReceiptContractError("fee_side_mismatch")
        currency = _text(
            _required(fee, "fee_currency"), "fee_currency"
        ).upper()
        if currency != quote_currency:
            raise ReceiptContractError("fee_currency_mismatch")
        rate = _decimal(
            _required(fee, "taker_rate"), "fee_taker_rate", allow_zero=True
        )
        if rate >= Decimal("1"):
            raise ReceiptContractError("fee_taker_rate_invalid")
        fee.update({"taker_rate": rate, "fee_currency": currency})
        return fee

    def _gate_component(
        self,
        raw: Any,
        *,
        kind: str,
        required_links: set[str],
        metric_fields: tuple[str, ...],
    ) -> Dict[str, Any]:
        component = _fresh_header(
            raw,
            kind=kind,
            clock=self._clock,
            max_age_seconds=self._max_age,
            truth_status="real_derived",
        )
        links_raw = _required(component, "input_receipt_ids")
        if not isinstance(links_raw, list):
            raise ReceiptContractError(f"{kind}_input_receipt_ids_required")
        links = {_text(item, f"{kind}_input_receipt_id") for item in links_raw}
        if not required_links.issubset(links):
            raise ReceiptContractError(f"{kind}_receipt_links_incomplete")
        if _required(component, "eligible_for_action") is not True:
            raise ReceiptContractError(f"{kind}_action_gate_closed")
        for field in metric_fields:
            component[field] = _decimal(
                _required(component, field), f"{kind}_{field}", allow_zero=True
            )
        return component

    def _gate(
        self,
        raw: Any,
        *,
        evidence: Mapping[str, Mapping[str, Any]],
        venue: str,
        symbol: str,
        side: str,
    ) -> Dict[str, Any]:
        gate = _fresh_header(
            raw,
            kind="hnc_auris_gate",
            clock=self._clock,
            max_age_seconds=self._max_age,
            truth_status="real_derived",
        )
        provider_links = {
            str(evidence[name]["receipt_id"])
            for name in ("quote", "account", "position", "fee")
        }
        hnc = self._gate_component(
            _required(gate, "hnc_receipt"),
            kind="hnc",
            required_links=provider_links,
            metric_fields=("hnc_coherence", "lambda_value", "phi_alignment"),
        )
        if not math.isclose(
            float(hnc["phi_alignment"]), PHI, rel_tol=0.0, abs_tol=1e-12
        ):
            raise ReceiptContractError("hnc_phi_alignment_invalid")
        auris = self._gate_component(
            _required(gate, "auris_receipt"),
            kind="auris",
            required_links=provider_links | {str(hnc["receipt_id"])},
            metric_fields=("auris_coherence", "auris_resonance"),
        )
        root_links_raw = _required(gate, "input_receipt_ids")
        if not isinstance(root_links_raw, list):
            raise ReceiptContractError("hnc_auris_input_receipt_ids_required")
        root_links = {
            _text(item, "hnc_auris_input_receipt_id")
            for item in root_links_raw
        }
        required_root_links = provider_links | {
            str(hnc["receipt_id"]),
            str(auris["receipt_id"]),
        }
        if not required_root_links.issubset(root_links):
            raise ReceiptContractError("hnc_auris_receipt_links_incomplete")
        if _required(gate, "eligible_for_action") is not True:
            raise ReceiptContractError("hnc_auris_action_gate_closed")
        if _text(_required(gate, "venue"), "gate_venue").lower() != venue:
            raise ReceiptContractError("hnc_auris_venue_mismatch")
        if _text(_required(gate, "symbol"), "gate_symbol").upper() != symbol:
            raise ReceiptContractError("hnc_auris_symbol_mismatch")
        if _text(_required(gate, "side"), "gate_side").lower() != side:
            raise ReceiptContractError("hnc_auris_side_mismatch")
        quote_currency = str(evidence["quote"]["quote_currency"])
        gate_currency = _text(
            _required(gate, "authorization_currency"),
            "authorization_currency",
        ).upper()
        if gate_currency != quote_currency:
            raise ReceiptContractError("authorization_currency_mismatch")
        gate["hnc_receipt"] = hnc
        gate["auris_receipt"] = auris
        gate["authorization_currency"] = gate_currency
        gate["authorized_notional"] = _decimal(
            _required(gate, "authorized_notional"),
            "authorized_notional",
        )
        if side == "sell":
            gate["authorized_quantity"] = _decimal(
                _required(gate, "authorized_quantity"),
                "authorized_quantity",
            )
            gate["minimum_net_profit"] = _decimal(
                _required(gate, "minimum_net_profit"),
                "minimum_net_profit",
                allow_zero=True,
            )
        return gate

    def _evidence(
        self, *, venue: str, symbol: str, side: str
    ) -> Dict[str, Any]:
        adapter = self._adapter(venue)
        quote = self._quote(
            adapter.get_quote_receipt(symbol), venue=venue, symbol=symbol
        )
        account = self._account(
            adapter.get_account_receipt(),
            venue=venue,
            quote_currency=str(quote["quote_currency"]),
        )
        position = self._position(
            adapter.get_position_receipt(symbol),
            venue=venue,
            symbol=symbol,
            quote_currency=str(quote["quote_currency"]),
        )
        fee = self._fee(
            adapter.get_fee_receipt(symbol, side),
            venue=venue,
            symbol=symbol,
            side=side,
            quote_currency=str(quote["quote_currency"]),
        )
        evidence: Dict[str, Any] = {
            "quote": quote,
            "account": account,
            "position": position,
            "fee": fee,
        }
        if not callable(self._gate_supplier):
            raise ReceiptContractError("hnc_auris_gate_supplier_required")
        gate_request = {
            "venue": venue,
            "symbol": symbol,
            "side": side,
            "provider_receipt_ids": {
                name: str(item["receipt_id"])
                for name, item in evidence.items()
            },
            "quote_currency": str(quote["quote_currency"]),
        }
        evidence["gate"] = self._gate(
            self._gate_supplier(gate_request),
            evidence=evidence,
            venue=venue,
            symbol=symbol,
            side=side,
        )
        return evidence

    def _plan(
        self,
        *,
        strategy: str,
        venue: str,
        symbol: str,
        side: str,
        evidence: Mapping[str, Any],
    ) -> Dict[str, Any]:
        quote = evidence["quote"]
        account = evidence["account"]
        position = evidence["position"]
        fee = evidence["fee"]
        gate = evidence["gate"]
        currency = str(quote["quote_currency"])
        rate: Decimal = fee["taker_rate"]
        if side == "buy":
            price: Decimal = quote["ask"]
            authorized_notional: Decimal = gate["authorized_notional"]
            fee_reserve = authorized_notional * rate
            if (
                account["available_quote_balance"]
                < authorized_notional + fee_reserve
            ):
                raise ReceiptContractError("insufficient_exact_quote_balance")
            quantity = authorized_notional / price
            planned_notional = quantity * price
        else:
            price = quote["bid"]
            quantity = gate["authorized_quantity"]
            if position["quantity"] == 0 or quantity > position["quantity"]:
                raise ReceiptContractError("insufficient_observed_position")
            planned_notional = quantity * price
            if planned_notional > gate["authorized_notional"]:
                raise ReceiptContractError("sell_notional_exceeds_authorization")
            allocated_cost = (
                position["cost_basis_total"] * quantity / position["quantity"]
            )
            projected_fee = planned_notional * rate
            projected_net_profit = (
                planned_notional - projected_fee - allocated_cost
            )
            if projected_net_profit < gate["minimum_net_profit"]:
                raise ReceiptContractError("net_profit_gate_not_met")
        receipt_ids = {
            name: str(evidence[name]["receipt_id"])
            for name in ("quote", "account", "position", "fee", "gate")
        }
        client_order_id = (
            "snowball:"
            + strategy
            + ":"
            + venue
            + ":"
            + symbol
            + ":"
            + side
            + ":"
            + ":".join(receipt_ids.values())
        )
        return {
            "client_order_id": client_order_id,
            "strategy": strategy,
            "venue": venue,
            "symbol": symbol,
            "side": side,
            "quantity": str(quantity),
            "planned_price": str(price),
            "planned_notional": str(planned_notional),
            "quote_currency": currency,
            "provider_receipt_ids": receipt_ids,
            "position_quantity": str(position["quantity"]),
            "position_cost_basis_total": str(position["cost_basis_total"]),
            "position_cost_basis_currency": str(
                position["cost_basis_currency"]
            ),
            "reserved_at": _timestamp(self._clock(), "clock"),
        }

    def _terminal_fill(
        self, raw: Any, unresolved: Mapping[str, Any]
    ) -> Dict[str, Any]:
        venue = _text(unresolved["venue"], "unresolved_venue")
        symbol = _text(unresolved["symbol"], "unresolved_symbol")
        side = _text(unresolved["side"], "unresolved_side")
        fill = _fresh_header(
            raw,
            kind="terminal_fill",
            clock=self._clock,
            max_age_seconds=self._max_age,
            truth_status="real_observed",
            venue=venue,
            symbol=symbol,
        )
        if _required(fill, "status") != _TERMINAL_FILL_STATUS:
            raise ReceiptContractError("terminal_fill_status_required")
        if _required(fill, "fill_receipt_complete") is not True:
            raise ReceiptContractError("complete_terminal_fill_required")
        if _required(fill, "eligible_for_accounting") is not True:
            raise ReceiptContractError(
                "terminal_fill_accounting_eligibility_required"
            )
        if _required(fill, "eligible_for_learning") is not True:
            raise ReceiptContractError(
                "terminal_fill_learning_eligibility_required"
            )
        if _required(fill, "reconciliation_required") is not False:
            raise ReceiptContractError("terminal_fill_reconciliation_incomplete")
        if _text(_required(fill, "side"), "terminal_fill_side").lower() != side:
            raise ReceiptContractError("terminal_fill_side_mismatch")
        if _text(
            _required(fill, "client_order_id"), "terminal_fill_client_order_id"
        ) != unresolved["client_order_id"]:
            raise ReceiptContractError("terminal_fill_client_order_id_mismatch")
        provider_order_id = _text(
            _required(fill, "provider_order_id"),
            "terminal_fill_provider_order_id",
        )
        latched_order_id = unresolved.get("provider_order_id")
        if latched_order_id is not None and provider_order_id != latched_order_id:
            raise ReceiptContractError(
                "terminal_fill_provider_order_id_mismatch"
            )
        receipt_type = _text(
            _required(fill, "provider_receipt_type"),
            "terminal_fill_provider_receipt_type",
        )
        quantity = _decimal(_required(fill, "filled_quantity"), "filled_quantity")
        expected_quantity = _decimal(unresolved["quantity"], "requested_quantity")
        if not _same_number(quantity, expected_quantity):
            raise ReceiptContractError("partial_fill_not_terminal_success")
        price = _decimal(
            _required(fill, "filled_average_price"), "filled_average_price"
        )
        notional = _decimal(
            _required(fill, "filled_notional"), "filled_notional"
        )
        if not _same_number(notional, quantity * price):
            raise ReceiptContractError("terminal_fill_notional_inconsistent")
        currency = _text(
            _required(fill, "notional_currency"), "fill_notional_currency"
        ).upper()
        if currency != unresolved["quote_currency"]:
            raise ReceiptContractError("terminal_fill_currency_mismatch")
        fee = _decimal(
            _required(fill, "fee"), "terminal_fill_fee", allow_zero=True
        )
        fee_currency = _text(
            _required(fill, "fee_currency"), "terminal_fill_fee_currency"
        ).upper()
        if fee_currency != currency:
            raise ReceiptContractError("terminal_fill_fee_currency_mismatch")
        provider_time = _timestamp(
            _required(fill, "provider_timestamp"),
            "terminal_fill_provider_timestamp",
        )
        now = _timestamp(self._clock(), "clock")
        if (
            provider_time > float(fill["received_at"])
            or provider_time > now + 1.0
            or now - provider_time > self._max_age
        ):
            raise ReceiptContractError("terminal_fill_provider_time_invalid")
        if provider_time + 1.0 < float(unresolved["reserved_at"]):
            raise ReceiptContractError("terminal_fill_precedes_intent")
        fill.update(
            {
                "provider_order_id": provider_order_id,
                "provider_receipt_type": receipt_type,
                "filled_quantity": quantity,
                "filled_average_price": price,
                "filled_notional": notional,
                "notional_currency": currency,
                "fee": fee,
                "fee_currency": fee_currency,
                "provider_timestamp": provider_time,
            }
        )
        return fill

    def _commit_fill(
        self,
        state: Dict[str, Any],
        unresolved: Mapping[str, Any],
        fill: Mapping[str, Any],
    ) -> Dict[str, Any]:
        receipt_id = str(fill["receipt_id"])
        committed = state["committed_receipt_ids"]
        if receipt_id in committed:
            return _result(
                "no_data",
                "duplicate_terminal_fill_receipt",
                receipt_id=receipt_id,
            )
        record = {
            "receipt_id": receipt_id,
            "provider_receipt_type": str(fill["provider_receipt_type"]),
            "provider_order_id": str(fill["provider_order_id"]),
            "client_order_id": str(unresolved["client_order_id"]),
            "venue": str(unresolved["venue"]),
            "symbol": str(unresolved["symbol"]),
            "side": str(unresolved["side"]),
            "filled_quantity": str(fill["filled_quantity"]),
            "filled_average_price": str(fill["filled_average_price"]),
            "filled_notional": str(fill["filled_notional"]),
            "notional_currency": str(fill["notional_currency"]),
            "fee": str(fill["fee"]),
            "fee_currency": str(fill["fee_currency"]),
            "provider_timestamp": float(fill["provider_timestamp"]),
            "source_timestamp": float(fill["source_timestamp"]),
            "received_at": float(fill["received_at"]),
            "provider_receipt_ids": dict(unresolved["provider_receipt_ids"]),
        }
        realized_record: Optional[Dict[str, Any]] = None
        if unresolved["side"] == "sell":
            position_quantity = _decimal(
                unresolved["position_quantity"], "position_quantity"
            )
            cost_basis_total = _decimal(
                unresolved["position_cost_basis_total"],
                "position_cost_basis_total",
            )
            filled_quantity: Decimal = fill["filled_quantity"]
            allocated_cost = (
                cost_basis_total * filled_quantity / position_quantity
            )
            net_proceeds = fill["filled_notional"] - fill["fee"]
            net_profit = net_proceeds - allocated_cost
            realized_record = {
                "fill_receipt_id": receipt_id,
                "currency": str(fill["notional_currency"]),
                "gross_proceeds": str(fill["filled_notional"]),
                "fee": str(fill["fee"]),
                "allocated_cost_basis": str(allocated_cost),
                "net_profit": str(net_profit),
            }
        committed.append(receipt_id)
        state["fills"].append(record)
        if realized_record is not None:
            state["realized"].append(realized_record)
        state["unresolved"] = None
        self._save_state(state)
        return _result(
            _TERMINAL_FILL_STATUS,
            "complete_terminal_fill_committed",
            action=True,
            accounting=True,
            learning=True,
            receipt_id=receipt_id,
            fill=record,
            realized=realized_record,
        )

    def _acknowledgement(
        self, raw: Any, unresolved: Mapping[str, Any]
    ) -> Dict[str, Any]:
        if not isinstance(raw, Mapping):
            raise ReceiptContractError("provider_acknowledgement_required")
        acknowledgement = dict(raw)
        status = _text(
            _required(acknowledgement, "status"), "provider_order_status"
        ).upper()
        if status == _TERMINAL_FILL_STATUS:
            raise ReceiptContractError("terminal_fill_requires_full_validation")
        if status not in _NON_FILL_STATUSES:
            raise ReceiptContractError("recognized_provider_order_status_required")
        if _text(
            _required(acknowledgement, "venue"), "provider_order_venue"
        ).lower() != unresolved["venue"]:
            raise ReceiptContractError("provider_order_venue_mismatch")
        if _text(
            _required(acknowledgement, "symbol"), "provider_order_symbol"
        ).upper() != unresolved["symbol"]:
            raise ReceiptContractError("provider_order_symbol_mismatch")
        if _text(
            _required(acknowledgement, "side"), "provider_order_side"
        ).lower() != unresolved["side"]:
            raise ReceiptContractError("provider_order_side_mismatch")
        if _text(
            _required(acknowledgement, "client_order_id"),
            "provider_client_order_id",
        ) != unresolved["client_order_id"]:
            raise ReceiptContractError("provider_client_order_id_mismatch")
        if status != "DRY_RUN":
            _fresh_header(
                acknowledgement,
                kind="provider_order",
                clock=self._clock,
                max_age_seconds=self._max_age,
                truth_status="real_observed",
                venue=str(unresolved["venue"]),
                symbol=str(unresolved["symbol"]),
            )
            _text(
                _required(acknowledgement, "provider_receipt_type"),
                "provider_order_receipt_type",
            )
        provider_order_id = acknowledgement.get("provider_order_id")
        if provider_order_id is not None:
            provider_order_id = _text(
                provider_order_id, "provider_order_id"
            )
            latched_order_id = unresolved.get("provider_order_id")
            if (
                latched_order_id is not None
                and provider_order_id != latched_order_id
            ):
                raise ReceiptContractError("provider_order_id_mismatch")
        return {"status": status, "provider_order_id": provider_order_id}

    def _reconcile_locked(
        self, state: Dict[str, Any], adapter: Any
    ) -> Dict[str, Any]:
        unresolved = state["unresolved"]
        if unresolved is None:
            return _result("no_data", "no_unresolved_intent")
        try:
            raw = adapter.read_order_receipt(dict(unresolved))
        except Exception:
            return _result(
                "pending_reconciliation",
                "provider_readback_unavailable",
                client_order_id=unresolved["client_order_id"],
            )
        try:
            fill = self._terminal_fill(raw, unresolved)
        except ReceiptContractError as fill_error:
            try:
                acknowledgement = self._acknowledgement(raw, unresolved)
            except ReceiptContractError:
                return _result(
                    "pending_reconciliation",
                    str(fill_error),
                    client_order_id=unresolved["client_order_id"],
                )
            status = acknowledgement["status"]
            if acknowledgement["provider_order_id"] is not None:
                unresolved["provider_order_id"] = acknowledgement[
                    "provider_order_id"
                ]
                state["unresolved"] = unresolved
                self._save_state(state)
            if status in {"REJECTED", "CANCELED", "CANCELLED", "EXPIRED"}:
                state["unresolved"] = None
                self._save_state(state)
                return _result(
                    status.lower(),
                    "provider_order_terminal_non_fill",
                    client_order_id=unresolved["client_order_id"],
                )
            return _result(
                "pending_reconciliation",
                "terminal_fill_receipt_not_yet_complete",
                client_order_id=unresolved["client_order_id"],
            )
        return self._commit_fill(state, unresolved, fill)

    def reconcile_unresolved(self) -> Dict[str, Any]:
        """Perform at most one provider read-back for the durable intent."""
        try:
            with self._state_lock():
                state = self._load_state()
                unresolved = state["unresolved"]
                if unresolved is None:
                    return _result("no_data", "no_unresolved_intent")
                adapter = self._adapter(str(unresolved["venue"]))
                return self._reconcile_locked(state, adapter)
        except (DurableStateError, ReceiptContractError) as exc:
            return _result("no_data", str(exc))

    def _execute(
        self, *, strategy: str, venue: str, symbol: str, side: str
    ) -> Dict[str, Any]:
        venue = _text(venue, "venue").lower()
        symbol = _text(symbol, "symbol").upper()
        side = _text(side, "side").lower()
        if side not in {"buy", "sell"}:
            return _result("no_data", "supported_order_side_required")
        try:
            adapter = self._adapter(venue)
            with self._state_lock():
                state = self._load_state()
                if state["unresolved"] is not None:
                    unresolved_venue = str(state["unresolved"]["venue"])
                    if unresolved_venue != venue:
                        return _result(
                            "pending_reconciliation",
                            "unresolved_other_venue_blocks_submission",
                        )
                    return self._reconcile_locked(state, adapter)
                evidence = self._evidence(
                    venue=venue, symbol=symbol, side=side
                )
                plan = self._plan(
                    strategy=strategy,
                    venue=venue,
                    symbol=symbol,
                    side=side,
                    evidence=evidence,
                )
                state["unresolved"] = dict(plan)
                self._save_state(state)
                try:
                    raw = adapter.submit_order_receipt(dict(plan))
                except Exception:
                    return _result(
                        "pending_reconciliation",
                        "submission_outcome_unknown",
                        client_order_id=plan["client_order_id"],
                    )
                try:
                    fill = self._terminal_fill(raw, plan)
                except ReceiptContractError:
                    try:
                        acknowledgement = self._acknowledgement(raw, plan)
                    except ReceiptContractError:
                        return _result(
                            "pending_reconciliation",
                            "submission_receipt_incomplete",
                            client_order_id=plan["client_order_id"],
                        )
                    status = acknowledgement["status"]
                    if status == "DRY_RUN":
                        state["unresolved"] = None
                        self._save_state(state)
                        return _result(
                            "dry_run",
                            "dry_run_is_not_provider_execution",
                            client_order_id=plan["client_order_id"],
                        )
                    if acknowledgement["provider_order_id"] is not None:
                        plan["provider_order_id"] = acknowledgement[
                            "provider_order_id"
                        ]
                        state["unresolved"] = dict(plan)
                        self._save_state(state)
                    if status in {
                        "REJECTED",
                        "CANCELED",
                        "CANCELLED",
                        "EXPIRED",
                    }:
                        state["unresolved"] = None
                        self._save_state(state)
                        return _result(
                            status.lower(),
                            "provider_order_terminal_non_fill",
                            client_order_id=plan["client_order_id"],
                        )
                    return _result(
                        "pending_reconciliation",
                        "provider_acknowledgement_is_not_fill",
                        client_order_id=plan["client_order_id"],
                    )
                return self._commit_fill(state, plan, fill)
        except (DurableStateError, ReceiptContractError) as exc:
            return _result("no_data", str(exc))

    def execute_momentum(self, opportunity: Mapping[str, Any]) -> Dict[str, Any]:
        """Execute a provider-receipt momentum action through HNC/Auris."""
        try:
            return self._execute(
                strategy="momentum",
                venue=_text(_required(opportunity, "venue"), "venue"),
                symbol=_text(_required(opportunity, "symbol"), "symbol"),
                side="buy",
            )
        except ReceiptContractError as exc:
            return _result("no_data", str(exc))

    def execute_dip(self, opportunity: Mapping[str, Any]) -> Dict[str, Any]:
        """Execute a provider-receipt dip action through HNC/Auris."""
        try:
            return self._execute(
                strategy="dip",
                venue=_text(_required(opportunity, "venue"), "venue"),
                symbol=_text(_required(opportunity, "symbol"), "symbol"),
                side="buy",
            )
        except ReceiptContractError as exc:
            return _result("no_data", str(exc))

    def execute_profit_exit(
        self, opportunity: Mapping[str, Any]
    ) -> Dict[str, Any]:
        """Execute a net-profit-qualified exit through HNC/Auris."""
        try:
            return self._execute(
                strategy="profit_exit",
                venue=_text(_required(opportunity, "venue"), "venue"),
                symbol=_text(_required(opportunity, "symbol"), "symbol"),
                side="sell",
            )
        except ReceiptContractError as exc:
            return _result("no_data", str(exc))

    def execute_arbitrage(
        self, opportunity: Mapping[str, Any]
    ) -> Dict[str, Any]:
        """Execute one explicitly authorized leg of a receipt-linked cycle.

        Cross-venue orchestration supplies the current leg identity. This
        coordinator never assumes inventory exists at the opposite venue and
        never treats one leg acknowledgement as a completed arbitrage cycle.
        """
        try:
            return self._execute(
                strategy="arbitrage_leg",
                venue=_text(
                    _required(opportunity, "execution_venue"),
                    "execution_venue",
                ),
                symbol=_text(
                    _required(opportunity, "execution_symbol"),
                    "execution_symbol",
                ),
                side=_text(
                    _required(opportunity, "execution_side"),
                    "execution_side",
                ),
            )
        except ReceiptContractError as exc:
            return _result("no_data", str(exc))

    def check_profit_targets(
        self, opportunities: Optional[List[Mapping[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Evaluate only receipt-originated exit opportunities."""
        if not opportunities:
            return _result("no_data", "profit_exit_opportunity_receipt_required")
        for opportunity in opportunities:
            if opportunity.get("type") == "PROFIT_EXIT":
                return self.execute_profit_exit(opportunity)
        return _result("no_data", "no_profit_exit_opportunity")

    def _portfolio(self) -> Dict[str, Any]:
        if not callable(self._portfolio_supplier):
            return _result("no_data", "portfolio_receipt_supplier_required")
        try:
            receipt = _fresh_header(
                self._portfolio_supplier(),
                kind="portfolio",
                clock=self._clock,
                max_age_seconds=self._max_age,
                truth_status="real_observed",
            )
            if _required(receipt, "portfolio_scope") != "complete":
                raise ReceiptContractError("complete_portfolio_scope_required")
            value = _decimal(
                _required(receipt, "total_value"),
                "portfolio_total_value",
                allow_zero=True,
            )
            currency = _text(
                _required(receipt, "currency"), "portfolio_currency"
            ).upper()
            return _result(
                "observed",
                "complete_portfolio_receipt",
                receipt_id=str(receipt["receipt_id"]),
                total_value=str(value),
                currency=currency,
            )
        except ReceiptContractError as exc:
            return _result("no_data", str(exc))

    def get_portfolio_value(self) -> Dict[str, Any]:
        """Return a complete observed portfolio envelope, never a guessed sum."""
        return self._portfolio()

    @staticmethod
    def _doublings_needed(value: Decimal) -> Optional[int]:
        if value <= 0:
            return None
        doublings = 0
        current = value
        while current < MILLION:
            current *= 2
            doublings += 1
        return doublings

    def _opportunities(self) -> Dict[str, Any]:
        if not callable(self._opportunity_supplier):
            return _result("no_data", "opportunity_receipt_supplier_required")
        try:
            receipt = _fresh_header(
                self._opportunity_supplier(),
                kind="opportunity",
                clock=self._clock,
                max_age_seconds=self._max_age,
                truth_status="real_derived",
            )
            items = _required(receipt, "opportunities")
            if not isinstance(items, list):
                raise ReceiptContractError("opportunity_list_required")
            accepted: List[Dict[str, Any]] = []
            for item in items:
                if not isinstance(item, Mapping):
                    raise ReceiptContractError("opportunity_mapping_required")
                candidate = dict(item)
                candidate["type"] = _text(
                    _required(candidate, "type"), "opportunity_type"
                ).upper()
                candidate["rank"] = _decimal(
                    _required(candidate, "rank"),
                    "opportunity_rank",
                    allow_zero=True,
                )
                candidate["source_receipt_id"] = str(receipt["receipt_id"])
                accepted.append(candidate)
            accepted.sort(key=lambda item: item["rank"], reverse=True)
            return _result(
                "observed",
                "complete_opportunity_receipt",
                receipt_id=str(receipt["receipt_id"]),
                opportunities=accepted,
            )
        except ReceiptContractError as exc:
            return _result("no_data", str(exc))

    def scan_arbitrage(self) -> List[Dict[str, Any]]:
        """Keep the legacy ungated export inert.

        Existing external consumers convert these dictionaries into action
        candidates without preserving receipt links. Autonomous execution now
        stays inside run_cycle, where every leg crosses the HNC/Auris gate.
        """
        return []

    def scan_momentum(self) -> List[Dict[str, Any]]:
        """Keep the legacy ungated export inert; use run_cycle."""
        return []

    def scan_kraken_dips(self) -> List[Dict[str, Any]]:
        """Keep the legacy ungated export inert; use run_cycle."""
        return []

    def run_cycle(self) -> Dict[str, Any]:
        """Run one bounded autonomous cycle with at most one order read-back."""
        state = self._read_state_if_available()
        if state is None and self._state_path is not None:
            return _result("no_data", "durable_state_unreadable")
        if state is not None and state["unresolved"] is not None:
            return self.reconcile_unresolved()
        portfolio = self._portfolio()
        if portfolio["status"] != "observed":
            return portfolio
        value = _decimal(
            portfolio["total_value"], "portfolio_total_value", allow_zero=True
        )
        if value == 0:
            return _result(
                "no_data",
                "zero_portfolio_has_no_actionable_capital",
                receipt_id=portfolio["receipt_id"],
            )
        if value >= MILLION:
            return _result(
                "complete",
                "portfolio_target_observed",
                receipt_id=portfolio["receipt_id"],
                currency=portfolio["currency"],
            )
        opportunities = self._opportunities()
        if opportunities["status"] != "observed":
            return opportunities
        items = opportunities["opportunities"]
        if not items:
            return _result(
                "no_data",
                "complete_opportunity_receipt_contains_no_actions",
                receipt_id=opportunities["receipt_id"],
            )
        candidate = items[0]
        candidate_type = candidate["type"]
        if candidate_type == "PROFIT_EXIT":
            return self.execute_profit_exit(candidate)
        if candidate_type == "ARBITRAGE":
            return self.execute_arbitrage(candidate)
        if candidate_type == "MOMENTUM":
            return self.execute_momentum(candidate)
        if candidate_type == "DIP_BUY":
            return self.execute_dip(candidate)
        return _result("no_data", "unsupported_opportunity_type")

    def run_forever(self, cycle_seconds: Optional[float] = None) -> Dict[str, Any]:
        """Run autonomous bounded cycles; cadence must be explicitly supplied."""
        if cycle_seconds is None:
            return _result("no_data", "explicit_cycle_seconds_required")
        interval = _timestamp(cycle_seconds, "cycle_seconds")
        if interval <= 0:
            return _result("no_data", "positive_cycle_seconds_required")
        while True:
            outcome = self.run_cycle()
            if outcome["status"] == "complete":
                return outcome
            self._sleeper(interval)
