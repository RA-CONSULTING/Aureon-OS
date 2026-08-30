"""Durable one-cycle Capital entry, confirmation, containment, and settlement.

The cycle never makes a trading decision.  It accepts only a fully bound
``CapitalTradePlan`` and delegates both entry and the pre-entry close warrant to
``BoundedCapitalLiveTrade``.  Submission acknowledgement is not a fill, a
visible position is not accounting evidence, and a restart never resubmits an
uncertain entry or close.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import threading
import time
from collections.abc import Callable, Mapping
from contextlib import contextmanager
from dataclasses import asdict
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Protocol

from aureon.governance.durable_contingency import DurableContingencyRecordRef
from aureon.governance.economic_boundary import (
    EconomicGovernanceBlocked,
    EconomicIntent,
)
from aureon.trading.bounded_capital_live_trade import (
    BoundedCapitalLiveTrade,
    CapitalTradePlan,
    ProviderMoment,
)
from aureon.trading.capital_transaction_evidence import derive_capital_fee_receipt

CYCLE_SCHEMA = "aureon.capital_autonomous_cycle.v1"
_FINAL_STAGES = frozenset({"CLOSED_SETTLED", "ENTRY_REJECTED", "HELD_PRE_ENTRY"})
_LOCKS_GUARD = threading.Lock()
_LOCKS: dict[str, threading.RLock] = {}
_SAFE_REASON = re.compile(r"[a-z0-9_.:-]{1,160}")


class CapitalCycleClient(Protocol):
    def confirm_order(
        self,
        deal_reference: str,
        *,
        fee_receipt: dict[str, Any] | None = None,
    ) -> Mapping[str, Any]: ...

    def get_positions(self): ...

    def get_transaction_history(self, last_period: int = 600): ...


def _canonical(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name}_required")
    return value.strip()


def _number(value: Any, name: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{name}_must_be_finite")
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{name}_must_be_finite") from exc
    if not math.isfinite(result):
        raise ValueError(f"{name}_must_be_finite")
    return result


def _decimal_equal(left: Any, right: Any) -> bool:
    if isinstance(left, bool) or isinstance(right, bool):
        return False
    try:
        return Decimal(str(left)) == Decimal(str(right))
    except (InvalidOperation, TypeError, ValueError):
        return False


def _decimal_text(value: Any) -> str:
    number = Decimal(str(_number(value, "decimal_value")))
    text = format(number, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return "0" if number == 0 else text


def _plan_digest(plan: CapitalTradePlan) -> str:
    evidence_id = plan.market_evidence_receipt.get(
        "capital_market_evidence_receipt_id"
    )
    return _sha(
        {
            "account_id_hash": plan.account_id_hash,
            "auris_receipt_id": plan.field_moment.auris_receipt_id,
            "authorization_receipt_id": plan.authorization_receipt_id,
            "close_client_order_id": plan.close_client_order_id,
            "cycle_id": plan.cycle_id,
            "entry_client_order_id": plan.entry_client_order_id,
            "epic": plan.epic,
            "evidence_receipt_id": evidence_id,
            "field_provider_moment_digest": plan.field_moment.provider_moment_digest,
            "hnc_receipt_id": plan.field_moment.hnc_receipt_id,
            "profit_distance": plan.profit_distance,
            "quantity": plan.quantity,
            "side": plan.side,
            "stop_distance": plan.stop_distance,
            "symbol": plan.symbol,
            "target_provider_moment_digest": plan.target_moment.moment_digest,
        }
    )


def _exception_reason(exc: Exception) -> str:
    if isinstance(exc, (EconomicGovernanceBlocked, ValueError)):
        value = str(exc).strip()
        if _SAFE_REASON.fullmatch(value):
            return value
    return type(exc).__name__


def _public_confirmation(receipt: Mapping[str, Any]) -> dict[str, Any]:
    keys = (
        "affected_deals",
        "dealReference",
        "eligible_for_learning",
        "eligible_for_pnl",
        "eligible_for_state",
        "epic",
        "fee_amount",
        "fee_currency",
        "fee_receipt",
        "filled_avg_price",
        "filled_qty",
        "generated_values",
        "provider_deal_id",
        "provider_order_id",
        "reason",
        "received_at",
        "side",
        "source_id",
        "source_timestamp",
        "status",
        "terminal_fill",
        "terminal_fill_receipt_complete",
        "truth_status",
    )
    return {key: receipt.get(key) for key in keys if key in receipt}


def _entry_intent_from_state(value: Mapping[str, Any]) -> EconomicIntent:
    payload = dict(value)
    payload["provider_receipt_ids"] = tuple(payload["provider_receipt_ids"])
    if payload.get("field_provider_receipt_ids") is not None:
        payload["field_provider_receipt_ids"] = tuple(
            payload["field_provider_receipt_ids"]
        )
    payload["body_bindings"] = tuple(
        tuple(item) for item in payload.get("body_bindings", ())
    )
    return EconomicIntent(**payload)


def _recovery_reference_from_state(value: Mapping[str, Any]) -> DurableContingencyRecordRef:
    return DurableContingencyRecordRef(**dict(value))


class CapitalAutonomousCycle:
    """Single-writer lifecycle that resumes containment but never entry."""

    def __init__(
        self,
        *,
        route: BoundedCapitalLiveTrade,
        client: CapitalCycleClient,
        state_path: Path,
        clock: Callable[[], float] = time.time,
        sleeper: Callable[[float], None] = time.sleep,
        confirmation_attempts: int = 3,
        poll_interval_s: float = 1.0,
    ) -> None:
        if not isinstance(route, BoundedCapitalLiveTrade):
            raise TypeError("bounded_capital_live_trade_required")
        if getattr(route, "client", None) is not client:
            raise ValueError("capital_cycle_route_client_identity_required")
        path = Path(state_path)
        if path.suffix.casefold() != ".json" or {part.casefold() for part in path.parts}.intersection(
            {"frontend", "public"}
        ):
            raise ValueError("private_capital_cycle_json_path_required")
        if (
            isinstance(confirmation_attempts, bool)
            or not isinstance(confirmation_attempts, int)
            or not 1 <= confirmation_attempts <= 20
        ):
            raise ValueError("bounded_confirmation_attempts_required")
        if _number(poll_interval_s, "poll_interval_s") < 0:
            raise ValueError("nonnegative_poll_interval_required")
        self.route = route
        self.client = client
        self.state_path = path
        self.clock = clock
        self.sleeper = sleeper
        self.confirmation_attempts = confirmation_attempts
        self.poll_interval_s = float(poll_interval_s)
        with _LOCKS_GUARD:
            self._thread_lock = _LOCKS.setdefault(str(path.resolve()), threading.RLock())

    @property
    def _lock_path(self) -> Path:
        return self.state_path.with_name(self.state_path.stem + ".lock")

    @contextmanager
    def _lock(self):
        with self._thread_lock:
            self.state_path.parent.mkdir(parents=True, exist_ok=True)
            with self._lock_path.open("a+b") as handle:
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

    def _now(self) -> float:
        return _number(self.clock(), "cycle_clock")

    def _read(self) -> dict[str, Any] | None:
        if not self.state_path.exists():
            return None
        try:
            raw = json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise EconomicGovernanceBlocked("capital_cycle_state_unreadable") from exc
        if not isinstance(raw, dict) or raw.get("schema") != CYCLE_SCHEMA:
            raise EconomicGovernanceBlocked("capital_cycle_state_schema_invalid")
        observed = raw.get("state_hash")
        core = {key: value for key, value in raw.items() if key != "state_hash"}
        if observed != _sha(core):
            raise EconomicGovernanceBlocked("capital_cycle_state_hash_mismatch")
        return raw

    def _write(self, state: Mapping[str, Any]) -> dict[str, Any]:
        core = {key: value for key, value in state.items() if key != "state_hash"}
        stored = {**core, "state_hash": _sha(core)}
        encoded = (_canonical(stored) + "\n").encode("utf-8")
        temporary = self.state_path.with_name(
            f".{self.state_path.name}.{os.getpid()}.{threading.get_ident()}.tmp"
        )
        try:
            with temporary.open("wb") as handle:
                handle.write(encoded)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.state_path)
        finally:
            if temporary.exists():
                temporary.unlink()
        return stored

    def _set_stage(
        self,
        state: Mapping[str, Any],
        stage: str,
        reason: str,
        **updates: Any,
    ) -> dict[str, Any]:
        return self._write(
            {
                **{key: value for key, value in state.items() if key != "state_hash"},
                **updates,
                "reason": reason,
                "stage": stage,
                "updated_at": self._now(),
            }
        )

    @staticmethod
    def _result(state: Mapping[str, Any]) -> dict[str, Any]:
        stage = str(state.get("stage") or "HOLD")
        payload = {
            "accounting_complete": bool(state.get("accounting_complete") is True),
            "capital_cycle_id": state.get("cycle_id"),
            "close_deal_reference": state.get("close_deal_reference"),
            "economic_mutation_attempted": bool(state.get("economic_mutation_attempted") is True),
            "entry_deal_reference": state.get("entry_deal_reference"),
            "exposure_open": bool(state.get("exposure_open") is True),
            "provider_deal_id": state.get("provider_deal_id"),
            "reason": state.get("reason"),
            "schema": CYCLE_SCHEMA,
            "stage": stage,
            "state_hash": state.get("state_hash"),
        }
        return {
            **payload,
            "action_eligible": False,
            "economic_mutation": False,
            "generated_values": False,
            "learning_eligible": bool(payload["accounting_complete"]),
            "receipt_id": f"capital:autonomous-cycle:{_sha(payload)}",
        }

    def _submission_reference(
        self,
        receipt: Mapping[str, Any],
        *,
        purpose: str,
    ) -> str:
        if not isinstance(receipt, Mapping):
            raise EconomicGovernanceBlocked("capital_submission_receipt_required")
        current = self._now()
        source_timestamp = _number(receipt.get("source_timestamp"), "submission_source_timestamp")
        deal_reference = _text(receipt.get("dealReference"), "deal_reference")
        if (
            receipt.get("purpose") != purpose
            or receipt.get("status") != "submitted"
            or receipt.get("truth_status") != "real_observed"
            or receipt.get("generated_values") is not False
            or receipt.get("submission_acknowledged") is not True
            or receipt.get("terminal_fill") is not False
            or receipt.get("terminal_fill_receipt_complete") is not False
            or source_timestamp > current + 5.0
            or current - source_timestamp > 300.0
            or receipt.get("source_id") != f"capital_submission:{deal_reference}"
        ):
            raise EconomicGovernanceBlocked("durable_capital_submission_ack_required")
        return deal_reference

    def _poll_confirmation(
        self,
        deal_reference: str,
        *,
        fee_receipt: dict[str, Any] | None = None,
    ) -> Mapping[str, Any]:
        latest: Mapping[str, Any] = {}
        for attempt in range(self.confirmation_attempts):
            latest = self.client.confirm_order(
                deal_reference,
                fee_receipt=fee_receipt,
            )
            if latest.get("status") == "rejected" or latest.get("terminal_fill") is True:
                return latest
            if attempt + 1 < self.confirmation_attempts and self.poll_interval_s:
                self.sleeper(self.poll_interval_s)
        return latest

    def _validate_fill(
        self,
        receipt: Mapping[str, Any],
        *,
        plan: CapitalTradePlan,
        deal_reference: str,
        phase: str,
        provider_deal_id: str | None = None,
    ) -> str:
        if receipt.get("status") == "rejected":
            return "REJECTED"
        if receipt.get("terminal_fill") is not True:
            return "PENDING"
        expected_side = plan.side if phase == "entry" else plan.close_side
        expected_status = "OPENED" if phase == "entry" else "CLOSED"
        deal_id = _text(receipt.get("provider_deal_id"), "provider_deal_id")
        affected = receipt.get("affected_deals")
        if (
            receipt.get("dealReference") != deal_reference
            or receipt.get("provider_order_id") != deal_reference
            or receipt.get("generated_values") is not False
            or receipt.get("epic") != plan.epic
            or receipt.get("side") != expected_side
            or not _decimal_equal(receipt.get("filled_qty"), plan.quantity)
            or not isinstance(affected, list)
            or affected != [{"dealId": deal_id, "status": expected_status}]
            or (provider_deal_id is not None and deal_id != provider_deal_id)
        ):
            raise EconomicGovernanceBlocked("exact_capital_terminal_fill_required")
        source_timestamp = _number(receipt.get("source_timestamp"), "fill_source_timestamp")
        current = self._now()
        if source_timestamp > current + 5.0 or current - source_timestamp > 900.0:
            raise EconomicGovernanceBlocked("fresh_capital_terminal_fill_required")
        return deal_id

    def _position_moment(
        self,
        *,
        plan: CapitalTradePlan,
        provider_deal_id: str,
        entry_receipt_id: str,
    ) -> ProviderMoment | None:
        positions = self.client.get_positions()
        if getattr(positions, "generated_values", None) is not False:
            return None
        source_timestamp = getattr(positions, "source_timestamp", None)
        if source_timestamp is None:
            return None
        observed_at = _number(source_timestamp, "positions_source_timestamp")
        current = self._now()
        if observed_at > current + 5.0 or current - observed_at > 300.0:
            return None
        matches = []
        for row in positions:
            if not isinstance(row, Mapping):
                return None
            position = row.get("position")
            market = row.get("market")
            if not isinstance(position, Mapping) or not isinstance(market, Mapping):
                return None
            if str(position.get("dealId") or "").strip() != provider_deal_id:
                continue
            if (
                row.get("truth_status") != "real_observed"
                or row.get("generated_values") is not False
                or str(market.get("epic") or "").strip().upper() != plan.epic
                or str(position.get("direction") or "").strip().upper() != plan.side
                or not _decimal_equal(position.get("size"), plan.quantity)
            ):
                return None
            matches.append(row)
        if len(matches) != 1:
            return None
        row = matches[0]
        position_receipt_id = _text(row.get("source_id"), "position_source_id")
        snapshot_id = f"capital_positions_snapshot:{_decimal_text(observed_at)}"
        receipt_ids = tuple(sorted({entry_receipt_id, position_receipt_id, snapshot_id}))
        digest = _sha(
            {
                "direction": plan.side,
                "epic": plan.epic,
                "position_receipt_id": position_receipt_id,
                "provider_deal_id": provider_deal_id,
                "quantity": plan.quantity,
                "receipt_ids": receipt_ids,
                "source_timestamp": _decimal_text(observed_at),
            }
        )
        return ProviderMoment(
            receipt_ids=receipt_ids,
            moment_digest=digest,
            source_timestamp=_decimal_text(observed_at),
            position_receipt_id=position_receipt_id,
        )

    def _position_absent(self, provider_deal_id: str) -> bool:
        positions = self.client.get_positions()
        if getattr(positions, "generated_values", None) is not False:
            return False
        observed_at = getattr(positions, "source_timestamp", None)
        if observed_at is None or self._now() - _number(observed_at, "positions_source_timestamp") > 300.0:
            return False
        for row in positions:
            if not isinstance(row, Mapping):
                return False
            position = row.get("position")
            if not isinstance(position, Mapping):
                return False
            if str(position.get("dealId") or "").strip() == provider_deal_id:
                return False
        return True

    def _finish(self, state: Mapping[str, Any], stage: str, reason: str, **updates: Any):
        return self._result(self._set_stage(state, stage, reason, **updates))

    def execute(self, plan: CapitalTradePlan) -> dict[str, Any]:
        """Run or resume one exact plan; an uncertain mutation is never retried."""

        if not isinstance(plan, CapitalTradePlan):
            raise TypeError("capital_trade_plan_required")
        binding = _plan_digest(plan)
        with self._lock():
            state = self._read()
            if state is not None:
                if state.get("cycle_id") != plan.cycle_id or state.get("plan_digest") != binding:
                    raise EconomicGovernanceBlocked("capital_cycle_plan_binding_mismatch")
                if state.get("stage") in _FINAL_STAGES:
                    return self._result(state)
                return self._resume(plan, state)

            initial = {
                "account_id_hash": plan.account_id_hash,
                "accounting_complete": False,
                "created_at": self._now(),
                "cycle_id": plan.cycle_id,
                "economic_mutation_attempted": False,
                "exposure_open": False,
                "plan_digest": binding,
                "reason": "capital_cycle_created",
                "schema": CYCLE_SCHEMA,
                "stage": "CREATED",
                "updated_at": self._now(),
            }
            state = self._write(initial)
            try:
                prepared = self.route.prepare(plan)
            except Exception as exc:
                return self._finish(
                    state,
                    "HELD_PRE_ENTRY",
                    _exception_reason(exc),
                )
            state = self._set_stage(
                state,
                "PREPARED",
                "entry_and_contingency_dual_authorized",
                entry_intent=asdict(prepared.entry_intent),
                recovery_reference=asdict(prepared.recovery_reference),
            )
            state = self._set_stage(
                state,
                "ENTRY_SUBMITTING",
                "entry_transport_may_be_in_flight",
                economic_mutation_attempted=True,
            )
            try:
                acknowledgement = self.route.submit_entry(prepared)
                deal_reference = self._submission_reference(
                    acknowledgement,
                    purpose="open_position",
                )
            except Exception as exc:
                return self._finish(
                    state,
                    "ENTRY_AMBIGUOUS",
                    _exception_reason(exc),
                )
            state = self._set_stage(
                state,
                "ENTRY_SUBMITTED",
                "terminal_entry_confirmation_required",
                entry_deal_reference=deal_reference,
            )
            return self._resume(plan, state)

    def _resume(self, plan: CapitalTradePlan, state: Mapping[str, Any]) -> dict[str, Any]:
        stage = state.get("stage")
        if stage == "PREPARED":
            return self._finish(
                state,
                "HELD_PRE_ENTRY",
                "in_memory_entry_permit_lost_without_submission",
            )
        if stage == "ENTRY_SUBMITTING":
            return self._finish(
                state,
                "ENTRY_AMBIGUOUS",
                "entry_submission_uncertain_reconciliation_required",
            )
        if stage == "CLOSE_SUBMITTING":
            return self._finish(
                state,
                "CLOSE_AMBIGUOUS",
                "close_submission_uncertain_reconciliation_required",
                exposure_open=True,
            )
        if stage == "CLOSED_UNSETTLED":
            return self._settle_closed(plan, state)

        if stage in {"ENTRY_SUBMITTED", "ENTRY_RECONCILIATION_PENDING"}:
            entry_reference = _text(state.get("entry_deal_reference"), "entry_deal_reference")
            confirmation = self._poll_confirmation(entry_reference)
            status = self._validate_fill(
                confirmation,
                plan=plan,
                deal_reference=entry_reference,
                phase="entry",
            )
            if status == "REJECTED":
                return self._finish(
                    state,
                    "ENTRY_REJECTED",
                    str(confirmation.get("reason") or "provider_rejected"),
                )
            if status == "PENDING":
                return self._finish(
                    state,
                    "ENTRY_RECONCILIATION_PENDING",
                    "terminal_entry_confirmation_pending",
                )
            provider_deal_id = status
            entry_receipt_id = _text(
                confirmation.get("source_id"),
                "entry_confirmation_source_id",
            )
            moment = self._position_moment(
                plan=plan,
                provider_deal_id=provider_deal_id,
                entry_receipt_id=entry_receipt_id,
            )
            if moment is None:
                return self._finish(
                    state,
                    "ENTRY_RECONCILIATION_PENDING",
                    "fresh_exact_provider_position_readback_required",
                    provider_deal_id=provider_deal_id,
                )
            state = self._set_stage(
                state,
                "ENTRY_OPEN_OBSERVED",
                "exact_position_observed_containment_required",
                entry_confirmation=_public_confirmation(confirmation),
                exposure_open=True,
                post_entry_moment=asdict(moment),
                provider_deal_id=provider_deal_id,
            )
            stage = "ENTRY_OPEN_OBSERVED"

        if stage == "ENTRY_OPEN_OBSERVED":
            entry_intent = _entry_intent_from_state(state["entry_intent"])
            reference = _recovery_reference_from_state(state["recovery_reference"])
            moment = ProviderMoment(**dict(state["post_entry_moment"]))
            entry_receipt_id = _text(
                state["entry_confirmation"].get("source_id"),
                "entry_confirmation_source_id",
            )
            provider_deal_id = _text(state.get("provider_deal_id"), "provider_deal_id")
            state = self._set_stage(
                state,
                "CLOSE_SUBMITTING",
                "containment_transport_may_be_in_flight",
            )
            try:
                acknowledgement = self.route.close_from_recovery(
                    plan=plan,
                    entry_intent=entry_intent,
                    recovery_reference=reference,
                    provider_deal_id=provider_deal_id,
                    entry_receipt_id=entry_receipt_id,
                    post_entry_moment=moment,
                )
                close_reference = self._submission_reference(
                    acknowledgement,
                    purpose="close_position",
                )
            except Exception as exc:
                return self._finish(
                    state,
                    "CLOSE_AMBIGUOUS",
                    _exception_reason(exc),
                    exposure_open=True,
                )
            state = self._set_stage(
                state,
                "CLOSE_SUBMITTED",
                "terminal_close_confirmation_required",
                close_deal_reference=close_reference,
            )
            stage = "CLOSE_SUBMITTED"

        if stage in {"CLOSE_SUBMITTED", "CLOSE_RECONCILIATION_PENDING"}:
            close_reference = _text(state.get("close_deal_reference"), "close_deal_reference")
            provider_deal_id = _text(state.get("provider_deal_id"), "provider_deal_id")
            confirmation = self._poll_confirmation(close_reference)
            status = self._validate_fill(
                confirmation,
                plan=plan,
                deal_reference=close_reference,
                phase="close",
                provider_deal_id=provider_deal_id,
            )
            if status == "REJECTED":
                return self._finish(
                    state,
                    "CLOSE_REJECTED_EXPOSURE_OPEN",
                    str(confirmation.get("reason") or "provider_rejected"),
                    exposure_open=True,
                )
            if status == "PENDING" or not self._position_absent(provider_deal_id):
                return self._finish(
                    state,
                    "CLOSE_RECONCILIATION_PENDING",
                    "terminal_close_and_absent_position_readback_required",
                    exposure_open=True,
                )
            state = self._set_stage(
                state,
                "CLOSED_UNSETTLED",
                "position_closed_fee_complete_receipts_pending",
                close_confirmation=_public_confirmation(confirmation),
                exposure_open=False,
            )
            return self._settle_closed(plan, state)

        return self._result(state)

    def _settle_closed(
        self,
        plan: CapitalTradePlan,
        state: Mapping[str, Any],
    ) -> dict[str, Any]:
        entry = state.get("entry_confirmation") or {}
        close = state.get("close_confirmation") or {}
        if (
            entry.get("terminal_fill_receipt_complete") is True
            and close.get("terminal_fill_receipt_complete") is True
        ):
            return self._finish(
                state,
                "CLOSED_SETTLED",
                "entry_and_close_terminal_fee_receipts_complete",
                accounting_complete=True,
                exposure_open=False,
            )
        provider_deal_id = _text(state.get("provider_deal_id"), "provider_deal_id")
        try:
            transactions = self.client.get_transaction_history(last_period=900)
            cycle_fee = derive_capital_fee_receipt(
                transactions,
                provider_deal_id=provider_deal_id,
                instrument_name=plan.epic,
                now=self._now(),
            )
        except Exception:
            return self._result(state)
        return self._result(
            self._set_stage(
                state,
                "CLOSED_UNSETTLED",
                "aggregate_cycle_fee_observed_phase_allocation_pending",
                cycle_fee_receipt=cycle_fee,
                exposure_open=False,
            )
        )


__all__ = ["CYCLE_SCHEMA", "CapitalAutonomousCycle", "CapitalCycleClient"]
