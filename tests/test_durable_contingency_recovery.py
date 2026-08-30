from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from multiprocessing import get_context
from pathlib import Path
from typing import Any

import pytest
from test_economic_governance_boundary import (
    POSITION_BEFORE,
    _boundary,
    _entry_intent,
    _reduction_intent,
    _scope,
)

from aureon.governance.durable_contingency import (
    DurableContingencyRecordRef,
    DurableContingencyStateError,
    bind_durable_contingency_recovery,
)
from aureon.governance.economic_boundary import EconomicGovernanceBlocked

ADAPTER_ID = 'adapter:durable-contingency-test:v1'


def _adapter(boundary, path: Path, clock):
    return bind_durable_contingency_recovery(
        adapter_id=ADAPTER_ID,
        trusted_adapter_ids=frozenset({ADAPTER_ID}),
        boundary=boundary,
        store_path=path,
        clock=clock,
        claim_ttl_s=5.0,
    )


def _fresh_restart(monkeypatch, tmp_path):
    first_boundary, first_harness, clock = _boundary(monkeypatch)
    entry = _entry_intent(clock)
    scope = _scope(clock, entry)
    warrant = first_boundary.approve_contingency_warrant(scope)
    store_path = tmp_path / 'private' / 'cycle.contingency.json'
    first = _adapter(first_boundary, store_path, clock)
    reference = first.register(
        warrant,
        scope,
        entry_state_anchor='d' * 64,
    )
    first.bind_route_state(reference)
    first.verify_route_binding(reference)

    restarted_boundary, restarted_harness, _ = _boundary(
        monkeypatch,
        clock=clock,
    )
    restarted = _adapter(restarted_boundary, store_path, clock)
    return (
        entry,
        reference,
        restarted,
        restarted_harness,
        clock,
        store_path,
        first_harness,
    )


def test_field_provider_ids_survive_json_sidecar_round_trip(
    monkeypatch,
    tmp_path,
) -> None:
    boundary, _, clock = _boundary(monkeypatch)
    entry = _entry_intent(clock)
    scope = replace(
        _scope(clock, entry),
        field_provider_receipt_ids=(
            "provider:field:auris",
            "provider:field:hnc",
        ),
        field_provider_moment_digest="e" * 64,
        field_provider_source_timestamp=str(int(clock.value - 1)),
    )
    warrant = boundary.approve_contingency_warrant(scope)
    recovery = _adapter(
        boundary,
        tmp_path / "private" / "field-moment.contingency.json",
        clock,
    )

    reference = recovery.register(
        warrant,
        scope,
        entry_state_anchor="d" * 64,
    )
    recovery.bind_route_state(reference)
    recovery.verify_route_binding(reference)

    assert recovery.material_for_recovery(reference).scope == scope


def _consume(recovery, prepared, calls: list[str]):
    intent = prepared.intent
    return recovery.consume_and_call(
        prepared,
        method=intent.method,
        path=intent.path,
        body=json.loads(intent.body_json),
        transport=lambda: calls.append('provider') or {'ok': True},
    )


def _process_claim_once(store_path, reference, barrier, outcomes) -> None:
    patcher = pytest.MonkeyPatch()
    try:
        boundary, _, clock = _boundary(patcher)
        recovery = _adapter(boundary, Path(store_path), clock)
        intent = _reduction_intent(clock, _entry_intent(clock))
        barrier.wait(timeout=10)
        recovery.prepare_reduction(reference, intent)
        outcomes.put(('prepared', recovery.status(reference)))
    except BaseException as exc:
        outcomes.put(('blocked', type(exc).__name__))
    finally:
        patcher.undo()


def test_fresh_process_recovers_exact_scope_once_without_new_voices(
    monkeypatch,
    tmp_path,
) -> None:
    (
        entry,
        reference,
        recovery,
        restarted_harness,
        clock,
        _,
        first_harness,
    ) = _fresh_restart(monkeypatch, tmp_path)
    intent = _reduction_intent(clock, entry)

    prepared = recovery.prepare_reduction(reference, intent)
    calls: list[str] = []
    result = _consume(recovery, prepared, calls)

    assert result == {'ok': True}
    assert calls == ['provider']
    assert prepared.permit.permit_kind == (
        'durable_contingency_reduction'
    )
    assert len(first_harness.calls) == 1
    assert restarted_harness.calls == []
    with pytest.raises(EconomicGovernanceBlocked):
        recovery.prepare_reduction(reference, intent)
    assert calls == ['provider']


@pytest.mark.parametrize(
    ('mutation', 'overrides'),
    [
        ('route', {'path': '/api/v3/wrong'}),
        ('account', {'account_id_hash': 'e' * 64}),
        (
            'authorization',
            {'authorization_receipt_id': 'authorization:wrong'},
        ),
        ('cycle', {'cycle_id': 'cycle-wrong'}),
    ],
)
def test_wrong_route_account_authorization_or_cycle_is_zero_call(
    monkeypatch,
    tmp_path,
    mutation: str,
    overrides: dict[str, Any],
) -> None:
    entry, reference, recovery, _, clock, _, _ = _fresh_restart(
        monkeypatch,
        tmp_path,
    )
    intent = _reduction_intent(clock, entry, **overrides)
    calls: list[str] = []

    with pytest.raises(EconomicGovernanceBlocked):
        prepared = recovery.prepare_reduction(reference, intent)
        _consume(recovery, prepared, calls)

    assert calls == [], mutation


@pytest.mark.parametrize('mutation', ['position', 'excess'])
def test_wrong_position_or_excess_is_zero_call(
    monkeypatch,
    tmp_path,
    mutation: str,
) -> None:
    entry, reference, recovery, _, clock, _, _ = _fresh_restart(
        monkeypatch,
        tmp_path,
    )
    if mutation == 'position':
        intent = _reduction_intent(
            clock,
            entry,
            position_receipt_id=POSITION_BEFORE,
            provider_receipt_ids={
                POSITION_BEFORE,
                'provider:binance:fill:entry',
                'provider:binance:account:current',
            },
        )
    else:
        intent = _reduction_intent(
            clock,
            entry,
            quantity='0.003',
            observed_exposure_quantity='0.003',
            body={'quantity': '0.003'},
        )
    calls: list[str] = []

    with pytest.raises(EconomicGovernanceBlocked):
        prepared = recovery.prepare_reduction(reference, intent)
        _consume(recovery, prepared, calls)

    assert calls == []


def test_reciprocal_binding_and_sidecar_tamper_are_zero_call(
    monkeypatch,
    tmp_path,
) -> None:
    entry, reference, recovery, _, clock, store_path, _ = (
        _fresh_restart(monkeypatch, tmp_path)
    )
    wrong_reference = replace(
        reference,
        bound_route_state_anchor='f' * 64,
    )
    calls: list[str] = []

    with pytest.raises(EconomicGovernanceBlocked):
        recovery.prepare_reduction(
            wrong_reference,
            _reduction_intent(clock, entry),
        )
    raw = json.loads(store_path.read_text(encoding='utf-8'))
    raw['records'][reference.record_digest]['scope']['cycle_id'] = 'tampered'
    store_path.write_text(json.dumps(raw), encoding='utf-8')
    with pytest.raises(DurableContingencyStateError):
        recovery.prepare_reduction(
            reference,
            _reduction_intent(clock, entry),
        )

    assert calls == []


def test_expired_warrant_is_zero_call(
    monkeypatch,
    tmp_path,
) -> None:
    entry, reference, recovery, _, clock, _, _ = _fresh_restart(
        monkeypatch,
        tmp_path,
    )
    clock.value += 31
    intent = _reduction_intent(clock, entry)
    calls: list[str] = []

    with pytest.raises(EconomicGovernanceBlocked):
        prepared = recovery.prepare_reduction(reference, intent)
        _consume(recovery, prepared, calls)

    assert calls == []


def test_competing_adapters_claim_once_and_replay_is_zero_call(
    monkeypatch,
    tmp_path,
) -> None:
    entry, reference, first, _, clock, store_path, _ = _fresh_restart(
        monkeypatch,
        tmp_path,
    )
    second_boundary, second_harness, _ = _boundary(
        monkeypatch,
        clock=clock,
    )
    second = _adapter(second_boundary, store_path, clock)
    intent = _reduction_intent(clock, entry)
    calls: list[str] = []

    def claim(adapter):
        try:
            prepared = adapter.prepare_reduction(reference, intent)
            return _consume(adapter, prepared, calls)
        except (OSError, BlockingIOError, EconomicGovernanceBlocked) as exc:
            return exc

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(claim, (first, second)))
    successful = [
        item for item in outcomes
        if not isinstance(item, BaseException)
    ]
    assert successful == [{'ok': True}]
    assert second_harness.calls == []
    for adapter in (first, second):
        with pytest.raises(EconomicGovernanceBlocked):
            adapter.prepare_reduction(reference, intent)
    assert calls == ['provider']


def test_competing_processes_can_persist_only_one_prepared_claim(
    monkeypatch,
    tmp_path,
) -> None:
    _, reference, recovery, _, _, store_path, _ = _fresh_restart(
        monkeypatch,
        tmp_path,
    )
    context = get_context('spawn')
    barrier = context.Barrier(2)
    outcomes = context.Queue()
    processes = [
        context.Process(
            target=_process_claim_once,
            args=(str(store_path), reference, barrier, outcomes),
        )
        for _ in range(2)
    ]

    for process in processes:
        process.start()
    for process in processes:
        process.join(timeout=20)
        assert process.exitcode == 0
    results = [outcomes.get(timeout=5) for _ in processes]

    assert sum(result[0] == 'prepared' for result in results) == 1
    assert sum(result[0] == 'blocked' for result in results) == 1
    assert recovery.status(reference) == 'PERMIT_PREPARED'


def test_ambiguous_transport_stays_reconciliation_only(
    monkeypatch,
    tmp_path,
) -> None:
    entry, reference, recovery, _, clock, _, _ = _fresh_restart(
        monkeypatch,
        tmp_path,
    )
    intent = _reduction_intent(clock, entry)
    prepared = recovery.prepare_reduction(reference, intent)
    calls: list[str] = []

    with pytest.raises(TimeoutError):
        recovery.consume_and_call(
            prepared,
            method=intent.method,
            path=intent.path,
            body=json.loads(intent.body_json),
            transport=lambda: calls.append('provider')
            or (_ for _ in ()).throw(TimeoutError('ambiguous')),
        )

    assert recovery.status(reference) == 'AMBIGUOUS'
    with pytest.raises(EconomicGovernanceBlocked):
        recovery.prepare_reduction(reference, intent)
    assert calls == ['provider']
