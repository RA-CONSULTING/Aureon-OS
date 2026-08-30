"""Collect strict read-only Capital observations into one local evidence receipt."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from typing import Any, Protocol

from aureon.trading.capital_market_evidence import (
    build_capital_market_evidence_receipt,
    build_capital_market_source_receipt,
)


class CapitalEvidenceReadClient(Protocol):
    def get_ticker(self, symbol: str) -> Mapping[str, Any]: ...

    def get_price_history(
        self,
        epic: str,
        *,
        resolution: str,
        max_points: int,
    ) -> Sequence[Mapping[str, Any]]: ...

    def get_accounts(self, *, cache_ttl: float) -> Sequence[Mapping[str, Any]]: ...

    def get_positions(self) -> Sequence[Mapping[str, Any]]: ...

    def get_working_orders(self) -> Sequence[Mapping[str, Any]]: ...


def _timestamp(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"fresh_{name}_required")
    return float(value)


def _observed_list(value: Any, name: str) -> tuple[list[Any], float, float]:
    if not isinstance(value, list):
        raise ValueError(f"{name}_observation_list_required")
    truth = str(getattr(value, "truth_status", ""))
    if truth not in {"real_observed", "incomplete"}:
        raise ValueError(f"real_observed_{name}_required")
    return (
        list(value),
        _timestamp(getattr(value, "source_timestamp", None), f"{name}_source_timestamp"),
        _timestamp(getattr(value, "received_at", None), f"{name}_received_at"),
    )


def _account(accounts: Sequence[Mapping[str, Any]]) -> Mapping[str, Any]:
    eligible = [
        item
        for item in accounts
        if isinstance(item, Mapping)
        and item.get("truth_status") == "real_observed"
        and item.get("generated_values") is False
        and item.get("action_eligible") is True
        and str(item.get("currency") or "").upper() == "GBP"
    ]
    preferred = [item for item in eligible if item.get("preferred") is True]
    selected = preferred if preferred else eligible
    if len(selected) != 1:
        raise ValueError("exact_one_enabled_gbp_capital_account_required")
    return selected[0]


def _private_source_id(prefix: str, value: Any) -> str:
    digest = hashlib.sha256(str(value).encode("utf-8")).hexdigest()
    return f"{prefix}:{digest}"


def collect_capital_market_evidence(
    *,
    client: CapitalEvidenceReadClient,
    public_contexts: Sequence[Mapping[str, Any]],
    now: float,
    symbol: str = "GOLD",
    max_history_points: int = 100,
) -> dict[str, Any]:
    """Read the five Capital surfaces and bind caller-fetched official context."""

    quote = client.get_ticker(symbol)
    if (
        not isinstance(quote, Mapping)
        or quote.get("truth_status") != "real_derived"
        or quote.get("generated_values") is not False
        or quote.get("action_eligible") is not True
    ):
        raise ValueError("fresh_tradeable_capital_quote_required")
    epic = str(quote.get("epic") or "").strip()
    if not epic:
        raise ValueError("capital_quote_epic_required")
    history_raw = client.get_price_history(
        epic,
        resolution="MINUTE",
        max_points=max_history_points,
    )
    history, history_time, history_received = _observed_list(
        history_raw,
        "capital_price_history",
    )
    accounts_raw = client.get_accounts(cache_ttl=0.0)
    accounts, account_time, account_received = _observed_list(
        accounts_raw,
        "capital_accounts",
    )
    account = _account(accounts)
    positions, positions_time, positions_received = _observed_list(
        client.get_positions(),
        "capital_positions",
    )
    orders, orders_time, orders_received = _observed_list(
        client.get_working_orders(),
        "capital_working_orders",
    )

    sources = [
        build_capital_market_source_receipt(
            source_kind="capital_quote",
            source_id=str(quote["source_id"]),
            source_uri=f"https://api-capital.backend-capital.com/api/v1/markets/{epic}",
            source_timestamp=_timestamp(quote.get("source_timestamp"), "capital_quote_source_timestamp"),
            received_at=_timestamp(quote.get("received_at"), "capital_quote_received_at"),
            payload={
                key: quote[key]
                for key in ("ask", "bid", "change_pct", "epic", "high", "low", "market_status", "symbol")
            },
        ),
        build_capital_market_source_receipt(
            source_kind="capital_price_history",
            source_id=f"capital_price_history:{epic}",
            source_uri=f"https://api-capital.backend-capital.com/api/v1/prices/{epic}",
            source_timestamp=history_time,
            received_at=history_received,
            payload={"bars": history, "epic": epic, "resolution": "MINUTE"},
        ),
        build_capital_market_source_receipt(
            source_kind="capital_account",
            source_id=_private_source_id("capital_account_hash", account.get("source_id")),
            source_uri="https://api-capital.backend-capital.com/api/v1/accounts",
            source_timestamp=account_time,
            received_at=account_received,
            payload={
                "available": account["available"],
                "balance": account["balance"],
                "currency": "GBP",
            },
        ),
        build_capital_market_source_receipt(
            source_kind="capital_positions",
            source_id="capital_positions:aggregate_snapshot",
            source_uri="https://api-capital.backend-capital.com/api/v1/positions",
            source_timestamp=positions_time,
            received_at=positions_received,
            payload={"open_position_count": len(positions)},
        ),
        build_capital_market_source_receipt(
            source_kind="capital_working_orders",
            source_id="capital_working_orders:aggregate_snapshot",
            source_uri="https://api-capital.backend-capital.com/api/v1/workingorders",
            source_timestamp=orders_time,
            received_at=orders_received,
            payload={"working_order_count": len(orders)},
        ),
    ]
    context_received_times: list[float] = []
    for context in public_contexts:
        if not isinstance(context, Mapping):
            raise ValueError("public_context_observation_required")
        sources.append(
            build_capital_market_source_receipt(
                source_kind=context["source_kind"],
                source_id=context["source_id"],
                source_uri=context["source_uri"],
                source_timestamp=context["source_timestamp"],
                received_at=context["received_at"],
                payload=context["payload"],
            )
        )
        context_received_times.append(
            _timestamp(context["received_at"], "public_context_received_at")
        )
    derived_at = max(
        float(now),
        _timestamp(quote.get("received_at"), "capital_quote_received_at"),
        history_received,
        account_received,
        positions_received,
        orders_received,
        *context_received_times,
    )
    return build_capital_market_evidence_receipt(
        source_receipts=sorted(sources, key=lambda item: item["receipt_id"]),
        now=derived_at,
    )


__all__ = ["CapitalEvidenceReadClient", "collect_capital_market_evidence"]
