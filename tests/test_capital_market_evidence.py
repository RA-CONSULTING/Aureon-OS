from __future__ import annotations

import copy
import hashlib
import json
from typing import Any

import pytest

from aureon.trading.capital_market_evidence import (
    CAPITAL_EVIDENCE_PREFIX,
    build_capital_market_evidence_receipt,
    build_capital_market_source_receipt,
    capital_market_decision_summary,
    capital_market_provider_moment,
    validate_capital_market_evidence_receipt,
)

NOW = 1_786_480_000.0
EPIC = "CS.D.GOLD.CFD.IP"


def _sha(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(raw.encode()).hexdigest()


def _rehash(receipt: dict[str, Any]) -> None:
    causal = {k: v for k, v in receipt.items() if k not in {"receipt_id", "derived_at"}}
    receipt["receipt_id"] = f"{CAPITAL_EVIDENCE_PREFIX}{_sha(causal)}"


def _bars(direction: int = 1) -> list[dict[str, Any]]:
    result = []
    for index in range(30):
        mid = 4_300.0 + direction * index
        bid, ask = mid - 0.1, mid + 0.1
        result.append(
            {
                "timestamp": NOW - (30 - index) * 60.0,
                "open_bid": bid,
                "open_ask": ask,
                "high_bid": bid + 0.4,
                "high_ask": ask + 0.4,
                "low_bid": bid - 0.4,
                "low_ask": ask - 0.4,
                "close_bid": bid,
                "close_ask": ask,
                "volume": 100 + index,
            }
        )
    return result


def _source(kind: str, payload: dict[str, Any], *, observed: float = NOW - 1.0):
    uris = {
        "capital_quote": "https://api-capital.backend-capital.com/api/v1/markets/GOLD",
        "capital_price_history": "https://api-capital.backend-capital.com/api/v1/prices/GOLD",
        "capital_account": "https://api-capital.backend-capital.com/api/v1/accounts",
        "capital_positions": "https://api-capital.backend-capital.com/api/v1/positions",
        "capital_working_orders": "https://api-capital.backend-capital.com/api/v1/workingorders",
        "cftc_cot": "https://publicreporting.cftc.gov/resource/6dca-aqww.json",
        "treasury_yield": "https://home.treasury.gov/resource-center/data-chart-center/interest-rates",
    }
    return build_capital_market_source_receipt(
        source_kind=kind,
        source_id=f"source:{kind}:observed",
        source_uri=uris[kind],
        source_timestamp=observed,
        received_at=NOW - 0.5,
        payload=payload,
    )


def _sources(direction: int = 1, *, context: bool = True):
    bars = _bars(direction)
    mid = 4_300.0 + direction * 29
    items = [
        _source(
            "capital_quote",
            {
                "ask": mid + 0.1,
                "bid": mid - 0.1,
                "change_pct": 0.25 * direction,
                "epic": EPIC,
                "high": mid + 2.0,
                "low": mid - 2.0,
                "market_status": "TRADEABLE",
                "symbol": "GOLD",
            },
        ),
        _source("capital_price_history", {"bars": bars, "epic": EPIC, "resolution": "MINUTE"}),
        _source("capital_account", {"available": 226.88, "balance": 226.88, "currency": "GBP"}),
        _source("capital_positions", {"open_position_count": 0}),
        _source("capital_working_orders", {"working_order_count": 0}),
    ]
    if context:
        items += [
            _source(
                "cftc_cot",
                {"market": "GOLD", "report_date": "2026-08-11", "net_contracts": 1},
                observed=NOW - 86_400.0,
            ),
            _source(
                "treasury_yield",
                {"date": "2026-08-12", "ten_year_yield_pct": 4.2},
                observed=NOW - 86_400.0,
            ),
        ]
    return sorted(items, key=lambda item: item["receipt_id"])


def _evidence(direction: int = 1, *, context: bool = True):
    return build_capital_market_evidence_receipt(
        source_receipts=_sources(direction, context=context), now=NOW, ghost_horizon_bars=3
    )


def test_validated_ghost_receipt_can_influence_but_never_authorize() -> None:
    receipt = validate_capital_market_evidence_receipt(_evidence(), now=NOW)
    probability = receipt["quantum_probability_validation"]

    assert receipt["action_influence_allowed"] is True
    assert receipt["recommended_side"] == "BUY"
    assert probability["calibration_status"] == "validated"
    assert probability["sample_count"] >= 12
    assert probability["model_class"] == "derived_probability_not_physical_quantum_evidence"
    assert probability["outcomes"][0]["pnl_points_after_spread"] == pytest.approx(2.8)
    assert receipt["action_eligible"] is False
    assert receipt["economic_mutation"] is False


def test_missing_official_context_or_unvalidated_model_forces_hold() -> None:
    missing = _evidence(context=False)
    assert missing["recommended_side"] == "HOLD"
    assert "official_cftc_and_treasury_context_required" in missing["blockers"]

    sources = _sources()
    history = next(x for x in sources if x["source_kind"] == "capital_price_history")
    flat = _bars()
    for bar in flat:
        for key in ("open_bid", "high_bid", "low_bid", "close_bid"):
            bar[key] = 4_299.9
        for key in ("open_ask", "high_ask", "low_ask", "close_ask"):
            bar[key] = 4_300.1
    sources[sources.index(history)] = _source(
        "capital_price_history", {"bars": flat, "epic": EPIC, "resolution": "MINUTE"}
    )
    held = build_capital_market_evidence_receipt(
        source_receipts=sorted(sources, key=lambda x: x["receipt_id"]), now=NOW
    )
    assert held["recommended_side"] == "HOLD"
    assert held["action_influence_allowed"] is False


def test_provider_moment_and_council_summary_are_exactly_bound() -> None:
    receipt = _evidence(-1)
    moment = capital_market_provider_moment(receipt, now=NOW)
    summary = capital_market_decision_summary(receipt, now=NOW)

    assert moment["source_timestamp"] == "1786479999"
    assert moment["receipt_ids"] == tuple(sorted({receipt["receipt_id"], *receipt["component_receipt_ids"]}))
    assert moment["moment_digest"] == receipt["target_provider_moment_digest"]
    assert moment["position_receipt_id"] == receipt["position_receipt_id"]
    assert summary["capital_market_evidence_receipt_id"] == receipt["receipt_id"]
    assert summary["recommended_side"] == "SELL"


def test_unofficial_context_stale_quote_and_source_tamper_reject() -> None:
    with pytest.raises(ValueError, match="official_cftc_cot_source_required"):
        build_capital_market_source_receipt(
            source_kind="cftc_cot",
            source_id="source:cftc:spoof",
            source_uri="https://example.com/cot.json",
            source_timestamp=NOW - 1.0,
            received_at=NOW - 0.5,
            payload={"market": "GOLD"},
        )
    sources = _sources()
    quote = next(x for x in sources if x["source_kind"] == "capital_quote")
    sources[sources.index(quote)] = _source("capital_quote", quote["payload"], observed=NOW - 31.0)
    with pytest.raises(ValueError, match="fresh_source_required"):
        build_capital_market_evidence_receipt(
            source_receipts=sorted(sources, key=lambda x: x["receipt_id"]), now=NOW
        )
    sources = _sources()
    next(x for x in sources if x["source_kind"] == "capital_quote")["payload"]["bid"] += 10
    with pytest.raises(ValueError, match="capital_source_content_digest_mismatch"):
        build_capital_market_evidence_receipt(source_receipts=sources, now=NOW)


@pytest.mark.parametrize(
    ("mutator", "reason"),
    [
        (lambda r: r.__setitem__("recommended_side", "SELL"), "capital_decision_recomputation_mismatch"),
        (lambda r: r.__setitem__("epic", "FAKE.EPIC"), "capital_target_identity_recomputation_mismatch"),
        (
            lambda r: r["quantum_probability_validation"].__setitem__("gross_loss_points", -0.0),
            "capital_ghost_probability_recomputation_mismatch",
        ),
    ],
)
def test_rehashed_derived_tamper_still_rejects(mutator, reason: str) -> None:
    receipt = copy.deepcopy(_evidence())
    mutator(receipt)
    _rehash(receipt)
    with pytest.raises(ValueError, match=reason):
        validate_capital_market_evidence_receipt(receipt, now=NOW)
