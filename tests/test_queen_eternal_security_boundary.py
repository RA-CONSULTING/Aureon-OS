from __future__ import annotations

import ast
import builtins
import importlib
import socket
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "aureon" / "queen" / "queen_eternal_machine.py"
MODULE_NAME = "aureon.queen.queen_eternal_machine"
FORBIDDEN_PROVIDER_IMPORTS = (
    "aureon.exchanges",
    "aureon.core.api_gateway",
)


def _module():
    return importlib.import_module(MODULE_NAME)


def _mint_authorization(monkeypatch, plan):
    from aureon.queen import queen_force_trade_governance as governance

    monkeypatch.setattr(governance, "_module_available", lambda _name: True)
    monkeypatch.setattr(
        governance,
        "validate_magic_star_v02",
        lambda *_args, **_kwargs: {
            "valid": True,
            "production_ready": True,
            "star_commitment": "a" * 64,
            "expires_at_ms": 9_999_999_999_999,
        },
    )
    return governance._mint_magic_star_authorization(
        star=object(),
        trust={},
        plan=plan,
        trusted_now_ms=lambda: 1,
    )


def _armed_machine(
    monkeypatch,
    tmp_path,
    *,
    authorization_provider,
    dispatcher,
):
    module = _module()
    monkeypatch.setenv("LIVE", "1")
    return module.QueenEternalMachine(
        initial_vault=100.0,
        dry_run=False,
        load_state=False,
        state_file=str(tmp_path / "state.json"),
        cost_basis_file=str(tmp_path / "cost-basis.json"),
        authorization_provider=authorization_provider,
        final_order_dispatcher=dispatcher,
    )


def test_import_and_default_constructor_are_offline_and_inert(monkeypatch, tmp_path):
    monkeypatch.setenv("LIVE", "1")
    before_stdout = sys.stdout
    original_import = builtins.__import__

    def guarded_import(name, *args, **kwargs):
        if name.startswith(FORBIDDEN_PROVIDER_IMPORTS):
            raise AssertionError(f"provider import attempted: {name}")
        return original_import(name, *args, **kwargs)

    def forbidden_socket(*_args, **_kwargs):
        raise AssertionError("network socket attempted")

    monkeypatch.setattr(builtins, "__import__", guarded_import)
    monkeypatch.setattr(socket, "socket", forbidden_socket)
    sys.modules.pop(MODULE_NAME, None)

    module = importlib.import_module(MODULE_NAME)
    machine = module.QueenEternalMachine(
        state_file=str(tmp_path / "missing-state.json"),
        cost_basis_file=str(tmp_path / "missing-cost-basis.json"),
        load_state=False,
    )

    assert sys.stdout is before_stdout
    assert machine.dry_run is True
    assert machine.live_trading is False
    assert machine.economic_boundary_status() == {
        "mode": "hold",
        "dry_run": True,
        "live_requested": True,
        "authorization_provider_injected": False,
        "final_order_dispatcher_injected": False,
        "reason": "economic_effects_disabled",
    }
    assert machine._fetch_live_balances() == {}
    assert machine.fetch_market_data() == {}
    assert machine._get_exchange_client("binance") is None


def test_live_env_and_forged_boolean_authority_cannot_dispatch(monkeypatch, tmp_path):
    dispatched = []
    machine = _armed_machine(
        monkeypatch,
        tmp_path,
        authorization_provider=lambda _plan: True,
        dispatcher=lambda plan: dispatched.append(plan) or {},
    )

    receipt = machine._place_market_order(
        "binance", "ETH", "SELL", quantity=1.25
    )

    assert receipt["status"] == "not_submitted"
    assert receipt["reason"] == (
        "external_production_magic_star_authority_service_unavailable"
    )
    assert dispatched == []


def test_local_authorization_never_reaches_eternal_dispatcher(monkeypatch, tmp_path):
    module = _module()
    expected = module.ForceTradePlan(
        provider="binance",
        symbol="ETHUSDT",
        side="SELL",
        quantity="1.25",
    )
    authorization = _mint_authorization(monkeypatch, expected)
    dispatched = []
    machine = _armed_machine(
        monkeypatch,
        tmp_path,
        authorization_provider=lambda _plan: authorization,
        dispatcher=lambda plan: dispatched.append(plan) or {"error": "indeterminate"},
    )

    first = machine._place_market_order(
        "binance", "ETH", "SELL", quantity=1.25
    )
    machine._pending_orders.clear()
    replay = machine._place_market_order(
        "binance", "ETH", "SELL", quantity=1.25
    )

    assert first["status"] == "not_submitted"
    assert replay["status"] == "not_submitted"
    assert first["reason"] == replay["reason"] == (
        "external_production_magic_star_authority_service_unavailable"
    )
    assert dispatched == []


def test_exact_plan_mismatch_does_not_reach_dispatcher(monkeypatch, tmp_path):
    module = _module()
    eth_plan = module.ForceTradePlan(
        provider="binance",
        symbol="ETHUSDT",
        side="SELL",
        quantity="1.25",
    )
    authorization = _mint_authorization(monkeypatch, eth_plan)
    dispatched = []
    machine = _armed_machine(
        monkeypatch,
        tmp_path,
        authorization_provider=lambda _plan: authorization,
        dispatcher=lambda plan: dispatched.append(plan) or {},
    )

    receipt = machine._place_market_order(
        "binance", "BTC", "SELL", quantity=1.25
    )

    assert receipt["status"] == "not_submitted"
    assert receipt["reason"] == "force_trade_authorization_plan_mismatch"
    assert dispatched == []


def test_unavailable_external_authority_never_calls_handler(monkeypatch, tmp_path):
    module = _module()
    plan = module.ForceTradePlan(
        provider="binance",
        symbol="ETHUSDT",
        side="SELL",
        quantity="1.25",
    )
    authorization = _mint_authorization(monkeypatch, plan)
    handler_calls = []

    def failing_dispatcher(observed_plan):
        handler_calls.append(observed_plan)
        raise RuntimeError("offline simulated boundary failure")

    machine = _armed_machine(
        monkeypatch,
        tmp_path,
        authorization_provider=lambda _plan: authorization,
        dispatcher=failing_dispatcher,
    )

    first = machine._place_market_order(
        "binance", "ETH", "SELL", quantity=1.25
    )
    machine._pending_orders.clear()
    machine._final_order_dispatcher = lambda observed: handler_calls.append(observed) or {}
    retry = machine._place_market_order(
        "binance", "ETH", "SELL", quantity=1.25
    )

    assert first["status"] == "not_submitted"
    assert first["submitted"] is False
    assert first["reason"] == (
        "external_production_magic_star_authority_service_unavailable"
    )
    assert retry["status"] == "not_submitted"
    assert retry["reason"] == (
        "external_production_magic_star_authority_service_unavailable"
    )
    assert handler_calls == []


def test_concurrent_local_authority_attempts_never_dispatch(monkeypatch, tmp_path):
    module = _module()
    workers = 16
    plan = module.ForceTradePlan(
        provider="binance",
        symbol="ETHUSDT",
        side="SELL",
        quantity="1.25",
    )
    authorization = _mint_authorization(monkeypatch, plan)
    authorization_barrier = threading.Barrier(workers)
    dispatch_lock = threading.Lock()
    dispatch_count = 0

    def authorization_provider(_plan):
        authorization_barrier.wait(timeout=5)
        return authorization

    def dispatcher(_plan):
        nonlocal dispatch_count
        with dispatch_lock:
            dispatch_count += 1
        return {"error": "indeterminate"}

    machine = _armed_machine(
        monkeypatch,
        tmp_path,
        authorization_provider=authorization_provider,
        dispatcher=dispatcher,
    )

    with ThreadPoolExecutor(max_workers=workers) as pool:
        receipts = list(
            pool.map(
                lambda _index: machine._place_market_order(
                    "binance", "ETH", "SELL", quantity=1.25
                ),
                range(workers),
            )
        )

    assert dispatch_count == 0
    assert all(r.get("status") == "not_submitted" for r in receipts)
    assert all(
        r.get("reason")
        == "external_production_magic_star_authority_service_unavailable"
        for r in receipts
    )


def test_cli_default_is_offline_and_live_request_holds(monkeypatch, tmp_path, capsys):
    module = _module()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("LIVE", "1")
    monkeypatch.setattr(
        socket,
        "socket",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("network socket attempted")
        ),
    )

    def run_without_event_loop(coroutine):
        """Drive these preflight-only coroutines without asyncio's socketpair."""

        with pytest.raises(StopIteration) as stopped:
            coroutine.send(None)
        return stopped.value.value

    monkeypatch.setattr(module.asyncio, "run", run_without_event_loop)

    assert module.main([]) == 0
    assert module.main(["--live"]) == 2
    output = capsys.readouterr().out
    assert "Offline dry-run status" in output
    assert "HOLD: live execution requires LIVE=1" in output


def test_source_has_no_raw_provider_fallback_or_direct_order_sink():
    source = TARGET.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(TARGET))

    imported_modules = {
        node.module or ""
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }
    direct_sink_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr
        in {"place_market_order", "place_order", "create_order", "submit_order"}
    ]

    assert not any(
        module.startswith(FORBIDDEN_PROVIDER_IMPORTS)
        for module in imported_modules
    )
    assert direct_sink_calls == []
    assert 'os.getenv("LIVE", "0")' in source
    assert "dry_run: bool = True" in source
