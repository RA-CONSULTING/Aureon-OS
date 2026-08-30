from __future__ import annotations

import threading

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


def test_link_system_does_not_start_sonar(monkeypatch):
    class Bus:
        def publish(self, thought):
            return thought

    monkeypatch.setattr(baton, '_ensure_stdio', lambda: None)
    monkeypatch.setattr(baton, '_enforce_real_data_only', lambda: None)
    monkeypatch.setattr(baton, '_audit_mode_enabled', lambda: False)
    monkeypatch.setattr(baton, '_import_side_effects_suppressed', lambda: False)
    monkeypatch.setattr(baton, 'THOUGHT_BUS_AVAILABLE', True)
    monkeypatch.setattr(baton, 'get_thought_bus', lambda **_kwargs: Bus())
    monkeypatch.setattr(
        baton,
        '_load_sonar',
        lambda: (_ for _ in ()).throw(AssertionError('sonar started during import link')),
    )
    baton._LINKED.discard('tests.import_safety')

    baton.link_system('tests.import_safety')


def test_thought_bus_construction_starts_no_background_thread(tmp_path):
    before = {thread.ident for thread in threading.enumerate()}
    ThoughtBus(persist_path=str(tmp_path / 'thoughts.jsonl'))
    started = [
        thread.name
        for thread in threading.enumerate()
        if thread.ident not in before
    ]
    assert 'WhaleSonarLoop' not in started
