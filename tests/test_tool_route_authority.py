from __future__ import annotations

from copy import deepcopy

import pytest

import aureon.governance.tool_route_authority as route_module
from aureon.governance.tool_route_authority import (
    build_tool_route_authority_request,
    issue_tool_route_authority_lease,
    validate_tool_route_authority_lease,
)
from aureon.inhouse_ai.tool_registry import ToolEffect, ToolRegistry
from aureon.swarm.auris_node_receipts import DEFAULT_MAX_AGE_S

NOW = 1_800_000_000.0
GOVERNANCE_PROPOSAL = "7" * 64
DUAL_ID = "governance:dual_key:" + ("8" * 64)


def _proposal():
    registry = ToolRegistry(include_builtins=False)
    registry.define_tool(
        "mutate_fixture",
        "bounded fixture mutation",
        {"type": "object", "properties": {}},
        lambda arguments: '{"ok":true}',
        effect=ToolEffect.LOCAL_MUTATION,
        operation_id="aureon.test.route-authority.v1",
    )
    return registry.build_dispatch_proposal(
        tool_call_id="route-call",
        runner_turn_index=1,
        response_call_index=0,
        name="mutate_fixture",
        arguments={},
        context={"trace_id": "route-trace"},
    )


def _dual_key() -> dict:
    return {
        "decision": "ACCEPT",
        "receipt_id": DUAL_ID,
        "proposal_digest": GOVERNANCE_PROPOSAL,
        "source_timestamp": NOW - 1.0,
    }


@pytest.fixture(autouse=True)
def _strict_dual_key_stub(monkeypatch):
    def _validate(value, *, now, max_age_s):
        del max_age_s
        assert now == NOW
        return dict(value)

    monkeypatch.setattr(route_module, "validate_dual_key_receipt", _validate)


def _request():
    return build_tool_route_authority_request(
        _proposal(),
        _dual_key(),
        expected_governance_proposal_digest=GOVERNANCE_PROPOSAL,
        now=NOW,
    )


def _lease(request, **overrides):
    params = {
        "supplier_id": "resolver:test-route-authority",
        "mandate_receipt_id": "mandate:director:test",
        "mandate_receipt_digest": "9" * 64,
        "nonce": "route-authority-nonce-0001",
        "issued_at": NOW,
        "not_before": NOW,
        "expires_at": NOW + 1.0,
    }
    params.update(overrides)
    return issue_tool_route_authority_lease(request, **params)


def test_exact_short_lived_lease_binds_every_route_input() -> None:
    request = _request()
    lease = _lease(request)

    validated = validate_tool_route_authority_lease(
        lease,
        request=request,
        expected_supplier_id="resolver:test-route-authority",
        now=NOW + 0.5,
    )

    assert validated == lease
    assert validated["effect_executed"] is False
    assert validated["one_use"] is True
    assert validated["truth_status"] == "trusted_supplier_assertion"
    assert validated["receipt_id"].startswith("tool:route-authority:")


def test_accept_for_another_governance_proposal_cannot_be_laundered() -> None:
    with pytest.raises(ValueError, match="governance_proposal_mismatch"):
        build_tool_route_authority_request(
            _proposal(),
            _dual_key(),
            expected_governance_proposal_digest="a" * 64,
            now=NOW,
        )


def test_dual_key_freshness_window_cannot_be_expanded_by_caller() -> None:
    with pytest.raises(ValueError, match="bounded_dual_key_max_age"):
        build_tool_route_authority_request(
            _proposal(),
            _dual_key(),
            expected_governance_proposal_digest=GOVERNANCE_PROPOSAL,
            now=NOW,
            dual_key_max_age_s=DEFAULT_MAX_AGE_S + 1.0,
        )


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("proposal_digest", "tool:proposal:" + ("b" * 64)),
        ("effect", ToolEffect.PRIVILEGED.value),
        ("operation_id", "aureon.test.changed.v1"),
        ("dual_key_receipt_digest", "c" * 64),
        ("effect_executed", True),
        ("one_use", False),
    ),
)
def test_tampered_lease_never_validates(field: str, value) -> None:
    request = _request()
    tampered = deepcopy(_lease(request))
    tampered[field] = value

    with pytest.raises(ValueError):
        validate_tool_route_authority_lease(
            tampered,
            request=request,
            expected_supplier_id="resolver:test-route-authority",
            now=NOW + 0.5,
        )


def test_expired_or_overlong_lease_is_rejected() -> None:
    request = _request()
    lease = _lease(request)
    with pytest.raises(ValueError, match="fresh_short_lived"):
        validate_tool_route_authority_lease(
            lease,
            request=request,
            expected_supplier_id="resolver:test-route-authority",
            now=NOW + 1.0,
        )

    with pytest.raises(ValueError, match="fresh_short_lived"):
        _lease(request, expires_at=NOW + 6.0)

    with pytest.raises(ValueError, match="bounded_max_ttl"):
        _lease(request, expires_at=NOW + 6.0, max_ttl_s=90.0)


def test_independent_mandate_receipt_is_required() -> None:
    request = _request()
    with pytest.raises(ValueError, match="independent_mandate"):
        _lease(request, mandate_receipt_id=DUAL_ID)
