import importlib.util
import sys
from pathlib import Path

from aureon.core.aureon_runtime_safety import (
    apply_live_runtime_environment,
    real_orders_allowed,
    runtime_mode_snapshot,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
IGNITION_PATH = REPO_ROOT / "scripts" / "aureon_ignition.py"


def load_ignition_module():
    spec = importlib.util.spec_from_file_location("aureon_ignition_test", IGNITION_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def set_fake_exchange_env(monkeypatch):
    monkeypatch.setenv("ENABLE_KRAKEN", "true")
    monkeypatch.setenv("ENABLE_BINANCE", "true")
    monkeypatch.setenv("ENABLE_ALPACA", "true")
    monkeypatch.setenv("ENABLE_CAPITAL", "true")
    monkeypatch.setenv("KRAKEN_API_KEY", "test-kraken-key")
    monkeypatch.setenv("KRAKEN_API_SECRET", "test-kraken-secret")
    monkeypatch.setenv("BINANCE_API_KEY", "test-binance-key")
    monkeypatch.setenv("BINANCE_API_SECRET", "test-binance-secret")
    monkeypatch.setenv("ALPACA_API_KEY", "test-alpaca-key")
    monkeypatch.setenv("ALPACA_SECRET_KEY", "test-alpaca-secret")
    monkeypatch.setenv("CAPITAL_API_KEY", "test-capital-key")
    monkeypatch.setenv("CAPITAL_IDENTIFIER", "test@example.com")
    monkeypatch.setenv("CAPITAL_PASSWORD", "test-capital-password")


def test_live_runtime_profile_enables_single_boot_live_flags(monkeypatch):
    for key in runtime_mode_snapshot().keys():
        monkeypatch.delenv(key, raising=False)

    apply_live_runtime_environment()

    assert real_orders_allowed() is True
    assert runtime_mode_snapshot()["AUREON_AUDIT_MODE"] == "0"
    assert runtime_mode_snapshot()["AUREON_LIVE_TRADING"] == "1"
    assert runtime_mode_snapshot()["AUREON_DISABLE_REAL_ORDERS"] == "0"
    assert runtime_mode_snapshot()["DRY_RUN"] == "0"
    assert runtime_mode_snapshot()["LIVE"] == "1"
    assert runtime_mode_snapshot()["AUREON_LLM_LIVE_CAPABILITIES"] == "1"
    assert runtime_mode_snapshot()["AUREON_COGNITIVE_LIVE_MODE"] == "1"
    assert runtime_mode_snapshot()["AUREON_LLM_ORDER_AUTHORITY"] == "0"
    assert runtime_mode_snapshot()["AUREON_LLM_ORDER_INTENT_AUTHORITY"] == "0"
    assert runtime_mode_snapshot()["AUREON_ORDER_AUTHORITY_MODE"] == "intent_only_runtime_gated"


def test_ignition_live_audit_is_ready_without_booting(monkeypatch):
    set_fake_exchange_env(monkeypatch)
    ignition = load_ignition_module()

    ignition.configure_ignition_runtime(live=True)
    report = ignition.build_ignition_audit(
        live=True,
        no_trade=False,
        env_report={"loaded": False, "loaded_paths": [], "candidate_paths": [], "errors": []},
    )

    assert report["ready"] is True
    assert report["mode"] == "LIVE"
    assert report["real_orders_allowed"] is True
    assert report["kraken_env"]["KRAKEN_API_KEY"]["set"] is True
    assert report["kraken_env"]["KRAKEN_API_SECRET"]["set"] is True
    for exchange in ("kraken", "binance", "alpaca", "capital"):
        assert all(item["set"] for item in report["credential_groups"][exchange].values())
    assert report["goal_capability_map"]["directive_version"] == "goal-capability-v1"
    assert report["goal_capability_map"]["tool_registry"]["count"] >= 5
    assert report["accounting"]["manual_filing_required"] is True
    assert report["accounting"]["accounting_system_registry"]["module_count"] >= 25
    assert report["accounting"]["accounting_evidence_authoring"]["summary"]["draft_count"] >= 1
    assert report["accounting"]["uk_accounting_requirements_brain"]["summary"]["question_count"] >= 8
    assert any(check["name"] == "accounting_context_status" for check in report["checks"])
    assert any(check["name"] == "accounting_system_registry" for check in report["checks"])
    assert any(check["name"] == "accounting_uk_requirements_brain" for check in report["checks"])
    assert any(check["name"] == "accounting_evidence_authoring" for check in report["checks"])


def test_ignition_live_audit_supports_runtime_gated_order_intent_mode(monkeypatch):
    set_fake_exchange_env(monkeypatch)
    ignition = load_ignition_module()

    ignition.configure_ignition_runtime(live=True)
    monkeypatch.setenv("AUREON_LLM_ORDER_INTENT_AUTHORITY", "1")
    monkeypatch.setenv("AUREON_COGNITIVE_ORDER_INTENT_AUTHORITY", "1")
    monkeypatch.setenv("AUREON_ORDER_AUTHORITY_MODE", "intent_only_runtime_gated")
    monkeypatch.setenv("AUREON_ORDER_INTENT_PUBLISH", "1")
    report = ignition.build_ignition_audit(
        live=True,
        no_trade=False,
        env_report={"loaded": False, "loaded_paths": [], "candidate_paths": [], "errors": []},
    )

    checks = {check["name"]: check for check in report["checks"]}
    assert report["ready"] is True
    assert checks["llm_no_direct_order_authority"]["ok"] is True
    assert checks["cognitive_no_direct_order_authority"]["ok"] is True
    assert checks["cognitive_order_intent_authority"]["ok"] is True


def test_ignition_audit_checks_heavy_modules_without_import_side_effects(monkeypatch):
    set_fake_exchange_env(monkeypatch)
    ignition = load_ignition_module()
    heavy_modules = [
        "aureon.trading.micro_profit_labyrinth",
        "aureon.core.mycelium_whale_sonar",
        "aureon.wisdom.aureon_enigma_integration",
    ]
    for module_name in heavy_modules:
        sys.modules.pop(module_name, None)

    ignition.configure_ignition_runtime(live=True)
    report = ignition.build_ignition_audit(
        live=True,
        no_trade=False,
        env_report={"loaded": False, "loaded_paths": [], "candidate_paths": [], "errors": []},
    )

    checks = {check["name"]: check for check in report["checks"]}
    assert checks["import:micro_profit_labyrinth"]["ok"] is True
    for module_name in heavy_modules:
        assert module_name not in sys.modules


def test_ignition_live_audit_fails_closed_without_kraken_env(monkeypatch):
    monkeypatch.setenv("ENABLE_KRAKEN", "true")
    monkeypatch.delenv("KRAKEN_API_KEY", raising=False)
    monkeypatch.delenv("KRAKEN_API_SECRET", raising=False)
    ignition = load_ignition_module()

    ignition.configure_ignition_runtime(live=True)
    report = ignition.build_ignition_audit(
        live=True,
        no_trade=False,
        env_report={"loaded": False, "loaded_paths": [], "candidate_paths": [], "errors": []},
    )

    checks = {check["name"]: check for check in report["checks"]}
    assert report["ready"] is False
    assert checks["kraken_credentials_present"]["ok"] is False
