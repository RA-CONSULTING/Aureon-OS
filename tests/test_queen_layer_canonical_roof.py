from __future__ import annotations

import sys
from types import SimpleNamespace

from aureon.queen import queen_layer


def test_queen_layer_holds_before_any_queen_or_provider_import(monkeypatch) -> None:
    monkeypatch.setattr(
        "aureon.queen.queen_process_roof.get_canonical_queen_process_roof",
        lambda: None,
    )
    before = set(sys.modules)
    layer = queen_layer.QueenLayer(live_trading=True)

    result = layer.boot()

    imported = set(sys.modules) - before
    assert result["status"] == "HOLD"
    assert result["reason"] == "canonical_queen_process_roof_required"
    assert result["live_trading"] is False
    assert result["provider_call_count"] == 0
    assert result["order_call_count"] == 0
    assert "aureon.utils.aureon_queen_hive_mind" not in imported
    assert "aureon.exchanges.kraken_client" not in imported
    assert "aureon.exchanges.binance_client" not in imported
    assert "aureon.exchanges.capital_client" not in imported
    assert "aureon.exchanges.alpaca_client" not in imported


def test_safe_activate_routes_queen_factory_through_roof(monkeypatch) -> None:
    calls = []

    class FakeRoof:
        def activate(self, module_name, factory):
            calls.append(module_name)
            return SimpleNamespace(status="ACTIVE", reason=None, instance=factory())

    class QueenAlpha:
        pass

    imported = []
    monkeypatch.setattr(
        "aureon.queen.queen_process_roof.get_canonical_queen_process_roof",
        lambda: FakeRoof(),
    )
    monkeypatch.setattr(
        queen_layer.importlib,
        "import_module",
        lambda module_name: imported.append(module_name)
        or SimpleNamespace(QueenAlpha=QueenAlpha),
    )
    layer = queen_layer.QueenLayer()

    instance = layer._safe_activate(
        "queen_alpha",
        "queen_alpha",
        class_name="QueenAlpha",
    )

    assert isinstance(instance, QueenAlpha)
    assert calls == ["aureon.queen.queen_alpha"]
    assert imported == ["aureon.queen.queen_alpha"]
