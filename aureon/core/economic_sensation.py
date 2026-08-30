"""Machine-readable economic outcomes for the Aureon nervous system.

This module does not claim human sensation.  It translates an already-made
economic mutation outcome into one bounded, provenance-preserving signal that
the ThoughtBus, Hive state, and Mycelium can all receive.  The signal is
feedback only: it carries no action eligibility and cannot authorize a retry.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable, Mapping
from threading import Lock
from typing import Any

_EXECUTED_STATUSES = {
    "ACCEPTED",
    "CLOSED",
    "EXECUTED",
    "FILLED",
    "OPEN",
    "OPENED",
    "SUCCESS",
}
_PROTECTIVE_STATUSES = {
    "ABORT",
    "BLOCKED",
    "HOLD",
    "NO_DATA",
    "NOT_SUBMITTED",
    "REJECTED",
}


def _text(value: Any, *, fallback: str, limit: int = 240) -> str:
    rendered = str(value or "").strip()
    return (rendered or fallback)[:limit]


def _receipt_status(receipt: Mapping[str, Any]) -> str:
    nested = receipt.get("aureon_legacy_unity_receipt")
    if isinstance(nested, Mapping):
        nested_status = _text(nested.get("status"), fallback="").upper()
        if nested_status:
            return nested_status
    return _text(receipt.get("status"), fallback="NO_DATA").upper()


def economic_sensation(
    operation: str,
    receipt: Mapping[str, Any],
) -> dict[str, Any]:
    """Derive a bounded feedback-only sensation from an immutable outcome."""

    if not isinstance(receipt, Mapping):
        raise TypeError("economic_mutation_receipt_required")
    status = _receipt_status(receipt)
    rejected = receipt.get("rejected") is True
    executed = status in _EXECUTED_STATUSES and not rejected
    if executed:
        felt_state = "RESOLVED_EXECUTION"
        mood = "Attentive"
    elif status in _PROTECTIVE_STATUSES or rejected:
        felt_state = "PROTECTIVE_HOLD"
        mood = "Protective"
    else:
        felt_state = "UNCERTAIN_OUTCOME"
        mood = "Cautious"

    nested = receipt.get("aureon_legacy_unity_receipt")
    nested = nested if isinstance(nested, Mapping) else {}
    reason = _text(
        receipt.get("reason") or nested.get("reason"),
        fallback="provider_outcome_observed" if executed else "outcome_reason_unavailable",
    )
    exchange = _text(
        receipt.get("exchange") or nested.get("venue"),
        fallback="unknown",
        limit=32,
    ).lower()
    symbol = _text(
        receipt.get("symbol") or nested.get("symbol"),
        fallback="UNKNOWN",
        limit=80,
    ).upper()
    truth_status = _text(
        receipt.get("truth_status") or nested.get("truth_status"),
        fallback="real_observed" if executed else "no_data",
        limit=40,
    )
    receipt_id = _text(
        receipt.get("receipt_id") or nested.get("receipt_id"),
        fallback="",
        limit=160,
    )

    return {
        "schema": "aureon.organism.economic_sensation.v1",
        "source": "queen_governed_exchange_brain",
        "operation": _text(operation, fallback="unknown_mutation", limit=80),
        "exchange": exchange,
        "symbol": symbol,
        "status": status,
        "reason": reason,
        "truth_status": truth_status,
        "receipt_id": receipt_id or None,
        "felt_state": felt_state,
        "mood": mood,
        "executed": executed,
        "feedback_only": True,
        "actionable": False,
        "action_eligible": False,
        "economic_mutation": False,
        "eligible_for_accounting": False,
        "eligible_for_learning": False,
        "not_human_sensation": True,
    }


class OrganismEconomicSensationRouter:
    """Fan an economic sensation into Aureon's existing nervous-system sinks."""

    def __init__(
        self,
        *,
        bus_getter: Callable[[], Any] | None = None,
        hive_getter: Callable[[], Any] | None = None,
        mycelium_getter: Callable[[], Any] | None = None,
        history_limit: int = 64,
    ) -> None:
        if isinstance(history_limit, bool) or not isinstance(history_limit, int):
            raise TypeError("economic_sensation_history_limit_integer_required")
        if history_limit < 1 or history_limit > 1024:
            raise ValueError("economic_sensation_history_limit_out_of_range")
        self._bus_getter = bus_getter
        self._hive_getter = hive_getter
        self._mycelium_getter = mycelium_getter
        self._history: deque[dict[str, Any]] = deque(maxlen=history_limit)
        self._lock = Lock()

    def observe(self, operation: str, receipt: Mapping[str, Any]) -> dict[str, Any]:
        sensation = economic_sensation(operation, receipt)
        delivery = {"thought_bus": False, "hive": False, "mycelium": False}

        bus = self._resolve(self._bus_getter)
        if bus is not None and hasattr(bus, "publish"):
            try:
                from aureon.core.aureon_thought_bus import Thought

                bus.publish(
                    Thought(
                        source="organism_economic_sensation",
                        topic="organism.economic.sensation",
                        payload=dict(sensation),
                        meta={"feedback_only": True},
                    )
                )
                delivery["thought_bus"] = True
            except Exception:
                pass

        hive = self._resolve(self._hive_getter)
        if hive is not None and hasattr(hive, "update"):
            try:
                kwargs: dict[str, Any] = {
                    "mood": sensation["mood"],
                    "scanner": (
                        f"economic:{sensation['exchange']}:{sensation['operation']}"
                    )[:120],
                }
                if sensation["felt_state"] == "PROTECTIVE_HOLD":
                    kwargs["veto_reason"] = sensation["reason"]
                hive.update(**kwargs)
                if hasattr(hive, "log_message"):
                    hive.log_message(
                        f"{sensation['felt_state']} {sensation['exchange']} "
                        f"{sensation['symbol']} {sensation['status']}"
                    )
                delivery["hive"] = True
            except Exception:
                pass

        mycelium = self._resolve(self._mycelium_getter)
        if mycelium is not None:
            try:
                delivered = False
                if hasattr(mycelium, "broadcast_signal"):
                    mycelium.broadcast_signal("economic_sensation", dict(sensation))
                    delivered = True
                if hasattr(mycelium, "propagate_to_all"):
                    mycelium.propagate_to_all("economic_sensation", dict(sensation))
                    delivered = True
                delivery["mycelium"] = delivered
            except Exception:
                pass

        observed = {**sensation, "delivery": delivery}
        with self._lock:
            self._history.append(observed)
        return dict(observed)

    def recent(self) -> list[dict[str, Any]]:
        with self._lock:
            return [dict(item) for item in self._history]

    @staticmethod
    def _resolve(getter: Callable[[], Any] | None) -> Any:
        if getter is None:
            return None
        try:
            return getter()
        except Exception:
            return None
