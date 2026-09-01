from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
AUDITOR_PATH = ROOT / "scripts" / "validation" / "audit_economic_mutation_boundaries.py"
SPEC = importlib.util.spec_from_file_location("economic_mutation_census", AUDITOR_PATH)
assert SPEC is not None and SPEC.loader is not None
AUDITOR = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = AUDITOR
SPEC.loader.exec_module(AUDITOR)


@pytest.fixture(scope="module")
def census() -> dict[str, Any]:
    return AUDITOR.audit()


def test_inventory_is_exact_but_truthfully_not_certified(census: dict[str, Any]) -> None:
    assert census["inventory_aligned"] is True
    assert census["certified_no_bypass"] is False
    assert census["detected_count"] == 1607
    assert census["classified_count"] == 1607
    assert census["blocker_count"] == 1236
    assert census["parse_errors"] == []
    assert census["unallowlisted"] == []
    assert census["stale_allowlist_entries"] == []
    assert census["counts_by_classification"] == {
        "dry-run-test-demo-only": 122,
        "economic-boundary-last-mile": 4,
        "live-capable-unguarded-blocker": 1236,
        "provider-client-raw-transport-guard": 245,
        "unreachable-quarantined-launcher": 0,
    }
    assert census["counts_by_provider"] == {
        "alpaca": 235,
        "binance": 371,
        "capital": 207,
        "kraken": 445,
        "multi-provider": 343,
        "oanda": 6,
    }


def test_every_entry_is_explicitly_owned_and_line_independent(
    census: dict[str, Any],
) -> None:
    assert all(item["fingerprint"].startswith("econop:") for item in census["findings"])
    assert all(item["rationale"].strip() for item in census["findings"])
    assert all(item["owner"].strip() for item in census["findings"])
    allowlist = AUDITOR.load_allowlist()
    assert len(allowlist) == 1607
    assert all("line" not in entry for entry in allowlist.values())


def test_imported_snapshots_are_live_capable_blockers(
    census: dict[str, Any],
) -> None:
    imported = [
        finding
        for finding in census["findings"]
        if finding["file"].startswith("imports/")
    ]
    assert len(imported) == 602
    assert all(
        finding["classification"] == "live-capable-unguarded-blocker"
        for finding in imported
    )


def test_guarded_last_mile_and_provider_raw_transport_guards_are_exact(
    census: dict[str, Any],
) -> None:
    guarded = [
        finding
        for finding in census["findings"]
        if finding["classification"] == "economic-boundary-last-mile"
    ]
    assert len(guarded) == 4
    assert {finding["file"] for finding in guarded} == {
        "aureon/strategies/s5_live_execution.py",
        "aureon/trading/bounded_binance_roundtrip.py",
    }
    assert all(finding["transport"] == "economic-boundary-dispatch" for finding in guarded)

    provider_guards = [
        finding
        for finding in census["findings"]
        if finding["classification"] == "provider-client-raw-transport-guard"
    ]
    assert len(provider_guards) == 245
    assert {finding["file"] for finding in provider_guards} == {
        "Kings_Accounting_Suite/aureon_systems/queen_quantum_frog.py",
        "Kings_Accounting_Suite/core/hnc_hmrc_api.py",
        "Kings_Accounting_Suite/aureon_systems/queen_profit_dashboard.py",
        "aureon/exchanges/alpaca_client.py",
        "aureon/exchanges/alpaca_options_client.py",
        "aureon/exchanges/binance_client.py",
        "aureon/exchanges/capital_client.py",
        "aureon/exchanges/kraken_client.py",
        "aureon/exchanges/kraken_margin_penny_trader.py",
        "aureon/bots/gaia_aggressive_reclaimerfix.py",
        "aureon/bots/orca_complete_kill_cycle.py",
        "aureon/queen/queen_quantum_frog.py",
        "aureon/queen/unity_exchange_brain.py",
        "aureon/trading/bounded_capital_live_trade.py",
        "aureon/trading/aureon_the_play.py",
        "aureon/trading/aureon_unified_ecosystem.py",
        "aureon/trading/unified_exchange_client.py",
        "aureon/exchanges/unified_market_trader.py",
    }
    assert {finding["provider"] for finding in provider_guards} == {
        "alpaca",
        "binance",
        "capital",
        "kraken",
        "multi-provider",
    }
    hmrc_guards = [
        finding
        for finding in provider_guards
        if finding["file"] == "Kings_Accounting_Suite/core/hnc_hmrc_api.py"
    ]
    assert len(hmrc_guards) == 3
    hmrc_source = (
        ROOT / "Kings_Accounting_Suite" / "core" / "hnc_hmrc_api.py"
    ).read_text(encoding="utf-8")
    for method, next_method in (
        ("_post", "_put"),
        ("_put", "_delete"),
        ("_delete", "_handle_response"),
    ):
        start = hmrc_source.index(f"    def {method}(")
        end = hmrc_source.index(f"    def {next_method}(", start)
        method_source = hmrc_source[start:end]
        assert "canonical_hmrc_mutation_registry_required" in method_source
        assert "self._mutation_registry.execute(" in method_source
        assert "transport=lambda: self._handle_response(" in method_source
    kraken_guards = [
        finding
        for finding in provider_guards
        if finding["file"] == "aureon/exchanges/kraken_client.py"
    ]
    assert len(kraken_guards) == 20
    assert all(
        finding["operation"]
        in {
            "dynamic-provider-mutation",
            "submit-order",
            "cancel-order",
            "sdk-cancel-order",
            "cancel-all-orders",
            "edit-order",
            "sdk-submit-order",
        }
        for finding in kraken_guards
    )

    client_source = (
        ROOT / "aureon" / "exchanges" / "binance_client.py"
    ).read_text(encoding="utf-8")
    signed_source = client_source[
        client_source.index("    def _signed_request("):
        client_source.index("    def ping(")
    ]
    assert (
        signed_source.index("_claim_economic_transport_context(")
        < signed_source.index("self._get_server_timestamp()")
        < signed_source.index("return self._do_request(")
    )
    assert "_economic_dispatch=dispatch" in signed_source

    raw_source = client_source[
        client_source.index("    def _do_request("):
        client_source.index("    def _signed_request(")
    ]
    assert (
        raw_source.index("self._consume_economic_dispatch(")
        < raw_source.index("self.session.request(")
    )

    kraken_source = (
        ROOT / "aureon" / "exchanges" / "kraken_client.py"
    ).read_text(encoding="utf-8")
    private_source = kraken_source[
        kraken_source.index("    def _private("):
        kraken_source.index("    def _public_get(")
    ]
    assert (
        private_source.index("_claim_economic_transport_context(")
        < private_source.index("wire_data[\"nonce\"]")
        < private_source.index("self._private_http_post(")
    )
    assert "_economic_dispatch=dispatch" in private_source

    raw_kraken_source = kraken_source[
        kraken_source.index("    def _private_http_post("):
        kraken_source.index("    def _private(")
    ]
    assert (
        raw_kraken_source.index("_is_kraken_economic_mutation_path(")
        < raw_kraken_source.index("self._consume_economic_dispatch(")
        < raw_kraken_source.index("self.session.post(")
    )
    assert "path not in _KRAKEN_CANONICAL_MUTATION_PATHS" in (
        raw_kraken_source
    )
    assert 'self._private("/0/private/Balance", {})' in kraken_source

    unified_guards = [
        finding
        for finding in provider_guards
        if finding["file"] == "aureon/trading/unified_exchange_client.py"
    ]
    assert len(unified_guards) == 44
    unified_source = (
        ROOT / "aureon" / "trading" / "unified_exchange_client.py"
    ).read_text(encoding="utf-8")
    unified_class = unified_source[unified_source.index("class UnifiedExchangeClient:"):]
    dispatch = unified_class[
        unified_class.index("    def _execute_optional_legacy_unity("):
        unified_class.index("    def normalize(")
    ]
    assert "canonical_legacy_unity_composition_required" in dispatch
    assert "return transport()" not in dispatch
    for method, next_method in (
        ("place_order_with_tp_sl", "get_open_orders"),
        ("place_margin_order", "close_margin_position"),
        ("close_margin_position", None),
    ):
        start = unified_class.index(f"    def {method}(")
        end = (
            unified_class.index(f"    def {next_method}(", start)
            if next_method is not None
            else len(unified_class)
        )
        method_source = unified_class[start:end]
        assert "_execute_optional_legacy_unity(" in method_source
        assert "unity_invocation: LegacyEconomicInvocation | None" in method_source
        assert "unity_plan: LegacyUnityIntentPlan | None" in method_source
        assert "unity_invocation," in method_source
        assert "plan=unity_plan" in method_source

    governed_class = unified_source[
        unified_source.index("class GovernedMultiExchangeClient("):
        unified_source.index("class UnifiedExchangeClient:")
    ]
    governed_constructor = governed_class[
        governed_class.index("    def __init__("):
        governed_class.index("    @staticmethod")
    ]
    assert "trusted_unified_ecosystem_plan_supplier_required" in governed_constructor
    assert "unified_ecosystem_plan_supplier_not_allowlisted" in governed_constructor
    assert "canonical_unified_exchange_unity_composition_required" in governed_constructor
    governed_dispatch = governed_class[
        governed_class.index("    def _execute_governed("):
        governed_class.index("    @staticmethod", governed_class.index("    def _execute_governed("))
    ]
    assert (
        governed_dispatch.index("supply_unity_plan(request)")
        < governed_dispatch.index("self._plan_matches(")
        < governed_dispatch.index("if plan.plan_digest in self._consumed_plan_digests")
        < governed_dispatch.index("self._consumed_plan_digests.add(plan.plan_digest)")
        < governed_dispatch.index("result = dispatch(plan)")
    )
    assert governed_class.count("return self._execute_governed(") == 10
    assert governed_class.count("unity_plan=exact_plan") == 10

    ecosystem_guards = [
        finding
        for finding in provider_guards
        if finding["file"] == "aureon/trading/aureon_unified_ecosystem.py"
    ]
    assert len(ecosystem_guards) == 24
    ecosystem_source = (
        ROOT / "aureon" / "trading" / "aureon_unified_ecosystem.py"
    ).read_text(encoding="utf-8")
    ecosystem_constructor = ecosystem_source[
        ecosystem_source.index("class AureonKrakenEcosystem:"):
        ecosystem_source.index("        # Positions must exist", ecosystem_source.index("class AureonKrakenEcosystem:"))
    ]
    assert "unity_composition_plan_supplier_and_allowlist_required_together" in ecosystem_constructor
    assert "self.client = GovernedMultiExchangeClient(" in ecosystem_constructor
    assert '"canonical_unified_exchange_unity_composition_required"' in ecosystem_constructor

    ecosystem_test_findings = [
        finding
        for finding in census["findings"]
        if finding["file"] == "tests/test_unified_ecosystem_governed_client.py"
    ]
    assert len(ecosystem_test_findings) == 7
    assert all(
        finding["classification"] == "dry-run-test-demo-only"
        for finding in ecosystem_test_findings
    )

    queen_guard_counts = {
        path: len(
            [
                finding
                for finding in provider_guards
                if finding["file"] == path
            ]
        )
        for path in (
            "aureon/queen/queen_quantum_frog.py",
            "Kings_Accounting_Suite/aureon_systems/queen_quantum_frog.py",
        )
    }
    assert queen_guard_counts == {
        "aureon/queen/queen_quantum_frog.py": 26,
        "Kings_Accounting_Suite/aureon_systems/queen_quantum_frog.py": 26,
    }
    queen_brain_guards = [
        finding
        for finding in provider_guards
        if finding["file"] == "aureon/queen/unity_exchange_brain.py"
    ]
    assert len(queen_brain_guards) == 5
    queen_brain_source = (
        ROOT / "aureon" / "queen" / "unity_exchange_brain.py"
    ).read_text(encoding="utf-8")
    queen_market = queen_brain_source[
        queen_brain_source.index("    def place_market_order("):
        queen_brain_source.index("    def _blocked_mutation(")
    ]
    assert (
        queen_market.index("if self._governed_client is None:")
        < queen_market.index("self._governed_client.place_market_order(")
    )
    assert "caller_supplied_unity_authority_forbidden" in queen_market
    assert "provider_specific_mutation_arguments_require_exact_unity_route" in queen_market
    assert "self._governed_client.place_margin_order(" in queen_market
    assert "self._governed_client.close_margin_position(" in queen_market
    assert "self._governed_client.place_take_profit_order(" in queen_market
    assert "self._governed_client.place_trailing_stop_order(" in queen_market
    assert queen_market.count("return self._observe(") >= 8
    queen_getattr = queen_brain_source[
        queen_brain_source.index("    def __getattr__("):
        queen_brain_source.index("\ndef build_queen_exchange_brains(")
    ]
    assert "_BLOCKED_MUTATION_NAMES" in queen_getattr
    assert "_BLOCKED_MUTATION_PREFIXES" in queen_getattr

    for relative in queen_guard_counts:
        source = (ROOT / relative).read_text(encoding="utf-8")
        constructor = source[
            source.index("class OrcaKillCycle:"):
            source.index("        self.exchange = exchange", source.index("class OrcaKillCycle:"))
        ]
        assert "build_queen_exchange_brains" in constructor
        assert "fallback_read_clients" in constructor
        assert "self.client = self.clients[exchange]" in constructor

    queen_test_findings = [
        finding
        for finding in census["findings"]
        if finding["file"] == "tests/test_queen_unity_exchange_brain.py"
    ]
    assert len(queen_test_findings) == 22
    assert all(
        finding["classification"] == "dry-run-test-demo-only"
        for finding in queen_test_findings
    )

    orca_guards = [
        finding
        for finding in provider_guards
        if finding["file"] == "aureon/bots/orca_complete_kill_cycle.py"
    ]
    assert len(orca_guards) == 16
    assert all(
        finding["canonical_call"].startswith("self._governed_client_for(")
        for finding in orca_guards
    )
    orca_source = (
        ROOT / "aureon" / "bots" / "orca_complete_kill_cycle.py"
    ).read_text(encoding="utf-8")
    orca_constructor = orca_source[
        orca_source.index("class OrcaKillCycle:"):
        orca_source.index("    def audit_event")
    ]
    assert "OrganismEconomicSensationRouter" in orca_constructor
    assert "outcome_observer=self.economic_sensation_router.observe" in orca_constructor
    assert "self.clients = brains" in orca_constructor
    assert orca_source.count("self._governed_client_for(") == 16
    assert "client.place_market_order" not in orca_source
    assert "client.place_margin_order" not in orca_source
    assert "pos.client.close_margin_position" not in orca_source
    assert "pos.client.place_market_order" not in orca_source
    orca_test_findings = [
        finding
        for finding in census["findings"]
        if finding["file"] == "tests/test_orca_unity_sensation.py"
    ]
    assert len(orca_test_findings) == 2
    assert all(
        finding["classification"] == "dry-run-test-demo-only"
        for finding in orca_test_findings
    )
    orca_residual = [
        finding
        for finding in census["blockers"]
        if finding["file"] == "aureon/bots/orca_complete_kill_cycle.py"
    ]
    assert len(orca_residual) == 2
    assert all("urllib.request.Request" in finding["canonical_call"] for finding in orca_residual)

    margin_guards = [
        finding
        for finding in provider_guards
        if finding["file"] == "aureon/exchanges/kraken_margin_penny_trader.py"
    ]
    assert len(margin_guards) == 8
    assert all(
        "place_margin_order" in finding["canonical_call"]
        or "close_margin_position" in finding["canonical_call"]
        or finding["canonical_call"].startswith("self.close_position(")
        for finding in margin_guards
    )
    margin_source = (
        ROOT / "aureon" / "exchanges" / "kraken_margin_penny_trader.py"
    ).read_text(encoding="utf-8")
    margin_constructor = margin_source[
        margin_source.index("class KrakenMarginArmyTrader:"):
        margin_source.index("    def _install_unity_exchange_brain")
    ]
    margin_installer = margin_source[
        margin_source.index("    def _install_unity_exchange_brain"):
        margin_source.index("    def recent_economic_sensations")
    ]
    assert margin_constructor.index("self.hive_state =") < margin_constructor.index(
        "self._install_unity_exchange_brain("
    )
    assert "OrganismEconomicSensationRouter" in margin_installer
    assert "build_queen_exchange_brains" in margin_installer
    assert "outcome_observer=self._economic_sensation_router.observe" in margin_installer
    assert 'self.client = brains["kraken"]' in margin_installer
    margin_test_findings = [
        finding
        for finding in census["findings"]
        if finding["file"] == "tests/test_kraken_margin_unity_sensation.py"
    ]
    assert len(margin_test_findings) == 2
    assert all(
        finding["classification"] == "dry-run-test-demo-only"
        for finding in margin_test_findings
    )
    margin_residual = [
        finding
        for finding in census["blockers"]
        if finding["file"] == "aureon/exchanges/kraken_margin_penny_trader.py"
    ]
    assert len(margin_residual) == 10
    assert all(
        "urllib.request.Request" in finding["canonical_call"]
        for finding in margin_residual
    )

    gaia_guards = [
        finding
        for finding in provider_guards
        if finding["file"] == "aureon/bots/gaia_aggressive_reclaimerfix.py"
    ]
    assert len(gaia_guards) == 11
    assert all(
        finding["canonical_call"].startswith("self._governed_client_for(")
        for finding in gaia_guards
    )
    gaia_source = (
        ROOT / "aureon" / "bots" / "gaia_aggressive_reclaimerfix.py"
    ).read_text(encoding="utf-8")
    gaia_constructor = gaia_source[
        gaia_source.index("class AggressiveReclaimer:"):
        gaia_source.index("    def log(")
    ]
    assert "OrganismEconomicSensationRouter" in gaia_constructor
    assert "build_queen_exchange_brains" in gaia_constructor
    assert "outcome_observer=self._economic_sensation_router.observe" in gaia_constructor
    assert gaia_source.count("self._governed_client_for(") == 11
    assert "self.alpaca.place_order(" not in gaia_source
    assert "self.alpaca.place_market_order(" not in gaia_source
    assert "self.binance.place_market_order(" not in gaia_source
    assert "self.kraken.place_market_order(" not in gaia_source
    gaia_test_findings = [
        finding
        for finding in census["findings"]
        if finding["file"] == "tests/test_gaia_reclaimer_unity_sensation.py"
    ]
    assert len(gaia_test_findings) == 1
    assert gaia_test_findings[0]["classification"] == "dry-run-test-demo-only"
    assert not [
        finding
        for finding in census["blockers"]
        if finding["file"] == "aureon/bots/gaia_aggressive_reclaimerfix.py"
    ]

    unified_market_guards = [
        finding
        for finding in provider_guards
        if finding["file"] == "aureon/exchanges/unified_market_trader.py"
    ]
    assert len(unified_market_guards) == 11
    assert all(
        finding["canonical_call"].startswith("self._governed_client_for(")
        for finding in unified_market_guards
    )
    unified_market_source = (
        ROOT / "aureon" / "exchanges" / "unified_market_trader.py"
    ).read_text(encoding="utf-8")
    unified_market_constructor = unified_market_source[
        unified_market_source.index("class UnifiedMarketTrader:"):
        unified_market_source.index("    def _governor")
    ]
    assert "OrganismEconomicSensationRouter" in unified_market_constructor
    assert "build_queen_exchange_brains" in unified_market_constructor
    assert "outcome_observer=self._economic_sensation_router.observe" in unified_market_constructor
    assert unified_market_source.count("self._governed_client_for(") == 11
    for raw_mutation in (
        "client.place_trailing_stop_order(",
        "client.place_take_profit_order(",
        "client.place_market_order(",
        "client.place_margin_order(",
        "self.alpaca.place_market_order(",
        "self.binance.place_market_order(",
        "self.binance.place_margin_order(",
    ):
        assert raw_mutation not in unified_market_source
    unified_market_test_findings = [
        finding
        for finding in census["findings"]
        if finding["file"] == "tests/test_unified_market_trader_unity_sensation.py"
    ]
    assert len(unified_market_test_findings) == 5
    assert all(
        finding["classification"] == "dry-run-test-demo-only"
        for finding in unified_market_test_findings
    )
    assert not [
        finding
        for finding in census["blockers"]
        if finding["file"] == "aureon/exchanges/unified_market_trader.py"
    ]

    the_play_guards = [
        finding
        for finding in provider_guards
        if finding["file"] == "aureon/trading/aureon_the_play.py"
    ]
    assert len(the_play_guards) == 2
    assert all(
        finding["canonical_call"].startswith("self._governed_client_for(")
        for finding in the_play_guards
    )
    the_play_source = (
        ROOT / "aureon" / "trading" / "aureon_the_play.py"
    ).read_text(encoding="utf-8")
    the_play_constructor = the_play_source[
        the_play_source.index("class AureonThePlayTrader:"):
        the_play_source.index("    def load_existing_positions(")
    ]
    assert "OrganismEconomicSensationRouter" in the_play_constructor
    assert "build_queen_exchange_brains" in the_play_constructor
    assert "outcome_observer=self._economic_sensation_router.observe" in the_play_constructor
    assert 'self.client = brains["binance"]' in the_play_constructor
    assert the_play_source.count('self._governed_client_for("binance").place_market_order(') == 2
    assert "self.client.place_market_order(" not in the_play_source
    assert "self.close_position(" not in the_play_source
    assert the_play_source.count("self._exit_managed_position(") == 6
    assert "if not self._governed_execution_confirmed(res):" in the_play_source
    assert "if not self._governed_execution_confirmed(result):" in the_play_source
    assert not [
        finding
        for finding in census["blockers"]
        if finding["file"] == "aureon/trading/aureon_the_play.py"
    ]

    capital_guards = [
        finding
        for finding in provider_guards
        if finding["file"] == "aureon/exchanges/capital_client.py"
    ]
    assert len(capital_guards) == 6
    capital_source = (
        ROOT / "aureon" / "exchanges" / "capital_client.py"
    ).read_text(encoding="utf-8")
    request_source = capital_source[
        capital_source.index("    def _request("):
        capital_source.index("    def _get_headers(")
    ]
    assert (
        request_source.index("_claim_capital_economic_transport_context(")
        < request_source.index("headers = self._get_headers()")
        < request_source.index("self._capital_http_request(")
    )
    assert "if is_mutation:\n            return resp" in request_source
    raw_capital_source = capital_source[
        capital_source.index("    def _capital_http_request("):
        capital_source.index("    def _request(")
    ]
    assert (
        raw_capital_source.index("self._consume_economic_dispatch(")
        < raw_capital_source.index("requests.request(")
    )
    assert "CAPITAL_LIVE_BASE" in raw_capital_source
    assert "CAPITAL_DEMO_BASE" in raw_capital_source

    alpaca_guards = [
        finding
        for finding in provider_guards
        if finding["file"] == "aureon/exchanges/alpaca_client.py"
    ]
    assert len(alpaca_guards) == 22
    alpaca_source = (
        ROOT / "aureon" / "exchanges" / "alpaca_client.py"
    ).read_text(encoding="utf-8")
    alpaca_request_source = alpaca_source[
        alpaca_source.index("    def _request("):
        alpaca_source.index("    def _normalize_pair_symbol(")
    ]
    assert (
        alpaca_request_source.index("_claim_economic_transport_context(")
        < alpaca_request_source.index("self._register_economic_dispatch(")
        < alpaca_request_source.index("self._alpaca_http_request(")
    )
    assert "attempt_count = 1 if is_mutation" in alpaca_request_source
    raw_alpaca_source = alpaca_source[
        alpaca_source.index("    def _alpaca_http_request("):
        alpaca_source.index("    def _request(")
    ]
    assert (
        raw_alpaca_source.index("self._consume_economic_dispatch(")
        < raw_alpaca_source.index("self.session.request(")
    )
    assert "ALPACA_LIVE_BASE" in raw_alpaca_source
    assert "ALPACA_PAPER_BASE" in raw_alpaca_source

    alpaca_test_findings = [
        finding
        for finding in census["findings"]
        if finding["file"] == "tests/test_alpaca_economic_transport_guard.py"
    ]
    assert len(alpaca_test_findings) == 7
    assert all(
        finding["classification"] == "dry-run-test-demo-only"
        for finding in alpaca_test_findings
    )

    alpaca_options_guards = [
        finding
        for finding in provider_guards
        if finding["file"] == "aureon/exchanges/alpaca_options_client.py"
    ]
    assert len(alpaca_options_guards) == 6
    alpaca_options_source = (
        ROOT / "aureon" / "exchanges" / "alpaca_options_client.py"
    ).read_text(encoding="utf-8")
    options_prepare_source = alpaca_options_source[
        alpaca_options_source.index("    def _prepare_options_mutation("):
        alpaca_options_source.index("    def _discard_options_mutation_dispatch(")
    ]
    assert (
        options_prepare_source.index("_claim_economic_transport_context(")
        < options_prepare_source.index("self._economic_dispatches[dispatch]")
    )
    options_raw_source = alpaca_options_source[
        alpaca_options_source.index("    def _options_mutation_request("):
        alpaca_options_source.index("    # ACCOUNT & CONFIGURATION")
    ]
    assert (
        options_raw_source.index("self._economic_dispatches.pop(")
        < options_raw_source.index("self.session.request(")
    )
    assert "ALPACA_OPTIONS_LIVE_BASE" in options_raw_source
    assert "ALPACA_OPTIONS_PAPER_BASE" in options_raw_source
    assert "self.session.post(" not in alpaca_options_source
    assert "self.session.delete(" not in alpaca_options_source

    alpaca_options_test_findings = [
        finding
        for finding in census["findings"]
        if finding["file"]
        == "tests/test_alpaca_options_economic_transport_guard.py"
    ]
    assert len(alpaca_options_test_findings) == 7
    assert all(
        finding["classification"] == "dry-run-test-demo-only"
        for finding in alpaca_options_test_findings
    )

    kraken_test_findings = [
        finding
        for finding in census["findings"]
        if finding["file"] == "tests/test_kraken_economic_transport_guard.py"
    ]
    assert len(kraken_test_findings) == 4
    assert all(
        finding["classification"] == "dry-run-test-demo-only"
        for finding in kraken_test_findings
    )

    boundary_source = (
        ROOT / "aureon" / "governance" / "economic_boundary.py"
    ).read_text(encoding="utf-8")
    consume_source = boundary_source[
        boundary_source.index("    def consume_and_call("):
        boundary_source.index("\ndef bind_economic_governance_boundary(")
    ]
    assert (
        consume_source.index("_install_economic_transport_context(")
        < consume_source.index("return transport()")
    )
    assert "finally:" in consume_source
    assert "_clear_economic_transport_context(" in consume_source


def test_fail_closed_migration_batches_are_disjoint_and_complete(
    census: dict[str, Any],
) -> None:
    batches = census["migration_batches"]
    assert [batch["batch"] for batch in batches] == [
        "01-quarantine-live-test-clis",
        "02-gate-supabase-provider-functions",
        "03-guard-provider-client-chokepoints",
        "04-migrate-direct-http-bypasses",
        "05-migrate-legacy-sdk-wrapper-callers",
    ]
    assert sum(batch["call_site_count"] for batch in batches) == census["blocker_count"]
    assert all(batch["call_site_count"] > 0 for batch in batches)
    assert all(batch["file_count"] == len(batch["files"]) for batch in batches)


def test_cli_exit_semantics_are_distinct_without_rescanning(
    census: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(AUDITOR, "audit", lambda **_kwargs: census)
    assert AUDITOR.main(["--compact"]) == 1
    capsys.readouterr()
    assert AUDITOR.main(["--report-only", "--compact"]) == 0
    capsys.readouterr()
    drifted = {**census, "inventory_aligned": False}
    monkeypatch.setattr(AUDITOR, "audit", lambda **_kwargs: drifted)
    assert AUDITOR.main(["--report-only", "--compact"]) == 2


def _python_fixture_findings(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    source: str,
    *,
    name: str = "fixture.py",
) -> list[Any]:
    monkeypatch.setattr(AUDITOR, "ROOT", tmp_path)
    path = tmp_path / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    findings, error = AUDITOR._python_findings(path, source)
    assert error is None
    return findings


def _typescript_fixture_findings(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    source: str,
    *,
    name: str = "fixture.ts",
) -> list[Any]:
    monkeypatch.setattr(AUDITOR, "ROOT", tmp_path)
    path = tmp_path / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    findings, error = AUDITOR._ts_findings(path, source)
    assert error is None
    return findings


@pytest.mark.parametrize(
    ("provider", "endpoint"),
    [
        ("binance", "/api/v3/order"),
        ("alpaca", "/v2/orders"),
        ("kraken", "/0/private/AddOrder"),
    ],
)
def test_python_resolves_container_endpoint_into_aiohttp_post(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    provider: str,
    endpoint: str,
) -> None:
    findings = _python_fixture_findings(
        tmp_path,
        monkeypatch,
        f"""
ROUTES = {{"{provider}": {{"order_endpoint": "{endpoint}"}}}}
async def submit(session):
    url = "https://provider.invalid" + ROUTES["{provider}"]["order_endpoint"]
    return await session.post(url, json={{"side": "BUY"}})
""",
    )
    assert [(item.provider, item.operation) for item in findings] == [
        (provider, "submit-order")
    ]


@pytest.mark.parametrize(
    ("message", "provider"),
    [
        ('{"method": "order.place", "params": {"side": "BUY"}}', "binance"),
        ('{"event": "addOrder", "type": "buy"}', "kraken"),
    ],
)
def test_python_detects_authenticated_websocket_order_messages(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    message: str,
    provider: str,
) -> None:
    findings = _python_fixture_findings(
        tmp_path,
        monkeypatch,
        f"""
import json
MESSAGE = {message}
async def submit(websocket):
    await websocket.send(json.dumps(MESSAGE))
""",
    )
    assert len(findings) == 1
    assert findings[0].provider == provider
    assert findings[0].operation == "submit-order"
    assert findings[0].transport == "authenticated-websocket"


@pytest.mark.parametrize(
    ("call", "provider", "operation"),
    [
        ("binance.create_market_order(symbol='BTCUSDT')", "binance", "sdk-submit-order"),
        ("kraken.create_limit_order(pair='XBTUSD')", "kraken", "sdk-submit-order"),
        ("binance.place_margin_order('BTCUSDT', 'BUY', 1)", "binance", "sdk-submit-margin-order"),
        ("kraken.close_margin_position('XBTUSD', 'sell')", "kraken", "sdk-close-margin-position"),
        ("capital.place_working_order('AAPL', 'BUY', 1, 100)", "capital", "sdk-submit-working-order"),
        ("capital.delete_working_order('deal-1')", "capital", "sdk-cancel-working-order"),
        ("capital.update_position_limits('deal-1')", "capital", "sdk-edit-position"),
        ("alpaca.place_stop_order('AAPL', 1, 'sell', 90)", "alpaca", "sdk-submit-stop-order"),
        ("alpaca.place_stop_limit_order('AAPL', 1, 'sell', 90, 89)", "alpaca", "sdk-submit-stop-order"),
        ("alpaca.place_stop_loss_order('AAPL', 'sell', 1, 90)", "alpaca", "sdk-submit-stop-order"),
        ("alpaca.place_take_profit_order('AAPL', 'sell', 1, 110)", "alpaca", "sdk-submit-take-profit-order"),
        ("alpaca.place_trailing_stop_order('AAPL', 'sell', 1, 2)", "alpaca", "sdk-submit-stop-order"),
        ("alpaca.place_bracket_order('AAPL', 1, 'buy')", "alpaca", "sdk-submit-bracket-order"),
        ("alpaca.place_oco_order('AAPL', 1, 'sell')", "alpaca", "sdk-submit-oco-order"),
        ("alpaca.place_oto_order('AAPL', 1, 'buy')", "alpaca", "sdk-submit-oto-order"),
        ("alpaca.place_order_with_tp_sl('AAPL', 'buy', 1)", "alpaca", "sdk-submit-tp-sl-order"),
        ("alpaca.open_position_with_tp_sl('AAPL', 'buy', 1)", "alpaca", "sdk-submit-tp-sl-order"),
    ],
)
def test_python_detects_extended_provider_wrapper_vocabulary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    call: str,
    provider: str,
    operation: str,
) -> None:
    findings = _python_fixture_findings(
        tmp_path,
        monkeypatch,
        f"""
import {provider}
def mutate({provider}):
    return {call}
""",
    )
    assert [(item.provider, item.operation) for item in findings] == [
        (provider, operation)
    ]


@pytest.mark.parametrize(
    ("method", "operation"),
    [
        ("create_order", "sdk-submit-order"),
        ("create_market_order", "sdk-submit-order"),
        ("create_limit_order", "sdk-submit-order"),
        ("create_market_buy_order", "sdk-submit-order"),
        ("create_market_sell_order", "sdk-submit-order"),
        ("edit_order", "sdk-replace-order"),
        ("cancel_order", "sdk-cancel-order"),
        ("cancel_orders", "sdk-cancel-orders"),
        ("cancel_all_orders", "sdk-cancel-all-orders"),
    ],
)
def test_python_resolves_ccxt_receiver_provider(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    method: str,
    operation: str,
) -> None:
    findings = _python_fixture_findings(
        tmp_path,
        monkeypatch,
        f"""
import ccxt
exchange = ccxt.binance()
def mutate():
    return exchange.{method}('BTC/USDT')
""",
    )
    assert [(item.provider, item.operation) for item in findings] == [
        ("binance", operation)
    ]


def test_python_conservatively_detects_dynamic_provider_raw_transport(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    findings = _python_fixture_findings(
        tmp_path,
        monkeypatch,
        """
class BinanceClient:
    def request(self, method, path, data=None):
        url = self.base_url + path
        return self.session.request(method, url, json=data)

def bypass(client):
    return client._do_request(
        "POST",
        "/api/v3/order",
        params={"symbol": "BTCUSDT"},
    )
""",
        name="aureon/exchanges/binance_client.py",
    )
    assert len(findings) == 2
    assert {finding.provider for finding in findings} == {"binance"}
    assert {finding.operation for finding in findings} == {
        "dynamic-provider-mutation",
        "submit-order",
    }
    assert {finding.transport for finding in findings} == {
        "raw-http",
        "raw-http-dynamic",
    }


def test_python_proves_injected_fetch_uses_read_only_registry_default(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    read_only = _python_fixture_findings(
        tmp_path,
        monkeypatch,
        """
from typing import Callable

BINANCE_REFERENCE = "https://api.binance.com/api/v3/ticker/price"
Fetcher = Callable[[str], dict]

def _registry_fetch(url: str):
    return ToolRegistry().execute("web_fetch", {"url": url})

def scout(url: str, fetcher: Fetcher | None = None):
    fetch = fetcher or _registry_fetch
    return fetch(url)
""",
        name="aureon/grants/scout.py",
    )
    assert read_only == []

    unknown_default = _python_fixture_findings(
        tmp_path,
        monkeypatch,
        """
from typing import Callable

BINANCE_REFERENCE = "https://api.binance.com/api/v3/ticker/price"
Fetcher = Callable[[str], dict]

def scout(url: str, fetcher: Fetcher | None = None):
    fetch = fetcher or unknown_fetch
    return fetch(url)
""",
        name="aureon/grants/unknown_scout.py",
    )
    assert [(item.operation, item.transport) for item in unknown_default] == [
        ("dynamic-provider-mutation", "raw-http-dynamic")
    ]


def test_python_fetch_with_explicit_or_dynamic_method_remains_a_blocker(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    findings = _python_fixture_findings(
        tmp_path,
        monkeypatch,
        """
BINANCE_REFERENCE = "https://api.binance.com/api/v3/order"

def mutate(fetch, url, method):
    fetch(url, method=method)
    return fetch(url, method="POST")
""",
        name="aureon/exchanges/binance_dynamic_fetch.py",
    )
    assert len(findings) == 2
    assert all(item.operation == "dynamic-provider-mutation" for item in findings)
    assert all(item.transport == "raw-http-dynamic" for item in findings)


def test_typescript_detects_url_constructor_method_variable_and_camel_sdk(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    findings = _typescript_fixture_findings(
        tmp_path,
        monkeypatch,
        """
const BASE_URL = 'https://api.binance.com';
async function binanceRequest(endpoint: string, method: string) {
  const url = new URL(endpoint, BASE_URL);
  return fetch(url.toString(), { method });
}
async function submit(client: any) {
  await binanceRequest('/api/v3/order', 'POST');
  await client.createMarketOrder('BTCUSDT');
}
""",
        name="scripts/traders/binance_fixture.ts",
    )
    assert any(
        item.provider == "binance"
        and item.operation == "dynamic-provider-mutation"
        and item.transport == "raw-http-dynamic"
        for item in findings
    )
    assert any(
        item.provider == "binance" and item.operation == "submit-order"
        for item in findings
    )
    assert any(
        item.provider == "binance" and item.operation == "sdk-submit-order"
        for item in findings
    )


@pytest.mark.parametrize("suffix", [".js", ".mjs", ".cjs"])
def test_javascript_modules_use_typescript_scanner_and_source_discovery(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    suffix: str,
) -> None:
    source = """
const endpoint = '/0/private/AddOrder';
const method = 'POST';
fetch(new URL(endpoint, 'https://api.kraken.com'), { method });
"""
    findings = _typescript_fixture_findings(
        tmp_path,
        monkeypatch,
        source,
        name=f"scripts/traders/kraken_fixture{suffix}",
    )
    discovered_paths = AUDITOR.source_paths(tmp_path)
    assert [path.suffix for path in discovered_paths] == [suffix]
    assert any(
        item.provider == "kraken" and item.operation == "submit-order"
        for item in findings
    )


def test_javascript_global_provider_words_do_not_taint_unrelated_mutations(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    findings = _typescript_fixture_findings(
        tmp_path,
        monkeypatch,
        """
const courseCopy = 'Compare Binance, Kraken, Capital, Alpaca and OANDA.';
sandboxSessions.delete(sessionId);
socket.send(JSON.stringify({ event: 'subscribe', channel: 'prices' }));
http.request({
  hostname: '127.0.0.1',
  port: AUREON_PORT,
  path: '/internal/run',
  method: 'POST',
});
fetch('https://api.openai.com/v1/chat/completions', { method: 'POST' });
""",
        name="server.mjs",
    )
    assert findings == []


def test_typescript_sdk_action_keeps_file_provider_context_without_tainting_delete(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    findings = _typescript_fixture_findings(
        tmp_path,
        monkeypatch,
        """
const supportedProviders = ['Binance', 'Kraken'];
async function exit(key: string) {
  await this.closePosition(key, 'STOP');
  this.positions.delete(key);
}
""",
        name="scripts/traders/waveRider.ts",
    )
    assert len(findings) == 1
    assert findings[0].provider == "multi-provider"
    assert findings[0].operation == "sdk-close-position"
    assert findings[0].transport == "sdk-or-provider-wrapper"


def test_provider_file_context_does_not_turn_local_queues_into_mutations(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    findings = _python_fixture_findings(
        tmp_path,
        monkeypatch,
        """
class BinanceWebSocketClient:
    def publish(self, trade):
        self.trade_queue.put(trade, block=False)
        self.error_queue.put('local diagnostic')
""",
        name="aureon/exchanges/binance_ws_client.py",
    )
    assert findings == []


def test_capital_session_auth_post_is_not_an_economic_mutation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    findings = _python_fixture_findings(
        tmp_path,
        monkeypatch,
        """
import requests

class CapitalClient:
    def _create_session(self, payload, headers):
        url = f'{self.base_url}/session'
        return requests.post(url, json=payload, headers=headers, timeout=10)
""",
        name="aureon/exchanges/capital_client.py",
    )
    assert findings == []


def test_hmrc_oauth_token_exchange_is_not_an_economic_mutation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    findings = _python_fixture_findings(
        tmp_path,
        monkeypatch,
        """
import requests

class HMRCApiClient:
    def _token_request(self, payload):
        return requests.post(
            self.config.token_url,
            data=payload,
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
        )
""",
        name="Kings_Accounting_Suite/core/hnc_hmrc_api.py",
    )
    assert findings == []


@pytest.mark.parametrize(
    ("endpoint", "method", "operation"),
    [
        ("/fapi/v1/order", "POST", "submit-futures-order"),
        ("/dapi/v1/order", "DELETE", "cancel-delivery-order"),
        ("/eapi/v1/order", "POST", "submit-options-order"),
        ("/papi/v1/order", "POST", "submit-portfolio-order"),
        ("/fapi/v1/batchOrders", "POST", "submit-futures-order-batch"),
        ("/api/v3/orderList/oco", "POST", "submit-oco-order"),
        ("/sapi/v1/margin/order/oco", "POST", "submit-margin-oco-order"),
        ("/api/v3/sor/order", "POST", "submit-sor-order"),
        ("/api/v3/order/amend/keepPriority", "PUT", "amend-order"),
        ("/0/private/AmendOrder", "POST", "amend-order"),
    ],
)
def test_endpoint_families_cover_advanced_provider_mutations(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    endpoint: str,
    method: str,
    operation: str,
) -> None:
    findings = _python_fixture_findings(
        tmp_path,
        monkeypatch,
        f"""
def mutate(client):
    return client.request('{method}', '{endpoint}')
""",
    )
    assert [item.operation for item in findings] == [operation]


@pytest.mark.parametrize(
    "source",
    [
        "def read(client):\n    return client.request('GET', '/api/v3/order')\n",
        "def test(client):\n    return client.request('POST', '/api/v3/order/test')\n",
        "def read(client):\n    return client.request('GET', '/v2/orders')\n",
        "def read(client):\n    return client.request('POST', '/trade/v2/orders')\n",
        (
            "import json\n"
            "async def subscribe(ws):\n"
            "    await ws.send(json.dumps({'action': 'subscribe', 'trades': ['BTC/USD']}))\n"
        ),
    ],
)
def test_read_only_and_non_target_routes_are_negative_controls(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    source: str,
) -> None:
    assert _python_fixture_findings(tmp_path, monkeypatch, source) == []


def test_consume_and_call_requires_structural_last_mile_binding(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    valid = _python_fixture_findings(
        tmp_path,
        monkeypatch,
        """
def dispatch(boundary, permit, client, body):
    def transport():
        return client.place_market_order('BTCUSDT', 'BUY')
    return boundary.consume_and_call(
        permit,
        method='POST',
        path='/api/v3/order',
        body=body,
        transport=transport,
    )
""",
        name="arbitrary/path.py",
    )
    assert any(item.transport == "economic-boundary-dispatch" for item in valid)

    invalid = _python_fixture_findings(
        tmp_path,
        monkeypatch,
        """
def dispatch(boundary, permit, body):
    def transport(value):
        return value
    return boundary.consume_and_call(
        permit,
        method='POST',
        path='/api/v3/order',
        body=body,
        transport=transport,
    )
""",
        name="aureon/trading/bounded_binance_roundtrip.py",
    )
    assert invalid == []


def test_recovery_consume_requires_recovered_permit_and_provider_transport(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    valid = _python_fixture_findings(
        tmp_path,
        monkeypatch,
        """
def dispatch(recovery, recovered, client, body):
    return recovery.consume_and_call(
        recovered,
        method='POST',
        path='/0/private/AddOrder',
        body=body,
        transport=lambda: client.place_market_order('XBTUSD', 'sell'),
    )
""",
    )
    assert any(item.transport == "economic-boundary-dispatch" for item in valid)

    invalid = _python_fixture_findings(
        tmp_path,
        monkeypatch,
        """
def dispatch(recovery, permit, client, body):
    return recovery.consume_and_call(
        permit,
        method='POST',
        path='/0/private/AddOrder',
        body=body,
        transport=lambda: client.place_market_order('XBTUSD', 'sell'),
    )
""",
    )
    assert not any(item.transport == "economic-boundary-dispatch" for item in invalid)
