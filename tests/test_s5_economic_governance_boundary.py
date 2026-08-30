from __future__ import annotations

import ast
import inspect
import json
import textwrap

import pytest
from test_s5_kraken_spot_readiness import _engine_and_evidence

from aureon.governance.economic_boundary import EconomicGovernanceBlocked
from aureon.strategies.s5_live_execution import S5LiveExecutionEngine


@pytest.mark.parametrize(
    ('failure', 'phase'),
    [
        ('HOLD', 'prepare'),
        ('ABORT', 'prepare'),
        ('stale', 'prepare'),
        ('tamper', 'prepare'),
        ('replay', 'consume'),
        ('path', 'consume'),
        ('body', 'consume'),
    ],
)
def test_non_accept_or_inexact_permit_never_calls_kraken(
    tmp_path,
    failure: str,
    phase: str,
) -> None:
    engine, kraken, evidence, opportunity, _ = _engine_and_evidence(
        tmp_path,
        'success',
    )
    boundary = engine.economic_governance_boundary
    error = EconomicGovernanceBlocked(failure)
    if phase == 'prepare':
        boundary.prepare_mutation.side_effect = error
    else:
        boundary.consume_and_call.side_effect = error

    result = engine._submit_intent(opportunity, bundle=evidence)

    assert result['status'] == 'no_data'
    assert result['reason'] in {
        'economic_governance_not_accepted',
        'economic_permit_rejected_before_transport',
    }
    assert kraken.submissions == []
    assert engine._pending_intents == {}
    assert len(engine._closed_intents) == 1


def test_missing_boundary_is_zero_call_and_zero_state(tmp_path) -> None:
    engine, kraken, evidence, opportunity, state_path = (
        _engine_and_evidence(tmp_path, 'success')
    )
    engine.economic_governance_boundary = None

    result = engine._submit_intent(opportunity, bundle=evidence)

    assert result['reason'] == 'economic_governance_boundary_required'
    assert engine.check_runtime_ready() is False
    assert kraken.submissions == []
    assert engine._pending_intents == {}
    assert not state_path.exists()


def test_accept_consumes_once_after_durable_lineage_snapshot(tmp_path) -> None:
    engine, kraken, evidence, opportunity, state_path = (
        _engine_and_evidence(tmp_path, 'success')
    )
    boundary = engine.economic_governance_boundary

    result = engine._submit_intent(opportunity, bundle=evidence)

    assert result['status'] == 'pending_reconciliation'
    assert len(kraken.submissions) == 1
    boundary.consume_and_call.assert_called_once()
    consume_kwargs = boundary.consume_and_call.call_args.kwargs
    assert consume_kwargs['method'] == 'POST'
    assert consume_kwargs['path'] == '/0/private/AddOrder'
    assert consume_kwargs['body'] == {
        'pair': 'XBTUSD',
        'type': 'buy',
        'ordertype': 'market',
        'volume': '1',
        'cl_ord_id': kraken.submissions[0]['client_order_id'],
    }
    before_call = kraken.snapshots_before_post[0]['pending_intents'][0]
    assert before_call['state'] == 'submission_in_progress'
    assert before_call['governance_permit_consumed'] is False
    assert before_call['durable_state_anchor']
    assert before_call['economic_intent_digest']
    assert before_call['economic_body_digest']
    assert before_call['provider_moment_digest']
    assert before_call['governance_permit_id']
    assert before_call['governance_dual_receipt_id']
    assert before_call['governance_proposal_digest']
    assert before_call['contingency_warrant_id']
    assert before_call['contingency_scope_digest']
    persisted = json.loads(state_path.read_text(encoding='utf-8'))
    assert persisted['pending_intents'][0][
        'governance_permit_consumed'
    ] is True


def test_static_kraken_calls_are_only_boundary_transport_lambdas() -> None:
    methods = (
        S5LiveExecutionEngine._submit_intent_locked,
        S5LiveExecutionEngine
        ._submit_preapproved_contingency_reduction_locked,
    )
    for method in methods:
        tree = ast.parse(textwrap.dedent(inspect.getsource(method)))
        parents: dict[ast.AST, ast.AST] = {}
        for parent in ast.walk(tree):
            for child in ast.iter_child_nodes(parent):
                parents[child] = parent
        provider_calls = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == 'place_order'
        ]
        consume_calls = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == 'consume_and_call'
        ]
        assert len(provider_calls) == 1
        assert len(consume_calls) == 1
        transport = next(
            keyword.value
            for keyword in consume_calls[0].keywords
            if keyword.arg == 'transport'
        )
        assert isinstance(transport, ast.Lambda)
        assert provider_calls[0] is transport.body
        assert parents[provider_calls[0]] is transport
        source = inspect.getsource(method)
        assert '._private(' not in source
        assert '.place_market_order(' not in source
