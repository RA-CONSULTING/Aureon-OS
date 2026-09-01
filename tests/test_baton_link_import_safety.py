from __future__ import annotations

import threading

import pytest

from aureon.core import aureon_baton_link as baton
from aureon.core.aureon_thought_bus import ThoughtBus


def test_real_data_policy_does_not_enable_live_orders(monkeypatch):
    monkeypatch.setenv('AUREON_AUDIT_MODE', '0')
    monkeypatch.setenv('REAL_DATA_ONLY', '1')
    execution_controls = {
        'AUREON_DRY_RUN': '1',
        'DRY_RUN': '1',
        'BINANCE_DRY_RUN': 'true',
        'KRAKEN_DRY_RUN': 'true',
        'ALPACA_PAPER': 'true',
        'BINANCE_TESTNET': 'true',
        'CAPITAL_DEMO': '1',
        'PAPER_TRADING': 'true',
    }
    for key, value in execution_controls.items():
        monkeypatch.setenv(key, value)

    baton._enforce_real_data_only()

    for key, value in execution_controls.items():
        assert baton.os.environ[key] == value
    assert baton.os.environ['AUREON_ALLOW_SIM_FALLBACK'] == '0'
    assert baton.os.environ['STATUS_MOCK'] == 'false'


def test_link_system_is_unconditional_no_effect_hold(monkeypatch):
    def fail(reason):
        return lambda *_args, **_kwargs: pytest.fail(reason)

    monkeypatch.setenv('AUREON_ACTIVATE_ON_IMPORT', '1')
    monkeypatch.setattr(baton, '_ensure_stdio', fail('stdio mutated during import link'))
    monkeypatch.setattr(baton, '_enforce_real_data_only', fail('environment mutated'))
    monkeypatch.setattr(baton, 'get_thought_bus', fail('ThoughtBus constructed'))
    monkeypatch.setattr(baton, '_load_sonar', fail('sonar started during import link'))
    baton._LINKED.discard('tests.import_safety')

    baton.link_system('tests.import_safety')

    assert 'tests.import_safety' not in baton._LINKED


def test_autonomous_control_and_stage_emission_are_held_before_effects(monkeypatch):
    monkeypatch.setattr(
        baton,
        '_log_baton_event',
        lambda *_args, **_kwargs: pytest.fail('baton HOLD must not write logs'),
    )
    monkeypatch.setattr(
        baton,
        'get_thought_bus',
        lambda *_args, **_kwargs: pytest.fail('baton HOLD must not construct bus'),
    )

    with pytest.raises(RuntimeError, match='autonomous_control_hold'):
        baton.activate_autonomous_control()
    with pytest.raises(RuntimeError, match='baton_stage_hold'):
        baton.emit_stage('execute', 'tests')


def test_thought_bus_construction_starts_no_background_thread(tmp_path):
    before = {thread.ident for thread in threading.enumerate()}
    ThoughtBus(persist_path=str(tmp_path / 'thoughts.jsonl'))
    started = [
        thread.name
        for thread in threading.enumerate()
        if thread.ident not in before
    ]
    assert 'WhaleSonarLoop' not in started
