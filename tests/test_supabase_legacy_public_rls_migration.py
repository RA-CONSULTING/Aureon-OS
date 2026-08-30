from __future__ import annotations

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = REPO_ROOT / "supabase" / "migrations"
PROVIDER_RECEIPT = (
    REPO_ROOT / "docs" / "SUPABASE_PRODUCTION_RLS_HARDENING_20260811.json"
)
TARGET_TABLES = {
    "backend_health_metrics",
    "backup_jobs",
    "backup_records",
    "backup_restore_logs",
    "celestial_data",
    "chart_annotations",
    "chart_data",
    "chat_messages",
    "dashboard_comments",
    "dashboard_configurations",
    "data_backups",
    "electromagnetic_data",
    "health_alert_events",
    "load_balancer_metrics",
    "optimization_recommendations",
    "performance_optimization_analysis",
    "predictive_scaling_models",
    "resource_allocation_history",
    "schumann_resonance_data",
    "server_correlation_analysis",
    "server_registry",
    "system_alerts",
}


def _migration_sql() -> str:
    matches = list(MIGRATIONS.glob("*_lock_down_legacy_public_tables.sql"))
    assert len(matches) == 1
    return matches[0].read_text(encoding="utf-8").lower()


def test_legacy_public_table_boundary_is_complete_and_fail_closed() -> None:
    sql = _migration_sql()
    array_match = re.search(
        r"foreach\s+target_table\s+in\s+array\s+array\[(.*?)\]\s+loop",
        sql,
        flags=re.DOTALL,
    )
    assert array_match is not None
    assert set(re.findall(r"'([a-z_][a-z0-9_]*)'", array_match.group(1))) == (
        TARGET_TABLES
    )

    assert "to_regclass(format('public.%i', target_table))" in sql
    assert "'alter table public.%i enable row level security'" in sql
    assert (
        "'revoke all privileges on table public.%i "
        "from public, anon, authenticated'"
    ) in sql
    assert (
        "'grant select, insert, update, delete on table public.%i "
        "to service_role'"
    ) in sql
    assert (
        "'create policy deny_direct_client_access on public.%i '"
        in sql
    )
    assert (
        "'for all to anon, authenticated using (false) with check (false)'"
        in sql
    )


def test_migration_does_not_add_client_grants_or_privileged_functions() -> None:
    sql = _migration_sql()

    assert re.search(r"grant\s+[^;]+\s+to\s+(anon|authenticated)", sql) is None
    assert "security definer" not in sql
    assert "auth.role()" not in sql
    assert "grant all" not in sql


def test_provider_receipt_confirms_exact_metadata_only_readback() -> None:
    receipt = json.loads(PROVIDER_RECEIPT.read_text(encoding="utf-8"))

    assert (
        receipt["schema_version"]
        == "aureon.supabase.production_rls_hardening.v1"
    )
    assert receipt["migration_name"] == "lock_down_legacy_public_tables"
    assert receipt["target_table_count"] == len(TARGET_TABLES) == 22
    assert receipt["target_tables"] == sorted(TARGET_TABLES)
    assert receipt["row_content_read"] is False
    assert receipt["row_content_changed"] is False

    readback = receipt["provider_readback"]
    assert readback["migration_ledger_recorded"] is True
    for field in (
        "rls_enabled_count",
        "anon_crud_revoked_count",
        "authenticated_crud_revoked_count",
        "service_role_crud_retained_count",
        "deny_direct_client_access_policy_count",
    ):
        assert readback[field] == 22
    assert readback["target_table_security_advisor_findings"] == 0
    assert receipt["completion_status"] == "provider_applied_and_read_back"
