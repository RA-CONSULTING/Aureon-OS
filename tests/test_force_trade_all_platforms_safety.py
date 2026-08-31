from __future__ import annotations

import builtins
import importlib
import os
import sys
from pathlib import Path
from types import SimpleNamespace

from aureon.queen import queen_force_trade_governance as governance

MODULE_NAME = "aureon.trading.force_trade_all_platforms"
SOURCE = Path(__file__).resolve().parents[1] / "aureon" / "trading" / "force_trade_all_platforms.py"


def _module():
    return importlib.import_module(MODULE_NAME)


def _mint_simulated_production_authorization(monkeypatch, plan):
    monkeypatch.setattr(
        governance,
        "validate_magic_star_v02",
        lambda *_args, **_kwargs: {
            "valid": True,
            "production_ready": True,
            "star_commitment": "b" * 64,
            "expires_at_ms": 2**62,
        },
    )
    return governance._mint_magic_star_authorization(
        star=object(),
        trust={},
        plan=plan,
        trusted_now_ms=lambda: 1_000,
    )


def test_import_is_silent_offline_and_does_not_change_live_flags(
    monkeypatch, tmp_path, capsys
):
    sys.modules.pop(MODULE_NAME, None)
    before_env = {
        key: os.environ.get(key)
        for key in (
            "LIVE",
            "KRAKEN_DRY_RUN",
            "BINANCE_DRY_RUN",
            "ALPACA_DRY_RUN",
            "CAPITAL_DEMO",
        )
    }
    before_stdout = sys.stdout
    real_import = builtins.__import__

    def guarded_import(name, *args, **kwargs):
        if name.startswith("aureon.exchanges"):
            raise AssertionError(f"provider import attempted during module import: {name}")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded_import)
    monkeypatch.chdir(tmp_path)
    imported = importlib.import_module(MODULE_NAME)

    assert imported.CANONICAL_FORCE_TRADE_PLANS
    assert {key: os.environ.get(key) for key in before_env} == before_env
    assert sys.stdout is before_stdout
    assert capsys.readouterr().out == ""
    assert not (tmp_path / "force_trade_results.json").exists()


def test_default_preflight_holds_every_plan_without_provider_construction(monkeypatch):
    module = _module()
    monkeypatch.setattr(governance, "_module_available", lambda _name: True)

    report = module.preflight_force_trade_all_platforms()

    assert report["status"] == "HOLD"
    assert report["mode"] == "status_only_no_provider_construction"
    assert report["plan_count"] == 4
    assert report["ready_count"] == 0
    assert report["hold_count"] == 4
    assert all(item["status"] == "HOLD" for item in report["plans"])


def test_missing_or_forged_authority_never_calls_final_dispatcher(monkeypatch):
    module = _module()
    monkeypatch.setattr(governance, "_module_available", lambda _name: True)
    plan = module.CANONICAL_FORCE_TRADE_PLANS[0]
    calls = []

    def dispatcher(candidate):
        calls.append(candidate)
        raise AssertionError("unauthorized dispatcher call")

    missing = module.dispatch_authorized_force_trade(
        plan=plan,
        authorization=None,
        final_dispatcher=dispatcher,
    )
    forged = module.dispatch_authorized_force_trade(
        plan=plan,
        authorization=object(),  # type: ignore[arg-type]
        final_dispatcher=dispatcher,
    )

    assert missing["status"] == "HOLD"
    assert forged["status"] == "HOLD"
    assert calls == []


def test_local_authority_never_reaches_dispatcher(monkeypatch):
    module = _module()
    monkeypatch.setattr(governance, "_module_available", lambda _name: True)
    authorized_plan, substituted_plan = module.CANONICAL_FORCE_TRADE_PLANS[:2]
    authorization = _mint_simulated_production_authorization(
        monkeypatch, authorized_plan
    )
    calls = []

    def dispatcher(plan):
        calls.append(plan)
        return {
            "status": "EXECUTED",
            "plan_sha256": plan.commitment,
            "provider_receipt_id": "synthetic-offline-receipt",
        }

    substituted = module.dispatch_authorized_force_trade(
        plan=substituted_plan,
        authorization=authorization,
        final_dispatcher=dispatcher,
    )
    exact = module.dispatch_authorized_force_trade(
        plan=authorized_plan,
        authorization=authorization,
        final_dispatcher=dispatcher,
    )

    assert substituted["status"] == "HOLD"
    assert "plan_mismatch" in substituted["reason"]
    assert exact["status"] == "HOLD"
    assert exact["reason"].endswith(
        "external_production_magic_star_authority_service_unavailable"
    )
    assert calls == []


def test_fabricated_dispatcher_receipt_cannot_self_certify_execution(monkeypatch):
    module = _module()
    plan = module.CANONICAL_FORCE_TRADE_PLANS[0]
    monkeypatch.setattr(
        module,
        "claim_queen_force_trade_authority",
        lambda **_kwargs: SimpleNamespace(allowed=True),
    )

    result = module.dispatch_authorized_force_trade(
        plan=plan,
        authorization=object(),  # type: ignore[arg-type]
        final_dispatcher=lambda candidate: {
            "status": "EXECUTED",
            "plan_sha256": candidate.commitment,
            "provider_receipt_id": "synthetic-offline-receipt",
        },
    )

    assert result["status"] == "PENDING_RECONCILIATION"
    assert result["reason"] == "independent_provider_readback_required"
    assert result["dispatcher_acknowledgement_untrusted"] is True
    assert "provider_receipt_id" not in result


def test_dispatcher_failure_consumes_one_use_authorization(monkeypatch):
    module = _module()
    plan = module.CANONICAL_FORCE_TRADE_PLANS[0]
    authorization = object()
    monkeypatch.setattr(
        module,
        "claim_queen_force_trade_authority",
        lambda **_kwargs: SimpleNamespace(allowed=True),
    )
    calls = []

    def failing_dispatcher(candidate):
        calls.append(candidate)
        raise RuntimeError("synthetic failure after potential provider effect")

    first = module.dispatch_authorized_force_trade(
        plan=plan,
        authorization=authorization,
        final_dispatcher=failing_dispatcher,
    )
    assert first["status"] == "INDETERMINATE"
    assert first["authorization_consumed"] is True
    assert calls == [plan]


def test_missing_dispatcher_does_not_consume_authorization(monkeypatch):
    module = _module()
    monkeypatch.setattr(governance, "_module_available", lambda _name: True)
    plan = module.CANONICAL_FORCE_TRADE_PLANS[0]
    authorization = _mint_simulated_production_authorization(monkeypatch, plan)

    held = module.dispatch_authorized_force_trade(
        plan=plan,
        authorization=authorization,
        final_dispatcher=None,
    )
    still_held = module.dispatch_authorized_force_trade(
        plan=plan,
        authorization=authorization,
        final_dispatcher=lambda candidate: {
            "status": "EXECUTED",
            "plan_sha256": candidate.commitment,
            "provider_receipt_id": "synthetic-offline-receipt",
        },
    )

    assert held["status"] == "HOLD"
    assert held["reason"] == "production_force_trade_dispatcher_unavailable"
    assert still_held["status"] == "HOLD"
    assert "external_production_magic_star_authority_service_unavailable" in still_held["reason"]


def test_cli_path_is_status_only_and_returns_hold(monkeypatch, capsys):
    module = _module()
    monkeypatch.setattr(governance, "_module_available", lambda _name: True)

    exit_code = module.main([])
    payload = capsys.readouterr().out

    assert exit_code == 2
    assert '"status": "HOLD"' in payload
    assert "status_only_no_provider_construction" in payload


def test_source_contains_no_live_flag_provider_import_or_raw_order_sink():
    source = SOURCE.read_text(encoding="utf-8")

    assert "os.environ" not in source
    assert "load_dotenv" not in source
    assert "from aureon.exchanges" not in source
    assert ".place_market_order(" not in source
    assert ".place_order(" not in source
    assert "force_trade_results.json" not in source
    assert 'if __name__ == "__main__":' in source
