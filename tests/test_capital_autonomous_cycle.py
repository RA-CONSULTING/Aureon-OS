from __future__ import annotations

from types import SimpleNamespace

from aureon.exchanges.capital_client import ObservationList
from aureon.governance.durable_contingency import DurableContingencyRecordRef
from aureon.governance.economic_boundary import EconomicGovernanceBlocked, EconomicIntent
from aureon.trading.bounded_capital_live_trade import (
    BoundedCapitalLiveTrade,
    CapitalTradePlan,
    FieldMoment,
    ProviderMoment,
)
from aureon.trading.capital_autonomous_cycle import CapitalAutonomousCycle

NOW = 1_786_632_900.0
DIGEST = "a" * 64
ACCOUNT = "b" * 64
HNC = "hnc:live_field:test"
AURIS = "auris:cosmic_state:test"


def _plan() -> CapitalTradePlan:
    return CapitalTradePlan(
        cycle_id="cycle-1",
        authorization_receipt_id="capital:owner:test",
        authorization_receipt={"receipt_id": "capital:owner:test"},
        account_id_hash=ACCOUNT,
        symbol="GOLD",
        epic="GOLD",
        side="BUY",
        quantity="0.01",
        stop_distance="5",
        profit_distance="5",
        entry_client_order_id="cycle-1-entry",
        close_client_order_id="cycle-1-close",
        target_moment=ProviderMoment(
            receipt_ids=("capital_position:pre",),
            moment_digest=DIGEST,
            source_timestamp=str(int(NOW - 1.0)),
            position_receipt_id="capital_position:pre",
        ),
        field_moment=FieldMoment(
            hnc_receipt_id=HNC,
            auris_receipt_id=AURIS,
            provider_receipt_ids=("provider:field",),
            provider_moment_digest="c" * 64,
            provider_source_timestamp=str(int(NOW - 1.0)),
        ),
        market_evidence_receipt={
            "capital_market_evidence_receipt_id": "capital:council-evidence:test"
        },
    )


def _entry_intent(plan: CapitalTradePlan) -> EconomicIntent:
    return EconomicIntent.build(
        venue="capital",
        environment="live",
        account_id_hash=plan.account_id_hash,
        method="POST",
        path="/positions",
        operation="MARKET_ORDER",
        purpose="ENTRY",
        symbol=plan.epic,
        side=plan.side,
        order_type="MARKET",
        quantity=plan.quantity,
        quote_quantity=None,
        limit_price=None,
        stop_price=plan.stop_distance,
        take_profit=plan.profit_distance,
        reduce_only=False,
        client_order_id=plan.entry_client_order_id,
        authorization_receipt_id=plan.authorization_receipt_id,
        cycle_id=plan.cycle_id,
        position_receipt_id=plan.target_moment.position_receipt_id,
        hnc_receipt_id=HNC,
        auris_receipt_id=AURIS,
        provider_receipt_ids=plan.target_moment.receipt_ids,
        provider_moment_digest=plan.target_moment.moment_digest,
        provider_source_timestamp=plan.target_moment.source_timestamp,
        body=plan.entry_body,
        body_bindings={
            "order_type": "/orderType",
            "quantity": "/size",
            "side": "/direction",
            "symbol": "/epic",
        },
        body_requires_json_numbers=True,
        decision_evidence={"recommended_side": "BUY"},
    )


def _submission(reference: str, purpose: str) -> dict:
    return {
        "dealReference": reference,
        "generated_values": False,
        "purpose": purpose,
        "source_id": f"capital_submission:{reference}",
        "source_timestamp": NOW - 1.0,
        "status": "submitted",
        "submission_acknowledged": True,
        "terminal_fill": False,
        "terminal_fill_receipt_complete": False,
        "truth_status": "real_observed",
    }


def _confirmation(reference: str, *, side: str, affected: str, complete: bool) -> dict:
    deal_id = "DEAL-1"
    receipt = {
        "affected_deals": [{"dealId": deal_id, "status": affected}],
        "dealReference": reference,
        "eligible_for_learning": complete,
        "eligible_for_pnl": complete,
        "eligible_for_state": complete,
        "epic": "GOLD",
        "filled_avg_price": 4_384.6,
        "filled_qty": 0.01,
        "generated_values": False,
        "provider_deal_id": deal_id,
        "provider_order_id": reference,
        "reason": "complete" if complete else "provider_fee_receipt_required",
        "received_at": NOW,
        "side": side,
        "source_id": f"capital_confirmation:{reference}",
        "source_timestamp": NOW - 1.0,
        "status": "filled" if complete else "filled_unsettled",
        "terminal_fill": True,
        "terminal_fill_receipt_complete": complete,
        "truth_status": "real_observed" if complete else "incomplete",
    }
    if complete:
        receipt["fee_receipt"] = {
            "amount": 0.0,
            "currency": "GBP",
            "generated_values": False,
            "source_id": f"capital_transaction_fee:{reference}",
            "source_timestamp": NOW - 1.0,
            "truth_status": "real_observed",
        }
    return receipt


def _open_positions() -> ObservationList:
    return ObservationList(
        [
            {
                "generated_values": False,
                "market": {"epic": "GOLD"},
                "position": {
                    "dealId": "DEAL-1",
                    "direction": "BUY",
                    "size": 0.01,
                },
                "source_id": "capital_position:DEAL-1",
                "source_timestamp": NOW - 1.0,
                "truth_status": "real_observed",
            }
        ],
        truth_status="incomplete",
        reason="provider_positions_visible_but_fee_receipts_required",
        source_timestamp=NOW - 1.0,
        received_at=NOW,
    )


def _empty_positions() -> ObservationList:
    return ObservationList(
        [],
        truth_status="real_observed",
        reason="no_open_positions",
        source_timestamp=NOW - 1.0,
        received_at=NOW,
    )


class _Route(BoundedCapitalLiveTrade):
    def __init__(self, *, hold: bool = False, submit_error: bool = False) -> None:
        self.hold = hold
        self.submit_error = submit_error
        self.calls = []

    def prepare(self, plan):
        self.calls.append("prepare")
        if self.hold:
            raise EconomicGovernanceBlocked("council_hold")
        return SimpleNamespace(
            entry_intent=_entry_intent(plan),
            recovery_reference=DurableContingencyRecordRef(
                record_digest="d" * 64,
                entry_state_anchor=plan.entry_state_anchor,
                bound_route_state_anchor="e" * 64,
            ),
        )

    def submit_entry(self, prepared):
        self.calls.append("entry")
        if self.submit_error:
            raise RuntimeError("transport_uncertain")
        return _submission("ENTRY-REF", "open_position")

    def close_from_recovery(self, **kwargs):
        self.calls.append(("close", kwargs["provider_deal_id"]))
        return _submission("CLOSE-REF", "close_position")


class _Client:
    def __init__(self, *, complete: bool) -> None:
        self.confirmations = {
            "ENTRY-REF": _confirmation(
                "ENTRY-REF", side="BUY", affected="OPENED", complete=complete
            ),
            "CLOSE-REF": _confirmation(
                "CLOSE-REF", side="SELL", affected="CLOSED", complete=complete
            ),
        }
        self.positions = [_open_positions(), _empty_positions()]
        self.transaction_calls = 0

    def confirm_order(self, deal_reference, *, fee_receipt=None):
        return dict(self.confirmations[deal_reference])

    def get_positions(self):
        return self.positions.pop(0)

    def get_transaction_history(self, last_period=600):
        self.transaction_calls += 1
        return ObservationList(
            [
                {
                    "amount": -1.0,
                    "currency": "GBP",
                    "generated_values": False,
                    "instrument_name": "GOLD",
                    "reference": "DEAL-1",
                    "source_id": "capital_transaction:DEAL-1:TRADE",
                    "source_timestamp": NOW - 1.0,
                    "status": "PROCESSED",
                    "transaction_type": "TRADE",
                    "truth_status": "real_observed",
                }
            ],
            truth_status="real_observed",
            reason="complete_provider_transaction_history",
            source_timestamp=NOW - 1.0,
            received_at=NOW,
        )


class _PendingEntryClient(_Client):
    def __init__(self) -> None:
        super().__init__(complete=True)
        self.entry_confirmation_calls = 0

    def confirm_order(self, deal_reference, *, fee_receipt=None):
        if deal_reference == "ENTRY-REF":
            self.entry_confirmation_calls += 1
            if self.entry_confirmation_calls == 1:
                return {"status": "pending", "terminal_fill": False}
        return super().confirm_order(deal_reference, fee_receipt=fee_receipt)


class _PendingCloseClient(_Client):
    def __init__(self) -> None:
        super().__init__(complete=True)
        self.close_confirmation_calls = 0

    def confirm_order(self, deal_reference, *, fee_receipt=None):
        if deal_reference == "CLOSE-REF":
            self.close_confirmation_calls += 1
            if self.close_confirmation_calls == 1:
                return {"status": "pending", "terminal_fill": False}
        return super().confirm_order(deal_reference, fee_receipt=fee_receipt)


def _cycle(tmp_path, route, client):
    route.client = client
    return CapitalAutonomousCycle(
        route=route,
        client=client,
        state_path=tmp_path / "capital-cycle.json",
        clock=lambda: NOW,
        sleeper=lambda _: None,
        confirmation_attempts=1,
        poll_interval_s=0,
    )


def test_full_accept_submits_entry_and_exact_close_once(tmp_path) -> None:
    route = _Route()
    client = _Client(complete=True)
    cycle = _cycle(tmp_path, route, client)

    result = cycle.execute(_plan())

    assert result["stage"] == "CLOSED_SETTLED"
    assert result["accounting_complete"] is True
    assert result["exposure_open"] is False
    assert route.calls == ["prepare", "entry", ("close", "DEAL-1")]
    assert cycle.execute(_plan()) == result
    assert route.calls == ["prepare", "entry", ("close", "DEAL-1")]


def test_council_hold_never_calls_entry_or_close(tmp_path) -> None:
    route = _Route(hold=True)
    cycle = _cycle(tmp_path, route, _Client(complete=True))

    result = cycle.execute(_plan())

    assert result["stage"] == "HELD_PRE_ENTRY"
    assert result["economic_mutation_attempted"] is False
    assert route.calls == ["prepare"]


def test_uncertain_entry_is_never_resubmitted_on_restart(tmp_path) -> None:
    route = _Route(submit_error=True)
    client = _Client(complete=True)
    first = _cycle(tmp_path, route, client).execute(_plan())

    restarted_route = _Route()
    second = _cycle(tmp_path, restarted_route, client).execute(_plan())

    assert first["stage"] == "ENTRY_AMBIGUOUS"
    assert first["reason"] == "RuntimeError"
    assert second["stage"] == "ENTRY_AMBIGUOUS"
    assert route.calls == ["prepare", "entry"]
    assert restarted_route.calls == []


def test_cycle_requires_same_client_as_governed_route(tmp_path) -> None:
    route = _Route()
    route.client = _Client(complete=True)

    try:
        CapitalAutonomousCycle(
            route=route,
            client=_Client(complete=True),
            state_path=tmp_path / "capital-cycle.json",
        )
    except ValueError as exc:
        assert str(exc) == "capital_cycle_route_client_identity_required"
    else:
        raise AssertionError("mismatched client must fail closed")


def test_closed_trade_without_phase_fee_receipts_stays_unsettled(tmp_path) -> None:
    route = _Route()
    client = _Client(complete=False)

    result = _cycle(tmp_path, route, client).execute(_plan())

    assert result["stage"] == "CLOSED_UNSETTLED"
    assert result["accounting_complete"] is False
    assert result["exposure_open"] is False
    assert result["learning_eligible"] is False
    assert client.transaction_calls == 1


def test_restart_reconciles_entry_then_closes_without_entry_resubmit(tmp_path) -> None:
    first_route = _Route()
    client = _PendingEntryClient()
    first = _cycle(tmp_path, first_route, client).execute(_plan())

    restarted_route = _Route()
    second = _cycle(tmp_path, restarted_route, client).execute(_plan())

    assert first["stage"] == "ENTRY_RECONCILIATION_PENDING"
    assert second["stage"] == "CLOSED_SETTLED"
    assert first_route.calls == ["prepare", "entry"]
    assert restarted_route.calls == [("close", "DEAL-1")]


def test_restart_reconciles_close_without_close_resubmit(tmp_path) -> None:
    first_route = _Route()
    client = _PendingCloseClient()
    first = _cycle(tmp_path, first_route, client).execute(_plan())

    restarted_route = _Route()
    second = _cycle(tmp_path, restarted_route, client).execute(_plan())

    assert first["stage"] == "CLOSE_RECONCILIATION_PENDING"
    assert first["exposure_open"] is True
    assert second["stage"] == "CLOSED_SETTLED"
    assert first_route.calls == ["prepare", "entry", ("close", "DEAL-1")]
    assert restarted_route.calls == []
