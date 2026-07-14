import json
import os
from pathlib import Path

import pytest

from aureon.autonomous.mind_wiring_audit import (
    AUDIT_ENV_FLAGS,
    ImportProbe,
    MindAuditEntry,
    MindAuditReport,
    LocalServiceProbe,
    apply_audit_environment,
    blocked_order,
    build_module_index,
    build_report,
    classify_entry,
    render_markdown,
    repo_root_from,
    resolve_module_name,
    write_report,
    LiveOrderBlocked,
)
from aureon.core.aureon_organism_spine import build_organism_manifest, connect_organism
from aureon.core.aureon_runtime_safety import (
    apply_live_runtime_environment,
    child_env_for_mode,
    live_block_reason,
    real_orders_allowed,
)


def test_resolver_maps_registry_short_name_to_real_package_path():
    root = repo_root_from(Path(__file__))
    by_stem, by_module = build_module_index(root)

    resolved, rel_path, evidence = resolve_module_name(
        "global_financial_feed",
        root,
        by_stem,
        by_module,
    )

    assert resolved == "aureon.data_feeds.global_financial_feed"
    assert rel_path == "aureon/data_feeds/global_financial_feed.py"
    assert evidence


def test_classification_distinguishes_wired_partial_broken_and_vision():
    wired = MindAuditEntry(
        id="wired",
        name="Wired",
        domain="mind",
        sources=["test"],
        declared_module="aureon.wired",
        resolved_module="aureon.wired",
        path="aureon/wired.py",
        event_topics=["mind.ready"],
    )
    wired.import_probe = ImportProbe(attempted=True, ok=True)
    classify_entry(wired, {}, is_surface=False)
    assert wired.status == "wired"

    partial = MindAuditEntry(
        id="partial",
        name="Partial",
        domain="mind",
        sources=["test"],
        declared_module="aureon.partial",
        resolved_module="aureon.partial",
        path="aureon/partial.py",
    )
    partial.import_probe = ImportProbe(attempted=True, ok=True)
    classify_entry(partial, {}, is_surface=False)
    assert partial.status == "partial"

    broken = MindAuditEntry(
        id="broken",
        name="Broken",
        domain="mind",
        sources=["test"],
        declared_module="missing_module",
    )
    classify_entry(broken, {}, is_surface=False)
    assert broken.status == "broken"

    vision = MindAuditEntry(
        id="vision",
        name="Future System",
        domain="mind",
        sources=["test"],
        declared_module="future_system",
        purpose="Planned future capability",
    )
    classify_entry(vision, {"has_placeholder": True}, is_surface=False)
    assert vision.status == "vision_only"


def test_audit_environment_blocks_live_order_paths(monkeypatch):
    for key in AUDIT_ENV_FLAGS:
        monkeypatch.delenv(key, raising=False)

    applied = apply_audit_environment()

    assert applied["AUREON_AUDIT_MODE"] == "1"
    assert applied["AUREON_LIVE_TRADING"] == "0"
    assert applied["AUREON_DISABLE_REAL_ORDERS"] == "1"
    for key, value in AUDIT_ENV_FLAGS.items():
        assert applied[key] == value

    try:
        blocked_order(symbol="BTC/GBP", side="buy", qty=1)
    except LiveOrderBlocked:
        pass
    else:
        raise AssertionError("blocked_order must fail closed")


def test_runtime_safety_requires_explicit_live_gate(monkeypatch):
    for key in ("AUREON_AUDIT_MODE", "AUREON_LIVE_TRADING", "AUREON_DISABLE_REAL_ORDERS"):
        monkeypatch.delenv(key, raising=False)

    assert real_orders_allowed() is False
    assert live_block_reason("test") == "test: AUREON_LIVE_TRADING is not explicitly enabled"

    monkeypatch.setenv("AUREON_LIVE_TRADING", "1")
    assert real_orders_allowed() is True

    monkeypatch.setenv("AUREON_DISABLE_REAL_ORDERS", "1")
    assert real_orders_allowed() is False
    with pytest.raises(RuntimeError):
        child_env_for_mode(True, os.environ)

    safe_env = child_env_for_mode(False, {})
    assert safe_env["AUREON_LIVE_TRADING"] == "0"
    assert safe_env["AUREON_DISABLE_REAL_ORDERS"] == "1"


def test_queen_autonomy_stays_simulated_in_audit_mode(monkeypatch):
    monkeypatch.setenv("AUREON_AUDIT_MODE", "1")
    monkeypatch.setenv("AUREON_DISABLE_REAL_ORDERS", "1")

    from aureon.autonomous.aureon_queen_full_autonomy_enablement import initialize_queen_autonomy

    result = initialize_queen_autonomy()

    assert result["safe_mode"] is True
    assert result["trading_mode"] == "AUDIT_DRY_RUN"
    assert os.environ["AUREON_LIVE_TRADING"] == "0"
    assert os.environ["AUREON_DISABLE_REAL_ORDERS"] == "1"


def test_queen_autonomy_live_profile_keeps_runtime_order_gates(monkeypatch):
    for key in (
        "AUREON_AUDIT_MODE",
        "AUREON_LIVE_TRADING",
        "AUREON_DISABLE_REAL_ORDERS",
        "AUREON_DISABLE_EXCHANGE_MUTATIONS",
        "AUREON_TRADE_GATING",
        "AUREON_APPROVAL_REQUIRED",
        "AUREON_QUEEN_VETO",
        "AUREON_SAFETY_CHECKS",
    ):
        monkeypatch.delenv(key, raising=False)

    apply_live_runtime_environment()

    import aureon.autonomous.aureon_queen_full_autonomy_enablement as autonomy_module

    monkeypatch.setattr(
        autonomy_module.QueenAutonomyConfig,
        "verify_autonomy_status",
        lambda self: {"all_checks_passed": True, "checks": {"unit_test": True}},
    )

    result = autonomy_module.initialize_queen_autonomy()

    assert result.get("safe_mode") is not True
    assert result["sovereignty_level"] == "RUNTIME_GATED"
    assert result["trading_mode"] == "INTENT_ONLY_RUNTIME_GATED_LIVE"
    assert os.environ["AUREON_TRADE_GATING"] == "RUNTIME_GATED"
    assert os.environ["AUREON_APPROVAL_REQUIRED"] == "1"
    assert os.environ["AUREON_QUEEN_VETO"] == "ENABLED"
    assert os.environ["AUREON_SAFETY_CHECKS"] == "ENFORCED"


def test_baton_link_preserves_audit_dry_run_flags(monkeypatch):
    from aureon.core import aureon_baton_link

    monkeypatch.setenv("AUREON_AUDIT_MODE", "1")
    monkeypatch.setenv("AUREON_DRY_RUN", "1")
    monkeypatch.setenv("DRY_RUN", "1")

    aureon_baton_link._enforce_real_data_only()

    assert aureon_baton_link._audit_mode_enabled() is True
    assert aureon_baton_link.os.environ["AUREON_DRY_RUN"] == "1"
    assert aureon_baton_link.os.environ["DRY_RUN"] == "1"


def test_report_includes_registry_overlay_and_safe_service_probes():
    root = repo_root_from(Path(__file__))

    report = build_report(
        repo_root=root,
        do_static=True,
        do_imports=False,
        do_local_services=True,
    )

    assert report.counts["total"] > 20
    assert report.counts["broken"] == 0
    assert report.counts["partial"] == 0
    assert report.counts["vision_only"] == 0
    assert any("registry:" in ",".join(entry.sources) for entry in report.entries)
    assert any("overlay:surface" in entry.sources for entry in report.entries)
    assert any("organism_spine" in entry.sources for entry in report.entries)
    assert any(entry.domain == "accounting" for entry in report.entries)
    assert any(entry.resolved_module == "aureon.core.organism_contracts" for entry in report.entries)
    assert any(entry.domain == "contract_stack" for entry in report.entries)
    assert any(probe.id == "cognition.runtime" for probe in report.service_probes)
    assert any(probe.id == "accounting.context" for probe in report.service_probes)
    assert not any(probe.status == "unsafe_order_path" for probe in report.service_probes)


def test_organism_spine_registers_repo_modules_without_runtime_side_effects(monkeypatch):
    root = repo_root_from(Path(__file__))
    monkeypatch.setenv("AUREON_AUDIT_MODE", "1")

    manifest = build_organism_manifest(repo_root=root)

    modules = manifest.by_module()
    assert "aureon.autonomous.aureon_cognition_runtime" in modules
    assert "aureon.core.aureon_thought_bus" in modules
    assert "aureon.core.organism_contracts" in modules
    assert modules["aureon.core.organism_contracts"].domain == "contract_stack"
    assert "Kings_Accounting_Suite.tools.generate_full_company_accounts" in modules
    assert modules["Kings_Accounting_Suite.tools.generate_full_company_accounts"].domain == "accounting"
    assert modules["aureon.core.aureon_thought_bus"].organism_topic.startswith("organism.")

    connected = connect_organism(repo_root=root, publish_heartbeat=False)
    assert len(connected.nodes) == len(manifest.nodes)


def test_render_and_write_artifacts(tmp_path):
    entry = MindAuditEntry(
        id="thoughtbus",
        name="ThoughtBus",
        domain="thought_bus",
        sources=["test"],
        declared_module="aureon.core.aureon_thought_bus",
        resolved_module="aureon.core.aureon_thought_bus",
        path="aureon/core/aureon_thought_bus.py",
        status="wired",
        evidence=["test evidence"],
        next_action="Keep covered.",
    )
    report = MindAuditReport(
        generated_at="2026-05-08T00:00:00+00:00",
        repo_root=str(tmp_path),
        safety={"AUREON_AUDIT_MODE": "1"},
        counts={"wired": 1, "partial": 0, "broken": 0, "vision_only": 0, "unknown": 0, "total": 1},
        entries=[entry],
        service_probes=[
            LocalServiceProbe(
                id="service",
                name="Service",
                url="http://127.0.0.1:1",
                source="test",
                status="not_running",
            )
        ],
    )

    markdown = render_markdown(report)
    assert "Aureon Whole-Mind Wiring Audit" in markdown
    assert "`wired`: 1" in markdown

    md_path = tmp_path / "mind.md"
    json_path = tmp_path / "mind.json"
    write_report(report, md_path, json_path)

    assert md_path.exists()
    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert data["counts"]["total"] == 1
