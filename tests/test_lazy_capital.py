"""Hermetic contract for Orca's lazy Capital.com client construction."""

from __future__ import annotations

from aureon.bots import orca_complete_kill_cycle as orca_module


def test_lazy_capital_constructs_once_and_caches(monkeypatch) -> None:
    created: list[object] = []

    class _CapitalClient:
        pass

    def _factory() -> _CapitalClient:
        client = _CapitalClient()
        created.append(client)
        return client

    monkeypatch.setattr(orca_module, "CapitalClient", _factory)
    orca = orca_module.OrcaKillCycle.__new__(orca_module.OrcaKillCycle)
    orca.clients = {"capital": None}

    assert orca.clients["capital"] is None
    first = orca._ensure_capital_client()
    second = orca._ensure_capital_client()

    assert len(created) == 1
    assert first is created[0]
    assert second is first
    assert orca.clients["capital"] is first
