#!/usr/bin/env python3
"""Receipt-gated, fail-closed GAIA position reclaimer.

Importing this module never constructs a provider client or changes process
state.  A runtime caller must inject venue-specific adapters whose methods
return fresh provider receipts.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import time
from contextlib import contextmanager
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Callable, Mapping, Protocol, Sequence

# Sacred Constants
PHI = (1 + math.sqrt(5)) / 2
SCHUMANN = 7.83

_OPEN_STATUSES = frozenset(
    {"ack", "acknowledged", "accepted", "new", "open", "pending", "partially_filled"}
)
_FILLED_STATUSES = frozenset({"complete", "completed", "executed", "filled"})
_REJECTED_STATUSES = frozenset({"cancelled", "canceled", "expired", "rejected"})


class VenueAdapter(Protocol):
    """Narrow provider boundary; implementations live outside this module."""

    venue: str

    def get_account_receipt(self) -> Mapping[str, Any]: ...

    def get_position_receipts(self) -> Sequence[Mapping[str, Any]]: ...

    def get_market_receipt(self, symbol: str) -> Mapping[str, Any]: ...

    def get_cost_basis_receipt(self, symbol: str) -> Mapping[str, Any]: ...

    def submit_market_order(
        self,
        *,
        symbol: str,
        side: str,
        quantity: str,
        client_order_id: str,
    ) -> Mapping[str, Any]: ...

    def read_order_receipt(self, order_reference: str) -> Mapping[str, Any]: ...


def _decimal(value: Any, field: str, *, positive: bool = False, nonnegative: bool = False) -> Decimal:
    if isinstance(value, bool) or value is None:
        raise ValueError(f"{field} must be a finite number")
    try:
        number = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be a finite number") from exc
    if not number.is_finite():
        raise ValueError(f"{field} must be finite")
    if positive and number <= 0:
        raise ValueError(f"{field} must be positive")
    if nonnegative and number < 0:
        raise ValueError(f"{field} must be nonnegative")
    return number


def _provider_epoch(value: Any) -> float:
    if isinstance(value, bool) or value is None:
        raise ValueError("provider_timestamp is required")
    if isinstance(value, (int, float)):
        stamp = float(value)
    elif isinstance(value, str):
        text = value.strip()
        if not text:
            raise ValueError("provider_timestamp is required")
        try:
            stamp = float(text)
        except ValueError:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                raise ValueError("provider_timestamp must include a timezone")
            stamp = parsed.timestamp()
    else:
        raise ValueError("provider_timestamp has an unsupported type")
    if not math.isfinite(stamp):
        raise ValueError("provider_timestamp must be finite")
    return stamp


class AggressiveReclaimer:
    """Exit profitable positions only when every input is provider evidenced."""

    def __init__(
        self,
        adapters: Mapping[str, VenueAdapter] | None = None,
        *,
        state_path: str | Path | None = None,
        min_net_profit_pct: Decimal | str = Decimal("0.01"),
        max_receipt_age_seconds: float = 30.0,
        now: Callable[[], float] = time.time,
        logger: Callable[[str], None] | None = None,
    ) -> None:
        self.adapters: dict[str, VenueAdapter] = {}
        for name, adapter in (adapters or {}).items():
            venue = str(getattr(adapter, "venue", "")).strip().lower()
            if not venue or venue != str(name).strip().lower():
                raise ValueError("adapter mapping keys must exactly match adapter.venue")
            self.adapters[venue] = adapter
        self.state_path = Path(state_path) if state_path is not None else (
            Path.cwd() / ".aureon" / "gaia_aggressive_reclaimer_state.json"
        )
        self.min_net_profit_pct = _decimal(
            min_net_profit_pct, "min_net_profit_pct", nonnegative=True
        )
        self.max_receipt_age_seconds = float(max_receipt_age_seconds)
        if not math.isfinite(self.max_receipt_age_seconds) or self.max_receipt_age_seconds <= 0:
            raise ValueError("max_receipt_age_seconds must be finite and positive")
        self._now = now
        self._logger = logger

    def log(self, message: str) -> None:
        if self._logger is not None:
            self._logger(message)

    def _empty_state(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "pending": {},
            "applied_fill_receipt_ids": [],
            "trade_count": 0,
            "filled_notional_by_currency": {},
            "fee_totals_by_currency": {},
            "realized_pnl_by_currency": {},
        }

    def _load_state(self) -> dict[str, Any]:
        if not self.state_path.exists():
            return self._empty_state()
        data = json.loads(self.state_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or data.get("schema_version") != 1:
            raise ValueError("GAIA state has an unsupported schema")
        required = {
            "pending",
            "applied_fill_receipt_ids",
            "trade_count",
            "filled_notional_by_currency",
            "fee_totals_by_currency",
            "realized_pnl_by_currency",
        }
        if not required.issubset(data):
            raise ValueError("GAIA state is incomplete")
        if not isinstance(data["pending"], dict) or not isinstance(data["applied_fill_receipt_ids"], list):
            raise ValueError("GAIA state lifecycle fields are invalid")
        if (
            isinstance(data["trade_count"], bool)
            or not isinstance(data["trade_count"], int)
            or data["trade_count"] < 0
        ):
            raise ValueError("GAIA trade count is invalid")
        if any(
            not isinstance(receipt_id, str) or not receipt_id.strip()
            for receipt_id in data["applied_fill_receipt_ids"]
        ):
            raise ValueError("GAIA applied receipt ids are invalid")
        for bucket_name in (
            "filled_notional_by_currency",
            "fee_totals_by_currency",
            "realized_pnl_by_currency",
        ):
            bucket = data[bucket_name]
            if not isinstance(bucket, dict):
                raise ValueError(f"GAIA {bucket_name} is invalid")
            for currency, value in bucket.items():
                if not isinstance(currency, str) or not currency.strip():
                    raise ValueError(f"GAIA {bucket_name} currency is invalid")
                _decimal(value, f"{bucket_name}.{currency}")
        return data

    def _save_state(self, state: Mapping[str, Any]) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.state_path.with_suffix(self.state_path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(state, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, self.state_path)

    @contextmanager
    def _state_lock(self):
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        lock_path = self.state_path.with_suffix(self.state_path.suffix + ".lock")
        try:
            descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError as exc:
            raise RuntimeError(
                f"GAIA state is locked; inspect the unresolved lock at {lock_path}"
            ) from exc
        try:
            os.write(descriptor, str(os.getpid()).encode("ascii"))
            os.close(descriptor)
            descriptor = -1
            yield
        finally:
            if descriptor >= 0:
                os.close(descriptor)
            lock_path.unlink(missing_ok=True)

    def _base_receipt(
        self,
        receipt: Mapping[str, Any],
        *,
        venue: str,
        receipt_type: str,
    ) -> dict[str, Any]:
        if not isinstance(receipt, Mapping):
            raise ValueError(f"{receipt_type} receipt is missing")
        data = dict(receipt)
        for field in ("receipt_id", "provider", "venue", "receipt_type"):
            if not isinstance(data.get(field), str) or not data[field].strip():
                raise ValueError(f"{receipt_type}.{field} is required")
        if data["venue"].strip().lower() != venue:
            raise ValueError("cross-venue receipt relabeling is forbidden")
        if data["provider"].strip().lower() != venue:
            raise ValueError("provider must match the injected venue")
        if data["receipt_type"].strip().lower() != receipt_type:
            raise ValueError(f"expected a {receipt_type} receipt")
        observed = _provider_epoch(data.get("provider_timestamp"))
        now = float(self._now())
        if not math.isfinite(now):
            raise ValueError("runtime clock must be finite")
        if observed > now + 5.0 or now - observed > self.max_receipt_age_seconds:
            raise ValueError(f"{receipt_type} receipt is stale or future-dated")
        return data

    @staticmethod
    def _required_text(receipt: Mapping[str, Any], field: str) -> str:
        value = receipt.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field} is required")
        return value.strip()

    def _select_exit(self, venue: str, adapter: VenueAdapter) -> dict[str, Any] | None:
        account = self._base_receipt(
            adapter.get_account_receipt(), venue=venue, receipt_type="account"
        )
        account_id = self._required_text(account, "account_id")
        if account.get("provider_account_status") != "active":
            raise ValueError("provider account is not active")
        if account.get("trading_permitted") is not True:
            raise ValueError("provider account does not explicitly permit trading")

        positions = adapter.get_position_receipts()
        if not isinstance(positions, Sequence) or isinstance(positions, (str, bytes)):
            raise ValueError("position receipt collection is missing")

        candidates: list[dict[str, Any]] = []
        for raw_position in positions:
            position = self._base_receipt(
                raw_position, venue=venue, receipt_type="position"
            )
            if self._required_text(position, "account_id") != account_id:
                raise ValueError("position account does not match account receipt")
            symbol = self._required_text(position, "symbol")
            quantity = _decimal(position.get("quantity"), "position.quantity", nonnegative=True)
            sellable = _decimal(
                position.get("sellable_quantity"),
                "position.sellable_quantity",
                nonnegative=True,
            )
            if quantity == 0:
                if sellable != 0:
                    raise ValueError("zero position cannot have sellable quantity")
                continue
            if sellable != quantity:
                raise ValueError("only a complete provider-confirmed position can be reclaimed")

            market = self._base_receipt(
                adapter.get_market_receipt(symbol), venue=venue, receipt_type="market"
            )
            basis = self._base_receipt(
                adapter.get_cost_basis_receipt(symbol),
                venue=venue,
                receipt_type="cost_basis",
            )
            if self._required_text(market, "symbol") != symbol:
                raise ValueError("market symbol does not match position")
            if self._required_text(basis, "symbol") != symbol:
                raise ValueError("cost-basis symbol does not match position")
            if self._required_text(basis, "account_id") != account_id:
                raise ValueError("cost-basis account does not match account receipt")
            if market.get("actionable") is not True:
                raise ValueError("market receipt is not explicitly actionable")
            if basis.get("unit_cost_includes_fees") is not True:
                raise ValueError("cost basis must explicitly include acquisition fees")

            quote_currency = self._required_text(market, "quote_currency")
            if self._required_text(basis, "quote_currency") != quote_currency:
                raise ValueError("market and cost-basis currencies do not match")
            price = _decimal(market.get("price"), "market.price", positive=True)
            unit_cost = _decimal(basis.get("unit_cost"), "cost_basis.unit_cost", positive=True)
            observed_exit_cost_pct = _decimal(
                market.get("observed_exit_cost_pct"),
                "market.observed_exit_cost_pct",
                nonnegative=True,
            )

            # Preserve GAIA's genuine profit equations, but all operands now
            # originate in fresh same-venue provider receipts.
            gross_profit_pct = ((price - unit_cost) / unit_cost) * Decimal("100")
            net_profit_pct = gross_profit_pct - observed_exit_cost_pct
            if net_profit_pct <= self.min_net_profit_pct:
                continue
            candidates.append(
                {
                    "venue": venue,
                    "account_id": account_id,
                    "symbol": symbol,
                    "side": "sell",
                    "quantity": quantity,
                    "quote_currency": quote_currency,
                    "gross_profit_pct": gross_profit_pct,
                    "net_profit_pct": net_profit_pct,
                    "source_receipt_ids": [
                        account["receipt_id"],
                        position["receipt_id"],
                        market["receipt_id"],
                        basis["receipt_id"],
                    ],
                }
            )
        if not candidates:
            return None
        return max(candidates, key=lambda candidate: candidate["net_profit_pct"])

    def _order_receipt(
        self,
        raw_receipt: Mapping[str, Any],
        *,
        venue: str,
        pending: Mapping[str, Any],
    ) -> tuple[dict[str, Any], str]:
        receipt = self._base_receipt(raw_receipt, venue=venue, receipt_type="order")
        if self._required_text(receipt, "symbol") != pending["symbol"]:
            raise ValueError("order symbol does not match the durable intent")
        if self._required_text(receipt, "side").lower() != pending["side"]:
            raise ValueError("order side does not match the durable intent")
        if self._required_text(receipt, "client_order_id") != pending["client_order_id"]:
            raise ValueError("provider did not echo the durable client order id")
        status = self._required_text(receipt, "status").lower()
        return receipt, status

    @staticmethod
    def _add_amount(state: dict[str, Any], bucket_name: str, currency: str, amount: Decimal) -> None:
        bucket = state[bucket_name]
        if not isinstance(bucket, dict):
            raise ValueError(f"{bucket_name} state is invalid")
        prior = _decimal(bucket[currency], f"{bucket_name}.{currency}") if currency in bucket else Decimal("0")
        bucket[currency] = str(prior + amount)

    def _validate_terminal_fill(
        self,
        receipt: Mapping[str, Any],
        pending: Mapping[str, Any],
    ) -> dict[str, Any]:
        if receipt.get("is_final") is not True:
            raise ValueError("filled receipt is not explicitly final")
        provider_order_id = self._required_text(receipt, "provider_order_id")
        expected_provider_id = pending.get("provider_order_id")
        if expected_provider_id and provider_order_id != expected_provider_id:
            raise ValueError("provider order id changed during reconciliation")

        filled_quantity = _decimal(
            receipt.get("filled_quantity"), "order.filled_quantity", positive=True
        )
        requested_quantity = _decimal(
            pending["requested_quantity"], "pending.requested_quantity", positive=True
        )
        remaining_quantity = _decimal(
            receipt.get("remaining_quantity"),
            "order.remaining_quantity",
            nonnegative=True,
        )
        average_fill_price = _decimal(
            receipt.get("average_fill_price"),
            "order.average_fill_price",
            positive=True,
        )
        filled_notional = _decimal(
            receipt.get("filled_notional"), "order.filled_notional", positive=True
        )
        fee_amount = _decimal(
            receipt.get("fee_amount"), "order.fee_amount", nonnegative=True
        )
        realized_pnl = _decimal(receipt.get("realized_pnl"), "order.realized_pnl")

        if filled_quantity != requested_quantity or remaining_quantity != 0:
            raise ValueError("terminal fill must exactly complete the requested quantity")
        if filled_notional != filled_quantity * average_fill_price:
            raise ValueError("terminal fill notional does not equal quantity times fill price")
        quote_currency = pending["quote_currency"]
        if self._required_text(receipt, "filled_notional_currency") != quote_currency:
            raise ValueError("fill notional currency does not match the source market")
        if self._required_text(receipt, "realized_pnl_currency") != quote_currency:
            raise ValueError("realized PnL currency does not match the source market")
        if receipt.get("realized_pnl_source") != "provider":
            raise ValueError("realized PnL must be provider supplied")

        return {
            "receipt_id": receipt["receipt_id"],
            "provider_order_id": provider_order_id,
            "filled_quantity": filled_quantity,
            "filled_notional": filled_notional,
            "filled_notional_currency": quote_currency,
            "average_fill_price": average_fill_price,
            "fee_amount": fee_amount,
            "fee_currency": self._required_text(receipt, "fee_currency"),
            "realized_pnl": realized_pnl,
            "realized_pnl_currency": quote_currency,
            "provider_timestamp": receipt["provider_timestamp"],
        }

    def _apply_terminal_fill(
        self,
        state: dict[str, Any],
        venue: str,
        pending: Mapping[str, Any],
        receipt: Mapping[str, Any],
    ) -> str:
        fill = self._validate_terminal_fill(receipt, pending)
        applied = state["applied_fill_receipt_ids"]
        if fill["receipt_id"] in applied:
            state["pending"].pop(venue, None)
            return "duplicate_terminal_fill"
        applied.append(fill["receipt_id"])
        state["trade_count"] += 1
        self._add_amount(
            state,
            "filled_notional_by_currency",
            fill["filled_notional_currency"],
            fill["filled_notional"],
        )
        self._add_amount(
            state,
            "fee_totals_by_currency",
            fill["fee_currency"],
            fill["fee_amount"],
        )
        self._add_amount(
            state,
            "realized_pnl_by_currency",
            fill["realized_pnl_currency"],
            fill["realized_pnl"],
        )
        state["pending"].pop(venue, None)
        return "terminal_fill_applied"

    def _handle_order_receipt(
        self,
        state: dict[str, Any],
        venue: str,
        pending: dict[str, Any],
        raw_receipt: Mapping[str, Any],
    ) -> str:
        receipt, status = self._order_receipt(
            raw_receipt, venue=venue, pending=pending
        )
        if receipt.get("dry_run") is True or status == "dry_run":
            state["pending"].pop(venue, None)
            return "dry_run_no_accounting"
        if status in _REJECTED_STATUSES:
            state["pending"].pop(venue, None)
            return "terminal_nonfill_no_accounting"
        if status in _OPEN_STATUSES:
            provider_order_id = self._required_text(receipt, "provider_order_id")
            known_order_id = pending.get("provider_order_id")
            if known_order_id and provider_order_id != known_order_id:
                raise ValueError("provider order id changed during reconciliation")
            pending["provider_order_id"] = provider_order_id
            pending["last_order_receipt_id"] = receipt["receipt_id"]
            pending["last_status"] = status
            return "unresolved_order_latched"
        if status in _FILLED_STATUSES:
            return self._apply_terminal_fill(state, venue, pending, receipt)
        raise ValueError(f"unsupported provider order status: {status}")

    @staticmethod
    def _client_order_id(candidate: Mapping[str, Any]) -> str:
        evidence = "|".join(candidate["source_receipt_ids"])
        digest = hashlib.sha256(
            f"{candidate['venue']}|{candidate['symbol']}|{evidence}".encode("utf-8")
        ).hexdigest()
        return f"gaia-{digest[:24]}"

    def _new_intent(self, candidate: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "phase": "submission_intent",
            "venue": candidate["venue"],
            "account_id": candidate["account_id"],
            "symbol": candidate["symbol"],
            "side": candidate["side"],
            "requested_quantity": str(candidate["quantity"]),
            "quote_currency": candidate["quote_currency"],
            "client_order_id": self._client_order_id(candidate),
            "source_receipt_ids": list(candidate["source_receipt_ids"]),
        }

    def run_cycle(self) -> dict[str, Any]:
        """Run at most one provider reconciliation or submission.

        A pending order globally blocks new submissions.  Exactly one provider
        readback is attempted per invocation, and a pre-submission intent is
        saved atomically before the injected adapter can place an order.
        """
        if not self.adapters:
            return {"status": "no_data", "reason": "no_injected_adapters"}

        with self._state_lock():
            state = self._load_state()
            pending_by_venue = state["pending"]
            if pending_by_venue:
                if len(pending_by_venue) != 1:
                    return {
                        "status": "blocked",
                        "reason": "multiple_unresolved_orders_require_operator_review",
                    }
                venue = next(iter(pending_by_venue))
                adapter = self.adapters.get(venue)
                if adapter is None:
                    return {
                        "status": "blocked",
                        "reason": f"missing_adapter_for_unresolved_{venue}_order",
                    }
                pending = pending_by_venue[venue]
                order_reference = pending.get("provider_order_id") or pending["client_order_id"]
                try:
                    raw_receipt = adapter.read_order_receipt(order_reference)
                    outcome = self._handle_order_receipt(
                        state, venue, pending, raw_receipt
                    )
                except Exception as exc:
                    return {
                        "status": "no_action",
                        "venue": venue,
                        "reason": f"order_readback_incomplete:{type(exc).__name__}:{exc}",
                    }
                self._save_state(state)
                return {"status": outcome, "venue": venue}

            candidates: list[tuple[str, VenueAdapter, dict[str, Any]]] = []
            rejected_inputs: dict[str, str] = {}
            for venue, adapter in sorted(self.adapters.items()):
                try:
                    candidate = self._select_exit(venue, adapter)
                except Exception as exc:
                    rejected_inputs[venue] = f"{type(exc).__name__}:{exc}"
                    continue
                if candidate is not None:
                    candidates.append((venue, adapter, candidate))
            if not candidates:
                return {
                    "status": "no_action",
                    "reason": "no_complete_profitable_same_venue_receipt_chain",
                    "rejected_inputs": rejected_inputs,
                }

            venue, adapter, candidate = max(
                candidates, key=lambda item: item[2]["net_profit_pct"]
            )
            intent = self._new_intent(candidate)
            state["pending"][venue] = intent
            self._save_state(state)
            try:
                raw_receipt = adapter.submit_market_order(
                    symbol=intent["symbol"],
                    side=intent["side"],
                    quantity=intent["requested_quantity"],
                    client_order_id=intent["client_order_id"],
                )
                outcome = self._handle_order_receipt(
                    state, venue, intent, raw_receipt
                )
            except Exception as exc:
                return {
                    "status": "unresolved_submission_latched",
                    "venue": venue,
                    "reason": f"{type(exc).__name__}:{exc}",
                }
            self._save_state(state)
            return {"status": outcome, "venue": venue}

    def status(self) -> dict[str, Any]:
        """Read durable lifecycle/accounting state without contacting a provider."""
        with self._state_lock():
            return self._load_state()

    def print_status(self) -> dict[str, Any]:
        snapshot = self.status()
        self.log(json.dumps(snapshot, sort_keys=True))
        return snapshot

    def run(self) -> None:
        raise RuntimeError(
            "continuous execution is disabled; an authorized caller must invoke run_cycle explicitly"
        )


def main() -> int:
    print(
        "GAIA is inert: inject audited venue adapters and invoke one explicit run_cycle."
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
